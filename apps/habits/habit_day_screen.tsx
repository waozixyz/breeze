// A habit's day and the dialog that writes its entries. The day's screen
// lists the day's entries, each with buttons that change or delete it and,
// while a span runs, one that ends it, then the practice sessions linked to
// the day on a card for each practice: each session's time and what it did,
// and a breathing session's rounds, each changed with the number pad or
// deleted. A counting habit's count steps below them. The entry dialog asks
// for an entry's time, or a span's start and end, and its questions. The
// host keeps the habits, their entries and sessions and does what the page
// asks once it is drawn.
import * as Model from "habit_day_view";
import {
    Alpha,
    AnswerAreaHeight,
    AnswersHeight,
    Bounds,
    CancelRound,
    DAY_ANSWER_INPUT_Y,
    DAY_ANSWER_ROW_HEIGHT,
    DAY_CARD_PADDING,
    DAY_CARD_RADIUS,
    DAY_ENTRY_BUTTON,
    DAY_ROUND_MAX,
    DateText,
    DayAsk,
    DeleteBeforeCursor,
    DeleteImage,
    EditImage,
    EntryAsk,
    Filled,
    InsertDigit,
    KeyboardHeight,
    Locale,
    NewOptions,
    Number,
    ParagraphHeight,
    ReadHabitsAnswerHost,
    ReadHabitsDayEntryHost,
    ReadHabitsDayHost,
    ReadHabitsDayRoundHost,
    ReadHabitsDaySessionHost,
    ReadHabitsEntryHost,
    Replaced,
    RoundKeys,
    SaveRound,
    Scale,
    Strong,
    TitleFont,
    UiImage,
    Width,
    WriteHabitsAnswerHost,
    WriteHabitsDayHost,
    WriteHabitsEntryHost
} from "habit_day_view";
import {
    HABIT_ANSWER_NUMBER,
    HABIT_ANSWER_SIZE,
    HABIT_ANSWER_TIME,
    HABIT_ANSWER_YES_NO
} from "habit_types";
import {
    HABITS_DAY_SCREEN_ADD_ENTRY,
    HABITS_DAY_SCREEN_CLOSE,
    HABITS_DAY_SCREEN_DELETE_ENTRY,
    HABITS_DAY_SCREEN_DELETE_ROUND,
    HABITS_DAY_SCREEN_DELETE_SESSION,
    HABITS_DAY_SCREEN_EDIT_ENTRY,
    HABITS_DAY_SCREEN_END_SPAN,
    HABITS_DAY_SCREEN_NONE,
    HABITS_DAY_SCREEN_STEP_COUNT,
    HABITS_ENTRY_CANCEL,
    HABITS_ENTRY_DELETE,
    HABITS_ENTRY_NONE,
    HABITS_ENTRY_SAVE,
    HABITS_ENTRY_SKIP,
    HabitsMessage
} from "habits_types";
import { HabitsAnswer, HabitsDayEntry } from "habits_ui_types";
import * as NativeButton from "kryon/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { DarkenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import * as NativeImage from "kryon/image";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import { SemanticKind } from "kryon/semantic";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import * as NativeTextField from "kryon/text_field";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Shape } from "kryon/tsx/shape";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { ControlledTextField } from "kryon/tsx/text_field";
import { TimePicker } from "kryon/tsx/time_picker";
import { TitleBar } from "kryon/tsx/title_bar";

function EntryActionProps(
    key: u64,
    id: s32,
    bounds: Rectangle,
    image: NativeImage.Props,
    disabled: boolean
): NativeButton.Props {
    return {
        key: key,
        id: id,
        bounds: bounds,
        label: image.alt_text,
        image: image,
        icon_only: true,
        tone: ButtonTone.ButtonToneNeutral,
        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
        disabled: disabled
    };
}

function Card(bounds: Rectangle): void {
    const day_state = Model.CurrentDay();
    <Box
        session={Model.CurrentSession()}
        props={{
            bounds: bounds,
            fill: day_state.card_fill,
            border: day_state.card_border,
            radius: float32(Scale(DAY_CARD_RADIUS))
        }}
    />;
}

// An entry's answers: each question muted, its value under it in bold.
// Returns their height; draws them when draw is set.
function EntryAnswers(summary: string, x: s32, y: s32, width: s32, draw: boolean): s32 {
    let height: s32 = 0n;
    let start: s64 = 0n;
    let line: s32 = 0n;
    while (start < summary.count) {
        let end = start;
        while (end < summary.count && summary[end] !== u8(10n)) {
            end += 1n;
        }
        let text = summary[start:end];
        let value = line % 2n === 1n;
        let font = value ? Model.look_font + Scale(2n) : Model.look_small_font;
        let text_height = ParagraphHeight(text, width, font);
        if (draw) {
            let strong = Strong(text);
            let props: NativeText.Props = {
                bounds: Bounds(x, y + height, width, text_height),
                text: text,
                size: font,
                wrap: NativeText.Wrap.TextWrapAuto
            };
            if (value) {
                props.strong = strong[:];
            } else {
                props.class_name = Model.look_muted;
            }
            <Text session={Model.CurrentSession()} props={props} />;
        }
        height += text_height;
        height += value ? Scale(10n) : Scale(2n);
        start = end + 1n;
        line += 1n;
    }
    if (height > Scale(10n)) {
        height -= Scale(10n);
    }
    return height;
}

