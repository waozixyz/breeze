// Authored UI composition; native application state remains in mini_mode_expand.zi.
import * as NativeButton from "kryon/button";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { IconType, ImageForIcon } from "kryon/icon";
import { Button } from "kryon/tsx/button";
import { LocaleText } from "locale";

export function AppMiniExpandButton(app: NativeRef<InnerBreeze>, bounds: Rectangle): boolean {
    let label = LocaleText("mini_open_full_app");
    let icon = ImageForIcon(s32(s32(IconType.IconExpand)), bounds, label);
    let button: NativeButton.Props = {};
    button.id = 9103n;
    button.label = label;
    button.bounds = bounds;
    button.image.asset_path = icon.asset_path;
    button.image.alt_text = label;
    button.image.source = icon.source;
    button.icon_only = true;
    button.circle = true;
    button.tone = ButtonTone.ButtonToneNeutral;
    button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    return Button({ session: app.ui.session, props: button });
}
