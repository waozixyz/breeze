#ifndef APP_WHM_SESSION_H
#define APP_WHM_SESSION_H

#include "app/app.h"

void session_reset_round_breathe(BreathSession *breathing);
void session_update_circle_bounds_for_view(BreathSession *breathing, int top_reserve, int bottom_reserve);
void session_start(InnerBreeze*app);
int session_ensure_results_saved(InnerBreeze*app);
void session_discard_saved_results(InnerBreeze*app);
int session_has_completed_rounds(InnerBreeze*app);
void session_draw_inbe(InnerBreeze*app, int center_x, int center_y);
void draw_session_progress_circle(InnerBreeze*app, int center_x, int center_y, float radius);
int session_draw_start_preview(InnerBreeze*app, int center_x, int center_y);
void session_update_screen(InnerBreeze*app, int center_x, int center_y, int *hover);
void session_draw_results_screen(InnerBreeze*app, int center_x, int center_y, int *hover);
void update_session_sounds(InnerBreeze*app);
void session_background_start(InnerBreeze*app);
void session_advance_elapsed(InnerBreeze*app, int elapsed_ms);
void update_preview_bounds(BreathSession *breathing, int content_w, int max_h);
void draw_breath_preview(BreathSession *breathing, int center_x, int center_y, float fraction);

#endif
