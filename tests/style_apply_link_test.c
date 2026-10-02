#define _POSIX_C_SOURCE 200809L
#include "style_apply_link_behavior.h"

#include <assert.h>
#include <pthread.h>

static void *
startup(void *argument)
{
    (void)argument;
    assert(StartupStyleCheck() == 42);
    return NULL;
}

int
main(void)
{
    pthread_attr_t attributes;
    pthread_t thread;

    /* Android native threads have much smaller stacks than the host main
     * thread. Exercise the entire startup parser chain within that budget. */
    assert(pthread_attr_init(&attributes) == 0);
    assert(pthread_attr_setstacksize(&attributes, 1024 * 1024) == 0);
    assert(pthread_create(&thread, &attributes, startup, NULL) == 0);
    assert(pthread_join(thread, NULL) == 0);
    assert(pthread_attr_destroy(&attributes) == 0);
    assert(Answer() == 42);
    return 0;
}
