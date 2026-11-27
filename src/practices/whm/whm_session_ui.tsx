import { WhmSessionNewRow } from "whm_session";
import { WhmSessionNewSecondsText } from "whm_session";
import { WhmSessionNewLines } from "whm_session";
import { WhmSessionNewRoundTimes } from "whm_session";
import { CurrentApp } from "current_app";
import { AppControlTextY, GetPageSidePadding } from "metrics";
import { MaxRounds } from "types";
import { AppTextFromCString } from "text_buffers";
import { StyleTokenColor } from "kryon/drawing_props";
import { session_discard_saved_results, session_ensure_results_saved } from "whm_session";
// Authored UI composition; native application state remains in whm_session.zi.
import * as NativeText from "kryon/text";
import { practice_label } from "app_notifications";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { DarkenColor } from "kryon/drawing_props";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    AppFontSize,
    AppScale,
    AppSmallFontSize,
    AppTextLineHeight,
    AppTextWidth,
    AppTitleFontSize,
    GetCenteredColumn
} from "metrics";
import { AppCopyText, AppFormatS32, FormatTwoNumberTemplate, FrameTextHold } from "text_buffers";
import { FormatLocaleCount, collect_result_rounds, whm_exit_to_start } from "whm_session";

export function session_draw_start_previewView(
    app: NativeRef<InnerBreeze>,
    center_x: s32,
    center_y: s32
): s32 {
    let play_text: string = LocaleText("play_button");
    let practice_text: string = practice_label(app.exercise_type);
    let practice_font: s32 = AppFontSize();
    let practice_w: s32 = s32(0);
    let practice_y: s32 = s32(0);
    let radius: s32 = AppScale(44n);
    let pointer_x = app.ui.mouse_x - center_x;
    let pointer_y = app.ui.mouse_y - center_y;
    let hovered =
        app.ui.pointer_active && pointer_x * pointer_x + pointer_y * pointer_y <= radius * radius;
    app.play_circle_hover = hovered ? 1n : 0n;
    let target_scale: float32 = hovered ? float32(1.08) : float32(1.0);
    app.play_circle_scale =
        app.play_circle_scale + (target_scale - app.play_circle_scale) * float32(0.2);
    if (app.play_circle_scale < float32(1.0)) {
        app.play_circle_scale = float32(1.0);
    }
    if (app.play_circle_scale > float32(1.08)) {
        app.play_circle_scale = float32(1.08);
    }
    let scaled_radius: s32 = s32(float32(radius) * app.play_circle_scale);
    practice_w = AppTextWidth(practice_text, practice_font);
    if (practice_w > app.ui.view_width - AppScale(48n)) {
        practice_font = AppSmallFontSize();
    }
    practice_w = AppTextWidth(practice_text, practice_font);
    practice_y = center_y - scaled_radius - AppScale(42n);
    if (practice_y < AppScale(8n)) {
        practice_y = AppScale(8n);
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(center_x - practice_w / 2n),
                y: float32(
                    AppControlTextY(practice_text, practice_y, AppScale(32n), practice_font)
                ),
                width: 0.0,
                height: 0.0
            },
            text: practice_text,
            wrap: Wrap.TextWrapNone
        }}
    />;
    const clicked = Button({
        session: app.ui.session,
        props: {
            bounds: {
                x: float32(center_x - scaled_radius),
                y: float32(center_y - scaled_radius),
                width: float32(scaled_radius * 2n),
                height: float32(scaled_radius * 2n)
            },
            label: play_text,
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
            circle: true
        }
    });
    if (clicked) {
        return 1n;
    }
    return 0n;
}

