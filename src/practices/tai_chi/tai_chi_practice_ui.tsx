import { ActionModal } from "kryon/tsx/action_modal";
import { TaiChiItemAllowed } from "tai_chi_entry";
import { TaiChiDrawPreview } from "tai_chi_draw";
import { AppScale } from "metrics";
import { ExerciseType } from "exercise_types";
import { UnlockTaiChi, UnlockStart } from "practice_unlocks";
import { PracticeContentRequest } from "practice_downloads";
import * as EntryState from "tai_chi_entry";
// Authored UI composition; native application state remains in tai_chi_practice.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeLockIcon from "mingcute/mingcute_regular_lock";
import * as State_tai_chi_course from "tai_chi_course";
import * as State_practice_unlocks from "practice_unlocks";
import * as State_practice_downloads from "practice_downloads";
import { InnerBreeze } from "app_types";
import { DewReady } from "dew";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Button } from "kryon/tsx/button";
import { LocaleText } from "locale";
import { MetricsScale } from "metrics";
import { PracticeContentStatus } from "practice_downloads";
import { PracticeDownloadPriceText } from "practice_offer";
import { PracticeFigureRequest } from "practice_ui_types";
import { UnlockBuying, UnlockOwned } from "practice_unlocks";
import { TAI_CHI_SOURCE_LOCKED, TaiChiCourseItemIndex } from "tai_chi_course";
import { TAI_CHI_CHARACTER_COUNT } from "tai_chi_rules";

export function TaiChiCourseFigureView(
    app: *InnerBreeze,
    request: PracticeFigureRequest
): void {
    if (
        request.preview &&
        request.index >= 0n &&
        request.index < State_tai_chi_course.tai_chi_course.item_count &&
        request.character >= 0n &&
        request.character < TAI_CHI_CHARACTER_COUNT
    ) {
        if (TaiChiItemAllowed(request.index)) {
            TaiChiDrawPreview(
                app.ui.session,
                request.index,
                request.character,
                app.tai_chi.view,
                request.bounds,
                request.key,
                request.alt_text
            );
        } else {
            <Button
                session={app.ui.session}
                props={{
                    key: request.key,
                    bounds: {
                        x: request.bounds.x + (request.bounds.width - float32(AppScale(48n))) / 2.0,
                        y:
                            request.bounds.y +
                            (request.bounds.height - float32(AppScale(48n))) / 2.0,
                        width: float32(AppScale(48n)),
                        height: float32(AppScale(48n))
                    },
                    icon_shape: NativeLockIcon.Shape,
                    label: LocaleText("tai_chi_unlock_title"),
                    icon_only: true,
                    disabled: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />;
        }
    }
}

export function TaiChiUnlockDrawView(app: *InnerBreeze): boolean {
    let owned = UnlockOwned(UnlockTaiChi);
    let full = TaiChiCourseItemIndex("full/normal");
    if (
        owned &&
        full >= 0n &&
        State_tai_chi_course.tai_chi_course.items[full].source !== TAI_CHI_SOURCE_LOCKED
    ) {
        EntryState.tai_chi_unlock_requested = false;
        return false;
    }
    let busy = owned
        ? PracticeContentStatus(s32(ExerciseType.EXERCISE_TAI_CHI)) === 1n
        : UnlockBuying();
    let note = LocaleText("tai_chi_unlock_message");
    if (busy) {
        note = LocaleText(owned ? "practice_download_busy" : "practice_unlock_busy");
    } else if (!owned && !DewReady()) {
        note = LocaleText("practice_unlock_account");
    } else if (!owned && State_practice_unlocks.unlock_notice.count > 0n) {
        note = LocaleText(State_practice_unlocks.unlock_notice);
    } else if (owned && PracticeContentStatus(s32(ExerciseType.EXERCISE_TAI_CHI)) === 3n) {
        note = LocaleText("practice_download_failed");
    }
    let label = LocaleText("practice_install");
    if (!owned) {
        label = PracticeDownloadPriceText(app, "practice_unlock_button");
    }
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
        {
            label: LocaleText("back_button"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: label,
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
            disabled:
                busy || (!owned && (!DewReady() || !State_practice_downloads.practice_paid_allowed))
        }
    ];
    let result = (
        <ActionModal
            session={app.ui.session}
            props={{
                key: NativeLayout.KeyHash("tai-chi/unlock"),
                title: LocaleText("tai_chi_unlock_title"),
                message: note,
                scale: MetricsScale()
            }}
            actions={actions[:]}
        />
    ).action;
    if (result === -1n || result === 1n) {
        EntryState.tai_chi_unlock_requested = false;
    } else if (result === 2n) {
        if (owned) {
            PracticeContentRequest(s32(ExerciseType.EXERCISE_TAI_CHI));
        } else {
            UnlockStart();
        }
    }
    return true;
}
