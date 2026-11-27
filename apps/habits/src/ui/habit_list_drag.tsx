import * as Model from "habit_list_view";
import {
    Alpha,
    Ask,
    Bounds,
    EdgeScroll,
    EndDrag,
    Filled,
    Intersection,
    LIST_CARD_HOLD_SECONDS,
    Locale,
    PointIn,
    RowDrag,
    RowTouch,
    Scale
} from "habit_list_view";
import { HABITS_LIST_DEACTIVATE, HABITS_LIST_MOVE, HABITS_LIST_REACTIVATE } from "habits_types";
import { ButtonEmphasis, ButtonTone, ContentAlignment } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Button } from "kryon/tsx/button";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import { Fill, Outline, PressButton } from "habit_list_visuals";
import { HabitIcon } from "habit_list_marks";

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

export function DeactivatedRow(index: s32, bounds: Rectangle): void {
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

export function InactiveHeader(bounds: Rectangle, count: s32, pad: s32): void {
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

export function Drop(
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
