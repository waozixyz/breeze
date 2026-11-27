import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in meditation_session.zi.
import * as NativeModal from "kryon/modal";
import * as State_meditation_session from "meditation_session";
import { app_close_modal } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { meditation_start_seconds } from "meditation_session";
import { NativePresent } from "native_flags";

export function meditation_draw_setup_modalView(app: *InnerBreeze): void {
    if (!NativePresent(app)) {
        return;
    }
    let actions: [
        NativeModal.ActionModalAction,
        NativeModal.ActionModalAction,
        NativeModal.ActionModalAction,
        NativeModal.ActionModalAction,
        NativeModal.ActionModalAction,
        NativeModal.ActionModalAction
    ] = [
        {
            label: LocaleText("duration_5m"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: LocaleText("duration_15m"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: LocaleText("duration_30m"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: LocaleText("duration_1h"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: LocaleText("duration_2h"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        },
        {
            label: LocaleText("cancel_button"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        }
    ];
    let result = (
        <ActionModal
            session={app.ui.session}
            props={{ title: LocaleText("meditation_title") }}
            actions={actions[:6n]}
        />
    ).action;
    if (result >= 1n && result <= 5n) {
        meditation_start_seconds(app, State_meditation_session.duration_presets[result - 1n]);
    } else if (result === 6n || result === -1n) {
        app_close_modal(app);
    }
}
