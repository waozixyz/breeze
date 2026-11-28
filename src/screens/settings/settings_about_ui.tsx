import { SettingsAboutNewProgressText } from "settings_about";
import { SettingsAboutNewTitleText } from "settings_about";
import { SettingsAboutNewRow } from "settings_about";
// Authored UI composition; native application state remains in settings_about.zi.
import { LauncherAppPackage } from "app_launcher_apps";
import { app_nav_route_label } from "app_nav_state";
import { InnerBreeze } from "app_types";
import { CurrentApp } from "current_app";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { ParagraphSpec } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { OpenUri } from "kryon/open_uri";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Link } from "kryon/tsx/link";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import { LauncherRoutes } from "launcher_policy";
import { LocaleText } from "locale";
import { AppFontSize, AppParagraphHeight, AppScale, AppTextWidth, AppTitleFontSize } from "metrics";
import {
    PackageAutomaticEnabled,
    PackageRootPending,
    PackageSetAutomatic,
    PackageUpdatesPossible,
    PackageVersion
} from "package_manager";
import {
    ABOUT_SOCIAL_TELEGRAM,
    about_link_icon_columns,
    about_link_icons_height,
    about_route_installed,
    about_social_icon_alt,
    about_social_icon_asset,
    update_action_label_native,
    update_available,
    update_can_self_update,
    update_download_fraction,
    update_download_url_native,
    update_error_text_native,
    update_host_text,
    update_is_downloading,
    update_row_action,
    update_row_text_native
} from "settings_about";
import { draw_toggle_row } from "settings_ui_ui";
import { TelegramIconShape } from "telegram_icon";
import {
    AppCopyText,
    AppTextFromCString,
    FormatArg,
    FormatTemplate,
    FrameTextHold
} from "text_buffers";
import { VersionString } from "version";

export function about_package_row(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>,
    label: string,
    version: string
): void {
    let row = SettingsAboutNewRow();
    let row_args: [FormatArg, FormatArg] = [
        { text: label, is_text: true },
        { text: version, is_text: true }
    ];
    FormatTemplate("%s · %s", nativeSlice(row_args), nativeSlice(row));
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(w),
                height: float32(AppScale(28n))
            },
            text: FrameTextHold(
                nativeRef(app.ui.frame_text),
                AppTextFromCString(nativeRef(nativeAt(row, 0n)), 128n)
            ),
            size: AppFontSize()
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(28n);
}

export function about_draw_package_updates(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    if (!PackageUpdatesPossible()) {
        return;
    }
    let allowed: s32 = PackageAutomaticEnabled() ? 1n : 0n;
    if (draw_toggle_row(app, x, w, y, LocaleText("package_updates_setting"), nativeRef(allowed))) {
        PackageSetAutomatic(allowed !== 0n);
    }
    let note = LocaleText("package_updates_note");
    let note_h = AppParagraphHeight(note, w, AppFontSize(), AppScale(4n));
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(w),
                height: float32(note_h)
            },
            text: note,
            size: AppFontSize(),
            wrap: Wrap.TextWrapAuto
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + (note_h + AppScale(20n));
}

