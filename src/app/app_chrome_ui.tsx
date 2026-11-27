import { AppChromeNewOptions } from "app_chrome";
// Authored UI composition; native application state remains in app_chrome.zi.
import * as NativeButton from "kryon/button";
import * as NativeTitleBar from "kryon/title_bar";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Button } from "kryon/tsx/button";
import { TitleBar } from "kryon/tsx/title_bar";
import { AppScale } from "metrics";
import { NativePresent } from "native_flags";

export function app_draw_close_title_barView(
    app: NativeRef<InnerBreeze>,
    title: string,
    close_label: string,
    height: s32
): s32 {
    if (!NativePresent(app) || app.ui.view_width <= 0n || height <= 0n) {
        return 0n;
    }
    let button_size = AppScale(22n);
    let padding = AppScale(11n);
    let button_total = button_size + padding * 2n;
    let x = app.ui.view_width - button_total - AppScale(8n);
    let y = (height - button_total) / 2n;
    if (y < 0n) {
        y = 0n;
    }
    let options = AppChromeNewOptions();
    let bar: NativeTitleBar.Props = {};
    bar.title = title;
    bar.height = height;
    bar.bounds = { x: 0.0, y: 0.0, width: float32(app.ui.view_width), height: float32(height) };
    <TitleBar session={app.ui.session} props={bar} options={nativeSlice(options, 0n, 0n)} />;
    let close: NativeButton.Props = {};
    close.id = 9101n;
    close.label = close_label;
    close.bounds = {
        x: float32(x),
        y: float32(y),
        width: float32(button_total),
        height: float32(button_total)
    };
    close.image.asset_path = "icons/ui.webp";
    close.image.alt_text = close_label;
    close.image.source = { x: 448.0, y: 384.0, width: 64.0, height: 64.0 };
    close.icon_only = true;
    close.circle = true;
    close.tone = ButtonTone.ButtonToneNeutral;
    close.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    if (app.modal.active === 0n && Button({ session: app.ui.session, props: close })) {
        return 1n;
    }
    return 0n;
}
