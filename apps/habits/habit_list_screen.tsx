// The habit list and a habit's own page. The list shows today's progress
// and the coins to spend, then a table: day names over the rows, each row a
// habit's icon and name and a circle for each of the last days. A tap on a
// row opens its details; a row held on a touch screen, or pressed and moved
// with a mouse, drags it to another place, or among the inactive habits
// below the table. A habit's page lists its days, or shows them on a
// calendar. The host keeps the habits and their days and does what the
// page asks once it is drawn.
import { HabitsCoinColor } from "coin_color";
import { DateValid } from "date_parse";
import { HabitIconShape } from "habit_icons";
import * as Model from "habit_list_view";
import {
    ActiveIndices,
    WeeklyCountLabel,
    Alpha,
    Ask,
    Bounds,
    Coins,
    DateText,
    Day,
    DayAgo,
    DayCountText,
    EdgeScroll,
    EndDrag,
    FaceState,
    Filled,
    FirstLetter,
    FitFont,
    FollowDrag,
    Hairline,
    InkClass,
    Intersection,
    LIST_BACK_SHAPE,
    LIST_CARD_HOLD_SECONDS,
    LIST_CARD_PADDING,
    LIST_CARD_RADIUS,
    LIST_CHECK_SHAPE,
    LIST_DAY_MAX_WIDTH,
    LIST_DAY_MIN_WIDTH,
    LIST_DEACTIVATED_HINT_HEIGHT,
    LIST_DEACTIVATED_ROW_HEIGHT,
    LIST_DETAIL_ACTION_SIZE,
    LIST_DETAIL_PADDING,
    LIST_DETAIL_TITLE_GAP,
    LIST_DETAIL_TITLE_HEIGHT,
    LIST_FACE_KEYS,
    LIST_FIGURE_CARD_HEIGHT,
    LIST_HALF_DOT_SHAPE,
    LIST_ICON_COLUMN_WIDTH,
    LIST_INACTIVE_HEADER_HEIGHT,
    LIST_NAME_MAXIMUM_WIDTH,
    LIST_NAME_MIN_WIDTH,
    LIST_NAME_PREFERRED_WIDTH,
    LIST_NAME_RESIZE_HANDLE_WIDTH,
    LIST_RESIZE_SHAPE,
    LIST_ROW_HEIGHT,
    LIST_ROW_SMALL_ICON_SIZE,
    LIST_ROW_ICON_SIZE,
    LIST_TABLE_HEADER_HEIGHT,
    Locale,
    NewActive,
    NewCards,
    NewHeadingStrong,
    NewStrong,
    Number,
    OffDay,
    OpenHeight,
    PointIn,
    Pointer,
    ReadHabitsListHost,
    ReadRows,
    RowDetailHeight,
    RowDrag,
    RowTouch,
    Scale,
    TextOn,
    TitleFont,
    Weekday,
    WeekdayLabel,
    Width,
    WriteHabitsListHost
} from "habit_list_view";
import {
    HABITS_SCREEN_HISTORY,
    HABIT_VIEW_CALENDAR,
    HABIT_VIEW_WEEKLY,
    HABIT_WEEKLY_INITIAL_DAYS,
    HABIT_WEEKLY_LOAD_DAYS,
    HABIT_WEEKLY_MAX_DAYS
} from "habit_types";
import {
    HABITS_LIST_ADD,
    HABITS_LIST_ALL_STATISTICS,
    HABITS_LIST_BACK,
    HABITS_LIST_CLOSE,
    HABITS_LIST_DAY,
    HABITS_LIST_DEACTIVATE,
    HABITS_LIST_EDIT,
    HABITS_LIST_HISTORY,
    HABITS_LIST_MOVE,
    HABITS_LIST_NONE,
    HABITS_LIST_OPEN,
    HABITS_LIST_REACTIVATE,
    HABITS_LIST_SHOP,
    HABITS_LIST_STATISTICS,
    HabitsMessage
} from "habits_types";
import * as NativeButton from "kryon/button";
import { ButtonEmphasis, ButtonState, ButtonTone, ContentAlignment } from "kryon/control_props";
import { Color, DarkenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { IconType } from "kryon/icon";
import * as NativeLayout from "kryon/layout";
import { SamplePointer } from "kryon/pointer_input";
import * as NativePress from "kryon/press";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Press } from "kryon/tsx/press";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import * as NativeCoinIcon from "mingcute/mingcute_filled_copper_coin";
import * as NativeStatisticsIcon from "mingcute/mingcute_regular_chart_line";
import * as NativeShopIcon from "mingcute/mingcute_regular_shop";
import { HabitRowOffset, HabitTableLayout, HabitTableLayoutFor } from "table_layout";

function Fill(bounds: Rectangle, radius: float32, color: Color): void {
    const list_state = Model.CurrentList();
    <Box session={list_state.session} props={{ bounds: bounds, fill: color, radius: radius }} />;
}

function Circle(x: s32, y: s32, radius: s32, color: Color): void {
    Fill(Bounds(x - radius, y - radius, radius * 2n, radius * 2n), float32(radius), color);
}

// The drop place and the dragged copy are outlined in the text colour,
// which stands out on every theme, two pixels wide.
function Outline(bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let radius = float32(Scale(12n));
    let color = Alpha(list_state.text_color, 0.8);
    <Box session={list_state.session} props={{ bounds: bounds, border: color, radius: radius }} />;
    let inset = float32(Hairline());
    <Box
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + inset,
                y: bounds.y + inset,
                width: bounds.width - inset * 2.0,
                height: bounds.height - inset * 2.0
            },
            border: color,
            radius: radius - inset
        }}
    />;
}

// A button's face with a press over it, which holds, drags and counts a
// secondary click as well. Returns the press; its click also counts a
// keyboard activation of the face.
function PressButton(face: NativeButton.Props, press: NativePress.Props): NativePress.PressResult {
    const list_state = Model.CurrentList();
    face.key = u64(LIST_FACE_KEYS + press.id);
    face.id = 0n;
    face.disabled = face.disabled || list_state.modal_active;
    // The press is drawn over the face, so the face never sees the pointer;
    // its look follows the pointer instead.
    face.state = FaceState(face.bounds, face.selected);
    if (face.disabled) {
        face.state = ButtonState.ButtonStateAuto;
    }
    let activated = <Button session={list_state.session} props={face} />;
    press.key = u64(press.id);
    press.bounds = face.bounds;
    press.label = face.label;
    press.now = list_state.now;
    press.disabled = press.disabled || face.disabled;
    let result = <Press session={list_state.session} props={press} />;
    result.clicked = result.clicked || activated;
    return result;
}

