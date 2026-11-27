import { DateValid } from "date_parse";
import * as Model from "habit_list_view";
import {
    WeeklyCountLabel,
    Ask,
    Bounds,
    DateText,
    Day,
    DayAgo,
    Filled,
    Locale,
    Number,
    OffDay,
    Scale,
    Weekday
} from "habit_list_view";
import {
    HABIT_WEEKLY_INITIAL_DAYS,
    HABIT_WEEKLY_LOAD_DAYS,
    HABIT_WEEKLY_MAX_DAYS
} from "habit_types";
import { HABITS_LIST_DAY } from "habits_types";
import * as NativeButton from "kryon/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Button } from "kryon/tsx/button";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { PressButton } from "habit_list_visuals";
import { DayDot } from "habit_list_marks";

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

export function Weekly(index: s32, x: s32, width: s32, top: s32, bottom: s32): void {
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

export function Calendar(index: s32, x: s32, width: s32, top: s32): void {
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
