import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in crash_report_dialog.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as State_crash_report_dialog from "crash_report_dialog";
import { app_close_modal } from "app_modal_state";
import { AppToast } from "app_toast";
import { InnerBreeze } from "app_types";
import { CrashReportModalMessage } from "crash_report_dialog";
import { CrashReportApproveAndQueue, CrashReportDiscard } from "crash_report_store";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { LocaleText } from "locale";
import { LumiNodeTrafficAllowed } from "lumi_connection";
import { LumiFeedbackWake } from "lumi_online";
import { AppsInstalledMask } from "module_host";
import { FlagIntersection, NativePresent } from "native_flags";
import { AppThemeName } from "settings_actions";
import { storage_has_sync_account } from "sync_state";

export function CrashReportModalDraw(app: NativeRef<InnerBreeze>): void {
    if (!NativePresent(app)) {
        return;
    }
    if (!State_crash_report_dialog.crash_report_pending.present) {
        app_close_modal(app);
        return;
    }
    let message = CrashReportModalMessage(app);
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
        {
            label: LocaleText("crash_report_dismiss"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: LocaleText("crash_report_send"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        }
    ];
    let props: NativeModal.ActionModalProps = {
        key: NativeLayout.KeyHash("inbe/crash-report"),
        title: LocaleText("crash_report_title"),
        message: message,
        max_width: 460n
    };
    let choice = ActionModal({
        session: app.ui.session,
        props: props,
        actions: nativeSlice(actions)
    }).action;
    if (choice === 1n || choice === -1n) {
        CrashReportDiscard(nativeRef(State_crash_report_dialog.crash_report_pending));
        State_crash_report_dialog.crash_report_prompted = false;
        app_close_modal(app);
    } else if (choice === 2n) {
        let queued = CrashReportApproveAndQueue(
            nativeRef(State_crash_report_dialog.crash_report_pending),
            app.breathing.screen,
            FlagIntersection(app.enabled_apps, AppsInstalledMask()),
            AppThemeName(app.theme_id),
            app.ui_scale_tenths
        );
        if (queued) {
            LumiFeedbackWake();
            State_crash_report_dialog.crash_report_prompted = false;
            app_close_modal(app);
            let online_ready = storage_has_sync_account() !== 0n && LumiNodeTrafficAllowed();
            AppToast(
                LocaleText(online_ready ? "crash_report_queued" : "crash_report_saved_offline")
            );
        } else {
            AppToast(LocaleText("crash_report_failed"));
        }
    }
}