// A coin and its amount, centred on the bounds' height from their left.
function CoinAmount(amount: string, bounds: Rectangle, font: s32): void {
    const list_state = Model.CurrentList();
    let size = float32(font);
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x,
                y: bounds.y + (bounds.height - size) * 0.5,
                width: size,
                height: size
            },
            shape: NativeCoinIcon.Shape,
            color: HabitsCoinColor(list_state.highlight_color, list_state.text_color)
        }}
    />;
    let strong = NewStrong();
    strong[0n] = { start: 0n, end: s32(amount.count) };
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + size + float32(Scale(6n)),
                y: bounds.y,
                width: bounds.width - size - float32(Scale(6n)),
                height: bounds.height
            },
            text: amount,
            size: font,
            strong: strong[:],
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
}

// A figure on a card: its label muted above it and the figure strong, with
// the card's edge in the accent colour.
function FigureCard(bounds: Rectangle, label: string, value: string, accent: Color): void {
    const list_state = Model.CurrentList();
    let radius = float32(Scale(LIST_CARD_RADIUS));
    let bar = float32(Scale(5n));
    Fill(bounds, radius, accent);
    <Box
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar,
                y: bounds.y,
                width: bounds.width - bar,
                height: bounds.height
            },
            fill: list_state.card_fill,
            radius: radius
        }}
    />;
    <Box
        session={list_state.session}
        props={{ bounds: bounds, border: list_state.card_border, radius: radius }}
    />;
    let pad = float32(Scale(LIST_CARD_PADDING));
    let inner = bounds.width - bar - pad * 2.0;
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(10n)),
                width: inner,
                height: float32(Scale(22n))
            },
            text: label,
            size: list_state.small_font,
            class_name: list_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let strong = NewStrong();
    strong[0n] = { start: 0n, end: s32(value.count) };
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(34n)),
                width: inner,
                height: float32(Scale(32n))
            },
            text: value,
            size: FitFont(value, s32(inner), Scale(NativeText.Text24), Scale(NativeText.Text16)),
            strong: strong[:],
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

