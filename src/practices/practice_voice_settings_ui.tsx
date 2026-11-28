import { PracticeVoiceSettingsNewCodes } from "practice_voice_settings";
import { PracticeVoiceSettingsNewPacks } from "practice_voice_settings";
import { PracticeVoiceSettingsNewOptions } from "practice_voice_settings";
// Authored UI composition; native application state remains in practice_voice_settings.zi.
import { AppCopyText, FrameTextHold } from "text_buffers";
import { PracticeNarrationDecline } from "practice_downloads";
import * as NativeLayout from "kryon/layout";
import * as NativeSegmentedControl from "kryon/segmented_control";
import { save_settings } from "app_settings";
import { InnerBreeze } from "app_types";
import { Wrap } from "kryon/text_props";
import { Dropdown } from "kryon/tsx/dropdown";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Text } from "kryon/tsx/text";
import { Toggle } from "kryon/tsx/toggle";
import { LocaleLanguageAt, LocaleLanguageCount, LocaleText } from "locale";
import { AppFontSize, AppParagraphHeight, AppScale } from "metrics";
import {
    PracticeContentReviewNext,
    PracticeNarrationDownload,
    PracticeNarrationPackAt,
    PracticeNarrationPrefer,
    PracticeNarrationShownLanguage,
    PracticeNarrationState,
    PracticeVoiceRecorded
} from "practice_downloads";
import {
    EmptyString,
    NARRATION_DOWNLOAD_ICON,
    NARRATION_LANGUAGE_MAX,
    NARRATION_REMOVE_ICON,
    PracticeNarrationStatus
} from "practice_voice_settings";

export function PracticeNarrationLanguagesView(
    app: NativeRef<InnerBreeze>,
    practice: s32,
    voice: string,
    choice: u8[],
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let options = PracticeVoiceSettingsNewOptions();
    let packs = PracticeVoiceSettingsNewPacks();
    let codes = PracticeVoiceSettingsNewCodes();
    let count: s32 = s32(0n);
    for (let rank = s32(0n); rank < LocaleLanguageCount(); rank += s32(1)) {
        let index = PracticeNarrationPackAt(practice, rank, voice);
        if (index < 0n || count >= NARRATION_LANGUAGE_MAX) {
            continue;
        }
        let state = PracticeNarrationState(index);
        {
            let language = LocaleLanguageAt(rank);
            nativeSet(options, count, {
                key: u64(rank + 1n),
                label: FrameTextHold(nativeRef(app.ui.frame_text), language.label),
                action_shape:
                    state === 2n
                        ? NARRATION_REMOVE_ICON
                        : state === 1n
                          ? EmptyString()
                          : NARRATION_DOWNLOAD_ICON,
                action_label: ""
            });
            nativeSet(codes, count, FrameTextHold(nativeRef(app.ui.frame_text), language.code));
        }
        nativeAt(options, count).action_label = FrameTextHold(
            nativeRef(app.ui.frame_text),
            LocaleText(state === 2n ? "practice_download_remove" : "practice_narration_download")
        );
        nativeSet(packs, count, index);
        count = count + 1n;
    }
    if (count === 0n) {
        return;
    }
    let selected: s32 = s32(-1n);
    {
        let shown = PracticeNarrationShownLanguage(practice, voice);
        for (let option = s32(0n); option < count; option += s32(1)) {
            if (nativeAt(codes, option) === shown) {
                selected = option;
            }
        }
    }
    let pick = Dropdown({
        session: app.ui.session,
        props: {
            key: NativeLayout.KeyHash("inbe/practice/customize/narration-language") + u64(practice),
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(44n))
            },
            selected_index: selected,
            placeholder: LocaleText("language_label")
        },
        options: nativeSlice(options, 0n, count)
    });
    if (pick.action_index >= 0n && pick.action_index < count) {
        let index = nativeAt(packs, pick.action_index);
        let state = PracticeNarrationState(index);
        if (state === 1n || state === 2n) {
            PracticeNarrationDecline(index);
        } else {
            PracticeNarrationDownload(index);
        }
    }
    if (pick.changed && pick.selected_index >= 0n && pick.selected_index < count) {
        AppCopyText(nativeAt(codes, pick.selected_index), choice);
        PracticeNarrationPrefer(practice, nativeAt(codes, pick.selected_index));
        PracticeNarrationDownload(nativeAt(packs, pick.selected_index));
        app.settings_dirty = 1n;
        save_settings(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(44n + 16n);
    let status = PracticeNarrationStatus(app, practice, voice);
    if (status.count > 0n) {
        let status_h = AppParagraphHeight(status, width, AppFontSize(), AppScale(3n));
        <Text
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: float32(width),
                    height: float32(status_h)
                },
                text: status,
                size: AppFontSize(),
                wrap: Wrap.TextWrapAuto
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + (status_h + AppScale(12n));
    }
}

export function PracticeNarrationSettingsView(
    app: NativeRef<InnerBreeze>,
    practice: s32,
    male: boolean,
    choice: u8[],
    x: s32,
    width: s32,
    y: NativeRef<s32>
): s32 {
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(28n))
            },
            text: LocaleText("voice_narration_label")
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(36n);
    let narration = Toggle({
        session: app.ui.session,
        props: {
            id: 15422n,
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(44n))
            },
            value: app.voice_narration_enabled !== 0n,
            off_label: LocaleText("toggle_off"),
            on_label: LocaleText("toggle_on")
        }
    });
    if (narration.changed) {
        app.voice_narration_enabled = narration.value ? 1n : 0n;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(56n);
    if (app.voice_narration_enabled === 0n) {
        return -1n;
    }
    PracticeContentReviewNext();
    let picked: s32 = s32(-1n);
    if (!PracticeVoiceRecorded(practice, "male")) {
        PracticeNarrationLanguagesView(app, practice, EmptyString(), choice, x, width, y);
        return picked;
    }
    {
        let options: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] =
            [
                { label: LocaleText("practice_voice_female") },
                { label: LocaleText("practice_voice_male") }
            ];
        let props: NativeSegmentedControl.Props = {};
        props.key = NativeLayout.KeyHash("inbe/practice/customize/voice") + u64(practice);
        props.bounds = {
            x: float32(x),
            y: float32(nativeDeref(y)),
            width: float32(width),
            height: float32(AppScale(42n))
        };
        props.height = AppScale(42n);
        props.selected_index = male ? 1n : 0n;
        props.has_selection = true;
        let choice_voice = SegmentedControl({
            session: app.ui.session,
            props: props,
            options: nativeSlice(options)
        });
        if (choice_voice.changed) {
            picked = choice_voice.selected_index;
            male = choice_voice.selected_index === 1n;
        }
        nativeDeref(y) = nativeDeref(y) + AppScale(42n + 12n);
    }
    PracticeNarrationLanguagesView(
        app,
        practice,
        male ? "male" : EmptyString(),
        choice,
        x,
        width,
        y
    );
    return picked;
}
