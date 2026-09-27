#include "breaks/break_rules.h"

#include <stdio.h>
#include <string.h>

/*
 * Workrave-style break engine test.
 *
 * Drives the checked Ziran BreakTick() value function tick by tick and asserts
 * the Workrave semantics: activity-based timers, natural breaks, the prompt
 * escalation loop, skip/postpone, micro->rest promotion, the daily limit,
 * operation modes, and reading mode. Pure engine: no raylib.
 */

static int failures = 0;

static void
expect(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL %s\n", message);
        failures++;
    }
}

/* Keep the existing scenario driver while it moves to value-based Ziran. */
static void break_engine_init(BreakEngine *e) { *e = BreakInit(); }
static void break_engine_tick(BreakEngine *e, int active)
{
    *e = BreakTick(*e, active);
}
static void break_engine_skip(BreakEngine *e, int t) { *e = BreakSkip(*e, t); }
static void break_engine_postpone(BreakEngine *e, int t)
{
    *e = BreakPostpone(*e, t);
}
static void break_engine_force_break(BreakEngine *e, int t)
{
    *e = BreakForce(*e, t);
}
static void break_engine_set_mode(BreakEngine *e, int mode, int duration_s)
{
    *e = BreakSetMode(*e, mode, duration_s);
}
static int break_engine_set_day(BreakEngine *e, int day_key)
{
    BreakDayChange result = BreakSetDay(*e, day_key);
    *e = result.engine;
    return result.changed;
}
static int break_engine_take_event(BreakEngine *e, int *break_out)
{
    BreakEventTake result = BreakTakeEvent(*e);
    *e = result.engine;
    if (break_out != NULL) *break_out = result.break_type;
    return result.event;
}
static int break_engine_active_break(const BreakEngine *e)
{
    return BreakActive(*e);
}
static int break_timer_next_due_s(const BreakEngine *e, int t)
{
    return BreakNextDueSeconds(*e, t);
}
static int break_engine_note_idle(BreakEngine *e, int idle_s)
{
    BreakIdleSample result = BreakNoteIdle(*e, idle_s);
    *e = result.engine;
    return result.took;
}

static void break_format_duration(char *dst, size_t size, int seconds)
{
    if (dst == NULL || size == 0) return;
    BreakDurationText text = BreakFormatDuration(seconds);
    snprintf(dst, size, "%s", text.bytes);
}

/* Advance one full second and return the event raised during it. */
static int
step_second(BreakEngine *e, int active, int *break_out)
{
    int i;
    for (i = 0; i < 60; i++) {
        break_engine_tick(e, active);
    }
    return break_engine_take_event(e, break_out);
}

static void
run_seconds(BreakEngine *e, int seconds, int active)
{
    int i, brk;
    for (i = 0; i < seconds; i++) {
        step_second(e, active, &brk);
    }
}

static void
test_defaults_match_workrave(void)
{
    BreakEngine e;
    break_engine_init(&e);

    expect(e.timers[BREAK_MICRO].limit_s == 180 &&
           e.timers[BREAK_MICRO].duration_s == 30 &&
           e.timers[BREAK_MICRO].postpone_s == 150,
           "micro defaults: 3 min / 30 s / 150 s");
    expect(e.timers[BREAK_REST].limit_s == 2700 &&
           e.timers[BREAK_REST].duration_s == 600 &&
           e.timers[BREAK_REST].postpone_s == 180,
           "rest defaults: 45 min / 10 min / 180 s");
    expect(e.timers[BREAK_DAILY].limit_s == 14400 &&
           e.timers[BREAK_DAILY].duration_s == 0 &&
           e.timers[BREAK_DAILY].postpone_s == 1200,
           "daily defaults: 4 h / no duration / 1200 s");
    expect(e.timers[BREAK_MICRO].max_prompts == 0 &&
           e.timers[BREAK_REST].max_prompts == 3 &&
           e.timers[BREAK_DAILY].max_prompts == 3,
           "micro opens directly; rest/daily max prompts default to 3");
    expect(e.mode == BreakModeNormal, "mode defaults to normal");
    expect(break_timer_next_due_s(&e, BREAK_MICRO) == 180,
           "fresh micro timer due in 180 s");
}

