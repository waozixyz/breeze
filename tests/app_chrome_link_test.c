#include "app/app_chrome.h"
#include "app/practice_title_bar.h"
#include "paint_queue.h"
#include "image_raster.h"
#include "session.h"
#include "tree.h"

#include <assert.h>
#include <string.h>

void RasterLine(Rectangle line, Color color) { (void)line; (void)color; assert(0); }
void RasterRoundedRectangle(Rectangle bounds, float radius, int32_t segments, Color color) {
    (void)bounds; (void)radius; (void)segments; (void)color; assert(0);
}
void RasterRoundedRectangleOutline(Rectangle bounds, float radius, int32_t segments,
    float width, Color color) {
    (void)bounds; (void)radius; (void)segments; (void)width; (void)color; assert(0);
}
void RasterText(String value, int32_t x, int32_t y, int32_t font, Color color) {
    (void)value; (void)x; (void)y; (void)font; (void)color; assert(0);
}
void RasterTextClipped(String value, int32_t x, int32_t y, int32_t font,
    Color color, Rectangle clip) {
    (void)value; (void)x; (void)y; (void)font; (void)color; (void)clip; assert(0);
}
void RasterImage(String path, uint32_t texture, Rectangle source,
    Rectangle destination, Rectangle clip, Vector2 origin, float rotation,
    float radius, Color tint) {
    (void)path; (void)texture; (void)source; (void)destination;
    (void)clip; (void)origin; (void)rotation; (void)radius; (void)tint;
    assert(0);
}

void app_device_resize(int32_t width, int32_t height) {
    (void)width; (void)height; assert(0);
}

void app_mini_restore_selection(InnerBreeze *app) {
    (void)app; assert(0);
}

int32_t
MeasureGlyphWidth(String value, int32_t font, String typeface)
{
    (void)typeface;
    return (int32_t)value.length * font / 2;
}

int32_t
MeasureGlyphLineHeight(int32_t font, String typeface)
{
    (void)typeface;
    return font;
}

int
main(void)
{
    InnerBreeze app = {0};
    int32_t count;
    bool found_icon = false;

    app.ui.session = SessionOpen();
    assert(SessionValid(app.ui.session));
    app.ui.view_width = 400;
    AppMetricsConfigure(1.0f);
    assert(ImageWidth(StringView("icons/ui.png", 12)) == 512);
    assert(ImageHeight(StringView("icons/ui.png", 12)) == 512);
    assert(app_toolbar_height() == 58);
    assert(app_content_top_reserved(&app) == GetTabBarHeight());
    app.breathing.screen = ScreenSettings;
    assert(app_content_top_reserved(&app) == 58);

    TreeStart(app.ui.session, 1, (Rectangle){0, 0, 400, 58});
    assert(app_draw_close_title_bar(&app, StringView("Habits", 6),
        StringView("Close", 5), 58) == 0);
    count = PendingPaintCount(app.ui.session);
    for(int32_t index = 0; index < count; index++) {
        PaintCommand command = PendingPaintAt(app.ui.session, index);
        if(command.kind == PaintKindImage &&
           StringEqual(command.asset_path, StringView("icons/ui.png", 12))) {
            assert(command.source.x == 448.0f);
            assert(command.source.y == 384.0f);
            assert(command.source.width == 64.0f);
            assert(command.source.height == 64.0f);
            found_icon = true;
        }
    }
    assert(found_icon);
    assert(TreeFinish(app.ui.session));

    found_icon = false;
    app.ui.view_height = 480;
    assert(PracticeTitleBarHeight() >= 76);
    TreeStart(app.ui.session, 2, (Rectangle){0, 0, 400, 480});
    assert(!PracticeTitleBar(&app, StringView("Meditation", 10),
        PracticeTitleBarHeight()));
    count = PendingPaintCount(app.ui.session);
    for(int32_t index = 0; index < count; index++) {
        PaintCommand command = PendingPaintAt(app.ui.session, index);
        if(command.kind == PaintKindImage &&
           StringEqual(command.asset_path, StringView("icons/ui.png", 12))) {
            assert(command.source.x == 448.0f);
            assert(command.source.y == 384.0f);
            found_icon = true;
        }
    }
    assert(found_icon);
    assert(TreeFinish(app.ui.session));
    assert(SessionClose(app.ui.session));
    return 0;
}
