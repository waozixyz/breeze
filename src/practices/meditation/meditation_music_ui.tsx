import { MeditationMusicNewTrackOptions } from "meditation_music";
import { MeditationMusicNewDownloadStatus } from "meditation_music";
// Authored UI composition; native application state remains in meditation_music.zi.
import {
    AUDIO_BUILTIN_MUSIC_COUNT,
    AUDIO_MUSIC_COUNT_MAX,
    AUDIO_MUSIC_NONE,
    InnerBreeze
} from "app_types";
import { app_audio_music_count } from "audio_selection";
import { CurrentApp } from "current_app";
import { ExerciseType, practice_clamp_id } from "exercise_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { DarkenColor, LightenColor, StyleTokenColor } from "kryon/drawing_props";
import { FileDownload, FileDownloadStatus } from "kryon/file_download";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    attribution_paragraph,
    meditation_music_format_download_status,
    meditation_music_start_download,
    meditation_music_track_installed,
    meditation_music_unload,
    sanitize_practice_music,
    save_settings,
    test_track
} from "meditation_music";
import { AppFontSize, AppParagraphHeight, AppScale, AppTextWidth } from "metrics";
import { app_audio_music_label } from "music_library";
import {
    FlagComplement,
    FlagIntersection,
    FlagShiftLeft,
    FlagUnion,
    NativePresent
} from "native_flags";
import { AppTextFromCString } from "text_buffers";

export function meditation_music_draw_download_progressView(
    app: NativeRef<InnerBreeze>,
    x: s32,
    y: s32,
    w: s32
): void {
    let download: NativeRef<FileDownload> = nativeRef(app.meditation.music_download);
    let bar_h = AppScale(10n);
    let fill_w: s32 = s32(0n);
    let bg = StyleTokenColor("canvas");
    let button = StyleTokenColor("accent");
    if (!NativePresent(app) || w <= 0n) {
        return;
    }
    download = nativeRef(app.meditation.music_download);
    if (download.status !== FileDownloadStatus.Downloading) {
        return;
    }
    if (download.total_bytes > 0n) {
        fill_w = s32((s64(download.bytes) * s64(w)) / s64(download.total_bytes));
    }
    if (fill_w < 0n) {
        fill_w = 0n;
    }
    if (fill_w > w) {
        fill_w = w;
    }
    let session = app.ui.session;
    <Box
        session={session}
        props={{
            bounds: { x: float32(x), y: float32(y), width: float32(w), height: float32(bar_h) },
            fill: DarkenColor(bg, 28n)
        }}
    />;
    let dark = DarkenColor(bg, 55n);
    let light = LightenColor(bg, 35n);
    let left = float32(x);
    let top = float32(y);
    let right = float32(x + w - 1n);
    let bottom = float32(y + bar_h - 1n);
    <Shape
        session={session}
        props={{ start: { x: left, y: top }, end: { x: right, y: top }, color: light }}
    />;
    <Shape
        session={session}
        props={{ start: { x: left, y: top }, end: { x: left, y: bottom }, color: light }}
    />;
    <Shape
        session={session}
        props={{ start: { x: left, y: bottom }, end: { x: right, y: bottom }, color: dark }}
    />;
    <Shape
        session={session}
        props={{ start: { x: right, y: top }, end: { x: right, y: bottom }, color: dark }}
    />;
    if (fill_w > 0n) {
        let inner_w = fill_w - AppScale(4n);
        if (inner_w < AppScale(2n)) {
            inner_w = AppScale(2n);
        }
        <Box
            session={session}
            props={{
                bounds: {
                    x: float32(x + AppScale(2n)),
                    y: float32(y + AppScale(2n)),
                    width: float32(inner_w),
                    height: float32(bar_h - AppScale(4n))
                },
                fill: button
            }}
        />;
    }
}

export function draw_attributionView(content_x: s32, content_w: s32, y: NativeRef<s32>): void {
    if (!NativePresent(y) || content_w <= 0n) {
        return;
    }
    let paragraph = attribution_paragraph(content_w);
    let height = AppParagraphHeight(
        paragraph.text,
        paragraph.width,
        paragraph.font,
        paragraph.line_gap
    );
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(content_x),
                y: float32(nativeDeref(y)),
                width: float32(content_w),
                height: float32(height)
            },
            text: paragraph.text,
            size: paragraph.font,
            wrap: Wrap.TextWrapAuto
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + height;
}