static void
test_active_time_prompts_at_limit(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 60;
    e.timers[BREAK_MICRO].max_prompts = 3;

    run_seconds(&e, 59, 1);
    expect(e.timers[BREAK_MICRO].state == BreakStateRunning &&
           e.timers[BREAK_MICRO].active_s == 59,
           "no prompt before the limit");

    ev = step_second(&e, 1, &brk);
    expect(ev == BreakEventPrompt && brk == BREAK_MICRO,
           "reaching the limit raises a prompt");
    expect(e.timers[BREAK_MICRO].state == BreakStatePrompting,
           "timer enters prompting");
    expect(e.stats[BREAK_MICRO].prompts == 1, "prompt counted once");
}

static void
test_input_resets_idle_and_natural_take(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;

    run_seconds(&e, 170, 1);
    expect(e.timers[BREAK_MICRO].active_s == 170, "active time accrues");

    run_seconds(&e, 29, 0);
    expect(e.timers[BREAK_MICRO].idle_s == 29 &&
           e.timers[BREAK_MICRO].state == BreakStateRunning,
           "idle below duration does not take the break");

    run_seconds(&e, 1, 1);
    expect(e.timers[BREAK_MICRO].idle_s == 0,
           "any input resets the idle counter");

    run_seconds(&e, 29, 0);
    ev = step_second(&e, 0, &brk);
    expect(ev == BreakEventNatural && brk == BREAK_MICRO,
           "idle for the duration takes the break naturally");
    expect(e.stats[BREAK_MICRO].natural == 1, "natural break counted");
    expect(e.timers[BREAK_MICRO].active_s == 0 &&
           e.timers[BREAK_MICRO].state == BreakStateRunning,
           "natural take resets the timer");
}

static void
test_ignored_prompts_escalate_to_break(void)
{
    BreakEngine e;
    int brk = -1, ev, s;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].max_prompts = 3;

    ev = 0;
    for (s = 0; s < 240; s++) {
        ev = step_second(&e, 1, &brk);
    }
    expect(ev == BreakEventStart && brk == BREAK_MICRO,
           "three ignored prompts force the break");
    expect(e.timers[BREAK_MICRO].state == BreakStateBreaking,
           "timer enters breaking after max prompts");
    expect(e.stats[BREAK_MICRO].prompts == 1 &&
           e.stats[BREAK_MICRO].repeated_prompts == 2,
           "one prompt plus two repeats before forcing");
    expect(e.stats[BREAK_MICRO].overdue_s >= 60,
           "ignored time counts as overdue");
}

static void
test_unignorable_break_forces_immediately(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].max_prompts = 0;

    run_seconds(&e, 179, 1);
    ev = step_second(&e, 1, &brk);
    expect(ev == BreakEventStart && e.timers[BREAK_MICRO].state == BreakStateBreaking,
           "max_prompts 0 skips prompting entirely");
}

static void
test_skip_and_postpone(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10;
    e.timers[BREAK_MICRO].max_prompts = 0;

    run_seconds(&e, 10, 1);
    expect(e.timers[BREAK_MICRO].state == BreakStateBreaking, "break started");

    break_engine_skip(&e, BREAK_MICRO);
    ev = break_engine_take_event(&e, &brk);
    expect(ev == BreakEventSkipped &&
           e.timers[BREAK_MICRO].state == BreakStateRunning &&
           e.timers[BREAK_MICRO].active_s == 0,
           "skip resets the timer as if taken");
    expect(e.stats[BREAK_MICRO].skipped == 1, "skip counted");

    run_seconds(&e, 10, 1);
    expect(e.timers[BREAK_MICRO].state == BreakStateBreaking, "break re-started");

    break_engine_postpone(&e, BREAK_MICRO);
    ev = break_engine_take_event(&e, &brk);
    expect(ev == BreakEventPostponed &&
           e.timers[BREAK_MICRO].state == BreakStateSnoozed &&
           e.timers[BREAK_MICRO].snooze_s == 150,
           "postpone snoozes for the postpone time");
    expect(e.stats[BREAK_MICRO].postponed == 1, "postpone counted");

    run_seconds(&e, 149, 0);
    expect(e.timers[BREAK_MICRO].state == BreakStateSnoozed, "still snoozing");
    ev = step_second(&e, 0, &brk);
    expect(ev == BreakEventStart &&
           e.timers[BREAK_MICRO].state == BreakStateBreaking,
           "snooze expiry re-arms an un-ignorable break");
}