// An entry's card: a span's times with the buttons that change or delete
// it and its answers below, and End now while it runs. Other entries ask
// no time, so their answers sit beside the buttons, and a skipped one shows
// when it was recorded.
function EntryCardHeight(item: HabitsDayEntry, width: s32): s32 {
    const day_state = Model.CurrentDay();
    let pad = Scale(DAY_CARD_PADDING);
    let buttons = Scale(DAY_ENTRY_BUTTON);
    if (!day_state.span && item.summary.count > 0n) {
        let answers = EntryAnswers(
            item.summary,
            0n,
            0n,
            width - pad * 2n - buttons * 2n - Scale(18n),
            false
        );
        if (answers < buttons) {
            answers = buttons;
        }
        return pad + answers + pad;
    }
    let height = pad + buttons + pad;
    if (item.summary.count > 0n) {
        height += EntryAnswers(item.summary, 0n, 0n, width - pad * 2n, false) + Scale(8n);
    }
    if (item.running) {
        height += Scale(44n) + Scale(12n);
    }
    return height;
}

// The day's entries: a card for each entry, then a button that adds one.
// Returns the y below them.
function DayEntries(x: s32, width: s32, y: s32, draw: boolean): s32 {
    const day_state = Model.CurrentDay();
    let icon_width = Scale(DAY_ENTRY_BUTTON);
    let pad = Scale(DAY_CARD_PADDING);
    let heading_height = Scale(34n);
    if (draw) {
        let heading = Locale("habit_day_entries");
        let strong = Strong(heading);
        <Text
            session={Model.CurrentSession()}
            props={{
                bounds: Bounds(x, y, width, heading_height),
                text: heading,
                size: TitleFont(heading, width),
                strong: strong[:],
                semantic_kind: SemanticKind.SemanticHeading,
                heading_level: 2n,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    y += heading_height + Scale(8n);
    for (let index = s32(0n); index < day_state.entry_count; index += s32(1)) {
        let item = ReadHabitsDayEntryHost(index);
        let card_height = EntryCardHeight(item, width);
        if (draw) {
            Card(Bounds(x, y, width, card_height));
            let inner_x = x + pad;
            let inner_width = width - pad * 2n;
            let buttons_width = icon_width * 2n + Scale(10n);
            if (day_state.span || item.summary.count === 0n) {
                let strong = Strong(item.when);
                let when: NativeText.Props = {
                    bounds: Bounds(
                        inner_x,
                        y + pad,
                        inner_width - buttons_width - Scale(8n),
                        icon_width
                    ),
                    text: item.when,
                    size: Model.look_font,
                    vertical_align: TextAlign.TextAlignCenter,
                    wrap: NativeText.Wrap.TextWrapEllipsis
                };
                if (day_state.span) {
                    when.size = Model.look_font + Scale(4n);
                    when.strong = strong[:];
                } else {
                    when.class_name = Model.look_muted;
                }
                <Text session={Model.CurrentSession()} props={when} />;
            } else {
                EntryAnswers(
                    item.summary,
                    inner_x,
                    y + pad,
                    inner_width - buttons_width - Scale(8n),
                    true
                );
            }
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={EntryActionProps(
                            u64(5740000n + index * 2n),
                            5740000n + index * 2n,
                            Bounds(
                                inner_x + inner_width - buttons_width,
                                y + pad,
                                icon_width,
                                icon_width
                            ),
                            EditImage(),
                            day_state.modal_active
                        )}
                    />
                )
            ) {
                DayAsk(HABITS_DAY_SCREEN_EDIT_ENTRY, index, 0n);
            }
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={EntryActionProps(
                            u64(5740001n + index * 2n),
                            5740001n + index * 2n,
                            Bounds(
                                inner_x + inner_width - icon_width,
                                y + pad,
                                icon_width,
                                icon_width
                            ),
                            DeleteImage(),
                            day_state.modal_active
                        )}
                    />
                )
            ) {
                DayAsk(HABITS_DAY_SCREEN_DELETE_ENTRY, index, 0n);
            }
            let line_y = y + pad + icon_width + Scale(8n);
            if (day_state.span && item.summary.count > 0n) {
                line_y +=
                    EntryAnswers(item.summary, inner_x, line_y, inner_width, true) + Scale(8n);
            }
            if (item.running) {
                if (
                    (
                        <Button
                            session={Model.CurrentSession()}
                            props={{
                                id: 5739990n,
                                bounds: Bounds(
                                    inner_x,
                                    line_y + Scale(4n),
                                    inner_width,
                                    Scale(44n)
                                ),
                                label: Locale("habit_span_end_now"),
                                tone: ButtonTone.ButtonToneAccent,
                                emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                                disabled: day_state.modal_active
                            }}
                        />
                    )
                ) {
                    DayAsk(HABITS_DAY_SCREEN_END_SPAN, index, 0n);
                }
            }
        }
        y += card_height + Scale(12n);
    }
    if (draw) {
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        id: 5739991n,
                        bounds: Bounds(x, y, width, Scale(48n)),
                        label: Locale("habit_entry_add"),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                        disabled: day_state.modal_active
                    }}
                />
            )
        ) {
            DayAsk(HABITS_DAY_SCREEN_ADD_ENTRY, -1n, 0n);
        }
    }
    return y + Scale(48n);
}

