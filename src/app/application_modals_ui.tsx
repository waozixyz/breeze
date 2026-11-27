import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in application_modals.zi.
import * as NativeModal from "kryon/modal";
import { app_close_modal } from "app_modal_state";
import { TraceLog } from "app_trace";
import { InnerBreeze } from "app_types";
import { LOG_INFO, draw_profile_picture_picker_modal } from "application_modals";
import { CrashReportPump } from "crash_report_dialog";
import { CrashReportModalDraw } from "crash_report_dialog_ui";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { MediaCompressionPump } from "media_compression_dialog";
import { MediaCompressionDialogDraw, MediaCompressionOfferDraw } from "media_compression_dialog_ui";
import { meditation_music_start_download } from "meditation_music";
import { ModalType } from "modal_rules";
import { NativePresent } from "native_flags";
import { NodeAppName, NodeAppRetryOpen, NodeAppTitle } from "node_apps";
import { practice_screen_draw_modal } from "practice_screen_ui";
import { ProfileStoragePlansModalDraw, ProfileTopUpModalDraw } from "profile_dew_ui";
import { app_return_to_apps } from "return_bar";
import { settings_data_draw_modals } from "settings_data_ui";
import {
    settings_screen_set_status_error,
    settings_screen_set_status_success
} from "settings_status";
import {
    settings_sync_account_draw_alias_modal,
    settings_sync_account_draw_public_id_modal
} from "settings_sync_account_impl";
import { settings_screen_draw_app_icon_modal } from "settings_theme";
import { settings_screen_draw_theme_picker_modal } from "settings_theme";
import { tai_chi_modal_draw } from "tai_chi_practice";
import { ScreenNodeApp } from "types";
import { WorkoutManagerDraw } from "workout";

export function draw_global_modal(app: *InnerBreeze): void {
    if (NativePresent(app)) {
        CrashReportPump(app);
        MediaCompressionPump(app);
        MediaCompressionOfferDraw(app);
    }
    let modal_result: s32 = s32(0);
    if (!NativePresent(app) || app.modal.active === 0n) {
        return;
    }
    if (app.blocked_input_frame === app.breathing.frame) {
        return;
    }
    if (app.modal.type === ModalType.ModalCrashReport) {
        CrashReportModalDraw(app);
        return;
    }
    if (app.modal.type === ModalType.ModalMediaCompression) {
        MediaCompressionDialogDraw(app);
        return;
    }
    if (settings_data_draw_modals(app) !== 0n) {
        return;
    }
    if (app.modal.type === ModalType.ModalNodeAppFailure) {
        if (app.breathing.screen !== ScreenNodeApp) {
            app_close_modal(app);
            return;
        }
        let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
            {
                label: LocaleText("close_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: LocaleText("retry_button"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        ];
        let choice = (
            <ActionModal
                session={app.ui.session}
                props={{
                    title: NodeAppTitle(NodeAppName(app.node_app_slot)),
                    message: LocaleText("node_app_unavailable")
                }}
                actions={actions[:]}
            />
        ).action;
        if (choice === 1n || choice === -1n) {
            app_close_modal(app);
            app.host_feature = 0n;
            app_return_to_apps(app);
        } else if (choice === 2n) {
            app_close_modal(app);
            NodeAppRetryOpen(app.node_app_slot);
        }
        return;
    }
    if (app.modal.type === ModalType.ModalMeditationNetworkError) {
        let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
            {
                label: LocaleText("cancel_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            },
            {
                label: LocaleText("retry_button"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        ];
        modal_result = (
            <ActionModal
                session={app.ui.session}
                props={{
                    title: LocaleText("meditation_music_network_error_title"),
                    message: LocaleText("meditation_music_network_error_message")
                }}
                actions={actions[:2n]}
            />
        ).action;
        if (modal_result === 1n || modal_result === -1n) {
            TraceLog(LOG_INFO, "AUDIO: Network error download cancelled");
            app_close_modal(app);
        } else if (modal_result === 2n) {
            TraceLog(LOG_INFO, "AUDIO: Network error download retry requested");
            app_close_modal(app);
            meditation_music_start_download(app);
        }
    }
    if (app.modal.type === ModalType.ModalStoragePlans) {
        ProfileStoragePlansModalDraw(app);
        return;
    }
    if (app.modal.type === ModalType.ModalDewTopUp) {
        ProfileTopUpModalDraw(app);
        return;
    }
    if (app.modal.type === ModalType.ModalWorkoutManager) {
        WorkoutManagerDraw(app);
        return;
    }
    if (
        app.modal.type === ModalType.ModalTaiChiCourse ||
        app.modal.type === ModalType.ModalTaiChiCustomize
    ) {
        tai_chi_modal_draw(app);
        return;
    }
    if (app.modal.type === ModalType.ModalAppIconPicker) {
        settings_screen_draw_app_icon_modal(app);
        return;
    }
    if (app.modal.type === ModalType.ModalThemePicker) {
        settings_screen_draw_theme_picker_modal(app);
    }
    if (app.modal.type === ModalType.ModalProfilePicturePicker) {
        draw_profile_picture_picker_modal(app);
        return;
    }
    if (
        app.modal.type === ModalType.ModalPracticeManual ||
        app.modal.type === ModalType.ModalPracticeConfig ||
        app.modal.type === ModalType.ModalEditProgressiveStartSpeed
    ) {
        practice_screen_draw_modal(app);
        return;
    }
    if (app.modal.type === ModalType.ModalSyncAlias) {
        modal_result = settings_sync_account_draw_alias_modal(app);
        if (modal_result === 1n) {
            app_close_modal(app);
            settings_screen_set_status_success(LocaleText("sync_alias_saved"), "");
        } else if (modal_result === 2n) {
            settings_screen_set_status_error(LocaleText("sync_alias_failed"));
        } else if (modal_result === 3n) {
            app_close_modal(app);
        }
    }
    if (app.modal.type === ModalType.ModalSyncPublicId) {
        modal_result = settings_sync_account_draw_public_id_modal(app);
        if (modal_result !== 0n) {
            app_close_modal(app);
        }
    }
}