static void
test_break_freezes_on_activity(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10;
    e.timers[BREAK_MICRO].max_prompts = 0;

    run_seconds(&e, 10, 1);
    run_seconds(&e, 29, 1);
    expect(e.timers[BREAK_MICRO].state == BreakStateBreaking &&
           e.timers[BREAK_MICRO].idle_s == 0,
           "activity during the break freezes progress");

    run_seconds(&e, 29, 0);
    ev = step_second(&e, 0, &brk);
    expect(ev == BreakEventTaken && e.stats[BREAK_MICRO].taken == 1,
           "idle for the duration completes the break");
    expect(e.timers[BREAK_MICRO].active_s == 0 &&
           e.timers[BREAK_MICRO].state == BreakStateRunning,
           "taken break resets the timer");
}

static void
test_micro_promotes_to_rest(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 60;
    e.timers[BREAK_MICRO].max_prompts = 3;
    e.timers[BREAK_REST].limit_s = 80;

    run_seconds(&e, 59, 1);
    ev = step_second(&e, 1, &brk);
    expect(ev == BreakEventStart && brk == BREAK_REST,
           "rest break fires in place of a due micro break");
    expect(e.timers[BREAK_REST].state == BreakStateBreaking,
           "rest timer owns the window");
    expect(e.timers[BREAK_MICRO].active_s == 0 &&
           e.timers[BREAK_MICRO].state == BreakStateRunning,
           "micro timer credited and reset");
    expect(e.timers[BREAK_REST].lock_buttons_s == 0,
           "ignorable micro leaves rest buttons unlocked");

    /* An un-ignorable micro promotion locks the rest window buttons. */
    break_engine_init(&e);
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 60;
    e.timers[BREAK_MICRO].max_prompts = 0;
    e.timers[BREAK_REST].limit_s = 80;

    run_seconds(&e, 60, 1);
    expect(e.timers[BREAK_REST].state == BreakStateBreaking &&
           e.timers[BREAK_REST].lock_buttons_s == e.timers[BREAK_REST].duration_s,
           "un-ignorable micro locks the rest buttons");
}

static void
test_daily_limit_skip_and_day_reset(void)
{
    BreakEngine e;

    break_engine_init(&e);
    e.timers[BREAK_MICRO].enabled = 0;
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].limit_s = 60;

    run_seconds(&e, 60, 1);
    expect(e.timers[BREAK_DAILY].state == BreakStatePrompting,
           "daily limit prompts when reached");
    run_seconds(&e, 60, 1);
    expect(e.timers[BREAK_DAILY].state == BreakStateBreaking,
           "daily limit breaks after ignored prompts");

    break_engine_skip(&e, BREAK_DAILY);
    expect(e.timers[BREAK_DAILY].skipped_today == 1 &&
           e.timers[BREAK_DAILY].state == BreakStateRunning,
           "skipping disables the daily limit for today");

    run_seconds(&e, 1000, 1);
    expect(e.timers[BREAK_DAILY].state == BreakStateRunning,
           "skipped daily limit stays silent");

    expect(break_engine_set_day(&e, 1) == 1, "day change reported");
    expect(e.timers[BREAK_DAILY].skipped_today == 0 &&
           e.timers[BREAK_DAILY].active_s == 0,
           "day reset restores the daily limit");
    expect(break_engine_set_day(&e, 1) == 0, "same day is a no-op");

    run_seconds(&e, 60, 1);
    expect(e.timers[BREAK_DAILY].state == BreakStatePrompting,
           "daily limit runs again after the day reset");
}

static void
test_quiet_suspended_and_timed_modes(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 60;
    e.timers[BREAK_MICRO].max_prompts = 3;

    break_engine_set_mode(&e, BreakModeQuiet, 0);
    run_seconds(&e, 70, 1);
    expect(e.timers[BREAK_MICRO].state == BreakStateRunning,
           "quiet mode monitors but never prompts");
    expect(e.stats[BREAK_MICRO].overdue_s == 11,
           "quiet mode accrues overdue time");

    break_engine_set_mode(&e, BreakModeNormal, 0);
    ev = step_second(&e, 1, &brk);
    expect(ev == BreakEventPrompt, "overdue break fires after quiet ends");

    {
        int active_before = e.timers[BREAK_MICRO].active_s;
        int usage_before = e.usage_today_s;

        break_engine_set_mode(&e, BreakModeSuspended, 0);
        run_seconds(&e, 500, 1);
        expect(e.timers[BREAK_MICRO].active_s == active_before &&
               e.usage_today_s == usage_before,
               "suspended mode stops monitoring entirely");
    }

    break_engine_set_mode(&e, BreakModeQuiet, 2);
    (void)step_second(&e, 1, &brk);
    expect(e.mode == BreakModeQuiet, "timed mode still active");
    ev = step_second(&e, 1, &brk);
    expect(ev == BreakEventModeExpired && e.mode == BreakModeNormal,
           "timed mode expires back to normal");
}

