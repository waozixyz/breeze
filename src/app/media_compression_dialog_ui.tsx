// Authored UI composition; native application state remains in media_compression_dialog.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSlider from "kryon/slider";
import * as State_media_compression_dialog from "media_compression_dialog";
import { app_close_modal } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { HostSeconds } from "host_clock";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { ImageFit } from "kryon/image_props";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Text } from "kryon/tsx/text";
import { Toast } from "kryon/tsx/toast";
import { LocaleText } from "locale";
import {
    MediaCompressionCountText,
    MediaCompressionInvalidate,
    MediaCompressionOpen,
    MediaCompressionRefresh,
    MediaCompressionScreen
} from "media_compression_dialog";
import { MediaCompressionOffer, MediaCompressionSetQuality } from "media_compression_settings";
import {
    MediaCompressionCommit,
    MediaCompressionNext,
    MediaCompressionStats
} from "media_compression_store";
import {
    MediaCompressionWorkCurrent,
    MediaCompressionWorkSuccessful
} from "media_compression_work";
import { AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { PackageFree } from "package_files";
import { AppRequestSmoothFrames } from "smooth_frames";
import { FrameTextReset } from "text_buffers";

export function MediaCompressionOfferDraw(app: NativeRef<InnerBreeze>): void {
    if (
        !MediaCompressionScreen(app) ||
        app.launcher_open ||
        app.modal.active !== 0n ||
        app.file_dialog_active !== 0n ||
        app.host_feature !== 0n
    ) {
        return;
    }
    MediaCompressionRefresh();
    let message: string = "";
    if (
        State_media_compression_dialog.media_compression_statistics.complete &&
        MediaCompressionOffer(
            State_media_compression_dialog.media_compression_statistics.review_count > 0n
        )
    ) {
        message = LocaleText("media_compression_offer");
    }
    let result = Toast({
        session: app.ui.session,
        props: {
            key: NativeLayout.KeyHash("media/compression/offer"),
            viewport: {
                x: 0.0,
                y: 0.0,
                width: float32(app.ui.view_width),
                height: float32(app.ui.view_height)
            },
            state: State_media_compression_dialog.media_compression_toast,
            message: message,
            action_label: LocaleText("media_compression_review"),
            seconds: 12.0,
            now_seconds: HostSeconds(),
            scale: MetricsScale()
        }
    });
    State_media_compression_dialog.media_compression_toast = result.state;
    if (result.visible) {
        AppRequestSmoothFrames(2n);
    }
    if (result.action_clicked) {
        State_media_compression_dialog.media_compression_toast = {};
        MediaCompressionOpen(app);
    }
}

export function MediaCompressionLine(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    text: string
): void {
    <Text
        session={app.ui.session}
        props={{ bounds: area, text: text, size: AppSmallFontSize(), wrap: Wrap.TextWrapAuto }}
    />;
}

export function MediaCompressionDialogDraw(app: NativeRef<InnerBreeze>): void {
    FrameTextReset(nativeRef(State_media_compression_dialog.media_compression_text));
    let width = AppScale(760n);
    if (width > app.ui.view_width - AppScale(24n)) {
        width = app.ui.view_width - AppScale(24n);
    }
    let height = AppScale(680n);
    if (height > app.ui.view_height - AppScale(24n)) {
        height = app.ui.view_height - AppScale(24n);
    }
    let frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("media/compression/dialog"),
        title: LocaleText("media_compression_title"),
        width: width,
        height: height,
        scale: MetricsScale(),
        has_right_action: true,
        right_label: LocaleText("close_button")
    });
    if (frame.dismissed || frame.right_clicked) {
        MediaCompressionInvalidate(app);
        app_close_modal(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let scroll = NativeScroll.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("media/compression/scroll"),
        bounds: frame.layout.content,
        content_height: AppScale(520n),
        scroll_offset: State_media_compression_dialog.media_compression_scroll
    });
    State_media_compression_dialog.media_compression_scroll = scroll.scroll_offset;
    if (scroll.opened) {
        MediaCompressionContent(app, scroll.content);
        End(app.ui.session);
    }
    End(app.ui.session);
}

