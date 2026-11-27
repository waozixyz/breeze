// Authored UI composition; native application state remains in meditation_view.zi.
import * as NativeShape from "kryon/shape";
import * as NativeText from "kryon/text";
import * as State_meditation_view from "meditation_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Vector2 } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import {
    Bounds,
    FitFont,
    ReadPracticeMeditationHost,
    RowX,
    Scale,
    WritePracticeMeditationHost
} from "meditation_view";
import {
    PRACTICE_MEDITATION_EXTEND,
    PRACTICE_MEDITATION_FINISH,
    PRACTICE_MEDITATION_NONE,
    PracticeMessage
} from "practice_types";

export function ExtendControls(y: s32): void {
    let gap = Scale(8n);
    let height = Scale(34n);
    let finish_y = y;
    if (State_meditation_view.meditation.extend) {
        let minutes: [s32, s32, s32] = [1n, 5n, 10n];
        let labels: [string, string, string] = ["+1", "+5", "+10"];
        let width = Scale(58n);
        let x = RowX(State_meditation_view.meditation.center_x, width * 3n + gap * 2n);
        for (let index = s32(0n); index <= 2n; index += s32(1)) {
            if (
                Button({
                    session: State_meditation_view.meditation.session,
                    props: {
                        bounds: Bounds(x + index * (width + gap), y, width, height),
                        label: nativeAt(labels, index),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }
                })
            ) {
                State_meditation_view.meditation.action = PRACTICE_MEDITATION_EXTEND;
                State_meditation_view.meditation.value = nativeAt(minutes, index) * 60n;
            }
        }
        finish_y = y + height + Scale(10n);
    }
    if (!State_meditation_view.meditation.complete) {
        return;
    }
    let finish_width = Scale(96n);
    if (
        Button({
            session: State_meditation_view.meditation.session,
            props: {
                bounds: Bounds(
                    RowX(State_meditation_view.meditation.center_x, finish_width),
                    finish_y,
                    finish_width,
                    height
                ),
                label: State_meditation_view.meditation.finish_label,
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        })
    ) {
        State_meditation_view.meditation.action = PRACTICE_MEDITATION_FINISH;
    }
}

export function PracticeMeditationView(message: PracticeMessage): PracticeMessage {
    State_meditation_view.meditation = ReadPracticeMeditationHost();
    State_meditation_view.meditation.action = PRACTICE_MEDITATION_NONE;
    State_meditation_view.meditation.value = 0n;
    let radius = Scale(86n);
    let center: Vector2 = {
        x: float32(State_meditation_view.meditation.center_x),
        y: float32(State_meditation_view.meditation.center_y)
    };
    let halo = State_meditation_view.meditation.accent_color;
    halo.a = u8(255.0 * 0.24);
    NativeShape.Circle(State_meditation_view.meditation.session, {
        center: center,
        radius: float32(radius + Scale(20n)),
        fill: halo
    });
    NativeShape.Circle(State_meditation_view.meditation.session, {
        center: center,
        radius: float32(radius),
        fill: State_meditation_view.meditation.accent_color
    });
    <Text
        session={State_meditation_view.meditation.session}
        props={{
            text: State_meditation_view.meditation.time_text,
            bounds: Bounds(
                State_meditation_view.meditation.center_x - radius,
                State_meditation_view.meditation.center_y - radius,
                radius * 2n,
                radius * 2n
            ),
            size: FitFont(
                State_meditation_view.meditation.time_text,
                radius * 2n - Scale(20n),
                Scale(NativeText.Text24),
                Scale(NativeText.Text16)
            ),
            class_name: State_meditation_view.meditation.ink_class,
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    ExtendControls(State_meditation_view.meditation.center_y + radius + Scale(24n));
    WritePracticeMeditationHost(State_meditation_view.meditation);
    message.succeeded = true;
    return message;
}
