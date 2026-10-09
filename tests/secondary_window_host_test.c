#include <SDL2/SDL.h>
#include "raylib.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void *app_secondary_window_open(const uint8_t *title, int x, int y,
    int width, int height, int flags, uint8_t red, uint8_t green,
    uint8_t blue, uint8_t alpha, float scale);
extern void app_secondary_window_close(void *handle);
extern bool app_secondary_window_begin(void *handle);
extern bool app_secondary_window_end(void *handle);
extern void app_secondary_window_pump(void);
extern bool app_secondary_window_clicked(void *handle);
extern bool app_secondary_window_dragged(void *handle);
extern bool app_secondary_window_keyboard_grab(void *handle, bool enabled);
extern void app_secondary_window_position(void *handle, int *x, int *y);
extern void app_secondary_window_size(void *handle, int *width, int *height);
extern bool app_secondary_window_take_close(void *handle);

static SDL_Window *
secondary_sdl_window(SDL_Window *main_window)
{
    for(Uint32 id = 1; id < 16; id++) {
        SDL_Window *found = SDL_GetWindowFromID(id);
        if(found != NULL && found != main_window)
            return found;
    }
    return NULL;
}

static Color
surface_color(SDL_Surface *surface, int x, int y)
{
    Color color = {0};
    SDL_LockSurface(surface);
    Uint32 pixel = *(Uint32 *)((uint8_t *)surface->pixels +
        y * surface->pitch + x * surface->format->BytesPerPixel);
    SDL_GetRGBA(pixel, surface->format,
        &color.r, &color.g, &color.b, &color.a);
    SDL_UnlockSurface(surface);
    return color;
}

static bool
is_private_display(void)
{
    const char *display = getenv("DISPLAY");
    const char *authority = getenv("XAUTHORITY");
    if(display == NULL || display[0] != ':' || authority == NULL ||
       strstr(authority, "xvfb-run.") == NULL)
        return false;
    char *end;
    long server = strtol(display + 1, &end, 10);
    return server >= 200 && (*end == '\0' || *end == '.');
}

