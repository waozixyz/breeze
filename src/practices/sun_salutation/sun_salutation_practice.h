#ifndef APP_SUN_SALUTATION_PRACTICE_H
#define APP_SUN_SALUTATION_PRACTICE_H

#include "app_fwd.h"

#define SUN_SALUTATION_STEP_COUNT 12
#define SUN_SALUTATION_POSE_COUNT SUN_SALUTATION_STEP_COUNT
#define SUN_SALUTATION_FIGURE_COUNT 2
#define SUN_SALUTATION_ACTIVE_FIGURE_COUNT SUN_SALUTATION_FIGURE_COUNT
#define SUN_SALUTATION_FIGURE_MAN 0
#define SUN_SALUTATION_FIGURE_WOMAN 1
#define SUN_SALUTATION_POSE_SHEET_COLS 4
#define SUN_SALUTATION_POSE_FRAME_W 106
#define SUN_SALUTATION_POSE_FRAME_H 96
#define SUN_SALUTATION_TRANSITION_COUNT 2
#define SUN_SALUTATION_TRANSITION_FRAME_COUNT 8
#define SUN_SALUTATION_TRANSITION_SHEET_COLS 8
#define SUN_SALUTATION_SECONDS_MIN 3
#define SUN_SALUTATION_SECONDS_MAX 12
#define SUN_SALUTATION_DEFAULT_REPETITIONS 3
#define SUN_SALUTATION_DEFAULT_START_SECONDS 8
#define SUN_SALUTATION_DEFAULT_END_SECONDS 5

int sun_salutation_step_pose_index(int step);
void sun_salutation_practice_init(InnerBreeze*app);
const char *sun_salutation_pose_asset(int figure);
const char *sun_salutation_transition_asset(int figure, int transition);
void sun_salutation_practice_start(InnerBreeze*app);
void sun_manual_draw(InnerBreeze*app);
void sun_manual_close(InnerBreeze*app, int mark_seen);
void sun_salutation_config_screen_draw(InnerBreeze*app);
void sun_salutation_draw_screen(InnerBreeze*app, int center_x, int center_y);
void sun_salutation_request_exit(InnerBreeze*app);

#endif
