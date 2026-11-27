import { SettingsAudioNewDownloadStatus } from "settings_audio";
import { SettingsAudioNewOptions } from "settings_audio";
// Authored UI composition; native application state remains in settings_audio.zi.
import * as State_settings_audio from "settings_audio";
import { save_settings } from "app_settings";
import {
    AUDIO_BUILTIN_MUSIC_COUNT,
    AUDIO_CUSTOM_MUSIC_MAX,
    AUDIO_CUSTOM_SOUND_MAX,
    AUDIO_LABEL_SIZE,
    AUDIO_MUSIC_COUNT_MAX,
    AUDIO_MUSIC_NONE,
    InnerBreeze,
    SETTINGS_VOLUME_MAX,
    SETTINGS_VOLUME_MIN
} from "app_types";
import {
    app_audio_output_level,
    app_audio_reinitialize,
    app_audio_reload_cue_sounds,
    app_play_bell_cue
} from "audio";
import { audio_set_music_volume, audio_set_sound_volume } from "audio_runtime";
import { app_audio_music_count, app_audio_music_sanitize_selection } from "audio_selection";
import { CurrentApp } from "current_app";
import { practice_count } from "exercise_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { FileDownloadStatus } from "kryon/file_download";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    meditation_music_available,
    meditation_music_draw_download_progress,
    meditation_music_format_download_status,
    meditation_music_start_download,
    meditation_music_unload
} from "meditation_music";
import { AppScale, AppSmallFontSize } from "metrics";
import { app_audio_music_label, app_audio_remove_custom_music } from "music_library";
import { FlagComplement, FlagIntersection, FlagShiftLeft, NativePresent } from "native_flags";
import {
    SETTINGS_AUDIO_ACTION_MUSIC,
    settings_audio_button_row_height,
    settings_audio_clamp_count,
    settings_audio_list_row_height,
    settings_audio_music_body,
    settings_audio_music_volume,
    settings_audio_output_body,
    settings_audio_practice_label,
    settings_audio_preview_cue_playing,
    settings_audio_preview_music_playing,
    settings_audio_sound_volume,
    settings_audio_start_import,
    settings_audio_stop_preview,
    settings_audio_toggle_cue_preview,
    settings_audio_toggle_music_preview
} from "settings_audio";
import { settings_button_width, settings_section_end } from "settings_ui";
import {
    commit_slider_rowView as commit_slider_row,
    draw_audio_meterView as draw_audio_meter,
    draw_toggle_row,
    settings_row_dividerView as settings_row_divider,
    settings_section_beginView as settings_section_begin
} from "settings_ui_ui";
import { AppTextFromCString } from "text_buffers";

export function settings_audio_draw_status(x: s32, y: NativeRef<s32>, action: s32): void {
    if (
        State_settings_audio.audio_status_action !== action ||
        nativeAt(State_settings_audio.audio_status, 0n) === u8(0n)
    ) {
        return;
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: { x: float32(x), y: float32(nativeDeref(y)), width: 0n, height: 0n },
            text: AppTextFromCString(
                nativeRef(nativeAt(State_settings_audio.audio_status, 0n)),
                256n
            ),
            wrap: Wrap.TextWrapNone
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(24n);
}

export function settings_audio_subheading(x: s32, w: s32, y: NativeRef<s32>, text: string): void {
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y) + AppScale(10n)),
                width: float32(w),
                height: float32(AppScale(20n))
            },
            text: text,
            size: AppSmallFontSize(),
            wrap: Wrap.TextWrapNone
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(36n);
}

export function settings_audio_list_row(
    app: NativeRef<InnerBreeze>,
    id: s32,
    x: s32,
    w: s32,
    y: NativeRef<s32>,
    title: string,
    detail: string,
    playing: boolean
): s32 {
    let control_h = AppScale(32n);
    let play_label = playing ? LocaleText("audio_preview_stop") : LocaleText("audio_preview_play");
    let play_w = settings_button_width(play_label, AppScale(72n));
    let remove_w = settings_button_width(LocaleText("remove_button"), AppScale(92n));
    let gap = AppScale(8n);
    let row_h = settings_audio_list_row_height();
    let label_w = w - play_w - remove_w - gap * 3n;
    if (detail === "") {
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: float32(label_w),
                    height: float32(row_h)
                },
                text: title,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone
            }}
        />;
    } else {
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y) + AppScale(6n)),
                    width: float32(label_w),
                    height: float32(AppScale(20n))
                },
                text: title,
                wrap: Wrap.TextWrapNone
            }}
        />;
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y) + AppScale(26n)),
                    width: float32(label_w),
                    height: float32(AppScale(16n))
                },
                text: detail,
                size: AppSmallFontSize(),
                wrap: Wrap.TextWrapNone
            }}
        />;
    }
    let control_y = nativeDeref(y) + (row_h - control_h) / 2n;
    let result: s32 = s32(0n);
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: id,
                bounds: {
                    x: float32(x + w - remove_w - gap - play_w),
                    y: float32(control_y),
                    width: float32(play_w),
                    height: float32(control_h)
                },
                label: play_label,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: !NativePresent(app) || app.audio_ready === 0n
            }
        })
    ) {
        result = 1n;
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: id + 1n,
                bounds: {
                    x: float32(x + w - remove_w),
                    y: float32(control_y),
                    width: float32(remove_w),
                    height: float32(control_h)
                },
                label: LocaleText("remove_button"),
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        result = 2n;
    }
    nativeDeref(y) = nativeDeref(y) + row_h;
    return result;
}