// A habit's icon: a circle in its colour with the icon, or the first
// letter of its name, in the colour that reads on it.
function HabitIcon(index: s32, bounds: Rectangle): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let row = rows[index];
    let radius = s32(bounds.width * 0.5);
    let center_x = s32(bounds.x) + radius;
    let center_y = s32(bounds.y) + radius;
    Circle(center_x, center_y, radius, DarkenColor(row.color, 10n));
    Circle(center_x, center_y, radius - Scale(1n), row.color);
    let shape = HabitIconShape(row.icon);
    if (row.icon >= 1n && shape.count > 0n) {
        let inset = bounds.width * 0.22;
        <SvgIcon
            session={list_state.session}
            props={{
                bounds: {
                    x: bounds.x + inset,
                    y: bounds.y + inset,
                    width: bounds.width - inset * 2.0,
                    height: bounds.height - inset * 2.0
                },
                shape: shape,
                color: TextOn(row.color)
            }}
        />;
        return;
    }
    <Text
        session={list_state.session}
        props={{
            bounds: bounds,
            text: FirstLetter(row.name),
            size: list_state.font,
            class_name: InkClass(row.color),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

// A day's dot: filled once the day is complete, showing the day's count
// when the habit counts and a clean check when it does not. The flat fill
// and thin rim stay legible in tight rows and at small touch targets.
function DayDot(
    center_x: s32,
    center_y: s32,
    radius: s32,
    accent: Color,
    complete: boolean,
    half: boolean,
    counting: boolean,
    count: s32
): void {
    const list_state = Model.CurrentList();
    let show_count = counting && count > 0n;
    if (complete) {
        Circle(center_x, center_y, radius, DarkenColor(accent, 12n));
        Circle(center_x, center_y, radius - Scale(1n), accent);
        if (!show_count) {
            let reach = radius - Scale(4n);
            <SvgIcon
                session={list_state.session}
                props={{
                    bounds: Bounds(center_x - reach, center_y - reach, reach * 2n, reach * 2n),
                    shape: LIST_CHECK_SHAPE,
                    color: TextOn(accent)
                }}
            />;
        }
    } else {
        Circle(center_x, center_y, radius, Alpha(list_state.text_color, 0.26));
        Circle(center_x, center_y, radius - Scale(1n), list_state.surface_color);
        if (half) {
            let face = radius - Scale(1n);
            <SvgIcon
                session={list_state.session}
                props={{
                    bounds: Bounds(center_x - face, center_y - face, face * 2n, face * 2n),
                    shape: LIST_HALF_DOT_SHAPE,
                    color: accent
                }}
            />;
        }
    }
    if (show_count) {
        let count_text = Number(s64(count));
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(center_x - radius, center_y - radius, radius * 2n, radius * 2n),
                text: count_text,
                size: FitFont(count_text, radius * 2n - Scale(2n), radius + Scale(4n), Scale(8n)),
                class_name: complete ? InkClass(accent) : 0n,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
}

// One of the last days in a habit's row: a planned day has a circle that
// marks it. A day off the schedule has none and cannot be tapped, unless
// something was recorded on it, which shows faded and opens like any other
// day.
function DayCell(
    index: s32,
    first_active: boolean,
    day: s32,
    column: s32,
    bounds: Rectangle
): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let row = rows[index];
    let state = Day(index, day);
    let shown = state.planned || state.complete || state.count > 0n || state.running;
    let id = 5200000n + index * 16n + column;
    let press = (
        <Press
            session={list_state.session}
            props={{
                key: u64(id),
                id: id,
                bounds: bounds,
                now: list_state.now,
                disabled: list_state.modal_active || !shown
            }}
        />
    );
    if (first_active && column === 0n) {
        list_state.first_day = bounds;
    }
    let center_x = s32(bounds.x + bounds.width * 0.5);
    let center_y = s32(bounds.y + bounds.height * 0.5);
    let radius = s32(bounds.width * 0.3);
    if (radius > Scale(14n)) {
        radius = Scale(14n);
    }
    if (radius < Scale(9n)) {
        radius = Scale(9n);
    }
    if (
        shown &&
        !list_state.modal_active &&
        !list_state.touch &&
        !list_state.dragging &&
        PointIn(Pointer(), bounds)
    ) {
        Circle(center_x, center_y, radius + Scale(5n), Alpha(row.color, 0.24));
    }
    if (state.planned) {
        DayDot(
            center_x,
            center_y,
            radius,
            row.color,
            state.complete,
            state.running,
            row.counting,
            state.count
        );
    } else if (shown) {
        DayDot(
            center_x,
            center_y,
            radius,
            OffDay(row.color),
            state.complete,
            state.running,
            row.counting,
            state.count
        );
    }
    if (press.clicked) {
        Ask(HABITS_LIST_DAY, index, day);
    }
}

// The day names over the table's day columns, today first.
function TableHeader(x: s32, y: s32, layout: HabitTableLayout, height: s32): void {
    const list_state = Model.CurrentList();
    for (let column = s32(0n); column < layout.days; column += s32(1)) {
        let label = WeekdayLabel(DayAgo(column), column);
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(x + column * layout.day_width, y, layout.day_width, height),
                text: label,
                size: FitFont(
                    label,
                    layout.day_width - Scale(4n),
                    list_state.small_font,
                    Scale(10n)
                ),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
}

// The border between names and days resizes the name column. Its saved
// width is in design units, so it follows the window and device scale. The
// handle sits left of the border, so it never covers today's day name.
function NameResize(x: s32, y: s32, height: s32, name_width: s32): void {
    const list_state = Model.CurrentList();
    let handle_width = Scale(LIST_NAME_RESIZE_HANDLE_WIDTH);
    let press = PressButton(
        {
            bounds: Bounds(x - handle_width - Scale(2n), y, handle_width, height),
            label: Locale("session_resize_button"),
            icon_only: true,
            icon_shape: LIST_RESIZE_SHAPE,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisGhost
        },
        { id: 4100000n, capture: true }
    );
    let unit = float32(Scale(1n));
    if (unit <= 0.0) {
        unit = 1.0;
    }
    if (press.down && !list_state.name_resizing && !list_state.dragging) {
        list_state.name_resizing = true;
        list_state.name_resize_origin = press.x;
        list_state.name_resize_start = float32(name_width) / unit;
    }
    if (list_state.name_resizing && (press.down || press.released)) {
        let width = list_state.name_resize_start + (press.x - list_state.name_resize_origin) / unit;
        if (width < float32(LIST_NAME_MIN_WIDTH)) {
            width = float32(LIST_NAME_MIN_WIDTH);
        }
        if (width > float32(LIST_NAME_MAXIMUM_WIDTH)) {
            width = float32(LIST_NAME_MAXIMUM_WIDTH);
        }
        list_state.name_width = s32(width + 0.5);
        if (press.released) {
            list_state.name_resizing = false;
            list_state.save = true;
        }
    } else if (list_state.name_resizing && !press.down) {
        list_state.name_resizing = false;
        list_state.save = true;
    }
}

// A habit's icon and name at the start of its row; without room for the
// name, a smaller icon alone.
function RowFace(index: s32, bounds: Rectangle, layout: HabitTableLayout, pad: s32): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let icon_size = Scale(layout.names ? LIST_ROW_ICON_SIZE : LIST_ROW_SMALL_ICON_SIZE);
    HabitIcon(
        index,
        Bounds(
            s32(bounds.x) + pad,
            s32(bounds.y + (bounds.height - float32(icon_size)) * 0.5),
            icon_size,
            icon_size
        )
    );
    if (!layout.names) {
        return;
    }
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(
                s32(bounds.x) + pad + icon_size + Scale(10n),
                s32(bounds.y),
                layout.name_width - icon_size - Scale(14n),
                s32(bounds.height)
            ),
            text: rows[index].name,
            size: list_state.font,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
}

// A habit's row: its icon and name, which open its details and drag it to
// another place, and then a circle for each of the last days. Returns true
// when the row was tapped.
function Row(
    index: s32,
    first_active: boolean,
    bounds: Rectangle,
    layout: HabitTableLayout,
    pad: s32,
    open: boolean
): boolean {
    const list_state = Model.CurrentList();
    let touch = RowTouch(bounds);
    let lifted = list_state.dragging && list_state.drag_habit === index && list_state.drag_lifted;
    let press = PressButton(
        {
            bounds: touch,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisGhost,
            selected: open
        },
        {
            id: 4200n + index,
            hold_seconds: LIST_CARD_HOLD_SECONDS,
            capture: !list_state.touch || lifted
        }
    );
    let tapped = RowDrag(index, touch, press);
    RowFace(index, bounds, layout, pad);
    let x = s32(bounds.x) + pad + layout.name_width;
    for (let column = s32(0n); column < layout.days; column += s32(1)) {
        DayCell(
            index,
            first_active,
            DayAgo(column),
            column,
            Bounds(
                x + column * layout.day_width,
                s32(bounds.y),
                layout.day_width,
                s32(bounds.height)
            )
        );
    }
    return tapped;
}

// An open habit's details below its row, together on a tinted panel: its
// description, its history, statistics and editor, and its current streak
// and this week's days.
function RowDetail(index: s32, first_active: boolean, bounds: Rectangle, pad: s32): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let row = rows[index];
    let panel_x = s32(bounds.x) + pad;
    let panel_width = s32(bounds.width) - pad * 2n;
    let panel_y = s32(bounds.y) + Scale(4n);
    let panel_height = s32(bounds.height) - Scale(4n) - Scale(12n);
    Fill(
        Bounds(panel_x, panel_y, panel_width, panel_height),
        float32(Scale(LIST_CARD_RADIUS)),
        Alpha(list_state.text_color, 0.04)
    );
    let inner = Scale(LIST_DETAIL_PADDING);
    let x = panel_x + inner;
    let width = panel_width - inner * 2n;
    let y = panel_y + inner;
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(x, y, width, Scale(LIST_DETAIL_TITLE_HEIGHT)),
            text: row.name,
            size: list_state.font,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    y += Scale(LIST_DETAIL_TITLE_HEIGHT + LIST_DETAIL_TITLE_GAP);
    if (row.description.count > 0n) {
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(x, y, width, Scale(22n)),
                text: row.description,
                size: list_state.small_font,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
        y += Scale(30n);
    }
    let action_size = Scale(LIST_DETAIL_ACTION_SIZE);
    let action_gap = (width - action_size * 3n) / 2n;
    let icons: [s32, s32, s32] = [
        s32(IconType.IconCalendar),
        s32(IconType.IconStat),
        s32(IconType.IconEdit)
    ];
    let actions: [s32, s32, s32] = [HABITS_LIST_HISTORY, HABITS_LIST_STATISTICS, HABITS_LIST_EDIT];
    for (let column = s32(0n); column <= 2n; column += s32(1)) {
        let action_bounds = Bounds(
            x + column * (action_size + action_gap),
            y,
            action_size,
            action_size
        );
        if (
            (
                <Button
                    session={list_state.session}
                    props={{
                        id: 5600000n + index * 3n + column,
                        bounds: action_bounds,
                        icon_type: icons[column],
                        icon_only: true,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisOutline,
                        disabled: list_state.modal_active
                    }}
                />
            )
        ) {
            Ask(actions[column], index, 0n);
        }
        if (first_active) {
            if (column === 0n) {
                list_state.anchor_history = action_bounds;
            } else if (column === 1n) {
                list_state.anchor_statistics = action_bounds;
            } else {
                list_state.anchor_edit = action_bounds;
            }
        }
    }
    if (first_active) {
        list_state.anchor_day = list_state.anchor_table;
    }
    let metric_y = y + action_size + Scale(12n);
    let metric_gap = Scale(10n);
    let metric_width = (width - metric_gap) / 2n;
    FigureCard(
        Bounds(x, metric_y, metric_width, Scale(LIST_FIGURE_CARD_HEIGHT)),
        Locale("habit_stats_current_streak"),
        DayCountText(row.streak),
        row.color
    );
    FigureCard(
        Bounds(
            x + metric_width + metric_gap,
            metric_y,
            width - metric_width - metric_gap,
            Scale(LIST_FIGURE_CARD_HEIGHT)
        ),
        Locale("profile_progress_title"),
        Filled("%d / %d", row.week_done, row.week_planned),
        row.color
    );
}

// Three short bars at a row's end show that the row can be dragged.
function Grip(bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let width = float32(Scale(18n));
    let thickness = float32(Scale(2n));
    let spacing = float32(Scale(5n));
    let x = bounds.x + bounds.width - float32(Scale(16n)) - width;
    let y = bounds.y + bounds.height * 0.5 - spacing - thickness * 0.5;
    let color = Alpha(list_state.text_color, 0.45);
    for (let bar = s32(0n); bar <= 2n; bar += s32(1)) {
        Fill(
            { x: x, y: y + float32(bar) * spacing, width: width, height: thickness },
            thickness * 0.5,
            color
        );
    }
}

// A habit's icon, name and grip, in a deactivated habit's row or in the
// copy that follows the pointer while a habit is dragged.
function DragFace(index: s32, bounds: Rectangle): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let icon_size = Scale(32n);
    HabitIcon(
        index,
        Bounds(
            s32(bounds.x) + Scale(12n),
            s32(bounds.y + (bounds.height - float32(icon_size)) * 0.5),
            icon_size,
            icon_size
        )
    );
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(
                s32(bounds.x) + Scale(54n),
                s32(bounds.y),
                s32(bounds.width) - Scale(104n),
                s32(bounds.height)
            ),
            text: rows[index].name,
            size: list_state.font,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    Grip(bounds);
}

