// Authored UI composition; native application state remains in whm_view.zi.
import * as NativeShape from "kryon/shape";
import * as NativeText from "kryon/text";
import * as State_whm_view from "whm_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Vector2 } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import { PRACTICE_WHM_BREATH } from "practice_types";
import { Contrast, Scale, ThinRing, WHM_PI, Width, WithAlpha } from "whm_view";
import { Cos, Sin } from "std/math";

export function ProgressCircle(): void {
    let gap = Scale(5n);
    let band_width = Scale(10n);
    if (band_width > State_whm_view.whm.rmin - gap - 4n) {
        band_width = State_whm_view.whm.rmin - gap - 4n;
    }
    if (band_width < 1n) {
        band_width = 1n;
    }
    let thickness = State_whm_view.whm.ticks <= 40n ? Scale(3n) : Scale(2n);
    if (thickness < 1n) {
        thickness = 1n;
    }
    let outer = State_whm_view.whm.radius - float32(gap);
    let inner = outer - float32(band_width);
    let center: Vector2 = {
        x: float32(State_whm_view.whm.center_x),
        y: float32(State_whm_view.whm.center_y)
    };
    NativeShape.Circle(State_whm_view.whm.session, {
        center: center,
        radius: State_whm_view.whm.radius,
        fill: State_whm_view.whm.accent_color
    });
    if (outer <= inner) {
        return;
    }
    let contrast = Contrast(State_whm_view.whm.accent_color);
    let band = WithAlpha(contrast, 72n);
    NativeShape.Ring(State_whm_view.whm.session, {
        center: center,
        inner_radius: inner,
        outer_radius: outer,
        start_angle: 0.0,
        end_angle: 360.0,
        color: WithAlpha(contrast, 30n)
    });
    let progress = State_whm_view.whm.progress;
    if (State_whm_view.whm.countdown) {
        if (progress < 1.0) {
            NativeShape.Ring(State_whm_view.whm.session, {
                center: center,
                inner_radius: inner,
                outer_radius: outer,
                start_angle: -450.0,
                end_angle: -90.0 - 360.0 * progress,
                color: band
            });
        }
    } else if (progress > 0.0) {
        NativeShape.Ring(State_whm_view.whm.session, {
            center: center,
            inner_radius: inner,
            outer_radius: outer,
            start_angle: -90.0,
            end_angle: -90.0 + 360.0 * progress,
            color: band
        });
    }
    let ring = WithAlpha(contrast, 175n);
    ThinRing(center, inner, ring);
    ThinRing(center, outer, ring);
    let ticks = State_whm_view.whm.ticks;
    if (ticks < 1n) {
        ticks = 1n;
    }
    for (let index = s32(0n); index < ticks; index += s32(1)) {
        let share = float32(index) / float32(ticks);
        let direction: float32 = State_whm_view.whm.countdown ? -1.0 : 1.0;
        let angle = -WHM_PI * 0.5 + float64(direction * share) * 2.0 * WHM_PI;
        if (State_whm_view.whm.countdown && index === 0n) {
            share = 1.0;
        }
        let done = share <= progress + 0.0001;
        if (State_whm_view.whm.countdown) {
            done = share > progress + 0.0001;
        }
        let c = float32(Cos(angle));
        let s = float32(Sin(angle));
        <Shape
            session={State_whm_view.whm.session}
            props={{
                start: { x: center.x + c * inner, y: center.y + s * inner },
                end: { x: center.x + c * outer, y: center.y + s * outer },
                thickness: float32(thickness),
                color: WithAlpha(contrast, done ? 235n : 96n)
            }}
        />;
    }
}

export function Count(): void {
    let radius = s32(State_whm_view.whm.radius);
    let font: s32 = NativeText.Text48;
    while (
        font > NativeText.Text24 &&
        Width(State_whm_view.whm.count, font) > s32(float32(radius) * 1.12)
    ) {
        font = font - 1n;
    }
    <Text
        session={State_whm_view.whm.session}
        props={{
            text: State_whm_view.whm.count,
            bounds: {
                x: float32(State_whm_view.whm.center_x - radius),
                y: float32(State_whm_view.whm.center_y - radius),
                width: float32(radius * 2n),
                height: float32(radius * 2n)
            },
            size: font,
            class_name: State_whm_view.whm.ink_class,
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}

export function Hold(): void {
    if (State_whm_view.whm.double_tap) {
        let width = Width(State_whm_view.whm.hint, State_whm_view.whm.font);
        let y = State_whm_view.whm.center_y + State_whm_view.whm.rmax + Scale(12n);
        if (y > State_whm_view.whm.breath_max_y) {
            y = State_whm_view.whm.breath_max_y;
        }
        <Text
            session={State_whm_view.whm.session}
            props={{
                text: State_whm_view.whm.hint,
                bounds: {
                    x: float32(State_whm_view.whm.center_x - width / 2n),
                    y: float32(y),
                    width: 0n,
                    height: 0n
                },
                wrap: Wrap.TextWrapNone
            }}
        />;
        return;
    }
    let width = Width(State_whm_view.whm.breath_label, NativeText.Text16) + Scale(72n);
    if (width < Scale(184n)) {
        width = Scale(184n);
    }
    if (width > State_whm_view.whm.view_width - Scale(24n)) {
        width = State_whm_view.whm.view_width - Scale(24n);
    }
    let y = State_whm_view.whm.center_y + State_whm_view.whm.rmax - Scale(42n);
    if (y > State_whm_view.whm.breath_max_y) {
        y = State_whm_view.whm.breath_max_y;
    }
    if (
        Button({
            session: State_whm_view.whm.session,
            props: {
                bounds: {
                    x: float32(State_whm_view.whm.center_x - width / 2n),
                    y: float32(y),
                    width: float32(width),
                    height: float32(NativeText.Text16 + Scale(28n))
                },
                label: State_whm_view.whm.breath_label,
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        })
    ) {
        State_whm_view.whm.action = PRACTICE_WHM_BREATH;
    }
}
