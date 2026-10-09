#include "app/sync_safety.h"

#include <assert.h>

static InnerBreeze app;

int
main(void)
{
    assert(app_background_sync_safe(NULL) == 0);
    app.breathing.screen = ScreenHabits;
    assert(app_background_sync_safe(&app) == 1);
    assert(sync_safety_SyncUiUpdateSafe(&app, 2.5, 1.0, false));
    app.breathing.screen = ScreenLumi;
    app.ui.text_input_active = true;
    assert(!sync_safety_SyncUiUpdateSafe(&app, 20.0, 1.0, false));
    app.ui.text_input_active = false;
    assert(sync_safety_SyncUiUpdateSafe(&app, 20.0, 1.0, false));

    /* This native build runs sync on a worker thread, so a running
       practice does not hold it back. */
    app.breathing.screen = ScreenSession;
    assert(app_background_sync_safe(&app) == 1);
    app.breathing.screen = ScreenLumi;

    /* A visible practice, also in its small window, holds frame-thread
       work; in the background nothing is drawn. */
    assert(!sync_safety_app_practice_holds_frame_work(&app));
    app.breathing.screen = ScreenSession;
    assert(sync_safety_app_practice_holds_frame_work(&app));
    app.breathing.screen = ScreenHabits;
    app.session_window.screen = ScreenMeditation;
    assert(sync_safety_app_practice_holds_frame_work(&app));
    app.backgrounded = 1;
    assert(!sync_safety_app_practice_holds_frame_work(&app));
    app.backgrounded = 0;
    app.session_window.screen = ScreenStart;
    app.breathing.screen = ScreenLumi;

    app.modal.active = 1;
    assert(app_background_sync_safe(&app) == 0);
    app.sync_alias_focused = 1;
    assert(app_background_sync_safe(&app) == 0);
    return 0;
}
