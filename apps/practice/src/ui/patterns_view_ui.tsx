// Authored UI composition; native application state remains in patterns_view.zi.
import * as NativeShape from "kryon/shape";
import * as NativeText from "kryon/text";
import * as State_patterns_view from "patterns_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle, Vector2 } from "kryon/geometry";
import { TextHeight } from "kryon/text_measure";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import {
    NewDigits,
    ReadPracticePatternsHost,
    Scale,
    Width,
    WritePracticePatternsHost
} from "patterns_view";
import {
    PRACTICE_PATTERNS_NONE,
    PRACTICE_PATTERNS_PAUSE,
    PRACTICE_PATTERNS_RESUME,
    PracticeMessage
} from "practice_types";
import { FormatInteger } from "std/number_text";

export function CenteredLine(text: string, font: s32, x: s32, y: s32, ink_class: s32 = 0n): void {
    let width = Width(text, font);
    let height = TextHeight(State_patterns_view.patterns.session, { text: text, size: font });
    <Text
        session={State_patterns_view.patterns.session}
        props={{
            text: text,
            size: font,
            class_name: ink_class,
            bounds: {
                x: float32(x - width / 2n),
                y: float32(y - height / 2n),
                width: float32(width),
                height: float32(height)
            },
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function PracticePatternsView(message: PracticeMessage): PracticeMessage {
    State_patterns_view.patterns = ReadPracticePatternsHost();
    State_patterns_view.patterns.action = PRACTICE_PATTERNS_NONE;
    State_patterns_view.patterns.value = 0n;
    let center_x = State_patterns_view.patterns.center_x;
    let center_y = State_patterns_view.patterns.center_y;
    let center: Vector2 = { x: float32(center_x), y: float32(center_y) };
    NativeShape.Circle(State_patterns_view.patterns.session, {
        center: center,
        radius: float32(State_patterns_view.patterns.max_radius),
        fill: State_patterns_view.patterns.well_color
    });
    NativeShape.Circle(State_patterns_view.patterns.session, {
        center: center,
        radius: State_patterns_view.patterns.circle_radius,
        fill: State_patterns_view.patterns.accent_color
    });
    let phase_font = Scale(NativeText.Text32);
    if (
        Width(State_patterns_view.patterns.phase_label, phase_font) >
        State_patterns_view.patterns.view_width - Scale(80n)
    ) {
        phase_font = Scale(NativeText.Text24);
    }
    let digits = NewDigits();
    let counter = FormatInteger(
        s64(State_patterns_view.patterns.phase_seconds),
        digits[:]
    );
    CenteredLine(
        counter,
        Scale(NativeText.Text48),
        center_x,
        center_y - Scale(16n),
        State_patterns_view.patterns.ink_class
    );
    CenteredLine(
        State_patterns_view.patterns.phase_label,
        phase_font,
        center_x,
        center_y + Scale(36n),
        State_patterns_view.patterns.ink_class
    );
    let status_font = Scale(NativeText.Text20);
    if (
        Width(State_patterns_view.patterns.status, status_font) >
        State_patterns_view.patterns.view_width - Scale(96n)
    ) {
        status_font = State_patterns_view.patterns.small_font;
    }
    CenteredLine(
        State_patterns_view.patterns.status,
        status_font,
        center_x,
        State_patterns_view.patterns.status_y
    );
    let width = State_patterns_view.patterns.view_width - Scale(112n);
    let bounds: Rectangle = {
        x: float32(center_x - width / 2n),
        y: float32(center_y + State_patterns_view.patterns.max_radius + Scale(42n)),
        width: float32(width),
        height: float32(Scale(56n))
    };
    if (State_patterns_view.patterns.paused) {
        if (
            (
                <Button
                    session={State_patterns_view.patterns.session}
                    props={{
                        bounds: bounds,
                        label: State_patterns_view.patterns.resume_label,
                        tone: ButtonTone.ButtonToneAccent,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled
                    }}
                />
            )
        ) {
            State_patterns_view.patterns.action = PRACTICE_PATTERNS_RESUME;
        }
    } else if (
        (
            <Button
                session={State_patterns_view.patterns.session}
                props={{
                    bounds: bounds,
                    label: State_patterns_view.patterns.pause_label,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        State_patterns_view.patterns.action = PRACTICE_PATTERNS_PAUSE;
    }
    WritePracticePatternsHost(State_patterns_view.patterns);
    message.succeeded = true;
    return message;
}
