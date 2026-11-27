// Authored UI composition; native application state remains in movement_view.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeShape from "kryon/shape";
import * as NativeText from "kryon/text";
import * as NativeToolbar from "kryon/toolbar";
import * as State_movement_view from "movement_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle, Vector2 } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { TextHeight, TextWidth } from "kryon/text_measure";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { DiscreteSlider } from "kryon/tsx/slider";
import { Text } from "kryon/tsx/text";
import {
    Alpha,
    Bounds,
    Figure,
    FormatCount,
    JoinCue,
    Locale,
    NewLabelKey,
    ParagraphHeight,
    Scale
} from "movement_view";
import {
    PRACTICE_MOVEMENT_PAUSE,
    PRACTICE_MOVEMENT_SEEK,
    PRACTICE_MOVEMENT_VIEWPOINT
} from "practice_types";
import { SalutationClamp, SalutationSideKey } from "sun_salutation_rules";
import {
    WORKOUT_COUNT_GO,
    WORKOUT_COUNT_NONE,
    WORKOUT_PHASE_LOADING,
    WORKOUT_PHASE_PREPARE,
    WORKOUT_PHASE_WORK,
    WORKOUT_TIMELINE_LIMIT,
    WorkoutCountdownAt,
    WorkoutKeyFor,
    WorkoutRoutineCount,
    WorkoutRoutineExercise
} from "workout_rules";
import { WORKOUT_ROUTINE_CUSTOM } from "workout_sequence";
import { ExerciseType } from "exercise_types";
import { FlagIntersection, FlagShiftLeft } from "native_flags";

export function Controls(): s32 {
    let layout = NativeToolbar.BottomIconRowLayoutFor(
        {
            center_x: State_movement_view.movement.view_width / 2n,
            view_width: State_movement_view.movement.view_width,
            view_height: State_movement_view.movement.view_height,
            count: 3n
        },
        State_movement_view.movement.scale
    );
    let labels: [string, string, string] = [
        Locale("back_button"),
        Locale(State_movement_view.movement.paused ? "play_button" : "pause_button"),
        Locale("next_button")
    ];
    let sources: [Rectangle, Rectangle, Rectangle] = [
        { x: 128n, y: 0n, width: 64n, height: 64n },
        { x: State_movement_view.movement.paused ? 256.0 : 64.0, y: 192n, width: 64n, height: 64n },
        { x: 128n, y: 64n, width: 64n, height: 64n }
    ];
    for (let index = s32(0n); index <= 2n; index += s32(1)) {
        if (
            Button({
                session: State_movement_view.movement.session,
                props: {
                    id: 83000n + index,
                    bounds: NativeToolbar.BottomIconRowButtonBoundsFor(layout, index),
                    label: nativeAt(labels, index),
                    icon_only: true,
                    image: {
                        asset_path: "icons/ui.webp",
                        source: nativeAt(sources, index),
                        alt_text: nativeAt(labels, index)
                    },
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: index === 0n && !State_movement_view.movement.can_back
                }
            })
        ) {
            State_movement_view.movement.action = index + 1n;
        }
    }
    return layout.y;
}

export function SunBreathCue(y: s32, width: s32): void {
    let text_size = Scale(16n);
    let inhale_width = TextWidth(State_movement_view.movement.session, {
        text: Locale("sun_salutation_breathe_in"),
        size: text_size
    });
    let exhale_width = TextWidth(State_movement_view.movement.session, {
        text: Locale("sun_salutation_breathe_out"),
        size: text_size
    });
    let label_width = inhale_width > exhale_width ? inhale_width : exhale_width;
    let icon_slot = Scale(34n);
    if (label_width > width - icon_slot) {
        label_width = width - icon_slot;
    }
    let left = (State_movement_view.movement.view_width - label_width - icon_slot) / 2n;
    let center: Vector2 = { x: float32(left + Scale(15n)), y: float32(y + Scale(15n)) };
    let radius = float32(Scale(13n));
    let inner_radius = radius - float32(Scale(1n));
    let amount =
        float32(SalutationClamp(State_movement_view.movement.progress, 0n, 1000n)) / 1000.0;
    NativeShape.Circle(State_movement_view.movement.session, {
        center: center,
        radius: inner_radius,
        fill: Alpha(State_movement_view.movement.accent_color, 0.12)
    });
    NativeShape.Ring(State_movement_view.movement.session, {
        center: center,
        inner_radius: inner_radius,
        outer_radius: radius,
        start_angle: 0.0,
        end_angle: 360.0,
        color: Alpha(State_movement_view.movement.accent_color, 0.55)
    });
    NativeShape.Ring(State_movement_view.movement.session, {
        center: center,
        outer_radius: inner_radius,
        start_angle: -90.0,
        end_angle: -90.0 + amount * 360.0,
        color: State_movement_view.movement.accent_color
    });
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.cue,
            bounds: Bounds(left + icon_slot, y, label_width, Scale(30n)),
            size: text_size,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
}