static void
test_reading_mode(void)
{
    BreakEngine e;
    int brk = -1, ev;

    break_engine_init(&e);
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10000;
    e.timers[BREAK_REST].limit_s = 10;
    e.timers[BREAK_REST].max_prompts = 0;
    e.reading_mode = 1;

    (void)step_second(&e, 1, &brk);          /* first input latches reading */
    run_seconds(&e, 9, 0);                   /* idle still counts as active */
    expect(e.timers[BREAK_REST].active_s == 10 && e.usage_today_s == 10,
           "reading mode keeps timers running without input");
    expect(e.timers[BREAK_REST].state == BreakStateBreaking,
           "rest break started while reading");
    expect(e.reading_active == 0, "reading latch cleared at rest break");

    run_seconds(&e, 599, 0);
    ev = step_second(&e, 0, &brk);
    expect(ev == BreakEventTaken && e.stats[BREAK_REST].taken == 1,
           "rest break completes once the user actually rests");
    expect(e.usage_today_s == 10, "idle rest time is not usage");
}

static void
test_micro_counts_toward_daily_limit(void)
{
    BreakEngine e;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10;
    e.timers[BREAK_MICRO].duration_s = 5;
    e.timers[BREAK_MICRO].max_prompts = 3;
    e.timers[BREAK_DAILY].limit_s = 20;
    e.micro_counts_as_activity = 1;

    run_seconds(&e, 10, 1);                  /* micro due -> prompting */
    run_seconds(&e, 5, 0);                   /* idle -> natural take */
    expect(e.stats[BREAK_MICRO].natural == 1, "micro taken naturally");
    expect(e.timers[BREAK_DAILY].active_s == 15,
           "taken micro break counts toward the daily limit");
}

static void
test_force_break_and_next_due(void)
{
    BreakEngine e;
    int brk = -1;

    break_engine_init(&e);
    run_seconds(&e, 60, 1);
    expect(break_timer_next_due_s(&e, BREAK_MICRO) == 120 &&
           break_timer_next_due_s(&e, BREAK_REST) == 2640,
           "next due reports active seconds remaining");

    break_engine_force_break(&e, BREAK_REST);
    expect(break_engine_take_event(&e, &brk) == BreakEventStart &&
           brk == BREAK_REST &&
           e.timers[BREAK_REST].state == BreakStateBreaking &&
           e.timers[BREAK_REST].active_s == e.timers[BREAK_REST].limit_s,
           "forced break opens the window immediately");

    expect(break_engine_active_break(&e) == BREAK_REST,
           "active break reports the breaking timer");
    expect(break_timer_next_due_s(&e, BREAK_REST) == 0,
           "breaking timer reports due now");
}

static void
test_natural_take_latches_until_activity(void)
{
    BreakEngine e;

    break_engine_init(&e);
    e.timers[BREAK_REST].enabled = 0;
    e.timers[BREAK_DAILY].enabled = 0;

    /* Three break-durations of continuous idle: exactly one natural take. */
    run_seconds(&e, 90, 0);
    expect(e.stats[BREAK_MICRO].natural == 1 &&
           e.timers[BREAK_MICRO].active_s == 0,
           "one continuous idle period takes the break once");

    run_seconds(&e, 5, 1);          /* input re-arms the natural break */
    run_seconds(&e, 30, 0);         /* a fresh idle period takes again */
    expect(e.stats[BREAK_MICRO].natural == 2,
           "input re-arms the natural break");
}

