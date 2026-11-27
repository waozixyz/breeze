import { HabitsCoinColor } from "coin_color";
import * as Model from "habit_list_view";
import {
    Alpha,
    Bounds,
    FaceState,
    FitFont,
    Hairline,
    LIST_CARD_PADDING,
    LIST_CARD_RADIUS,
    LIST_FACE_KEYS,
    NewStrong,
    Scale
} from "habit_list_view";
import * as NativeButton from "kryon/button";
import { ButtonState } from "kryon/control_props";
import { Color } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import * as NativePress from "kryon/press";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Press } from "kryon/tsx/press";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import * as NativeCoinIcon from "mingcute/mingcute_filled_copper_coin";

export function Fill(bounds: Rectangle, radius: float32, color: Color): void {
    const list_state = Model.CurrentList();
    <Box session={list_state.session} props={{ bounds: bounds, fill: color, radius: radius }} />;
}

export function Circle(x: s32, y: s32, radius: s32, color: Color): void {
    Fill(Bounds(x - radius, y - radius, radius * 2n, radius * 2n), float32(radius), color);
}

export function Outline(bounds: Rectangle): void {
    const list_state = Model.CurrentList();
    let radius = float32(Scale(12n));
    let color = Alpha(list_state.text_color, 0.8);
    <Box session={list_state.session} props={{ bounds: bounds, border: color, radius: radius }} />;
    let inset = float32(Hairline());
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
    face.key = u64(LIST_FACE_KEYS + press.id);
    face.id = 0n;
    face.disabled = face.disabled || list_state.modal_active;
    face.state = FaceState(face.bounds, face.selected);
    if (face.disabled) {
        face.state = ButtonState.ButtonStateAuto;
    }
    let activated = <Button session={list_state.session} props={face} />;
    press.key = u64(press.id);
    press.bounds = face.bounds;
    press.label = face.label;
    press.now = list_state.now;
    press.disabled = press.disabled || face.disabled;
    let result = <Press session={list_state.session} props={press} />;
    result.clicked = result.clicked || activated;
    return result;
}

export function CoinAmount(amount: string, bounds: Rectangle, font: s32): void {
    const list_state = Model.CurrentList();
    let size = float32(font);
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x,
                y: bounds.y + (bounds.height - size) * 0.5,
                width: size,
                height: size
            },
            shape: NativeCoinIcon.Shape,
            color: HabitsCoinColor(list_state.highlight_color, list_state.text_color)
        }}
    />;
    let strong = NewStrong();
    strong[0n] = { start: 0n, end: s32(amount.count) };
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + size + float32(Scale(6n)),
                y: bounds.y,
                width: bounds.width - size - float32(Scale(6n)),
                height: bounds.height
            },
            text: amount,
            size: font,
            strong: strong[:],
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
}

export function FigureCard(bounds: Rectangle, label: string, value: string, accent: Color): void {
    const list_state = Model.CurrentList();
    let radius = float32(Scale(LIST_CARD_RADIUS));
    let bar = float32(Scale(5n));
    Fill(bounds, radius, accent);
    <Box
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar,
                y: bounds.y,
                width: bounds.width - bar,
                height: bounds.height
            },
            fill: list_state.card_fill,
            radius: radius
        }}
    />;
    <Box
        session={list_state.session}
        props={{ bounds: bounds, border: list_state.card_border, radius: radius }}
    />;
    let pad = float32(Scale(LIST_CARD_PADDING));
    let inner = bounds.width - bar - pad * 2.0;
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(10n)),
                width: inner,
                height: float32(Scale(22n))
            },
            text: label,
            size: list_state.small_font,
            class_name: list_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let strong = NewStrong();
    strong[0n] = { start: 0n, end: s32(value.count) };
    <Text
        session={list_state.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Scale(34n)),
                width: inner,
                height: float32(Scale(32n))
            },
            text: value,
            size: FitFont(value, s32(inner), Scale(NativeText.Text24), Scale(NativeText.Text16)),
            strong: strong[:],
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}