export function about_draw_link_icons(
    app: NativeRef<InnerBreeze>,
    content_x: s32,
    content_w: s32,
    y: NativeRef<s32>
): void {
    let link_count: s32 = s32(3n);
    let icon_size: s32 = AppScale(32n);
    let icon_padding: s32 = AppScale(4n);
    let icon_spacing: s32 = AppScale(20n);
    let icon_btn_w: s32 = icon_size + icon_padding * 2n;
    let columns: s32 = about_link_icon_columns(content_w);
    let grid_w: s32 = icon_btn_w * columns + icon_spacing * (columns - 1n);
    let links_start_x: s32 = content_x + (content_w - grid_w) / 2n;
    let row_spacing: s32 = AppScale(16n);
    let urls: [string, string, string] = [
        "https://discord.com/invite/JbGZ4yENDt",
        "https://t.me/lotusinbe",
        "https://github.com/waozixyz/breathing"
    ];
    {
        let i: s32 = s32(0n);
        while (i < link_count) {
            let col: s32 = i % columns;
            let row: s32 = i / columns;
            let button_x: s32 = links_start_x + col * (icon_btn_w + icon_spacing);
            let button_y: s32 = nativeDeref(y) + row * (icon_btn_w + row_spacing);
            if (
                Button({
                    session: CurrentApp().ui.session,
                    props: {
                        bounds: {
                            x: float32(button_x),
                            y: float32(button_y),
                            width: float32(icon_btn_w),
                            height: float32(icon_btn_w)
                        },
                        id: s32(18100n) + i,
                        label: about_social_icon_alt(i),
                        icon_only: true,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }
                })
            ) {
                OpenUri(nativeAt(urls, i));
            }
            let icon_bounds: Rectangle = {
                x: float32(button_x + icon_padding),
                y: float32(button_y + icon_padding),
                width: float32(icon_size),
                height: float32(icon_size)
            };
            if (i === ABOUT_SOCIAL_TELEGRAM) {
                <SvgIcon
                    session={CurrentApp().ui.session}
                    props={{
                        bounds: icon_bounds,
                        shape: TelegramIconShape,
                        color: { r: 38n, g: 165n, b: 228n, a: 255n }
                    }}
                />;
            } else {
                <Image
                    session={CurrentApp().ui.session}
                    props={{
                        asset_path: about_social_icon_asset(app, i),
                        alt_text: about_social_icon_alt(i),
                        bounds: icon_bounds
                    }}
                />;
            }
            i = i + 1n;
        }
    }
    nativeDeref(y) = nativeDeref(y) + about_link_icons_height(content_w);
}

