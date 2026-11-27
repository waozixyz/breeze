// A habit's statistics: its streaks and its last 30 days, a span habit's
// lengths and when its spans started and ended, the moods after its
// practices, its Wim Hof rounds, the weekdays it is done on, its practice
// time or best streak, what each question's answers add up to with a chart
// of the last 30 days, and its latest changes. The host counts the figures
// from the habit's days and entries; the page lays them out and draws them.
import * as Model from "habit_stats_view";
import {
    Alpha,
    TrendDetail,
    MoodAverageLabel,
    PercentLabel,
    TimeRangeLabel,
    AnswerHeight,
    AnswersHeight,
    Bounds,
    ChangeRowHeight,
    ChangeRowsHeight,
    ContentHeight,
    DateText,
    DayCountText,
    DecimalText,
    Filled,
    HabitTrendLegendColumns,
    HabitsTrendsHeight,
    Locale,
    MetricValueText,
    MoodColor,
    MoodPanelHeight,
    NewDayPoints,
    NewDayTotals,
    NewFirstX,
    NewLastX,
    NewSeen,
    Number,
    OnTargetText,
    PointBand,
    ReadHabitsStatsChangeHost,
    ReadHabitsStatsChartHost,
    ReadHabitsStatsHoldHost,
    ReadHabitsStatsHost,
    ReadHabitsStatsPointHost,
    ReadHabitsStatsRecentHost,
    STATS_ANSWER_ROW,
    STATS_BACK_SHAPE,
    STATS_CARD_GAP,
    STATS_CARD_PADDING,
    STATS_CARD_RADIUS,
    STATS_CHART_HEIGHT,
    STATS_CONTENT_MAX_WIDTH,
    STATS_DAYS,
    STATS_FIGURE_HEIGHT,
    STATS_HOLD_GRAPH_HEIGHT,
    STATS_HOLD_MAX,
    STATS_MOOD_BARS_HEIGHT,
    STATS_POINT_MAX,
    STATS_SECTION_GAP,
    STATS_TREND_HEIGHT,
    STATS_TREND_LEGEND_HEIGHT,
    SameBand,
    Scale,
    SectionFont,
    SectionTitleHeight,
    ShownAnswers,
    SpanHeight,
    SpanText,
    Strong,
    TimeText,
    TrendDate,
    TrendDistance,
    ValueText,
    Width,
    WriteHabitsStatsHost
} from "habit_stats_view";
import {
    HABIT_ANSWER_NUMBER,
    HABIT_ANSWER_TEXT,
    HABIT_ANSWER_TIME,
    HABIT_ANSWER_YES_NO
} from "habit_types";
import { HABITS_STATS_BACK, HABITS_STATS_NONE, HabitsMessage } from "habits_types";
import { HabitsStatsChart, HabitsStatsPoint } from "habits_ui_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color, LightenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import * as NativeLayout from "kryon/layout";
import { SamplePointer } from "kryon/pointer_input";
import * as NativeScroll from "kryon/scroll";
import { SemanticKind } from "kryon/semantic";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Shape } from "kryon/tsx/shape";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { BandChart } from "plot/band_chart";

function Card(x: s32, y: s32, width: s32, height: s32): void {
    const stats_state = Model.CurrentStatistics();
    <Box
        session={stats_state.session}
        props={{
            bounds: Bounds(x, y, width, height),
            fill: stats_state.card_fill,
            border: stats_state.card_border,
            radius: float32(Scale(STATS_CARD_RADIUS))
        }}
    />;
}

function Fill(bounds: Rectangle, radius: float32, color: Color): void {
    const stats_state = Model.CurrentStatistics();
    <Box session={stats_state.session} props={{ bounds: bounds, fill: color, radius: radius }} />;
}

// A line of a chart, from one end to the other, one pixel wide.
function ChartLine(x1: s32, y1: s32, x2: s32, y2: s32, color: Color): void {
    const stats_state = Model.CurrentStatistics();
    <Shape
        session={stats_state.session}
        props={{
            start: { x: float32(x1), y: float32(y1) },
            end: { x: float32(x2), y: float32(y2) },
            color: color
        }}
    />;
}

// How often a written question was answered, with its latest answers below
// on the same card: each answer's day muted beside it.
function TextAnswers(
    chart_index: s32,
    chart: HabitsStatsChart,
    answered: string,
    x: s32,
    y: s32,
    width: s32
): void {
    const stats_state = Model.CurrentStatistics();
    let row_height = Scale(STATS_ANSWER_ROW);
    FigureCard(
        Bounds(x, y, width, Scale(STATS_FIGURE_HEIGHT) + chart.recent_count * row_height),
        Locale("habit_stats_answered"),
        answered
    );
    let inset = Scale(5n) + Scale(STATS_CARD_PADDING);
    let row_x = x + inset;
    let row_width = width - inset - Scale(STATS_CARD_PADDING);
    let date_width = Width("0000-00-00", stats_state.small_font) + Scale(20n);
    let row_y = y + Scale(STATS_FIGURE_HEIGHT);
    let index = s32(0n);
    while (index < chart.recent_count) {
        let recent = ReadHabitsStatsRecentHost(chart_index, index);
        Fill(Bounds(row_x, row_y, row_width, Scale(1n)), 0.0, Alpha(stats_state.text_color, 0.1));
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(row_x, row_y, date_width, row_height),
                text: DateText(recent.day),
                size: stats_state.small_font,
                class_name: stats_state.muted_class,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(row_x + date_width, row_y, row_width - date_width, row_height),
                text: recent.text,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
        row_y += row_height;
        index += 1n;
    }
}