export function settings_audio_draw_output(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    let section = settings_section_begin(
        app,
        x,
        w,
        y,
        LocaleText("audio_output_label"),
        settings_audio_output_body(w)
    );
    let ix = section.inner_x;
    let iw = section.inner_width;
    if (
        draw_toggle_row(
            app,
            ix,
            iw,
            y,
            LocaleText("guide_narration_label"),
            nativeRef(app.guide_narration_enabled)
        )
    ) {
        app.guide_narration_muted = 0n;
        save_settings(app);
    }
    let status_label =
        app.audio_ready !== 0n
            ? LocaleText("audio_status_ready")
            : LocaleText("audio_status_unavailable");
    let status_w = AppScale(140n);
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(ix),
                y: float32(nativeDeref(y)),
                width: float32(iw - status_w),
                height: float32(AppScale(48n))
            },
            text: LocaleText("audio_system_default_label"),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone
        }}
    />;
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(ix + iw - status_w),
                y: float32(nativeDeref(y)),
                width: float32(status_w),
                height: float32(AppScale(48n))
            },
            text: status_label,
            align: TextAlign.TextAlignEnd,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(48n);
    let button_gap = AppScale(12n);
    let button_w = (iw - button_gap) / 2n;
    let clicked: s32 = s32(0n);
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: 3401n,
                bounds: {
                    x: float32(ix),
                    y: float32(nativeDeref(y) + AppScale(10n)),
                    width: float32(button_w),
                    height: float32(AppScale(36n))
                },
                label: LocaleText("audio_test_output_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        clicked = 1n;
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: 3402n,
                bounds: {
                    x: float32(ix + button_w + button_gap),
                    y: float32(nativeDeref(y) + AppScale(10n)),
                    width: float32(iw - button_w - button_gap),
                    height: float32(AppScale(36n))
                },
                label: LocaleText("audio_reinitialize_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        clicked = 2n;
    }
    nativeDeref(y) = nativeDeref(y) + settings_audio_button_row_height();
    if (clicked === 1n) {
        app_play_bell_cue(app, float32(1.0));
    }
    if (clicked === 2n) {
        app_audio_reinitialize(app);
    }
    nativeDeref(y) =
        nativeDeref(y) +
        draw_audio_meter(
            app,
            app_audio_output_level(app),
            ix,
            nativeDeref(y),
            iw,
            LocaleText("audio_output_level_label")
        );
    nativeDeref(y) = nativeDeref(y) + AppScale(12n);
    settings_row_divider(app, section, nativeDeref(y));
    let sound_volume = app.sound_volume;
    let music_volume = app.music_volume;
    nativeDeref(y) = nativeDeref(y) + AppScale(10n);
    if (
        commit_slider_row(
            app,
            871n,
            ix,
            iw,
            y,
            AppScale(66n),
            LocaleText("cue_volume_label"),
            SETTINGS_VOLUME_MIN,
            SETTINGS_VOLUME_MAX,
            nativeRef(sound_volume),
            "",
            0n
        ) !== 0n
    ) {
        app.sound_volume = sound_volume;
        if (State_settings_audio.audio_preview_sound.frame_count !== 0n) {
            audio_set_sound_volume(
                State_settings_audio.audio_preview_sound,
                settings_audio_sound_volume(app)
            );
        }
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(10n);
    if (
        commit_slider_row(
            app,
            872n,
            ix,
            iw,
            y,
            AppScale(66n),
            LocaleText("music_volume_label"),
            SETTINGS_VOLUME_MIN,
            SETTINGS_VOLUME_MAX,
            nativeRef(music_volume),
            "",
            0n
        ) !== 0n
    ) {
        app.music_volume = music_volume;
        if (State_settings_audio.audio_preview_music_loaded !== 0n) {
            audio_set_music_volume(
                State_settings_audio.audio_preview_music,
                settings_audio_music_volume(app)
            );
        }
    }
    settings_section_end(y);
}

export function draw_import_button(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>,
    label: string,
    action: s32,
    practice: s32
): void {
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y) + AppScale(10n)),
                    width: float32(w),
                    height: float32(AppScale(36n))
                },
                label: label,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: false
            }
        })
    ) {
        settings_audio_start_import(app, action, practice);
    }
    nativeDeref(y) = nativeDeref(y) + settings_audio_button_row_height();
    if (
        action !== SETTINGS_AUDIO_ACTION_MUSIC ||
        practice === State_settings_audio.audio_status_practice
    ) {
        settings_audio_draw_status(x, y, action);
    }
}