export function meditation_music_draw_practice_settingsView(
    app: NativeRef<InnerBreeze>,
    practice: s32,
    content_x: s32,
    content_w: s32,
    y: NativeRef<s32>,
    show_installed_download: s32,
    show_status: s32
): void {
    let button_h = AppScale(48n);
    let button_w: s32 = s32(0);
    let installed: s32 = s32(0);
    let selected_track: s32 = s32(0);
    let selection: s32 = s32(0);
    let test_label: string = "";
    let download_status = MeditationMusicNewDownloadStatus();
    let track_options = MeditationMusicNewTrackOptions();
    let track_count: s32 = s32(0);
    if (!NativePresent(app) || !NativePresent(y)) {
        return;
    }
    sanitize_practice_music(app);
    practice = practice_clamp_id(practice);
    selected_track = nativeAt(app.meditation.music_practice_tracks, practice);
    if (selected_track < 0n) {
        selected_track = AUDIO_MUSIC_NONE;
        nativeSet(app.meditation.music_practice_tracks, practice, AUDIO_MUSIC_NONE);
        app.meditation.music_practice_mask = FlagIntersection(
            app.meditation.music_practice_mask,
            FlagComplement(FlagShiftLeft(s32(1n), practice))
        );
    } else {
        app.meditation.music_practice_mask = FlagUnion(
            app.meditation.music_practice_mask,
            FlagShiftLeft(s32(1n), practice)
        );
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(content_x),
                y: float32(nativeDeref(y)),
                width: 0n,
                height: 0n
            },
            text: LocaleText(
                practice === s32(ExerciseType.EXERCISE_SUN_SALUTATION)
                    ? "sun_salutation_music_track_label"
                    : "practice_background_music_label"
            ),
            wrap: Wrap.TextWrapNone
        }}
    />;
    track_count = app_audio_music_count(app);
    if (track_count > AUDIO_MUSIC_COUNT_MAX) {
        track_count = AUDIO_MUSIC_COUNT_MAX;
    }
    nativeSet(track_options, 0n, { label: LocaleText("audio_music_none_option") });
    {
        let i: s32 = s32(0n);
        while (i < track_count) {
            nativeSet(track_options, i + 1n, { label: app_audio_music_label(app, i) });
            i = i + 1n;
        }
    }
    selection = selected_track === AUDIO_MUSIC_NONE ? 0n : selected_track + 1n;
    if (selection < 0n || selection > track_count) {
        selection = 0n;
    }
    let dropdown_pick = Dropdown({
        session: CurrentApp().ui.session,
        props: {
            id: s32(451n) + practice,
            bounds: {
                x: float32(content_x),
                y: float32(nativeDeref(y) + AppScale(26n)),
                width: float32(content_w),
                height: float32(AppScale(48n))
            },
            selected_index: selection
        },
        options: nativeSlice(track_options, 0n, track_count + 1n)
    });
    if (dropdown_pick.changed) {
        selection = dropdown_pick.selected_index;
        if (selection <= 0n) {
            nativeSet(app.meditation.music_practice_tracks, practice, AUDIO_MUSIC_NONE);
            app.meditation.music_practice_mask = FlagIntersection(
                app.meditation.music_practice_mask,
                FlagComplement(FlagShiftLeft(s32(1n), practice))
            );
        } else {
            nativeSet(app.meditation.music_practice_tracks, practice, selection - 1n);
            app.meditation.music_practice_mask = FlagUnion(
                app.meditation.music_practice_mask,
                FlagShiftLeft(s32(1n), practice)
            );
            app.meditation.music_track = nativeAt(app.meditation.music_practice_tracks, practice);
        }
        app.settings_dirty = 1n;
        meditation_music_unload(app);
        save_settings(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(90n);
    selected_track = nativeAt(app.meditation.music_practice_tracks, practice);
    if (selected_track === AUDIO_MUSIC_NONE) {
        return;
    }
    installed = meditation_music_track_installed(app, selected_track);
    let built_in = selected_track < AUDIO_BUILTIN_MUSIC_COUNT;
    if (installed !== 0n) {
        if (app.meditation.music_playing !== 0n) {
            test_label = LocaleText("meditation_music_stop_test_button");
        } else {
            test_label = LocaleText("meditation_music_test_button");
        }
        button_w = AppTextWidth(test_label, AppFontSize()) + AppScale(24n);
        if (button_w > content_w) {
            button_w = content_w;
        }
        if (
            Button({
                session: CurrentApp().ui.session,
                props: {
                    bounds: {
                        x: float32(content_x),
                        y: float32(nativeDeref(y)),
                        width: float32(button_w),
                        height: float32(button_h)
                    },
                    label: test_label,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: false
                }
            })
        ) {
            app.meditation.music_track = nativeAt(app.meditation.music_practice_tracks, practice);
            test_track(app);
        }
        nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(12n));
    }
    if (built_in && (installed === 0n || show_installed_download !== 0n)) {
        let download_label: string = "";
        if (installed !== 0n) {
            download_label = LocaleText("meditation_music_redownload_button");
        } else {
            download_label = LocaleText("meditation_music_download_button");
        }
        button_w = AppTextWidth(download_label, AppFontSize()) + AppScale(24n);
        if (button_w > content_w) {
            button_w = content_w;
        }
        if (
            Button({
                session: CurrentApp().ui.session,
                props: {
                    bounds: {
                        x: float32(content_x),
                        y: float32(nativeDeref(y)),
                        width: float32(button_w),
                        height: float32(button_h)
                    },
                    label: download_label,
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                    disabled: false
                }
            })
        ) {
            meditation_music_start_download(app);
        }
        nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(12n));
    }
    if (
        show_status !== 0n &&
        (installed === 0n || app.meditation.music_download.status !== FileDownloadStatus.Idle)
    ) {
        if (app.meditation.music_download.status === FileDownloadStatus.Downloading) {
            meditation_music_format_download_status(
                nativeRef(nativeAt(download_status, 0n)),
                s32(download_status.count),
                nativeRef(app.meditation.music_download)
            );
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(content_x),
                        y: float32(nativeDeref(y)),
                        width: 0n,
                        height: 0n
                    },
                    text: AppTextFromCString(
                        nativeRef(nativeAt(download_status, 0n)),
                        s32(download_status.count)
                    ),
                    wrap: Wrap.TextWrapNone
                }}
            />;
            nativeDeref(y) = nativeDeref(y) + AppScale(28n);
            meditation_music_draw_download_progressView(app, content_x, nativeDeref(y), content_w);
            nativeDeref(y) = nativeDeref(y) + AppScale(22n);
        } else {
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(content_x),
                        y: float32(nativeDeref(y)),
                        width: 0n,
                        height: 0n
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
    draw_attributionView(content_x, content_w, y);
    nativeDeref(y) = nativeDeref(y) + AppScale(10n);
}
