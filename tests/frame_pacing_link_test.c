#include <assert.h>
#include <stdbool.h>
#include <stdint.h>

#include "app/app_frame_pacing.h"
#include "smooth_frames.h"

static int android_platform;
static bool guide_animating;

int32_t
AndroidPlatform(void)
{
    return android_platform;
}

bool
LumiGuideAnimating(void)
{
    return guide_animating;
}

int
main(void)
{
    static InnerBreeze app;
    FrameActivitySample sample = {0};
    FramePacingDecision decision;

    FramePacingReset();
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);

    for (int frame = 0; frame < 12; frame++) {
        decision = app_update_frame_pacing(&app, sample);
        assert(!decision.apply_target && decision.state.target_fps == 60);
    }
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 30);

    sample.keyboard_active = true;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);

    sample.keyboard_active = false;
    android_platform = 1;
    for (int frame = 0; frame < 12; frame++) {
        decision = app_update_frame_pacing(&app, sample);
        assert(!decision.apply_target && decision.state.target_fps == 60);
    }
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 15);

    /* A route fade keeps the active rate after the tap is released. */
    app.ui.route_transition_active = true;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);
    app.ui.route_transition_active = false;
    for (int frame = 0; frame < 12; frame++) {
        decision = app_update_frame_pacing(&app, sample);
    }
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.state.target_fps == 15);

    app.breathing.screen = ScreenMeditation;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);

    /* A practice running in its small window over another app keeps the
       active rate. */
    app.breathing.screen = ScreenHabits;
    for (int frame = 0; frame < 14; frame++) {
        decision = app_update_frame_pacing(&app, sample);
    }
    assert(decision.state.target_fps == 15);
    app.session_window.screen = ScreenSession;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);

    /* Lumi flying, typing or speaking in a guide keeps the active rate. */
    app.session_window.screen = ScreenHabits;
    for (int frame = 0; frame < 14; frame++) {
        decision = app_update_frame_pacing(&app, sample);
    }
    assert(decision.state.target_fps == 15);
    guide_animating = true;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);

    /* An app package asking for smooth frames keeps the active rate until
       they are spent, then the phone settles back to its idle rate. */
    guide_animating = false;
    for (int frame = 0; frame < 14; frame++) {
        decision = app_update_frame_pacing(&app, sample);
    }
    assert(decision.state.target_fps == 15);
    AppRequestSmoothFrames(20);
    for (int frame = 0; frame < 20; frame++) {
        decision = app_update_frame_pacing(&app, sample);
        assert(decision.state.target_fps == 60);
    }
    for (int frame = 0; frame < 14; frame++) {
        decision = app_update_frame_pacing(&app, sample);
    }
    assert(decision.state.target_fps == 15);
    return 0;
}
