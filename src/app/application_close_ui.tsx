import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in application_close.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import { AppClosePromptResult, InnerBreeze, SessionExitModalResult } from "app_types";
import { app_request_desktop_quit } from "application_close";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { NativePresent } from "native_flags";
import { FrameTextSave, FrameTextRead } from "text_buffers";

export function app_draw_session_exit_modalView(
    app: NativeRef<InnerBreeze>,
    can_save: s32,
    save_message: string,
    discard_message: string
): SessionExitModalResult {
    let cancel_button_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("cancel_button")
    );
    let save_button_range = FrameTextSave(nativeRef(app.ui.frame_text), LocaleText("save_button"));
    let discard_button_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("discard_button")
    );
    let exit_button_range = FrameTextSave(nativeRef(app.ui.frame_text), LocaleText("exit_button"));
    let exit_session_title_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("exit_session_title")
    );
    let modal_result: s32 = s32(0);
    if (can_save !== 0n) {
        let actions: [
            NativeModal.ActionModalAction,
            NativeModal.ActionModalAction,
            NativeModal.ActionModalAction
        ] = [
            {
                label: FrameTextRead(nativeRef(app.ui.frame_text), cancel_button_range),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: FrameTextRead(nativeRef(app.ui.frame_text), save_button_range),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            },
            {
                label: FrameTextRead(nativeRef(app.ui.frame_text), discard_button_range),
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        ];
        modal_result = ActionModal({
            session: app.ui.session,
            props: {
                title: FrameTextRead(nativeRef(app.ui.frame_text), exit_session_title_range),
                message: save_message
            },
            actions: nativeSlice(actions, 0n, 3n)
        }).action;
        if (modal_result === 2n) {
            return SessionExitModalResult.SessionExitModalSave;
        }
        if (modal_result === 3n) {
            return SessionExitModalResult.SessionExitModalDiscard;
        }
    } else {
        let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
            {
                label: FrameTextRead(nativeRef(app.ui.frame_text), cancel_button_range),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: FrameTextRead(nativeRef(app.ui.frame_text), exit_button_range),
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        ];
        modal_result = ActionModal({
            session: app.ui.session,
            props: {
                title: FrameTextRead(nativeRef(app.ui.frame_text), exit_session_title_range),
                message: discard_message
            },
            actions: nativeSlice(actions, 0n, 2n)
        }).action;
        if (modal_result === 2n) {
            return SessionExitModalResult.SessionExitModalDiscard;
        }
    }
    return modal_result === 1n || modal_result === -1n
        ? SessionExitModalResult.SessionExitModalCancel
        : SessionExitModalResult.SessionExitModalNone;
}

export function app_draw_close_prompt(app: NativeRef<InnerBreeze>): void {
    let modal_result: s32 = s32(0);
    if (!NativePresent(app) || app.close_prompt_open === 0n) {
        return;
    }
    if (app.blocked_input_frame === app.breathing.frame) {
        return;
    }
    let desktop_close_keep_running_button_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("desktop_close_keep_running_button")
    );
    let desktop_close_quit_button_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("desktop_close_quit_button")
    );
    let desktop_close_prompt_title_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("desktop_close_prompt_title")
    );
    let desktop_close_prompt_message_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("desktop_close_prompt_message")
    );
    {
        let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [{}, {}];
        let props: NativeModal.ActionModalProps = {};
        nativeAt(actions, 0n).label = FrameTextRead(
            nativeRef(app.ui.frame_text),
            desktop_close_keep_running_button_range
        );
        nativeAt(actions, 0n).tone = ButtonTone.ButtonToneAccent;
        nativeAt(actions, 0n).emphasis = ButtonEmphasis.ButtonEmphasisFilled;
        nativeAt(actions, 1n).label = FrameTextRead(
            nativeRef(app.ui.frame_text),
            desktop_close_quit_button_range
        );
        nativeAt(actions, 1n).tone = ButtonTone.ButtonToneDanger;
        nativeAt(actions, 1n).emphasis = ButtonEmphasis.ButtonEmphasisFilled;
        props.key = NativeLayout.KeyHash("inbe/desktop-close");
        props.title = FrameTextRead(nativeRef(app.ui.frame_text), desktop_close_prompt_title_range);
        props.message = FrameTextRead(
            nativeRef(app.ui.frame_text),
            desktop_close_prompt_message_range
        );
        props.max_width = 420n;
        modal_result = ActionModal({
            session: app.ui.session,
            props: props,
            actions: nativeSlice(actions, 0n, 2n)
        }).action;
    }
    if (modal_result === -1n) {
        app.close_prompt_open = 0n;
    } else if (modal_result === 1n) {
        app.close_prompt_open = 0n;
        app.close_prompt_result = AppClosePromptResult.AppClosePromptKeepRunning;
    } else if (modal_result === 2n) {
        app.close_prompt_open = 0n;
        app.close_prompt_result = AppClosePromptResult.AppClosePromptQuit;
        app_request_desktop_quit(app);
    }
}
