import * as Cards from "habit_cards";
import * as Shared from "habit_shared";
// A habit's statistics: its streaks and its last 30 days, a span habit's
// lengths and when its spans started and ended, the moods after its
// practices, its Wim Hof rounds, the weekdays it is done on, its practice
// time or best streak, what each question's answers add up to with a chart
// of the last 30 days, and its latest changes. The host counts the figures
// from the habit's days and entries; the page lays them out and draws them.
import * as Model from "habit_stats_view";
import * as Habit from "habit_types";
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
            bounds: Shared.Bounds(x, y, width, height),
            fill: stats_state.card_fill,
            border: stats_state.card_border,
            radius: float32(Model.Scale(Model.STATS_CARD_RADIUS))
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
    let row_height = Model.Scale(Model.STATS_ANSWER_ROW);
    FigureCard(
        Shared.Bounds(
            x,
            y,
            width,
            Model.Scale(Model.STATS_FIGURE_HEIGHT) + chart.recent_count * row_height
        ),
        Model.Locale("habit_stats_answered"),
        answered
    );
    let inset = Model.Scale(5n) + Model.Scale(Model.STATS_CARD_PADDING);
    let row_x = x + inset;
    let row_width = width - inset - Model.Scale(Model.STATS_CARD_PADDING);
    let date_width = Model.Width("0000-00-00", stats_state.small_font) + Model.Scale(20n);
    let row_y = y + Model.Scale(Model.STATS_FIGURE_HEIGHT);
    let index = s32(0n);
    while (index < chart.recent_count) {
        let recent = Model.ReadHabitsStatsRecentHost(chart_index, index);
        Fill(
            Shared.Bounds(row_x, row_y, row_width, Model.Scale(1n)),
            0.0,
            Shared.Alpha(stats_state.text_color, 0.1)
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(row_x, row_y, date_width, row_height),
                text: Model.DateText(recent.day),
                size: stats_state.small_font,
                class_name: stats_state.muted_class,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    row_x + date_width,
                    row_y,
                    row_width - date_width,
                    row_height
                ),
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
    if (stats_state.question_count <= 0n || Model.ShownAnswers() <= 0n) {
        return;
    }
    y += SectionTitle(Model.Locale("habit_stats_answers_title"), x, y, width) + Model.Scale(10n);
    for (
        let chart_index = s32(1n);
        chart_index <= stats_state.question_count;
        chart_index += s32(1)
    ) {
        let chart = Model.ReadHabitsStatsChartHost(chart_index);
        if (!chart.shown) {
            continue;
        }
        Answer(chart_index, chart, x, y, width);
        y += Model.AnswerHeight(chart, width);
    }
}

// The habit's latest changes on one card, newest first: each change's day
// and time muted above its line, which wraps.
function Changes(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    if (stats_state.change_count <= 0n) {
        return;
    }
    y += SectionTitle(Model.Locale("habit_changes_title"), x, y, width) + Model.Scale(10n);
    let padding = Model.Scale(Model.STATS_CARD_PADDING);
    Card(x, y, width, Model.ChangeRowsHeight(width) + padding * 2n);
    let row_x = x + padding;
    let row_width = width - padding * 2n;
    let row_y = y + padding;
    for (let index = s32(0n); index < stats_state.change_count; index += s32(1)) {
        let change = Model.ReadHabitsStatsChangeHost(index);
        if (index > 0n) {
            Fill(
                Shared.Bounds(row_x, row_y, row_width, Model.Scale(1n)),
                0.0,
                Shared.Alpha(stats_state.text_color, 0.1)
            );
        }
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(row_x, row_y + Model.Scale(6n), row_width, Model.Scale(18n)),
                text: change.when,
                size: stats_state.small_font,
                class_name: stats_state.muted_class,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
        let row_height = Model.ChangeRowHeight(change.line, row_width);
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    row_x,
                    row_y + Model.Scale(28n),
                    row_width,
                    row_height - Model.Scale(36n)
                ),
                text: change.line,
                size: stats_state.font,
                wrap: NativeText.Wrap.TextWrapAuto,
                line_gap: Model.Scale(6n)
            }}
        />;
        row_y += row_height;
    }
}

