import * as Model from "habit_list_view";
import {
    Ask,
    Bounds,
    LIST_BACK_SHAPE,
    Locale,
    NewStrong,
    Scale,
    TitleFont,
    Width
} from "habit_list_view";
import { HABIT_VIEW_CALENDAR, HABIT_VIEW_WEEKLY } from "habit_types";
import { HABITS_LIST_BACK } from "habits_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Button } from "kryon/tsx/button";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Text } from "kryon/tsx/text";
import { Weekly, Calendar } from "habit_list_history";

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

export function HabitPage(): void {
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
