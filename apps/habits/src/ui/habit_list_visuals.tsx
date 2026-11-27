import * as Cards from "habit_cards";
import * as Shared from "habit_shared";
import * as Model from "habit_list_view";
import * as NativeButton from "kryon/button";
import { ButtonState } from "kryon/control_props";
import { Color } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import * as NativePress from "kryon/press";
import * as NativeText from "kryon/text";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Press } from "kryon/tsx/press";

export function Fill(bounds: Rectangle, radius: float32, color: Color): void {
    const list_state = Model.CurrentList();
    <Box session={list_state.session} props={{ bounds: bounds, fill: color, radius: radius }} />;
}

export function Circle(x: s32, y: s32, radius: s32, color: Color): void {
    Fill(Shared.Bounds(x - radius, y - radius, radius * 2n, radius * 2n), float32(radius), color);
}

export function Outline(bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let radius = float32(Model.Scale(12n));
    let color = Shared.Alpha(list_state.text_color, 0.8);
    <Box session={list_state.session} props={{ bounds: bounds, border: color, radius: radius }} />;
    let inset = float32(Model.Hairline());
    <Box
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + inset,
                y: bounds.y + inset,
                width: bounds.width - inset * 2.0,
                height: bounds.height - inset * 2.0
            },
            border: color,
            radius: radius - inset
        }}
    />;
}

export function PressButton(
    face: NativeButton.Props,
    press: NativePress.Props
): NativePress.PressResult {
    const list_state = Model.CurrentList();
    face.key = u64(Model.LIST_FACE_KEYS + press.id);
    face.id = 0n;
    face.disabled = face.disabled || list_state.modal_active;
    face.state = Model.FaceState(face.bounds, face.selected);
    if (face.disabled) {
        face.state = ButtonState.ButtonStateAuto;
    }
    let activated = Button({ session: list_state.session, props: face });
    press.key = u64(press.id);
    press.bounds = face.bounds;
    press.label = face.label;
    press.now = list_state.now;
    press.disabled = press.disabled || face.disabled;
    let result = Press({ session: list_state.session, props: press });
    result.clicked = result.clicked || activated;
    return result;
}

export function CoinAmount(amount: string, bounds: Rectangle, font: s32): void {
    Cards.CoinAmount(Model.SurfaceStyle(), amount, bounds, font, NativeText.Wrap.TextWrapEllipsis);
}

export function FigureCard(bounds: Rectangle, label: string, value: string, accent: Color): void {
    Cards.FigureCard(Model.SurfaceStyle(), bounds, label, value, accent);
}