// A line between the rows of a practice's card.
function Divider(x: s32, y: s32, width: s32): void {
    const day_state = Model.CurrentDay();
    <Box
        session={Model.CurrentSession()}
        props={{ bounds: Bounds(x, y, width, Scale(1n)), fill: Alpha(day_state.text_color, 0.1) }}
    />;
}

// Each breathing session shows its actual round values on a labelled plot.
function SessionRoundGraph(session_index: s32, rounds: s32, x: s32, y: s32, width: s32): void {
    const day_state = Model.CurrentDay();
    let left = x + Scale(62n);
    let right = x + width - Scale(12n);
    let top = y + Scale(12n);
    let bottom = y + Scale(120n);
    let highest: s32 = 0n;
    for (let round = s32(0n); round < rounds; round += s32(1)) {
        let value = ReadHabitsDayRoundHost(session_index, round);
        if (value > highest) {
            highest = value;
        }
    }
    if (highest < 1n) {
        highest = 1n;
    }
    <Text
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(x, top - Scale(8n), Scale(56n), Scale(20n)),
            text: Filled(Locale("results_metric_seconds"), highest),
            size: Model.look_small_font,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Text
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(x, bottom - Scale(8n), Scale(56n), Scale(20n)),
            text: Filled(Locale("results_metric_seconds"), 0n),
            size: Model.look_small_font,
            align: TextAlign.TextAlignEnd
        }}
    />;
    <Shape
        session={Model.CurrentSession()}
        props={{
            start: { x: float32(left), y: float32(bottom) },
            end: { x: float32(right), y: float32(bottom) },
            color: Alpha(day_state.text_color, 0.2)
        }}
    />;
    let previous_x = left;
    let previous_y = bottom;
    for (let round = s32(0n); round < rounds; round += s32(1)) {
        let value = ReadHabitsDayRoundHost(session_index, round);
        let point_x = left + (right - left) / 2n;
        if (rounds > 1n) {
            point_x = left + ((right - left) * round) / (rounds - 1n);
        }
        let point_y = bottom - s32((s64(bottom - top) * value) / highest);
        if (round > 0n) {
            <Shape
                session={Model.CurrentSession()}
                props={{
                    start: { x: float32(previous_x), y: float32(previous_y) },
                    end: { x: float32(point_x), y: float32(point_y) },
                    color: day_state.text_color
                }}
            />;
        }
        <Box
            session={Model.CurrentSession()}
            props={{
                bounds: Bounds(point_x - Scale(3n), point_y - Scale(3n), Scale(6n), Scale(6n)),
                fill: day_state.text_color,
                radius: float32(Scale(3n))
            }}
        />;
        if (round === 0n || round === rounds - 1n) {
            let label_x = round === 0n ? left : left + (right - left) / 2n;
            let label_width = rounds === 1n ? right - left : (right - left) / 2n;
            <Text
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(label_x, bottom + Scale(6n), label_width, Scale(20n)),
                    text: Filled(Locale("round_number_label"), round + 1n),
                    size: Model.look_small_font,
                    align:
                        rounds === 1n
                            ? TextAlign.TextAlignCenter
                            : round === 0n
                              ? TextAlign.TextAlignStart
                              : TextAlign.TextAlignEnd
                }}
            />;
        }
        previous_x = point_x;
        previous_y = point_y;
    }
}