export function SunSalutation(): void {
    let controls_y = Controls();
    let pad = Scale(24n);
    let text_w = State_movement_view.movement.view_width - pad * 2n;
    if (text_w > Scale(560n)) {
        text_w = Scale(560n);
    }
    let text_x = (State_movement_view.movement.view_width - text_w) / 2n;
    let heading_y = State_movement_view.movement.top + Scale(8n);
    let breath_y = heading_y + Scale(34n);
    let emphasis: [NativeText.Range] = [
        { start: 0n, end: s32(State_movement_view.movement.heading.count) }
    ];
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.heading,
            bounds: Bounds(
                pad,
                heading_y,
                State_movement_view.movement.view_width - pad * 2n,
                Scale(32n)
            ),
            size: Scale(22n),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            strong: nativeSlice(emphasis, 0n, 1n),
            wrap: Wrap.TextWrapEllipsis
        }}
    />;
    SunBreathCue(breath_y, text_w);
    let cue_font = Scale(16n);
    let line_h = TextHeight(State_movement_view.movement.session, { text: "M", size: cue_font });
    let cue_h = line_h * 3n;
    let cue_y = controls_y - Scale(8n) - cue_h;
    let side = SalutationSideKey(State_movement_view.movement.phase);
    let cue = State_movement_view.movement.subtitle;
    if (side.count > 0n) {
        cue = JoinCue(Locale(side), cue);
    }
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: cue,
            bounds: Bounds(text_x, cue_y, text_w, cue_h),
            size: cue_font,
            class_name: State_movement_view.movement.muted_class,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapAuto
        }}
    />;
    let stage_y = breath_y + Scale(32n);
    Figure(
        Bounds(
            pad,
            stage_y,
            State_movement_view.movement.view_width - pad * 2n,
            cue_y - Scale(4n) - stage_y
        ),
        "sun-salutation/figure",
        Locale("exercise_sun_salutation")
    );
}

