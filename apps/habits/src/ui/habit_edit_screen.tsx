// The habit editor: a habit's details (its name, description, colour and
// icon), its routine (how it repeats, its days and when it reminds), and how
// it is tracked (how hard it is and the coins a done day earns, counting or
// measuring spans, linked practices, and the questions it asks when a day is
// done). The host keeps the habit being edited; the editor changes it and
// asks the host to save it, delete it, open the practice picker, or add or
// remove a question.
import { HabitsCoinColor } from "coin_color";
import {
    HabitCoinParse,
    HabitDifficultyAt,
    HabitDifficultyHalfCoins,
    HabitDifficultyIndex
} from "habit_coins";
import * as Model from "habit_edit_view";
import {
    AnswerLabel,
    FirstLetterEnd,
    ReminderHourLabel,
    DaySelected,
    DayMask,
    ToggleDayMask,
    PracticeLinked,
    Ask,
    Bounds,
    Clipboard,
    CoinText,
    Columns,
    ContentHeight,
    CounterText,
    DifficultyEarns,
    DifficultyHeight,
    DifficultyLabel,
    EDIT_CONTENT_MAX_WIDTH,
    EDIT_ICON_BUTTON_BASE,
    EDIT_QUESTION_GAP,
    EDIT_QUESTION_PADDING,
    EDIT_SPAN_FIELD_CODE,
    EditColor,
    EnsureVisible,
    Filled,
    FitFont,
    FocusOnly,
    FormulaValid,
    GoalHasValues,
    GoalMenuWidth,
    GoalOptions,
    GoalTexts,
    GridBounds,
    GridHeight,
    HasSpanStart,
    HintHeight,
    IconSlots,
    Locale,
    NewHours,
    NewKinds,
    NewMonths,
    NewOptions,
    NewOptions1NativeDropdownOption,
    NewOptions6NativeDropdownOption,
    NewParts,
    NewRepeats,
    NewTypes,
    NewWeeks,
    Normalize,
    Number,
    QuestionCardHeight,
    ReadHabitsEditHost,
    ReadHabitsEditPracticeHost,
    ReadQuestions,
    RepeatPhrase,
    Replaced,
    Scale,
    SectionBody,
    SectionHeight,
    SetRepeat,
    SpanGoalHeight,
    SpanTexts,
    SpreadBounds,
    Width,
    WriteHabitsEditHost,
    WriteHabitsEditQuestionHost
} from "habit_edit_view";
import { HABIT_ICON_LETTER, HabitIconShape } from "habit_icons";
import { HABIT_LINK_DIARY, HabitLinkSelect } from "habit_links";
import { HabitGoalDefault, HabitSpanGoalDefault, HabitTimeTypedNumber } from "habit_questions";
import { HabitScheduleDateOf, HabitScheduleMonthLength } from "habit_schedule";
import {
    HABIT_ANSWER_NUMBER,
    HABIT_ANSWER_TYPE_COUNT,
    HABIT_COUNTER_TARGET_MAX,
    HABIT_DESCRIPTION_SIZE,
    HABIT_DIFFICULTY_EASY,
    HABIT_DIFFICULTY_HARD,
    HABIT_DIFFICULTY_MEDIUM,
    HABIT_DIFFICULTY_VERY_HARD,
    HABIT_FORMULA_SIZE,
    HABIT_GOAL_ABOVE_AVERAGE,
    HABIT_GOAL_AT_LEAST,
    HABIT_GOAL_AT_MOST,
    HABIT_GOAL_BELOW_AVERAGE,
    HABIT_GOAL_BETWEEN,
    HABIT_GOAL_NONE,
    HABIT_NAME_SIZE,
    HABIT_QUESTION_MAX,
    HABIT_QUESTION_TEXT_SIZE,
    HABIT_REPEAT_DAILY,
    HABIT_REPEAT_FORMULA,
    HABIT_REPEAT_MONTHLY,
    HABIT_REPEAT_NONE,
    HABIT_REPEAT_WEEKLY,
    HABIT_REPEAT_YEARLY,
    HABIT_SCHEDULE_EVERY_MAX
} from "habit_types";
import {
    HABITS_EDIT_ADD_QUESTION,
    HABITS_EDIT_BACK,
    HABITS_EDIT_DELETE,
    HABITS_EDIT_NONE,
    HABITS_EDIT_PRACTICES,
    HABITS_EDIT_PRACTICES_DONE,
    HABITS_EDIT_REMOVE_QUESTION,
    HABITS_EDIT_SAVE,
    HabitsMessage
} from "habits_types";
import { HabitsEditQuestion } from "habits_ui_types";
import * as NativeButton from "kryon/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import { SemanticKind } from "kryon/semantic";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import * as NativeTextField from "kryon/text_field";
import { TextHeight } from "kryon/text_measure";
import * as NativeToggle from "kryon/toggle";
import { ToggleSize } from "kryon/toggle_measure";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Checkbox } from "kryon/tsx/checkbox";
import { Dropdown } from "kryon/tsx/dropdown";
import { Fieldset } from "kryon/tsx/fieldset";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Spinbox } from "kryon/tsx/spinbox";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { TextArea } from "kryon/tsx/text_area";
import { ControlledTextField } from "kryon/tsx/text_field";
import { TimePicker } from "kryon/tsx/time_picker";
import { TitleBar } from "kryon/tsx/title_bar";
import { Toggle } from "kryon/tsx/toggle";
import * as NativeCoinIcon from "mingcute/mingcute_filled_copper_coin";

function Label(text: string, x: s32, y: s32, width: s32, height: s32): void {
    const edit_state = Model.CurrentEditor();
    <Text
        session={edit_state.session}
        props={{ bounds: Bounds(x, y, width, height), text: text }}
    />;
}

