// Shared cards compose Kryon widgets; sizing and theme rules live in cards.zi.
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import * as NativeText from "kryon/text";
import { Rectangle } from "kryon/geometry";
import { Color } from "kryon/drawing_props";
import { SemanticKind } from "kryon/semantic";
import { Session } from "kryon/session";
import {
    CARD_RADIUS,
    CARD_PADDING,
    CardProps,
    StrongWhole,
    MutedTextClass,
    SectionTitleFont,
    SectionTitleHeight
} from "cards";
import { AppScale, AppSmallFontSize, AppFitFontSize } from "metrics";

export function SectionTitle(session: Session, title: string, x: s32, y: s32, width: s32): s32 {
    const height = SectionTitleHeight(title, width);
    const strong = StrongWhole(title);
    <Text
        session={session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(y),
                width: float32(width),
                height: float32(height)
            },
            text: title,
            size: SectionTitleFont(),
            strong: nativeSlice(strong),
            semantic_kind: SemanticKind.SemanticHeading,
            heading_level: s32(2),
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    return height;
}

export function FigureCard(
    session: Session,
    bounds: Rectangle,
    label: string,
    value: string,
    accent: Color
): void {
    const radius = float32(AppScale(CARD_RADIUS));
    const bar = float32(AppScale(s32(5)));
    <Box session={session} props={{ bounds: bounds, fill: accent, radius: radius }} />;
    let face = CardProps({
        x: bounds.x + bar,
        y: bounds.y,
        width: bounds.width - bar,
        height: bounds.height
    });
    const transparent: Color = {};
    face.border = transparent;
    <Box session={session} props={face} />;
    let edge = CardProps(bounds);
    edge.fill = transparent;
    <Box session={session} props={edge} />;
    const pad = float32(AppScale(CARD_PADDING));
    const inner = bounds.width - bar - pad * 2;
    <Text
        session={session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(AppScale(s32(10))),
                width: inner,
                height: float32(AppScale(s32(22)))
            },
            text: label,
            size: AppSmallFontSize(),
            class_name: MutedTextClass(),
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    const valueFont = AppFitFontSize(
        value,
        s32(inner),
        AppScale(NativeText.Text24),
        AppScale(NativeText.Text16)
    );
    const strong = StrongWhole(value);
    <Text
        session={session}
        props={{
            bounds: {
                x: bounds.x + bar + pad,
                y: bounds.y + float32(AppScale(s32(34))),
                width: inner,
                height: float32(AppScale(s32(32)))
            },
            text: value,
            size: valueFont,
            strong: nativeSlice(strong),
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
}
