#define _POSIX_C_SOURCE 200809L
#include "app/app_profile.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static double clock_now;
static int log_count;
static char log_text[256];

double app_monotonic_seconds(void) { return clock_now; }

uint8_t *app_getenv_bytes(uint8_t *name)
{
    return (uint8_t *)getenv((const char *)name);
}

void app_log_info(const char *format, ...)
{
    va_list args;
    log_count++;
    va_start(args, format);
    vsnprintf(log_text, sizeof(log_text), format, args);
    va_end(args);
}

void app_log_line(uint8_t *line)
{
    app_log_info("%s", (const char *)line);
}

int main(int argc, char **argv)
{
    if(argc > 1 && strcmp(argv[1], "disabled") == 0) {
        if(setenv("APP_PROFILE", "0", 1) != 0)
            return 8;
        clock_now = 10.0;
        if(app_profile_now() != 0.0)
            return 9;
        app_profile_record_update(10.0);
        app_profile_frame_end(10.0);
        return log_count == 0 ? 0 : 10;
    }
    if(unsetenv("APP_PROFILE") != 0 || app_profile_env_enabled())
        return 1;
    if(setenv("APP_PROFILE", "0", 1) != 0 || app_profile_env_enabled())
        return 2;
    if(setenv("APP_PROFILE", "1", 1) != 0 || !app_profile_env_enabled())
        return 3;

    clock_now = 10.0;
    if(app_profile_now() != clock_now)
        return 4;
    clock_now = 10.01;
    app_profile_record_update(10.0);
    app_profile_record_habits(10.0);
    app_profile_record_sync(10.0);
    for(int i = 0; i < 119; i++)
        app_profile_frame_end(10.0);
    if(log_count != 0)
        return 5;
    app_profile_frame_end(10.0);
    if(log_count != 1 ||
       strcmp(log_text,
              "PROFILE: frame avg=10.00 max=10.00 update avg=0.08 max=10.00 habits avg=0.08 max=10.00 sync avg=0.08 max=10.00 fps=12000.00"))
        return 6;
    app_profile_frame_end(10.0);
    if(log_count != 1)
        return 7;
    unsetenv("APP_PROFILE");
    puts("profile host test passed");
    return 0;
}