function Answers(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    if (stats_state.question_count <= 0n || ShownAnswers() <= 0n) {
        return;
    }
    y += SectionTitle(Locale("habit_stats_answers_title"), x, y, width) + Scale(10n);
    for (
        let chart_index = s32(1n);
        chart_index <= stats_state.question_count;
        chart_index += s32(1)
    ) {
        let chart = ReadHabitsStatsChartHost(chart_index);
        if (!chart.shown) {
            continue;
        }
        Answer(chart_index, chart, x, y, width);
        y += AnswerHeight(chart, width);
    }
}

// The habit's latest changes on one card, newest first: each change's day
// and time muted above its line, which wraps.
function Changes(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    if (stats_state.change_count <= 0n) {
        return;
    }
    y += SectionTitle(Locale("habit_changes_title"), x, y, width) + Scale(10n);
    let padding = Scale(STATS_CARD_PADDING);
    Card(x, y, width, ChangeRowsHeight(width) + padding * 2n);
    let row_x = x + padding;
    let row_width = width - padding * 2n;
    let row_y = y + padding;
    for (let index = s32(0n); index < stats_state.change_count; index += s32(1)) {
        let change = ReadHabitsStatsChangeHost(index);
        if (index > 0n) {
            Fill(
                Bounds(row_x, row_y, row_width, Scale(1n)),
                0.0,
                Alpha(stats_state.text_color, 0.1)
            );
        }
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(row_x, row_y + Scale(6n), row_width, Scale(18n)),
                text: change.when,
                size: stats_state.small_font,
                class_name: stats_state.muted_class,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
        let row_height = ChangeRowHeight(change.line, row_width);
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(row_x, row_y + Scale(28n), row_width, row_height - Scale(36n)),
                text: change.line,
                size: stats_state.font,
                wrap: NativeText.Wrap.TextWrapAuto,
                line_gap: Scale(6n)
            }}
        />;
        row_y += row_height;
    }
}

// A daily completion series, oldest to newest, with zero days retained.
// The same chart draws one habit and the whole collection.
function CompletionTrend(chart_index: s32, x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let chart = ReadHabitsStatsChartHost(chart_index);
    let height = Scale(STATS_TREND_HEIGHT);
    Card(x, y, width, height);
    let left = x + Scale(32n);
    let right = x + width - Scale(14n);
    let top = y + Scale(18n);
    let bottom = y + height - Scale(52n);
    let highest = chart.highest;
    if (highest < 1n) {
        highest = 1n;
    }
    for (let grid = s32(0n); grid <= 2n; grid += s32(1)) {
        let grid_y = top + ((bottom - top) * grid) / 2n;
        ChartLine(left, grid_y, right, grid_y, Alpha(stats_state.text_color, 0.12));
    }
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(x + Scale(4n), top - Scale(8n), Scale(24n), Scale(18n)),
            text: Number(s64(highest)),
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(x + Scale(4n), bottom - Scale(8n), Scale(24n), Scale(18n)),
            text: "0",
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    let count = chart.point_count;
    if (count > STATS_DAYS) {
        count = STATS_DAYS;
    }
    let previous_x = left;
    let previous_y = bottom;
    let selected: HabitsStatsPoint = {};
    let first: HabitsStatsPoint = {};
    let last: HabitsStatsPoint = {};
    for (let slot = s32(0n); slot < count; slot += s32(1)) {
        let point = ReadHabitsStatsPointHost(chart_index, slot);
        let point_x = left + ((right - left) * slot) / (STATS_DAYS - 1n);
        let point_y = bottom - ((bottom - top) * point.value) / highest;
        if (slot > 0n) {
            ChartLine(previous_x, previous_y, point_x, point_y, stats_state.color);
        }
        let dot = Scale(4n);
        Fill(
            Bounds(point_x - dot / 2n, point_y - dot / 2n, dot, dot),
            float32(dot) * 0.5,
            stats_state.color
        );
        if (
            (
                <Button
                    session={stats_state.session}
                    props={{
                        id: 6100000n + -chart_index * STATS_DAYS + slot,
                        bounds: Bounds(
                            point_x - Scale(8n),
                            point_y - Scale(10n),
                            Scale(16n),
                            Scale(20n)
                        ),
                        label: point.label,
                        invisible: true,
                        disabled: stats_state.modal_active
                    }}
                />
            )
        ) {
            Model.trend_selected_chart = chart_index;
            Model.trend_selected_slot = slot;
        }
        if (slot === 0n) {
            first = point;
        }
        last = point;
        if (slot === Model.trend_selected_slot) {
            selected = point;
        }
        previous_x = point_x;
        previous_y = point_y;
    }
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(left, bottom + Scale(6n), (right - left) / 2n, Scale(18n)),
            text: TrendDate(first.label),
            size: stats_state.small_font,
            class_name: stats_state.muted_class
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(
                left + (right - left) / 2n,
                bottom + Scale(6n),
                (right - left) / 2n,
                Scale(18n)
            ),
            text: TrendDate(last.label),
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    if (Model.trend_selected_chart !== chart_index) {
        selected = last;
    }
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(left, bottom + Scale(28n), right - left, Scale(20n)),
            text: selected.label,
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
}