// One practice's sessions of the day on its card: the practice's name, each
// session's time and summary with a button that deletes it, and a breathing
// session's rounds below it, each with buttons that change or delete it.
// Returns the y below the card.
function PracticeCard(
    first_session: s32,
    last_session: s32,
    content_x: s32,
    content_width: s32,
    y: s32,
    draw: boolean
): s32 {
    const day_state = Model.CurrentDay();
    let pad = Scale(DAY_CARD_PADDING);
    let x = content_x + pad;
    let width = content_width - pad * 2n;
    let row_height = Scale(48n);
    let summary_height = Scale(44n);
    let icon_width = Scale(DAY_ENTRY_BUTTON);
    let font = Model.look_font;
    let title = ReadHabitsDaySessionHost(first_session).title;
    y += pad;
    if (draw) {
        let strong = Strong(title);
        <Text
            session={Model.CurrentSession()}
            props={{
                bounds: Bounds(x, y, width - icon_width - Scale(8n), Scale(34n)),
                text: title,
                size: TitleFont(title, width - icon_width - Scale(8n)),
                strong: strong[:],
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
    }
    y += Scale(34n);
    for (let index = first_session; index <= last_session; index += s32(1)) {
        let session = ReadHabitsDaySessionHost(index);
        let trash_x = x + width - icon_width;
        let summary_x = x + Scale(100n);
        if (index > first_session) {
            if (draw) {
                Divider(x, y + Scale(6n), width);
            }
            y += Scale(12n);
        }
        if (summary_x + Width(session.summary, font) > trash_x - Scale(8n)) {
            summary_x = x + Scale(68n);
        }
        if (draw) {
            <Text
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(x, y, summary_x - x - Scale(8n), summary_height),
                    text: session.time,
                    size: font,
                    wrap: NativeText.Wrap.TextWrapNone,
                    vertical_align: TextAlign.TextAlignCenter
                }}
            />;
            <Text
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(summary_x, y, trash_x - summary_x - Scale(8n), summary_height),
                    text: session.summary,
                    size: font,
                    wrap: NativeText.Wrap.TextWrapNone,
                    vertical_align: TextAlign.TextAlignCenter
                }}
            />;
            if (
                !day_state.editing && (
                    <Button
                        session={Model.CurrentSession()}
                        props={EntryActionProps(
                            u64(5750000n + index),
                            0n,
                            Bounds(
                                trash_x,
                                y + (summary_height - icon_width) / 2n,
                                icon_width,
                                icon_width
                            ),
                            DeleteImage(),
                            day_state.modal_active
                        )}
                    />
                )
            ) {
                DayAsk(HABITS_DAY_SCREEN_DELETE_SESSION, index, 0n);
            }
        }
        y += summary_height;
        if (session.details.count > 0n) {
            if (draw) {
                <Text
                    session={Model.CurrentSession()}
                    props={{
                        bounds: Bounds(x, y, width, Scale(32n)),
                        text: session.details,
                        size: Model.look_small_font,
                        wrap: NativeText.Wrap.TextWrapEllipsis
                    }}
                />;
            }
            y += Scale(32n);
        }
        let rounds = session.rounds;
        if (rounds > DAY_ROUND_MAX) {
            rounds = DAY_ROUND_MAX;
        }
        if (rounds > 0n) {
            if (draw) {
                SessionRoundGraph(index, rounds, x, y, width);
            }
            y += Scale(156n);
        }
        for (let round = s32(0n); round < rounds; round += s32(1)) {
            let round_trash_x = x + width - icon_width;
            let round_edit_x = round_trash_x - icon_width - Scale(10n);
            let value_x = x + width / 3n;
            let value_width = round_edit_x - value_x - Scale(8n);
            let editing_round =
                day_state.editing &&
                day_state.edit_session === index &&
                day_state.edit_round === round;
            let value_text_x = editing_round ? value_x - Scale(8n) : value_x;
            let value_text_width = editing_round ? Scale(78n) : value_width;
            if (draw) {
                let value = day_state.edit_text;
                if (!editing_round) {
                    value = Filled(
                        Locale("results_metric_seconds"),
                        ReadHabitsDayRoundHost(index, round)
                    );
                }
                Divider(x, y, width);
                if (editing_round) {
                    <Box
                        session={Model.CurrentSession()}
                        props={{
                            bounds: Bounds(x, y + Scale(2n), width, row_height - Scale(4n)),
                            fill: Alpha(day_state.surface_color, 0.75),
                            border: Alpha(day_state.text_color, 0.55),
                            radius: float32(Scale(8n))
                        }}
                    />;
                    <Box
                        session={Model.CurrentSession()}
                        props={{
                            bounds: Bounds(
                                value_x - Scale(8n),
                                y + Scale(6n),
                                Scale(78n),
                                row_height - Scale(12n)
                            ),
                            border: day_state.text_color,
                            radius: float32(Scale(6n))
                        }}
                    />;
                }
                <Text
                    session={Model.CurrentSession()}
                    props={{
                        bounds: Bounds(x, y, value_x - x - Scale(8n), row_height),
                        text: Filled(Locale("round_number_label"), round + 1n),
                        size: font,
                        wrap: NativeText.Wrap.TextWrapNone,
                        vertical_align: TextAlign.TextAlignCenter
                    }}
                />;
                <Text
                    session={Model.CurrentSession()}
                    props={{
                        bounds: Bounds(value_text_x, y, value_text_width, row_height),
                        text: value,
                        size: Scale(19n),
                        wrap: NativeText.Wrap.TextWrapNone,
                        align: editing_round ? TextAlign.TextAlignCenter : TextAlign.TextAlignStart,
                        vertical_align: TextAlign.TextAlignCenter
                    }}
                />;
                let key = u64(5760000n + index * 64n + round * 2n);
                if (
                    !day_state.editing && (
                        <Button
                            session={Model.CurrentSession()}
                            props={EntryActionProps(
                                key,
                                0n,
                                Bounds(
                                    round_edit_x,
                                    y + (row_height - icon_width) / 2n,
                                    icon_width,
                                    icon_width
                                ),
                                EditImage(),
                                day_state.modal_active
                            )}
                        />
                    )
                ) {
                    day_state.editing = true;
                    day_state.edit_session = index;
                    day_state.edit_round = round;
                    day_state.edit_text = Number(s64(ReadHabitsDayRoundHost(index, round)));
                    day_state.edit_cursor = s32(day_state.edit_text.count);
                }
                if (
                    !day_state.editing && (
                        <Button
                            session={Model.CurrentSession()}
                            props={EntryActionProps(
                                key + u64(1n),
                                0n,
                                Bounds(
                                    round_trash_x,
                                    y + (row_height - icon_width) / 2n,
                                    icon_width,
                                    icon_width
                                ),
                                DeleteImage(),
                                day_state.modal_active
                            )}
                        />
                    )
                ) {
                    DayAsk(HABITS_DAY_SCREEN_DELETE_ROUND, index, round);
                }
            }
            y += row_height;
        }
    }
    return y + pad;
}

