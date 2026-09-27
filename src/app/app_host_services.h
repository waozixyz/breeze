#ifndef INBE_APP_HOST_SERVICES_H
#define INBE_APP_HOST_SERVICES_H

#include <stdint.h>

uint8_t *app_getenv_bytes(uint8_t *name);
double app_monotonic_seconds(void);
void app_log_line(uint8_t *line);
int app_desktop_platform(void);
int app_web_platform(void);
int app_android_platform(void);
int app_windows_platform(void);
int app_plan9_platform(void);
int app_preview_mode(void);

#endif
