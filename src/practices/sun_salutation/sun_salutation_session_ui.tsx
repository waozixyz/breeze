import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in sun_salutation_session.zi.
import * as NativeModal from "kryon/modal";
import { app_close_modal } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { ModalType } from "modal_rules";
import { NativePresent } from "native_flags";
import { exit_to_start } from "sun_salutation_session";

export function sun_salutation_handle_exit_modalView(app: *InnerBreeze): s32 {
    if (
        !NativePresent(app) ||
        app.modal.active === 0n ||
        app.modal.type !== ModalType.ModalConfirmExitSession
    ) {
        return 0n;
    }
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
        {
            label: LocaleText("cancel_button"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: LocaleText("exit_button"),
            tone: ButtonTone.ButtonToneDanger,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        }
    ];
    let modal_result = (
        <ActionModal
            session={app.ui.session}
            props={{
                title: LocaleText("exit_session_title"),
                message: LocaleText("all_progress_lost_message")
            }}
            actions={actions[:2n]}
        />
    ).action;
    if (modal_result === 1n || modal_result === -1n) {
        app_close_modal(app);
    } else if (modal_result === 2n) {
        exit_to_start(app);
        return 2n;
    }
    return 1n;
}
