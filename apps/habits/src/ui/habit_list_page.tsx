import * as Cards from "habit_cards";
import * as Shared from "habit_shared";
import * as Model from "habit_list_view";
import { HABIT_VIEW_CALENDAR, HABIT_VIEW_WEEKLY } from "habit_types";
import { HABITS_LIST_BACK } from "habits_types";
import * as NativeSegmentedControl from "kryon/segmented_control";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Weekly, Calendar } from "habit_list_history";

function PageHeader(x: s32, y: s32, width: s32, title: string): s32 {
    return Cards.PageHeader(
        Model.SurfaceStyle(),
        Shared.Bounds(x, y, width, 0n),
        4300n,
        title,
        "",
        true,
        Model.Locale("back_button")
    );
}

function ViewSwitch(x: s32, width: s32, top: s32): s32 {
    const list_state = Model.CurrentList();
    let options: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] = [
        { label: Model.Locale("habit_focus_week") },
        { label: Model.Locale("habit_focus_calendar") }
    ];
    let selection = SegmentedControl({
        session: list_state.session,
        props: {
            id: 4301n,
            bounds: Shared.Bounds(x, top, width, Model.Scale(42n)),
            height: Model.Scale(42n),
            selected_index: list_state.view_mode === HABIT_VIEW_CALENDAR ? 1n : 0n,
            has_selection: true,
            disabled: list_state.modal_active
        },
        options: nativeSlice(options)
    });
    if (selection.changed) {
        list_state.view_mode =
            selection.selected_index === 1n ? HABIT_VIEW_CALENDAR : HABIT_VIEW_WEEKLY;
        list_state.scroll = 0n;
        list_state.save = true;
    }
    return top + Model.Scale(54n);
}

export function HabitPage(): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let x = s32(list_state.bounds.x);
    let y = s32(list_state.bounds.y);
    let width = s32(list_state.bounds.width);
    let bottom = y + s32(list_state.bounds.height);
    let index = list_state.selected;
    let top = PageHeader(x, y, width, nativeAt(rows, index).name);
    if (top < 0n) {
        Model.Ask(HABITS_LIST_BACK, index, 0n);
        return;
    }
    top = ViewSwitch(x, width, top);
    if (list_state.view_mode === HABIT_VIEW_CALENDAR) {
        Calendar(index, x, width, top);
    } else {
        Weekly(index, x, width, top, bottom);
    }
}
