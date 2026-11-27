import { AppBreaksNewLine } from "app_breaks";
// Authored UI composition; native application state remains in app_breaks.zi.
import * as NativeText from "kryon/text";
import * as NativeToast from "kryon/toast";
import * as State_app_breaks from "app_breaks";
import { break_hud_label, break_hud_time_reserve } from "app_breaks";
import { InnerBreeze } from "app_types";
import { BreakReminderLayout, BreakReminderLayoutResult } from "break_reminder_layout";
import { BreakFormatDuration, BreakNextDueSeconds } from "break_rules";
import { BREAK_TYPE_COUNT, BreakStateBreaking, BreakStateRunning, BreakTimer } from "break_types";
import { CurrentApp } from "current_app";
import { GetDPIScale } from "dpi_state";
import { HostSeconds } from "host_clock";
import { Color, DarkenColor, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { Session, SessionValid } from "kryon/session";
import { TextAlign } from "kryon/text_align";
import { TextHeight } from "kryon/text_measure";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import { Toast } from "kryon/tsx/toast";
import { LocaleText } from "locale";
import { AppScale, AppTextWidth } from "metrics";
import { NativePresent } from "native_flags";
import { AppNotificationToastSeconds } from "notification_presentation";
import { AppCopyText, AppTextFromCString } from "text_buffers";

export function app_breaks_draw_toastView(
    app: *InnerBreeze,
    viewport: Rectangle
): void {
    if (!NativePresent(app) || !SessionValid(app.ui.session)) {
        return;
    }
    if (
        State_app_breaks.break_toast_state.message.count === 0n &&
        State_app_breaks.break_toast_request.count === 0n
    ) {
        return;
    }
    let props: NativeToast.Props = {};
    props.key = u64(0x627265616b746f61n);
    props.viewport = viewport;
    props.state = State_app_breaks.break_toast_state;
    props.message = State_app_breaks.break_toast_request;
    props.seconds = AppNotificationToastSeconds;
    props.now_seconds = HostSeconds();
    props.scale = GetDPIScale();
    State_app_breaks.break_toast_state = (<Toast session={app.ui.session} props={props} />).state;
    State_app_breaks.break_toast_request = "";
}

export function break_hud_draw_timeView(
    session: Session,
    text: string,
    right_x: s32,
    layout: BreakReminderLayoutResult,
    width: s32,
    font: s32
): void {
    let props: NativeText.Props = {};
    props.bounds = {
        x: float32(right_x - AppTextWidth(text, font)),
        y: layout.text.y,
        width: float32(width),
        height: layout.text.height
    };
    props.text = text;
    props.size = font;
    props.vertical_align = TextAlign.TextAlignCenter;
    props.wrap = Wrap.TextWrapNone;
    <Text session={session} props={props} />;
}

export function app_breaks_hud_drawView(
    app: *InnerBreeze,
    hud_w: s32,
    hud_h: s32,
    row_h: s32,
    pad: s32,
    scale: float32
): void {
    let track = DarkenColor(StyleTokenColor("canvas"), 18n);
    let border: Color = DarkenColor(StyleTokenColor("text"), 62n);
    let fill = StyleTokenColor("progress");
    let overdue = StyleTokenColor("danger");
    let idle_col = StyleTokenColor("link");
    <Box
        session={app.ui.session}
        props={{
            bounds: { x: 0.0, y: 0.0, width: float32(hud_w), height: float32(hud_h) },
            fill: track,
            border: border
        }}
    />;
    let row: s32 = 0n;
    {
        let t: s32 = 0n;
        while (t < BREAK_TYPE_COUNT) {
            let timer: *BreakTimer = &app.breaks.timers[t];
            if (timer.enabled === 0n) {
                t = t + 1n;
                continue;
            }
            let row_y = pad + row_h * row;
            row = row + 1n;
            let bar_x = pad;
            let bar_w = hud_w - pad * 2n;
            let time_x = hud_w - pad;
            let next = BreakNextDueSeconds(app.breaks, t);
            let font: s32 = AppScale(NativeText.Text12);
            let time_reserve = break_hud_time_reserve(timer);
            let label_width = bar_w - time_reserve - AppScale(8n);
            if (label_width < 1n) {
                label_width = 1n;
            }
            let label_props: NativeText.Props = {};
            label_props.bounds = {
                x: float32(bar_x),
                y: float32(row_y),
                width: float32(label_width),
                height: 0.0
            };
            label_props.text = break_hud_label(t);
            label_props.size = font;
            label_props.wrap = Wrap.TextWrapAuto;
            let label_height = TextHeight(app.ui.session, label_props);
            if (label_height <= 0n) {
                label_height = font;
            }
            let row_layout = BreakReminderLayout(label_props.bounds, label_height, scale);
            label_props.bounds = row_layout.text;
            <Text session={CurrentApp().ui.session} props={label_props} />;
            if (next < 0n) {
                let line_text = "off";
                break_hud_draw_timeView(
                    app.ui.session,
                    line_text,
                    time_x,
                    row_layout,
                    time_reserve,
                    font
                );
            } else if (timer.state === BreakStateBreaking) {
                let left: s32 = timer.duration_s - timer.idle_s;
                if (left < 0n) {
                    left = 0n;
                }
                let line = BreakFormatDuration(left);
                let line_text = AppTextFromCString(&line.bytes[0n], 16n);
                break_hud_draw_timeView(
                    app.ui.session,
                    line_text,
                    time_x,
                    row_layout,
                    time_reserve,
                    font
                );
                if (timer.duration_s > 0n) {
                    let fraction = (timer.idle_s * (bar_w - 2n)) / timer.duration_s;
                    if (fraction > bar_w - 2n) {
                        fraction = bar_w - 2n;
                    }
                    let bar_bounds: Rectangle = {
                        x: row_layout.bar.x,
                        y: row_layout.bar.y,
                        width: float32(bar_w),
                        height: row_layout.bar.height
                    };
                    <Box
                        session={app.ui.session}
                        props={{
                            bounds: bar_bounds,
                            fill: DarkenColor(StyleTokenColor("canvas"), 30n),
                            border: DarkenColor(StyleTokenColor("canvas"), 30n)
                        }}
                    />;
                    if (fraction > 0n) {
                        <Box
                            session={app.ui.session}
                            props={{
                                bounds: {
                                    x: bar_bounds.x + 1.0,
                                    y: bar_bounds.y,
                                    width: float32(fraction),
                                    height: bar_bounds.height
                                },
                                fill: fill,
                                border: fill
                            }}
                        />;
                    }
                }
            } else {
                let line = AppBreaksNewLine();
                if (next === 0n) {
                    AppCopyText(
                        LocaleText("settings_breaks_due_now"),
                        line[:]
                    );
                } else {
                    let duration = BreakFormatDuration(next);
                    AppCopyText(
                        AppTextFromCString(&duration.bytes[0n], 16n),
                        line[:]
                    );
                }
                let line_text = AppTextFromCString(&line[0n], 64n);
                break_hud_draw_timeView(
                    app.ui.session,
                    line_text,
                    time_x,
                    row_layout,
                    time_reserve,
                    font
                );
                if (timer.limit_s > 0n) {
                    let fraction = (timer.active_s * (bar_w - 2n)) / timer.limit_s;
                    if (fraction > bar_w - 2n) {
                        fraction = bar_w - 2n;
                    }
                    let bar_bounds: Rectangle = {
                        x: row_layout.bar.x,
                        y: row_layout.bar.y,
                        width: float32(bar_w),
                        height: row_layout.bar.height
                    };
                    <Box
                        session={app.ui.session}
                        props={{
                            bounds: bar_bounds,
                            fill: DarkenColor(StyleTokenColor("canvas"), 30n),
                            border: DarkenColor(StyleTokenColor("canvas"), 30n)
                        }}
                    />;
                    if (fraction > 0n) {
                        let bar_color = next === 0n ? overdue : fill;
                        <Box
                            session={app.ui.session}
                            props={{
                                bounds: {
                                    x: bar_bounds.x + 1.0,
                                    y: bar_bounds.y,
                                    width: float32(fraction),
                                    height: bar_bounds.height
                                },
                                fill: bar_color,
                                border: bar_color
                            }}
                        />;
                    }
                    if (
                        timer.state === BreakStateRunning &&
                        timer.duration_s > 0n &&
                        timer.idle_s > 0n &&
                        timer.idle_latched === 0n
                    ) {
                        let tip = ((bar_w - 2n - fraction) * timer.idle_s) / timer.duration_s;
                        if (tip > 0n) {
                            <Box
                                session={app.ui.session}
                                props={{
                                    bounds: {
                                        x: bar_bounds.x + 1.0 + float32(fraction),
                                        y: bar_bounds.y,
                                        width: float32(tip),
                                        height: bar_bounds.height
                                    },
                                    fill: idle_col,
                                    border: idle_col
                                }}
                            />;
                        }
                    }
                }
            }
            t = t + 1n;
        }
    }
}
