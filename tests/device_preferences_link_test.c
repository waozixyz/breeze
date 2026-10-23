#include "device_preferences_link_behavior.h"

#include <assert.h>

static int platform;
static int system_dark;
static int width;
static int height;
static int last_width;
static int last_height;
static int last_orientation;

void fixture_platform(int value) { platform = value; }
void fixture_dark(int value) { system_dark = value; }
void fixture_size(int w, int h) { width = w; height = h; }
int fixture_last_width(void) { return last_width; }
int fixture_last_height(void) { return last_height; }
int fixture_last_orientation(void) { return last_orientation; }

int app_desktop_platform(void) { return platform == 0; }
int app_web_platform(void) { return platform == 1; }
int app_android_platform(void) { return platform == 2; }
int app_windows_platform(void) { return 0; }
int app_web_extension_available(void) { return 0; }

int app_device_system_dark(void) { return system_dark; }
int app_device_orientation(void) { return 1; }
void app_device_set_orientation(int mode) { last_orientation = mode; }
int app_device_width(void) { return width; }
int app_device_height(void) { return height; }
void app_device_resize(int w, int h) { last_width = w; last_height = h; }
void app_device_fullscreen(int enabled) { (void)enabled; }
void app_device_web_orientation(int mode) { last_orientation = mode; }

int DeviceSystemDark(void)
{
    return app_device_system_dark();
}

int DeviceOrientation(void)
{
    return app_device_orientation();
}

void DeviceSetOrientation(int mode)
{
    app_device_set_orientation(mode);
}

int DeviceWidth(void)
{
    return app_device_width();
}

int DeviceHeight(void)
{
    return app_device_height();
}

void DeviceResize(int w, int h)
{
    app_device_resize(w, h);
}

void DeviceFullscreen(int enabled)
{
    app_device_fullscreen(enabled);
}

void DeviceWebOrientation(int mode)
{
    app_device_web_orientation(mode);
}

int main(void)
{
    assert(Answer() == 42);
    return 0;
}
