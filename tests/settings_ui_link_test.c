#include "screens/settings/settings_ui.h"
#include "tree.h"
#include "tree_input.h"
#include "paint_queue.h"
#include "metrics.h"

#include <assert.h>

void RasterRoundedRectangle(Rectangle bounds, float radius, int32_t segments,
    Color color)
{
    (void)bounds;
    (void)radius;
    (void)segments;
    (void)color;
    assert(0);
}

void RasterRoundedRectangleOutline(Rectangle bounds, float radius,
    int32_t segments, float width, Color color)
{
    (void)bounds;
    (void)radius;
    (void)segments;
    (void)width;
    (void)color;
    assert(0);
}

void RasterText(String value, int32_t x, int32_t y, int32_t font,
    Color color)
{
    (void)value;
    (void)x;
    (void)y;
    (void)font;
    (void)color;
    assert(0);
}

void RasterTextClipped(String value, int32_t x, int32_t y, int32_t font,
    Color color, Rectangle clip)
{
    (void)value;
    (void)x;
    (void)y;
    (void)font;
    (void)color;
    (void)clip;
    assert(0);
}

int32_t MeasureGlyphWidth(String value, int32_t font, String typeface)
{
    (void)typeface;
    return (int32_t)value.length * font / 2;
}

int32_t MeasureGlyphLineHeight(int32_t font, String typeface)
{
    (void)typeface;
    return font;
}

int main(void)
{
    InnerBreeze app = {0};
    int32_t enabled = 0;
    int32_t y = 10;
    String label = StringView("Notifications", 13);

    app.ui.session = SessionOpen();
    assert(SessionValid(app.ui.session));
    AppMetricsConfigure(1.0f);
    assert(toggle_switch_width() == 50);
    assert(toggle_row_height(label, 300) >= 52);

    TreeStart(app.ui.session, 1, (Rectangle){0, 0, 400, 300});
    assert(!settings_ui_draw_toggle_row(&app, 10, 300, &y, label, &enabled));
    assert(enabled == 0);
    assert(draw_audio_meter(&app, 0.5f, 10, 120, 300,
        StringView("Output", 6)) == audio_meter_height());
    assert(PendingPaintCount(app.ui.session) > 0);
    assert(TreeFinish(app.ui.session));

    TreePointerUpdate(app.ui.session,
        (PointerFrame){270.0f, 35.0f, true, true, false});
    TreePointerUpdate(app.ui.session,
        (PointerFrame){270.0f, 35.0f, false, false, true});
    TreePointerUpdate(app.ui.session,
        (PointerFrame){390.0f, 290.0f, false, false, false});

    y = 10;
    TreeStart(app.ui.session, 1, (Rectangle){0, 0, 400, 300});
    assert(settings_ui_draw_toggle_row(&app, 10, 300, &y, label, &enabled));
    assert(enabled == 1);
    assert(TreeFinish(app.ui.session));
    assert(SessionClose(app.ui.session));
    return 0;
}