// A label beside a row's 44-unit control, centred on it.
function RowLabel(text: string, x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    <Text
        session={edit_state.session}
        props={{
            bounds: Bounds(x, y + Scale(4n), width, Scale(44n)),
            text: text,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}

function Step(id: s32, label: string, bounds: Rectangle, disabled: boolean): boolean {
    const edit_state = Model.CurrentEditor();
    return (
        <Button
            session={edit_state.session}
            props={{
                id: id,
                bounds: bounds,
                label: label,
                disabled: disabled,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }}
        />
    );
}

// A planned day's button lights up in the habit's colour, as its circles do
// in the habit table, with its label in black or white on it.
function LitDay(bounds: Rectangle, label: string): void {
    const edit_state = Model.CurrentEditor();
    let color = edit_state.color;
    color.a = 255n;
    <Box
        session={edit_state.session}
        props={{ bounds: bounds, fill: color, radius: bounds.width * 0.5 }}
    />;
    let luma = s32(color.r) * 299n + s32(color.g) * 587n + s32(color.b) * 114n;
    <Text
        session={edit_state.session}
        props={{
            bounds: bounds,
            text: label,
            size: FitFont(label, s32(bounds.width) - Scale(6n), edit_state.small_font, Scale(9n)),
            class_name: luma >= 128000n ? edit_state.ink_dark_class : edit_state.ink_light_class,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

// Round day buttons from Monday to Sunday: a lit day is planned, and a tap
// turns it on or off. The last lit day stays.
function WeekdayButtons(x: s32, y: s32, width: s32): s32 {
    const edit_state = Model.CurrentEditor();
    let days: [string, string, string, string, string, string, string] = [
        Locale("habit_day_mon"),
        Locale("habit_day_tue"),
        Locale("habit_day_wed"),
        Locale("habit_day_thu"),
        Locale("habit_day_fri"),
        Locale("habit_day_sat"),
        Locale("habit_day_sun")
    ];
    for (let day = s32(0n); day <= 6n; day += s32(1)) {
        let selected = DaySelected(edit_state.weekdays, day);
        let bounds = SpreadBounds(x, y, width, 7n, day);
        let clicked = (
            <Button
                session={edit_state.session}
                props={{
                    id: 7710n + day,
                    bounds: bounds,
                    label: days[day],
                    circle: true,
                    fit_content: true,
                    selected: selected,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        );
        if (selected) {
            LitDay(bounds, days[day]);
        }
        if (clicked) {
            let mask = ToggleDayMask(edit_state.weekdays, day);
            if (mask !== 0n) {
                edit_state.weekdays = mask;
            }
        }
    }
    return y + GridHeight(7n, width);
}

// The days of the month from the 1st to the 31st, and the last day.
function MonthDayButtons(x: s32, y: s32, width: s32): s32 {
    const edit_state = Model.CurrentEditor();
    for (let day = s32(1n); day <= 31n; day += s32(1)) {
        let selected = DaySelected(edit_state.month_days, day - 1n);
        let label = Number(s64(day));
        let bounds = GridBounds(x, y, width, day - 1n);
        let clicked = (
            <Button
                session={edit_state.session}
                props={{
                    id: 7730n + day,
                    bounds: bounds,
                    label: label,
                    circle: true,
                    selected: selected,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        );
        if (selected) {
            LitDay(bounds, label);
        }
        if (clicked) {
            let mask = ToggleDayMask(edit_state.month_days, day - 1n);
            if (mask !== 0n || edit_state.last_day) {
                edit_state.month_days = mask;
            }
        }
    }
    y += GridHeight(31n, width);
    let last = edit_state.last_day;
    if (
        (
            <Button
                session={edit_state.session}
                props={{
                    id: 7729n,
                    bounds: Bounds(x, y, width, Scale(40n)),
                    label: Locale("habit_month_last_day"),
                    selected: last,
                    tone: last ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
                    emphasis: last
                        ? ButtonEmphasis.ButtonEmphasisFilled
                        : ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        if (!last || edit_state.month_days !== 0n) {
            edit_state.last_day = !last;
        }
    }
    return y + Scale(48n);
}

// A monthly schedule plans days of the month, or a weekday in a week of the
// month such as the last Friday.
function Monthly(x: s32, y: s32, width: s32): s32 {
    const edit_state = Model.CurrentEditor();
    let options: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] = [
        { label: Locale("habit_month_by_day") },
        { label: Locale("habit_month_by_weekday") }
    ];
    let selection = (
        <SegmentedControl
            session={edit_state.session}
            props={{
                id: 7720n,
                bounds: Bounds(x, y + Scale(4n), width, Scale(42n)),
                height: Scale(42n),
                selected_index: edit_state.week_of_month !== 0n ? 1n : 0n,
                has_selection: true
            }}
            options={options[:]}
        />
    );
    if (selection.changed) {
        let anchor_day = edit_state.start;
        if (anchor_day === 0n) {
            anchor_day = edit_state.today;
        }
        let anchor = HabitScheduleDateOf(anchor_day);
        if (selection.selected_index === 1n) {
            edit_state.week_of_month = (anchor.day - 1n) / 7n + 1n;
            if (anchor.day + 7n > anchor.month_length) {
                edit_state.week_of_month = -1n;
            }
            edit_state.weekdays = DayMask(anchor.weekday);
        } else {
            edit_state.week_of_month = 0n;
        }
        Normalize();
    }
    y += Scale(52n);
    if (edit_state.week_of_month === 0n) {
        return MonthDayButtons(x, y, width);
    }
    let control_width = Scale(168n);
    RowLabel(Locale("habit_week_of_month_label"), x, y, width - control_width - Scale(8n));
    let week_keys: [string, string, string, string, string, string] = [
        "habit_week_first",
        "habit_week_second",
        "habit_week_third",
        "habit_week_fourth",
        "habit_week_fifth",
        "habit_week_last"
    ];
    let weeks = NewWeeks();
    for (let index = s32(0n); index <= 5n; index += s32(1)) {
        weeks[index].label = Locale(week_keys[index]);
    }
    let week_menu = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7721n,
                bounds: Bounds(x + width - control_width, y + Scale(4n), control_width, Scale(44n)),
                selected_index: edit_state.week_of_month > 0n ? edit_state.week_of_month - 1n : 5n
            }}
            options={weeks[:]}
        />
    );
    if (week_menu.changed) {
        edit_state.week_of_month = week_menu.selected_index + 1n;
        if (week_menu.selected_index === 5n) {
            edit_state.week_of_month = -1n;
        }
    }
    y += Scale(52n);
    return WeekdayButtons(x, y, width);
}

// A yearly schedule's month and day.
function Yearly(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let date = HabitScheduleDateOf(edit_state.start);
    if (!date.valid) {
        date = HabitScheduleDateOf(edit_state.today);
    }
    let gap = Scale(8n);
    let month_width = (width - gap) / 2n;
    let keys: [
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
        "habit_month_name_1",
        "habit_month_name_2",
        "habit_month_name_3",
        "habit_month_name_4",
        "habit_month_name_5",
        "habit_month_name_6",
        "habit_month_name_7",
        "habit_month_name_8",
        "habit_month_name_9",
        "habit_month_name_10",
        "habit_month_name_11",
        "habit_month_name_12"
    ];
    let months = NewMonths();
    for (let month = s32(0n); month <= 11n; month += s32(1)) {
        months[month].label = Locale(keys[month]);
    }
    let month_menu = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7724n,
                bounds: Bounds(x, y + Scale(4n), month_width, Scale(44n)),
                selected_index: date.month - 1n
            }}
            options={months[:]}
        />
    );
    let chosen_month = date.month;
    if (month_menu.changed) {
        chosen_month = month_menu.selected_index + 1n;
    }
    let stepped = (
        <Spinbox
            session={edit_state.session}
            props={{
                id: 7725n,
                bounds: Bounds(
                    x + month_width + gap,
                    y + Scale(4n),
                    width - month_width - gap,
                    Scale(44n)
                ),
                label: Locale("habit_every_year"),
                min: 1n,
                max: 31n,
                step: 1n,
                value: date.day,
                wrap: true,
                value_text: Number(s64(date.day))
            }}
        />
    );
    let chosen_day = date.day;
    if (stepped.changed) {
        chosen_day = stepped.value;
    }
    if (chosen_month !== date.month || chosen_day !== date.day) {
        let length = HabitScheduleMonthLength(date.year, chosen_month);
        if (chosen_day > length) {
            chosen_day = length;
        }
        edit_state.start = date.year * 10000n + chosen_month * 100n + chosen_day;
    }
}

function FormulaField(bounds: Rectangle): boolean {
    const edit_state = Model.CurrentEditor();
    let focused = edit_state.formula_focused;
    let result = (
        <ControlledTextField
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/formula"),
                bounds: bounds,
                value: edit_state.formula,
                cursor: edit_state.formula_cursor,
                anchor: edit_state.formula_anchor,
                scroll_x: edit_state.formula_scroll_x,
                focused: focused,
                focus_id: 7770n,
                max_bytes: HABIT_FORMULA_SIZE - 1n,
                max_codepoints: HABIT_FORMULA_SIZE - 1n,
                input: focused ? edit_state.input : {}
            }}
        />
    );
    if (result.edit.changed) {
        edit_state.formula = Replaced(
            edit_state.formula,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            HABIT_FORMULA_SIZE - 1n
        );
    }
    edit_state.formula_cursor = result.cursor;
    edit_state.formula_anchor = result.anchor;
    edit_state.formula_scroll_x = result.scroll_x;
    if (result.focused) {
        FocusOnly(4n);
    } else {
        edit_state.formula_focused = false;
    }
    Clipboard(result);
    return result.focused;
}

// The schedule reads as a sentence: how it repeats, with buttons for how
// often, then its days and when it reminds.
function Routine(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let row = Scale(52n);
    let step_width = Scale(44n);
    let counted =
        edit_state.repeat >= HABIT_REPEAT_DAILY && edit_state.repeat <= HABIT_REPEAT_YEARLY;
    let menu_width = width;
    if (counted) {
        menu_width = width - step_width * 2n - Scale(8n);
    }
    let repeats = NewRepeats();
    for (let index = s32(0n); index <= 5n; index += s32(1)) {
        repeats[index].label = RepeatPhrase(index + 1n, edit_state.every);
    }
    let repeat_menu = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7700n,
                bounds: Bounds(x, y + Scale(4n), menu_width, Scale(44n)),
                selected_index: edit_state.repeat - 1n
            }}
            options={repeats[:]}
        />
    );
    if (repeat_menu.changed) {
        SetRepeat(repeat_menu.selected_index + 1n);
    }
    if (counted) {
        if (
            Step(
                7702n,
                "-",
                Bounds(x + menu_width + Scale(4n), y + Scale(4n), step_width, Scale(44n)),
                edit_state.every <= 1n
            )
        ) {
            edit_state.every = edit_state.every - 1n;
            Normalize();
        }
        if (
            Step(
                7703n,
                "+",
                Bounds(x + width - step_width, y + Scale(4n), step_width, Scale(44n)),
                edit_state.every >= HABIT_SCHEDULE_EVERY_MAX
            )
        ) {
            edit_state.every = edit_state.every + 1n;
            Normalize();
        }
    }
    y += row;
    if (edit_state.repeat === HABIT_REPEAT_WEEKLY) {
        y = WeekdayButtons(x, y, width);
    } else if (edit_state.repeat === HABIT_REPEAT_MONTHLY) {
        y = Monthly(x, y, width);
    } else if (edit_state.repeat === HABIT_REPEAT_YEARLY) {
        Yearly(x, y, width);
        y += row;
    } else if (edit_state.repeat === HABIT_REPEAT_FORMULA) {
        let formula_bounds = Bounds(x, y + Scale(4n), width, Scale(44n));
        let was_focused = edit_state.formula_focused;
        if (FormulaField(formula_bounds) && !was_focused) {
            EnsureVisible(formula_bounds);
        }
        y += row;
        let hint_height = HintHeight(width);
        <Text
            session={edit_state.session}
            props={{
                bounds: Bounds(x, y, width, hint_height),
                text: Locale("habit_formula_hint"),
                size: edit_state.small_font,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        y += hint_height + Scale(8n);
        if (!FormulaValid()) {
            Label(Locale("habit_formula_invalid"), x, y, width, Scale(24n));
            y += Scale(28n);
        }
    }
    if (edit_state.repeat === HABIT_REPEAT_NONE) {
        return;
    }
    RowLabel(Locale("habit_reminder_label"), x, y, width - Scale(144n));
    let hours = NewHours();
    hours[0n].label = Locale("habit_reminder_off");
    for (let hour = s32(0n); hour <= 23n; hour += s32(1)) {
        hours[hour + 1n].label = ReminderHourLabel(hour);
    }
    let hour_menu = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7400n,
                bounds: Bounds(x + width - Scale(136n), y + Scale(4n), Scale(136n), Scale(44n)),
                selected_index: edit_state.reminder_hour + 1n
            }}
            options={hours[:]}
        />
    );
    if (hour_menu.changed) {
        edit_state.reminder_hour = hour_menu.selected_index - 1n;
    }
}