export function draw_cue_selector(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>,
    cue: s32,
    label: string,
    action: s32
): void {
    let options = SettingsAudioNewOptions();
    let count = app.audio_custom_sound_count + 1n;
    let play_label =
        settings_audio_preview_cue_playing(app, cue) !== 0n
            ? LocaleText("audio_preview_stop")
            : LocaleText("audio_preview_play");
    let play_w = settings_button_width(play_label, AppScale(72n));
    let import_w = settings_button_width(LocaleText("audio_import_sound_button"), AppScale(120n));
    let gap = AppScale(8n);
    let dropdown_w = w - play_w - import_w - gap * 2n;
    nativeAt(options, 0n).label = LocaleText("audio_builtin_label");
    if (count > AUDIO_CUSTOM_SOUND_MAX + 1n) {
        count = AUDIO_CUSTOM_SOUND_MAX + 1n;
    }
    let i: s32 = s32(0n);
    while (i < app.audio_custom_sound_count && i < AUDIO_CUSTOM_SOUND_MAX) {
        nativeAt(options, i + 1n).label = AppTextFromCString(
            nativeRef(nativeAt(nativeAt(app.audio_custom_sounds, i).title, 0n)),
            AUDIO_LABEL_SIZE
        );
        i = i + 1n;
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y) + AppScale(10n)),
                width: float32(w),
                height: float32(AppScale(22n))
            },
            text: label,
            wrap: Wrap.TextWrapNone
        }}
    />;
    let control_y = nativeDeref(y) + AppScale(38n);
    let menu = Dropdown({
        session: CurrentApp().ui.session,
        props: {
            id: s32(820n) + cue,
            bounds: {
                x: float32(x),
                y: float32(control_y),
                width: float32(dropdown_w),
                height: float32(AppScale(36n))
            },
            selected_index: nativeAt(app.audio_cue_selected, cue)
        },
        options: nativeSlice(options, 0n, count)
    });
    if (menu.changed) {
        nativeSet(app.audio_cue_selected, cue, menu.selected_index);
        settings_audio_stop_preview(app);
        app_audio_reload_cue_sounds(app);
        app.settings_dirty = 1n;
        save_settings(app);
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: s32(830n) + cue,
                bounds: {
                    x: float32(x + dropdown_w + gap),
                    y: float32(control_y),
                    width: float32(play_w),
                    height: float32(AppScale(36n))
                },
                label: play_label,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: !NativePresent(app) || app.audio_ready === 0n
            }
        })
    ) {
        settings_audio_toggle_cue_preview(app, cue);
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                id: s32(840n) + cue,
                bounds: {
                    x: float32(x + w - import_w),
                    y: float32(control_y),
                    width: float32(import_w),
                    height: float32(AppScale(36n))
                },
                label: LocaleText("audio_import_sound_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        settings_audio_start_import(app, action, -1n);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(86n);
    settings_audio_draw_status(x, y, action);
}

export function draw_music_download(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app)) {
        return;
    }
    let installed = meditation_music_available(app);
    let download_label: string = "";
    if (installed !== 0n) {
        download_label = LocaleText("meditation_music_redownload_button");
    } else {
        download_label = LocaleText("meditation_music_download_button");
    }
    if (
        Button({
            session: CurrentApp().ui.session,
            props: {
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y) + AppScale(10n)),
                    width: float32(w),
                    height: float32(AppScale(36n))
                },
                label: download_label,
                tone: installed !== 0n ? ButtonTone.ButtonToneNeutral : ButtonTone.ButtonToneAccent,
                emphasis:
                    installed !== 0n
                        ? ButtonEmphasis.ButtonEmphasisSoft
                        : ButtonEmphasis.ButtonEmphasisFilled,
                disabled: false
            }
        })
    ) {
        meditation_music_start_download(app);
    }
    nativeDeref(y) = nativeDeref(y) + settings_audio_button_row_height();
    if (installed === 0n || app.meditation.music_download.status !== FileDownloadStatus.Idle) {
        if (app.meditation.music_download.status === FileDownloadStatus.Downloading) {
            let download_status = SettingsAudioNewDownloadStatus();
            meditation_music_format_download_status(
                nativeRef(nativeAt(download_status, 0n)),
                s32(download_status.count),
                nativeRef(app.meditation.music_download)
            );
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(x),
                        y: float32(nativeDeref(y)),
                        width: float32(w),
                        height: float32(AppScale(22n))
                    },
                    text: AppTextFromCString(nativeRef(nativeAt(download_status, 0n)), 96n),
                    wrap: Wrap.TextWrapNone
                }}
            />;
            nativeDeref(y) = nativeDeref(y) + AppScale(28n);
            meditation_music_draw_download_progress(app, x, nativeDeref(y), w);
            nativeDeref(y) = nativeDeref(y) + AppScale(22n);
        } else if (app.meditation.music_download.status === FileDownloadStatus.Error) {
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(x),
                        y: float32(nativeDeref(y)),
                        width: float32(w),
                        height: float32(AppScale(28n))
                    },
                    text: AppTextFromCString(
                        nativeRef(nativeAt(app.meditation.music_status, 0n)),
                        s32(app.meditation.music_status.count)
                    ),
                    wrap: Wrap.TextWrapNone
                }}
            />;
            nativeDeref(y) = nativeDeref(y) + AppScale(34n);
        }
    }
}

