import * as Model from "habit_list_view";
import {
    Alpha,
    Ask,
    Bounds,
    DayAgo,
    DayCountText,
    Filled,
    FitFont,
    LIST_CARD_HOLD_SECONDS,
    LIST_CARD_RADIUS,
    LIST_DETAIL_ACTION_SIZE,
    LIST_DETAIL_PADDING,
    LIST_DETAIL_TITLE_GAP,
    LIST_DETAIL_TITLE_HEIGHT,
    LIST_FIGURE_CARD_HEIGHT,
    LIST_NAME_MAXIMUM_WIDTH,
    LIST_NAME_MIN_WIDTH,
    LIST_NAME_RESIZE_HANDLE_WIDTH,
    LIST_RESIZE_SHAPE,
    LIST_ROW_SMALL_ICON_SIZE,
    LIST_ROW_ICON_SIZE,
    Locale,
    RowDrag,
    RowTouch,
    Scale,
    WeekdayLabel
} from "habit_list_view";
import { HABITS_LIST_EDIT, HABITS_LIST_HISTORY, HABITS_LIST_STATISTICS } from "habits_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { IconType } from "kryon/icon";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { HabitTableLayout } from "table_layout";
import { Fill, PressButton, FigureCard } from "habit_list_visuals";
import { HabitIcon, DayCell } from "habit_list_marks";

export function TableHeader(x: s32, y: s32, layout: HabitTableLayout, height: s32): void {
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

export function NameResize(x: s32, y: s32, height: s32, name_width: s32): void {
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

export function Row(
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

export function RowDetail(index: s32, first_active: boolean, bounds: Rectangle, pad: s32): void {
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