// ---- The details ------------------------------------------------------------
function NameField(bounds: Rectangle): boolean {
    const edit_state = Model.CurrentEditor();
    let focused = edit_state.name_focused;
    let result = (
        <ControlledTextField
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/name"),
                bounds: bounds,
                value: edit_state.name,
                cursor: edit_state.name_cursor,
                anchor: edit_state.name_anchor,
                scroll_x: edit_state.name_scroll_x,
                focused: focused,
                focus_id: 7511n,
                max_bytes: HABIT_NAME_SIZE - 1n,
                max_codepoints: HABIT_NAME_SIZE - 1n,
                input: focused ? edit_state.input : {}
            }}
        />
    );
    if (result.edit.changed) {
        let changed = Replaced(
            edit_state.name,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            HABIT_NAME_SIZE - 1n
        );
        if (changed !== edit_state.name) {
            edit_state.name_error = 0n;
        }
        edit_state.name = changed;
    }
    edit_state.name_cursor = result.cursor;
    edit_state.name_anchor = result.anchor;
    edit_state.name_scroll_x = result.scroll_x;
    edit_state.name_focused = result.focused;
    if (result.focused) {
        FocusOnly(1n);
    }
    Clipboard(result);
    return result.focused;
}

function DescriptionField(bounds: Rectangle): boolean {
    const edit_state = Model.CurrentEditor();
    let focused = edit_state.description_focused;
    let result = (
        <TextArea
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/description"),
                bounds: bounds,
                value: edit_state.description,
                cursor: edit_state.description_cursor,
                anchor: edit_state.description_anchor,
                scroll_y: edit_state.description_scroll_y,
                focused: focused,
                focus_id: 7512n,
                max_bytes: HABIT_DESCRIPTION_SIZE - 1n,
                max_codepoints: HABIT_DESCRIPTION_SIZE - 1n,
                wrap: true,
                input: focused ? edit_state.area_input : {}
            }}
        />
    );
    if (result.edit.changed) {
        edit_state.description = Replaced(
            edit_state.description,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            HABIT_DESCRIPTION_SIZE - 1n
        );
    }
    edit_state.description_cursor = result.cursor;
    edit_state.description_anchor = result.anchor;
    edit_state.description_scroll_y = result.scroll_y;
    edit_state.description_focused = result.focused;
    if (result.focused) {
        FocusOnly(2n);
    }
    if (result.clipboard_write) {
        edit_state.clipboard_write = true;
        edit_state.clipboard_text = result.clipboard_text;
    }
    return result.focused;
}

function Colors(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let columns = Columns(width);
    let count: s32 = edit_state.more_colors ? 12n : 7n;
    for (let index = s32(0n); index < count; index += s32(1)) {
        let more = index === 6n && !edit_state.more_colors;
        let swatch = EditColor(index);
        let chosen =
            !more &&
            edit_state.color.r === swatch.r &&
            edit_state.color.g === swatch.g &&
            edit_state.color.b === swatch.b;
        if (
            (
                <Button
                    session={edit_state.session}
                    props={{
                        id: 7530n + index,
                        bounds: Bounds(
                            x + (index % columns) * Scale(48n) + Scale(4n),
                            y + (index / columns) * Scale(44n) + Scale(2n),
                            Scale(40n),
                            Scale(40n)
                        ),
                        label: more ? "..." : "",
                        circle: true,
                        selected: chosen,
                        swatch: !more,
                        swatch_color: swatch,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled
                    }}
                />
            )
        ) {
            if (more) {
                edit_state.more_colors = true;
            } else {
                edit_state.color = swatch;
            }
        }
    }
}

