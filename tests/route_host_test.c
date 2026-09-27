#define _POSIX_C_SOURCE 200809L
#include "app/route_host.h"
#include "app/route_log.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

static char last_route[2049];
static int pushes;
static int replacements;
static int log_count;
static char log_text[128];

void app_log_info(const char *format, ...)
{
    va_list args;
    log_count++;
    va_start(args, format);
    vsnprintf(log_text, sizeof(log_text), format, args);
    va_end(args);
}

uint8_t *app_getenv_bytes(uint8_t *name)
{
    return (uint8_t *)getenv((const char *)name);
}

void app_log_line(uint8_t *line)
{
    app_log_info("%s", (const char *)line);
}

String app_text_from_cstring(uint8_t *text, int32_t capacity)
{
    int32_t length = 0;
    while (length < capacity && text[length] != 0)
        length++;
    return StringView((const char *)text, (size_t)length);
}

uint8_t *GetRoutePath(void) { return (uint8_t *)"/app"; }
uint8_t *GetRouteHash(void) { return (uint8_t *)"#/start"; }
int GetRouteVersion(void) { return 7; }

void PushRoute(uint8_t *path)
{
    snprintf(last_route, sizeof(last_route), "%s", path);
    pushes++;
}

void ReplaceRoute(uint8_t *path)
{
    snprintf(last_route, sizeof(last_route), "%s", path);
    replacements++;
}

int main(void)
{
    const char url[] = "/app#/settings";
    Slice bytes = {(void *)url, (int32_t)(sizeof(url) - 1)};
    String text = app_route_text(NULL);
    if(text.length != 0 || app_route_hash().length != 7 ||
       app_route_base().length != 4 || app_route_version() != 7)
        return 1;
    if(!app_route_write(bytes, bytes.length, true) || pushes != 1 ||
       replacements != 0 || strcmp(last_route, url))
        return 2;
    if(!app_route_write(bytes, bytes.length, false) || replacements != 1 ||
       strcmp(last_route, url))
        return 3;
    if(app_route_write(bytes, bytes.length + 1, true) ||
       app_route_write((Slice){NULL, 0}, 0, true) ||
       pushes != 1 || replacements != 1)
        return 4;
    if(unsetenv("INBE_DEBUG_ROUTE") != 0)
        return 5;
    app_route_log(0, 7, 1, 2);
    if(log_count != 0 || setenv("INBE_DEBUG_ROUTE", "", 1) != 0)
        return 6;
    app_route_log(0, 7, 1, 2);
    if(log_count != 0 || setenv("INBE_DEBUG_ROUTE", "1", 1) != 0)
        return 7;
    app_route_log(0, 7, 1, 2);
    if(log_count != 1 ||
       strcmp(log_text, "ROUTE switch frame=7 screen=1->2"))
        return 8;
    app_route_log(1, 8, 2, 3);
    if(log_count != 2 ||
       strcmp(log_text, "ROUTE request frame=8 screen=2->3"))
        return 9;
    unsetenv("INBE_DEBUG_ROUTE");
    puts("route host test passed");
    return 0;
}
