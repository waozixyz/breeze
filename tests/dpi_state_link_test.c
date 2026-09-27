#include "app/dpi_state.h"

#include <stdbool.h>
#include <math.h>

void SetDeviceDensity(float density);

static int platform;
static bool ready;
static Vector2 window_scale = {1.0f, 1.0f};

int32_t app_android_platform(void) { return platform == 1; }
int32_t app_web_platform(void) { return platform == 2; }
bool IsWindowReady(void) { return ready; }
Vector2 GetWindowScaleDPI(void) { return window_scale; }

static bool
near(float actual, float expected)
{
    return fabsf(actual - expected) < 0.01f;
}

int
main(void)
{
    InitDPI();
    SetDeviceDensity(0.0f);
    UpdateDPI(900, 720);
    if(!near(GetDPIScale(), 1.0f) || GetLayoutWidth() != 900 ||
       GetLayoutHeight() != 720)
        return 1;

    SetDeviceDensity(2.0f);
    UpdateDPI(900, 720);
    if(!near(GetDPIScale(), 2.0f) || GetLayoutWidth() != 450 ||
       GetLayoutHeight() != 360)
        return 2;

    platform = 1;
    UpdateDPI(360, 640);
    if(!near(GetDPIScale(), 2.0f) || GetLayoutWidth() != 180 ||
       GetLayoutHeight() != 320)
        return 3;

    SetDeviceDensity(0.0f);
    UpdateDPI(360, 640);
    if(!near(GetDPIScale(), 640.0f / 560.0f) ||
       GetLayoutWidth() != 315 || GetLayoutHeight() != 560)
        return 4;

    platform = 0;
    ready = true;
    window_scale = (Vector2){1.5f, 1.5f};
    UpdateDPI(900, 720);
    if(!near(GetDPIScale(), 1.5f) || GetLayoutWidth() != 600 ||
       GetLayoutHeight() != 480 || !near(GetRenderScale(), 1.5f))
        return 5;
    return 0;
}
