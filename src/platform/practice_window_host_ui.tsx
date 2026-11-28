// Authored UI composition; native application state remains in practice_window_host.zi.
import * as NativeButton from "kryon/button";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { Button } from "kryon/tsx/button";
import { LocaleText } from "locale";
import { AppScale } from "metrics";
import { practice_draw_audio_controls_at } from "practice_audio_controls";
import { practice_get, practice_label } from "practice_registry";
import {
    PRACTICE_WINDOW_CLOSE,
    PRACTICE_WINDOW_RESTORE,
    PRACTICE_WINDOW_STAY
} from "practice_window_host";
import {
    SESSION_WINDOW_DESKTOP_ID,
    session_window_breathe_tap,
    session_window_can_breathe,
    session_window_practice
} from "session_window_view";
import { session_window_breathe_button } from "session_window_view_ui";

export function PracticeWindowControls(app: NativeRef<InnerBreeze>, bounds: Rectangle): s32 {
    let session = app.ui.session;
    let tapped = false;
    {
        let card: NativeButton.Props = {};
        card.id = SESSION_WINDOW_DESKTOP_ID + 2n;
        card.bounds = bounds;
        card.invisible = true;
        card.label = practice_label(session_window_practice(app.session_window.screen));
        tapped = Button({ session: session, props: card });
    }
    let action: s32 = PRACTICE_WINDOW_STAY;
    for (let index = s32(0n); index <= s32(1n); index += s32(1)) {
        let button: NativeButton.Props = {};
        button.id = SESSION_WINDOW_DESKTOP_ID + index;
        button.bounds = {
            x: bounds.width - 78.0 + float32(index) * 36.0,
            y: 2.0,
            width: 36.0,
            height: 36.0
        };
        button.label =
            index === 0n ? LocaleText("session_maximize_button") : LocaleText("close_button");
        button.icon_only = true;
        button.icon_shape =
            index === 0n
                ? "S1.8rr:M14 5H19V10M10 19H5V14M19 5L13 11M5 19L11 13"
                : "S1.8rr:M6 6L18 18M18 6L6 18";
        button.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
        if (Button({ session: session, props: button })) {
            action = index === 0n ? PRACTICE_WINDOW_RESTORE : PRACTICE_WINDOW_CLOSE;
        }
    }
    let practice = practice_get(session_window_practice(app.session_window.screen));
    let can_breathe = session_window_can_breathe(app, practice);
    let double_tap = can_breathe && app.double_tap_to_breathe !== 0n;
    if (!double_tap) {
        app.breath_tap_last_time = 0.0;
    }
    let breathed = can_breathe && !double_tap && session_window_breathe_button(app, bounds);
    practice_draw_audio_controls_at(
        app,
        AppScale(4n),
        AppScale(52n),
        2n,
        session_window_practice(app.session_window.screen)
    );
    if (action !== PRACTICE_WINDOW_STAY) {
        return action;
    }
    if (breathed) {
        practice.breathe(app);
        return PRACTICE_WINDOW_STAY;
    }
    if (!tapped) {
        return PRACTICE_WINDOW_STAY;
    }
    if (double_tap) {
        session_window_breathe_tap(app, practice);
        return PRACTICE_WINDOW_STAY;
    }
    return PRACTICE_WINDOW_RESTORE;
}