export function MediaCompressionContent(app: NativeRef<InnerBreeze>, area: Rectangle): void {
    let x = area.x;
    let y = area.y;
    let w = area.width - float32(AppScale(10n));
    let line = float32(AppScale(32n));
    let stats = State_media_compression_dialog.media_compression_statistics;
    let quality = NativeSlider.DiscreteSlider(app.ui.session, {
        key: NativeLayout.KeyHash("media/compression/quality"),
        bounds: { x: x, y: y, width: w, height: line * 2.0 },
        label: LocaleText("media_compression_quality"),
        value_text: MediaCompressionCountText(
            "media_compression_quality",
            State_media_compression_dialog.media_compression_quality
        ),
        value: State_media_compression_dialog.media_compression_quality,
        min: 1n,
        max: 100n
    });
    if (quality.changed) {
        State_media_compression_dialog.media_compression_quality = quality.value;
        MediaCompressionSetQuality(quality.value);
        State_media_compression_dialog.media_compression_notice = "";
        MediaCompressionInvalidate(app);
    }
    y = y + line * 2.0;
    let half = (w - float32(AppScale(12n))) / 2.0;
    let work = State_media_compression_dialog.media_compression_work;
    let ready =
        MediaCompressionWorkCurrent(
            work,
            State_media_compression_dialog.media_compression_owner,
            State_media_compression_dialog.media_compression_hash,
            State_media_compression_dialog.media_compression_generation
        ) &&
        MediaCompressionWorkSuccessful(work) &&
        State_media_compression_dialog.media_compression_uploaded &&
        State_media_compression_dialog.media_compression_before.id !== 0n &&
        State_media_compression_dialog.media_compression_after.id !== 0n;
    let before_label = LocaleText("media_compression_before");
    let after_label = LocaleText("media_compression_after");
    if (ready) {
        before_label = MediaCompressionCountText(
            "media_compression_before",
            work.source.count,
            true
        );
        after_label = MediaCompressionCountText(
            "media_compression_after",
            work.encoded.data.count,
            true
        );
    }
    MediaCompressionLine(app, { x: x, y: y, width: half, height: line }, before_label);
    MediaCompressionLine(
        app,
        { x: x + half + float32(AppScale(12n)), y: y, width: half, height: line },
        after_label
    );
    y = y + line;
    let image_height = float32(AppScale(180n));
    <Image
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("media/compression/original"),
            bounds: { x: x, y: y, width: half, height: image_height },
            texture: State_media_compression_dialog.media_compression_before,
            alt_text: before_label,
            fit: ImageFit.ImageFitContain,
            smooth: true
        }}
    />;
    <Image
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("media/compression/encoded"),
            bounds: {
                x: x + half + float32(AppScale(12n)),
                y: y,
                width: half,
                height: image_height
            },
            texture: State_media_compression_dialog.media_compression_after,
            alt_text: after_label,
            fit: ImageFit.ImageFitContain,
            smooth: true
        }}
    />;
    y = y + (image_height + float32(AppScale(8n)));
    if (ready) {
        MediaCompressionLine(
            app,
            { x: x, y: y, width: w, height: line },
            MediaCompressionCountText(
                "media_compression_saving",
                work.source.count - work.encoded.data.count,
                true
            )
        );
    }
    y = y + line;
    let apply = Button({
        session: app.ui.session,
        props: {
            key: NativeLayout.KeyHash("media/compression/apply"),
            bounds: { x: x, y: y, width: half, height: float32(AppScale(44n)) },
            label: LocaleText("media_compression_apply"),
            disabled: !ready || work.encoded.data.count >= work.source.count,
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled
        }
    });
    if (apply && ready) {
        if (
            MediaCompressionCommit(
                work.owner,
                work.hash,
                work.source,
                work.encoded.data,
                work.quality
            )
        ) {
            let next = MediaCompressionNext(State_media_compression_dialog.media_compression_hash);
            State_media_compression_dialog.media_compression_notice = "media_compression_applied";
            State_media_compression_dialog.media_compression_statistics = MediaCompressionStats();
            MediaCompressionInvalidate(app);
            PackageFree(State_media_compression_dialog.media_compression_hash);
            State_media_compression_dialog.media_compression_hash = next;
        } else {
            State_media_compression_dialog.media_compression_notice = "media_compression_failed";
        }
    }
    if (
        Button({
            session: app.ui.session,
            props: {
                key: NativeLayout.KeyHash("media/compression/next"),
                bounds: {
                    x: x + half + float32(AppScale(12n)),
                    y: y,
                    width: half,
                    height: float32(AppScale(44n))
                },
                label: LocaleText("media_compression_next"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        let next = MediaCompressionNext(State_media_compression_dialog.media_compression_hash);
        MediaCompressionInvalidate(app);
        PackageFree(State_media_compression_dialog.media_compression_hash);
        State_media_compression_dialog.media_compression_hash = next;
        State_media_compression_dialog.media_compression_notice = "";
    }
    y = y + float32(AppScale(52n));
    let notice = State_media_compression_dialog.media_compression_notice;
    if (notice.count === 0n && State_media_compression_dialog.media_compression_hash.count === 0n) {
        notice = "media_compression_empty";
    }
    if (notice.count > 0n) {
        MediaCompressionLine(app, { x: x, y: y, width: w, height: line * 2.0 }, LocaleText(notice));
    }
}