export function TaiChi(): void {
    let row_y = Controls();
    let y = State_movement_view.movement.top + Scale(12n);
    let subtitle_h = TextHeight(State_movement_view.movement.session, {
        text: "M",
        size: Scale(16n)
    });
    if (State_movement_view.movement.subtitle.count > 0n) {
        <Text
            session={State_movement_view.movement.session}
            props={{
                text: State_movement_view.movement.subtitle,
                bounds: Bounds(
                    Scale(24n),
                    y,
                    State_movement_view.movement.view_width - Scale(48n),
                    subtitle_h
                ),
                size: Scale(16n),
                class_name: State_movement_view.movement.muted_class,
                align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapEllipsis
            }}
        />;
    }
    y = y + (subtitle_h + Scale(4n));
    let cue_height =
        TextHeight(State_movement_view.movement.session, { text: "M", size: Scale(20n) }) * 2n;
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.cue,
            bounds: Bounds(
                Scale(24n),
                y,
                State_movement_view.movement.view_width - Scale(48n),
                cue_height
            ),
            size: Scale(20n),
            align: TextAlign.TextAlignCenter
        }}
    />;
    y = y + (cue_height + Scale(8n));
    let progress_y = row_y - Scale(48n);
    let width = State_movement_view.movement.view_width - Scale(96n);
    if (width > Scale(420n)) {
        width = Scale(420n);
    }
    let seek = DiscreteSlider({
        session: State_movement_view.movement.session,
        props: {
            key: NativeLayout.KeyHash("inbe/practices/tai_chi/progress"),
            bounds: Bounds(
                (State_movement_view.movement.view_width - width) / 2n,
                progress_y,
                width,
                Scale(44n)
            ),
            semantic_label: Locale("practice_playback_position"),
            min: 0n,
            max: State_movement_view.movement.length_ms / 1000n,
            value: State_movement_view.movement.elapsed_ms / 1000n
        }
    });
    if (seek.changed) {
        State_movement_view.movement.action = PRACTICE_MOVEMENT_SEEK;
        State_movement_view.movement.value = seek.value;
    }
    let angle_y = progress_y - Scale(52n);
    width = State_movement_view.movement.view_width - Scale(48n);
    if (width > Scale(440n)) {
        width = Scale(440n);
    }
    let options: [
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption
    ] = [
        { label: Locale("tai_chi_view_front") },
        { label: Locale("tai_chi_view_back") },
        { label: Locale("tai_chi_view_side") },
        { label: Locale("tai_chi_view_angled") }
    ];
    let choice = SegmentedControl({
        session: State_movement_view.movement.session,
        props: {
            key: NativeLayout.KeyHash("inbe/practices/tai_chi/angle"),
            bounds: Bounds(
                (State_movement_view.movement.view_width - width) / 2n,
                angle_y,
                width,
                Scale(40n)
            ),
            height: Scale(40n),
            selected_index: State_movement_view.movement.view,
            has_selection: true
        },
        options: nativeSlice(options)
    });
    if (choice.changed) {
        State_movement_view.movement.action = PRACTICE_MOVEMENT_VIEWPOINT;
        State_movement_view.movement.value = choice.selected_index;
    }
    Figure(
        Bounds(
            Scale(12n),
            y,
            State_movement_view.movement.view_width - Scale(24n),
            angle_y - Scale(12n) - y
        ),
        "inbe/practices/tai_chi/figure",
        Locale("exercise_tai_chi")
    );
}