// The day's entries, its sessions by practice and a counting habit's count.
// Returns the y below them.
function DayContent(content_x: s32, content_width: s32, y: s32, draw: boolean): s32 {
    const day_state = Model.CurrentDay();
    let section_gap = Scale(16n);
    if (day_state.keeps_entries) {
        y = DayEntries(content_x, content_width, y, draw);
        if (day_state.session_count <= 0n) {
            return y;
        }
        y += section_gap;
    }
    if (day_state.session_count <= 0n) {
        if (draw) {
            <Text
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(content_x, y, content_width, Scale(40n)),
                    text: Locale("no_sessions"),
                    wrap: NativeText.Wrap.TextWrapNone
                }}
            />;
        }
        return y + Scale(40n);
    }
    // The host lists the sessions by practice; each practice has a card.
    let first: s32 = 0n;
    while (first < day_state.session_count) {
        let activity = ReadHabitsDaySessionHost(first).activity;
        let last = first;
        while (
            last + 1n < day_state.session_count &&
            ReadHabitsDaySessionHost(last + 1n).activity === activity
        ) {
            last += 1n;
        }
        let card_height = PracticeCard(first, last, content_x, content_width, y, false) - y;
        if (draw) {
            Card(Bounds(content_x, y, content_width, card_height));
            PracticeCard(first, last, content_x, content_width, y, true);
        }
        y += card_height + section_gap;
        first = last + 1n;
    }
    if (day_state.counting) {
        let button_height = Scale(34n);
        let step_width = Scale(42n);
        let gap = Scale(8n);
        let minus_x = content_x;
        let plus_x = content_x + content_width - step_width;
        let label_x = minus_x + step_width + gap;
        let label_width = plus_x - label_x - gap;
        y += Scale(6n);
        if (draw) {
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={{
                            id: 5739992n,
                            bounds: Bounds(minus_x, y, step_width, button_height),
                            label: "-",
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                            disabled:
                                day_state.modal_active || day_state.count <= day_state.minimum_count
                        }}
                    />
                )
            ) {
                DayAsk(HABITS_DAY_SCREEN_STEP_COUNT, -1n, 0n);
                day_state.action_step = -1n;
            }
            <Box
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(label_x, y, label_width, button_height),
                    fill: DarkenColor(day_state.canvas_color, 5n),
                    radius: float32(Scale(8n))
                }}
            />;
            <Text
                session={Model.CurrentSession()}
                props={{
                    bounds: Bounds(label_x + Scale(8n), y, label_width - Scale(8n), button_height),
                    text: Filled(Locale("habit_session_total_count"), day_state.count),
                    vertical_align: TextAlign.TextAlignCenter,
                    wrap: NativeText.Wrap.TextWrapNone
                }}
            />;
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={{
                            id: 5739993n,
                            bounds: Bounds(plus_x, y, step_width, button_height),
                            label: "+",
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                            disabled: day_state.modal_active
                        }}
                    />
                )
            ) {
                DayAsk(HABITS_DAY_SCREEN_STEP_COUNT, -1n, 0n);
                day_state.action_step = 1n;
            }
        }
        y += button_height + Scale(8n);
    }
    return y;
}

