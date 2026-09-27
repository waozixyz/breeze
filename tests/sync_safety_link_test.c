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

    app.modal.active = 1;
    assert(app_background_sync_safe(&app) == 0);
    app.sync_alias_focused = 1;
    assert(app_background_sync_safe(&app) == 0);
    return 0;
}
