#define _DEFAULT_SOURCE
#include "ziran_host.h"
#include <assert.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

static atomic_bool parser_blocked;
static atomic_bool parser_started;
static atomic_int bundle_opens;
static bool other_account;

/* Snapshot integration uses the real variadic logger's calling convention. */
void __wrap_TraceLog(int32_t level, const char *format, ...)
{
    (void)level;
    va_list arguments;
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    fputc('\n', stderr);
}

void IconsBlockParser(bool blocked)
{
    if (blocked) atomic_store(&parser_started, false);
    atomic_store(&parser_blocked, blocked);
}

bool IconsParserStarted(void)
{
    return atomic_load(&parser_started);
}

int32_t IconsBundleOpens(void)
{
    return atomic_load(&bundle_opens);
}

void IconsYield(void)
{
    usleep(1000);
}

double IconsNow(void)
{
    struct timespec now;
    assert(clock_gettime(CLOCK_MONOTONIC, &now) == 0);
    return (double)now.tv_sec + (double)now.tv_nsec / 1e9;
}

void IconsOtherAccount(bool enabled)
{
    other_account = enabled;
}

unsigned char *__real_storage_user_id_buffer(void);
unsigned char *__wrap_storage_user_id_buffer(void)
{
    return other_account ? (unsigned char *)"another-account" : __real_storage_user_id_buffer();
}

Bundle *__real_BundleOpenBytes(const unsigned char *bytes, size_t size);
Bundle *__wrap_BundleOpenBytes(const unsigned char *bytes, size_t size)
{
    atomic_fetch_add(&bundle_opens, 1);
    if (atomic_load(&parser_blocked)) {
        atomic_store(&parser_started, true);
        while (atomic_load(&parser_blocked)) usleep(1000);
    }
    return __real_BundleOpenBytes(bytes, size);
}