export function settings_audio_draw_music(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    let section = settings_section_begin(
        app,
        x,
        w,
        y,
        LocaleText("audio_music_title"),
        settings_audio_music_body(app)
    );
    let ix = section.inner_x;
    let iw = section.inner_width;
    let count = app_audio_music_count(app);
    app_audio_music_sanitize_selection(app);
    if (count > AUDIO_MUSIC_COUNT_MAX) {
        count = AUDIO_MUSIC_COUNT_MAX;
    }
    draw_music_download(app, ix, iw, y);
    draw_import_button(
        app,
        ix,
        iw,
        y,
        LocaleText("audio_import_music_button"),
        SETTINGS_AUDIO_ACTION_MUSIC,
        -1n
    );
    settings_row_divider(app, section, nativeDeref(y));
    settings_audio_subheading(ix, iw, y, LocaleText("audio_music_applied_title"));
    let assigned: s32 = s32(0n);
    let p: s32 = s32(0n);
    while (p < practice_count()) {
        let current = nativeAt(app.meditation.music_practice_tracks, p);
        if (current !== AUDIO_MUSIC_NONE && current >= 0n && current < count) {
            assigned = assigned + 1n;
            let action = settings_audio_list_row(
                app,
                s32(18300n) + p * 2n,
                ix,
                iw,
                y,
                settings_audio_practice_label(p),
                app_audio_music_label(app, current),
                settings_audio_preview_music_playing(current) !== 0n
            );
            if (action === 1n) {
                settings_audio_toggle_music_preview(app, current);
            }
            if (action === 2n) {
                settings_audio_stop_preview(app);
                nativeSet(app.meditation.music_practice_tracks, p, AUDIO_MUSIC_NONE);
                app.meditation.music_practice_mask = FlagIntersection(
                    app.meditation.music_practice_mask,
                    FlagComplement(FlagShiftLeft(s32(1n), p))
                );
                meditation_music_unload(app);
                app.settings_dirty = 1n;
                save_settings(app);
                return;
            }
        }
        p = p + 1n;
    }
    if (assigned === 0n) {
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(ix),
                    y: float32(nativeDeref(y)),
                    width: float32(iw),
                    height: float32(AppScale(22n))
                },
                text: LocaleText("audio_music_no_practices"),
                size: AppSmallFontSize(),
                wrap: Wrap.TextWrapNone
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + AppScale(30n);
    }
    let custom_count = settings_audio_clamp_count(
        app.audio_custom_music_count,
        AUDIO_CUSTOM_MUSIC_MAX
    );
    if (custom_count > 0n) {
        settings_row_divider(app, section, nativeDeref(y));
        settings_audio_subheading(ix, iw, y, LocaleText("audio_custom_music_title"));
        let i: s32 = s32(0n);
        while (i < custom_count) {
            let track_index = AUDIO_BUILTIN_MUSIC_COUNT + i;
            let action = settings_audio_list_row(
                app,
                s32(18400n) + i * 2n,
                ix,
                iw,
                y,
                AppTextFromCString(
                    nativeRef(nativeAt(nativeAt(app.audio_custom_music, i).title, 0n)),
                    AUDIO_LABEL_SIZE
                ),
                "",
                settings_audio_preview_music_playing(track_index) !== 0n
            );
            if (action === 1n) {
                settings_audio_toggle_music_preview(app, track_index);
            }
            if (action === 2n) {
                settings_audio_stop_preview(app);
                app_audio_remove_custom_music(app, i);
                app.settings_dirty = 1n;
                save_settings(app);
                return;
            }
            i = i + 1n;
        }
    }
    settings_section_end(y);
}
