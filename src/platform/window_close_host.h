#ifndef INBE_WINDOW_CLOSE_HOST_H
#define INBE_WINDOW_CLOSE_HOST_H

/* The caller passes only the window it created through raylib. */
void app_window_close_watch(void *window);
int native_take_window_close(void);
void app_window_close_shutdown(void);

#endif
