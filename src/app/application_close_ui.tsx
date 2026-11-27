import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in application_close.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import { AppClosePromptResult, InnerBreeze, SessionExitModalResult } from "app_types";
import { app_request_desktop_quit } from "application_close";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { NativePresent } from "native_flags";

export function app_draw_session_exit_modalView(
    app: *InnerBreeze,
    can_save: s32,
    save_message: string,
    discard_message: string
): SessionExitModalResult {
    let modal_result: s32 = s32(0);
    if (can_save !== 0n) {
        let actions: [
            NativeModal.ActionModalAction,
            NativeModal.ActionModalAction,
            NativeModal.ActionModalAction
        ] = [
            {
                label: LocaleText("cancel_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: LocaleText("save_button"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            },
            {
                label: LocaleText("discard_button"),
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        ];
        modal_result = (
            <ActionModal
                session={app.ui.session}
                props={{ title: LocaleText("exit_session_title"), message: save_message }}
                actions={actions[:3n]}
            />
        ).action;
        if (modal_result === 2n) {
            return SessionExitModalResult.SessionExitModalSave;
        }
        if (modal_result === 3n) {
            return SessionExitModalResult.SessionExitModalDiscard;
        }
    } else {
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
        modal_result = (
            <ActionModal
                session={app.ui.session}
                props={{ title: LocaleText("exit_session_title"), message: discard_message }}
                actions={actions[:2n]}
            />
        ).action;
        if (modal_result === 2n) {
            return SessionExitModalResult.SessionExitModalDiscard;
        }
    }
    return modal_result === 1n || modal_result === -1n
        ? SessionExitModalResult.SessionExitModalCancel
        : SessionExitModalResult.SessionExitModalNone;
}

export function app_draw_close_prompt(app: *InnerBreeze): void {
    let modal_result: s32 = s32(0);
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [{}, {}];
    let props: NativeModal.ActionModalProps = {};
    if (!NativePresent(app) || app.close_prompt_open === 0n) {
        return;
    }
    if (app.blocked_input_frame === app.breathing.frame) {
        return;
    }
    actions[0n].label = LocaleText("desktop_close_keep_running_button");
    actions[0n].tone = ButtonTone.ButtonToneAccent;
    actions[0n].emphasis = ButtonEmphasis.ButtonEmphasisFilled;
    actions[1n].label = LocaleText("desktop_close_quit_button");
    actions[1n].tone = ButtonTone.ButtonToneDanger;
    actions[1n].emphasis = ButtonEmphasis.ButtonEmphasisFilled;
    props.key = NativeLayout.KeyHash("inbe/desktop-close");
    props.title = LocaleText("desktop_close_prompt_title");
    props.message = LocaleText("desktop_close_prompt_message");
    props.max_width = 420n;
    modal_result = (
        <ActionModal
            session={app.ui.session}
            props={props}
            actions={actions[:2n]}
        />
    ).action;
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
