#include <screen/screen.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *operation, int code) {
    fprintf(stderr, "%s failed: %d\n", operation, code);
    return 1;
}

int main(int argc, char **argv) {
    int width = argc > 1 ? atoi(argv[1]) : 320;
    int height = argc > 2 ? atoi(argv[2]) : 480;
    if (width <= 0 || height <= 0) {
        fprintf(stderr, "invalid LCD dimensions\n");
        return 2;
    }

    screen_context_t context = NULL;
    screen_window_t window = NULL;
    if (screen_create_context(&context, SCREEN_APPLICATION_CONTEXT) != 0) {
        return fail("screen_create_context", -1);
    }
    if (screen_create_window(&window, context) != 0) {
        screen_destroy_context(context);
        return fail("screen_create_window", -1);
    }

    int format = SCREEN_FORMAT_RGBA8888;
    int usage = SCREEN_USAGE_WRITE;
    int size[2] = {width, height};
    int visible = 1;
    if (screen_set_window_property_iv(window, SCREEN_PROPERTY_FORMAT, &format) != 0 ||
        screen_set_window_property_iv(window, SCREEN_PROPERTY_USAGE, &usage) != 0 ||
        screen_set_window_property_iv(window, SCREEN_PROPERTY_BUFFER_SIZE, size) != 0 ||
        screen_set_window_property_iv(window, SCREEN_PROPERTY_SIZE, size) != 0 ||
        screen_create_window_buffers(window, 2) != 0 ||
        screen_set_window_property_iv(window, SCREEN_PROPERTY_VISIBLE, &visible) != 0) {
        screen_destroy_window(window);
        screen_destroy_context(context);
        return fail("configure QNX Screen window", -1);
    }

    const size_t row_bytes = (size_t)width * 4;
    uint8_t *row = malloc(row_bytes);
    if (row == NULL) {
        screen_destroy_window(window);
        screen_destroy_context(context);
        return fail("allocate input row", -1);
    }

    char header[80];
    while (fgets(header, sizeof(header), stdin) != NULL) {
        int frame_width = 0;
        int frame_height = 0;
        if (sscanf(header, "IGNISRGBA %d %d", &frame_width, &frame_height) != 2 ||
            frame_width != width || frame_height != height) {
            fprintf(stderr, "invalid IGNIS LCD frame header: %s", header);
            break;
        }
        screen_buffer_t buffers[2];
        if (screen_get_window_property_pv(window, SCREEN_PROPERTY_RENDER_BUFFERS,
                                          (void **)buffers) != 0) {
            break;
        }
        void *pointer = NULL;
        int stride = 0;
        if (screen_get_buffer_property_pv(buffers[0], SCREEN_PROPERTY_POINTER, &pointer) != 0 ||
            screen_get_buffer_property_iv(buffers[0], SCREEN_PROPERTY_STRIDE, &stride) != 0) {
            break;
        }
        for (int y = 0; y < height; ++y) {
            if (fread(row, 1, row_bytes, stdin) != row_bytes) {
                goto done;
            }
            memcpy((uint8_t *)pointer + (size_t)y * (size_t)stride, row, row_bytes);
        }
        int rectangle[4] = {0, 0, width, height};
        if (screen_post_window(window, buffers[0], 1, rectangle, 0) != 0) {
            break;
        }
    }

done:
    free(row);
    screen_destroy_window(window);
    screen_destroy_context(context);
    return 0;
}