// An inactive habit's row below the inactive habits' header. It drags like
// a habit's row: back into the habits above makes it active again.
function DeactivatedRow(index: s32, bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let touch = RowTouch(bounds);
    let lifted = list_state.dragging && list_state.drag_habit === index && list_state.drag_lifted;
    let press = PressButton(
        {
            bounds: touch,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisGhost
        },
        {
            id: 4900n + index,
            hold_seconds: LIST_CARD_HOLD_SECONDS,
            capture: !list_state.touch || lifted
        }
    );
    RowDrag(index, touch, press);
    DragFace(index, bounds);
}

// The inactive habits' header row after the habits: their count and a
// chevron. A tap shows or hides their rows below it.
function InactiveHeader(bounds: Rectangle, count: s32, pad: s32): void {
    const list_state = Model.CurrentList();
    let open = list_state.show_deactivated;
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4110n,
                    bounds: RowTouch(bounds),
                    label: Filled(Locale("habits_inactive_section"), count, 0n),
                    content_alignment: ContentAlignment.ContentAlignmentStart,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        list_state.show_deactivated = !open;
        list_state.save = true;
    }
    // The chevron at the row's end points down while the rows are hidden.
    let span = Scale(5n);
    let center_x = s32(bounds.x + bounds.width) - pad - Scale(12n);
    let center_y = s32(bounds.y + bounds.height * 0.5);
    let shape = open ? "S2.4rr:M0 18L12 6L24 18" : "S2.4rr:M0 6L12 18L24 6";
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: Bounds(center_x - span, center_y - span, span * 2n, span * 2n),
            shape: shape,
            color: Alpha(list_state.text_color, 0.7)
        }}
    />;
}

