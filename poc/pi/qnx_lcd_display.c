#include <devctl.h>
#include <errno.h>
#include <fcntl.h>
#include <hw/io-spi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/neutrino.h>
#include <sys/rpi_gpio.h>
#include <unistd.h>

/* Waveshare 3.5inch RPi LCD (A): ILI9486 on SPI0 CE0. */
#define LCD_WIDTH 480
#define LCD_HEIGHT 320
#define LCD_DC_GPIO 24
#define LCD_RESET_GPIO 25
#define SPI_PATH "/dev/io-spi/spi0/dev0"
#define SPI_INIT_CLOCK_HZ 10000000U
#define SPI_FRAME_CLOCK_HZ 10000000U
#define LCD_BAND_HEIGHT 1
#define LCD_FRAME_PASSES 2
#define LCD_WRITER_LOCK_PATH "/dev/shmem/ignis-lcd-writer.lock"

static int spi_fd = -1;
static int gpio_fd = -1;
static int writer_lock_fd = -1;

/*
 * O_EXCL provides the atomic single-writer guard supported by this QNX image.
 * The helper owns SPI for its complete lifetime and removes the volatile lock
 * when its input closes.
 */
static void release_writer_guard(void) {
    if (writer_lock_fd >= 0) {
        close(writer_lock_fd);
        writer_lock_fd = -1;
    }
    unlink(LCD_WRITER_LOCK_PATH);
}

