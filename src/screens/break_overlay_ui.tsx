import { BreakOverlayNewLockedLabel } from "break_overlay";
import { BreakOverlayNewTimeLabel } from "break_overlay";
import { BreakOverlayNewRects } from "break_overlay";
// Authored UI composition; native application state remains in break_overlay.zi.
import * as NativeText from "kryon/text";
import { InnerBreeze } from "app_types";
import {
    BREAK_OVERLAY_HABITS_CHIP_ID,
    break_overlay_practice_chips,
    break_overlay_remaining_s
} from "break_overlay";
import { BreakReminderLayout } from "break_reminder_layout";
import {
    BreakActive,
    BreakForce,
    BreakFormatDuration,
    BreakPostpone,
    BreakSkip
} from "break_rules";
import { BREAK_DAILY, BREAK_MICRO, BREAK_REST } from "break_types";
import { CurrentApp } from "current_app";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color, DarkenColor, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { TextHeight } from "kryon/text_measure";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppSmallFontSize, AppTextWidth, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import { practice_label } from "practice_registry";
import { AppTextFromCString, FormatArg, FormatTemplate, FrameTextHold } from "text_buffers";

export function break_overlay_draw_bar(
    app: *InnerBreeze,
    x: s32,
    y: s32,
    w: s32,
    h: s32,
    fraction: s32
): void {
    let track = DarkenColor(StyleTokenColor("canvas"), 26n);
    let border = DarkenColor(StyleTokenColor("text"), 60n);
    let fill = StyleTokenColor("progress");
    <Box
        session={app.ui.session}
        props={{
            bounds: { x: float32(x), y: float32(y), width: float32(w), height: float32(h) },
            fill: track,
            border: border
        }}
    />;
    let filled = (w * fraction) / 100n;
    if (filled > 0n) {
        if (filled > w) {
            filled = w;
        }
        <Box
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x + 1n),
                    y: float32(y + 1n),
                    width: float32(filled),
                    height: float32(h - 2n)
                },
                fill: fill
            }}
        />;
    }
}

export function break_overlay_draw_practice_chips(
    app: *InnerBreeze,
    w: s32,
    h: s32
): void {
    let rects = BreakOverlayNewRects();
    let ids: [s32, s32, s32, s32, s32, s32] = [0n, 0n, 0n, 0n, 0n, 0n];
    let chips = break_overlay_practice_chips(
        app,
        w,
        h,
        &rects[0n],
        &ids[0n]
    );
    if (chips <= 0n) {
        return;
    }
    let chip_fill = DarkenColor(StyleTokenColor("canvas"), 18n);
    let chip_border = StyleTokenColor("border");
    {
        let i: s32 = 0n;
        while (i < chips) {
            let r: Rectangle = rects[i];
            <Box
                session={app.ui.session}
                props={{
                    bounds: r,
                    fill: chip_fill,
                    border: chip_border,
                    radius: float32(AppScale(8n))
                }}
            />;
            let label: string =
                ids[i] === BREAK_OVERLAY_HABITS_CHIP_ID
                    ? LocaleText("tab_habits")
                    : practice_label(ids[i]);
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: r,
                    text: label,
                    size: AppSmallFontSize(),
                    align: TextAlign.TextAlignCenter,
                    vertical_align: TextAlign.TextAlignCenter,
                    wrap: Wrap.TextWrapNone
                }}
            />;
            i = i + 1n;
        }
    }
}

