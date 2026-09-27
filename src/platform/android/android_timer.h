#ifndef APP_ANDROID_TIMER_H
#define APP_ANDROID_TIMER_H

#include <stddef.h>

#if defined(ANDROID_BUILD) && ANDROID_BUILD
#include <pthread.h>
void android_timer_start(void);
void android_timer_stop(void);
void android_timer_set_app(void *app_ptr);
void android_timer_activate(void);
void android_timer_deactivate(void);
pthread_mutex_t* android_timer_get_mutex(void);
#else
void android_timer_start(void);
void android_timer_stop(void);
void android_timer_set_app(void *app_ptr);
void android_timer_activate(void);
void android_timer_deactivate(void);
void* android_timer_get_mutex(void);
#endif

#endif
