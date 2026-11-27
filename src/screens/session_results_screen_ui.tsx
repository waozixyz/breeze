import { SessionResultsScreenNewLines } from "session_results_screen";
// Authored UI composition; native application state remains in session_results_screen.zi.
import * as NativeLayout from "kryon/layout";
import { practice_label } from "app_notifications";
import { InnerBreeze, SessionResult } from "app_types";
import { CssClass } from "css/Css";
import { StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFitFontSize, AppScale } from "metrics";
import { session_result_window_lines } from "session_results_screen";
import { AppTextFromCString, FrameTextHold } from "text_buffers";

export function practice_draw_results_window(
    app: NativeRef<InnerBreeze>,
    bounds: Rectangle,
    result: NativeRef<SessionResult>
): void {
    let session = app.ui.session;
    let lines = SessionResultsScreenNewLines();
    let count = session_result_window_lines(
        result,
        nativeSlice(nativeAt(lines, 0n)),
        nativeSlice(nativeAt(lines, 1n))
    );
    let padding = float32(AppScale(12n));
    let width = bounds.width - padding * 2.0;
    let heading_height = float32(AppScale(32n));
    let rule_height = float32(AppScale(3n));
    let name_height = float32(AppScale(22n));
    let line_height = float32(AppScale(24n));
    let gap = float32(AppScale(10n));
    let total =
        heading_height + gap + rule_height + gap + name_height + gap + float32(count) * line_height;
    let y = bounds.y + (bounds.height - total) * 0.5;
    let x = bounds.x + padding;
    let heading = LocaleText("session_window_finished");
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/picture-window/results/heading"),
            bounds: { x: x, y: y, width: width, height: heading_height },
            text: heading,
            size: AppFitFontSize(heading, s32(width), AppScale(24n), AppScale(14n)),
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    y = y + (heading_height + gap);
    let rule_width = float32(AppScale(40n));
    <Box
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/picture-window/results/rule"),
            bounds: {
                x: bounds.x + (bounds.width - rule_width) * 0.5,
                y: y,
                width: rule_width,
                height: rule_height
            },
            fill: StyleTokenColor("accent"),
            radius: rule_height * 0.5
        }}
    />;
    y = y + (rule_height + gap);
    let name = practice_label(result.activity);
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/picture-window/results/name"),
            bounds: { x: x, y: y, width: width, height: name_height },
            text: name,
            size: AppFitFontSize(name, s32(width), AppScale(15n), AppScale(11n)),
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            class_name: CssClass("launcher-muted")
        }}
    />;
    y = y + (name_height + gap);
    let keys: [u64, u64] = [
        NativeLayout.KeyHash("inbe/picture-window/results/line-1"),
        NativeLayout.KeyHash("inbe/picture-window/results/line-2")
    ];
    let index: s32 = s32(0n);
    while (index < count) {
        let line = FrameTextHold(
            nativeRef(app.ui.frame_text),
            AppTextFromCString(nativeRef(nativeAt(nativeAt(lines, index), 0n)), 80n)
        );
        <Text
            session={session}
            props={{
                key: nativeAt(keys, index),
                bounds: { x: x, y: y, width: width, height: line_height },
                text: line,
                size: AppFitFontSize(line, s32(width), AppScale(17n), AppScale(11n)),
                wrap: Wrap.TextWrapNone,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter
            }}
        />;
        y = y + line_height;
        index = index + 1n;
    }
}
