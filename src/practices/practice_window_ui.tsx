// Authored UI composition; native application state remains in practice_window.zi.
import { CssClass } from "css/Css";
import * as NativeLayout from "kryon/layout";
import * as NativeText from "kryon/text";
import { InnerBreeze } from "app_types";
import { Color, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle, Vector2 } from "kryon/geometry";
import { Session } from "kryon/session";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import { AppFitFontSize, AppScale } from "metrics";
import { PracticeWindowCircleBounds } from "practice_window";
import { FrameTextHold } from "text_buffers";

export function PracticeWindowCircleView(
    session: Session,
    bounds: Rectangle,
    share: float32,
    smallest: float32,
    backdrop: Color
): Rectangle {
    if (backdrop.a > 0n) {
        let full = PracticeWindowCircleBounds(bounds, 1.0, smallest);
        <Box
            session={session}
            props={{
                key: NativeLayout.KeyHash("inbe/practice-window/backdrop"),
                bounds: full,
                fill: backdrop,
                radius: full.width * 0.5
            }}
        />;
    }
    let circle = PracticeWindowCircleBounds(bounds, share, smallest);
    <Box
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/practice-window/circle"),
            bounds: circle,
            fill: StyleTokenColor("accent"),
            radius: circle.width * 0.5
        }}
    />;
    return circle;
}

export function PracticeWindowBandView(session: Session, circle: Rectangle, contrast: Color): void {
    let radius = circle.width * 0.5;
    let gap = radius * 0.04;
    let band = radius * 0.08;
    if (gap < 1.0) {
        gap = 1.0;
    }
    if (band < 2.0) {
        band = 2.0;
    }
    let outer = radius - gap;
    let inner = outer - band;
    if (inner <= 0.0) {
        return;
    }
    let center: Vector2 = { x: circle.x + radius, y: circle.y + radius };
    let line = contrast;
    line.a = 175n;
    let fill = contrast;
    fill.a = 30n;
    <Box
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/practice-window/band"),
            bounds: {
                x: center.x - outer,
                y: center.y - outer,
                width: outer * 2.0,
                height: outer * 2.0
            },
            fill: fill,
            border: line,
            radius: outer
        }}
    />;
    <Box
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/practice-window/band-inner"),
            bounds: {
                x: center.x - inner,
                y: center.y - inner,
                width: inner * 2.0,
                height: inner * 2.0
            },
            fill: StyleTokenColor("accent"),
            border: line,
            radius: inner
        }}
    />;
}

export function PracticeWindowLabelView(
    app: *InnerBreeze,
    circle: Rectangle,
    text: string
): void {
    if (text.count === 0n) {
        return;
    }
    let width = s32(circle.width * 0.78);
    let largest = s32(circle.height * 0.36);
    if (largest > AppScale(NativeText.Text48)) {
        largest = AppScale(NativeText.Text48);
    }
    let smallest = AppScale(11n);
    if (largest < smallest) {
        largest = smallest;
    }
    let font = AppFitFontSize(text, width, largest, smallest);
    <Text
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("inbe/practice-window/label"),
            text: FrameTextHold(&app.ui.frame_text, text),
            bounds: circle,
            size: font,
            class_name: CssClass("circle-ink"),
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}