export function Pause(x: s32, y: s32, width: s32): void {
    if (
        Button({
            session: State_movement_view.movement.session,
            props: {
                key: NativeLayout.KeyHash(
                    State_movement_view.movement.practice === s32(ExerciseType.EXERCISE_WORKOUT)
                        ? "workout/pause"
                        : "astral/pause"
                ),
                label: Locale(
                    State_movement_view.movement.paused ? "patterns_resume_button" : "pause_button"
                ),
                bounds: Bounds(x, y, width, Scale(48n)),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        State_movement_view.movement.action = PRACTICE_MOVEMENT_PAUSE;
    }
}

export function Astral(): void {
    let pad = Scale(24n);
    let width = State_movement_view.movement.view_width - pad * 2n;
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.time,
            bounds: Bounds(pad, State_movement_view.movement.top + Scale(12n), width, Scale(48n)),
            size: Scale(28n),
            align: TextAlign.TextAlignCenter
        }}
    />;
    let y = State_movement_view.movement.top + Scale(64n);
    if (State_movement_view.movement.length_ms > 0n) {
        let seek = DiscreteSlider({
            session: State_movement_view.movement.session,
            props: {
                key: NativeLayout.KeyHash("astral/progress"),
                bounds: Bounds(pad, y, width, Scale(44n)),
                semantic_label: Locale("practice_playback_position"),
                min: 0n,
                max: State_movement_view.movement.length_ms / 1000n,
                value: State_movement_view.movement.elapsed_ms / 1000n
            }
        });
        if (seek.changed) {
            State_movement_view.movement.action = PRACTICE_MOVEMENT_SEEK;
            State_movement_view.movement.value = seek.value;
        }
        y = y + Scale(48n);
    }
    let button_y = State_movement_view.movement.view_height - Scale(76n);
    let height = button_y - y - Scale(16n);
    if (height < Scale(40n)) {
        height = Scale(40n);
    }
    if (height >= Scale(160n)) {
        let scene_height = (height * 48n) / 100n;
        Figure(
            Bounds(pad, y, width, scene_height),
            "astral/scene",
            Locale("exercise_astral_projection")
        );
        y = y + (scene_height + Scale(12n));
        height = height - (scene_height + Scale(12n));
    }
    let text_h = ParagraphHeight(
        State_movement_view.movement.cue,
        width,
        State_movement_view.movement.font
    );
    let scrolled = NativeScroll.Draw(State_movement_view.movement.session, {
        key: NativeLayout.KeyHash("astral/guidance"),
        bounds: Bounds(pad, y, width, height),
        content_height: text_h,
        scroll_offset: State_movement_view.movement.scroll
    });
    State_movement_view.movement.scroll = scrolled.scroll_offset;
    if (scrolled.opened) {
        <Text
            session={State_movement_view.movement.session}
            props={{
                text: State_movement_view.movement.cue,
                bounds: {
                    x: scrolled.content.x,
                    y: scrolled.content.y,
                    width: float32(width),
                    height: float32(text_h)
                },
                size: State_movement_view.movement.font,
                align: TextAlign.TextAlignCenter
            }}
        />;
        End(State_movement_view.movement.session);
    }
    let button_w = Scale(220n);
    if (button_w > width) {
        button_w = width;
    }
    Pause((State_movement_view.movement.view_width - button_w) / 2n, button_y, button_w);
}

export function WorkoutProgress(x: s32, y: s32, width: s32): s32 {
    let custom = State_movement_view.movement.view === WORKOUT_ROUTINE_CUSTOM;
    let count = custom
        ? s32(State_movement_view.movement.time.count)
        : WorkoutRoutineCount(State_movement_view.movement.view);
    if (count <= 0n || count > WORKOUT_TIMELINE_LIMIT) {
        return 0n;
    }
    let target = Scale(44n);
    let columns = width / target;
    if (columns < 1n) {
        columns = 1n;
    }
    let rows = (count + columns - 1n) / columns;
    if (rows > 3n) {
        rows = 3n;
    }
    columns = (count + rows - 1n) / rows;
    let bar_h = Scale(6n);
    let gap = Scale(4n);
    for (let index = s32(0n); index < count; index += s32(1)) {
        let col = index % columns;
        let top = y + (index / columns) * target;
        let left = x + (width * col) / columns;
        let cell = x + (width * (col + 1n)) / columns - left;
        let exercise = custom
            ? s32(nativeAt(State_movement_view.movement.time, index)) - 65n
            : WorkoutRoutineExercise(State_movement_view.movement.view, index);
        let label_key = NewLabelKey();
        let name = Locale(WorkoutKeyFor("workout_name_", exercise, nativeSlice(label_key)));
        let current = custom
            ? index === State_movement_view.movement.scroll
            : exercise === State_movement_view.movement.exercise;
        if (
            Button({
                session: State_movement_view.movement.session,
                props: {
                    key: NativeLayout.KeyHash("workout/progress") + u64(index),
                    bounds: Bounds(left, top, cell, target),
                    label: name,
                    icon_only: true,
                    selected: current,
                    disabled:
                        State_movement_view.movement.phase === WORKOUT_PHASE_LOADING ||
                        State_movement_view.movement.phase === WORKOUT_PHASE_PREPARE,
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }
            })
        ) {
            State_movement_view.movement.action = PRACTICE_MOVEMENT_SEEK;
            State_movement_view.movement.value = index;
        }
        let bar = Bounds(left + gap / 2n, top + (target - bar_h) / 2n, cell - gap, bar_h);
        let tint = current
            ? Alpha(State_movement_view.movement.accent_color, 0.35)
            : Alpha(State_movement_view.movement.text_color, 0.14);
        <Box
            session={State_movement_view.movement.session}
            props={{ bounds: bar, fill: tint, radius: float32(bar_h) / 2.0 }}
        />;
        let share: float32 = 0.0;
        if (
            FlagIntersection(
                State_movement_view.movement.progress,
                FlagShiftLeft(s32(1n), index)
            ) !== 0n
        ) {
            share = 1.0;
        } else if (
            current &&
            State_movement_view.movement.phase === WORKOUT_PHASE_WORK &&
            State_movement_view.movement.length_ms > 0n
        ) {
            share =
                float32(State_movement_view.movement.elapsed_ms) /
                float32(State_movement_view.movement.length_ms);
        }
        if (share > 0.0) {
            bar.width = bar.width * share;
            if (bar.width < float32(bar_h)) {
                bar.width = float32(bar_h);
            }
            <Box
                session={State_movement_view.movement.session}
                props={{
                    bounds: bar,
                    fill: State_movement_view.movement.accent_color,
                    radius: float32(bar_h) / 2.0
                }}
            />;
        }
    }
    return rows * target;
}

export function WorkoutCountdownNumber(center: Vector2, radius: float32, count: s32): void {
    let text = Locale("workout_go");
    if (count !== WORKOUT_COUNT_GO) {
        text = FormatCount(count);
    }
    let emphasis: [NativeText.Range] = [{ start: 0n, end: s32(text.count) }];
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: text,
            bounds: {
                x: center.x - radius * 2.0,
                y: center.y - radius,
                width: radius * 4.0,
                height: radius * 2.0
            },
            size: Scale(64n),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone,
            strong: nativeSlice(emphasis, 0n, 1n)
        }}
    />;
}

