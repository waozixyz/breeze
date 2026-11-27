// Authored UI composition; native application state remains in settings_status_view.zi.
import { CurrentApp } from "current_app";
import { Wrap } from "kryon/text_props";
import { Text } from "kryon/tsx/text";
import { NativePresent } from "native_flags";

export function settings_draw_status_line(value: string, x: s32, y: s32): void {
    let app = CurrentApp();
    if (!NativePresent(app) || value.count === 0n) {
        return;
    }
    <Text
        session={app.ui.session}
        props={{
            bounds: { x: float32(x), y: float32(y), width: 0.0, height: 0.0 },
            text: value,
            wrap: Wrap.TextWrapNone
        }}
    />;
}