// While a habit is dragged over the habit list, the row it would take the
// place of is outlined, or the whole list when it would go last. Releasing
// it there moves a row to that place or reactivates a deactivated habit. A
// row dragged onto the inactive habits below the list becomes inactive.
function Drop(
    viewport: Rectangle,
    max_scroll: s32,
    cards: Rectangle[],
    count: s32,
    section: Rectangle,
    released: boolean
): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    if (!list_state.dragging) {
        return;
    }
    let dragged = list_state.drag_habit;
    if (dragged < 0n || dragged >= Model.row_count) {
        EndDrag();
        return;
    }
    let reactivating = rows[dragged].deactivated;
    let point = list_state.drag_pointer;
    // Over the inactive habits, a habit is dropped among them.
    let in_section = list_state.drag_moving && section.height > 0.0 && PointIn(point, section);
    let target: s32 = -1n;
    if (list_state.drag_moving && !in_section && PointIn(point, viewport)) {
        target = count;
        let highlight = viewport;
        for (let position = s32(0n); position < count; position += s32(1)) {
            if (PointIn(point, cards[position])) {
                target = position;
                highlight = Intersection(cards[position], viewport);
                break;
            }
        }
        Outline(highlight);
    }
    let over_section = !reactivating && in_section;
    if (over_section) {
        Outline(section);
    }
    if (released) {
        if (list_state.drag_moving && over_section) {
            Ask(HABITS_LIST_DEACTIVATE, dragged, 0n);
        } else if (list_state.drag_moving && target >= 0n) {
            Ask(reactivating ? HABITS_LIST_REACTIVATE : HABITS_LIST_MOVE, dragged, 0n);
            list_state.action_target = target;
        }
        EndDrag();
        return;
    }
    if (!list_state.drag_moving) {
        return;
    }
    EdgeScroll(viewport, max_scroll, point);
    let lifted = list_state.drag_bounds;
    lifted.x = point.x - list_state.drag_grab.x;
    lifted.y = point.y - list_state.drag_grab.y;
    Fill(lifted, float32(Scale(12n)), list_state.surface_color);
    Outline(lifted);
    DragFace(dragged, lifted);
}