static void
test_rest_completion_resets_micro(void)
{
    BreakEngine e;

    break_engine_init(&e);
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10000;   /* keep micro dormant */
    e.timers[BREAK_MICRO].duration_s = 600;  /* longer than the rest break */
    e.timers[BREAK_REST].limit_s = 10;
    e.timers[BREAK_REST].duration_s = 10;
    e.timers[BREAK_REST].max_prompts = 0;

    run_seconds(&e, 10, 1);
    expect(e.timers[BREAK_REST].state == BreakStateBreaking,
           "rest break window opens at its limit");
    expect(e.timers[BREAK_MICRO].active_s == 10,
           "micro accrues while the user works");

    run_seconds(&e, 12, 0);         /* idle through the 10 s rest break */
    expect(e.timers[BREAK_REST].state == BreakStateRunning &&
           e.stats[BREAK_REST].taken == 1,
           "rest break completes on idle");
    expect(e.timers[BREAK_MICRO].active_s == 0,
           "completing a rest break resets the micro timer");
    /* micro idle_s re-accrues from zero after the reset while the user is
     * still away; that is expected, not a double take (the latch holds). */
}

static void
test_note_idle_resets_after_long_absence(void)
{
    BreakEngine e;
    int brk = -1;

    break_engine_init(&e);
    e.timers[BREAK_DAILY].enabled = 0;
    e.timers[BREAK_MICRO].limit_s = 10000;
    e.timers[BREAK_REST].limit_s = 10000;

    run_seconds(&e, 20, 1);
    expect(e.timers[BREAK_REST].active_s == 20 &&
           e.timers[BREAK_MICRO].active_s == 20,
           "activity accrues before the absence");

    /* The OS idle counter reports a 20 minute absence (beyond the catch-up
     * cap of the per-second ticks): both timers reset naturally, once. */
    expect(break_engine_note_idle(&e, 1200) == 1,
           "long observed absence takes the breaks");
    expect(e.stats[BREAK_MICRO].natural == 1 &&
           e.stats[BREAK_REST].natural == 1,
           "micro and rest both reset naturally");
    expect(e.timers[BREAK_MICRO].active_s == 0 &&
           e.timers[BREAK_REST].active_s == 0,
           "timers reset after the natural break");
    (void)break_engine_take_event(&e, &brk);

    expect(break_engine_note_idle(&e, 3000) == 0,
           "the same idle period does not take twice");

    run_seconds(&e, 1, 1);          /* input re-arms the latch */
    expect(break_engine_note_idle(&e, 1200) == 1,
           "after input a new absence takes again");
    (void)break_engine_take_event(&e, &brk);
}

static void
test_format_duration_formats_hours(void)
{
    char buf[16];

    break_format_duration(buf, sizeof(buf), 59);
    expect(strcmp(buf, "0:59") == 0, "below an hour stays M:SS");
    break_format_duration(buf, sizeof(buf), 3599);
    expect(strcmp(buf, "59:59") == 0, "just under an hour stays M:SS");
    break_format_duration(buf, sizeof(buf), 3600);
    expect(strcmp(buf, "1:00:00") == 0, "hour boundary switches to H:MM:SS");
    break_format_duration(buf, sizeof(buf), 14400);
    expect(strcmp(buf, "4:00:00") == 0, "daily limit renders as H:MM:SS");
    break_format_duration(buf, sizeof(buf), 2147483647);
    expect(strcmp(buf, "596523:14:07") == 0,
           "maximum signed seconds fits the duration buffer");
    break_format_duration(buf, sizeof(buf), -5);
    expect(strcmp(buf, "0:00") == 0, "negative clamps to zero");
}

int
main(void)
{
    test_defaults_match_workrave();
    test_active_time_prompts_at_limit();
    test_input_resets_idle_and_natural_take();
    test_ignored_prompts_escalate_to_break();
    test_unignorable_break_forces_immediately();
    test_skip_and_postpone();
    test_break_freezes_on_activity();
    test_micro_promotes_to_rest();
    test_daily_limit_skip_and_day_reset();
    test_quiet_suspended_and_timed_modes();
    test_reading_mode();
    test_micro_counts_toward_daily_limit();
    test_force_break_and_next_due();
    test_natural_take_latches_until_activity();
    test_rest_completion_resets_micro();
    test_note_idle_resets_after_long_absence();
    test_format_duration_formats_hours();

    if (failures) {
        printf("FAIL (%d assertion(s))\n", failures);
        return 1;
    }
    printf("OK\n");
    return 0;
}