export function settings_about_draw(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    let font = AppFontSize();
    let description: ParagraphSpec = {};
    {
        let title_text = SettingsAboutNewTitleText();
        let title_args: [FormatArg, FormatArg] = [
            { text: LocaleText("app_title"), is_text: true },
            { text: VersionString, is_text: true }
        ];
        FormatTemplate("%s · v%s", nativeSlice(title_args), nativeSlice(title_text));
        let title = FrameTextHold(
            nativeRef(app.ui.frame_text),
            AppTextFromCString(nativeRef(nativeAt(title_text, 0n)), s32(title_text.count))
        );
        let title_font = AppTitleFontSize(title, w);
        let logo_size = AppScale(56n);
        let text_w: s32 = s32(0n);
        nativeDeref(y) = nativeDeref(y) + AppScale(16n);
        <Image
            session={CurrentApp().ui.session}
            props={{
                asset_path: "assets/app/icon.webp",
                alt_text: "Inner Breeze",
                bounds: {
                    x: float32(x + (w - logo_size) / 2n),
                    y: float32(nativeDeref(y)),
                    width: float32(logo_size),
                    height: float32(logo_size)
                }
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + (logo_size + AppScale(12n));
        text_w = AppTextWidth(title, title_font);
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(x + (w - text_w) / 2n),
                    y: float32(nativeDeref(y)),
                    width: 0n,
                    height: 0n
                },
                text: title,
                size: title_font,
                wrap: Wrap.TextWrapNone
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + AppScale(34n);
    }
    if (PackageRootPending()) {
        <Text
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: float32(w),
                    height: float32(AppScale(28n))
                },
                text: LocaleText("update_restart"),
                size: font
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + AppScale(28n);
    }
    about_package_row(app, x, w, y, "Core", PackageVersion(0n));
    let routes = LauncherRoutes();
    for (const route of routes) {
        if (!about_route_installed(app, route)) {
            continue;
        }
        let index = LauncherAppPackage(route);
        about_package_row(app, x, w, y, app_nav_route_label(route), PackageVersion(index));
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(20n);
    about_draw_package_updates(app, x, w, y);
    if (update_available() !== 0n) {
        if (update_can_self_update() !== 0n) {
            <Text
                session={CurrentApp().ui.session}
                props={{
                    bounds: {
                        x: float32(x),
                        y: float32(nativeDeref(y)),
                        width: 0n,
                        height: 0n
                    },
                    text: update_host_text(update_row_text_native()),
                    wrap: Wrap.TextWrapNone
                }}
            />;
            nativeDeref(y) = nativeDeref(y) + AppScale(26n);
            if (update_is_downloading() !== 0n) {
                let fraction = update_download_fraction();
                let progress: s32 = fraction >= 0.0 ? s32(fraction * 100.0 + 0.5) : -1n;
                let progress_text = SettingsAboutNewProgressText();
                if (progress >= 0n) {
                    let progress_args: [FormatArg, FormatArg] = [
                        { text: LocaleText("update_downloading"), is_text: true },
                        { number: progress }
                    ];
                    FormatTemplate(
                        "%s %d%%",
                        nativeSlice(progress_args),
                        nativeSlice(progress_text)
                    );
                } else {
                    AppCopyText(LocaleText("update_downloading"), nativeSlice(progress_text));
                }
                <Text
                    session={CurrentApp().ui.session}
                    props={{
                        bounds: {
                            x: float32(x),
                            y: float32(nativeDeref(y)),
                            width: 0n,
                            height: 0n
                        },
                        text: AppTextFromCString(
                            nativeRef(nativeAt(progress_text, 0n)),
                            s32(progress_text.count)
                        ),
                        wrap: Wrap.TextWrapNone
                    }}
                />;
                nativeDeref(y) = nativeDeref(y) + AppScale(22n);
            } else {
                if (
                    Button({
                        session: CurrentApp().ui.session,
                        props: {
                            id: 18420n,
                            bounds: {
                                x: float32(x),
                                y: float32(nativeDeref(y)),
                                width: float32(w),
                                height: float32(AppScale(36n))
                            },
                            label: update_host_text(update_action_label_native()),
                            tone: ButtonTone.ButtonToneNeutral,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                            full_width: true
                        }
                    })
                ) {
                    update_row_action();
                }
                nativeDeref(y) = nativeDeref(y) + AppScale(36n);
            }
            let error_text = update_host_text(update_error_text_native());
            if (error_text.count !== 0n) {
                <Text
                    session={CurrentApp().ui.session}
                    props={{
                        bounds: {
                            x: float32(x),
                            y: float32(nativeDeref(y)),
                            width: 0n,
                            height: 0n
                        },
                        text: error_text,
                        wrap: Wrap.TextWrapNone
                    }}
                />;
                nativeDeref(y) = nativeDeref(y) + AppScale(20n);
            }
        } else {
            let update_text = update_host_text(update_row_text_native());
            let update_w = AppTextWidth(update_text, font);
            let link_result = Link({
                session: CurrentApp().ui.session,
                props: {
                    bounds: {
                        x: float32(x + (w - update_w) / 2n),
                        y: float32(nativeDeref(y)),
                        width: float32(update_w),
                        height: float32(AppScale(24n))
                    },
                    text: update_text,
                    link: update_host_text(update_download_url_native()),
                    focus_id: 18421n
                }
            });
            if (link_result.open_url) {
                OpenUri(link_result.url);
            }
            nativeDeref(y) = nativeDeref(y) + AppScale(30n);
        }
        nativeDeref(y) = nativeDeref(y) + AppScale(8n);
    }
    description = { text: LocaleText("about_text"), width: w, font: font, line_gap: AppScale(4n) };
    let description_h = AppParagraphHeight(
        description.text,
        description.width,
        description.font,
        description.line_gap
    );
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(w),
                height: float32(description_h)
            },
            text: description.text,
            wrap: Wrap.TextWrapAuto,
            align: TextAlign.TextAlignCenter
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + description_h;
    nativeDeref(y) = nativeDeref(y) + AppScale(18n);
    about_draw_link_icons(app, x, w, y);
    nativeDeref(y) = nativeDeref(y) + AppScale(32n);
}