// Every series shares dates, but uses its own measured minimum and maximum.
// No numeric y axis is shown until a line or its legend is selected.
function CompletionTrends(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    Card(x, y, width, HabitsTrendsHeight(width));
    let left = x + Scale(78n);
    let right = x + width - Scale(14n);
    let top = y + Scale(18n);
    let bottom = y + Scale(STATS_TREND_HEIGHT - 52n);
    let plot_width = right - left;
    if (plot_width <= 0n || stats_state.trend_count <= 0n) {
        return;
    }
    for (let grid = s32(0n); grid <= 2n; grid += s32(1)) {
        let grid_y = top + ((bottom - top) * grid) / 2n;
        ChartLine(left, grid_y, right, grid_y, Alpha(stats_state.text_color, 0.12));
    }
    if (Model.trend_selected_habit >= stats_state.trend_count) {
        Model.trend_selected_habit = -1n;
    }
    let selected = Model.trend_selected_habit;
    let pointer = SamplePointer();
    let choose = (
        <Button
            session={stats_state.session}
            props={{
                id: 6100000n,
                bounds: Bounds(
                    left - Scale(8n),
                    top - Scale(8n),
                    plot_width + Scale(16n),
                    bottom - top + Scale(16n)
                ),
                label: Locale("habit_stats_answers_title"),
                invisible: true,
                disabled: stats_state.modal_active
            }}
        />
    );
    let nearest_distance = float32(Scale(14n) * Scale(14n));
    let nearest_series: s32 = -1n;
    let nearest_point: s32 = -1n;
    let columns = HabitTrendLegendColumns(width);
    let legend_x = x + Scale(10n);
    let legend_y = y + Scale(STATS_TREND_HEIGHT + 60n);
    let legend_width = (width - Scale(20n)) / columns;
    let first = TrendDate(ReadHabitsStatsPointHost(-1n, 0n).label);
    let last = TrendDate(ReadHabitsStatsPointHost(-1n, STATS_DAYS - 1n).label);
    let detail: string = "";
    for (let offset = s32(1n); offset <= stats_state.trend_count; offset += s32(1)) {
        let index = (selected + offset) % stats_state.trend_count;
        let chart_index = -2n - index;
        let chart = ReadHabitsStatsChartHost(chart_index);
        let entry_x = legend_x + (index % columns) * legend_width;
        let entry_y = legend_y + (index / columns) * Scale(STATS_TREND_LEGEND_HEIGHT);
        let bounds = Bounds(
            entry_x,
            entry_y,
            legend_width - Scale(4n),
            Scale(STATS_TREND_LEGEND_HEIGHT)
        );
        if (index === selected) {
            Fill(bounds, float32(Scale(8n)), Alpha(chart.color, 0.16));
        }
        if (
            (
                <Button
                    session={stats_state.session}
                    props={{
                        id: 6101000n + index,
                        bounds: bounds,
                        label: chart.title,
                        invisible: true,
                        selected: index === selected,
                        disabled: stats_state.modal_active
                    }}
                />
            )
        ) {
            Model.trend_selected_habit = index === selected ? -1n : index;
            Model.trend_selected_slot = chart.point_count - 1n;
        }
        let chip_size = Scale(8n);
        Fill(
            Bounds(entry_x + Scale(8n), entry_y + Scale(18n), chip_size, chip_size),
            float32(chip_size) * 0.5,
            chart.color
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(
                    entry_x + Scale(22n),
                    entry_y,
                    legend_width - Scale(32n),
                    Scale(STATS_TREND_LEGEND_HEIGHT)
                ),
                text: chart.title,
                size: stats_state.small_font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
        if (index === selected && chart.point_count > 0n) {
            <Text
                session={stats_state.session}
                props={{
                    bounds: Bounds(
                        x + Scale(4n),
                        (chart.lowest === chart.highest ? (top + bottom) / 2n : top) - Scale(8n),
                        Scale(66n),
                        Scale(18n)
                    ),
                    text: MetricValueText(chart.answer_type, chart.highest),
                    size: stats_state.small_font,
                    class_name: stats_state.muted_class,
                    align: TextAlign.TextAlignEnd
                }}
            />;
            if (chart.lowest !== chart.highest) {
                <Text
                    session={stats_state.session}
                    props={{
                        bounds: Bounds(x + Scale(4n), bottom - Scale(8n), Scale(66n), Scale(18n)),
                        text: MetricValueText(chart.answer_type, chart.lowest),
                        size: stats_state.small_font,
                        class_name: stats_state.muted_class,
                        align: TextAlign.TextAlignEnd
                    }}
                />;
            }
        }
        let count = chart.point_count;
        if (count > STATS_POINT_MAX) {
            count = STATS_POINT_MAX;
        }
        let previous_x = left;
        let previous_y = bottom;
        for (let point_index = s32(0n); point_index < count; point_index += s32(1)) {
            let point = ReadHabitsStatsPointHost(chart_index, point_index);
            // Day slots plus recorded time preserve multiple sessions per day.
            let elapsed = s64(point.slot) * 86400n + point.time;
            let point_x = left + s32((s64(plot_width) * elapsed) / (30n * 86400n - 1n));
            let point_y = top + (bottom - top) / 2n;
            let range = s64(chart.highest) - chart.lowest;
            if (range > 0n) {
                point_y =
                    bottom - s32((s64(bottom - top) * (s64(point.value) - chart.lowest)) / range);
            }
            if (point_index > 0n) {
                ChartLine(previous_x, previous_y, point_x, point_y, chart.color);
            }
            let dot = Scale(
                index === selected && point_index === Model.trend_selected_slot ? 8n : 4n
            );
            Fill(
                Bounds(point_x - dot / 2n, point_y - dot / 2n, dot, dot),
                float32(dot) * 0.5,
                chart.color
            );
            let distance = TrendDistance(pointer.x, pointer.y, point_x, point_y, point_x, point_y);
            if (distance <= nearest_distance) {
                nearest_distance = distance;
                nearest_series = index;
                nearest_point = point_index;
            }
            if (point_index > 0n) {
                let segment_distance = TrendDistance(
                    pointer.x,
                    pointer.y,
                    previous_x,
                    previous_y,
                    point_x,
                    point_y
                );
                if (segment_distance < nearest_distance) {
                    nearest_distance = segment_distance;
                    nearest_series = index;
                    let before = TrendDistance(
                        pointer.x,
                        pointer.y,
                        previous_x,
                        previous_y,
                        previous_x,
                        previous_y
                    );
                    nearest_point = before < distance ? point_index - 1n : point_index;
                }
            }
            if (index === selected && point_index === Model.trend_selected_slot) {
                detail = TrendDetail(chart.title, point.label);
            }
            previous_x = point_x;
            previous_y = point_y;
        }
    }
    if (choose && nearest_series >= 0n) {
        Model.trend_selected_habit = nearest_series;
        Model.trend_selected_slot = nearest_point;
    }
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(left, bottom + Scale(6n), plot_width / 2n, Scale(18n)),
            text: first,
            size: stats_state.small_font,
            class_name: stats_state.muted_class
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(left + plot_width / 2n, bottom + Scale(6n), plot_width / 2n, Scale(18n)),
            text: last,
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(x + Scale(12n), bottom + Scale(28n), width - Scale(24n), Scale(76n)),
            text: detail,
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
}

// A bar of a chart, its top a little rounded.
function Bar(x: s32, y: s32, width: s32, height: s32, color: Color): void {
    let radius = Scale(3n);
    if (radius * 2n > width) {
        radius = width / 2n;
    }
    Fill(Bounds(x, y, width, height), float32(radius), color);
}

// A figure on a card: its label muted above it and the figure strong, with
// the card's edge in the habit's colour.
function FigureCard(bounds: Rectangle, label: string, value: string): void {
    const stats_state = Model.CurrentStatistics();
    let radius = float32(Scale(STATS_CARD_RADIUS));
    let bar = float32(Scale(5n));
    Fill(bounds, radius, stats_state.color);
    <Box
        session={stats_state.session}
        props={{
            bounds: {
                x: bounds.x + bar,
                y: bounds.y,
                width: bounds.width - bar,
                height: bounds.height
            },
            fill: stats_state.card_fill,
            radius: radius
        }}
    />;
    <Box
        session={stats_state.session}
        props={{ bounds: bounds, border: stats_state.card_border, radius: radius }}
    />;
    let pad = float32(Scale(STATS_CARD_PADDING));
    let inner = bounds.width - bar - pad * 2.0;
    <Text
        session={stats_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(10n)),
                width: inner,
                height: float32(Scale(22n))
            },
            text: label,
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let font = Scale(NativeText.Text24);
    while (font > Scale(NativeText.Text16) && Width(value, font) > s32(inner)) {
        font -= 1n;
    }
    let strong = Strong(value);
    <Text
        session={stats_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(34n)),
                width: inner,
                height: float32(Scale(32n))
            },
            text: value,
            size: font,
            strong: strong[:],
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