static int acquire_writer_guard(void) {
    writer_lock_fd = open(LCD_WRITER_LOCK_PATH, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (writer_lock_fd < 0) {
        if (errno == EEXIST) {
            fprintf(stderr, "IGNIS LCD writer already active; skipping\n");
            return 1;
        }
        perror(LCD_WRITER_LOCK_PATH);
        return -1;
    }
    if (atexit(release_writer_guard) != 0) {
        perror("IGNIS LCD writer guard cleanup");
        close(writer_lock_fd);
        writer_lock_fd = -1;
        unlink(LCD_WRITER_LOCK_PATH);
        return -1;
    }
    return 0;
}

static int gpio_message(int pin, unsigned subtype, unsigned value) {
    if (gpio_fd < 0) {
        gpio_fd = open("/dev/gpio/msg", O_RDWR);
    }
    if (gpio_fd < 0) {
        perror("/dev/gpio/msg");
        return -1;
    }
    rpi_gpio_msg_t message = {
        .hdr.type = _IO_MSG,
        .hdr.subtype = subtype,
        .hdr.mgrid = RPI_GPIO_IOMGR,
        .gpio = (unsigned)pin,
        .value = value};
    if (MsgSend(gpio_fd, &message, sizeof(message), NULL, 0) != EOK) {
        perror("GPIO MsgSend");
        return -1;
    }
    return 0;
}

static int gpio_open_output(int pin) {
    return gpio_message(pin, RPI_GPIO_SET_SELECT, RPI_GPIO_FUNC_OUT);
}

static int gpio_write(int pin, int high) {
    return gpio_message(pin, RPI_GPIO_WRITE, high ? 1U : 0U);
}

static int spi_transfer(const uint8_t *data, uint32_t length) {
    spi_xchng_t *message = malloc(sizeof(*message) + length);
    if (message == NULL) {
        return -1;
    }
    message->nbytes = length;
    memcpy(message->data, data, length);
    int result = devctl(spi_fd, DCMD_SPI_DATA_XCHNG, message,
                        sizeof(*message) + length, NULL);
    free(message);
    if (result != EOK) {
        fprintf(stderr, "SPI transfer failed: %d\n", result);
        return -1;
    }
    return 0;
}

static int spi_configure(uint32_t clock_rate) {
    spi_cfg_t configuration = {
        .mode = SPI_MODE_WORD_WIDTH_8 | SPI_MODE_CPHA_0 | SPI_MODE_CPOL_0 |
                SPI_MODE_BODER_MSB,
        .clock_rate = clock_rate};
    int error = devctl(spi_fd, DCMD_SPI_SET_CONFIG, &configuration,
                       sizeof(configuration), NULL);
    if (error != EOK) {
        fprintf(stderr, "SPI configuration failed at %u Hz: %d\n", clock_rate, error);
        return -1;
    }
    spi_devinfo_t information;
    error = devctl(spi_fd, DCMD_SPI_GET_DEVINFO, &information,
                   sizeof(information), NULL);
    if (error == EOK) {
        fprintf(stderr, "IGNIS LCD SPI clock: %u Hz\n", information.current_clkrate);
    }
    return 0;
}

static void spi_report_driver(void) {
    spi_drvinfo_t information = {0};
    int error = devctl(spi_fd, DCMD_SPI_GET_DRVINFO, &information,
                       sizeof(information), NULL);
    if (error == EOK) {
        fprintf(stderr, "IGNIS LCD SPI driver: %s features=0x%08x%s\n",
                information.name, information.feature,
                (information.feature & SPI_FEATURE_DMA) ? " DMA" : "");
    }
}

static int lcd_command(uint8_t command, const uint8_t *data, size_t count) {
    uint8_t encoded_command[2] = {0, command};
    if (gpio_write(LCD_DC_GPIO, 0) != 0 ||
        spi_transfer(encoded_command, sizeof(encoded_command)) != 0) {
        return -1;
    }
    if (count == 0) {
        return 0;
    }
    uint8_t encoded[64];
    if (count * 2 > sizeof(encoded)) {
        return -1;
    }
    for (size_t index = 0; index < count; ++index) {
        encoded[index * 2] = 0;
        encoded[index * 2 + 1] = data[index];
    }
    if (gpio_write(LCD_DC_GPIO, 1) != 0) {
        return -1;
    }
    return spi_transfer(encoded, (uint32_t)(count * 2));
}

static int lcd_initialize(void) {
    if (gpio_open_output(LCD_DC_GPIO) != 0 ||
        gpio_open_output(LCD_RESET_GPIO) != 0 ||
        gpio_write(LCD_RESET_GPIO, 1) != 0) {
        return -1;
    }
    usleep(120000);
    gpio_write(LCD_RESET_GPIO, 0);
    usleep(120000);
    gpio_write(LCD_RESET_GPIO, 1);
    usleep(120000);

    /* Initialization used by the proven clear logo/red-white alert build. */
    const uint8_t interface_mode[] = {0x00};
    const uint8_t pixel_format[] = {0x55};
    const uint8_t power1[] = {0x09, 0x09};
    const uint8_t power2[] = {0x41, 0x00};
    const uint8_t power3[] = {0x33};
    const uint8_t vcom[] = {0x00, 0x36};
    const uint8_t madctl[] = {0x28}; /* BGR + row/column exchange: landscape */
    const uint8_t gamma_positive[] = {
        0x00, 0x2C, 0x2C, 0x0B, 0x0C, 0x04, 0x4C, 0x64,
        0x36, 0x03, 0x0E, 0x01, 0x10, 0x01, 0x00};
    const uint8_t gamma_negative[] = {
        0x0F, 0x37, 0x37, 0x0C, 0x0F, 0x05, 0x50, 0x32,
        0x36, 0x04, 0x0B, 0x00, 0x19, 0x14, 0x0F};
    const uint8_t display_function[] = {0x00, 0x02, 0x3B};

    if (lcd_command(0xB0, interface_mode, sizeof(interface_mode)) != 0 ||
        lcd_command(0x11, NULL, 0) != 0) {
        return -1;
    }
    usleep(120000);
    if (lcd_command(0x3A, pixel_format, sizeof(pixel_format)) != 0 ||
        lcd_command(0x20, NULL, 0) != 0 ||
        lcd_command(0xC0, power1, sizeof(power1)) != 0 ||
        lcd_command(0xC1, power2, sizeof(power2)) != 0 ||
        lcd_command(0xC2, power3, sizeof(power3)) != 0 ||
        lcd_command(0xC5, vcom, sizeof(vcom)) != 0 ||
        lcd_command(0x36, madctl, sizeof(madctl)) != 0 ||
        lcd_command(0xE0, gamma_positive, sizeof(gamma_positive)) != 0 ||
        lcd_command(0xE1, gamma_negative, sizeof(gamma_negative)) != 0 ||
        lcd_command(0xB6, display_function, sizeof(display_function)) != 0 ||
        lcd_command(0x11, NULL, 0) != 0) {
        return -1;
    }
    usleep(120000);
    return lcd_command(0x29, NULL, 0) == 0 &&
                   lcd_command(0x38, NULL, 0) == 0 &&
                   lcd_command(0x13, NULL, 0) == 0
               ? 0
               : -1;
}

static int lcd_set_columns(void) {
    const uint8_t columns[] = {0x00, 0x00, 0x01, 0xDF};
    return lcd_command(0x2A, columns, sizeof(columns));
}

static int lcd_begin_band(int first_row, int row_count) {
    int last_row = first_row + row_count - 1;
    const uint8_t rows[] = {
        (uint8_t)(first_row >> 8), (uint8_t)first_row,
        (uint8_t)(last_row >> 8), (uint8_t)last_row};
    return lcd_command(0x2B, rows, sizeof(rows)) == 0 &&
                   lcd_command(0x2C, NULL, 0) == 0 &&
                   gpio_write(LCD_DC_GPIO, 1) == 0
               ? 0
               : -1;
}

static int lcd_write_bgr(const uint8_t *bgr) {
    uint8_t pixels[LCD_WIDTH * LCD_BAND_HEIGHT * 2];
    const int band_count = (LCD_HEIGHT + LCD_BAND_HEIGHT - 1) / LCD_BAND_HEIGHT;
    if (lcd_set_columns() != 0) {
        return -1;
    }
    for (int band = 0; band < band_count; ++band) {
        int first_row = band * LCD_BAND_HEIGHT;
        int row_count = LCD_BAND_HEIGHT;
        if (first_row + row_count > LCD_HEIGHT) {
            row_count = LCD_HEIGHT - first_row;
        }
        size_t band_pixels = (size_t)LCD_WIDTH * (size_t)row_count;
        size_t first_pixel = (size_t)first_row * LCD_WIDTH;
        for (size_t index = 0; index < band_pixels; ++index) {
            const uint8_t *source = bgr + (first_pixel + index) * 3;
            uint16_t rgb565 = (uint16_t)((source[2] & 0xF8) << 8) |
                              (uint16_t)((source[1] & 0xFC) << 3) |
                              (uint16_t)(source[0] >> 3);
            pixels[index * 2] = (uint8_t)(rgb565 >> 8);
            pixels[index * 2 + 1] = (uint8_t)rgb565;
        }
        if (lcd_begin_band(first_row, row_count) != 0 ||
            spi_transfer(pixels, (uint32_t)(band_pixels * 2)) != 0) {
            return -1;
        }
    }
    return 0;
}

static int lcd_replace_bgr(const uint8_t *bgr) {
    /* Hide partial rows, then repeat the complete target frame before reveal. */
    if (lcd_command(0x28, NULL, 0) != 0) {
        return -1;
    }
    usleep(20000);
    for (int pass = 0; pass < LCD_FRAME_PASSES; ++pass) {
        if (lcd_write_bgr(bgr) != 0) {
            lcd_command(0x29, NULL, 0);
            return -1;
        }
    }
    if (lcd_command(0x29, NULL, 0) != 0) {
        return -1;
    }
    usleep(20000);
    return 0;
}

int main(int argc, char **argv) {
    int width = argc > 1 ? atoi(argv[1]) : LCD_WIDTH;
    int height = argc > 2 ? atoi(argv[2]) : LCD_HEIGHT;
    if (width != LCD_WIDTH || height != LCD_HEIGHT) {
        fprintf(stderr, "Waveshare LCD (A) requires a 480x320 landscape buffer\n");
        return 2;
    }

    int guard = acquire_writer_guard();
    if (guard > 0) {
        return 0;
    }
    if (guard < 0) {
        return 10;
    }

    spi_fd = open(SPI_PATH, O_RDWR);
    if (spi_fd < 0) {
        perror(SPI_PATH);
        return 3;
    }
    spi_report_driver();
    if (spi_configure(SPI_INIT_CLOCK_HZ) != 0) {
        close(spi_fd);
        return 4;
    }
    if (lcd_initialize() != 0) {
        close(spi_fd);
        return 5;
    }
    if (spi_configure(SPI_FRAME_CLOCK_HZ) != 0) {
        close(spi_fd);
        return 6;
    }

    const size_t frame_bytes = (size_t)width * height * 3;
    uint8_t *frame = malloc(frame_bytes);
    if (frame == NULL) {
        close(spi_fd);
        return 7;
    }
    char header[80];
    unsigned long frame_number = 0;
    while (fgets(header, sizeof(header), stdin) != NULL) {
        int frame_width = 0;
        int frame_height = 0;
        if (sscanf(header, "IGNISBGR %d %d", &frame_width, &frame_height) != 2 ||
            frame_width != width || frame_height != height) {
            fprintf(stderr, "invalid IGNIS LCD frame header\n");
            free(frame);
            close(gpio_fd);
            close(spi_fd);
            return 8;
        }
        if (fread(frame, 1, frame_bytes, stdin) != frame_bytes ||
            lcd_replace_bgr(frame) != 0) {
            free(frame);
            close(gpio_fd);
            close(spi_fd);
            return 9;
        }
        ++frame_number;
        fprintf(stderr, "IGNIS LCD frame %lu complete\n", frame_number);
    }
    fprintf(stderr, "IGNIS LCD writer stopped\n");
    free(frame);
    close(gpio_fd);
    close(spi_fd);
    return 0;
}