function Overview(): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let x = s32(list_state.bounds.x);
    let y = s32(list_state.bounds.y);
    let width = s32(list_state.bounds.width);
    let height = s32(list_state.bounds.height);
    let heading_height = Scale(34n);
    let button_height = Scale(42n);
    let gap = Scale(12n);
    let add_label = Locale("habit_new_button");
    let add_width = Width(add_label, list_state.font) + Scale(40n);
    if (add_width < Scale(120n)) {
        add_width = Scale(120n);
    }
    if (add_width > (width * 2n) / 3n) {
        add_width = (width * 2n) / 3n;
    }
    let heading = Locale("tab_habits");
    let heading_strong = NewHeadingStrong();
    heading_strong[0n] = { start: 0n, end: s32(heading.count) };
    let heading_width = width - add_width - gap;
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(x, y, heading_width, heading_height),
            text: heading,
            size: TitleFont(heading, heading_width),
            strong: heading_strong[:],
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4100n,
                    bounds: Bounds(x + width - add_width, y, add_width, button_height),
                    label: add_label,
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                    pill: true,
                    disabled: list_state.modal_active || Model.row_count >= list_state.habit_limit
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_ADD, -1n, 0n);
        return;
    }
    let summary_y = y + heading_height + gap;
    let coins = Coins(list_state.halves);
    let coins_width = list_state.font + Scale(6n) + Width(coins, list_state.font);
    let minimum_action_size: s32 = 44n;
    let action_size = Scale(minimum_action_size);
    let action_gap = Scale(8n);
    let coin_padding = Scale(6n);
    let coin_gap = Scale(10n);
    let wide_actions_width =
        coins_width + coin_padding + coin_gap + action_gap + 2n * minimum_action_size;
    if (action_size < minimum_action_size && width >= wide_actions_width) {
        action_size = minimum_action_size;
    }
    let icon_size = Scale(20n);
    let icon_inset = (action_size - icon_size) / 2n;
    let statistics_x = x + width - action_size;
    let shop_right = statistics_x - action_gap;
    let shop_icon_x = shop_right - action_size + icon_inset;
    let shop_x = shop_icon_x - coins_width - coin_gap - coin_padding;
    if (shop_x < x) {
        shop_x = x;
        coin_padding = 0n;
        coins_width = shop_icon_x - x - Scale(5n);
    }
    // Keep the coin balance and storefront in the same tap target.
    let action_y = summary_y + (Scale(34n) - action_size) / 2n;
    let summary_width = shop_x - x - gap;
    let due: s32 = 0n;
    let done: s32 = 0n;
    const today_days = Model.TodayDays();
    for (let index = s32(0n); index < Model.row_count; index += s32(1)) {
        if (today_days[index].planned) {
            due += 1n;
            if (today_days[index].complete) {
                done += 1n;
            }
        }
    }
    let summary = Filled(Locale("habits_done_count_label"), done, due);
    if (summary_width < Width(summary, list_state.font)) {
        action_y = summary_y;
        summary_y += action_size + Scale(6n);
        summary_width = width;
    }
    let shop_bounds = Bounds(shop_x, action_y, shop_right - shop_x, action_size);
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4120n,
                    bounds: shop_bounds,
                    label: Locale("habits_shop_button"),
                    invisible: true,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_SHOP, -1n, 0n);
        return;
    }
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4121n,
                    bounds: Bounds(statistics_x, action_y, action_size, action_size),
                    label: Locale("habit_statistics_title"),
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_ALL_STATISTICS, -1n, 0n);
        return;
    }
    CoinAmount(
        coins,
        Bounds(shop_x + coin_padding, action_y, coins_width, action_size),
        list_state.font
    );
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: Bounds(shop_icon_x, action_y + icon_inset, icon_size, icon_size),
            shape: NativeShopIcon.Shape,
            color: list_state.text_color
        }}
    />;
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: Bounds(statistics_x + icon_inset, action_y + icon_inset, icon_size, icon_size),
            shape: NativeStatisticsIcon.Shape,
            color: list_state.text_color
        }}
    />;
    list_state.anchor_coins = shop_bounds;
    let progress_y = summary_y + Scale(28n);
    let progress_height = Scale(6n);
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(x, summary_y, summary_width, Scale(24n)),
            text: summary,
            size: list_state.font,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    list_state.anchor_progress = Bounds(x, summary_y, summary_width, Scale(24n));
    let progress_width = summary_width;
    if (progress_width > Scale(420n)) {
        progress_width = Scale(420n);
    }
    Fill(
        Bounds(x, progress_y, progress_width, progress_height),
        float32(Scale(3n)),
        Alpha(list_state.text_color, 0.12)
    );
    if (due > 0n && done > 0n) {
        let progress_fill = (progress_width * done) / due;
        if (progress_fill > progress_width) {
            progress_fill = progress_width;
        }
        Fill(
            Bounds(x, progress_y, progress_fill, progress_height),
            float32(Scale(3n)),
            list_state.accent_color
        );
    }
    let released = FollowDrag();
    let active = NewActive();
    let active_count = ActiveIndices(active[:]);
    let selected_position: s32 = -1n;
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        if (active[position] === list_state.selected) {
            selected_position = position;
        }
    }
    let deactivated_count = Model.row_count - active_count;
    let show_section = Model.row_count > 0n;
    let list_y = summary_y + Scale(54n);
    let list_bottom = y + height;
    let header_height = Scale(LIST_TABLE_HEADER_HEIGHT);
    let rows_y = list_y + header_height;
    if (list_bottom < rows_y) {
        list_bottom = rows_y;
    }
    let viewport = Bounds(x, rows_y, width, list_bottom - rows_y);
    let row_height = Scale(LIST_ROW_HEIGHT);
    let detail_height: s32 = 0n;
    if (selected_position >= 0n) {
        detail_height = RowDetailHeight(active[selected_position]);
    }
    let active_height = active_count * row_height + detail_height;
    if (active_count === 0n) {
        active_height = Scale(80n);
    }
    // After the habits, the inactive habits' header, and their rows when it
    // is open.
    let section_height: s32 = 0n;
    let inactive_row_height = Scale(LIST_DEACTIVATED_ROW_HEIGHT);
    if (show_section) {
        section_height = Scale(LIST_INACTIVE_HEADER_HEIGHT);
        if (list_state.show_deactivated) {
            section_height +=
                Scale(LIST_DEACTIVATED_HINT_HEIGHT) + deactivated_count * inactive_row_height;
        }
    }
    let content_height = active_height + section_height;
    // When the rows would scroll with a habit's details and the inactive
    // habits open, the scrollbar shows from the start: opening them then
    // leaves the table's width, and so its day columns, as they are.
    let keep_scrollbar =
        OpenHeight(active[:], active_count, deactivated_count) >
        s32(viewport.height);
    // The table's panel holds the day names and the rows, as tall as the
    // rows need up to the space there is; the rows scroll within it, so a
    // scrollbar shown before they fill the space ends with the panel.
    let panel_rows_height = content_height;
    if (panel_rows_height > s32(viewport.height)) {
        panel_rows_height = s32(viewport.height);
    }
    <Box
        session={list_state.session}
        props={{
            bounds: Bounds(x, list_y, width, header_height + panel_rows_height),
            fill: list_state.surface_color,
            border: Alpha(list_state.text_color, 0.12),
            radius: float32(Scale(14n))
        }}
    />;
    // A habit that just opened scrolls into view: all of it when it fits,
    // otherwise from its top.
    if (list_state.reveal_selected) {
        list_state.reveal_selected = false;
        if (selected_position >= 0n) {
            let card_top = HabitRowOffset(
                selected_position,
                selected_position,
                row_height,
                detail_height
            );
            let card_bottom = card_top + row_height + detail_height;
            let view_height = s32(viewport.height);
            if (card_bottom - list_state.scroll > view_height) {
                list_state.scroll = card_bottom - view_height;
            }
            if (card_top < list_state.scroll) {
                list_state.scroll = card_top;
            }
            if (list_state.scroll > content_height - view_height) {
                list_state.scroll = content_height - view_height;
            }
            if (list_state.scroll < 0n) {
                list_state.scroll = 0n;
            }
        }
    }
    let scrolled = NativeScroll.Draw(list_state.session, {
        key: NativeLayout.KeyHash("inbe/habits/overview"),
        bounds: Bounds(x, rows_y, width, panel_rows_height),
        content_height: content_height,
        keep_scrollbar: keep_scrollbar,
        scroll_offset: list_state.scroll
    });
    list_state.scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let pad = Scale(12n);
    let table_x = s32(scrolled.content.x);
    let table_width = s32(scrolled.content.width);
    let name_preferred: s32 = LIST_NAME_PREFERRED_WIDTH;
    if (list_state.name_width > 0n) {
        name_preferred = list_state.name_width;
    }
    if (name_preferred < LIST_NAME_MIN_WIDTH) {
        name_preferred = LIST_NAME_MIN_WIDTH;
    }
    if (name_preferred > LIST_NAME_MAXIMUM_WIDTH) {
        name_preferred = LIST_NAME_MAXIMUM_WIDTH;
    }
    let layout = HabitTableLayoutFor(
        table_width - pad * 2n,
        Scale(name_preferred),
        Scale(LIST_NAME_MIN_WIDTH),
        Scale(LIST_ICON_COLUMN_WIDTH),
        Scale(LIST_DAY_MIN_WIDTH),
        Scale(LIST_DAY_MAX_WIDTH)
    );
    if (active_count === 0n) {
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(
                    table_x + pad,
                    s32(scrolled.content.y) + Scale(10n),
                    table_width - pad * 2n,
                    Scale(48n)
                ),
                text: Locale("habit_empty_title"),
                size: list_state.font,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    let cards = NewCards();
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        let index = active[position];
        let open = position === selected_position;
        let row = Bounds(
            table_x,
            s32(scrolled.content.y) +
                HabitRowOffset(position, selected_position, row_height, detail_height),
            table_width,
            row_height
        );
        cards[position] = row;
        if (position > 0n) {
            Fill(
                Bounds(table_x + pad, s32(row.y), table_width - pad * 2n, Hairline()),
                0.0,
                Alpha(list_state.text_color, 0.08)
            );
        }
        if (position === 0n) {
            list_state.anchor_table = row;
        }
        if (Row(index, position === 0n, row, layout, pad, open)) {
            Ask(open ? HABITS_LIST_CLOSE : HABITS_LIST_OPEN, index, 0n);
        }
        if (open) {
            RowDetail(
                index,
                position === 0n,
                Bounds(table_x, s32(row.y + row.height), table_width, detail_height),
                pad
            );
        }
    }
    let section = Bounds(
        table_x,
        s32(scrolled.content.y) + active_height,
        table_width,
        section_height
    );
    if (show_section) {
        Fill(
            Bounds(table_x, s32(section.y), table_width, Hairline()),
            0.0,
            Alpha(list_state.text_color, 0.12)
        );
        InactiveHeader(
            Bounds(table_x, s32(section.y), table_width, Scale(LIST_INACTIVE_HEADER_HEIGHT)),
            deactivated_count,
            pad
        );
    }
    if (show_section && list_state.show_deactivated) {
        let row_y = s32(section.y) + Scale(LIST_INACTIVE_HEADER_HEIGHT);
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(
                    table_x + pad,
                    row_y,
                    table_width - pad * 2n,
                    Scale(LIST_DEACTIVATED_HINT_HEIGHT)
                ),
                text: Locale("habits_deactivated_hint"),
                size: list_state.small_font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        row_y += Scale(LIST_DEACTIVATED_HINT_HEIGHT);
        for (let index = s32(0n); index < Model.row_count; index += s32(1)) {
            if (rows[index].deactivated) {
                DeactivatedRow(index, Bounds(table_x, row_y, table_width, inactive_row_height));
                row_y += inactive_row_height;
            }
        }
    }
    End(list_state.session);
    TableHeader(table_x + pad + layout.name_width, list_y, layout, header_height);
    NameResize(table_x + pad + layout.name_width, list_y, header_height, layout.name_width);
    Fill(Bounds(x, rows_y, width, Hairline()), 0.0, Alpha(list_state.text_color, 0.12));
    // A row dropped below the panel, while the rows do not fill the space,
    // still goes last.
    Drop(
        viewport,
        scrolled.max_scroll,
        cards[:],
        active_count,
        Intersection(section, scrolled.viewport),
        released
    );
}