export function WorkoutCountdown(center: Vector2, radius: float32): void {
    if (State_movement_view.movement.phase !== WORKOUT_PHASE_LOADING) {
        let count = WorkoutCountdownAt({
            phase: State_movement_view.movement.phase,
            exercise: State_movement_view.movement.exercise,
            elapsed_ms: State_movement_view.movement.elapsed_ms,
            length_ms: State_movement_view.movement.length_ms
        });
        if (count !== WORKOUT_COUNT_NONE) {
            WorkoutCountdownNumber(center, radius, count);
            return;
        }
    }
    let thickness = float32(Scale(6n));
    NativeShape.Ring(State_movement_view.movement.session, {
        center: center,
        inner_radius: radius - thickness,
        outer_radius: radius,
        start_angle: 0.0,
        end_angle: 360.0,
        color: Alpha(State_movement_view.movement.text_color, 0.12)
    });
    let left: float32 = 1.0;
    if (State_movement_view.movement.length_ms > 0n) {
        left =
            left -
            float32(State_movement_view.movement.elapsed_ms) /
                float32(State_movement_view.movement.length_ms);
    }
    if (left > 0.0) {
        NativeShape.Ring(State_movement_view.movement.session, {
            center: center,
            inner_radius: radius - thickness,
            outer_radius: radius,
            start_angle: -90.0,
            end_angle: -90.0 + 360.0 * left,
            color: State_movement_view.movement.accent_color
        });
    }
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: FormatCount(State_movement_view.movement.seconds_left),
            bounds: {
                x: center.x - radius,
                y: center.y - radius,
                width: radius * 2.0,
                height: radius * 2.0
            },
            size: Scale(30n),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function Workout(): void {
    let pad = Scale(20n);
    let wide =
        State_movement_view.movement.view_width >= Scale(760n) &&
        State_movement_view.movement.view_width * 10n >=
            State_movement_view.movement.view_height * 12n;
    let panel_w = wide
        ? (State_movement_view.movement.view_width * 2n) / 5n
        : State_movement_view.movement.view_width - pad * 2n;
    if (panel_w > Scale(560n)) {
        panel_w = Scale(560n);
    }
    let panel_x = wide
        ? State_movement_view.movement.view_width - pad - panel_w
        : (State_movement_view.movement.view_width - panel_w) / 2n;
    let progress_y = State_movement_view.movement.top + Scale(4n);
    let progress_h = WorkoutProgress(
        pad,
        progress_y,
        State_movement_view.movement.view_width - pad * 2n
    );
    let heading_h = ParagraphHeight(State_movement_view.movement.heading, panel_w, Scale(26n));
    let sub_h = ParagraphHeight(
        State_movement_view.movement.subtitle,
        panel_w,
        State_movement_view.movement.font
    );
    let tip_h = ParagraphHeight(
        State_movement_view.movement.cue,
        panel_w,
        State_movement_view.movement.font,
        Scale(3n)
    );
    if (!wide) {
        let body_line = TextHeight(State_movement_view.movement.session, {
            text: "M",
            size: State_movement_view.movement.font
        });
        heading_h =
            TextHeight(State_movement_view.movement.session, { text: "M", size: Scale(26n) }) * 2n;
        sub_h = body_line * 2n;
        tip_h = body_line * 3n;
    }
    let content_top = progress_y + progress_h + Scale(4n);
    let words_h = heading_h + Scale(4n) + sub_h;
    let ring_r = Scale(44n);
    let lower_h = tip_h + Scale(16n) + ring_r * 2n + Scale(16n + 48n + 20n);
    let panel_top = content_top;
    let stage: Rectangle = {};
    if (wide) {
        stage = Bounds(
            pad,
            content_top,
            panel_x - pad * 2n,
            State_movement_view.movement.view_height - content_top - pad
        );
        panel_top =
            content_top +
            (State_movement_view.movement.view_height -
                content_top -
                pad -
                words_h -
                Scale(24n) -
                lower_h) /
                2n;
        if (panel_top < content_top) {
            panel_top = content_top;
        }
    } else {
        stage = Bounds(
            pad,
            content_top + words_h + Scale(8n),
            State_movement_view.movement.view_width - pad * 2n,
            State_movement_view.movement.view_height - content_top - words_h - Scale(12n) - lower_h
        );
    }
    let emphasis: [NativeText.Range] = [
        { start: 0n, end: s32(State_movement_view.movement.heading.count) }
    ];
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.heading,
            bounds: Bounds(panel_x, panel_top, panel_w, heading_h),
            size: Scale(26n),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignEnd,
            strong: nativeSlice(emphasis, 0n, 1n)
        }}
    />;
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.subtitle,
            bounds: Bounds(panel_x, panel_top + heading_h + Scale(4n), panel_w, sub_h),
            size: State_movement_view.movement.font,
            align: TextAlign.TextAlignCenter,
            disabled: true
        }}
    />;
    let minimum_stage = float32(Scale(60n));
    if (
        stage.height < minimum_stage &&
        State_movement_view.movement.phase === WORKOUT_PHASE_LOADING
    ) {
        stage.height = minimum_stage;
    }
    if (stage.height > 0.0) {
        Figure(stage, "workout/figure", State_movement_view.movement.heading);
    }
    let lower_y = wide
        ? panel_top + words_h + Scale(24n)
        : State_movement_view.movement.view_height - lower_h;
    <Text
        session={State_movement_view.movement.session}
        props={{
            text: State_movement_view.movement.cue,
            bounds: Bounds(panel_x, lower_y, panel_w, tip_h),
            size: State_movement_view.movement.font,
            align: TextAlign.TextAlignCenter
        }}
    />;
    if (State_movement_view.movement.phase === WORKOUT_PHASE_PREPARE) {
        let label_h = TextHeight(State_movement_view.movement.session, {
            text: Locale("workout_starting_in"),
            size: State_movement_view.movement.font
        });
        <Text
            session={State_movement_view.movement.session}
            props={{
                text: Locale("workout_starting_in"),
                bounds: Bounds(panel_x, lower_y + tip_h + Scale(16n) - label_h, panel_w, label_h),
                size: State_movement_view.movement.font,
                align: TextAlign.TextAlignCenter
            }}
        />;
    }
    WorkoutCountdown(
        { x: float32(panel_x + panel_w / 2n), y: float32(lower_y + tip_h + Scale(16n) + ring_r) },
        float32(ring_r)
    );
    let width = Scale(220n);
    if (width > panel_w) {
        width = panel_w;
    }
    Pause(
        panel_x + (panel_w - width) / 2n,
        lower_y + tip_h + Scale(16n) + ring_r * 2n + Scale(16n),
        width
    );
}
