// Authored UI composition; native application state remains in profile_node_storage.zi.
import * as NativeText from "kryon/text";
import * as NativeToggle from "kryon/toggle";
import { app_sync_loading } from "app_sync";
import { InnerBreeze } from "app_types";
import { PackageFree } from "package_files";
import { color_with_alpha } from "color";
import { CssClass } from "css/Css";
import { DarkenColor, StyleTokenColor } from "kryon/drawing_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import { Toggle } from "kryon/tsx/toggle";
import { LocaleText } from "locale";
import { AppFontSize, AppParagraphHeight, AppScale, AppSmallFontSize, AppTextWidth } from "metrics";
import {
    ProfileNodeCard,
    ProfileNodeCardFor,
    ProfileNodeStorageActive,
    ProfileNodeStorageAddress,
    ProfileNodeStorageBarColor,
    ProfileNodeStoragePad,
    ProfileNodeStorageSetMedia,
    ProfileNodeStorageVisible
} from "profile_node_storage";

import { NativePresent } from "native_flags";
import { SyncMediaLocalBytes, SyncNodeStoragePercent } from "sync_node_storage";
import { SyncNodeCount } from "sync_nodes";

function ProfileNodeStorageText(
    app: NativeRef<InnerBreeze>,
    text: string,
    x: s32,
    y: s32,
    width: s32,
    height: s32,
    font: s32,
    class_name: string,
    align: TextAlign
): void {
    let props: NativeText.Props = {};
    props.text = text;
    props.size = font;
    props.wrap = Wrap.TextWrapAuto;
    props.align = align;
    props.bounds = { x: float32(x), y: float32(y), width: float32(width), height: float32(height) };
    if (class_name.count > 0n) {
        props.class_name = CssClass(class_name);
    }
    <Text session={app.ui.session} props={props} />;
}