// Back, then the habit's name, strong. Returns the y below it, or -1 when
// Back was pressed.
function PageHeader(x: s32, y: s32, width: s32, title: string): s32 {
    const list_state = Model.CurrentList();
    let back_label = Locale("back_button");
    let back_width = Width(back_label, list_state.font) + Scale(48n);
    if (back_width < Scale(88n)) {
        back_width = Scale(88n);
    }
    if (back_width > width / 3n) {
        back_width = width / 3n;
    }
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4300n,
                    bounds: Bounds(x, y + Scale(2n), back_width, Scale(42n)),
                    label: back_label,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisOutline,
                    icon_shape: LIST_BACK_SHAPE,
                    fit_content: true,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        return -1n;
    }
    let title_x = x + back_width + Scale(16n);
    let title_width = width - back_width - Scale(16n);
    let strong = NewStrong();
    strong[0n] = { start: 0n, end: s32(title.count) };
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(title_x, y, title_width, Scale(46n)),
            text: title,
            size: TitleFont(title, title_width),
            strong: strong[:],
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    return y + Scale(58n);
}

// The habit's page switches only between its week list and its calendar.
function ViewSwitch(x: s32, width: s32, top: s32): s32 {
    const list_state = Model.CurrentList();
    let options: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] = [
        { label: Locale("habit_focus_week") },
        { label: Locale("habit_focus_calendar") }
    ];
    let selection = (
        <SegmentedControl
            session={list_state.session}
            props={{
                id: 4301n,
                bounds: Bounds(x, top, width, Scale(42n)),
                height: Scale(42n),
                selected_index: list_state.view_mode === HABIT_VIEW_CALENDAR ? 1n : 0n,
                has_selection: true,
                disabled: list_state.modal_active
            }}
            options={options[:]}
        />
    );
    if (selection.changed) {
        list_state.view_mode =
            selection.selected_index === 1n ? HABIT_VIEW_CALENDAR : HABIT_VIEW_WEEKLY;
        list_state.scroll = 0n;
        list_state.save = true;
    }
    return top + Scale(54n);
}

// A day button. With a dot, as for a counting habit's calendar day, the
// label sits at the top and the day's dot with its count below it, and the
// dot rather than the button shows that the day is complete. A day off the
// habit's schedule has no background and a faded label, and opens only when
// something was recorded on it. A secondary click counts it down.
function DayButton(
    index: s32,
    day: s32,
    label: string,
    id: s32,
    bounds: Rectangle,
    dot: boolean
): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let row = rows[index];
    let state = Day(index, day);
    let scheduled = state.planned;
    let complete = state.complete;
    let recorded = complete || state.count > 0n || state.running;
    let disabled = list_state.modal_active || (!scheduled && !recorded);
    let filled = complete && !dot;
    let faded_label = !scheduled && !filled;
    let face: NativeButton.Props = {
        bounds: bounds,
        label: dot || faded_label ? "" : label,
        tone: filled ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
        selected: filled,
        disabled: disabled
    };
    if (filled && scheduled) {
        face.emphasis = ButtonEmphasis.ButtonEmphasisFilled;
    } else if (!scheduled && !filled) {
        face.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    }
    // A running span's day is lit softly until the span ends.
    if (!filled && state.running) {
        face.tone = ButtonTone.ButtonToneAccent;
        face.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    }
    let press = PressButton(face, { id: id });
    if (faded_label && !dot) {
        <Text
            session={list_state.session}
            props={{
                bounds: bounds,
                text: label,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone,
                disabled: true
            }}
        />;
    }
    if (dot) {
        let top = s32(bounds.y) + Scale(3n);
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(s32(bounds.x), top, s32(bounds.width), Scale(18n)),
                text: label,
                size: list_state.small_font,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone,
                disabled: disabled || !scheduled
            }}
        />;
        if (state.count > 0n || complete) {
            let radius = Scale(12n);
            let accent = row.color;
            if (!scheduled) {
                accent = OffDay(row.color);
            }
            DayDot(
                s32(bounds.x + bounds.width / 2n),
                s32(bounds.y + bounds.height) - Scale(4n) - radius,
                radius,
                accent,
                complete,
                false,
                true,
                state.count
            );
        }
    }
    if (press.clicked) {
        Ask(HABITS_LIST_DAY, index, day);
    } else if (press.right_clicked && !disabled) {
        Ask(HABITS_LIST_DAY, index, day);
        list_state.action_decrement = true;
    }
}

