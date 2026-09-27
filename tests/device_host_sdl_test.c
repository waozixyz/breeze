#include "device_host.h"

#include <SDL2/SDL.h>
#include <assert.h>

int
main(void)
{
    assert(SDL_Init(SDL_INIT_VIDEO) == 0);
    SDL_Window *owned = SDL_CreateWindow("owned", 0, 0, 300, 200, SDL_WINDOW_HIDDEN);
    SDL_Window *other = SDL_CreateWindow("other", 0, 0, 400, 250, SDL_WINDOW_HIDDEN);
    assert(owned != NULL && other != NULL);

    app_device_attach_window(owned);
    assert(app_device_width() == 300 && app_device_height() == 200);
    app_device_resize(500, 350);
    assert(app_device_width() == 500 && app_device_height() == 350);
    int width = 0;
    int height = 0;
    SDL_GetWindowSize(other, &width, &height);
    assert(width == 400 && height == 250);

    app_device_attach_window(NULL);
    app_device_resize(800, 600);
    app_device_fullscreen(1);
    SDL_GetWindowSize(owned, &width, &height);
    assert(width == 500 && height == 350);
    assert(app_device_width() == 0 && app_device_height() == 0);

    SDL_DestroyWindow(other);
    SDL_DestroyWindow(owned);
    SDL_Quit();
    return 0;
}