function ProfileDrawNodeCard(
    app: NativeRef<InnerBreeze>,
    index: s32,
    address: string,
    card: ProfileNodeCard,
    x: s32,
    y: s32,
    width: s32
): void {
    let pad = ProfileNodeStoragePad();
    let inner = width - pad * 2n;
    let small = AppSmallFontSize();
    <Box
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32(y),
                width: float32(width),
                height: float32(card.height)
            },
            fill: DarkenColor(StyleTokenColor("canvas"), 7n),
            radius: float32(AppScale(12n))
        }}
    />;
    let left = x + pad;
    let top = y + pad;
    let badge_w: s32 = s32(0n);
    if (card.active) {
        let badge = LocaleText("profile_node_storage_active");
        badge_w = AppTextWidth(badge, small) + AppScale(16n);
        <Box
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(left + inner - badge_w),
                    y: float32(top + AppScale(2n)),
                    width: float32(badge_w),
                    height: float32(AppScale(22n))
                },
                fill: color_with_alpha(StyleTokenColor("accent"), 0.22),
                radius: float32(AppScale(11n))
            }}
        />;
        ProfileNodeStorageText(
            app,
            badge,
            left + inner - badge_w,
            top + AppScale(2n),
            badge_w,
            AppScale(22n),
            small,
            "",
            TextAlign.TextAlignCenter
        );
    }
    let name_props: NativeText.Props = {};
    name_props.text = card.name;
    name_props.size = AppFontSize();
    name_props.wrap = Wrap.TextWrapNone;
    name_props.bounds = {
        x: float32(left),
        y: float32(top),
        width: float32(inner - badge_w - AppScale(8n)),
        height: float32(AppScale(26n))
    };
    <Text session={app.ui.session} props={name_props} />;
    top = top + AppScale(28n);
    let storage = card.storage;
    if (storage.known && storage.limit_bytes > 0n) {
        let bar_h = AppScale(8n);
        <Box
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(left),
                    y: float32(top),
                    width: float32(inner),
                    height: float32(bar_h)
                },
                fill: DarkenColor(StyleTokenColor("canvas"), 18n),
                radius: float32(bar_h) / 2.0
            }}
        />;
        let fill_w = s32((s64(inner) * s64(SyncNodeStoragePercent(storage))) / 100n);
        if (storage.used_bytes > 0n && fill_w < bar_h) {
            fill_w = bar_h;
        }
        if (fill_w > 0n) {
            <Box
                session={app.ui.session}
                props={{
                    bounds: {
                        x: float32(left),
                        y: float32(top),
                        width: float32(fill_w),
                        height: float32(bar_h)
                    },
                    fill: ProfileNodeStorageBarColor(card),
                    radius: float32(bar_h) / 2.0
                }}
            />;
        }
        top = top + AppScale(18n);
    }
    let usage_h = AppParagraphHeight(card.usage, inner - AppScale(48n), small, 0n);
    ProfileNodeStorageText(
        app,
        card.usage,
        left,
        top,
        inner - AppScale(48n),
        usage_h,
        small,
        storage.known ? "" : "storage-detail",
        TextAlign.TextAlignStart
    );
    if (card.percent.count > 0n) {
        ProfileNodeStorageText(
            app,
            card.percent,
            left + inner - AppScale(48n),
            top,
            AppScale(48n),
            usage_h,
            small,
            card.status_class,
            TextAlign.TextAlignEnd
        );
    }
    top = top + (usage_h + AppScale(6n));
    if (card.status.count > 0n) {
        let status_h = AppParagraphHeight(card.status, inner, small, 0n);
        ProfileNodeStorageText(
            app,
            card.status,
            left,
            top,
            inner,
            status_h,
            small,
            card.status_class,
            TextAlign.TextAlignStart
        );
        top = top + (status_h + AppScale(6n));
    }
    if (card.photos.count > 0n) {
        let photos_h = AppParagraphHeight(card.photos, inner, small, 0n);
        ProfileNodeStorageText(
            app,
            card.photos,
            left,
            top,
            inner,
            photos_h,
            small,
            "storage-detail",
            TextAlign.TextAlignStart
        );
        top = top + (photos_h + AppScale(6n));
    }
    top = top + AppScale(6n);
    <Box
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(left),
                y: float32(top),
                width: float32(inner),
                height: float32(AppScale(1n))
            },
            fill: color_with_alpha(StyleTokenColor("text"), 0.1)
        }}
    />;
    top = top + AppScale(6n);
    let toggle_w = AppScale(50n);
    let toggle_h = AppScale(28n);
    let media_changed = false;
    let media_value = card.media;
    {
        let label = LocaleText("profile_node_storage_media");
        let label_props: NativeText.Props = {};
        label_props.text = label;
        label_props.size = AppFontSize();
        label_props.wrap = Wrap.TextWrapAuto;
        label_props.vertical_align = TextAlign.TextAlignCenter;
        label_props.bounds = {
            x: float32(left),
            y: float32(top),
            width: float32(inner - toggle_w - AppScale(12n)),
            height: float32(AppScale(44n))
        };
        <Text session={app.ui.session} props={label_props} />;
        let toggle: NativeToggle.Props = {};
        toggle.id = 63000n + index;
        toggle.bounds = {
            x: float32(left + inner - toggle_w),
            y: float32(top + (AppScale(44n) - toggle_h) / 2n),
            width: float32(toggle_w),
            height: float32(toggle_h)
        };
        toggle.value = card.media;
        toggle.label = label;
        toggle.disabled = app_sync_loading() !== 0n;
        let result = Toggle({ session: app.ui.session, props: toggle });
        media_changed = result.changed;
        media_value = result.value;
    }
    if (media_changed) {
        ProfileNodeStorageSetMedia(app, address, media_value, card.active);
    }
    top = top + AppScale(44n);
    let hint = LocaleText(
        card.media ? "profile_node_storage_media_on" : "profile_node_storage_media_off"
    );
    ProfileNodeStorageText(
        app,
        hint,
        left,
        top,
        inner,
        AppParagraphHeight(hint, inner, small, 0n),
        small,
        "storage-detail",
        TextAlign.TextAlignStart
    );
}

export function ProfileNodeStorageView(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app) || !NativePresent(y) || !ProfileNodeStorageVisible()) {
        return;
    }
    <Text
        session={app.ui.session}
        props={{
            text: LocaleText("profile_node_storage_title"),
            size: AppFontSize(),
            wrap: Wrap.TextWrapNone,
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(26n))
            }
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(30n);
    {
        const hint = LocaleText("profile_node_storage_hint");
        const small = AppSmallFontSize();
        const hintHeight = AppParagraphHeight(hint, width, small, 0n);
        ProfileNodeStorageText(
            app,
            hint,
            x,
            nativeDeref(y),
            width,
            hintHeight,
            small,
            "storage-detail",
            TextAlign.TextAlignStart
        );
        nativeDeref(y) = nativeDeref(y) + hintHeight + AppScale(10n);
    }
    const active = ProfileNodeStorageActive();
    const mediaBytes = SyncMediaLocalBytes();
    const count = SyncNodeCount();
    for (let index: s32 = s32(0n); index < count; index += 1n) {
        const address = ProfileNodeStorageAddress(index);
        const card = ProfileNodeCardFor(app, address, active, mediaBytes, width, true);
        ProfileDrawNodeCard(app, index, address, card, x, nativeDeref(y), width);
        PackageFree(address);
        nativeDeref(y) = nativeDeref(y) + card.height + AppScale(10n);
    }
    PackageFree(active);
    nativeDeref(y) = nativeDeref(y) + AppScale(8n);
}