export function break_overlay_draw_sized(app: *InnerBreeze, w: s32, h: s32): void {
    if (!NativePresent(app)) {
        return;
    }
    let t = BreakActive(app.breaks);
    if (t < 0n) {
        return;
    }
    let timer = &app.breaks.timers[t];
    let panel_w = (w * 72n) / 100n;
    if (panel_w > AppScale(560n)) {
        panel_w = AppScale(560n);
    }
    if (panel_w < AppScale(280n)) {
        panel_w = AppScale(280n);
    }
    let panel_h = (h * 46n) / 100n;
    if (panel_h > AppScale(420n)) {
        panel_h = AppScale(420n);
    }
    if (panel_h < AppScale(240n)) {
        panel_h = AppScale(240n);
    }
    let panel_x = w / 2n - panel_w / 2n;
    let panel_y = h / 2n - panel_h / 2n;
    let scrim = DarkenColor(DarkenColor(StyleTokenColor("canvas"), 8n), 30n);
    <Box
        session={app.ui.session}
        props={{ bounds: { x: 0.0, y: 0.0, width: float32(w), height: float32(h) }, fill: scrim }}
    />;
    let activity_flash = app.break_input_active !== 0n && (app.breathing.frame / 30n) % 2n === 0n;
    let border: Color = activity_flash
        ? StyleTokenColor("danger")
        : DarkenColor(StyleTokenColor("text"), 62n);
    let fill = DarkenColor(StyleTokenColor("canvas"), 12n);
    <Box
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(panel_x),
                y: float32(panel_y),
                width: float32(panel_w),
                height: float32(panel_h)
            },
            fill: fill,
            border: border
        }}
    />;
    let title_font: s32 = AppScale(NativeText.Text24);
    let body_font: s32 = AppScale(NativeText.Text16);
    let title: string = "";
    let body: string = "";
    if (t === BREAK_REST) {
        title = LocaleText("break_rest_title");
    } else if (t === BREAK_DAILY) {
        title = LocaleText("break_daily_title");
    } else {
        title = LocaleText("break_micro_title");
    }
    if (t === BREAK_REST) {
        body = LocaleText("break_rest_body");
    } else if (t === BREAK_DAILY) {
        body = LocaleText("break_daily_body");
    } else {
        body = LocaleText("break_micro_body");
    }
    let title_bounds: Rectangle = {
        x: float32(panel_x),
        y: float32(panel_y + AppScale(20n)),
        width: float32(panel_w),
        height: 0.0
    };
    let title_props: NativeText.Props = {};
    title_props.bounds = title_bounds;
    title_props.text = title;
    title_props.size = title_font;
    title_props.align = TextAlign.TextAlignCenter;
    title_props.vertical_align = TextAlign.TextAlignCenter;
    title_props.wrap = Wrap.TextWrapAuto;
    title_bounds.height = float32(TextHeight(CurrentApp().ui.session, title_props));
    title_props.bounds = title_bounds;
    <Text session={CurrentApp().ui.session} props={title_props} />;
    let remaining = break_overlay_remaining_s(app, t);
    let reminder_bottom: s32 = s32(title_bounds.y) + s32(title_bounds.height);
    if (timer.duration_s > 0n) {
        let time_text = BreakFormatDuration(remaining);
        let time_label = BreakOverlayNewTimeLabel();
        let time_args: [FormatArg] = [
            {
                text: AppTextFromCString(&time_text.bytes[0n], time_text.count + 1n),
                is_text: true
            }
        ];
        FormatTemplate(
            LocaleText("break_time_remaining"),
            time_args[:],
            time_label[:]
        );
        let remaining_label = FrameTextHold(
            &app.ui.frame_text,
            AppTextFromCString(&time_label[0n], s32(time_label.count))
        );
        let reminder_bounds: Rectangle = {
            x: float32(panel_x + AppScale(24n)),
            y: title_bounds.y + float32(s32(title_bounds.height) + AppScale(4n)),
            width: float32(panel_w - AppScale(48n)),
            height: 0.0
        };
        let reminder_props: NativeText.Props = {};
        reminder_props.bounds = reminder_bounds;
        reminder_props.text = remaining_label;
        reminder_props.size = body_font;
        reminder_props.align = TextAlign.TextAlignCenter;
        reminder_props.vertical_align = TextAlign.TextAlignCenter;
        reminder_props.wrap = Wrap.TextWrapAuto;
        let reminder_layout = BreakReminderLayout(
            reminder_bounds,
            TextHeight(CurrentApp().ui.session, reminder_props),
            MetricsScale()
        );
        reminder_layout.bar.height = float32(AppScale(16n));
        reminder_props.bounds = reminder_layout.text;
        <Text session={CurrentApp().ui.session} props={reminder_props} />;
        let fraction = (timer.idle_s * 100n) / timer.duration_s;
        if (fraction > 100n) {
            fraction = 100n;
        }
        break_overlay_draw_bar(
            app,
            s32(reminder_layout.bar.x),
            s32(reminder_layout.bar.y),
            s32(reminder_layout.bar.width),
            AppScale(16n),
            fraction
        );
        reminder_bottom = s32(reminder_layout.bar.y) + AppScale(16n);
    }
    let body_y: s32 =
        timer.duration_s > 0n
            ? reminder_bottom + AppScale(16n)
            : s32(title_bounds.y) + s32(title_bounds.height) + AppScale(16n);
    let body_w = panel_w - AppScale(48n);
    let body_props: NativeText.Props = {};
    body_props.bounds = {
        x: float32(panel_x + AppScale(24n)),
        y: float32(body_y),
        width: float32(body_w),
        height: 0.0
    };
    body_props.text = body;
    body_props.size = body_font;
    body_props.align = TextAlign.TextAlignCenter;
    body_props.wrap = Wrap.TextWrapAuto;
    let body_h = TextHeight(CurrentApp().ui.session, body_props);
    body_props.bounds.height = float32(body_h);
    <Text
        session={app.ui.session}
        props={{
            bounds: body_props.bounds,
            text: body_props.text,
            size: body_props.size,
            align: body_props.align,
            wrap: body_props.wrap
        }}
    />;
    if (activity_flash) {
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(panel_x),
                    y: float32(panel_y + panel_h - AppScale(100n)),
                    width: float32(panel_w),
                    height: float32(AppScale(26n))
                },
                text: LocaleText("break_stay_idle_note"),
                size: body_font,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone
            }}
        />;
    }
    let button_y = panel_y + panel_h - AppScale(60n);
    let button_h = AppScale(36n);
    let gap = AppScale(12n);
    let button_w = AppScale(120n);
    let labels: [string, string, string] = [
        LocaleText("break_postpone_button"),
        LocaleText("break_skip_button"),
        LocaleText("break_rest_now_button")
    ];
    for (let label_index = s32(0); label_index <= 2n; label_index += s32(1)) {
        let label_w = AppTextWidth(labels[label_index], AppFontSize()) + AppScale(32n);
        if (label_w > button_w) {
            button_w = label_w;
        }
    }
    let count: s32 = 0n;
    if (timer.show_postpone !== 0n) {
        count = count + 1n;
    }
    if (timer.show_skip !== 0n) {
        count = count + 1n;
    }
    if (t === BREAK_MICRO) {
        count = count + 1n;
    }
    let row_w = count * button_w + (count - 1n) * gap;
    let button_x = w / 2n - row_w / 2n;
    let locked = timer.lock_buttons_s > 0n;
    if (timer.show_postpone !== 0n) {
        if (locked) {
            let locked_label = BreakOverlayNewLockedLabel();
            let lock_args: [FormatArg] = [{ number: timer.lock_buttons_s }];
            FormatTemplate(
                LocaleText("break_lock_note"),
                lock_args[:],
                locked_label[:]
            );
            let lock_text = FrameTextHold(
                &app.ui.frame_text,
                AppTextFromCString(&locked_label[0n], s32(locked_label.count))
            );
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(button_x),
                        y: float32(button_y),
                        width: float32(button_w),
                        height: float32(button_h)
                    },
                    text: lock_text,
                    wrap: Wrap.TextWrapNone,
                    align: TextAlign.TextAlignCenter,
                    vertical_align: TextAlign.TextAlignCenter
                }}
            />;
        } else {
            if (
                (
                    <Button
                        session={CurrentApp().ui.session}
                        props={{
                            id: 4101n,
                            label: LocaleText("break_postpone_button"),
                            bounds: {
                                x: float32(button_x),
                                y: float32(button_y),
                                width: float32(button_w),
                                height: float32(button_h)
                            },
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft
                        }}
                    />
                )
            ) {
                app.breaks = BreakPostpone(app.breaks, t);
                return;
            }
        }
        button_x = button_x + (button_w + gap);
    }
    if (timer.show_skip !== 0n) {
        if (!locked) {
            if (
                (
                    <Button
                        session={CurrentApp().ui.session}
                        props={{
                            id: 4102n,
                            label: LocaleText("break_skip_button"),
                            bounds: {
                                x: float32(button_x),
                                y: float32(button_y),
                                width: float32(button_w),
                                height: float32(button_h)
                            },
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft
                        }}
                    />
                )
            ) {
                app.breaks = BreakSkip(app.breaks, t);
                return;
            }
        }
        button_x = button_x + (button_w + gap);
    }
    if (t === BREAK_MICRO) {
        if (
            (
                <Button
                    session={CurrentApp().ui.session}
                    props={{
                        id: 4103n,
                        label: LocaleText("break_rest_now_button"),
                        bounds: {
                            x: float32(button_x),
                            y: float32(button_y),
                            width: float32(button_w),
                            height: float32(button_h)
                        },
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            app.breaks = BreakForce(app.breaks, BREAK_REST);
            return;
        }
    }
    break_overlay_draw_practice_chips(app, w, h);
}
