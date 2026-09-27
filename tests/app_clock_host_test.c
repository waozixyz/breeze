#define _POSIX_C_SOURCE 200809L
#include "date_time.h"

#include <stdio.h>
#include <time.h>

static int
same_civil_time(LocalDateTime got, const struct tm *expected)
{
    return got.year == expected->tm_year + 1900 &&
           got.month == expected->tm_mon + 1 &&
           got.day == expected->tm_mday &&
           got.day_of_year == expected->tm_yday &&
           got.hour == expected->tm_hour &&
           got.minute == expected->tm_min &&
           got.second == expected->tm_sec;
}

int
main(void)
{
    time_t before = time(NULL);
    LocalDateTime got = LocalNow();
    int64_t unix_now = UnixNow();
    time_t after = time(NULL);
    struct tm first;
    struct tm last;

    if(unix_now < (int64_t)before || unix_now > (int64_t)after)
        return 4;

    if(!got.valid || got.year < 1970 || got.month < 1 || got.month > 12 ||
       got.day < 1 || got.day > 31 || got.day_of_year < 0 ||
       got.day_of_year > 365 || got.hour < 0 || got.hour > 23 ||
       got.minute < 0 || got.minute > 59 || got.second < 0 ||
       got.second > 60)
        return 1;
#if defined(_WIN32)
    if(localtime_s(&first, &before) != 0 ||
       localtime_s(&last, &after) != 0)
        return 2;
#else
    if(localtime_r(&before, &first) == NULL ||
       localtime_r(&after, &last) == NULL)
        return 2;
#endif
    if(!same_civil_time(got, &first) && !same_civil_time(got, &last)) {
        fputs("local clock host returned a different civil time\n", stderr);
        return 3;
    }
    return 0;
}
