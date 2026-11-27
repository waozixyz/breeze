import * as Shared from "habit_shared";
import { Rectangle } from "kryon/geometry";
import { Color } from "kryon/drawing_props";
import { ButtonEmphasis } from "kryon/control_props";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import * as CoinIcon from "mingcute/mingcute_filled_copper_coin";

export function CoinAmount(
    surface: Shared.Surface,
    amount: string,
    bounds: Rectangle,
    font: s32,
    wrap: NativeText.Wrap
): void {
    let size = float32(font);
    let gap = float32(Shared.SurfaceScale(surface, 6n));
    <SvgIcon
        session={surface.session}
        props={{
            bounds: {
                x: bounds.x,
                y: bounds.y + (bounds.height - size) * 0.5,
                width: size,
                height: size
            },
            shape: CoinIcon.Shape,
            color: surface.coin
        }}
    />;
    let strong = Shared.Strong(amount);
    <Text
        session={surface.session}
        props={{
            bounds: {
                x: bounds.x + size + gap,
                y: bounds.y,
                width: bounds.width - size - gap,
                height: bounds.height
            },
            text: amount,
            size: font,
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: wrap
        }}
    />;
}

export function FigureCard(
    surface: Shared.Surface,
    bounds: Rectangle,
    label: string,
    value: string,
    accent: Color
): void {
    let radius = float32(surface.radius);
    let bar = float32(Shared.SurfaceScale(surface, 5n));
    let pad = float32(surface.padding);
    let inner = bounds.width - bar - pad * 2.0;
    <Box session={surface.session} props={{ bounds: bounds, fill: accent, radius: radius }} />;
    <Box
        session={surface.session}
        props={{
            bounds: {
                x: bounds.x + bar,
                y: bounds.y,
                width: bounds.width - bar,
                height: bounds.height
            },
            fill: surface.fill,
            radius: radius
        }}
    />;
    <Box
        session={surface.session}
        props={{ bounds: bounds, border: surface.border, radius: radius }}
    />;
    <Text
        session={surface.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Shared.SurfaceScale(surface, 10n)),
                width: inner,
                height: float32(Shared.SurfaceScale(surface, 22n))
            },
            text: label,
            size: surface.small_font,
            class_name: surface.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let strong = Shared.Strong(value);
    <Text
        session={surface.session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(Shared.SurfaceScale(surface, 34n)),
                width: inner,
                height: float32(Shared.SurfaceScale(surface, 32n))
            },
            text: value,
            size: Shared.SurfaceFigureFont(surface, value, s32(inner)),
            strong: nativeSlice(strong),
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}

export function PageHeader(
    surface: Shared.Surface,
    bounds: Rectangle,
    id: s32,
    title: string,
    subtitle: string,
    single_line: boolean,
    back_label: string
): s32 {
    let x = s32(bounds.x);
    let y = s32(bounds.y);
    let width = s32(bounds.width);
    let back = back_label;
    let back_width =
        Shared.SurfaceWidth(surface, back, surface.font) + Shared.SurfaceScale(surface, 48n);
    if (back_width < Shared.SurfaceScale(surface, 88n)) {
        back_width = Shared.SurfaceScale(surface, 88n);
    }
    if (back_width > width / 3n) {
        back_width = width / 3n;
    }
    if (
        Button({
            session: surface.session,
            props: {
                id: id,
                bounds: Shared.Bounds(
                    x,
                    y + Shared.SurfaceScale(surface, 2n),
                    back_width,
                    Shared.SurfaceScale(surface, 42n)
                ),
                label: back,
                emphasis: ButtonEmphasis.ButtonEmphasisOutline,
                icon_shape: "S1.8rr:M15 5L8 12L15 19",
                fit_content: true,
                disabled: surface.modal_active
            }
        })
    ) {
        return -1n;
    }
    let title_x = x + back_width + Shared.SurfaceScale(surface, 16n);
    let title_width = width - back_width - Shared.SurfaceScale(surface, 16n);
    let strong = Shared.Strong(title);
    <Text
        session={surface.session}
        props={{
            bounds: Shared.Bounds(
                title_x,
                y,
                title_width,
                Shared.SurfaceScale(surface, single_line ? 46n : 34n)
            ),
            text: title,
            size: Shared.SurfaceTitleFont(surface, title, title_width),
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    if (!single_line) {
        <Text
            session={surface.session}
            props={{
                bounds: Shared.Bounds(
                    title_x,
                    y + Shared.SurfaceScale(surface, 34n),
                    title_width,
                    Shared.SurfaceScale(surface, 22n)
                ),
                text: subtitle,
                size: surface.small_font,
                class_name: surface.muted_class,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
    }
    return y + Shared.SurfaceScale(surface, single_line ? 58n : 68n);
}