// The icons a habit can show in the habit list. The first is the first
// letter of its name. Until all are shown, one row holds the first icons,
// the chosen one, and a button that shows the rest.
function Icons(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let name = edit_state.name;
    const first = FirstLetterEnd(name);
    let chosen_icon = edit_state.icon;
    if (chosen_icon === HABIT_ICON_LETTER) {
        chosen_icon = 0n;
    }
    let slots = IconSlots(width);
    let collapsed = !edit_state.more_icons;
    let shown = collapsed ? slots - 1n : slots;
    for (let slot = s32(0n); slot < shown; slot += s32(1)) {
        let icon = slot;
        if (collapsed && slot === shown - 1n && chosen_icon >= shown) {
            icon = chosen_icon;
        }
        let chosen: s32 = icon;
        if (icon === 0n) {
            chosen = HABIT_ICON_LETTER;
        }
        let selected = edit_state.icon === chosen;
        let button: NativeButton.Props = {
            id: EDIT_ICON_BUTTON_BASE + icon,
            bounds: GridBounds(x, y - Scale(2n), width, slot),
            circle: true,
            selected: selected,
            tone: selected ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
            emphasis: selected
                ? ButtonEmphasis.ButtonEmphasisFilled
                : ButtonEmphasis.ButtonEmphasisSoft
        };
        if (icon === 0n) {
            button.label = name.count > 0n ? name[0n:first] : "-";
        } else {
            button.icon_shape = HabitIconShape(icon);
            button.icon_only = true;
        }
        if ((<Button session={edit_state.session} props={button} />)) {
            edit_state.icon = chosen;
        }
    }
    if (collapsed) {
        if (
            (
                <Button
                    session={edit_state.session}
                    props={{
                        id: 7559n,
                        bounds: GridBounds(x, y - Scale(2n), width, shown),
                        circle: true,
                        label: "...",
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            edit_state.more_icons = true;
        }
    }
}

function Details(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let label_height = Scale(24n);
    Label(Locale("habit_name_label"), x, y, width, label_height);
    y += label_height + Scale(4n);
    let name_bounds = Bounds(x, y, width, Scale(44n));
    let was_focused = edit_state.name_focused;
    if (NameField(name_bounds) && !was_focused) {
        EnsureVisible(name_bounds);
    }
    y += Scale(54n);
    Label(Locale("habit_description_label"), x, y, width, label_height);
    y += label_height + Scale(4n);
    let description_bounds = Bounds(x, y, width, Scale(80n));
    was_focused = edit_state.description_focused;
    if (DescriptionField(description_bounds) && !was_focused) {
        EnsureVisible(description_bounds);
    }
    y += Scale(90n);
    Label(Locale("habit_color_label"), x, y, width, label_height);
    y += label_height + Scale(4n);
    Colors(x, y, width);
    let columns = Columns(width);
    let colors: s32 = edit_state.more_colors ? 12n : 7n;
    y += ((colors + columns - 1n) / columns) * Scale(44n) + Scale(10n);
    Label(Locale("habit_icon_label"), x, y, width, label_height);
    y += label_height + Scale(4n);
    Icons(x, y, width);
}

function CoinField(bounds: Rectangle): void {
    const edit_state = Model.CurrentEditor();
    if (!edit_state.coin_focused) {
        edit_state.coin_text = CoinText(edit_state.coin_halves);
        edit_state.coin_cursor = s32(edit_state.coin_text.count);
        edit_state.coin_anchor = edit_state.coin_cursor;
    }
    let focused = edit_state.coin_focused;
    let result = (
        <ControlledTextField
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/coins"),
                bounds: bounds,
                value: edit_state.coin_text,
                cursor: edit_state.coin_cursor,
                anchor: edit_state.coin_anchor,
                scroll_x: edit_state.coin_scroll_x,
                focused: focused,
                focus_id: 7607n,
                max_bytes: 7n,
                max_codepoints: 7n,
                input: focused ? edit_state.input : {}
            }}
        />
    );
    if (result.edit.changed) {
        edit_state.coin_text = Replaced(
            edit_state.coin_text,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            7n
        );
        let halves = edit_state.coin_halves;
        if (HabitCoinParse(edit_state.coin_text, &halves)) {
            edit_state.coin_halves = halves;
        }
    }
    edit_state.coin_cursor = result.cursor;
    edit_state.coin_anchor = result.anchor;
    edit_state.coin_scroll_x = result.scroll_x;
    edit_state.coin_focused = result.focused;
    if (result.focused) {
        FocusOnly(7n);
    }
    Clipboard(result);
}

function Difficulty(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    Label(Locale("habit_difficulty_label"), x, y, width, Scale(26n));
    let options: [
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption,
        NativeSegmentedControl.SegmentOption
    ] = [
        { label: DifficultyLabel(HABIT_DIFFICULTY_EASY) },
        { label: DifficultyLabel(HABIT_DIFFICULTY_MEDIUM) },
        { label: DifficultyLabel(HABIT_DIFFICULTY_HARD) },
        { label: DifficultyLabel(HABIT_DIFFICULTY_VERY_HARD) }
    ];
    let selection = (
        <SegmentedControl
            session={edit_state.session}
            props={{
                id: 7605n,
                bounds: Bounds(x, y + Scale(30n), width, Scale(42n)),
                height: Scale(42n),
                selected_index: HabitDifficultyIndex(edit_state.difficulty),
                has_selection: !edit_state.custom_coins
            }}
            options={options[:]}
        />
    );
    if (selection.changed) {
        edit_state.difficulty = HabitDifficultyAt(selection.selected_index);
        edit_state.custom_coins = false;
    }
    let hint_y = y + Scale(80n);
    let coin = Scale(18n);
    <SvgIcon
        session={edit_state.session}
        props={{
            bounds: Bounds(x, hint_y + (Scale(22n) - coin) / 2n, coin, coin),
            shape: NativeCoinIcon.Shape,
            color: HabitsCoinColor(edit_state.highlight_color, edit_state.text_color)
        }}
    />;
    <Text
        session={edit_state.session}
        props={{
            bounds: Bounds(x + coin + Scale(8n), hint_y, width - coin - Scale(8n), Scale(30n)),
            text: edit_state.custom_coins
                ? Locale("habit_coins_signed_hint")
                : DifficultyEarns(edit_state.difficulty),
            size: edit_state.small_font,
            class_name: edit_state.muted_class,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    y += Scale(112n);
    Label(Locale("habit_custom_coins"), x, y + Scale(10n), width - Scale(110n), Scale(36n));
    let custom = (
        <Toggle
            session={edit_state.session}
            props={{
                id: 7606n,
                bounds: Bounds(x + width - Scale(100n), y, Scale(100n), Scale(36n)),
                value: edit_state.custom_coins,
                off_label: Locale("toggle_off"),
                on_label: Locale("toggle_on")
            }}
        />
    );
    if (custom.changed) {
        edit_state.custom_coins = custom.value;
        if (custom.value) {
            edit_state.coin_halves = HabitDifficultyHalfCoins(edit_state.difficulty);
        }
    }
    if (edit_state.custom_coins) {
        y += Scale(52n);
        Label(
            Locale("habit_coins_per_occurrence"),
            x,
            y + Scale(10n),
            width - Scale(128n),
            Scale(36n)
        );
        CoinField(Bounds(x + width - Scale(120n), y, Scale(120n), Scale(44n)));
    }
}

function CounterField(bounds: Rectangle): boolean {
    const edit_state = Model.CurrentEditor();
    if (!edit_state.counter_focused) {
        CounterText();
    }
    let focused = edit_state.counter_focused;
    let result = (
        <ControlledTextField
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/counter"),
                bounds: bounds,
                value: edit_state.counter_text,
                cursor: edit_state.counter_cursor,
                anchor: edit_state.counter_anchor,
                scroll_x: edit_state.counter_scroll_x,
                focused: focused,
                focus_id: 7622n,
                numeric: true,
                max_bytes: 4n,
                max_codepoints: 4n,
                input: focused ? edit_state.input : {}
            }}
        />
    );
    if (result.edit.changed) {
        edit_state.counter_text = Replaced(
            edit_state.counter_text,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            4n
        );
        let value: s32 = 0n;
        for (let at = s64(0n); at < edit_state.counter_text.count; at += s64(1)) {
            value = value * 10n + s32(edit_state.counter_text[at]) - 48n;
        }
        if (value > HABIT_COUNTER_TARGET_MAX) {
            value = HABIT_COUNTER_TARGET_MAX;
        }
        if (edit_state.counter_text.count > 0n) {
            edit_state.counter_target = value;
        }
    }
    edit_state.counter_cursor = result.cursor;
    edit_state.counter_anchor = result.anchor;
    edit_state.counter_scroll_x = result.scroll_x;
    edit_state.counter_focused = result.focused;
    if (result.focused) {
        FocusOnly(3n);
    }
    Clipboard(result);
    return result.focused;
}

// A toggle at the row's end, as wide as its labels need, with its label
// before it.
function RowToggle(
    id: s32,
    label: string,
    value: boolean,
    x: s32,
    y: s32,
    width: s32
): NativeToggle.ToggleValueResult {
    const edit_state = Model.CurrentEditor();
    let props: NativeToggle.Props = {
        id: id,
        value: value,
        off_label: Locale("toggle_off"),
        on_label: Locale("toggle_on")
    };
    let size = ToggleSize(edit_state.session, props);
    let toggle_width = s32(size.x);
    let toggle_height = s32(size.y);
    if (toggle_height < Scale(30n)) {
        toggle_height = Scale(30n);
    }
    props.bounds = Bounds(
        x + width - toggle_width,
        y + (Scale(44n) - toggle_height) / 2n,
        toggle_width,
        toggle_height
    );
    Label(label, x, y + Scale(10n), width - toggle_width - Scale(8n), Scale(36n));
    return <Toggle session={edit_state.session} props={props} />;
}

// One typed goal value. Goal fields share one cursor: only the focused one
// has it. Returns the typed text.
function GoalField(code: s32, bounds: Rectangle, value: string, max_bytes: s32): string {
    const edit_state = Model.CurrentEditor();
    let focused = edit_state.goal_focused === code + 1n;
    let props: NativeTextField.Props = {
        key: NativeLayout.KeyHash("habit/edit/goal") + u64(code),
        bounds: bounds,
        value: value,
        focused: focused,
        focus_id: 7800n + code,
        numeric: true,
        max_bytes: max_bytes,
        max_codepoints: max_bytes
    };
    if (focused) {
        props.cursor = edit_state.goal_cursor;
        props.anchor = edit_state.goal_anchor;
        props.scroll_x = edit_state.goal_scroll_x;
        props.input = edit_state.input;
    }
    let result = <ControlledTextField session={edit_state.session} props={props} />;
    let typed = value;
    if (result.edit.changed) {
        typed = Replaced(
            value,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            max_bytes
        );
    }
    if (result.focused) {
        edit_state.goal_focused = code + 1n;
        edit_state.goal_cursor = result.cursor;
        edit_state.goal_anchor = result.anchor;
        edit_state.goal_scroll_x = result.scroll_x;
        FocusOnly(6n);
    } else if (focused) {
        edit_state.goal_focused = 0n;
    }
    Clipboard(result);
    return typed;
}

// One bound at x: a number typed in its field, or a time picked in the time
// picker. Returns its width.
function GoalBound(
    slot: s32,
    high: boolean,
    question: *HabitsEditQuestion,
    x: s32,
    y: s32
): s32 {
    const edit_state = Model.CurrentEditor();
    if (question.answer_type === HABIT_ANSWER_NUMBER) {
        let code = slot * 2n + (high ? 1n : 0n);
        let typed = GoalField(
            code,
            Bounds(x, y, Scale(120n), Scale(44n)),
            high ? question.high_text : question.low_text,
            9n
        );
        let number = HabitTimeTypedNumber(typed);
        if (high) {
            question.high_text = typed;
            if (number >= 0n) {
                question.goal_high = number;
            }
        } else {
            question.low_text = typed;
            if (number >= 0n) {
                question.goal_low = number;
            }
        }
        return Scale(120n);
    }
    let picker_width = Scale(132n);
    let code = slot * 2n + (high ? 1n : 0n);
    let picked = (
        <TimePicker
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/goal-time") + u64(code),
                id: 7940n + code,
                bounds: Bounds(x, y, picker_width, Scale(44n)),
                label: Locale(high ? "habit_goal_before" : "habit_goal_after"),
                value: high ? question.goal_high : question.goal_low,
                now: edit_state.now,
                now_label: Locale("statistics_now_label"),
                done_label: Locale("done_button"),
                scale: edit_state.scale
            }}
        />
    );
    if (picked.changed && picked.value >= 0n) {
        if (high) {
            question.goal_high = picked.value;
        } else {
            question.goal_low = picked.value;
        }
    }
    return picker_width;
}

