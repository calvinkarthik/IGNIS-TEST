#include <camera/camera_api.h>

#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void stop_capture(int signal_number) {
    (void)signal_number;
    running = 0;
}

static void frame_callback(camera_handle_t handle, camera_buffer_t *buffer, void *arg) {
    (void)handle;
    (void)arg;
    if (buffer == NULL || buffer->framebuf == NULL ||
        buffer->frametype != CAMERA_FRAMETYPE_NV12) {
        return;
    }

    const camera_frame_nv12_t *nv12 = &buffer->framedesc.nv12;
    const uint8_t *y = buffer->framebuf;
    const uint8_t *uv = buffer->framebuf + nv12->uv_offset;

    if (fprintf(stdout, "IGNISNV12 %u %u\n", nv12->width, nv12->height) < 0) {
        running = 0;
        return;
    }
    for (uint32_t row = 0; row < nv12->height; ++row) {
        if (fwrite(y + (size_t)row * nv12->stride, 1, nv12->width, stdout) != nv12->width) {
            running = 0;
            return;
        }
    }
    for (uint32_t row = 0; row < nv12->height / 2; ++row) {
        if (fwrite(uv + (size_t)row * nv12->uv_stride, 1, nv12->width, stdout) != nv12->width) {
            running = 0;
            return;
        }
    }
    fflush(stdout);
}

static void status_callback(camera_handle_t handle, camera_devstatus_t status,
                            uint16_t extra, void *arg) {
    (void)handle;
    (void)arg;
    fprintf(stderr, "QNX camera status=%d extra=%u\n", (int)status, (unsigned)extra);
}

int main(int argc, char **argv) {
    int unit_number = argc > 1 ? atoi(argv[1]) : 1;
    camera_handle_t handle = CAMERA_HANDLE_INVALID;
    camera_error_t error;

    signal(SIGINT, stop_capture);
    signal(SIGTERM, stop_capture);
    setvbuf(stdout, NULL, _IONBF, 0);

    error = camera_open((camera_unit_t)unit_number, CAMERA_MODE_RW, &handle);
    if (error != CAMERA_EOK) {
        fprintf(stderr, "camera_open(unit=%d) failed: %d\n", unit_number, (int)error);
        return 2;
    }

    error = camera_set_vf_property(
        handle,
        CAMERA_IMGPROP_CREATEWINDOW, 0,
        CAMERA_IMGPROP_RENDERTOWINDOW, 0,
        CAMERA_IMGPROP_FORMAT, CAMERA_FRAMETYPE_NV12,
        CAMERA_IMGPROP_WIDTH, 1536,
        CAMERA_IMGPROP_HEIGHT, 864,
        CAMERA_IMGPROP_FRAMERATE, (double)30.0);
    if (error != CAMERA_EOK) {
        fprintf(stderr, "camera_set_vf_property failed: %d\n", (int)error);
        camera_close(handle);
        return 3;
    }

    error = camera_start_viewfinder(handle, frame_callback, status_callback, NULL);
    if (error != CAMERA_EOK) {
        fprintf(stderr, "camera_start_viewfinder failed: %d\n", (int)error);
        camera_close(handle);
        return 4;
    }

    while (running) {
        sleep(1);
    }

    camera_stop_viewfinder(handle);
    camera_close(handle);
    return 0;
}
