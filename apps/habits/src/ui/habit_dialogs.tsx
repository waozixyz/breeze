// Habits draws a counting habit's count dialog: the day's count with large
// steps down and up. The host supplies the day's count and the theme, and
// applies the step or opens the day the dialog asks for.
import { color_with_alpha } from "color";
import { HabitEditorDialog } from "editor_dialogs";
import * as Model from "habits_view";
import {
    Bounds,
    CurrentCountLabel,
    CounterTargetLabel,
    CountText,
    DayText,
    HabitsLocaleHost,
    NewCountStrong,
    ReadHabitsUiHost,
    Scale,
    WriteHabitsUiHost
} from "habits_view";
import {
    HABITS_COUNT_CLOSE,
    HABITS_COUNT_DECREMENT,
    HABITS_COUNT_INCREMENT,
    HABITS_COUNT_NONE,
    HABITS_COUNT_OPEN_DAY,
    HABITS_DELETE_DIALOG,
    HabitsMessage
} from "habits_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";

function CountLabel(bounds: Rectangle, text: string): void {
    const frame_state = Model.CurrentFrame();
    <Text
        session={frame_state.session}
        props={{
            bounds: bounds,
            text: text,
            size: frame_state.small_font,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

// A step button draws its minus or plus as bars sized to the button, which
// read clearly where a "-" or "+" glyph is thin and small.
function StepButton(id: s32, bounds: Rectangle, plus: boolean, disabled: boolean): boolean {
    const frame_state = Model.CurrentFrame();
    let clicked = (
        <Button
            session={frame_state.session}
            props={{
                id: id,
                bounds: bounds,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: disabled
            }}
        />
    );
    let side = bounds.height;
    if (bounds.width < side) {
        side = bounds.width;
    }
    let length = side * 0.36;
    let thickness = float32(Scale(3n));
    let center_x = bounds.x + bounds.width * 0.5;
    let center_y = bounds.y + bounds.height * 0.5;
    let color = frame_state.text_color;
    if (disabled) {
        color = color_with_alpha(color, 0.35);
    }
    <Box
        session={frame_state.session}
        props={{
            bounds: {
                x: center_x - length * 0.5,
                y: center_y - thickness * 0.5,
                width: length,
                height: thickness
            },
            fill: color,
            radius: thickness * 0.5
        }}
    />;
    if (plus) {
        <Box
            session={frame_state.session}
            props={{
                bounds: {
                    x: center_x - thickness * 0.5,
                    y: center_y - length * 0.5,
                    width: thickness,
                    height: length
                },
                fill: color,
                radius: thickness * 0.5
            }}
        />;
    }
    return clicked;
}

// Draws the dialog and leaves in frame.action what the host does next.
function CountDialog(): void {
    const frame_state = Model.CurrentFrame();
    frame_state.action = HABITS_COUNT_NONE;
    let gap = Scale(12n);
    let step_h = Scale(56n);
    let button_h = Scale(44n);
    let content_h = Scale(24n) + Scale(64n) + Scale(24n) + gap + step_h + gap + button_h;
    if (frame_state.linked_count > 0n) {
        content_h += button_h + gap;
    }
    // A counting habit that asks questions keeps their answers as the
    // day's entries, opened from here.
    if (frame_state.asks) {
        content_h += button_h + gap;
    }
    let dialog = NativeModal.Draw(frame_state.session, {
        key: NativeLayout.KeyHash("habits/count-dialog"),
        title: frame_state.name,
        strong_title: true,
        width: Scale(340n),
        height: content_h + Scale(74n),
        scale: frame_state.scale,
        has_right_action: true,
        right_label: HabitsLocaleHost("close_button")
    });
    if (dialog.dismissed || dialog.right_clicked) {
        frame_state.action = HABITS_COUNT_CLOSE;
        return;
    }
    if (!dialog.opened) {
        return;
    }
    let content = dialog.layout.content;
    let x = s32(content.x);
    let y = s32(content.y);
    let width = s32(content.width);
    let day_text = DayText(frame_state.day);
    if (frame_state.today) {
        day_text = HabitsLocaleHost("habits_today");
    }
    CountLabel(Bounds(x, y, width, Scale(24n)), day_text);
    y += Scale(24n);
    const count_text = CurrentCountLabel();
    let count_strong = NewCountStrong();
    count_strong[0n] = { start: 0n, end: s32(count_text.count) };
    <Text
        session={frame_state.session}
        props={{
            bounds: Bounds(x, y, width, Scale(64n)),
            text: count_text,
            size: Scale(NativeText.Text48),
            strong: count_strong[:],
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    y += Scale(64n);
    CountLabel(Bounds(x, y, width, Scale(24n)), CounterTargetLabel());
    y += Scale(24n) + gap;
    let step_w = (width - gap) / 2n;
    if (
        StepButton(
            5720000n,
            Bounds(x, y, step_w, step_h),
            false,
            frame_state.count <= frame_state.linked_count
        )
    ) {
        frame_state.action = HABITS_COUNT_DECREMENT;
    }
    if (StepButton(5720001n, Bounds(x + width - step_w, y, step_w, step_h), true, false)) {
        frame_state.action = HABITS_COUNT_INCREMENT;
    }
    y += step_h + gap;
    if (frame_state.asks) {
        if (
            (
                <Button
                    session={frame_state.session}
                    props={{
                        id: 5720004n,
                        bounds: Bounds(x, y, width, button_h),
                        label: HabitsLocaleHost("habit_day_entries"),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisOutline
                    }}
                />
            )
        ) {
            End(frame_state.session);
            frame_state.action = HABITS_COUNT_OPEN_DAY;
            return;
        }
        y += button_h + gap;
    }
    if (frame_state.linked_count > 0n) {
        let template = HabitsLocaleHost(
            frame_state.linked_count === 1n ? "session_count_singular" : "session_count_plural"
        );
        if (
            (
                <Button
                    session={frame_state.session}
                    props={{
                        id: 5720002n,
                        bounds: Bounds(x, y, width, button_h),
                        label: CountText(template, frame_state.linked_count),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisOutline
                    }}
                />
            )
        ) {
            End(frame_state.session);
            frame_state.action = HABITS_COUNT_OPEN_DAY;
            return;
        }
        y += button_h + gap;
    }
    if (
        (
            <Button
                session={frame_state.session}
                props={{
                    id: 5720003n,
                    bounds: Bounds(x, y, width, button_h),
                    label: HabitsLocaleHost("done_button"),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }}
            />
        )
    ) {
        frame_state.action = HABITS_COUNT_CLOSE;
    }
    End(frame_state.session);
}

export function HabitsCountView(message: HabitsMessage): HabitsMessage {
    const frame_state = Model.CurrentFrame();
    Model.SetFrame(ReadHabitsUiHost());
    CountDialog();
    WriteHabitsUiHost(*frame_state);
    message.succeeded = true;
    return message;
}

export function HabitsEditorView(message: HabitsMessage): HabitsMessage {
    const frame_state = Model.CurrentFrame();
    Model.SetFrame(ReadHabitsUiHost());
    let deleting = message.action === HABITS_DELETE_DIALOG;
    let result = (
        <HabitEditorDialog
            session={frame_state.session}
            deleting={deleting}
            title={HabitsLocaleHost(deleting ? "habit_delete_title" : "habit_unsaved_title")}
            message={HabitsLocaleHost(deleting ? "habit_delete_message" : "habit_unsaved_message")}
            keep_editing={HabitsLocaleHost("habit_keep_editing")}
            save={HabitsLocaleHost("save_button")}
            discard={HabitsLocaleHost("discard_button")}
            cancel={HabitsLocaleHost("cancel_button")}
            delete_label={HabitsLocaleHost("delete_button")}
        />
    );
    frame_state.action = result.action;
    WriteHabitsUiHost(*frame_state);
    message.succeeded = true;
    return message;
}
