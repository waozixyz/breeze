import { ManualScreenNewOptions } from "manual_screen";
import { ManualScreenNewProgress } from "manual_screen";
// Authored UI composition; native application state remains in manual_screen.zi.
import * as NativeButton from "kryon/button";
import * as NativeText from "kryon/text";
import * as NativeTitleBar from "kryon/title_bar";
import { app_block_current_click } from "app_modal_state";
import { app_nav_desktop_rail_enabled } from "app_nav_state";
import { InnerBreeze } from "app_types";
import { CurrentApp } from "current_app";
import { GuidePagerPageFor, GuidePagerPolicy, GuidePagerPolicyFor } from "guide_pager";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { ColorFromPacked } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { PaintRoundedFill } from "kryon/paint_queue";
import { Swipe } from "kryon/swipe";
import { SwipeDirection, SwipeSpec } from "kryon/swipe_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import {
    ManualGuideNav,
    ManualParagraphSpec,
    manual_screen_tutorial_max_width,
    manual_screen_tutorial_side_padding
} from "manual_screen";
import { AppFontSize, AppParagraphHeight, AppScale } from "metrics";
import { NativePresent } from "native_flags";
import { AppTextFromCString, FormatTwoNumberTemplate, FrameTextHold } from "text_buffers";
import { GuideFace } from "widgets";

export function ManualParagraphView(
    app: NativeRef<InnerBreeze>,
    paragraph: ManualParagraphSpec,
    x: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app) || !NativePresent(y) || paragraph.width <= 0n) {
        return;
    }
    let font = paragraph.font;
    if (font <= 0n) {
        font = AppFontSize();
    }
    let height = AppParagraphHeight(paragraph.text, paragraph.width, font, paragraph.line_gap);
    let current_y = nativeDeref(y);
    let props: NativeText.Props = {};
    props.bounds = {
        x: float32(x),
        y: float32(current_y),
        width: float32(paragraph.width),
        height: float32(height)
    };
    props.text = paragraph.text;
    props.size = font;
    props.wrap = Wrap.TextWrapAuto;
    props.align = paragraph.align;
    <Text session={app.ui.session} props={props} />;
    nativeDeref(y) = nativeDeref(y) + height;
}

export function manual_screen_draw_guide_headerView(
    title: string,
    page: s32,
    page_count: s32,
    content_x: s32,
    y: NativeRef<s32>,
    content_w: s32
): void {
    let app = CurrentApp();
    if (!NativePresent(app) || !NativePresent(y) || page_count <= 0n) {
        return;
    }
    page = GuidePagerPageFor(page, page_count);
    let progress = ManualScreenNewProgress();
    if (
        !FormatTwoNumberTemplate(
            LocaleText("tutorial_step_progress"),
            page + 1n,
            page_count,
            nativeSlice(progress)
        )
    ) {
        return;
    }
    let progress_text = FrameTextHold(
        nativeRef(app.ui.frame_text),
        AppTextFromCString(nativeRef(nativeAt(progress, 0n)), 96n)
    );
    let title_h = AppScale(42n);
    let title_step_gap = AppScale(10n);
    let step_h = AppScale(24n);
    let current_y = nativeDeref(y);
    let heading: NativeText.Props = {};
    heading.bounds = {
        x: float32(content_x),
        y: float32(current_y),
        width: float32(content_w),
        height: float32(title_h)
    };
    heading.text = title;
    heading.wrap = Wrap.TextWrapNone;
    heading.vertical_align = TextAlign.TextAlignCenter;
    <Text session={app.ui.session} props={heading} />;
    let label: NativeText.Props = {};
    label.bounds = {
        x: float32(content_x),
        y: float32(current_y + title_h + title_step_gap),
        width: float32(content_w),
        height: float32(step_h)
    };
    label.text = progress_text;
    label.wrap = Wrap.TextWrapNone;
    <Text session={app.ui.session} props={label} />;
    nativeDeref(y) = nativeDeref(y) + (title_h + title_step_gap + step_h + AppScale(16n));
}

export function manual_screen_draw_title_barView(
    app: NativeRef<InnerBreeze>,
    title: string,
    title_h: s32
): s32 {
    if (!NativePresent(app) || app_nav_desktop_rail_enabled(app) !== 0n) {
        return 0n;
    }
    let bar: NativeTitleBar.Props = {};
    bar.title = title;
    bar.height = title_h;
    bar.bounds = { x: 0.0, y: 0.0, width: float32(app.ui.view_width), height: float32(title_h) };
    bar.has_leading_action = true;
    bar.leading_label = LocaleText("back_button");
    let options = ManualScreenNewOptions();
    let result = TitleBar({
        session: app.ui.session,
        props: bar,
        options: nativeSlice(options, 0n, 0n)
    });
    if (!result.clicked_leading) {
        return 0n;
    }
    app_block_current_click(app);
    return 1n;
}

