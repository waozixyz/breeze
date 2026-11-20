#include "app_chrome.h"
#include "practice_title_bar.h"
#include "chrome_test_backend.h"
#include "zir_string.h"

#include <assert.h>
#include <string.h>

void app_device_resize(int32_t width, int32_t height) {
    (void)width; (void)height; assert(0);
}

void app_mini_restore_selection(InnerBreeze *app) {
    (void)app; assert(0);
}

int
main(void)
{
    static InnerBreeze app = {0};
    int32_t count;
    bool found_icon = false;

    InstallChromePictures();
    app.ui.session = SessionOpen();
    assert(SessionValid(app.ui.session));
    app.ui.view_width = 400;
    AppMetricsConfigure(1.0f);
    assert(ImageWidth(StringView("icons/ui.webp", 13)) == 512);
    assert(ImageHeight(StringView("icons/ui.webp", 13)) == 512);
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
           StringEqual(command.asset_path, StringView("icons/ui.webp", 13))) {
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
           StringEqual(command.asset_path, StringView("icons/ui.webp", 13))) {
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
