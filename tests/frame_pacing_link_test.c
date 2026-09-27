#include <assert.h>
#include <stdbool.h>
#include <stdint.h>

#include "app/app_frame_pacing.h"

static int android_platform;

int32_t
AndroidPlatform(void)
{
    return android_platform;
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

    app.breathing.screen = ScreenMeditation;
    decision = app_update_frame_pacing(&app, sample);
    assert(decision.apply_target && decision.state.target_fps == 60);
    return 0;
}