export function manual_screen_guide_controlsView(
    app: NativeRef<InnerBreeze>,
    nav: ManualGuideNav
): GuidePagerPolicy {
    let empty: GuidePagerPolicy = {};
    if (!NativePresent(app) || nav.page_count < 1n) {
        return empty;
    }
    let page = GuidePagerPageFor(nav.page, nav.page_count);
    let swipe_spec: SwipeSpec = {};
    swipe_spec.bounds = {
        x: 0.0,
        y: float32(nav.content_y),
        width: float32(app.ui.view_width),
        height: float32(nav.content_h)
    };
    swipe_spec.directions = u32(s32(SwipeDirection.SwipeHorizontal));
    swipe_spec.min_distance = float32(AppScale(48n));
    swipe_spec.axis_bias = 1.25;
    swipe_spec.max_duration = 0.8;
    let swipe = Swipe(swipe_spec, app.manual_swipe, app.ui.manual_swipe_frame);
    app.manual_swipe = swipe.gesture;
    if (swipe.claim_pointer) {
        app.ui.manual_swipe_owner = true;
    }
    if (swipe.release_pointer) {
        app.ui.manual_swipe_owner = false;
    }
    if (swipe.capture_input || swipe.consume_release) {
        app_block_current_click(app);
    }
    let previous = app.ui.manual_previous || swipe.direction === SwipeDirection.SwipeRight;
    let next = app.ui.manual_next || swipe.direction === SwipeDirection.SwipeLeft;
    let finish = app.ui.manual_finish;
    let close_requested = app.ui.manual_close;
    let pad = AppScale(12n);
    let content_w = app.ui.view_width - manual_screen_tutorial_side_padding() * 2n;
    if (content_w > manual_screen_tutorial_max_width()) {
        content_w = manual_screen_tutorial_max_width();
    }
    let content_x = (app.ui.view_width - content_w) / 2n;
    let width = (content_w - pad) / 2n;
    let height = nav.h - pad * 2n;
    if (height > AppScale(48n)) {
        height = AppScale(48n);
    }
    if (!close_requested && width > 0n && height > 0n) {
        let footer: Rectangle = {
            x: 0.0,
            y: float32(nav.y),
            width: float32(app.ui.view_width),
            height: float32(nav.h)
        };
        let face = GuideFace(2n);
        PaintRoundedFill(
            app.ui.session,
            -1n,
            footer,
            0.0,
            4n,
            ColorFromPacked(face.value.background)
        );
        let button_y = nav.y + (nav.h - height) / 2n;
        let back: NativeButton.Props = {};
        back.id = nav.focus_id;
        back.bounds = {
            x: float32(content_x),
            y: float32(button_y),
            width: float32(width),
            height: float32(height)
        };
        back.label = LocaleText("back_button");
        back.tone = ButtonTone.ButtonToneNeutral;
        back.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
        if (Button({ session: app.ui.session, props: back })) {
            if (page === 0n) {
                close_requested = true;
            } else {
                previous = true;
            }
        }
        let forward: NativeButton.Props = {};
        forward.id = nav.focus_id + 1n;
        forward.bounds = {
            x: float32(content_x + pad + width),
            y: float32(button_y),
            width: float32(width),
            height: float32(height)
        };
        forward.label = LocaleText("next_button");
        if (page === nav.page_count - 1n) {
            forward.label = LocaleText("practice_start_button");
        }
        forward.tone = ButtonTone.ButtonToneAccent;
        forward.emphasis = ButtonEmphasis.ButtonEmphasisFilled;
        if (Button({ session: app.ui.session, props: forward })) {
            finish = true;
        }
    }
    if (finish && page < nav.page_count - 1n) {
        next = true;
        finish = false;
    }
    let policy = GuidePagerPolicyFor(
        page,
        nav.page_count,
        previous,
        next,
        close_requested,
        finish,
        true
    );
    if (policy.closed) {
        app_block_current_click(app);
        return policy;
    }
    if (policy.finished) {
        app_block_current_click(app);
        return policy;
    }
    if (policy.changed) {
        app.manual_scroll = 0n;
    }
    app.tutorial_step = policy.page;
    return policy;
}