// "Good when" and the goal's options, then its values: from, up to, or
// from and to. Changes the question; returns the y below them.
function Goal(
    slot: s32,
    question: *HabitsEditQuestion,
    x: s32,
    y: s32,
    width: s32
): s32 {
    const edit_state = Model.CurrentEditor();
    let options = NewOptions();
    let kinds = NewKinds();
    let count = GoalOptions(
        question.answer_type,
        options[:],
        kinds[:]
    );
    if (count === 0n) {
        return y;
    }
    let menu_width = GoalMenuWidth(width);
    RowLabel(Locale("habit_goal_label"), x, y, width - menu_width - Scale(8n));
    let selected: s32 = 0n;
    for (let option = s32(0n); option < count; option += s32(1)) {
        if (kinds[option] === question.goal_kind) {
            selected = option;
        }
    }
    let chosen = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7770n + slot,
                bounds: Bounds(x + width - menu_width, y + Scale(4n), menu_width, Scale(44n)),
                selected_index: selected
            }}
            options={options[:count]}
        />
    );
    if (chosen.changed) {
        question.goal_kind = kinds[chosen.selected_index];
        GoalTexts(question);
    }
    y += Scale(52n);
    if (!GoalHasValues(question.goal_kind)) {
        return y;
    }
    let bound_x = x;
    if (question.goal_kind !== HABIT_GOAL_AT_MOST) {
        bound_x += GoalBound(slot, false, question, bound_x, y + Scale(4n));
    }
    if (question.goal_kind === HABIT_GOAL_BETWEEN) {
        <Text
            session={edit_state.session}
            props={{
                bounds: Bounds(bound_x, y + Scale(4n), Scale(40n), Scale(44n)),
                text: Locale("habit_goal_and"),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter
            }}
        />;
        bound_x += Scale(40n);
    }
    if (question.goal_kind !== HABIT_GOAL_AT_LEAST) {
        GoalBound(slot, true, question, bound_x, y + Scale(4n));
    }
    return y + Scale(52n);
}

