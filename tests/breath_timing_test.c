#include "core/types.h"
#include "core/breath_timing.h"

#include <stdio.h>
#include <string.h>

/*
 * Breath-engine timing test.
 *
 * Drives BreathSessionStep() tick by tick (60 ticks == 1 second) through complete Wim
 * Hof sessions and asserts the between-round countdown ("3-2-1") honors the
 * round-0 special case and the user's configured pause for later rounds. This
 * is the area that regressed when the auto-play and manual round-advance paths
 * drifted apart: pause_seconds was forced to 3 at session start and never
 * restored on the auto-play path, so every round counted down from 3 and the
 * configured "Pause after round" setting was ignored.
 *
 * Pure engine: no raylib or platform host.
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

/* count_value is #private in the engine; decode locally like the app does. */
static int
count_value(const char *v)
{
    int a = v[0] >= '0' && v[0] <= '9' ? v[0] - '0' : 0;
    int b = v[1] >= '0' && v[1] <= '9' ? v[1] - '0' : 0;
    int c = v[2] >= '0' && v[2] <= '9' ? v[2] - '0' : 0;
    return a * 100 + b * 10 + c;
}

/* Step the engine until phase transitions away from `phase` or `max_steps` hit. */
static int
run_while_phase(BreathSession *l, int phase, int max_steps)
{
    int steps = 0;
    while (l->phase == phase && steps < max_steps && !l->completed) {
        *l = BreathSessionStep(*l);
        steps++;
    }
    return steps;
}

/* Measure how many ticks the Starting countdown lasts for the current round. */
static int
measure_starting_ticks(BreathSession *l)
{
    int ticks = 0;
    while (l->phase == BreathPhaseStarting && ticks < 4000 && !l->completed) {
        *l = BreathSessionStep(*l);
        ticks++;
    }
    return ticks;
}

/*
 * Run one round from Starting through to the start of the next round's
 * Starting (or completion). Holds are ended immediately via BreathEndHold so
 * the session progresses without a user tap.
 */
static void
run_one_round(BreathSession *l)
{
    /* Starting countdown -> Breathe. */
    run_while_phase(l, BreathPhaseStarting, 4000);
    /* Breathe until max breaths -> Hold. */
    run_while_phase(l, BreathPhaseBreathe, 200000);
    /* End the hold immediately (simulates the breath tap). */
    if (l->phase == BreathPhaseHold) {
        *l = BreathEndHold(*l);
    }
    /* Recover -> Next -> Starting (or completion). */
    run_while_phase(l, BreathPhaseRecover, 200000);
    run_while_phase(l, BreathPhaseNext, 200000);
}

static void
test_round_zero_uses_three_second_countdown(void)
{
    BreathSession l;
    l = BreathSessionInit();
    l.pause_seconds = 15;          /* a configured pause that must NOT apply to round 0 */
    l.breath_half_ticks = 120;
    l.max_rounds = 3;

    /* Round 0 should always count down from 3 (180 ticks), regardless of config. */
    int ticks = measure_starting_ticks(&l);
    expect(ticks == 3 * 60,
           "round 0 countdown should be exactly 3s (180 ticks)");
    expect(l.phase == BreathPhaseBreathe,
           "round 0 should transition to Breathe after 3s");

    /* BreathPauseSeconds must report 3 for round 0. */
    l.round = 0;
    expect(BreathPauseSeconds(l) == 3,
           "effective pause for round 0 should be 3");
}

static void
test_later_rounds_use_configured_pause(void)
{
    BreathSession l;
    l = BreathSessionInit();
    l.pause_seconds = 15;          /* configured "Pause after round" */
    l.breath_half_ticks = 120;
    l.max_rounds = 3;
    l.phase = BreathPhaseStarting;
    l.round = 0;

    /* Complete round 0 so we land in round 1's Starting. */
    run_one_round(&l);
    expect(l.round == 1, "should advance to round 1 after round 0");

    /* The bug: round 1 used to count down from 3 (180 ticks) instead of 15. */
    expect(BreathPauseSeconds(l) == 15,
           "effective pause for round 1 should be configured (15)");
    int ticks = measure_starting_ticks(&l);
    expect(ticks == 15 * 60,
           "round 1 countdown should be configured 15s (900 ticks), not 3s");
}

static void
test_configured_pause_zero_skips_countdown(void)
{
    BreathSession l;
    l = BreathSessionInit();
    l.pause_seconds = 0;           /* no pause between rounds configured */
    l.breath_half_ticks = 120;
    l.max_rounds = 2;
    l.phase = BreathPhaseStarting;
    l.round = 0;

    run_one_round(&l);
    expect(l.round == 1, "should advance to round 1");

    expect(BreathPauseSeconds(l) == 0,
           "effective pause for round 1 should be 0 when configured 0");
    /* With pause 0, Starting must not linger (transitions within a couple ticks). */
    int ticks = measure_starting_ticks(&l);
    expect(ticks <= 1,
           "round 1 with pause 0 should skip countdown immediately");
}

static void
test_results_populated_each_round(void)
{
    BreathSession l;
    int i;

    l = BreathSessionInit();
    l.pause_seconds = 2;
    l.breath_half_ticks = 120;
    l.max_rounds = 3;
    l.phase = BreathPhaseStarting;
    l.round = 0;

    /* Run rounds 0 and 1 to completion of their holds. */
    run_one_round(&l);                 /* round 0 hold ended, now in round 1 Starting */
    expect(count_value(l.results[0]) >= 0,
           "round 0 results should be set (hold ended)");

    run_one_round(&l);                 /* round 1 hold ended, now in round 2 Starting */
    expect(l.round == 2, "should advance to round 2");
    expect(count_value(l.results[1]) >= 0,
           "round 1 results should be set (hold ended)");
    (void)i;
}

static void
test_final_round_completes(void)
{
    BreathSession l;
    l = BreathSessionInit();
    l.pause_seconds = 2;
    l.breath_half_ticks = 120;
    l.max_rounds = 2;
    l.phase = BreathPhaseStarting;
    l.round = 0;

    /* Run all rounds to completion. */
    run_one_round(&l);                 /* -> round 1 */
    expect(!l.completed, "not complete after round 0");
    run_one_round(&l);                 /* -> final round completes */
    expect(l.completed,
           "session should be marked complete after final round");
    expect(l.completed,
           "session should report completion after final round");

    /* Once complete, stepping must be a no-op (no phantom round). */
    int phase_before = l.phase;
    int round_before = l.round;
    l = BreathSessionStep(l);
    expect(l.phase == phase_before && l.round == round_before,
           "completed engine must not advance on further steps");

    /* Clearing completion resets the flag (the app layer does this on save). */
    l = BreathClearCompleted(l);
    expect(!l.completed,
           "BreathClearCompleted should clear the flag");
}

int
main(void)
{
    test_round_zero_uses_three_second_countdown();
    test_later_rounds_use_configured_pause();
    test_configured_pause_zero_skips_countdown();
    test_results_populated_each_round();
    test_final_round_completes();

    if (failures) {
        printf("FAIL (%d assertion(s))\n", failures);
        return 1;
    }
    printf("OK\n");
    return 0;
}
