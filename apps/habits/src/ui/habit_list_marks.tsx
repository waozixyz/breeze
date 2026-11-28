import * as Shared from "habit_shared";
import { HabitIconShape } from "habit_icons";
import * as Model from "habit_list_view";
import { HABITS_LIST_DAY } from "habits_types";
import { Color, DarkenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Press } from "kryon/tsx/press";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import { Circle } from "habit_list_visuals";

export function HabitIcon(index: s32, bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let row = Model.Row(index);
    let radius = s32(bounds.width * 0.5);
    let center_x = s32(bounds.x) + radius;
    let center_y = s32(bounds.y) + radius;
    Circle(center_x, center_y, radius, DarkenColor(row.color, 10n));
    Circle(center_x, center_y, radius - Model.Scale(1n), row.color);
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
                color: Model.TextOn(row.color)
            }}
        />;
        return;
    }
    <Text
        session={list_state.session}
        props={{
            bounds: bounds,
            text: Model.FirstLetter(row.name),
            size: list_state.font,
            class_name: Model.InkClass(row.color),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

export function DayDot(
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
        Circle(center_x, center_y, radius - Model.Scale(1n), accent);
        if (!show_count) {
            let reach = radius - Model.Scale(4n);
            <SvgIcon
                session={list_state.session}
                props={{
                    bounds: Shared.Bounds(
                        center_x - reach,
                        center_y - reach,
                        reach * 2n,
                        reach * 2n
                    ),
                    shape: Model.LIST_CHECK_SHAPE,
                    color: Model.TextOn(accent)
                }}
            />;
        }
    } else {
        Circle(center_x, center_y, radius, Shared.Alpha(list_state.text_color, 0.26));
        Circle(center_x, center_y, radius - Model.Scale(1n), list_state.surface_color);
        if (half) {
            let face = radius - Model.Scale(1n);
            <SvgIcon
                session={list_state.session}
                props={{
                    bounds: Shared.Bounds(center_x - face, center_y - face, face * 2n, face * 2n),
                    shape: Model.LIST_HALF_DOT_SHAPE,
                    color: accent
                }}
            />;
        }
    }
    if (show_count) {
        let count_text = Shared.Number(s64(count));
        <Text
            session={list_state.session}
            props={{
                bounds: Shared.Bounds(
                    center_x - radius,
                    center_y - radius,
                    radius * 2n,
                    radius * 2n
                ),
                text: count_text,
                size: Model.FitFont(
                    count_text,
                    radius * 2n - Model.Scale(2n),
                    radius + Model.Scale(4n),
                    Model.Scale(8n)
                ),
                class_name: complete ? Model.InkClass(accent) : 0n,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
}

export function DayCell(
    index: s32,
    first_active: boolean,
    day: s32,
    column: s32,
    bounds: Rectangle
): void {
    const list_state = Model.CurrentList();
    let row = Model.Row(index);
    let state = Model.Day(index, day);
    let shown = state.planned || state.complete || state.count > 0n || state.running;
    let id = 5200000n + index * 16n + column;
    let press = Press({
        session: list_state.session,
        props: {
            key: u64(id),
            id: id,
            bounds: bounds,
            now: list_state.now,
            disabled: list_state.modal_active || !shown
        }
    });
    if (first_active && column === 0n) {
        list_state.first_day = bounds;
    }
    let center_x = s32(bounds.x + bounds.width * 0.5);
    let center_y = s32(bounds.y + bounds.height * 0.5);
    let radius = s32(bounds.width * 0.3);
    if (radius > Model.Scale(14n)) {
        radius = Model.Scale(14n);
    }
    if (radius < Model.Scale(9n)) {
        radius = Model.Scale(9n);
    }
    if (
        shown &&
        !list_state.modal_active &&
        !list_state.touch &&
        !list_state.dragging &&
        Model.PointIn(Model.Pointer(), bounds)
    ) {
        Circle(center_x, center_y, radius + Model.Scale(5n), Shared.Alpha(row.color, 0.24));
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
            Model.OffDay(row.color),
            state.complete,
            state.running,
            row.counting,
            state.count
        );
    }
    if (press.clicked) {
        Model.Ask(HABITS_LIST_DAY, index, day);
    }
}