function Figure(x: s32, y: s32, width: s32, label: string, value: string): void {
    FigureCard(Bounds(x, y, width, Scale(STATS_FIGURE_HEIGHT)), label, value);
}

function FigurePair(
    x: s32,
    y: s32,
    width: s32,
    first_label: string,
    first: string,
    second_label: string,
    second: string
): void {
    let gap = Scale(STATS_CARD_GAP);
    let half = (width - gap) / 2n;
    Figure(x, y, half, first_label, first);
    Figure(x + half + gap, y, width - half - gap, second_label, second);
}

// A section's title above its cards: strong and a little larger than the
// text, wrapping onto more lines when it must. Returns its height.
function SectionTitle(title: string, x: s32, y: s32, width: s32): s32 {
    const stats_state = Model.CurrentStatistics();
    let height = SectionTitleHeight(title, width);
    let strong = Strong(title);
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(x, y, width, height),
            text: title,
            size: SectionFont(),
            strong: strong[:],
            semantic_kind: SemanticKind.SemanticHeading,
            heading_level: 2n,
            wrap: NativeText.Wrap.TextWrapAuto,
            line_gap: Scale(3n)
        }}
    />;
    return height;
}

// The mood check-ins: their average and count, and a bar for each mood.
function MoodPanel(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let gap = Scale(STATS_CARD_GAP);
    y += SectionTitle(Locale("habit_stats_mood_title"), x, y, width) + Scale(10n);
    let hundredths = s32(stats_state.mood_average * 100.0);
    const average_label = MoodAverageLabel(hundredths);
    FigurePair(
        x,
        y,
        width,
        Locale("habit_stats_mood_average"),
        average_label,
        Locale("habit_stats_mood_checkins"),
        Number(s64(stats_state.mood_total))
    );
    let bars_height = Scale(STATS_MOOD_BARS_HEIGHT);
    let bars_y = y + Scale(STATS_FIGURE_HEIGHT) + gap;
    Card(x, bars_y, width, bars_height);
    let counts: [s32, s32, s32, s32, s32] = [
        stats_state.mood_1,
        stats_state.mood_2,
        stats_state.mood_3,
        stats_state.mood_4,
        stats_state.mood_5
    ];
    let slot = width / 5n;
    for (let mood = s32(0n); mood <= 4n; mood += s32(1)) {
        let count = counts[mood];
        let bar_height = Scale(3n);
        if (count > 0n && stats_state.mood_total > 0n) {
            bar_height = (count * (bars_height - Scale(30n))) / stats_state.mood_total;
        }
        let bar_x = x + mood * slot + Scale(10n);
        let bar_width = slot - Scale(20n);
        if (bar_width < Scale(4n)) {
            bar_width = Scale(4n);
        }
        let color = MoodColor(mood + 1n);
        if (count <= 0n) {
            color = Alpha(stats_state.text_color, 0.16);
        }
        Bar(bar_x, bars_y + bars_height - bar_height - Scale(22n), bar_width, bar_height, color);
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(bar_x, bars_y + bars_height - Scale(20n), bar_width, Scale(16n)),
                text: Number(s64(mood + 1n)),
                size: NativeText.Text12,
                class_name: stats_state.muted_class,
                align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
}

// The week or the month, as two buttons side by side.
function HoldRange(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let labels: [string, string] = ["1W", "1M"];
    let values: [s32, s32] = [7n, 31n];
    let selected = stats_state.hold_days === 31n ? 1n : 0n;
    let segment = width / 2n;
    for (let index = s32(0n); index <= 1n; index += s32(1)) {
        let segment_x = x + index * segment;
        let segment_width = index === 1n ? x + width - segment_x : segment;
        if (
            (
                <Button
                    session={stats_state.session}
                    props={{
                        id: 24700n + index,
                        bounds: Bounds(segment_x, y, segment_width, Scale(34n)),
                        label: labels[index],
                        tone:
                            index === selected
                                ? ButtonTone.ButtonToneAccent
                                : ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                        selected: index === selected,
                        disabled: stats_state.modal_active
                    }}
                />
            ) &&
            selected !== index
        ) {
            stats_state.hold_days = values[index];
        }
    }
}

// Each round of the last days as a dot at its day, held longer higher,
// with a line through each day's average.
function HoldGraph(x: s32, y: s32, width: s32): void {
    const hold_points = Model.HoldPoints();
    const stats_state = Model.CurrentStatistics();
    let days: s32 = stats_state.hold_days === 31n ? 31n : 7n;
    let graph_height = Scale(STATS_HOLD_GRAPH_HEIGHT);
    let axis_width = Scale(48n);
    let plot_x = x + axis_width;
    let plot_y = y + Scale(8n);
    let plot_width = width - axis_width - Scale(10n);
    let plot_height = graph_height - Scale(36n);
    Card(x, y, width, graph_height);
    let count: s32 = 0n;
    let longest: s32 = 1n;
    let day_points = NewDayPoints();
    let day_totals = NewDayTotals();
    for (let index = s32(0n); index < stats_state.hold_count; index += s32(1)) {
        if (count >= STATS_HOLD_MAX) {
            break;
        }
        let hold = ReadHabitsStatsHoldHost(index);
        if (hold.days_ago < 0n || hold.days_ago >= days) {
            continue;
        }
        let slot = days - 1n - hold.days_ago;
        if (hold.seconds > longest) {
            longest = hold.seconds;
        }
        day_points[slot] = day_points[slot] + 1n;
        day_totals[slot] = day_totals[slot] + hold.seconds;
        hold_points[count] = {
            time_key: s64(-hold.days_ago) * 86400n + s64(hold.time),
            round: hold.round,
            slot: slot,
            seconds: hold.seconds
        };
        count += 1n;
    }
    // Oldest first, a session's rounds in order.
    for (let index = s32(1n); index < count; index += s32(1)) {
        let point = hold_points[index];
        let other = index - 1n;
        while (
            other >= 0n &&
            (hold_points[other].time_key > point.time_key ||
                (hold_points[other].time_key === point.time_key &&
                    hold_points[other].round > point.round))
        ) {
            hold_points[other + 1n] = hold_points[other];
            other -= 1n;
        }
        hold_points[other + 1n] = point;
    }
    let grid = Alpha(stats_state.text_color, 0.1);
    for (let day = s32(1n); day < days; day += s32(1)) {
        if (days === 7n || day % 5n === 0n) {
            let line_x = plot_x + (plot_width * day) / days;
            ChartLine(line_x, plot_y, line_x, plot_y + plot_height, grid);
        }
    }
    for (let step = s32(0n); step <= 2n; step += s32(1)) {
        let line_y = plot_y + (plot_height * step) / 2n;
        ChartLine(plot_x, line_y, plot_x + plot_width, line_y, grid);
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(
                    x + Scale(4n),
                    line_y - Scale(8n),
                    axis_width - Scale(4n),
                    Scale(18n)
                ),
                text: Number(s64(longest - (longest * step) / 2n)),
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    ChartLine(
        plot_x,
        plot_y + plot_height,
        plot_x + plot_width,
        plot_y + plot_height,
        Alpha(stats_state.text_color, 0.4)
    );
    let seen = NewSeen();
    let first_x = NewFirstX();
    let last_x = NewLastX();
    for (let day = s32(0n); day < days; day += s32(1)) {
        first_x[day] = -1n;
        last_x[day] = -1n;
    }
    for (let index = s32(0n); index < count; index += s32(1)) {
        let slot = hold_points[index].slot;
        let in_day = day_points[slot] > 0n ? day_points[slot] : 1n;
        let ordinal = seen[slot];
        seen[slot] = seen[slot] + 1n;
        let x0 = plot_x + (plot_width * slot) / days;
        let x1 = plot_x + (plot_width * (slot + 1n)) / days;
        hold_points[index].x = x0 + ((ordinal + 1n) * (x1 - x0)) / (in_day + 1n);
        hold_points[index].y =
            plot_y +
            plot_height -
            (hold_points[index].seconds * (plot_height - Scale(10n))) / longest;
        if (first_x[slot] < 0n || hold_points[index].x < first_x[slot]) {
            first_x[slot] = hold_points[index].x;
        }
        if (last_x[slot] < 0n || hold_points[index].x > last_x[slot]) {
            last_x[slot] = hold_points[index].x;
        }
    }
    let previous_x: s32 = 0n;
    let previous_y: s32 = 0n;
    let has_previous = false;
    for (let day = s32(0n); day < days; day += s32(1)) {
        if (day_points[day] <= 0n) {
            continue;
        }
        let average = day_totals[day] / day_points[day];
        let average_y = plot_y + plot_height - (average * (plot_height - Scale(10n))) / longest;
        if (has_previous) {
            ChartLine(previous_x, previous_y, first_x[day], average_y, stats_state.color);
        }
        ChartLine(first_x[day], average_y, last_x[day], average_y, stats_state.color);
        previous_x = last_x[day];
        previous_y = average_y;
        has_previous = true;
    }
    let dot = Scale(3n);
    for (let index = s32(0n); index < count; index += s32(1)) {
        Fill(
            Bounds(hold_points[index].x - dot, hold_points[index].y - dot, dot * 2n, dot * 2n),
            float32(dot),
            stats_state.color
        );
    }
    if (count <= 0n) {
        let empty = Locale(
            days === 31n ? "habit_stats_no_rounds_month" : "habit_stats_no_rounds_week"
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(x, y + graph_height / 2n - Scale(8n), width, Scale(18n)),
                text: empty,
                align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    for (let day = s32(0n); day < days; day += s32(1)) {
        let days_ago = days - 1n - day;
        if (!(days === 7n || days_ago === 0n || days_ago % 5n === 0n)) {
            continue;
        }
        let label = Locale("statistics_now_label");
        if (days_ago > 0n) {
            label = Filled(Locale("statistics_day_offset_label"), days_ago, 0n);
        }
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(
                    plot_x + (plot_width * day) / days + Scale(2n),
                    y + graph_height - Scale(20n),
                    Scale(48n),
                    Scale(18n)
                ),
                text: label,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
}

// The days oldest to newest: bars from zero for numbers and lengths, dots
// for times. Values that met their goal are in the habit's colour and the
// rest are muted; the good range is shaded as it was each day, so a changed
// goal or a moving average steps. Hovering or tapping a value shows its
// day, value and goal.
function AnswerChart(chart_index: s32, chart: HabitsStatsChart, x: s32, y: s32, width: s32): void {
    const chart_bands = Model.ChartBands();
    const chart_points = Model.ChartPoints();
    const stats_state = Model.CurrentStatistics();
    let chart_height = Scale(STATS_CHART_HEIGHT);
    Card(x, y, width, chart_height);
    if (chart.point_count <= 0n) {
        return;
    }
    let count = chart.point_count;
    if (count > STATS_POINT_MAX) {
        count = STATS_POINT_MAX;
    }
    let band_count: s32 = 0n;
    let is_time = chart.answer_type === HABIT_ANSWER_TIME;
    let low: float32 = 0.0;
    if (is_time) {
        low = float32(chart.lowest);
    }
    let high = float32(chart.highest);
    for (let index = s32(0n); index < count; index += s32(1)) {
        let point = ReadHabitsStatsPointHost(chart_index, index);
        chart_points[index] = {
            slot: point.slot,
            value: float32(point.value),
            good: point.good,
            label: point.label
        };
        let band = PointBand(chart, point);
        // Keep the good range in view.
        if (band.has_low && band.low > high) {
            high = band.low;
        }
        if (band.has_high && band.high > high) {
            high = band.high;
        }
        if (is_time && band.has_low && band.low < low) {
            low = band.low;
        }
        if (is_time && band.has_high && band.high < low) {
            low = band.high;
        }
        if (band_count === 0n) {
            band.from = 0n;
            chart_bands[0n] = band;
            band_count = 1n;
        } else if (!SameBand(chart_bands[band_count - 1n], band)) {
            if (chart_bands[band_count - 1n].from === band.from) {
                chart_bands[band_count - 1n] = band;
            } else {
                chart_bands[band_count] = band;
                band_count += 1n;
            }
        }
    }
    if (is_time && high - low < 60.0) {
        low -= 30.0;
        high += 30.0;
    }
    if (high <= low) {
        high = low + 1.0;
    }
    let inset = Scale(10n);
    BandChart(
        stats_state.session,
        {
            key: NativeLayout.KeyHash("statistics/answer-chart") + u64(chart_index),
            bounds: Bounds(x + inset, y + inset, width - inset * 2n, chart_height - inset * 2n),
            semantic_label: Locale("habit_stats_answers_title"),
            slots: STATS_DAYS,
            min_value: low,
            max_value: high,
            bars: !is_time,
            top_label: ValueText(chart.answer_type, s32(high)),
            bottom_label: ValueText(chart.answer_type, s32(low)),
            font: stats_state.small_font,
            good_color: stats_state.color,
            other_color: Alpha(stats_state.text_color, 0.35),
            band_color: Alpha(stats_state.color, 0.14),
            grid_color: Alpha(stats_state.text_color, 0.15),
            text_color: stats_state.text_color,
            label_fill: LightenColor(stats_state.canvas_color, 6n)
        },
        chart_points[:count],
        chart_bands[:band_count]
    );
}

function Answer(chart_index: s32, chart: HabitsStatsChart, x: s32, y: s32, width: s32): void {
    y += SectionTitle(chart.title, x, y, width) + Scale(10n);
    let first_label = Locale("habit_stats_average");
    let second_label = Locale("habit_stats_total");
    let first = "-";
    let second = "-";
    let answered = Filled("%d/%d", chart.days, STATS_DAYS);
    if (chart.answer_type === HABIT_ANSWER_TEXT) {
        TextAnswers(chart_index, chart, answered, x, y, width);
        return;
    }
    if (chart.answer_type === HABIT_ANSWER_YES_NO) {
        first_label = Locale("habit_answer_yes");
        second_label = Locale("habit_stats_answered");
        second = answered;
        if (chart.answered > 0n) {
            let percent = (chart.yes * 100n + chart.answered / 2n) / chart.answered;
            first = PercentLabel(percent);
        }
    } else if (chart.point_count > 0n) {
        if (chart.answer_type === HABIT_ANSWER_TIME) {
            first = TimeText(s32((chart.average + 50n) / 100n));
            second = TimeRangeLabel(chart.lowest, chart.highest);
            second_label = Locale("habit_stats_time_range");
        } else {
            first = DecimalText(chart.average);
            second = Number(chart.sum);
        }
    }
    // With a goal, the second figure is how many were on target.
    if (chart.judged > 0n) {
        second_label = Locale("habit_stats_on_target");
        second = OnTargetText(chart);
    }
    FigurePair(x, y, width, first_label, first, second_label, second);
    y += Scale(STATS_FIGURE_HEIGHT) + Scale(STATS_CARD_GAP);
    if (chart.answer_type === HABIT_ANSWER_TIME || chart.answer_type === HABIT_ANSWER_NUMBER) {
        AnswerChart(chart_index, chart, x, y, width);
    }
}

// A span habit's average and longest length, or how many were on target
// when its spans are judged, and when they started and ended on average.
function Spans(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let lengths = ReadHabitsStatsChartHost(0n);
    y += SectionTitle(Locale("habit_stats_spans_title"), x, y, width) + Scale(10n);
    let first = "-";
    let second = "-";
    let second_label = Locale("habit_stats_longest");
    if (lengths.point_count > 0n) {
        first = SpanText(s32((lengths.average + 50n) / 100n));
        second = SpanText(lengths.highest);
    }
    if (lengths.judged > 0n) {
        second_label = Locale("habit_stats_on_target");
        second = OnTargetText(lengths);
    }
    FigurePair(x, y, width, Locale("habit_stats_average"), first, second_label, second);
    y += Scale(STATS_FIGURE_HEIGHT) + Scale(STATS_CARD_GAP);
    AnswerChart(0n, lengths, x, y, width);
    y += Scale(STATS_CHART_HEIGHT) + Scale(STATS_CARD_GAP);
    let started = "-";
    let ended = "-";
    if (stats_state.span_start_average >= 0n) {
        started = TimeText(s32((stats_state.span_start_average + 50n) / 100n));
        ended = TimeText(s32((stats_state.span_end_average + 50n) / 100n));
    }
    FigurePair(
        x,
        y,
        width,
        Locale("habit_stats_started"),
        started,
        Locale("habit_stats_ended"),
        ended
    );
}

// Back, then the habit's name, strong, with "Statistics" muted below it.
// Returns the y below it, or -1 when Back was pressed.
function PageHeader(x: s32, y: s32, width: s32): s32 {
    const stats_state = Model.CurrentStatistics();
    let back_label = Locale("back_button");
    let back_width = Width(back_label, stats_state.font) + Scale(48n);
    if (back_width < Scale(88n)) {
        back_width = Scale(88n);
    }
    if (back_width > width / 3n) {
        back_width = width / 3n;
    }
    if (
        (
            <Button
                session={stats_state.session}
                props={{
                    id: 4300n,
                    bounds: Bounds(x, y + Scale(2n), back_width, Scale(42n)),
                    label: back_label,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisOutline,
                    icon_shape: STATS_BACK_SHAPE,
                    fit_content: true,
                    disabled: stats_state.modal_active
                }}
            />
        )
    ) {
        return -1n;
    }
    let title_x = x + back_width + Scale(16n);
    let title_width = width - back_width - Scale(16n);
    let font = Scale(NativeText.Text24);
    if (Width(stats_state.name, font) > title_width) {
        font = Scale(NativeText.Text16);
        if (Width(stats_state.name, font) > title_width) {
            font = Scale(NativeText.Text14);
        }
    }
    let strong = Strong(stats_state.name);
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(title_x, y, title_width, Scale(34n)),
            text: stats_state.name,
            size: font,
            strong: strong[:],
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Bounds(title_x, y + Scale(34n), title_width, Scale(22n)),
            text: Locale("habit_statistics_title"),
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    return y + Scale(68n);
}

function Content(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let gap = Scale(STATS_SECTION_GAP);
    let card_gap = Scale(STATS_CARD_GAP);
    if (stats_state.overview) {
        FigurePair(
            x,
            y,
            width,
            Locale("tab_habits"),
            Number(s64(stats_state.habit_count)),
            Locale("habit_stats_last_30_days"),
            Number(s64(stats_state.last_30_done))
        );
    } else {
        FigurePair(
            x,
            y,
            width,
            Locale("habit_stats_current_streak"),
            DayCountText(stats_state.current_streak),
            Locale("habit_stats_last_30_days"),
            Filled("%d/%d", stats_state.last_30_done, stats_state.last_30_due)
        );
    }
    y += Scale(STATS_FIGURE_HEIGHT) + gap;
    y +=
        SectionTitle(
            Locale(
                stats_state.overview ? "habit_stats_metric_trends" : "habit_stats_daily_completions"
            ),
            x,
            y,
            width
        ) + Scale(10n);
    if (stats_state.overview && stats_state.trend_count > 0n) {
        CompletionTrends(x, y, width);
        return;
    }
    CompletionTrend(-1n, x, y, width);
    y += Scale(STATS_TREND_HEIGHT) + gap;
    if (stats_state.overview) {
        return;
    }
    // A habit that measures spans is about their length: it comes first.
    if (stats_state.span) {
        Spans(x, y, width);
        y += SpanHeight(width);
    }
    if (stats_state.mood_total > 0n) {
        MoodPanel(x, y, width);
        y += MoodPanelHeight(width) + gap;
    }
    if (stats_state.hold_days > 0n) {
        y += SectionTitle(Locale("habit_stats_wim_hof_hold_rounds"), x, y, width) + Scale(10n);
        HoldRange(x, y, Scale(118n));
        y += Scale(42n);
        HoldGraph(x, y, width);
        y += Scale(STATS_HOLD_GRAPH_HEIGHT) + gap;
    }
    y += SectionTitle(Locale("habit_stats_weekday_pattern"), x, y, width) + Scale(10n);
    let chart_height = Scale(STATS_CHART_HEIGHT);
    Card(x, y, width, chart_height);
    let counts: [s32, s32, s32, s32, s32, s32, s32] = [
        stats_state.sunday,
        stats_state.monday,
        stats_state.tuesday,
        stats_state.wednesday,
        stats_state.thursday,
        stats_state.friday,
        stats_state.saturday
    ];
    let most: s32 = 1n;
    for (let day = s32(0n); day <= 6n; day += s32(1)) {
        if (counts[day] > most) {
            most = counts[day];
        }
    }
    let labels: [string, string, string, string, string, string, string] = [
        "S",
        "M",
        "T",
        "W",
        "T",
        "F",
        "S"
    ];
    let inner_x = x + Scale(8n);
    let slot = (width - Scale(16n)) / 7n;
    for (let day = s32(0n); day <= 6n; day += s32(1)) {
        let height = Scale(3n);
        if (counts[day] > 0n) {
            height = (counts[day] * (chart_height - Scale(44n))) / most;
        }
        let bar_x = inner_x + day * slot + Scale(5n);
        let bar_width = slot - Scale(10n);
        if (bar_width < Scale(4n)) {
            bar_width = Scale(4n);
        }
        Bar(
            bar_x,
            y + chart_height - height - Scale(28n),
            bar_width,
            height,
            counts[day] > 0n
                ? LightenColor(stats_state.color, 12n)
                : Alpha(stats_state.text_color, 0.16)
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Bounds(bar_x, y + chart_height - Scale(24n), bar_width, Scale(18n)),
                text: labels[day],
                size: NativeText.Text12,
                class_name: stats_state.muted_class,
                align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    y += chart_height + gap;
    if (stats_state.linked) {
        y += SectionTitle(Locale("habit_stats_practice_time"), x, y, width) + Scale(10n);
        FigurePair(
            x,
            y,
            width,
            Locale("habit_stats_best_hold"),
            stats_state.best_time,
            Locale("habit_stats_total_hold"),
            stats_state.total_time
        );
    } else {
        Figure(
            x,
            y,
            width,
            Locale("habit_stats_best_streak"),
            DayCountText(stats_state.best_streak)
        );
    }
    y += Scale(STATS_FIGURE_HEIGHT) + gap;
    Answers(x, y, width);
    y += AnswersHeight(width);
    Changes(x, y, width);
    card_gap;
}

export function HabitsStatsView(message: HabitsMessage): HabitsMessage {
    const stats_state = Model.CurrentStatistics();
    Model.SetStatistics(ReadHabitsStatsHost());
    stats_state.action = HABITS_STATS_NONE;
    let side = Scale(16n);
    let x = side;
    let width = stats_state.view_width - side * 2n;
    if (width > Scale(STATS_CONTENT_MAX_WIDTH)) {
        x += (width - Scale(STATS_CONTENT_MAX_WIDTH)) / 2n;
        width = Scale(STATS_CONTENT_MAX_WIDTH);
    }
    let top = PageHeader(x, Scale(20n), width);
    if (top < 0n) {
        stats_state.action = HABITS_STATS_BACK;
        WriteHabitsStatsHost(*stats_state);
        message.succeeded = true;
        return message;
    }
    let viewport_height = stats_state.view_height - top - stats_state.bottom - Scale(4n);
    if (viewport_height < 0n) {
        viewport_height = 0n;
    }
    const scrolled = (
        <Scroll
            session={stats_state.session}
            props={{
                key: NativeLayout.KeyHash("inbe/screens/statistics_screen/scroll/1"),
                bounds: Bounds(0n, top + Scale(4n), stats_state.view_width, viewport_height),
                content_height: ContentHeight(width),
                scroll_offset: stats_state.scroll
            }}
            children={(scrolled: NativeScroll.ScrollResult): void => {
                const stats_state = Model.CurrentStatistics();
                stats_state.scroll = scrolled.scroll_offset;
                Content(x, s32(scrolled.content.y) + Scale(8n), width);
            }}
        />
    );
    if (!scrolled.opened) {
        stats_state.scroll = scrolled.scroll_offset;
    }
    WriteHabitsStatsHost(*stats_state);
    message.succeeded = true;
    return message;
}