// A daily completion series, oldest to newest, with zero days retained.
// The same chart draws one habit and the whole collection.
function CompletionTrend(chart_index: s32, x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let chart = Model.ReadHabitsStatsChartHost(chart_index);
    let height = Model.Scale(Model.STATS_TREND_HEIGHT);
    Card(x, y, width, height);
    let left = x + Model.Scale(32n);
    let right = x + width - Model.Scale(14n);
    let top = y + Model.Scale(18n);
    let bottom = y + height - Model.Scale(52n);
    let highest = chart.highest;
    if (highest < 1n) {
        highest = 1n;
    }
    for (let grid = s32(0n); grid <= 2n; grid += s32(1)) {
        let grid_y = top + ((bottom - top) * grid) / 2n;
        ChartLine(left, grid_y, right, grid_y, Shared.Alpha(stats_state.text_color, 0.12));
    }
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(
                x + Model.Scale(4n),
                top - Model.Scale(8n),
                Model.Scale(24n),
                Model.Scale(18n)
            ),
            text: Shared.Number(s64(highest)),
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(
                x + Model.Scale(4n),
                bottom - Model.Scale(8n),
                Model.Scale(24n),
                Model.Scale(18n)
            ),
            text: "0",
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    let count = chart.point_count;
    if (count > Model.STATS_DAYS) {
        count = Model.STATS_DAYS;
    }
    let previous_x = left;
    let previous_y = bottom;
    let selected: HabitsStatsPoint = {};
    let first: HabitsStatsPoint = {};
    let last: HabitsStatsPoint = {};
    for (let slot = s32(0n); slot < count; slot += s32(1)) {
        let point = Model.ReadHabitsStatsPointHost(chart_index, slot);
        let point_x = left + ((right - left) * slot) / (Model.STATS_DAYS - 1n);
        let point_y = bottom - ((bottom - top) * point.value) / highest;
        if (slot > 0n) {
            ChartLine(previous_x, previous_y, point_x, point_y, stats_state.color);
        }
        let dot = Model.Scale(4n);
        Fill(
            Shared.Bounds(point_x - dot / 2n, point_y - dot / 2n, dot, dot),
            float32(dot) * 0.5,
            stats_state.color
        );
        if (
            Button({
                session: stats_state.session,
                props: {
                    id: 6100000n + -chart_index * Model.STATS_DAYS + slot,
                    bounds: Shared.Bounds(
                        point_x - Model.Scale(8n),
                        point_y - Model.Scale(10n),
                        Model.Scale(16n),
                        Model.Scale(20n)
                    ),
                    label: point.label,
                    invisible: true,
                    disabled: stats_state.modal_active
                }
            })
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
            bounds: Shared.Bounds(
                left,
                bottom + Model.Scale(6n),
                (right - left) / 2n,
                Model.Scale(18n)
            ),
            text: Model.TrendDate(first.label),
            size: stats_state.small_font,
            class_name: stats_state.muted_class
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(
                left + (right - left) / 2n,
                bottom + Model.Scale(6n),
                (right - left) / 2n,
                Model.Scale(18n)
            ),
            text: Model.TrendDate(last.label),
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
            bounds: Shared.Bounds(left, bottom + Model.Scale(28n), right - left, Model.Scale(20n)),
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
    Card(x, y, width, Model.HabitsTrendsHeight(width));
    let left = x + Model.Scale(78n);
    let right = x + width - Model.Scale(14n);
    let top = y + Model.Scale(18n);
    let bottom = y + Model.Scale(Model.STATS_TREND_HEIGHT - 52n);
    let plot_width = right - left;
    if (plot_width <= 0n || stats_state.trend_count <= 0n) {
        return;
    }
    for (let grid = s32(0n); grid <= 2n; grid += s32(1)) {
        let grid_y = top + ((bottom - top) * grid) / 2n;
        ChartLine(left, grid_y, right, grid_y, Shared.Alpha(stats_state.text_color, 0.12));
    }
    if (Model.trend_selected_habit >= stats_state.trend_count) {
        Model.trend_selected_habit = -1n;
    }
    let selected = Model.trend_selected_habit;
    let pointer = SamplePointer();
    let choose = Button({
        session: stats_state.session,
        props: {
            id: 6100000n,
            bounds: Shared.Bounds(
                left - Model.Scale(8n),
                top - Model.Scale(8n),
                plot_width + Model.Scale(16n),
                bottom - top + Model.Scale(16n)
            ),
            label: Model.Locale("habit_stats_answers_title"),
            invisible: true,
            disabled: stats_state.modal_active
        }
    });
    let nearest_distance = float32(Model.Scale(14n) * Model.Scale(14n));
    let nearest_series: s32 = s32(-1n);
    let nearest_point: s32 = s32(-1n);
    let columns = Model.HabitTrendLegendColumns(width);
    let legend_x = x + Model.Scale(10n);
    let legend_y = y + Model.Scale(Model.STATS_TREND_HEIGHT + 60n);
    let legend_width = (width - Model.Scale(20n)) / columns;
    let first = Model.TrendDate(Model.ReadHabitsStatsPointHost(-1n, 0n).label);
    let last = Model.TrendDate(Model.ReadHabitsStatsPointHost(-1n, Model.STATS_DAYS - 1n).label);
    let detail: string = "";
    for (let offset = s32(1n); offset <= stats_state.trend_count; offset += s32(1)) {
        let index = (selected + offset) % stats_state.trend_count;
        let chart_index = -2n - index;
        let chart = Model.ReadHabitsStatsChartHost(chart_index);
        let entry_x = legend_x + (index % columns) * legend_width;
        let entry_y = legend_y + (index / columns) * Model.Scale(Model.STATS_TREND_LEGEND_HEIGHT);
        let bounds = Shared.Bounds(
            entry_x,
            entry_y,
            legend_width - Model.Scale(4n),
            Model.Scale(Model.STATS_TREND_LEGEND_HEIGHT)
        );
        if (index === selected) {
            Fill(bounds, float32(Model.Scale(8n)), Shared.Alpha(chart.color, 0.16));
        }
        if (
            Button({
                session: stats_state.session,
                props: {
                    id: 6101000n + index,
                    bounds: bounds,
                    label: chart.title,
                    invisible: true,
                    selected: index === selected,
                    disabled: stats_state.modal_active
                }
            })
        ) {
            Model.trend_selected_habit = index === selected ? -1n : index;
            Model.trend_selected_slot = chart.point_count - 1n;
        }
        let chip_size = Model.Scale(8n);
        Fill(
            Shared.Bounds(
                entry_x + Model.Scale(8n),
                entry_y + Model.Scale(18n),
                chip_size,
                chip_size
            ),
            float32(chip_size) * 0.5,
            chart.color
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    entry_x + Model.Scale(22n),
                    entry_y,
                    legend_width - Model.Scale(32n),
                    Model.Scale(Model.STATS_TREND_LEGEND_HEIGHT)
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
                    bounds: Shared.Bounds(
                        x + Model.Scale(4n),
                        (chart.lowest === chart.highest ? (top + bottom) / 2n : top) -
                            Model.Scale(8n),
                        Model.Scale(66n),
                        Model.Scale(18n)
                    ),
                    text: Model.MetricValueText(chart.answer_type, chart.highest),
                    size: stats_state.small_font,
                    class_name: stats_state.muted_class,
                    align: TextAlign.TextAlignEnd
                }}
            />;
            if (chart.lowest !== chart.highest) {
                <Text
                    session={stats_state.session}
                    props={{
                        bounds: Shared.Bounds(
                            x + Model.Scale(4n),
                            bottom - Model.Scale(8n),
                            Model.Scale(66n),
                            Model.Scale(18n)
                        ),
                        text: Model.MetricValueText(chart.answer_type, chart.lowest),
                        size: stats_state.small_font,
                        class_name: stats_state.muted_class,
                        align: TextAlign.TextAlignEnd
                    }}
                />;
            }
        }
        let count = chart.point_count;
        if (count > Model.STATS_POINT_MAX) {
            count = Model.STATS_POINT_MAX;
        }
        let previous_x = left;
        let previous_y = bottom;
        for (let point_index = s32(0n); point_index < count; point_index += s32(1)) {
            let point = Model.ReadHabitsStatsPointHost(chart_index, point_index);
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
            let dot = Model.Scale(
                index === selected && point_index === Model.trend_selected_slot ? 8n : 4n
            );
            Fill(
                Shared.Bounds(point_x - dot / 2n, point_y - dot / 2n, dot, dot),
                float32(dot) * 0.5,
                chart.color
            );
            let distance = Model.TrendDistance(
                pointer.x,
                pointer.y,
                point_x,
                point_y,
                point_x,
                point_y
            );
            if (distance <= nearest_distance) {
                nearest_distance = distance;
                nearest_series = index;
                nearest_point = point_index;
            }
            if (point_index > 0n) {
                let segment_distance = Model.TrendDistance(
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
                    let before = Model.TrendDistance(
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
                detail = Model.TrendDetail(chart.title, point.label);
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
            bounds: Shared.Bounds(
                left,
                bottom + Model.Scale(6n),
                plot_width / 2n,
                Model.Scale(18n)
            ),
            text: first,
            size: stats_state.small_font,
            class_name: stats_state.muted_class
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(
                left + plot_width / 2n,
                bottom + Model.Scale(6n),
                plot_width / 2n,
                Model.Scale(18n)
            ),
            text: last,
            size: stats_state.small_font,
            class_name: stats_state.muted_class,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(
                x + Model.Scale(12n),
                bottom + Model.Scale(28n),
                width - Model.Scale(24n),
                Model.Scale(76n)
            ),
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
    let radius = Model.Scale(3n);
    if (radius * 2n > width) {
        radius = width / 2n;
    }
    Fill(Shared.Bounds(x, y, width, height), float32(radius), color);
}

// A figure on a card: its label muted above it and the figure strong, with
// the card's edge in the habit's colour.
function FigureCard(bounds: Rectangle, label: string, value: string): void {
    Cards.FigureCard(Model.SurfaceStyle(), bounds, label, value, Model.CurrentStatistics().color);
}

function Figure(x: s32, y: s32, width: s32, label: string, value: string): void {
    FigureCard(Shared.Bounds(x, y, width, Model.Scale(Model.STATS_FIGURE_HEIGHT)), label, value);
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
    let gap = Model.Scale(Model.STATS_CARD_GAP);
    let half = (width - gap) / 2n;
    Figure(x, y, half, first_label, first);
    Figure(x + half + gap, y, width - half - gap, second_label, second);
}

// A section's title above its cards: strong and a little larger than the
// text, wrapping onto more lines when it must. Returns its height.
function SectionTitle(title: string, x: s32, y: s32, width: s32): s32 {
    const stats_state = Model.CurrentStatistics();
    let height = Model.SectionTitleHeight(title, width);
    let strong = Shared.Strong(title);
    <Text
        session={stats_state.session}
        props={{
            bounds: Shared.Bounds(x, y, width, height),
            text: title,
            size: Model.SectionFont(),
            strong: nativeSlice(strong),
            semantic_kind: SemanticKind.SemanticHeading,
            heading_level: 2n,
            wrap: NativeText.Wrap.TextWrapAuto,
            line_gap: Model.Scale(3n)
        }}
    />;
    return height;
}

// The mood check-ins: their average and count, and a bar for each mood.
function MoodPanel(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let gap = Model.Scale(Model.STATS_CARD_GAP);
    y += SectionTitle(Model.Locale("habit_stats_mood_title"), x, y, width) + Model.Scale(10n);
    let hundredths = s32(stats_state.mood_average * 100.0);
    const average_label = Model.MoodAverageLabel(hundredths);
    FigurePair(
        x,
        y,
        width,
        Model.Locale("habit_stats_mood_average"),
        average_label,
        Model.Locale("habit_stats_mood_checkins"),
        Shared.Number(s64(stats_state.mood_total))
    );
    let bars_height = Model.Scale(Model.STATS_MOOD_BARS_HEIGHT);
    let bars_y = y + Model.Scale(Model.STATS_FIGURE_HEIGHT) + gap;
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
        let count = nativeAt(counts, mood);
        let bar_height = Model.Scale(3n);
        if (count > 0n && stats_state.mood_total > 0n) {
            bar_height = (count * (bars_height - Model.Scale(30n))) / stats_state.mood_total;
        }
        let bar_x = x + mood * slot + Model.Scale(10n);
        let bar_width = slot - Model.Scale(20n);
        if (bar_width < Model.Scale(4n)) {
            bar_width = Model.Scale(4n);
        }
        let color = Model.MoodColor(mood + 1n);
        if (count <= 0n) {
            color = Shared.Alpha(stats_state.text_color, 0.16);
        }
        Bar(
            bar_x,
            bars_y + bars_height - bar_height - Model.Scale(22n),
            bar_width,
            bar_height,
            color
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    bar_x,
                    bars_y + bars_height - Model.Scale(20n),
                    bar_width,
                    Model.Scale(16n)
                ),
                text: Shared.Number(s64(mood + 1n)),
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
            Button({
                session: stats_state.session,
                props: {
                    id: 24700n + index,
                    bounds: Shared.Bounds(segment_x, y, segment_width, Model.Scale(34n)),
                    label: nativeAt(labels, index),
                    tone:
                        index === selected
                            ? ButtonTone.ButtonToneAccent
                            : ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    selected: index === selected,
                    disabled: stats_state.modal_active
                }
            }) &&
            selected !== index
        ) {
            stats_state.hold_days = nativeAt(values, index);
        }
    }
}

// Each round of the last days as a dot at its day, held longer higher,
// with a line through each day's average.
function HoldGraph(x: s32, y: s32, width: s32): void {
    const hold_points = Model.HoldPoints();
    const stats_state = Model.CurrentStatistics();
    let days: s32 = stats_state.hold_days === 31n ? 31n : 7n;
    let graph_height = Model.Scale(Model.STATS_HOLD_GRAPH_HEIGHT);
    let axis_width = Model.Scale(48n);
    let plot_x = x + axis_width;
    let plot_y = y + Model.Scale(8n);
    let plot_width = width - axis_width - Model.Scale(10n);
    let plot_height = graph_height - Model.Scale(36n);
    Card(x, y, width, graph_height);
    let count: s32 = s32(0n);
    let longest: s32 = s32(1n);
    let day_points = Model.NewDayPoints();
    let day_totals = Model.NewDayTotals();
    for (let index = s32(0n); index < stats_state.hold_count; index += s32(1)) {
        if (count >= Model.STATS_HOLD_MAX) {
            break;
        }
        let hold = Model.ReadHabitsStatsHoldHost(index);
        if (hold.days_ago < 0n || hold.days_ago >= days) {
            continue;
        }
        let slot = days - 1n - hold.days_ago;
        if (hold.seconds > longest) {
            longest = hold.seconds;
        }
        nativeSet(day_points, slot, nativeAt(day_points, slot) + 1n);
        nativeSet(day_totals, slot, nativeAt(day_totals, slot) + hold.seconds);
        nativeSet(hold_points, count, {
            time_key: s64(-hold.days_ago) * 86400n + s64(hold.time),
            round: hold.round,
            slot: slot,
            seconds: hold.seconds
        });
        count += 1n;
    }
    // Oldest first, a session's rounds in order.
    for (let index = s32(1n); index < count; index += s32(1)) {
        let point = nativeAt(hold_points, index);
        let other = index - 1n;
        while (
            other >= 0n &&
            (nativeAt(hold_points, other).time_key > point.time_key ||
                (nativeAt(hold_points, other).time_key === point.time_key &&
                    nativeAt(hold_points, other).round > point.round))
        ) {
            nativeSet(hold_points, other + 1n, nativeAt(hold_points, other));
            other -= 1n;
        }
        nativeSet(hold_points, other + 1n, point);
    }
    let grid = Shared.Alpha(stats_state.text_color, 0.1);
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
                bounds: Shared.Bounds(
                    x + Model.Scale(4n),
                    line_y - Model.Scale(8n),
                    axis_width - Model.Scale(4n),
                    Model.Scale(18n)
                ),
                text: Shared.Number(s64(longest - (longest * step) / 2n)),
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    ChartLine(
        plot_x,
        plot_y + plot_height,
        plot_x + plot_width,
        plot_y + plot_height,
        Shared.Alpha(stats_state.text_color, 0.4)
    );
    let seen = Model.NewSeen();
    let first_x = Model.NewFirstX();
    let last_x = Model.NewLastX();
    for (let day = s32(0n); day < days; day += s32(1)) {
        nativeSet(first_x, day, -1n);
        nativeSet(last_x, day, -1n);
    }
    for (let index = s32(0n); index < count; index += s32(1)) {
        let slot = nativeAt(hold_points, index).slot;
        let in_day = nativeAt(day_points, slot) > 0n ? nativeAt(day_points, slot) : 1n;
        let ordinal = nativeAt(seen, slot);
        nativeSet(seen, slot, nativeAt(seen, slot) + 1n);
        let x0 = plot_x + (plot_width * slot) / days;
        let x1 = plot_x + (plot_width * (slot + 1n)) / days;
        nativeAt(hold_points, index).x = x0 + ((ordinal + 1n) * (x1 - x0)) / (in_day + 1n);
        nativeAt(hold_points, index).y =
            plot_y +
            plot_height -
            (nativeAt(hold_points, index).seconds * (plot_height - Model.Scale(10n))) / longest;
        if (
            nativeAt(first_x, slot) < 0n ||
            nativeAt(hold_points, index).x < nativeAt(first_x, slot)
        ) {
            nativeSet(first_x, slot, nativeAt(hold_points, index).x);
        }
        if (
            nativeAt(last_x, slot) < 0n ||
            nativeAt(hold_points, index).x > nativeAt(last_x, slot)
        ) {
            nativeSet(last_x, slot, nativeAt(hold_points, index).x);
        }
    }
    let previous_x: s32 = s32(0n);
    let previous_y: s32 = s32(0n);
    let has_previous = false;
    for (let day = s32(0n); day < days; day += s32(1)) {
        if (nativeAt(day_points, day) <= 0n) {
            continue;
        }
        let average = nativeAt(day_totals, day) / nativeAt(day_points, day);
        let average_y =
            plot_y + plot_height - (average * (plot_height - Model.Scale(10n))) / longest;
        if (has_previous) {
            ChartLine(previous_x, previous_y, nativeAt(first_x, day), average_y, stats_state.color);
        }
        ChartLine(
            nativeAt(first_x, day),
            average_y,
            nativeAt(last_x, day),
            average_y,
            stats_state.color
        );
        previous_x = nativeAt(last_x, day);
        previous_y = average_y;
        has_previous = true;
    }
    let dot = Model.Scale(3n);
    for (let index = s32(0n); index < count; index += s32(1)) {
        Fill(
            Shared.Bounds(
                nativeAt(hold_points, index).x - dot,
                nativeAt(hold_points, index).y - dot,
                dot * 2n,
                dot * 2n
            ),
            float32(dot),
            stats_state.color
        );
    }
    if (count <= 0n) {
        let empty = Model.Locale(
            days === 31n ? "habit_stats_no_rounds_month" : "habit_stats_no_rounds_week"
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    x,
                    y + graph_height / 2n - Model.Scale(8n),
                    width,
                    Model.Scale(18n)
                ),
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
        let label = Model.Locale("statistics_now_label");
        if (days_ago > 0n) {
            label = Model.Filled(Model.Locale("statistics_day_offset_label"), days_ago, 0n);
        }
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    plot_x + (plot_width * day) / days + Model.Scale(2n),
                    y + graph_height - Model.Scale(20n),
                    Model.Scale(48n),
                    Model.Scale(18n)
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
    let chart_height = Model.Scale(Model.STATS_CHART_HEIGHT);
    Card(x, y, width, chart_height);
    if (chart.point_count <= 0n) {
        return;
    }
    let count = chart.point_count;
    if (count > Model.STATS_POINT_MAX) {
        count = Model.STATS_POINT_MAX;
    }
    let band_count: s32 = s32(0n);
    let is_time = chart.answer_type === Habit.HABIT_ANSWER_TIME;
    let low: float32 = 0.0;
    if (is_time) {
        low = float32(chart.lowest);
    }
    let high = float32(chart.highest);
    for (let index = s32(0n); index < count; index += s32(1)) {
        let point = Model.ReadHabitsStatsPointHost(chart_index, index);
        nativeSet(chart_points, index, {
            slot: point.slot,
            value: float32(point.value),
            good: point.good,
            label: point.label
        });
        let band = Model.PointBand(chart, point);
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
            nativeSet(chart_bands, 0n, band);
            band_count = 1n;
        } else if (!Model.SameBand(nativeAt(chart_bands, band_count - 1n), band)) {
            if (nativeAt(chart_bands, band_count - 1n).from === band.from) {
                nativeSet(chart_bands, band_count - 1n, band);
            } else {
                nativeSet(chart_bands, band_count, band);
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
    let inset = Model.Scale(10n);
    BandChart(
        stats_state.session,
        {
            key: NativeLayout.KeyHash("statistics/answer-chart") + u64(chart_index),
            bounds: Shared.Bounds(
                x + inset,
                y + inset,
                width - inset * 2n,
                chart_height - inset * 2n
            ),
            semantic_label: Model.Locale("habit_stats_answers_title"),
            slots: Model.STATS_DAYS,
            min_value: low,
            max_value: high,
            bars: !is_time,
            top_label: Model.ValueText(chart.answer_type, s32(high)),
            bottom_label: Model.ValueText(chart.answer_type, s32(low)),
            font: stats_state.small_font,
            good_color: stats_state.color,
            other_color: Shared.Alpha(stats_state.text_color, 0.35),
            band_color: Shared.Alpha(stats_state.color, 0.14),
            grid_color: Shared.Alpha(stats_state.text_color, 0.15),
            text_color: stats_state.text_color,
            label_fill: LightenColor(stats_state.canvas_color, 6n)
        },
        nativeSlice(chart_points, 0n, count),
        nativeSlice(chart_bands, 0n, band_count)
    );
}

function Answer(chart_index: s32, chart: HabitsStatsChart, x: s32, y: s32, width: s32): void {
    y += SectionTitle(chart.title, x, y, width) + Model.Scale(10n);
    let first_label = Model.Locale("habit_stats_average");
    let second_label = Model.Locale("habit_stats_total");
    let first = "-";
    let second = "-";
    let answered = Model.Filled("%d/%d", chart.days, Model.STATS_DAYS);
    if (chart.answer_type === Habit.HABIT_ANSWER_TEXT) {
        TextAnswers(chart_index, chart, answered, x, y, width);
        return;
    }
    if (chart.answer_type === Habit.HABIT_ANSWER_YES_NO) {
        first_label = Model.Locale("habit_answer_yes");
        second_label = Model.Locale("habit_stats_answered");
        second = answered;
        if (chart.answered > 0n) {
            let percent = (chart.yes * 100n + chart.answered / 2n) / chart.answered;
            first = Model.PercentLabel(percent);
        }
    } else if (chart.point_count > 0n) {
        if (chart.answer_type === Habit.HABIT_ANSWER_TIME) {
            first = Model.TimeText(s32((chart.average + 50n) / 100n));
            second = Model.TimeRangeLabel(chart.lowest, chart.highest);
            second_label = Model.Locale("habit_stats_time_range");
        } else {
            first = Model.DecimalText(chart.average);
            second = Shared.Number(chart.sum);
        }
    }
    // With a goal, the second figure is how many were on target.
    if (chart.judged > 0n) {
        second_label = Model.Locale("habit_stats_on_target");
        second = Model.OnTargetText(chart);
    }
    FigurePair(x, y, width, first_label, first, second_label, second);
    y += Model.Scale(Model.STATS_FIGURE_HEIGHT) + Model.Scale(Model.STATS_CARD_GAP);
    if (
        chart.answer_type === Habit.HABIT_ANSWER_TIME ||
        chart.answer_type === Habit.HABIT_ANSWER_NUMBER
    ) {
        AnswerChart(chart_index, chart, x, y, width);
    }
}

// A span habit's average and longest length, or how many were on target
// when its spans are judged, and when they started and ended on average.
function Spans(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let lengths = Model.ReadHabitsStatsChartHost(0n);
    y += SectionTitle(Model.Locale("habit_stats_spans_title"), x, y, width) + Model.Scale(10n);
    let first = "-";
    let second = "-";
    let second_label = Model.Locale("habit_stats_longest");
    if (lengths.point_count > 0n) {
        first = Model.SpanText(s32((lengths.average + 50n) / 100n));
        second = Model.SpanText(lengths.highest);
    }
    if (lengths.judged > 0n) {
        second_label = Model.Locale("habit_stats_on_target");
        second = Model.OnTargetText(lengths);
    }
    FigurePair(x, y, width, Model.Locale("habit_stats_average"), first, second_label, second);
    y += Model.Scale(Model.STATS_FIGURE_HEIGHT) + Model.Scale(Model.STATS_CARD_GAP);
    AnswerChart(0n, lengths, x, y, width);
    y += Model.Scale(Model.STATS_CHART_HEIGHT) + Model.Scale(Model.STATS_CARD_GAP);
    let started = "-";
    let ended = "-";
    if (stats_state.span_start_average >= 0n) {
        started = Model.TimeText(s32((stats_state.span_start_average + 50n) / 100n));
        ended = Model.TimeText(s32((stats_state.span_end_average + 50n) / 100n));
    }
    FigurePair(
        x,
        y,
        width,
        Model.Locale("habit_stats_started"),
        started,
        Model.Locale("habit_stats_ended"),
        ended
    );
}

// Back, then the habit's name, strong, with "Statistics" muted below it.
// Returns the y below it, or -1 when Back was pressed.
function PageHeader(x: s32, y: s32, width: s32): s32 {
    return Cards.PageHeader(
        Model.SurfaceStyle(),
        Shared.Bounds(x, y, width, 0n),
        4300n,
        Model.CurrentStatistics().name,
        Model.Locale("habit_statistics_title"),
        false,
        Model.Locale("back_button")
    );
}

function Content(x: s32, y: s32, width: s32): void {
    const stats_state = Model.CurrentStatistics();
    let gap = Model.Scale(Model.STATS_SECTION_GAP);
    let card_gap = Model.Scale(Model.STATS_CARD_GAP);
    if (stats_state.overview) {
        FigurePair(
            x,
            y,
            width,
            Model.Locale("tab_habits"),
            Shared.Number(s64(stats_state.habit_count)),
            Model.Locale("habit_stats_last_30_days"),
            Shared.Number(s64(stats_state.last_30_done))
        );
    } else {
        FigurePair(
            x,
            y,
            width,
            Model.Locale("habit_stats_current_streak"),
            Model.DayCountText(stats_state.current_streak),
            Model.Locale("habit_stats_last_30_days"),
            Model.Filled("%d/%d", stats_state.last_30_done, stats_state.last_30_due)
        );
    }
    y += Model.Scale(Model.STATS_FIGURE_HEIGHT) + gap;
    y +=
        SectionTitle(
            Model.Locale(
                stats_state.overview ? "habit_stats_metric_trends" : "habit_stats_daily_completions"
            ),
            x,
            y,
            width
        ) + Model.Scale(10n);
    if (stats_state.overview && stats_state.trend_count > 0n) {
        CompletionTrends(x, y, width);
        return;
    }
    CompletionTrend(-1n, x, y, width);
    y += Model.Scale(Model.STATS_TREND_HEIGHT) + gap;
    if (stats_state.overview) {
        return;
    }
    // A habit that measures spans is about their length: it comes first.
    if (stats_state.span) {
        Spans(x, y, width);
        y += Model.SpanHeight(width);
    }
    if (stats_state.mood_total > 0n) {
        MoodPanel(x, y, width);
        y += Model.MoodPanelHeight(width) + gap;
    }
    if (stats_state.hold_days > 0n) {
        y +=
            SectionTitle(Model.Locale("habit_stats_wim_hof_hold_rounds"), x, y, width) +
            Model.Scale(10n);
        HoldRange(x, y, Model.Scale(118n));
        y += Model.Scale(42n);
        HoldGraph(x, y, width);
        y += Model.Scale(Model.STATS_HOLD_GRAPH_HEIGHT) + gap;
    }
    y += SectionTitle(Model.Locale("habit_stats_weekday_pattern"), x, y, width) + Model.Scale(10n);
    let chart_height = Model.Scale(Model.STATS_CHART_HEIGHT);
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
    let most: s32 = s32(1n);
    for (let day = s32(0n); day <= 6n; day += s32(1)) {
        if (nativeAt(counts, day) > most) {
            most = nativeAt(counts, day);
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
    let inner_x = x + Model.Scale(8n);
    let slot = (width - Model.Scale(16n)) / 7n;
    for (let day = s32(0n); day <= 6n; day += s32(1)) {
        let height = Model.Scale(3n);
        if (nativeAt(counts, day) > 0n) {
            height = (nativeAt(counts, day) * (chart_height - Model.Scale(44n))) / most;
        }
        let bar_x = inner_x + day * slot + Model.Scale(5n);
        let bar_width = slot - Model.Scale(10n);
        if (bar_width < Model.Scale(4n)) {
            bar_width = Model.Scale(4n);
        }
        Bar(
            bar_x,
            y + chart_height - height - Model.Scale(28n),
            bar_width,
            height,
            nativeAt(counts, day) > 0n
                ? LightenColor(stats_state.color, 12n)
                : Shared.Alpha(stats_state.text_color, 0.16)
        );
        <Text
            session={stats_state.session}
            props={{
                bounds: Shared.Bounds(
                    bar_x,
                    y + chart_height - Model.Scale(24n),
                    bar_width,
                    Model.Scale(18n)
                ),
                text: nativeAt(labels, day),
                size: NativeText.Text12,
                class_name: stats_state.muted_class,
                align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    y += chart_height + gap;
    if (stats_state.linked) {
        y +=
            SectionTitle(Model.Locale("habit_stats_practice_time"), x, y, width) + Model.Scale(10n);
        FigurePair(
            x,
            y,
            width,
            Model.Locale("habit_stats_best_hold"),
            stats_state.best_time,
            Model.Locale("habit_stats_total_hold"),
            stats_state.total_time
        );
    } else {
        Figure(
            x,
            y,
            width,
            Model.Locale("habit_stats_best_streak"),
            Model.DayCountText(stats_state.best_streak)
        );
    }
    y += Model.Scale(Model.STATS_FIGURE_HEIGHT) + gap;
    Answers(x, y, width);
    y += Model.AnswersHeight(width);
    Changes(x, y, width);
    card_gap;
}

export function HabitsStatsView(message: HabitsMessage): HabitsMessage {
    const stats_state = Model.CurrentStatistics();
    Model.SetStatistics(Model.ReadHabitsStatsHost());
    stats_state.action = HABITS_STATS_NONE;
    let side = Model.Scale(16n);
    let x = side;
    let width = stats_state.view_width - side * 2n;
    if (width > Model.Scale(Model.STATS_CONTENT_MAX_WIDTH)) {
        x += (width - Model.Scale(Model.STATS_CONTENT_MAX_WIDTH)) / 2n;
        width = Model.Scale(Model.STATS_CONTENT_MAX_WIDTH);
    }
    let top = PageHeader(x, Model.Scale(20n), width);
    if (top < 0n) {
        stats_state.action = HABITS_STATS_BACK;
        Model.WriteHabitsStatsHost(nativeDeref(stats_state));
        message.succeeded = true;
        return message;
    }
    let viewport_height = stats_state.view_height - top - stats_state.bottom - Model.Scale(4n);
    if (viewport_height < 0n) {
        viewport_height = 0n;
    }
    const scrolled = Scroll({
        session: stats_state.session,
        props: {
            key: NativeLayout.KeyHash("inbe/screens/statistics_screen/scroll/1"),
            bounds: Shared.Bounds(
                0n,
                top + Model.Scale(4n),
                stats_state.view_width,
                viewport_height
            ),
            content_height: Model.ContentHeight(width),
            scroll_offset: stats_state.scroll
        },
        children: (scrolled: NativeScroll.ScrollResult): void => {
            const stats_state = Model.CurrentStatistics();
            stats_state.scroll = scrolled.scroll_offset;
            Content(x, s32(scrolled.content.y) + Model.Scale(8n), width);
        }
    });
    if (!scrolled.opened) {
        stats_state.scroll = scrolled.scroll_offset;
    }
    Model.WriteHabitsStatsHost(nativeDeref(stats_state));
    message.succeeded = true;
    return message;
}
