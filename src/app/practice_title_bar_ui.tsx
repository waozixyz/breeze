import { PracticeTitleBarNewOptions } from "practice_title_bar";
// Authored UI composition; native application state remains in practice_title_bar.zi.
import * as NativeButton from "kryon/button";
import * as NativeText from "kryon/text";
import * as NativeTitleBar from "kryon/title_bar";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { SessionValid } from "kryon/session";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppTextLineHeight, AppTextWidth } from "metrics";
import { AppMiniMode } from "mini_mode";
import { AppMiniModeExpand } from "mini_mode_expand";
import { AppMiniExpandButton } from "mini_mode_expand_ui";
import { NativePresent } from "native_flags";
import { PracticeTitleBarHeight } from "practice_title_bar";
import { app_is_session_screen } from "session_screen";

export function PracticeTitleBarView(
    app: NativeRef<InnerBreeze>,
    title: string,
    height: s32
): boolean {
    if (!NativePresent(app) || app.ui.view_width <= 0n || !SessionValid(app.ui.session)) {
        return false;
    }
    if (height < PracticeTitleBarHeight()) {
        height = PracticeTitleBarHeight();
    }
    let view_width = app.ui.view_width;
    let button_size = AppScale(24n);
    let padding = AppScale(10n);
    let button_total = button_size + padding * 2n;
    let close_x = view_width - button_total - AppScale(12n);
    let close_y = (height - button_total) / 2n;
    if (close_y < 0n) {
        close_y = 0n;
    }
    let expand_x = close_x;
    if (AppMiniMode()) {
        close_x = close_x - (button_total + AppScale(4n));
    }
    let minimizable =
        !AppMiniMode() && app.host_feature === 0n && app_is_session_screen(app.breathing.screen);
    let minimize_x = close_x - button_total - AppScale(4n);
    let left_button_x = minimizable ? minimize_x : close_x;
    let side_reserved = view_width - left_button_x + AppScale(8n);
    let title_x = AppScale(112n);
    let title_width = view_width - title_x - side_reserved;
    if (title_width < 0n) {
        title_width = 0n;
    }
    let max_text_width = title_width - AppScale(24n);
    if (max_text_width < 0n) {
        max_text_width = 0n;
    }
    let font = AppScale(32n);
    let title_text_width = AppTextWidth(title, font);
    while (font > AppFontSize() && title_text_width > max_text_width) {
        font = font - 1n;
        title_text_width = AppTextWidth(title, font);
    }
    if (title_text_width > max_text_width) {
        title_text_width = max_text_width;
    }
    let options = PracticeTitleBarNewOptions();
    let bar: NativeTitleBar.Props = {};
    bar.height = height;
    bar.bounds = { x: 0.0, y: 0.0, width: float32(view_width), height: float32(height) };
    <TitleBar session={app.ui.session} props={bar} options={nativeSlice(options, 0n, 0n)} />;
    let text_props: NativeText.Props = {};
    text_props.text = title;
    text_props.size = font;
    text_props.wrap = Wrap.TextWrapNone;
    text_props.bounds = {
        x: float32(title_x + (title_width - title_text_width) / 2n),
        y: float32((height - AppTextLineHeight(font)) / 2n),
        width: float32(title_text_width),
        height: float32(AppTextLineHeight(font))
    };
    <Text session={app.ui.session} props={text_props} />;
    if (app.modal.active !== 0n) {
        return false;
    }
    let close: NativeButton.Props = {};
    close.id = 9102n;
    close.bounds = {
        x: float32(close_x),
        y: float32(close_y),
        width: float32(button_total),
        height: float32(button_total)
    };
    close.label = LocaleText("close_button");
    close.image.asset_path = "icons/ui.webp";
    close.image.alt_text = close.label;
    close.image.source = { x: 448.0, y: 384.0, width: 64.0, height: 64.0 };
    close.icon_only = true;
    close.circle = true;
    close.tone = ButtonTone.ButtonToneNeutral;
    close.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    if (minimizable) {
        let minimize: NativeButton.Props = {};
        minimize.id = 9103n;
        minimize.bounds = {
            x: float32(minimize_x),
            y: float32(close_y),
            width: float32(button_total),
            height: float32(button_total)
        };
        minimize.label = LocaleText("session_minimize_button");
        minimize.icon_shape = "S1.7rr:M4 6H20V18H4ZM12 12H17V16H12Z";
        minimize.icon_only = true;
        minimize.circle = true;
        minimize.tone = ButtonTone.ButtonToneNeutral;
        minimize.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
        if (Button({ session: app.ui.session, props: minimize })) {
            app.session_window.minimize_requested = true;
        }
    }
    if (
        AppMiniMode() &&
        AppMiniExpandButton(app, {
            x: float32(expand_x),
            y: float32(close_y),
            width: float32(button_total),
            height: float32(button_total)
        })
    ) {
        AppMiniModeExpand(app);
    }
    return Button({ session: app.ui.session, props: close });
}
