import { ArrowDirection } from "kryon/button";
// Authored UI composition; native application state remains in widgets.zi.
import * as NativeButton from "kryon/button";
import * as NativeImage from "kryon/image";
import * as NativeOverlay from "kryon/overlay";
import * as NativeText from "kryon/text";
import * as NativeToolbar from "kryon/toolbar";
import * as State_widgets from "widgets";
import { ActionIcon, GuideOverlayProps, GuideOverlayResult, IconRowRequest } from "app_types";
import { CurrentApp } from "current_app";
import {
    GuideLayoutFor,
    GuideMetricsFor,
    GuidePolicyFor,
    GuideScrimFor,
    GuideStepFor,
    GuideTapFor
} from "guide";
import { Opacity } from "kryon/color_props";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { ColorFromPacked } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { IconType } from "kryon/icon";
import { PaintRoundedFill, PaintRoundedOutline } from "kryon/paint_queue";
import { SessionValid } from "kryon/session";
import { StyleKindGuide } from "kryon/style_sheet";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { End, TreePushScope } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { DismissibleOverlay } from "kryon/tsx/overlay";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    LUMI_GUIDE_SHEET,
    LumiGuideFrame,
    LumiGuideRequest,
    LumiGuideReveal,
    LumiGuideShown,
    LumiGuideStop,
    LumiGuideToggleMuted
} from "lumi_guide";
import { AppFitFontSize, AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import {
    ActionImage,
    ActionLabel,
    GuideFace,
    GuideLumiOrigin,
    GuidePageLabel,
    GuideProgressDots,
    GuideRoundedScrimCorners,
    GuideStepGeometryFor
} from "widgets";

export function GuideOverlayView(guide: GuideOverlayProps): GuideOverlayResult {
    let result: GuideOverlayResult = {};
    let app = CurrentApp();
    if (
        !NativePresent(app) ||
        !SessionValid(app.ui.session) ||
        !NativePresent(guide.steps) ||
        guide.count <= 0n ||
        !NativePresent(guide.step)
    ) {
        return result;
    }
    let session = app.ui.session;
    let width = guide.view_width;
    let height = guide.view_height;
    if (width <= 0n) {
        width = app.ui.view_width;
    }
    if (height <= 0n) {
        height = app.ui.view_height;
    }
    let step = GuideStepFor(nativeDeref(guide.step), guide.count);
    let anchor = nativeAt(guide.steps, step).anchor;
    if (anchor.width <= 0.0 || anchor.height <= 0.0) {
        return result;
    }
    let panel = GuideFace(2n);
    let metrics = GuideMetricsFor(
        MetricsScale(),
        panel,
        GuideFace(24n),
        GuideFace(6n),
        GuideFace(17n),
        GuideFace(15n)
    );
    if (metrics.button_size < AppScale(44n)) {
        metrics.button_size = AppScale(44n);
    }
    if (metrics.close_size < AppScale(44n)) {
        metrics.close_size = AppScale(44n);
    }
    if (metrics.pad < AppScale(16n)) {
        metrics.pad = AppScale(16n);
    }
    if (metrics.anchor_padding < AppScale(12n)) {
        metrics.anchor_padding = AppScale(12n);
    }
    let geometry = GuideStepGeometryFor(guide, step, width, height, metrics);
    let tip = geometry.place.tip;
    let text = nativeAt(guide.steps, step).text;
    let layout = GuideLayoutFor(
        tip,
        geometry.text_width,
        geometry.text_height,
        step,
        guide.count,
        metrics
    );
    State_widgets.guide_layout = layout;
    let lumi_request: LumiGuideRequest = {};
    lumi_request.voice = nativeAt(guide.steps, step).voice;
    lumi_request.text = text;
    lumi_request.place = geometry.place;
    lumi_request.anchor = anchor;
    if (!LumiGuideShown()) {
        lumi_request.origin = GuideLumiOrigin(guide, step, width, height, metrics, geometry);
    }
    let lumi = LumiGuideFrame(app, lumi_request);
    let overlay_props: NativeOverlay.Props = {};
    overlay_props.key = u64(83100n);
    overlay_props.bounds = tip;
    overlay_props.view_width = width;
    overlay_props.view_height = height;
    overlay_props.dismiss_disabled = true;
    let overlay = DismissibleOverlay({ session: session, props: overlay_props });
    if (overlay.node < 0n || overlay.panel_node < 0n) {
        return result;
    }
    let scrim = GuideScrimFor(width, height, anchor, metrics);
    let scrim_face = GuideFace(19n);
    let scrim_color = ColorFromPacked(
        Opacity(scrim_face.value.background, scrim_face.value.opacity)
    );
    PaintRoundedFill(session, overlay.node, scrim.top, 0.0, 4n, scrim_color);
    PaintRoundedFill(session, overlay.node, scrim.bottom, 0.0, 4n, scrim_color);
    PaintRoundedFill(session, overlay.node, scrim.left, 0.0, 4n, scrim_color);
    PaintRoundedFill(session, overlay.node, scrim.right, 0.0, 4n, scrim_color);
    GuideRoundedScrimCorners(session, overlay.node, scrim, scrim_color);
    let focus: Rectangle = {
        x: scrim.left.width,
        y: scrim.top.height,
        width: scrim.right.x - scrim.left.width,
        height: scrim.bottom.y - scrim.top.height
    };
    let focus_radius = float32(AppScale(12n));
    if (focus_radius > focus.height / 2.0) {
        focus_radius = focus.height / 2.0;
    }
    if (focus_radius > focus.width / 2.0) {
        focus_radius = focus.width / 2.0;
    }
    let ink = ColorFromPacked(GuideFace(24n).value.foreground);
    PaintRoundedOutline(
        session,
        overlay.node,
        focus,
        focus_radius,
        12n,
        float32(metrics.anchor_stroke),
        ink
    );
    let panel_color = ColorFromPacked(Opacity(panel.value.background, panel.value.opacity));
    let panel_radius = panel.value.radius;
    if (panel_radius < float32(AppScale(18n))) {
        panel_radius = float32(AppScale(18n));
    }
    PaintRoundedFill(session, overlay.panel_node, tip, panel_radius, 16n, panel_color);
    if (panel.value.border_width > 0.0) {
        PaintRoundedOutline(
            session,
            overlay.panel_node,
            tip,
            panel_radius,
            16n,
            panel.value.border_width,
            ColorFromPacked(panel.value.border)
        );
    }
    if (!TreePushScope(session, overlay.panel_node)) {
        return result;
    }
    let title = GuidePageLabel(app, step, guide.count);
    let voice_control = app.guide_narration_enabled !== 0n;
    let title_controls: s32 = voice_control ? 2n : 1n;
    let title_width =
        tip.width -
        float32(metrics.pad * 2n + (metrics.close_size + metrics.nav_gap) * title_controls);
    let title_props: NativeText.Props = {};
    title_props.text = title;
    title_props.bounds = {
        x: tip.x + float32(metrics.pad),
        y: tip.y + float32(metrics.pad),
        width: title_width,
        height: float32(metrics.close_size)
    };
    title_props.size = AppFitFontSize(
        title,
        s32(title_width),
        AppScale(NativeText.Text16),
        AppSmallFontSize()
    );
    title_props.wrap = Wrap.TextWrapNone;
    title_props.vertical_align = TextAlign.TextAlignCenter;
    title_props.style_kind = StyleKindGuide();
    <Text session={session} props={title_props} />;
    let paragraph: NativeText.Props = {};
    paragraph.text = text;
    paragraph.bounds = layout.text;
    paragraph.size = geometry.font;
    paragraph.wrap = Wrap.TextWrapAuto;
    paragraph.style_kind = StyleKindGuide();
    paragraph.typing = lumi.typed < lumi.characters;
    paragraph.typed = lumi.typed;
    <Text session={session} props={paragraph} />;
    GuideProgressDots(
        session,
        overlay.panel_node,
        tip,
        layout.controls_y,
        metrics.button_size,
        metrics.pad,
        step,
        guide.count,
        ink,
        ColorFromPacked(panel.value.border)
    );
    let previous = guide.previous_requested;
    let next = guide.next_requested;
    let close = guide.close_requested;
    let button: NativeButton.Props = {};
    button.id = 83110n;
    button.bounds = layout.close_button;
    button.label = LocaleText("close_button");
    button.image = ActionImage(ActionIcon.IconClose, button.label);
    button.icon_only = true;
    button.circle = true;
    button.tone = ButtonTone.ButtonToneNeutral;
    button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    if (Button({ session: session, props: button })) {
        close = true;
    }
    if (voice_control) {
        button.id = 83113n;
        button.bounds = layout.close_button;
        button.bounds.x = button.bounds.x - float32(metrics.close_size + metrics.nav_gap);
        let voice_label =
            app.guide_narration_muted !== 0n ? "guide_voice_unmute" : "guide_voice_mute";
        button.label = LocaleText(voice_label);
        button.image = {};
        let voice_icon =
            app.guide_narration_muted !== 0n ? IconType.IconSound0 : IconType.IconSound3;
        button.icon_type = s32(voice_icon);
        if (Button({ session: session, props: button })) {
            LumiGuideToggleMuted(app);
        }
    }
    button.icon_type = 0n;
    if (step > 0n) {
        button.id = 83111n;
        button.bounds = layout.back_button;
        button.label = LocaleText("back_button");
        button.image.asset_path = "";
        button.arrow = true;
        button.direction = ArrowDirection.ArrowLeft;
        button.tone = ButtonTone.ButtonToneNeutral;
        button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
        if (Button({ session: session, props: button })) {
            previous = true;
        }
    }
    button.id = 83112n;
    button.bounds = layout.next_button;
    button.label = LocaleText("next_button");
    button.image.asset_path = "";
    button.arrow = true;
    button.direction = ArrowDirection.ArrowRight;
    button.tone = ButtonTone.ButtonToneAccent;
    button.emphasis = ButtonEmphasis.ButtonEmphasisFilled;
    if (layout.finish) {
        button.label = LocaleText("practice_start_button");
        button.arrow = false;
        button.image = ActionImage(ActionIcon.IconCheck, button.label);
    }
    if (Button({ session: session, props: button })) {
        next = true;
    }
    End(session);
    if (lumi.visible && TreePushScope(session, overlay.node)) {
        let sprite: NativeImage.Props = {};
        sprite.asset_path = LUMI_GUIDE_SHEET;
        sprite.alt_text = "Lumi";
        sprite.bounds = lumi.bounds;
        sprite.source = lumi.source;
        sprite.smooth = true;
        <Image session={session} props={sprite} />;
        End(session);
    }
    let tap = GuideTapFor(lumi.typed, lumi.characters, overlay.tapped);
    if (tap.reveal) {
        LumiGuideReveal();
    }
    if (tap.next) {
        next = true;
    }
    let policy = GuidePolicyFor(step, guide.count, previous, next, close);
    if (policy.closed || policy.finished) {
        LumiGuideStop();
    }
    nativeDeref(guide.step) = policy.step;
    result.step = policy.step;
    result.changed = policy.changed ? 1n : 0n;
    result.closed = policy.closed ? 1n : 0n;
    result.finished = policy.finished ? 1n : 0n;
    return result;
}

export function PracticeControlRowView(row: IconRowRequest): NativeToolbar.IconRowResult {
    let result: NativeToolbar.IconRowResult = {};
    result.clicked_index = -1n;
    let app = CurrentApp();
    if (
        !NativePresent(app) ||
        !SessionValid(app.ui.session) ||
        !NativePresent(row.items) ||
        row.count <= 0n
    ) {
        return result;
    }
    let props: NativeToolbar.BottomIconRowProps = {};
    props.center_x = row.center_x;
    props.view_width = row.view_width;
    props.view_height = row.view_height;
    props.count = row.count;
    let layout = NativeToolbar.BottomIconRowLayoutFor(props, MetricsScale());
    result.y = layout.y;
    result.button_width = layout.button_width;
    let index: s32 = s32(0n);
    while (index < row.count) {
        let action = nativeAt(row.items, index);
        let button: NativeButton.Props = {};
        button.id = s32(83000n) + index;
        button.bounds = NativeToolbar.BottomIconRowButtonBoundsFor(layout, index);
        button.label = ActionLabel(action.icon);
        button.image = ActionImage(action.icon, button.label);
        button.icon_only = true;
        button.tone = ButtonTone.ButtonToneNeutral;
        button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
        button.disabled = action.disabled;
        if (Button({ session: app.ui.session, props: button })) {
            result.clicked_index = index;
        }
        index = index + 1n;
    }
    return result;
}
