import * as Model from "habit_list_view";
import { HABITS_SCREEN_HISTORY } from "habit_types";
import { HABITS_LIST_NONE, HabitsMessage } from "habits_types";
import { SamplePointer } from "kryon/pointer_input";
import { Overview } from "habit_list_overview";
import { HabitPage } from "habit_list_page";

export function HabitsListView(message: HabitsMessage): HabitsMessage {
    const list_state = Model.CurrentList();
    Model.SetList(Model.ReadHabitsListHost());
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
    Model.ReadRows();
    let page =
        list_state.screen_mode === HABITS_SCREEN_HISTORY &&
        list_state.selected >= 0n &&
        list_state.selected < Model.row_count &&
        !Model.Row(list_state.selected).deactivated;
    if (page) {
        HabitPage();
    } else {
        Overview();
    }
    Model.WriteHabitsListHost(nativeDeref(list_state));
    message.succeeded = true;
    return message;
}