// The number pad under the page while a round is changed: the round and its
// seconds, the digits and Delete, then Cancel and Save.
function NumberPad(): void {
    const day_state = Model.CurrentDay();
    let height = KeyboardHeight();
    if (height <= 0n) {
        return;
    }
    let key_height = Scale(48n);
    let gap = Scale(6n);
    let pad = Scale(10n);
    let header_height = Scale(54n);
    let action_height = Scale(44n);
    let x = Scale(16n);
    let y = day_state.view_height - height;
    let width = day_state.view_width - x * 2n;
    let key_width = (width - gap * 2n) / 3n;
    <Box
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(0n, y, day_state.view_width, height),
            fill: DarkenColor(day_state.canvas_color, 10n)
        }}
    />;
    <Box
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(0n, y, day_state.view_width, Scale(1n)),
            fill: DarkenColor(day_state.canvas_color, 42n)
        }}
    />;
    <Text
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(x, y + pad, width, Scale(22n)),
            text: Filled(Locale("round_number_label"), day_state.edit_round + 1n),
            size: Model.look_font,
            wrap: NativeText.Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter
        }}
    />;
    <Text
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(x, y + pad + Scale(24n), width, Scale(28n)),
            text: day_state.edit_text,
            size: Scale(24n),
            wrap: NativeText.Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter
        }}
    />;
    let labels: [
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
    ] = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "DEL", "0"];
    for (let key = s32(0n); key <= 10n; key += s32(1)) {
        let column = key % 3n;
        let row = key / 3n;
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        key: u64(5770000n + key),
                        bounds: Bounds(
                            x + column * (key_width + gap),
                            y + pad + header_height + row * (key_height + gap),
                            key_width,
                            key_height
                        ),
                        label: labels[key],
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            if (key === 9n) {
                DeleteBeforeCursor();
            } else {
                InsertDigit(labels[key]);
            }
        }
    }
    let action_y = y + pad + header_height + key_height * 4n + gap * 4n;
    let action_width = (width - gap) / 2n;
    if (
        (
            <Button
                session={Model.CurrentSession()}
                props={{
                    key: u64(5770011n),
                    bounds: Bounds(x, action_y, action_width, action_height),
                    label: Locale("cancel_button"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        CancelRound();
        return;
    }
    if (
        (
            <Button
                session={Model.CurrentSession()}
                props={{
                    key: u64(5770012n),
                    bounds: Bounds(x + action_width + gap, action_y, action_width, action_height),
                    label: Locale("save_button")
                }}
            />
        )
    ) {
        SaveRound();
    }
}

// The day's screen: its title bar with Close, then its content scrolling
// in a centred column, and the number pad while a round is changed.
function DayScreen(): void {
    const day_state = Model.CurrentDay();
    let top_height = Scale(58n);
    let max_width = Scale(400n);
    let y = top_height + Scale(14n);
    let viewport_height = day_state.view_height - top_height - day_state.bottom - KeyboardHeight();
    if (viewport_height < Scale(80n)) {
        viewport_height = Scale(80n);
    }
    let options = NewOptions();
    <TitleBar
        session={Model.CurrentSession()}
        props={{
            title: day_state.title,
            height: top_height,
            bounds: Bounds(0n, 0n, day_state.view_width, top_height)
        }}
        options={options[0n:0n]}
    />;
    let button_total = Scale(22n) + Scale(11n) * 2n;
    let close_y = (top_height - button_total) / 2n;
    if (close_y < 0n) {
        close_y = 0n;
    }
    let close_label = Locale("close_button");
    if (
        !day_state.modal_active && (
            <Button
                session={Model.CurrentSession()}
                props={{
                    id: 9101n,
                    bounds: Bounds(
                        day_state.view_width - button_total - Scale(8n),
                        close_y,
                        button_total,
                        button_total
                    ),
                    label: close_label,
                    image: UiImage(close_label, 448.0, 384.0),
                    icon_only: true,
                    circle: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        CancelRound();
        DayAsk(HABITS_DAY_SCREEN_CLOSE, -1n, 0n);
        return;
    }
    let side = Scale(16n);
    let content_x = side;
    let content_width = day_state.view_width - side * 2n;
    if (content_width > max_width) {
        content_x += (content_width - max_width) / 2n;
        content_width = max_width;
    }
    let content_height = DayContent(content_x, content_width, y, false) - y;
    const scroll = (
        <Scroll
            session={Model.CurrentSession()}
            props={{
                key: NativeLayout.KeyHash("inbe/screens/habits/session/scroll/1"),
                bounds: Bounds(0n, y, day_state.view_width, viewport_height),
                content_height: content_height,
                scroll_offset: day_state.scroll
            }}
            children={(scroll: NativeScroll.ScrollResult): void => {
                const day_state = Model.CurrentDay();
                day_state.scroll = scroll.scroll_offset;
                DayContent(content_x, content_width, s32(scroll.content.y), true);
            }}
        />
    );
    if (!scroll.opened) {
        day_state.scroll = scroll.scroll_offset;
    }
    if (day_state.editing) {
        RoundKeys();
        NumberPad();
    }
}

export function HabitsDayView(message: HabitsMessage): HabitsMessage {
    const day_state = Model.CurrentDay();
    Model.SetDay(ReadHabitsDayHost());
    Model.SetSession(day_state.session);
    Model.look_scale = day_state.scale;
    Model.look_font = day_state.font;
    Model.look_small_font = day_state.small_font;
    Model.look_muted = day_state.muted_class;
    day_state.action = HABITS_DAY_SCREEN_NONE;
    day_state.action_index = -1n;
    day_state.action_round = -1n;
    day_state.action_step = 0n;
    if (
        day_state.editing &&
        (day_state.edit_session < 0n || day_state.edit_session >= day_state.session_count)
    ) {
        CancelRound();
    }
    DayScreen();
    WriteHabitsDayHost(*day_state);
    message.succeeded = true;
    return message;
}

// A time in the dialog, picked in the time picker: minutes after midnight,
// or -1 while none is chosen. Clear takes it away: a time answer is then
// unanswered, and a span's end empty, so the span keeps running.
function TimeField(
    key: s32,
    label: string,
    x: s32,
    y: s32,
    width: s32,
    value: s32,
    clearable: boolean,
    placeholder: string
): s32 {
    const entry_state = Model.CurrentEntry();
    if (label.count > 0n) {
        <Text
            session={Model.CurrentSession()}
            props={{
                bounds: Bounds(x, y, width, Scale(24n)),
                text: label,
                size: Model.look_font,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
    }
    let picker_width = Scale(160n);
    if (picker_width > width) {
        picker_width = width;
    }
    let picked = (
        <TimePicker
            session={Model.CurrentSession()}
            props={{
                key: NativeLayout.KeyHash("habits/answers/time") + u64(key),
                id: 7960n + key,
                bounds: Bounds(x, y + Scale(DAY_ANSWER_INPUT_Y), picker_width, Scale(44n)),
                label: label,
                value: value,
                now: entry_state.now,
                now_label: Locale("statistics_now_label"),
                done_label: Locale("done_button"),
                clear_label: clearable ? Locale("clear_button") : "",
                placeholder: placeholder,
                scale: Model.look_scale
            }}
        />
    );
    if (picked.changed) {
        return picked.value;
    }
    return value;
}

// A typed answer. Fields share one cursor: only the focused one has it.
function AnswerField(
    index: s32,
    answer: *HabitsAnswer,
    bounds: Rectangle,
    numeric: boolean,
    max_bytes: s32
): boolean {
    const entry_state = Model.CurrentEntry();
    let focused = entry_state.focus === index;
    let props: NativeTextField.Props = {
        key: NativeLayout.KeyHash("habits/answers/field") + u64(index),
        bounds: bounds,
        value: answer.value,
        focused: focused,
        focus_id: 7800n + index,
        numeric: numeric,
        max_bytes: max_bytes,
        max_codepoints: max_bytes,
        disabled: entry_state.modal_active
    };
    if (focused) {
        props.cursor = entry_state.cursor;
        props.anchor = entry_state.anchor;
        props.scroll_x = entry_state.scroll_x;
        props.input = entry_state.input;
    }
    let result = <ControlledTextField session={Model.CurrentSession()} props={props} />;
    let changed = false;
    if (result.edit.changed) {
        answer.value = Replaced(
            answer.value,
            result.edit.start,
            result.edit.end,
            result.edit.replacement,
            max_bytes
        );
        changed = true;
    }
    if (result.focused) {
        entry_state.focus = index;
        entry_state.cursor = result.cursor;
        entry_state.anchor = result.anchor;
        entry_state.scroll_x = result.scroll_x;
    } else if (focused) {
        entry_state.focus = -1n;
    }
    if (result.committed) {
        EntryAsk(HABITS_ENTRY_SAVE);
    }
    if (result.clipboard_write) {
        entry_state.clipboard_write = true;
        entry_state.clipboard_text = result.clipboard_text;
    }
    return changed;
}

// A yes or no answer: tapping the chosen one again leaves it unanswered.
function YesNo(answer: *HabitsAnswer, id: s32, x: s32, y: s32, width: s32): boolean {
    const entry_state = Model.CurrentEntry();
    let gap = Scale(8n);
    let half = (width - gap) / 2n;
    let values: [string, string] = ["yes", "no"];
    let labels: [string, string] = [Locale("habit_answer_yes"), Locale("habit_answer_no")];
    let changed = false;
    for (let option = s32(0n); option <= 1n; option += s32(1)) {
        let chosen = answer.value === values[option];
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        id: id + option,
                        bounds: Bounds(x + option * (half + gap), y, half, Scale(44n)),
                        label: labels[option],
                        tone: chosen ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
                        emphasis: chosen
                            ? ButtonEmphasis.ButtonEmphasisFilled
                            : ButtonEmphasis.ButtonEmphasisSoft,
                        disabled: entry_state.modal_active
                    }}
                />
            )
        ) {
            answer.value = chosen ? "" : values[option];
            changed = true;
        }
    }
    return changed;
}

// The entry's span start and end, then each question above its answer in
// the input its answer type takes.
function AnswerFields(x: s32, y: s32, width: s32): void {
    const entry_state = Model.CurrentEntry();
    if (entry_state.span) {
        let start_label = Locale("habit_span_start");
        if (entry_state.start_answer >= 0n) {
            start_label = ReadHabitsAnswerHost(entry_state.start_answer).question;
        }
        entry_state.start = TimeField(0n, start_label, x, y, width, entry_state.start, false, "");
        y += Scale(DAY_ANSWER_ROW_HEIGHT);
        // Without an end the span keeps running; the end is only ever set
        // here, by picking it or by Now.
        let end_label = Locale("habit_span_end");
        if (entry_state.end_answer >= 0n) {
            end_label = ReadHabitsAnswerHost(entry_state.end_answer).question;
        }
        entry_state.end = TimeField(
            1n,
            end_label,
            x,
            y,
            width,
            entry_state.end,
            true,
            Locale("habit_span_running")
        );
        let picker_width = Scale(160n);
        let now_width = Scale(96n);
        if (picker_width + Scale(8n) + now_width <= width) {
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={{
                            id: 5730005n,
                            bounds: Bounds(
                                x + picker_width + Scale(8n),
                                y + Scale(DAY_ANSWER_INPUT_Y),
                                now_width,
                                Scale(44n)
                            ),
                            label: Locale("statistics_now_label"),
                            tone: ButtonTone.ButtonToneAccent,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                            disabled: entry_state.modal_active
                        }}
                    />
                )
            ) {
                entry_state.end = entry_state.now;
            }
        }
        y += Scale(DAY_ANSWER_ROW_HEIGHT);
    }
    for (let index = s32(0n); index < entry_state.answer_count; index += s32(1)) {
        if (index === entry_state.start_answer || index === entry_state.end_answer) {
            continue;
        }
        let answer = ReadHabitsAnswerHost(index);
        <Text
            session={Model.CurrentSession()}
            props={{
                bounds: Bounds(x, y, width, Scale(24n)),
                text: answer.question,
                size: Model.look_font,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
        let input_y = y + Scale(DAY_ANSWER_INPUT_Y);
        let changed = false;
        if (answer.answer_type === HABIT_ANSWER_TIME) {
            let picked = TimeField(2n + index, "", x, y, width, answer.time, true, "");
            changed = picked !== answer.time;
            answer.time = picked;
        } else if (answer.answer_type === HABIT_ANSWER_YES_NO) {
            changed = YesNo(&answer, 7900n + index * 2n, x, input_y, width);
        } else if (answer.answer_type === HABIT_ANSWER_NUMBER) {
            changed = AnswerField(
                index,
                &answer,
                Bounds(x, input_y, width, Scale(44n)),
                true,
                9n
            );
        } else {
            changed = AnswerField(
                index,
                &answer,
                Bounds(x, input_y, width, Scale(44n)),
                false,
                HABIT_ANSWER_SIZE - 1n
            );
        }
        if (changed) {
            WriteHabitsAnswerHost(index, answer);
        }
        y += Scale(DAY_ANSWER_ROW_HEIGHT);
    }
}

// The fields in a scrolling area, for entries that do not all fit.
function AnswerArea(bounds: Rectangle): void {
    const entry_state = Model.CurrentEntry();
    const scroll = NativeScroll.Draw(Model.CurrentSession(), {
        key: NativeLayout.KeyHash("habits/answers/scroll"),
        bounds: bounds,
        content_height: AnswersHeight(),
        scroll_offset: entry_state.scroll,
        scale: Model.look_scale
    });
    entry_state.scroll = scroll.scroll_offset;
    if (scroll.opened) {
        AnswerFields(s32(scroll.content.x), s32(scroll.content.y), s32(scroll.content.width));
        End(Model.CurrentSession());
    }
}

// The entry dialog. Done records a new entry and Skip records it without
// answers; an entry that exists is saved again or deleted.
function EntryDialog(): void {
    const entry_state = Model.CurrentEntry();
    let gap = Scale(12n);
    // The day sits under the name, in the frame's gap above the content.
    let date_lift = Scale(16n);
    let date_height = Scale(22n);
    let button_height = Scale(44n);
    let date_room = date_height - date_lift + Scale(10n);
    let area_height = AnswerAreaHeight(date_room + gap + button_height);
    let content_height = date_room + area_height + gap + button_height;
    let frame = NativeModal.Draw(Model.CurrentSession(), {
        key: NativeLayout.KeyHash("habits/entry-dialog"),
        title: entry_state.name,
        strong_title: true,
        title_at_start: true,
        width: Scale(380n),
        height: content_height + Scale(74n),
        scale: Model.look_scale,
        has_right_action: true,
        right_label: Locale("cancel_button")
    });
    if (frame.dismissed || frame.right_clicked) {
        EntryAsk(HABITS_ENTRY_CANCEL);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content = frame.layout.content;
    let x = s32(content.x);
    let y = s32(content.y);
    let width = s32(content.width);
    let day_text =
        entry_state.day === entry_state.today ? Locale("habits_today") : DateText(entry_state.day);
    <Text
        session={Model.CurrentSession()}
        props={{
            bounds: Bounds(x, y - date_lift, width, date_height),
            text: day_text,
            size: Model.look_small_font,
            class_name: Model.look_muted,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    y += date_room;
    AnswerArea(Bounds(x, y, width, area_height));
    y += area_height + gap;
    if (entry_state.existing) {
        let half = (width - gap) / 2n;
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        id: 5730001n,
                        bounds: Bounds(x, y, half, button_height),
                        label: Locale("delete_button"),
                        tone: ButtonTone.ButtonToneDanger,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            EntryAsk(HABITS_ENTRY_DELETE);
        }
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        id: 5730002n,
                        bounds: Bounds(x + half + gap, y, width - half - gap, button_height),
                        label: Locale("save_button"),
                        tone: ButtonTone.ButtonToneAccent,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled
                    }}
                />
            )
        ) {
            EntryAsk(HABITS_ENTRY_SAVE);
        }
    } else {
        // Questions can be skipped: the day is done without answers.
        let done_x = x;
        if (entry_state.answer_count > 0n) {
            let half = (width - gap) / 2n;
            if (
                (
                    <Button
                        session={Model.CurrentSession()}
                        props={{
                            id: 5730004n,
                            bounds: Bounds(x, y, half, button_height),
                            label: Locale("skip_button"),
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft
                        }}
                    />
                )
            ) {
                EntryAsk(HABITS_ENTRY_SKIP);
            }
            done_x = x + half + gap;
        }
        if (
            (
                <Button
                    session={Model.CurrentSession()}
                    props={{
                        id: 5730003n,
                        bounds: Bounds(done_x, y, x + width - done_x, button_height),
                        label: Locale("done_button"),
                        tone: ButtonTone.ButtonToneAccent,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled
                    }}
                />
            )
        ) {
            EntryAsk(HABITS_ENTRY_SAVE);
        }
    }
    End(Model.CurrentSession());
}

export function HabitsEntryView(message: HabitsMessage): HabitsMessage {
    const entry_state = Model.CurrentEntry();
    Model.SetEntry(ReadHabitsEntryHost());
    Model.SetSession(entry_state.session);
    Model.look_scale = entry_state.scale;
    Model.look_font = entry_state.font;
    Model.look_small_font = entry_state.small_font;
    Model.look_muted = entry_state.muted_class;
    entry_state.action = HABITS_ENTRY_NONE;
    entry_state.clipboard_write = false;
    entry_state.clipboard_text = "";
    EntryDialog();
    WriteHabitsEntryHost(*entry_state);
    message.succeeded = true;
    return message;
}
