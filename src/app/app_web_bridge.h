#ifndef INBE_APP_WEB_BRIDGE_H
#define INBE_APP_WEB_BRIDGE_H

int web_download_file(const char *path, const char *filename,
                      const char *mime);
int web_context_click_in_bounds(int x0, int y0, int x1, int y1);
void app_web_storage_flush(int log_success);
int app_web_storage_flush_critical(int timeout_ms, int log_success);
int app_web_extension_available(void);

#endif