export function session_draw_results_screenView(
    app: NativeRef<InnerBreeze>,
    center_x: s32,
    center_y: s32,
    hover: NativeRef<s32>
): void {
    let box_x: s32 = s32(0);
    let box_y: s32 = AppScale(78n);
    let box_w: s32 = s32(0);
    let row_y: s32 = AppScale(215n);
    let row_h: s32 = AppScale(32n);
    let total: s32 = s32(0n);
    let best: s32 = s32(-1n);
    let round_times = WhmSessionNewRoundTimes();
    let rounds: s32 = collect_result_rounds(app, nativeRef(nativeAt(round_times, 0n)), MaxRounds);
    let action_y: s32 = app.ui.view_height - AppScale(40n);
    let title_font: s32 = s32(0);
    let title_w: s32 = s32(0);
    center_y;
    if (rounds <= 0n) {
        whm_exit_to_start(app);
        return;
    }
    let responsive_max_w: s32 = s32(float32(app.ui.view_width) * float32(0.96));
    let min_content_w: s32 = AppScale(320n);
    if (responsive_max_w < min_content_w) {
        responsive_max_w = min_content_w;
    }
    GetCenteredColumn(responsive_max_w, GetPageSidePadding(), nativeRef(box_x), nativeRef(box_w));
    title_font = AppTitleFontSize(LocaleText("results_title"), app.ui.view_width - AppScale(48n));
    title_w = AppTextWidth(LocaleText("results_title"), title_font);
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(center_x - title_w / 2n),
                y: float32(AppScale(34n)),
                width: 0n,
                height: 0n
            },
            text: LocaleText("results_title"),
            wrap: Wrap.TextWrapNone
        }}
    />;
    {
        let i: s32 = s32(0n);
        while (i < rounds) {
            let seconds: s32 = nativeAt(round_times, i);
            total = total + seconds;
            if (best < 0n || seconds > best) {
                best = seconds;
            }
            i = i + 1n;
        }
    }
    if (best < 0n) {
        best = 0n;
    }
    {
        let lines = WhmSessionNewLines();
        let summary_font: s32 = NativeText.Text16;
        FormatLocaleCount(nativeSlice(nativeAt(lines, 0n)), "results_rounds", rounds);
        FormatLocaleCount(nativeSlice(nativeAt(lines, 1n)), "results_best", best);
        FormatLocaleCount(
            nativeSlice(nativeAt(lines, 2n)),
            "results_avg",
            rounds > 0n ? total / rounds : 0n
        );
        if (
            app.ui.view_width < 420n &&
            AppTextWidth(
                AppTextFromCString(nativeRef(nativeAt(nativeAt(lines, 2n), 0n)), 64n),
                summary_font
            ) >
                box_w - AppScale(20n)
        ) {
            let seconds_text = WhmSessionNewSecondsText();
            AppFormatS32(rounds > 0n ? s32(total / rounds) : 0n, nativeSlice(seconds_text));
            AppCopyText(
                AppTextFromCString(nativeRef(nativeAt(seconds_text, 0n)), 16n),
                nativeSlice(nativeAt(lines, 2n))
            );
        }
        <Box
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(box_x),
                    y: float32(box_y),
                    width: float32(box_w),
                    height: float32(AppScale(29n) * 3n)
                },
                fill: DarkenColor(StyleTokenColor("canvas"), 6n)
            }}
        />;
        {
            let i: s32 = s32(0n);
            while (i < 3n) {
                let info_y = box_y + i * AppScale(29n);
                if (i > 0n) {
                    <Shape
                        session={CurrentApp().ui.session}
                        props={{
                            start: { x: float32(box_x), y: float32(info_y) },
                            end: { x: float32(box_x + box_w), y: float32(info_y) },
                            color: DarkenColor(StyleTokenColor("canvas"), 30n)
                        }}
                    />;
                }
                <Text
                    session={CurrentApp().ui.session}
                    props={{
                        bounds: {
                            x: float32(box_x + AppScale(10n)),
                            y: float32(info_y),
                            width: float32(box_w - AppScale(20n)),
                            height: float32(AppScale(29n))
                        },
                        text: FrameTextHold(
                            nativeRef(app.ui.frame_text),
                            AppTextFromCString(nativeRef(nativeAt(nativeAt(lines, i), 0n)), 64n)
                        ),
                        wrap: Wrap.TextWrapNone
                    }}
                />;
                i = i + 1n;
            }
        }
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(box_x),
                y: float32(AppScale(181n)),
                width: float32(box_w),
                height: float32(AppScale(28n))
            },
            text: LocaleText("round_times_title"),
            wrap: Wrap.TextWrapNone
        }}
    />;
    {
        let i: s32 = s32(0n);
        while (i < rounds) {
            let row = WhmSessionNewRow();
            let row_font: s32 = AppFontSize();
            FormatTwoNumberTemplate(
                LocaleText("round_result_label"),
                i + 1n,
                nativeAt(round_times, i),
                nativeSlice(row)
            );
            <Box
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(box_x),
                        y: float32(row_y - 1n),
                        width: float32(box_w),
                        height: float32(row_h)
                    },
                    fill: DarkenColor(StyleTokenColor("canvas"), 4n)
                }}
            />;
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(box_x + AppScale(10n)),
                        y: float32(row_y - 1n),
                        width: float32(box_w - AppScale(20n)),
                        height: float32(row_h)
                    },
                    text: FrameTextHold(
                        nativeRef(app.ui.frame_text),
                        AppTextFromCString(nativeRef(nativeAt(row, 0n)), 48n)
                    ),
                    wrap: Wrap.TextWrapNone
                }}
            />;
            row_y = row_y + row_h;
            i = i + 1n;
        }
    }
    let discard_label = LocaleText("discard_button");
    let save_label = LocaleText("save_results_button");
    let discard_w = AppTextWidth(discard_label, AppFontSize()) + AppScale(16n);
    let save_w = AppTextWidth(save_label, AppFontSize()) + AppScale(16n);
    let button_h = AppTextLineHeight(AppFontSize()) + AppScale(8n);
    if (discard_w < AppScale(34n)) {
        discard_w = AppScale(34n);
    }
    if (save_w < AppScale(34n)) {
        save_w = AppScale(34n);
    }
    if (button_h < AppScale(34n)) {
        button_h = AppScale(34n);
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                label: discard_label,
                bounds: {
                    x: float32(center_x - box_w / 4n - discard_w / 2n),
                    y: float32(action_y),
                    width: float32(discard_w),
                    height: float32(button_h)
                },
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        session_discard_saved_results(app);
        whm_exit_to_start(app);
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                label: save_label,
                bounds: {
                    x: float32(center_x + box_w / 4n - save_w / 2n),
                    y: float32(action_y),
                    width: float32(save_w),
                    height: float32(button_h)
                },
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        if (session_ensure_results_saved(app) !== 0n) {
            whm_exit_to_start(app);
        }
    }
    hover;
}