int
main(void)
{
    if(!is_private_display()) {
        fputs("secondary window test requires private Xvfb display 200+\n",
            stderr);
        return 1;
    }
    SetTraceLogLevel(LOG_WARNING);
    InitWindow(100, 100, "private-xvfb-main");
    if(!IsWindowReady())
        return 2;
    SDL_Window *main_window = SDL_GL_GetCurrentWindow();
    SDL_GLContext main_context = SDL_GL_GetCurrentContext();
    if(main_window == NULL || main_context == NULL)
        return 3;

    void *handle = app_secondary_window_open(
        (const uint8_t *)"owned-secondary", 40, 40, 40, 40, 1,
        0, 0, 0, 255, 1.0f);
    if(handle == NULL)
        return 4;
    if(SDL_GL_GetCurrentWindow() != main_window ||
       SDL_GL_GetCurrentContext() != main_context)
        return 5;
    if(!app_secondary_window_begin(handle))
        return 6;
    DrawRectangle(0, 0, 40, 20, RED);
    DrawRectangle(0, 20, 40, 20, BLUE);
    if(!app_secondary_window_end(handle))
        return 7;
    if(SDL_GL_GetCurrentWindow() != main_window ||
       SDL_GL_GetCurrentContext() != main_context)
        return 8;

    SDL_Window *secondary = secondary_sdl_window(main_window);
    if(secondary == NULL)
        return 9;
    SDL_Surface *surface = SDL_GetWindowSurface(secondary);
    if(surface == NULL)
        return 10;
    Color top = surface_color(surface, 20, 5);
    Color bottom = surface_color(surface, 20, 35);
    if(top.r < 180 || top.b > 80 || bottom.b < 180 || bottom.r > 80) {
        fprintf(stderr, "unexpected rendered colors: top=%u,%u,%u bottom=%u,%u,%u\n",
            top.r, top.g, top.b, bottom.r, bottom.g, bottom.b);
        return 11;
    }

    SDL_Window *foreign = SDL_CreateWindow("unregistered", 100, 100,
        20, 20, SDL_WINDOW_HIDDEN);
    if(foreign == NULL)
        return 12;
    SDL_Event event = {0};
    event.type = SDL_MOUSEBUTTONDOWN;
    event.button.windowID = SDL_GetWindowID(foreign);
    event.button.button = SDL_BUTTON_LEFT;
    SDL_PushEvent(&event);
    event.type = SDL_MOUSEBUTTONUP;
    SDL_PushEvent(&event);
    app_secondary_window_pump();
    if(app_secondary_window_clicked(handle))
        return 13;
    SDL_DestroyWindow(foreign);

    event = (SDL_Event){0};
    event.type = SDL_MOUSEBUTTONDOWN;
    event.button.windowID = SDL_GetWindowID(secondary);
    event.button.button = SDL_BUTTON_LEFT;
    event.button.x = 10;
    event.button.y = 10;
    SDL_PushEvent(&event);
    event.type = SDL_MOUSEBUTTONUP;
    SDL_PushEvent(&event);
    app_secondary_window_pump();
    if(!app_secondary_window_clicked(handle) ||
       app_secondary_window_clicked(handle))
        return 14;

    int before_x = 0;
    int before_y = 0;
    app_secondary_window_position(handle, &before_x, &before_y);
    event.type = SDL_MOUSEBUTTONDOWN;
    SDL_PushEvent(&event);
    event = (SDL_Event){0};
    event.type = SDL_MOUSEMOTION;
    event.motion.windowID = SDL_GetWindowID(secondary);
    event.motion.state = SDL_BUTTON_LMASK;
    event.motion.x = 20;
    event.motion.y = 10;
    SDL_PushEvent(&event);
    event = (SDL_Event){0};
    event.type = SDL_MOUSEBUTTONUP;
    event.button.windowID = SDL_GetWindowID(secondary);
    event.button.button = SDL_BUTTON_LEFT;
    event.button.x = 20;
    event.button.y = 10;
    SDL_PushEvent(&event);
    app_secondary_window_pump();
    int after_x = 0;
    int after_y = 0;
    app_secondary_window_position(handle, &after_x, &after_y);
    if(!app_secondary_window_dragged(handle) ||
       after_x != before_x + 10 || after_y != before_y ||
       app_secondary_window_clicked(handle))
        return 15;

    if(!app_secondary_window_keyboard_grab(handle, false))
        return 16;
    app_secondary_window_close(handle);
    app_secondary_window_pump();
    if(app_secondary_window_clicked(handle))
        return 17;

    // A detached resizable window must not resize, click or close the main
    // raylib window. Three owned windows can coexist with the break displays.
    handle = app_secondary_window_open((const uint8_t *)"detached-practice",
        20, 20, 200, 248, 2 | 32, 0, 0, 0, 255, 1.0f);
    if(handle == NULL)
        return 18;
    secondary = secondary_sdl_window(main_window);
    void *second = app_secondary_window_open((const uint8_t *)"break",
        0, 0, 40, 40, 1, 0, 0, 0, 255, 1.0f);
    void *third = app_secondary_window_open((const uint8_t *)"hud",
        0, 0, 40, 40, 1, 0, 0, 0, 255, 1.0f);
    if(second == NULL || third == NULL)
        return 19;
    SDL_SetWindowSize(secondary, 240, 300);
    SDL_PumpEvents();
    event = (SDL_Event){0};
    event.type = SDL_WINDOWEVENT;
    event.window.windowID = SDL_GetWindowID(secondary);
    event.window.event = SDL_WINDOWEVENT_SIZE_CHANGED;
    event.window.data1 = 240;
    event.window.data2 = 300;
    SDL_PushEvent(&event);
    event.window.event = SDL_WINDOWEVENT_CLOSE;
    SDL_PushEvent(&event);
    event = (SDL_Event){0};
    event.type = SDL_MOUSEBUTTONUP;
    event.button.windowID = SDL_GetWindowID(secondary);
    event.button.button = SDL_BUTTON_LEFT;
    SDL_PushEvent(&event);
    BeginDrawing();
    EndDrawing();
    if(GetScreenWidth() != 100 || GetScreenHeight() != 100 ||
       WindowShouldClose() || IsMouseButtonReleased(MOUSE_BUTTON_LEFT))
        return 20;
    if(!app_secondary_window_take_close(handle) ||
       app_secondary_window_take_close(handle) || !app_secondary_window_clicked(handle))
        return 21;
    if(!app_secondary_window_begin(handle))
        return 22;
    int width = 0, height = 0;
    app_secondary_window_size(handle, &width, &height);
    if(width != 240 || height != 300 || !app_secondary_window_end(handle))
        return 23;
    app_secondary_window_close(third);
    app_secondary_window_close(second);
    app_secondary_window_close(handle);
    BeginDrawing();
    EndDrawing();
    if(IsWindowHidden() || IsWindowMinimized() || WindowShouldClose())
        return 24;
    CloseWindow();
    return 0;
}
