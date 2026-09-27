#include "platform/android/android_timer.h"

#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <time.h>

static pthread_mutex_t callback_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t callback_ready = PTHREAD_COND_INITIALIZER;
static int callback_count;
static int self_stop_at;
static int self_stop_returned;
static int app_value;

int32_t TimerElapsedMillis(int64_t previous_nanoseconds,
                           int64_t now_nanoseconds);

void
practice_active_advance_elapsed(void *app, int32_t elapsed_ms)
{
    int stop_here;
    assert(app == &app_value);
    assert(elapsed_ms > 0 && elapsed_ms <= 300000);
    pthread_mutex_lock(&callback_mutex);
    callback_count++;
    stop_here = callback_count == self_stop_at;
    pthread_cond_broadcast(&callback_ready);
    pthread_mutex_unlock(&callback_mutex);
    if (stop_here) {
        android_timer_stop();
        pthread_mutex_lock(&callback_mutex);
        self_stop_returned = 1;
        pthread_cond_broadcast(&callback_ready);
        pthread_mutex_unlock(&callback_mutex);
    }
}

static void
wait_for_callbacks(int target)
{
    struct timespec deadline;
    int result = 0;
    clock_gettime(CLOCK_REALTIME, &deadline);
    deadline.tv_sec += 2;
    pthread_mutex_lock(&callback_mutex);
    while (callback_count < target && result == 0) {
        result = pthread_cond_timedwait(&callback_ready, &callback_mutex,
                                        &deadline);
    }
    assert(callback_count >= target);
    pthread_mutex_unlock(&callback_mutex);
}

static int
count_callbacks(void)
{
    int count;
    pthread_mutex_lock(&callback_mutex);
    count = callback_count;
    pthread_mutex_unlock(&callback_mutex);
    return count;
}

int
main(void)
{
    struct timespec quiet = {0, 200000000};
    int count;

    android_timer_set_app(&app_value);
    android_timer_start();
    android_timer_activate();
    wait_for_callbacks(2);
    android_timer_deactivate();
    pthread_mutex_lock(android_timer_get_mutex());
    pthread_mutex_unlock(android_timer_get_mutex());
    count = count_callbacks();
    nanosleep(&quiet, NULL);
    assert(count_callbacks() == count);
    android_timer_stop();

    android_timer_set_app(&app_value);
    android_timer_start();
    android_timer_activate();
    wait_for_callbacks(count + 1);
    android_timer_stop();
    android_timer_set_app(NULL);
    android_timer_stop();

    pthread_mutex_lock(&callback_mutex);
    self_stop_at = callback_count + 1;
    pthread_mutex_unlock(&callback_mutex);
    android_timer_set_app(&app_value);
    android_timer_start();
    android_timer_activate();
    wait_for_callbacks(self_stop_at);
    pthread_mutex_lock(&callback_mutex);
    while (!self_stop_returned) {
        pthread_cond_wait(&callback_ready, &callback_mutex);
    }
    pthread_mutex_unlock(&callback_mutex);
    android_timer_set_app(&app_value);
    android_timer_start();
    android_timer_activate();
    wait_for_callbacks(self_stop_at + 1);
    android_timer_stop();
    return 0;
}