// One length of a span goal, typed as hours and minutes at the row's end,
// after its label. Returns the length in minutes, or -1 while either part
// is empty.
function SpanLength(bound: s32, label: string, x: s32, y: s32, width: s32): s32 {
    const edit_state = Model.CurrentEditor();
    let unit_width = Width(Locale("habit_unit_hours"), edit_state.font);
    let minutes_unit = Width(Locale("habit_unit_minutes"), edit_state.font);
    if (minutes_unit > unit_width) {
        unit_width = minutes_unit;
    }
    unit_width += Scale(12n);
    let hours_width = Scale(64n);
    let minutes_width = Scale(56n);
    let fields_width = hours_width + unit_width + minutes_width + unit_width;
    RowLabel(label, x, y, width - fields_width - Scale(8n));
    let field_x = x + width - fields_width;
    let units: [string, string] = ["habit_unit_hours", "habit_unit_minutes"];
    let parts = NewParts();
    for (let part = s32(0n); part <= 1n; part += s32(1)) {
        let part_width = part === 0n ? hours_width : minutes_width;
        let typed = "";
        if (bound === 0n) {
            typed = part === 0n ? edit_state.span_low_hours : edit_state.span_low_minutes;
        } else {
            typed = part === 0n ? edit_state.span_high_hours : edit_state.span_high_minutes;
        }
        typed = GoalField(
            EDIT_SPAN_FIELD_CODE + bound * 2n + part,
            Bounds(field_x, y + Scale(4n), part_width, Scale(44n)),
            typed,
            part === 0n ? 3n : 2n
        );
        if (bound === 0n && part === 0n) {
            edit_state.span_low_hours = typed;
        } else if (bound === 0n) {
            edit_state.span_low_minutes = typed;
        } else if (part === 0n) {
            edit_state.span_high_hours = typed;
        } else {
            edit_state.span_high_minutes = typed;
        }
        parts[part] = HabitTimeTypedNumber(typed);
        <Text
            session={edit_state.session}
            props={{
                bounds: Bounds(field_x + part_width, y + Scale(4n), unit_width, Scale(44n)),
                text: Locale(units[part]),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter
            }}
        />;
        field_x += part_width + unit_width;
    }
    if (parts[0n] < 0n || parts[1n] < 0n || parts[1n] > 59n) {
        return -1n;
    }
    return parts[0n] * 60n + parts[1n];
}

// Which spans are good: any, shorter or longer than the average of the
// spans before them, or at least, at most or between lengths typed in hours
// and minutes, such as at most 8 hours for an eating window.
function SpanGoal(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    let options = NewOptions6NativeDropdownOption();
    let kinds: [s32, s32, s32, s32, s32, s32] = [
        HABIT_GOAL_NONE,
        HABIT_GOAL_BELOW_AVERAGE,
        HABIT_GOAL_ABOVE_AVERAGE,
        HABIT_GOAL_AT_LEAST,
        HABIT_GOAL_AT_MOST,
        HABIT_GOAL_BETWEEN
    ];
    options[0n].label = Locale("habit_span_goal_any");
    options[1n].label = Locale("habit_span_goal_shorter");
    options[2n].label = Locale("habit_span_goal_longer");
    options[3n].label = Locale("habit_goal_at_least");
    options[4n].label = Locale("habit_goal_at_most");
    options[5n].label = Locale("habit_goal_between");
    let menu_width = GoalMenuWidth(width);
    RowLabel(Locale("habit_goal_label"), x, y, width - menu_width - Scale(8n));
    let selected: s32 = 0n;
    for (let option = s32(0n); option <= 5n; option += s32(1)) {
        if (kinds[option] === edit_state.span_kind) {
            selected = option;
        }
    }
    let chosen = (
        <Dropdown
            session={edit_state.session}
            props={{
                id: 7615n,
                bounds: Bounds(x + width - menu_width, y + Scale(4n), menu_width, Scale(44n)),
                selected_index: selected
            }}
            options={options[:]}
        />
    );
    if (chosen.changed) {
        edit_state.span_kind = kinds[chosen.selected_index];
        // A length starts at 8 hours, or keeps the one typed.
        if (edit_state.span_low <= 0n && edit_state.span_high <= 0n) {
            edit_state.span_low = 8n * 60n;
            edit_state.span_high = 8n * 60n;
            SpanTexts();
        }
    }
    y += Scale(52n);
    let kind = edit_state.span_kind;
    if (kind === HABIT_GOAL_AT_LEAST || kind === HABIT_GOAL_BETWEEN) {
        let low = SpanLength(
            0n,
            Locale(kind === HABIT_GOAL_BETWEEN ? "habit_goal_between" : "habit_goal_at_least"),
            x,
            y,
            width
        );
        if (low >= 0n) {
            edit_state.span_low = low;
        }
        y += Scale(52n);
    }
    if (kind === HABIT_GOAL_AT_MOST || kind === HABIT_GOAL_BETWEEN) {
        let high = SpanLength(
            1n,
            Locale(kind === HABIT_GOAL_BETWEEN ? "habit_goal_and" : "habit_goal_at_most"),
            x,
            y,
            width
        );
        if (high >= 0n) {
            edit_state.span_high = high;
        }
    }
}

function QuestionField(
    index: s32,
    question: *HabitsEditQuestion,
    bounds: Rectangle
): boolean {
    const edit_state = Model.CurrentEditor();
    let focused = edit_state.question_focused === index + 1n;
    let props: NativeTextField.Props = {
        key: NativeLayout.KeyHash("habit/edit/question") + u64(index),
        bounds: bounds,
        value: question.text,
        placeholder: Locale("habit_question_placeholder"),
        focused: focused,
        focus_id: 7720n + index,
        max_bytes: HABIT_QUESTION_TEXT_SIZE - 1n,
        max_codepoints: HABIT_QUESTION_TEXT_SIZE - 1n
    };
    if (focused) {
        props.cursor = edit_state.question_cursor;
        props.anchor = edit_state.question_anchor;
        props.scroll_x = edit_state.question_scroll_x;
        props.input = edit_state.input;
    }
    let result = <ControlledTextField session={edit_state.session} props={props} />;
    if (result.edit.changed) {
        question.text = Replaced(
            question.text,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            HABIT_QUESTION_TEXT_SIZE - 1n
        );
    }
    if (result.focused) {
        edit_state.question_focused = index + 1n;
        edit_state.question_cursor = result.cursor;
        edit_state.question_anchor = result.anchor;
        edit_state.question_scroll_x = result.scroll_x;
        FocusOnly(5n);
    } else if (focused) {
        edit_state.question_focused = 0n;
    }
    Clipboard(result);
    return result.focused;
}

