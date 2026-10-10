#include "platform/android/android_timer_host.h"

#include <assert.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <time.h>

static pthread_mutex_t callback_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t callback_ready = PTHREAD_COND_INITIALIZER;
static int callback_count;
static int sync_count;
static int self_stop_at;
static int self_stop_returned;
static int app_value;

int32_t TimerElapsedMillis(int64_t previous_nanoseconds,
                           int64_t now_nanoseconds);

void
app_activity_background_sync(void *app)
{
    assert(app == &app_value);
    pthread_mutex_lock(&callback_mutex);
    sync_count++;
    assert(sync_count <= callback_count);
    pthread_mutex_unlock(&callback_mutex);
}

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

/* Another thread's attempt to exchange sync and activity requests. It ends
 * its own exchange, since only the holding thread may release the mutex. */
static void *
try_network_pump(void *unused)
{
    bool began;
    (void)unused;
    began = android_network_pump_begin();
    if (began) {
        android_network_pump_end();
    }
    return began ? &app_value : NULL;
}

static bool
network_pump_from_other_thread(void)
{
    pthread_t thread;
    void *result = NULL;
    assert(pthread_create(&thread, NULL, try_network_pump, NULL) == 0);
    assert(pthread_join(thread, &result) == 0);
    return result != NULL;
}

int
main(void)
{
    struct timespec quiet = {0, 200000000};
    int count;

    /* The frame and the background timer never exchange at the same time. */
    assert(android_network_pump_begin());
    assert(!network_pump_from_other_thread());
    android_network_pump_end();
    assert(network_pump_from_other_thread());

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
    assert(sync_count == callback_count);
    return 0;
}
