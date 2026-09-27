#ifndef INBE_DEVICE_HOST_H
#define INBE_DEVICE_HOST_H

/* The application runtime passes only its own window handle. */
void app_device_attach_window(void *window);
int app_device_system_dark(void);
int app_device_orientation(void);
void app_device_set_orientation(int mode);
int app_device_width(void);
int app_device_height(void);
void app_device_resize(int width, int height);
void app_device_fullscreen(int enabled);
void app_device_web_orientation(int mode);
void app_device_web_resize(void);

#endif
