// Authored UI composition; native application state remains in results_view.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeShape from "kryon/shape";
import * as NativeText from "kryon/text";
import * as State_results_view from "results_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color, DarkenColor } from "kryon/drawing_props";
import { Vector2 } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import {
    PRACTICE_HABIT_OFFER_ADDED,
    PRACTICE_RESULTS_ADD_HABIT,
    PRACTICE_RESULTS_DISCARD,
    PRACTICE_RESULTS_DONE,
    PRACTICE_RESULTS_MOOD,
    PRACTICE_RESULTS_SKIP_HABIT
} from "practice_types";
import {
    Accent,
    Alpha,
    Bounds,
    ChartHeight,
    ChartRoundLabel,
    ChartX,
    ChartY,
    Content,
    ContentHeight,
    Corner,
    Duration,
    EmptyString,
    Filled,
    FitFont,
    Locale,
    MoodColor,
    MoodLabelKey,
    MoodMuted,
    MoodPoint,
    NewLines,
    Number,
    RESULTS_MOODS,
    RoundCountLabel,
    RoundStats,
    Rounds,
    Scale
} from "results_view";
import { ExerciseType } from "exercise_types";

export function Label(
    text: string,
    x: s32,
    y: s32,
    width: s32,
    height: s32,
    font: s32,
    align: TextAlign
): void {
    <Text
        session={State_results_view.results.session}
        props={{
            bounds: Bounds(x, y, width, height),
            text: text,
            size: font,
            align: align,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function Card(x: s32, y: s32, width: s32, height: s32): void {
    <Box
        session={State_results_view.results.session}
        props={{
            bounds: Bounds(x, y, width, height),
            fill: State_results_view.results.surface_color,
            border: State_results_view.results.border_color,
            radius: Corner(0.12, width, height)
        }}
    />;
}

export function MoodFace(mood: s32, center_x: s32, center_y: s32, size: s32): void {
    let radius = float32(size) * 0.5;
    let cx = float32(center_x);
    let cy = float32(center_y);
    let centre = MoodPoint(cx, cy);
    let selected = State_results_view.results.mood === mood;
    let faded = State_results_view.results.mood > 0n && !selected;
    let fill = MoodColor(mood);
    let detail: Color = { r: 52n, g: 44n, b: 54n, a: 255n };
    if (faded) {
        fill = MoodMuted(fill);
        detail = Alpha(detail, 0.45);
    }
    let stroke = float32(Scale(2n));
    if (selected) {
        NativeShape.Ring(State_results_view.results.session, {
            center: centre,
            inner_radius: radius + float32(Scale(2n)),
            outer_radius: radius + float32(Scale(4n)),
            end_angle: 360.0,
            color: Accent()
        });
    }
    NativeShape.Circle(State_results_view.results.session, {
        center: centre,
        radius: radius,
        fill: fill
    });
    NativeShape.Ring(State_results_view.results.session, {
        center: centre,
        inner_radius: radius - 1.5,
        outer_radius: radius,
        end_angle: 360.0,
        color: Alpha(DarkenColor(fill, 40n), 0.55)
    });
    let eye = radius * 0.11;
    if (eye < 1.5) {
        eye = 1.5;
    }
    NativeShape.Circle(State_results_view.results.session, {
        center: MoodPoint(cx - radius * 0.36, cy - radius * 0.2),
        radius: eye,
        fill: detail
    });
    NativeShape.Circle(State_results_view.results.session, {
        center: MoodPoint(cx + radius * 0.36, cy - radius * 0.2),
        radius: eye,
        fill: detail
    });
    if (mood <= 1n) {
        <Shape
            session={State_results_view.results.session}
            props={{
                start: MoodPoint(cx - radius * 0.56, cy - radius * 0.52),
                end: MoodPoint(cx - radius * 0.2, cy - radius * 0.38),
                thickness: stroke,
                color: detail
            }}
        />;
        <Shape
            session={State_results_view.results.session}
            props={{
                start: MoodPoint(cx + radius * 0.56, cy - radius * 0.52),
                end: MoodPoint(cx + radius * 0.2, cy - radius * 0.38),
                thickness: stroke,
                color: detail
            }}
        />;
        NativeShape.Ring(State_results_view.results.session, {
            center: MoodPoint(cx, cy + radius * 0.74),
            inner_radius: radius * 0.34 - stroke * 0.5,
            outer_radius: radius * 0.34 + stroke * 0.5,
            start_angle: 205.0,
            end_angle: 335.0,
            color: detail
        });
    } else if (mood === 2n) {
        NativeShape.Ring(State_results_view.results.session, {
            center: MoodPoint(cx, cy + radius * 0.7),
            inner_radius: radius * 0.34 - stroke * 0.5,
            outer_radius: radius * 0.34 + stroke * 0.5,
            start_angle: 215.0,
            end_angle: 325.0,
            color: detail
        });
    } else if (mood === 3n) {
        <Shape
            session={State_results_view.results.session}
            props={{
                start: MoodPoint(cx - radius * 0.3, cy + radius * 0.42),
                end: MoodPoint(cx + radius * 0.3, cy + radius * 0.42),
                thickness: stroke,
                color: detail
            }}
        />;
    } else if (mood === 4n) {
        NativeShape.Ring(State_results_view.results.session, {
            center: MoodPoint(cx, cy + radius * 0.06),
            inner_radius: radius * 0.4 - stroke * 0.5,
            outer_radius: radius * 0.4 + stroke * 0.5,
            start_angle: 25.0,
            end_angle: 155.0,
            color: detail
        });
    } else {
        NativeShape.Ring(State_results_view.results.session, {
            center: MoodPoint(cx, cy + radius * 0.12),
            inner_radius: 0.0,
            outer_radius: radius * 0.5,
            start_angle: 0.0,
            end_angle: 180.0,
            color: detail
        });
        NativeShape.Circle(State_results_view.results.session, {
            center: MoodPoint(cx, cy + radius * 0.5),
            radius: radius * 0.16,
            fill: faded
                ? Alpha({ r: 236n, g: 108n, b: 128n, a: 255n }, 0.45)
                : { r: 236n, g: 108n, b: 128n, a: 255n }
        });
    }
}

export function MoodPicker(x: s32, y: s32, width: s32): void {
    let padding = Scale(14n);
    let gap = Scale(7n);
    let item_width = (width - padding * 2n - gap * (RESULTS_MOODS - 1n)) / RESULTS_MOODS;
    let button_y = y + Scale(46n);
    let button_height = Scale(56n);
    Card(x, y, width, Scale(State_results_view.MOOD_CARD_HEIGHT));
    Label(
        Locale("results_mood_title"),
        x + padding,
        y + Scale(10n),
        width - padding * 2n,
        Scale(30n),
        Scale(18n),
        TextAlign.TextAlignStart
    );
    for (let index = s32(0n); index < RESULTS_MOODS; index += s32(1)) {
        let button_x = x + padding + index * (item_width + gap);
        let button_width =
            index === RESULTS_MOODS - 1n ? x + width - padding - button_x : item_width;
        let selected = State_results_view.results.mood === index + 1n;
        if (
            Button({
                session: State_results_view.results.session,
                props: {
                    bounds: Bounds(button_x, button_y, button_width, button_height),
                    id: 24800n + index,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    selected: selected
                }
            })
        ) {
            State_results_view.results.action = PRACTICE_RESULTS_MOOD;
            State_results_view.results.value = index + 1n;
        }
        MoodFace(
            index + 1n,
            button_x + button_width / 2n,
            button_y + button_height / 2n,
            Scale(selected ? 36n : 30n)
        );
        let name = Locale(MoodLabelKey(index + 1n));
        let label_x = button_x - gap / 2n;
        let label_width = button_width + gap;
        let strong: [NativeText.Range] = [{ start: 0n, end: s32(name.count) }];
        <Text
            session={State_results_view.results.session}
            props={{
                bounds: Bounds(
                    label_x,
                    button_y + button_height + Scale(2n),
                    label_width,
                    Scale(20n)
                ),
                text: name,
                size: FitFont(name, label_width, Scale(12n), Scale(8n)),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone,
                disabled: !selected,
                strong: nativeSlice(strong, 0n, selected ? 1n : 0n)
            }}
        />;
    }
}

export function Metrics(x: s32, y: s32, width: s32, best: s32, average: s32): void {
    let titles: [string, string, string] = [
        Locale("results_metric_rounds"),
        Locale("results_metric_best"),
        Locale("results_metric_average")
    ];
    let values: [string, string, string] = [
        RoundCountLabel(),
        Number("results_metric_seconds", best),
        Number("results_metric_seconds", average)
    ];
    let count: s32 = State_results_view.results.round_count <= 1n ? 2n : 3n;
    let gap = Scale(8n);
    let cell_width = (width - gap * (count - 1n)) / count;
    for (let index = s32(0n); index < count; index += s32(1)) {
        let cell_x = x + index * (cell_width + gap);
        let actual = index === count - 1n ? x + width - cell_x : cell_width;
        Card(cell_x, y, actual, Scale(78n));
        <Shape
            session={State_results_view.results.session}
            props={{
                start: { x: float32(cell_x + Scale(14n)), y: float32(y + Scale(12n)) },
                end: { x: float32(cell_x + actual - Scale(14n)), y: float32(y + Scale(12n)) },
                color: Alpha(Accent(), index === 1n ? 0.72 : 0.34)
            }}
        />;
        Label(
            nativeAt(titles, index),
            cell_x + Scale(5n),
            y + Scale(18n),
            actual - Scale(10n),
            Scale(22n),
            FitFont(nativeAt(titles, index), actual - Scale(12n), Scale(17n), Scale(12n)),
            TextAlign.TextAlignCenter
        );
        Label(
            nativeAt(values, index),
            cell_x + Scale(5n),
            y + Scale(38n),
            actual - Scale(10n),
            Scale(34n),
            FitFont(nativeAt(values, index), actual - Scale(12n), Scale(28n), Scale(20n)),
            TextAlign.TextAlignCenter
        );
    }
}

export function Chart(x: s32, y: s32, width: s32, best: s32): void {
    let chart_x = x + Scale(34n);
    let chart_y = y + Scale(72n);
    let chart_width = width - Scale(68n);
    let chart_height = Scale(112n);
    let baseline = chart_y + chart_height;
    let top = ((best + 19n) / 20n) * 20n;
    if (top < 20n) {
        top = 20n;
    }
    let step = (State_results_view.results.round_count + 5n) / 6n;
    if (step < 1n) {
        step = 1n;
    }
    let accent = Accent();
    Card(x, y, width, ChartHeight());
    if (State_results_view.results.round_count <= 1n) {
        let glow: Vector2 = { x: float32(x + width / 2n), y: float32(y + Scale(91n)) };
        NativeShape.Circle(State_results_view.results.session, {
            center: glow,
            radius: float32(Scale(62n)),
            fill: Alpha(accent, 0.18),
            edge: Alpha(State_results_view.results.surface_color, 0.0),
            has_edge: true
        });
        NativeShape.Ring(State_results_view.results.session, {
            center: glow,
            inner_radius: float32(Scale(46n)),
            outer_radius: float32(Scale(48n)),
            end_angle: 360.0,
            color: Alpha(accent, 0.7)
        });
    }
    Label(
        Locale("round_times_title"),
        x + Scale(18n),
        y + Scale(10n),
        width - Scale(36n),
        Scale(32n),
        Scale(18n),
        TextAlign.TextAlignStart
    );
    if (State_results_view.results.round_count <= 1n) {
        let value =
            State_results_view.results.round_count === 1n
                ? nativeAt(State_results_view.results_rounds, 0n)
                : 0n;
        if (value < 0n) {
            value = 0n;
        }
        let detail = Number("results_rounds", 0n);
        if (State_results_view.results.round_count === 1n) {
            detail = Filled(Locale("round_result_label"), 1n, value, EmptyString());
        }
        Label(
            Number("results_metric_seconds", value),
            x + Scale(45n),
            y + Scale(57n),
            width - Scale(90n),
            Scale(55n),
            Scale(38n),
            TextAlign.TextAlignCenter
        );
        Label(
            detail,
            x + Scale(20n),
            y + Scale(127n),
            width - Scale(40n),
            Scale(25n),
            Scale(14n),
            TextAlign.TextAlignCenter
        );
        return;
    }
    for (let row = s32(0n); row <= 2n; row += s32(1)) {
        let guide = float32(chart_y + (row * chart_height) / 2n);
        <Shape
            session={State_results_view.results.session}
            props={{
                start: { x: float32(chart_x), y: guide },
                end: { x: float32(chart_x + chart_width), y: guide },
                color: Alpha(State_results_view.results.border_color, 0.55)
            }}
        />;
    }
    for (let index = s32(0n); index < State_results_view.results.round_count; index += s32(1)) {
        let point_x = ChartX(index, chart_x, chart_width);
        let point: Vector2 = {
            x: float32(point_x),
            y: float32(ChartY(index, baseline, chart_height, top))
        };
        <Shape
            session={State_results_view.results.session}
            props={{
                start: point,
                end: { x: float32(point_x), y: float32(baseline) },
                color: Alpha(accent, 0.18)
            }}
        />;
        if (index > 0n) {
            <Shape
                session={State_results_view.results.session}
                props={{
                    start: {
                        x: float32(ChartX(index - 1n, chart_x, chart_width)),
                        y: float32(ChartY(index - 1n, baseline, chart_height, top))
                    },
                    end: point,
                    thickness: float32(Scale(3n)),
                    color: accent
                }}
            />;
        }
        NativeShape.Circle(State_results_view.results.session, {
            center: point,
            radius: float32(Scale(5n)),
            fill: State_results_view.results.text_color
        });
    }
    for (let index = s32(0n); index < State_results_view.results.round_count; index += s32(1)) {
        if (index % step === 0n || index === State_results_view.results.round_count - 1n) {
            let value = nativeAt(State_results_view.results_rounds, index);
            if (value < 0n) {
                value = 0n;
            }
            let point_x = ChartX(index, chart_x, chart_width);
            let point_y = ChartY(index, baseline, chart_height, top);
            Label(
                Number("results_metric_seconds", value),
                point_x - Scale(25n),
                point_y - Scale(29n),
                Scale(50n),
                Scale(22n),
                Scale(14n),
                TextAlign.TextAlignCenter
            );
            Label(
                ChartRoundLabel(index),
                point_x - Scale(15n),
                baseline + Scale(7n),
                Scale(30n),
                Scale(20n),
                Scale(12n),
                TextAlign.TextAlignCenter
            );
        }
    }
}

export function RoundList(x: s32, y: s32, width: s32): void {
    let rows = (State_results_view.results.round_count + 1n) / 2n;
    let gap = Scale(8n);
    let padding = Scale(14n);
    let cell_width = (width - padding * 2n - gap) / 2n;
    Card(x, y, width, Scale(50n) + rows * Scale(40n));
    Label(
        Locale("round_times_title"),
        x + padding,
        y + Scale(8n),
        width - padding * 2n,
        Scale(30n),
        Scale(18n),
        TextAlign.TextAlignStart
    );
    for (let index = s32(0n); index < State_results_view.results.round_count; index += s32(1)) {
        let cell_x = x + padding + (index % 2n) * (cell_width + gap);
        let cell_y = y + Scale(42n) + (index / 2n) * Scale(40n);
        let label = Filled(
            Locale("round_result_label"),
            index + 1n,
            nativeAt(State_results_view.results_rounds, index),
            EmptyString()
        );
        <Box
            session={State_results_view.results.session}
            props={{
                bounds: Bounds(cell_x, cell_y, cell_width, Scale(32n)),
                fill: Alpha(State_results_view.results.link_color, 0.08),
                radius: Corner(0.16, cell_width, Scale(32n))
            }}
        />;
        Label(
            label,
            cell_x + Scale(7n),
            cell_y,
            cell_width - Scale(14n),
            Scale(32n),
            FitFont(label, cell_width - Scale(14n), Scale(14n), Scale(10n)),
            TextAlign.TextAlignStart
        );
    }
}

export function OtherSummary(x: s32, y: s32, width: s32): void {
    let lines = NewLines();
    let count: s32 = s32(0n);
    let activity = State_results_view.results.activity;
    if (
        activity === s32(ExerciseType.EXERCISE_MEDITATION) ||
        activity === s32(ExerciseType.EXERCISE_PATTERNS) ||
        activity === s32(ExerciseType.EXERCISE_TAI_CHI) ||
        activity === s32(ExerciseType.EXERCISE_ASTRAL_PROJECTION) ||
        activity === s32(ExerciseType.EXERCISE_WORKOUT)
    ) {
        nativeSet(
            lines,
            count,
            Filled(Locale("results_duration"), 0n, 0n, Duration(State_results_view.results.primary))
        );
        count = count + 1n;
        if (
            activity === s32(ExerciseType.EXERCISE_PATTERNS) &&
            State_results_view.results.detail.count > 0n
        ) {
            nativeSet(
                lines,
                count,
                Filled(Locale("results_pattern"), 0n, 0n, State_results_view.results.detail)
            );
            count = count + 1n;
        }
        if (
            activity === s32(ExerciseType.EXERCISE_PATTERNS) &&
            State_results_view.results.secondary > 0n
        ) {
            nativeSet(lines, count, Number("results_cycles", State_results_view.results.secondary));
            count = count + 1n;
        }
    } else {
        nativeSet(lines, count, Number("results_repetitions", State_results_view.results.primary));
        count = count + 1n;
    }
    Card(x, y, width, Scale(50n) + count * Scale(38n));
    for (let index = s32(0n); index < count; index += s32(1)) {
        if (index > 0n) {
            let rule = float32(y + Scale(30n + index * 38n));
            <Shape
                session={State_results_view.results.session}
                props={{
                    start: { x: float32(x + Scale(16n)), y: rule },
                    end: { x: float32(x + width - Scale(16n)), y: rule },
                    color: Alpha(State_results_view.results.border_color, 0.7)
                }}
            />;
        }
        Label(
            nativeAt(lines, index),
            x + Scale(18n),
            y + Scale(30n) + index * Scale(38n),
            width - Scale(36n),
            Scale(38n),
            Scale(17n),
            TextAlign.TextAlignStart
        );
    }
}

export function Status(x: s32, y: s32, width: s32): void {
    let key = "results_unsaved_status";
    let icon = State_results_view.results.link_color;
    if (State_results_view.results.write_failed) {
        key = "results_write_failed";
        icon = { r: 226n, g: 83n, b: 78n, a: 255n };
    } else if (State_results_view.results.saved) {
        key = "results_saved_status";
        icon = { r: 108n, g: 199n, b: 145n, a: 255n };
    }
    let status = Locale(key);
    Card(x, y, width, Scale(50n));
    <Box
        session={State_results_view.results.session}
        props={{
            bounds: Bounds(x, y, width, Scale(50n)),
            fill: Alpha(icon, 0.07),
            border: Alpha(icon, 0.34),
            radius: Corner(0.12, width, Scale(50n))
        }}
    />;
    let center: Vector2 = { x: float32(x + Scale(29n)), y: float32(y + Scale(25n)) };
    NativeShape.Circle(State_results_view.results.session, {
        center: center,
        radius: float32(Scale(12n)),
        fill: Alpha(icon, 0.25)
    });
    NativeShape.Circle(State_results_view.results.session, {
        center: center,
        radius: float32(Scale(5n)),
        fill: icon
    });
    Label(
        status,
        x + Scale(52n),
        y + Scale(7n),
        width - Scale(68n),
        Scale(36n),
        FitFont(status, width - Scale(68n), Scale(16n), Scale(12n)),
        TextAlign.TextAlignStart
    );
}

export function HabitOffer(x: s32, y: s32, width: s32): void {
    let padding = Scale(16n);
    let inner = width - padding * 2n;
    if (State_results_view.results.habit_offer === PRACTICE_HABIT_OFFER_ADDED) {
        let added = Locale("results_habit_added");
        let icon: Color = { r: 108n, g: 199n, b: 145n, a: 255n };
        Card(x, y, width, Scale(50n));
        let center: Vector2 = { x: float32(x + Scale(29n)), y: float32(y + Scale(25n)) };
        NativeShape.Circle(State_results_view.results.session, {
            center: center,
            radius: float32(Scale(12n)),
            fill: Alpha(icon, 0.25)
        });
        NativeShape.Circle(State_results_view.results.session, {
            center: center,
            radius: float32(Scale(5n)),
            fill: icon
        });
        Label(
            added,
            x + Scale(52n),
            y + Scale(7n),
            width - Scale(68n),
            Scale(36n),
            FitFont(added, width - Scale(68n), Scale(16n), Scale(12n)),
            TextAlign.TextAlignStart
        );
        return;
    }
    let title = Filled(Locale("results_habit_offer"), 0n, 0n, State_results_view.results.name);
    let hint = Locale("results_habit_offer_hint");
    Card(x, y, width, Scale(130n));
    Label(
        title,
        x + padding,
        y + Scale(10n),
        inner,
        Scale(30n),
        FitFont(title, inner, Scale(18n), Scale(13n)),
        TextAlign.TextAlignStart
    );
    <Text
        session={State_results_view.results.session}
        props={{
            bounds: Bounds(x + padding, y + Scale(40n), inner, Scale(24n)),
            text: hint,
            size: FitFont(hint, inner, Scale(14n), Scale(11n)),
            align: TextAlign.TextAlignStart,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone,
            disabled: true
        }}
    />;
    let gap = Scale(10n);
    let button_width = (inner - gap) / 2n;
    let button_y = y + Scale(76n);
    if (
        Button({
            session: State_results_view.results.session,
            props: {
                bounds: Bounds(x + padding, button_y, button_width, Scale(40n)),
                label: Locale("results_habit_not_now"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        State_results_view.results.action = PRACTICE_RESULTS_SKIP_HABIT;
    }
    if (
        Button({
            session: State_results_view.results.session,
            props: {
                bounds: Bounds(
                    x + padding + button_width + gap,
                    button_y,
                    inner - button_width - gap,
                    Scale(40n)
                ),
                label: Locale("results_habit_add"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        })
    ) {
        State_results_view.results.action = PRACTICE_RESULTS_ADD_HABIT;
    }
}

export function Results(): void {
    Rounds();
    let x = Scale(16n);
    let width = State_results_view.results.view_width - Scale(16n) * 2n;
    if (width > Scale(600n)) {
        x = x + (width - Scale(600n)) / 2n;
        width = Scale(600n);
    }
    let button_height = Scale(48n);
    let gap = Scale(12n);
    let button_y = State_results_view.results.view_height - Scale(20n) - button_height;
    if (button_y < Scale(200n)) {
        button_y = State_results_view.results.view_height - button_height;
    }
    let best: s32 = s32(0n);
    let average: s32 = s32(0n);
    if (State_results_view.results.activity === s32(ExerciseType.EXERCISE_WIM_HOF)) {
        RoundStats(nativeRef(best), nativeRef(average));
    }
    let scrolled = NativeScroll.Draw(State_results_view.results.session, {
        key: NativeLayout.KeyHash("inbe/screens/session_results/scroll/1"),
        bounds: Bounds(0n, 0n, State_results_view.results.view_width, button_y - Scale(12n)),
        content_height: ContentHeight(),
        scroll_offset: State_results_view.results.scroll
    });
    State_results_view.results.scroll = scrolled.scroll_offset;
    if (scrolled.opened) {
        Content(x, width, s32(scrolled.content.y), best, average);
        End(State_results_view.results.session);
    }
    if (State_results_view.results.saved) {
        let button_width = (width - gap) / 2n;
        if (
            Button({
                session: State_results_view.results.session,
                props: {
                    bounds: Bounds(x, button_y, button_width, button_height),
                    label: Locale("discard_button"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }
            })
        ) {
            State_results_view.results.action = PRACTICE_RESULTS_DISCARD;
        }
        if (
            Button({
                session: State_results_view.results.session,
                props: {
                    bounds: Bounds(
                        x + button_width + gap,
                        button_y,
                        width - button_width - gap,
                        button_height
                    ),
                    label: Locale("done_button"),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }
            })
        ) {
            State_results_view.results.action = PRACTICE_RESULTS_DONE;
        }
    } else if (
        Button({
            session: State_results_view.results.session,
            props: {
                bounds: Bounds(x, button_y, width, button_height),
                label: Locale("done_button"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        })
    ) {
        State_results_view.results.action = PRACTICE_RESULTS_DONE;
    }
}
