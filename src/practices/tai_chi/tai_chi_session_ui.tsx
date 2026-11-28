import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in tai_chi_session.zi.
import * as NativeModal from "kryon/modal";
import { app_close_modal } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { ModalType } from "modal_rules";
import { NativePresent } from "native_flags";
import { PackageFree, PackageText } from "package_files";
import { TaiChiExitToStart } from "tai_chi_session";
import { FrameTextHold } from "text_buffers";

export function tai_chi_handle_exit_modalView(app: NativeRef<InnerBreeze>): s32 {
    if (
        !NativePresent(app) ||
        app.modal.active === 0n ||
        app.modal.type !== ModalType.ModalConfirmExitSession
    ) {
        return 0n;
    }
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
        {
            label: FrameTextHold(nativeRef(app.ui.frame_text), LocaleText("cancel_button")),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: FrameTextHold(nativeRef(app.ui.frame_text), LocaleText("exit_button")),
            tone: ButtonTone.ButtonToneDanger,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        }
    ];
    let message = PackageText(LocaleText("all_progress_lost_message"), "");
    let modal_result = ActionModal({
        session: app.ui.session,
        props: {
            title: LocaleText("exit_session_title"),
            message: message
        },
        actions: nativeSlice(actions, 0n, 2n)
    }).action;
    PackageFree(message);
    if (modal_result === 1n || modal_result === -1n) {
        app_close_modal(app);
    } else if (modal_result === 2n) {
        TaiChiExitToStart(app);
        return 2n;
    }
    return 1n;
}