function Weekly(index: s32, x: s32, width: s32, top: s32, bottom: s32): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let row_height = Scale(46n);
    let gap = Scale(8n);
    let count = list_state.weekly_days;
    if (count < HABIT_WEEKLY_INITIAL_DAYS) {
        count = HABIT_WEEKLY_INITIAL_DAYS;
    }
    if (count > HABIT_WEEKLY_MAX_DAYS) {
        count = HABIT_WEEKLY_MAX_DAYS;
    }
    list_state.weekly_days = count;
    let content_height = count * (row_height + gap) + Scale(52n);
    let viewport = Bounds(x, top, width, bottom - top);
    const scrolled = (
        <Scroll
            session={list_state.session}
            props={{
                key: NativeLayout.KeyHash("inbe/habits/week"),
                bounds: viewport,
                content_height: content_height,
                scroll_offset: list_state.scroll
            }}
            children={(scrolled: NativeScroll.ScrollResult): void => {
                const list_state = Model.CurrentList();
                list_state.scroll = scrolled.scroll_offset;
                let first_row = (scrolled.scroll_offset - row_height) / (row_height + gap);
                if (first_row < 0n) {
                    first_row = 0n;
                }
                let last_row =
                    (scrolled.scroll_offset + s32(viewport.height) + row_height) /
                    (row_height + gap);
                if (last_row >= count) {
                    last_row = count - 1n;
                }
                let row = rows[index];
                for (let position = first_row; position <= last_row; position += s32(1)) {
                    let row_y = s32(scrolled.content.y) + position * (row_height + gap);
                    let day = DayAgo(position);
                    let label = DateText(day);
                    if (row.counting) {
                        label = WeeklyCountLabel(label, Day(index, day).count, row.target);
                    }
                    DayButton(
                        index,
                        day,
                        label,
                        4400n + position,
                        Bounds(x, row_y, width, row_height),
                        false
                    );
                }
                if (count < HABIT_WEEKLY_MAX_DAYS) {
                    let button_y = s32(scrolled.content.y) + count * (row_height + gap);
                    if (
                        (
                            <Button
                                session={list_state.session}
                                props={{
                                    id: 4500n,
                                    bounds: Bounds(x, button_y, width, Scale(42n)),
                                    label: Locale("habit_load_more_button"),
                                    tone: ButtonTone.ButtonToneNeutral,
                                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                                    disabled: list_state.modal_active
                                }}
                            />
                        )
                    ) {
                        list_state.weekly_days = list_state.weekly_days + HABIT_WEEKLY_LOAD_DAYS;
                        if (list_state.weekly_days > HABIT_WEEKLY_MAX_DAYS) {
                            list_state.weekly_days = HABIT_WEEKLY_MAX_DAYS;
                        }
                    }
                }
                list_state.anchor_day = Bounds(x, top, width, row_height);
            }}
        />
    );
    if (!scrolled.opened) {
        list_state.scroll = scrolled.scroll_offset;
    }
}

function Calendar(index: s32, x: s32, width: s32, top: s32): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let year = list_state.today / 10000n;
    let month = ((list_state.today / 100n) % 100n) + list_state.month_offset;
    while (month < 1n) {
        month += 12n;
        year -= 1n;
    }
    while (month > 12n) {
        month -= 12n;
        year += 1n;
    }
    if (!DateValid(year, month, 1n)) {
        return;
    }
    let header_height = Scale(42n);
    let gap = Scale(6n);
    let arrow_width = Scale(48n);
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4600n,
                    bounds: Bounds(x, top, arrow_width, header_height),
                    label: "<",
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        list_state.month_offset = list_state.month_offset - 1n;
    }
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4601n,
                    bounds: Bounds(x + width - arrow_width, top, arrow_width, header_height),
                    label: ">",
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: list_state.modal_active || list_state.month_offset >= 0n
                }}
            />
        )
    ) {
        list_state.month_offset = list_state.month_offset + 1n;
    }
    let month_keys: [
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string
    ] = [
        "habit_month_1",
        "habit_month_2",
        "habit_month_3",
        "habit_month_4",
        "habit_month_5",
        "habit_month_6",
        "habit_month_7",
        "habit_month_8",
        "habit_month_9",
        "habit_month_10",
        "habit_month_11",
        "habit_month_12"
    ];
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(
                x + arrow_width + gap,
                top,
                width - (arrow_width + gap) * 2n,
                header_height
            ),
            text: Filled(Locale(month_keys[month - 1n]), year, 0n),
            size: list_state.font,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    let weekday = Weekday(year * 10000n + month * 100n + 1n);
    let cell_width = (width - gap * 6n) / 7n;
    let counting = rows[index].counting;
    // A counting habit's day holds its date above its count.
    let cell_height = Scale(counting ? 56n : 50n);
    let day: s32 = 1n;
    while (DateValid(year, month, day)) {
        let slot = weekday + day - 1n;
        let column = slot % 7n;
        let row = slot / 7n;
        let day_index = year * 10000n + month * 100n + day;
        if (day_index <= list_state.today) {
            DayButton(
                index,
                day_index,
                Number(s64(day)),
                4700n + slot,
                Bounds(
                    x + column * (cell_width + gap),
                    top + header_height + gap + row * (cell_height + gap),
                    cell_width,
                    cell_height
                ),
                counting
            );
        }
        day += 1n;
    }
}

function HabitPage(): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let x = s32(list_state.bounds.x);
    let y = s32(list_state.bounds.y);
    let width = s32(list_state.bounds.width);
    let bottom = y + s32(list_state.bounds.height);
    let index = list_state.selected;
    let top = PageHeader(x, y, width, rows[index].name);
    if (top < 0n) {
        Ask(HABITS_LIST_BACK, index, 0n);
        return;
    }
    top = ViewSwitch(x, width, top);
    if (list_state.view_mode === HABIT_VIEW_CALENDAR) {
        Calendar(index, x, width, top);
    } else {
        Weekly(index, x, width, top, bottom);
    }
}

// Draws the habit list, or the selected habit's page, from the host's frame
// and returns what the page asks for.
export function HabitsListView(message: HabitsMessage): HabitsMessage {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    Model.SetList(ReadHabitsListHost());
    list_state.action = HABITS_LIST_NONE;
    list_state.action_habit = -1n;
    list_state.action_day = 0n;
    list_state.action_target = -1n;
    list_state.action_decrement = false;
    list_state.save = false;
    list_state.anchor_progress = {};
    list_state.anchor_coins = {};
    list_state.anchor_table = {};
    list_state.anchor_history = {};
    list_state.anchor_statistics = {};
    list_state.anchor_edit = {};
    list_state.anchor_day = {};
    list_state.first_day = {};
    Model.SetPointerFrame(SamplePointer());
    ReadRows();
    let page =
        list_state.screen_mode === HABITS_SCREEN_HISTORY &&
        list_state.selected >= 0n &&
        list_state.selected < Model.row_count &&
        !rows[list_state.selected].deactivated;
    if (page) {
        HabitPage();
    } else {
        Overview();
    }
    WriteHabitsListHost(*list_state);
    message.succeeded = true;
    return message;
}