// "Ask when done": each question's words with a button that removes it,
// "Answer as" its type under them, its goal, and a button that adds a
// question.
function Questions(x: s32, y: s32, width: s32): void {
    const questions = Model.Questions();
    const edit_state = Model.CurrentEditor();
    Label(Locale("habit_questions_label"), x, y + Scale(12n), width, Scale(28n));
    y += Scale(48n);
    let remove_width = Scale(44n);
    let type_width = Scale(160n);
    let types = NewTypes();
    for (let answer_type = s32(0n); answer_type < HABIT_ANSWER_TYPE_COUNT; answer_type += s32(1)) {
        types[answer_type].label = AnswerLabel(answer_type + 1n);
    }
    // Each question's card spans the options' width; its rows sit inside.
    let pad = Scale(EDIT_QUESTION_PADDING);
    let inner_x = x + pad;
    let inner_width = width - pad * 2n;
    for (let index = s32(0n); index < edit_state.question_count; index += s32(1)) {
        let question = questions[index];
        let before = question;
        let card_height = QuestionCardHeight(index);
        <Box
            session={edit_state.session}
            props={{
                bounds: Bounds(x, y, width, card_height),
                fill: edit_state.card_fill,
                border: edit_state.card_border,
                radius: float32(Scale(12n))
            }}
        />;
        let card_bottom = y + card_height;
        y += pad;
        let text_bounds = Bounds(inner_x, y, inner_width - remove_width - Scale(8n), Scale(44n));
        let was_focused = edit_state.question_focused === index + 1n;
        if (QuestionField(index, &question, text_bounds) && !was_focused) {
            EnsureVisible(text_bounds);
        }
        if (
            Step(
                7740n + index,
                "-",
                Bounds(inner_x + inner_width - remove_width, y, remove_width, Scale(44n)),
                false
            )
        ) {
            Ask(HABITS_EDIT_REMOVE_QUESTION, index);
        }
        RowLabel(
            Locale("habit_answer_as"),
            inner_x,
            y + Scale(48n),
            inner_width - type_width - Scale(8n)
        );
        let chosen = (
            <Dropdown
                session={edit_state.session}
                props={{
                    id: 7750n + index,
                    bounds: Bounds(
                        inner_x + inner_width - type_width,
                        y + Scale(52n),
                        type_width,
                        Scale(44n)
                    ),
                    selected_index: question.answer_type - 1n
                }}
                options={types[:]}
            />
        );
        if (chosen.changed) {
            // Another answer type starts with its own goal.
            question.answer_type = chosen.selected_index + 1n;
            let goal = HabitGoalDefault(question.answer_type);
            question.goal_kind = goal.kind;
            question.goal_low = goal.low;
            question.goal_high = goal.high;
            GoalTexts(&question);
        }
        y += Scale(104n);
        if (Model.question_roles[index] === 1n) {
            SpanGoal(inner_x, y, inner_width);
        } else if (Model.question_roles[index] === 0n) {
            Goal(index, &question, inner_x, y, inner_width);
        }
        if (
            question.text !== before.text ||
            question.answer_type !== before.answer_type ||
            question.goal_kind !== before.goal_kind ||
            question.goal_low !== before.goal_low ||
            question.goal_high !== before.goal_high ||
            question.low_text !== before.low_text ||
            question.high_text !== before.high_text
        ) {
            WriteHabitsEditQuestionHost(index, question);
            questions[index] = question;
        }
        y = card_bottom + Scale(EDIT_QUESTION_GAP);
    }
    if (
        (
            <Button
                session={edit_state.session}
                props={{
                    id: 7760n,
                    bounds: Bounds(x, y, width, Scale(44n)),
                    label: Filled("+  %s", 0n, Locale("habit_question_add")),
                    disabled: edit_state.question_count >= HABIT_QUESTION_MAX,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        Ask(HABITS_EDIT_ADD_QUESTION, -1n);
    }
}

function Tracking(x: s32, y: s32, width: s32): void {
    const edit_state = Model.CurrentEditor();
    Difficulty(x, y, width);
    y += Scale(DifficultyHeight());
    let counter = RowToggle(
        7610n,
        Locale("habit_counter_mode"),
        edit_state.counter_enabled,
        x,
        y,
        width
    );
    if (counter.changed) {
        edit_state.counter_enabled = counter.value;
        // A habit counts or measures spans, not both.
        if (counter.value) {
            edit_state.span = false;
        }
    }
    y += Scale(52n);
    if (edit_state.counter_enabled) {
        Label(Locale("habit_counter_target"), x, y + Scale(10n), width - Scale(164n), Scale(36n));
        let control_x = x + width - Scale(160n);
        if (
            Step(
                7620n,
                "-",
                Bounds(control_x, y, Scale(44n), Scale(44n)),
                edit_state.counter_target <= 0n
            )
        ) {
            edit_state.counter_target = edit_state.counter_target - 1n;
            CounterText();
        }
        let counter_bounds = Bounds(control_x + Scale(50n), y, Scale(60n), Scale(44n));
        let was_focused = edit_state.counter_focused;
        if (CounterField(counter_bounds) && !was_focused) {
            EnsureVisible(counter_bounds);
        }
        if (
            Step(
                7621n,
                "+",
                Bounds(control_x + Scale(116n), y, Scale(44n), Scale(44n)),
                edit_state.counter_target >= HABIT_COUNTER_TARGET_MAX
            )
        ) {
            edit_state.counter_target = edit_state.counter_target + 1n;
            CounterText();
        }
        y += Scale(52n);
    }
    let span = RowToggle(7612n, Locale("habit_span_mode"), edit_state.span, x, y, width);
    if (span.changed) {
        edit_state.span = span.value;
        if (span.value) {
            edit_state.counter_enabled = false;
            let goal = HabitSpanGoalDefault();
            edit_state.span_kind = goal.kind;
            edit_state.span_low = goal.low;
            edit_state.span_high = goal.high;
            SpanTexts();
        }
        ReadQuestions();
    }
    y += Scale(52n);
    // Without a start question the span's goal sits under its selection.
    if (edit_state.span && !HasSpanStart()) {
        SpanGoal(x, y, width);
        y += SpanGoalHeight();
    }
    let linked: s32 = 0n;
    for (let index = s32(0n); index < edit_state.practice_count; index += s32(1)) {
        if (PracticeLinked(ReadHabitsEditPracticeHost(index).mask)) {
            linked += 1n;
        }
    }
    if (
        (
            <Button
                session={edit_state.session}
                props={{
                    id: 7630n,
                    bounds: Bounds(x, y, width, Scale(44n)),
                    label: Filled("%s · %d", linked, Locale("habit_link_practices")),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        Ask(HABITS_EDIT_PRACTICES, -1n);
    }
    Questions(x, y + Scale(44n), width);
}

function Form(): void {
    const edit_state = Model.CurrentEditor();
    let top = Scale(56n);
    let footer = Scale(edit_state.name_error !== 0n ? 92n : 64n);
    let options = NewOptions1NativeDropdownOption();
    let title = (
        <TitleBar
            session={edit_state.session}
            props={{
                title: Locale(edit_state.is_new ? "habit_new_title" : "habit_edit_title"),
                height: top,
                strong_title: true,
                bounds: Bounds(0n, 0n, edit_state.view_width, top),
                has_leading_action: true,
                leading_label: Locale("back_button")
            }}
            options={options[0n:0n]}
        />
    );
    if (title.clicked_leading) {
        Ask(HABITS_EDIT_BACK, -1n);
        return;
    }
    let viewport_height = edit_state.view_height - top - footer;
    if (viewport_height < 1n) {
        viewport_height = 1n;
    }
    let side = Scale(16n);
    let x = side;
    let width = edit_state.view_width - side * 2n;
    if (width > Scale(EDIT_CONTENT_MAX_WIDTH)) {
        x += (width - Scale(EDIT_CONTENT_MAX_WIDTH)) / 2n;
        width = Scale(EDIT_CONTENT_MAX_WIDTH);
    }
    let content_height = ContentHeight(width);
    Model.form_top = top;
    Model.form_height = viewport_height;
    Model.form_content = content_height;
    const scrolled = (
        <Scroll
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/scroll"),
                bounds: Bounds(0n, top, edit_state.view_width, viewport_height),
                content_height: content_height,
                scroll_offset: edit_state.scroll
            }}
            children={(scrolled: NativeScroll.ScrollResult): void => {
                const edit_state = Model.CurrentEditor();
                edit_state.scroll = scrolled.scroll_offset;
                let y = s32(scrolled.content.y) + Scale(8n);
                let titles: [string, string, string] = [
                    Locale("habit_details_title"),
                    Locale("habit_routine_title"),
                    Locale("habit_tracking_title")
                ];
                for (let section = s32(0n); section <= 2n; section += s32(1)) {
                    let body_width = width - Scale(24n);
                    let body_height = SectionBody(section, body_width);
                    <Text
                        session={edit_state.session}
                        props={{
                            bounds: Bounds(x + Scale(4n), y, width - Scale(4n), Scale(26n)),
                            text: titles[section],
                            size: edit_state.font,
                            wrap: NativeText.Wrap.TextWrapNone,
                            semantic_kind: SemanticKind.SemanticHeading,
                            heading_level: 2n
                        }}
                    />;
                    <Fieldset
                        session={edit_state.session}
                        props={{
                            bounds: Bounds(x, y + Scale(30n), width, body_height + Scale(24n))
                        }}
                    />;
                    let body_x = x + Scale(12n);
                    let body_y = y + Scale(42n);
                    if (section === 0n) {
                        Details(body_x, body_y, body_width);
                    } else if (section === 1n) {
                        Routine(body_x, body_y, body_width);
                    } else {
                        Tracking(body_x, body_y, body_width);
                    }
                    y += SectionHeight(section, body_width) + Scale(12n);
                }
            }}
        />
    );
    if (!scrolled.opened) {
        edit_state.scroll = scrolled.scroll_offset;
    }
    // The footer keeps Save and Delete apart from the scrolling form.
    <Box
        session={edit_state.session}
        props={{
            bounds: Bounds(0n, edit_state.view_height - footer, edit_state.view_width, footer),
            fill: edit_state.canvas_color
        }}
    />;
    let rule = edit_state.text_color;
    rule.a = u8(255.0 * 0.12);
    <Box
        session={edit_state.session}
        props={{
            bounds: Bounds(0n, edit_state.view_height - footer, edit_state.view_width, Scale(1n)),
            fill: rule
        }}
    />;
    if (edit_state.name_error !== 0n) {
        Label(
            Locale(edit_state.name_error === 1n ? "habit_name_required" : "habit_name_duplicate"),
            x,
            edit_state.view_height - footer + Scale(8n),
            width,
            Scale(28n)
        );
    }
    let action_x = x;
    let action_width = width;
    if (!edit_state.is_new) {
        let delete_width = Scale(104n);
        if (
            (
                <Button
                    session={edit_state.session}
                    props={{
                        id: 7650n,
                        bounds: Bounds(
                            x,
                            edit_state.view_height - Scale(54n),
                            delete_width,
                            Scale(44n)
                        ),
                        label: Locale("habit_delete_button"),
                        tone: ButtonTone.ButtonToneDanger,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            Ask(HABITS_EDIT_DELETE, -1n);
        }
        action_x += delete_width + Scale(8n);
        action_width -= delete_width + Scale(8n);
    }
    if (
        (
            <Button
                session={edit_state.session}
                props={{
                    id: 7651n,
                    bounds: Bounds(
                        action_x,
                        edit_state.view_height - Scale(54n),
                        action_width,
                        Scale(44n)
                    ),
                    label: Locale(edit_state.is_new ? "habit_create_button" : "save_button"),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }}
            />
        )
    ) {
        Ask(HABITS_EDIT_SAVE, -1n);
    }
}

// What checks the habit, each with its checkbox: the practices whose
// sessions count, then apps such as Diary, as the host lists them.
function PracticePicker(): void {
    const edit_state = Model.CurrentEditor();
    let width = edit_state.view_width - Scale(32n);
    if (width > Scale(400n)) {
        width = Scale(400n);
    }
    let frame = NativeModal.Draw(edit_state.session, {
        key: NativeLayout.KeyHash("habit/edit/practices"),
        title: Locale("habit_link_practices"),
        width: width,
        height: Scale(160n + edit_state.practice_count * 42n),
        scale: edit_state.scale
    });
    if (frame.dismissed) {
        Ask(HABITS_EDIT_PRACTICES_DONE, -1n);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content = frame.layout.content;
    let x = s32(content.x);
    let y = s32(content.y);
    width = s32(content.width);
    let hint = Locale("habit_link_practices_hint");
    let hint_height = TextHeight(edit_state.session, {
        text: hint,
        size: edit_state.font,
        bounds: Bounds(0n, 0n, width, 0n),
        wrap: NativeText.Wrap.TextWrapAuto
    });
    Label(hint, x, y, width, hint_height);
    y += hint_height + Scale(8n);
    let choices_height = s32(content.y + content.height) - y - Scale(52n);
    if (choices_height < Scale(40n)) {
        choices_height = Scale(40n);
    }
    const choices = (
        <Scroll
            session={edit_state.session}
            props={{
                key: NativeLayout.KeyHash("habit/edit/practice-list"),
                bounds: Bounds(x, y, width, choices_height),
                scale: edit_state.scale,
                content_height: edit_state.practice_count * Scale(42n),
                scroll_offset: Model.practice_scroll
            }}
            children={(choices: NativeScroll.ScrollResult): void => {
                const edit_state = Model.CurrentEditor();
                Model.practice_scroll = choices.scroll_offset;
                let y = s32(choices.content.y);
                for (let index = s32(0n); index < edit_state.practice_count; index += s32(1)) {
                    let practice = ReadHabitsEditPracticeHost(index);
                    let checkbox = (
                        <Checkbox
                            session={edit_state.session}
                            props={{
                                id: 9120n + index,
                                bounds: Bounds(x, y, s32(choices.content.width), Scale(38n)),
                                label: practice.label,
                                checked: PracticeLinked(practice.mask),
                                disabled:
                                    PracticeLinked(HABIT_LINK_DIARY) &&
                                    practice.mask !== HABIT_LINK_DIARY
                            }}
                        />
                    );
                    if (checkbox.changed) {
                        edit_state.sync_activity = HabitLinkSelect(
                            edit_state.sync_activity,
                            practice.mask,
                            checkbox.checked
                        );
                    }
                    y += Scale(42n);
                }
            }}
        />
    );
    if (!choices.opened) {
        Model.practice_scroll = choices.scroll_offset;
    }
    if (
        (
            <Button
                session={edit_state.session}
                props={{
                    id: 9160n,
                    bounds: {
                        x: float32(x),
                        y: content.y + content.height - float32(Scale(44n)),
                        width: float32(width),
                        height: float32(Scale(40n))
                    },
                    label: Locale("done_button"),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }}
            />
        )
    ) {
        Ask(HABITS_EDIT_PRACTICES_DONE, -1n);
    }
    End(edit_state.session);
}

export function HabitsEditView(message: HabitsMessage): HabitsMessage {
    const edit_state = Model.CurrentEditor();
    Model.SetEditor(ReadHabitsEditHost());
    edit_state.action = HABITS_EDIT_NONE;
    edit_state.action_index = -1n;
    edit_state.clipboard_write = false;
    edit_state.clipboard_text = "";
    ReadQuestions();
    if (edit_state.picking_practices) {
        PracticePicker();
    } else {
        Model.practice_scroll = 0n;
        Form();
    }
    WriteHabitsEditHost(*edit_state);
    message.succeeded = true;
    return message;
}
