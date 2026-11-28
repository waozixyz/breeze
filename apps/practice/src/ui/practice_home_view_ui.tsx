import { ResolvedModal } from "kryon/tsx/modal";
import { ArrowDirection } from "kryon/button";
// Authored UI composition; native application state remains in practice_home_view.zi.
import * as NativeModal from "kryon/modal";
import * as NativeText from "kryon/text";
import * as State_practice_home_view from "practice_home_view";
import { ExerciseType } from "exercise_types";
import { ButtonEmphasis, ButtonTone, ControlSize } from "kryon/control_props";
import { ScalePixels } from "kryon/dpi";
import { Rectangle } from "kryon/geometry";
import { ImageFit } from "kryon/image_props";
import { Swipe } from "kryon/swipe";
import { SwipeDirection } from "kryon/swipe_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { TabBar } from "kryon/tsx/tab_bar";
import { Text } from "kryon/tsx/text";
import {
    ActionsShareRow,
    Alpha,
    Bounds,
    HOME_CAROUSEL_ID,
    HOME_OFFER_ID,
    HOME_TABS_ID,
    HOME_TAB_KEY,
    HOME_TAB_MAX,
    Locale,
    NewTabs,
    ParagraphHeight,
    PracticeHomeCarouselLabel,
    PriceRowHeight,
    ReadPracticeHomeTabHost,
    Status,
    StatusHeight,
    Title,
    Width
} from "practice_home_view";
import {
    PRACTICE_HOME_CONFIG,
    PRACTICE_HOME_MANUAL,
    PRACTICE_HOME_OFFER,
    PRACTICE_HOME_PICK,
    PRACTICE_HOME_RECOVERY_CANCEL,
    PRACTICE_HOME_RECOVERY_CONTINUE,
    PRACTICE_HOME_START,
    PRACTICE_HOME_STEP,
    PRACTICE_HOME_TAB,
    PRACTICE_OFFER_DOWNLOADING,
    PRACTICE_OFFER_NONE
} from "practice_types";

export function CentredLineView(text: string, x: s32, y: s32, width: s32): s32 {
    let height = ParagraphHeight(text, width, State_practice_home_view.home.small_font);
    <Text
        session={State_practice_home_view.home.session}
        props={{
            bounds: Bounds(
                x,
                y + ScalePixels(4n, State_practice_home_view.home.scale),
                width,
                height
            ),
            text: text,
            size: State_practice_home_view.home.small_font,
            align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapAuto
        }}
    />;
    return height + ScalePixels(4n, State_practice_home_view.home.scale);
}

export function PriceView(x: s32, y: s32, width: s32): void {
    let font = State_practice_home_view.home.small_font;
    let height: s32 = s32(0n);
    if (State_practice_home_view.home.regular_price.count > 0n) {
        height = PriceRowHeight();
        let regular_width = Width(State_practice_home_view.home.regular_price, font);
        <Text
            session={State_practice_home_view.home.session}
            props={{
                bounds: Bounds(x, y, regular_width, height),
                text: State_practice_home_view.home.regular_price,
                size: font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone,
                disabled: true,
                strikethrough: true
            }}
        />;
        let badge_height = font + ScalePixels(8n, State_practice_home_view.home.scale);
        let badge_width =
            Width(State_practice_home_view.home.discount, font) +
            ScalePixels(14n, State_practice_home_view.home.scale);
        let badge = Bounds(
            x + regular_width + ScalePixels(10n, State_practice_home_view.home.scale),
            y + (height - badge_height) / 2n,
            badge_width,
            badge_height
        );
        <Box
            session={State_practice_home_view.home.session}
            props={{
                bounds: badge,
                fill: Alpha(State_practice_home_view.home.accent_color, 64.0 / 255.0),
                radius: float32(badge_height) / 2.0
            }}
        />;
        <Text
            session={State_practice_home_view.home.session}
            props={{
                bounds: badge,
                text: State_practice_home_view.home.discount,
                size: font,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone
            }}
        />;
    }
    if (State_practice_home_view.home.worth.count > 0n) {
        <Text
            session={State_practice_home_view.home.session}
            props={{
                bounds: Bounds(
                    x,
                    y + height,
                    width,
                    font + ScalePixels(6n, State_practice_home_view.home.scale)
                ),
                text: State_practice_home_view.home.worth,
                size: font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: Wrap.TextWrapNone
            }}
        />;
    }
}

export function TabsView(bounds: Rectangle): void {
    if (State_practice_home_view.home.tab_count <= 0n) {
        return;
    }
    let tabs = NewTabs();
    let count = State_practice_home_view.home.tab_count;
    if (count > HOME_TAB_MAX) {
        count = HOME_TAB_MAX;
    }
    for (let index = s32(0n); index < count; index += s32(1)) {
        let tab = ReadPracticeHomeTabHost(index);
        nativeSet(tabs, index, {
            key: u64(HOME_TAB_KEY + tab.slot),
            label: tab.label,
            disabled: State_practice_home_view.home.modal_active
        });
    }
    <Box
        session={State_practice_home_view.home.session}
        props={{ bounds: bounds, fill: State_practice_home_view.home.canvas_color }}
    />;
    let bar = TabBar({
        session: State_practice_home_view.home.session,
        props: {
            id: HOME_TABS_ID,
            bounds: {
                x: bounds.x + float32(ScalePixels(12n, State_practice_home_view.home.scale)),
                y: bounds.y + float32(ScalePixels(2n, State_practice_home_view.home.scale)),
                width:
                    bounds.width - float32(ScalePixels(68n, State_practice_home_view.home.scale)),
                height:
                    bounds.height - float32(ScalePixels(4n, State_practice_home_view.home.scale))
            },
            selected_index: State_practice_home_view.home.tab_selected,
            min_tab_width: ScalePixels(72n, State_practice_home_view.home.scale),
            max_tab_width: ScalePixels(220n, State_practice_home_view.home.scale),
            content_sized: true,
            fit: true,
            scroll_offset: State_practice_home_view.home.tab_scroll,
            scale: State_practice_home_view.home.scale,
            focus_selected: State_practice_home_view.home.tab_focus
        },
        tabs: nativeSlice(tabs, 0n, count)
    });
    State_practice_home_view.home.tab_scroll = bar.scroll_offset;
    if (
        !State_practice_home_view.home.modal_active &&
        bar.selected_index >= 0n &&
        bar.selected_index < count &&
        bar.selected_index !== State_practice_home_view.home.tab_selected
    ) {
        State_practice_home_view.home.action = PRACTICE_HOME_TAB;
        State_practice_home_view.home.value = bar.selected_index;
    }
}

export function CarouselView(bounds: Rectangle): void {
    let count = State_practice_home_view.home.listed;
    let selected = State_practice_home_view.home.index;
    if (count <= 1n || bounds.width <= 0n || bounds.height <= 0n) {
        return;
    }
    let button_size = float32(ScalePixels(48n, State_practice_home_view.home.scale));
    let inset = bounds.width * 0.08;
    let button_y = bounds.y + (bounds.height - button_size) / 2n;
    let picked: s32 = s32(-1n);
    if (
        Button({
            session: State_practice_home_view.home.session,
            props: {
                bounds: {
                    x: bounds.x + inset,
                    y: button_y,
                    width: button_size,
                    height: button_size
                },
                id: HOME_CAROUSEL_ID + 1n,
                disabled: State_practice_home_view.home.modal_active,
                arrow: true,
                direction: ArrowDirection.ArrowLeft,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }
        })
    ) {
        picked = selected > 0n ? selected - 1n : count - 1n;
    }
    if (
        Button({
            session: State_practice_home_view.home.session,
            props: {
                bounds: {
                    x: bounds.x + bounds.width - button_size - inset,
                    y: button_y,
                    width: button_size,
                    height: button_size
                },
                id: HOME_CAROUSEL_ID + 2n,
                disabled: State_practice_home_view.home.modal_active,
                arrow: true,
                direction: ArrowDirection.ArrowRight,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }
        })
    ) {
        picked = selected < count - 1n ? selected + 1n : 0n;
    }
    <Text
        session={State_practice_home_view.home.session}
        props={{
            text: PracticeHomeCarouselLabel(selected, count),
            bounds: bounds,
            size: ScalePixels(18n, State_practice_home_view.home.scale),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: Wrap.TextWrapNone
        }}
    />;
    if (picked >= 0n && picked !== selected) {
        State_practice_home_view.home.action = PRACTICE_HOME_PICK;
        State_practice_home_view.home.value = picked;
    }
}

export function OfferView(bounds: Rectangle): void {
    let downloading = State_practice_home_view.home.offer === PRACTICE_OFFER_DOWNLOADING;
    let label = downloading
        ? Locale("practice_download_busy")
        : State_practice_home_view.home.offer_label;
    if (
        Button({
            session: State_practice_home_view.home.session,
            props: {
                id: HOME_OFFER_ID + State_practice_home_view.home.practice * 2n,
                bounds: bounds,
                pill: true,
                label: label,
                disabled: State_practice_home_view.home.offer_disabled || downloading,
                tone: downloading ? ButtonTone.ButtonToneNeutral : ButtonTone.ButtonToneAccent,
                emphasis: downloading
                    ? ButtonEmphasis.ButtonEmphasisSoft
                    : ButtonEmphasis.ButtonEmphasisFilled,
                size: ControlSize.ControlSizeLarge
            }
        })
    ) {
        State_practice_home_view.home.action = PRACTICE_HOME_OFFER;
    }
}

export function PageView(): void {
    let view_x = State_practice_home_view.home.left;
    let view_width = State_practice_home_view.home.view_width - State_practice_home_view.home.left;
    if (view_width < ScalePixels(320n, State_practice_home_view.home.scale)) {
        view_x = 0n;
        view_width = State_practice_home_view.home.view_width;
    }
    let content_width = view_width - ScalePixels(80n, State_practice_home_view.home.scale);
    if (content_width > ScalePixels(940n, State_practice_home_view.home.scale)) {
        content_width = ScalePixels(940n, State_practice_home_view.home.scale);
    }
    if (content_width < ScalePixels(520n, State_practice_home_view.home.scale)) {
        content_width = view_width - ScalePixels(32n, State_practice_home_view.home.scale);
    }
    let x = view_x + (view_width - content_width) / 2n;
    let hero_height =
        State_practice_home_view.home.view_height - State_practice_home_view.home.bottom;
    let tabs_height = State_practice_home_view.home.top;
    if (hero_height <= tabs_height) {
        return;
    }
    let hero = Bounds(view_x, tabs_height, view_width, hero_height - tabs_height);
    let button_height = ScalePixels(48n, State_practice_home_view.home.scale);
    let action_gap = ScalePixels(14n, State_practice_home_view.home.scale);
    let total_width = content_width;
    if (total_width > ScalePixels(700n, State_practice_home_view.home.scale)) {
        total_width = ScalePixels(700n, State_practice_home_view.home.scale);
    }
    if (total_width > view_width - ScalePixels(32n, State_practice_home_view.home.scale)) {
        total_width = view_width - ScalePixels(32n, State_practice_home_view.home.scale);
    }
    if (total_width < ScalePixels(360n, State_practice_home_view.home.scale)) {
        total_width = view_width - ScalePixels(24n, State_practice_home_view.home.scale);
    }
    let secondary_count: s32 = s32(0n);
    let manual = State_practice_home_view.home.ready && State_practice_home_view.home.has_manual;
    let config = State_practice_home_view.home.ready && State_practice_home_view.home.has_config;
    if (manual) {
        secondary_count = secondary_count + 1n;
    }
    if (config) {
        secondary_count = secondary_count + 1n;
    }
    let button_count = 1n + secondary_count;
    let wide = total_width >= ScalePixels(600n, State_practice_home_view.home.scale);
    let secondary_row = secondary_count < 2n || ActionsShareRow(total_width);
    let rows: s32 = s32(1n);
    if (!wide) {
        if (secondary_row) {
            rows = rows + (secondary_count > 0n ? 1n : 0n);
        } else {
            rows = rows + secondary_count;
        }
    }
    let bottom_gap =
        State_practice_home_view.home.bottom > 0n
            ? ScalePixels(28n, State_practice_home_view.home.scale)
            : ScalePixels(20n, State_practice_home_view.home.scale);
    let actions_height = rows * button_height + (rows - 1n) * action_gap;
    let button_y = hero_height - bottom_gap - actions_height;
    let pager_height =
        State_practice_home_view.home.listed > 1n
            ? ScalePixels(48n, State_practice_home_view.home.scale)
            : 0n;
    let pager_y = button_y - ScalePixels(10n, State_practice_home_view.home.scale) - pager_height;
    let title = Title(x, content_width);
    let title_block =
        title.height +
        StatusHeight(content_width) +
        ScalePixels(28n, State_practice_home_view.home.scale);
    if (title_block < ScalePixels(100n, State_practice_home_view.home.scale)) {
        title_block = ScalePixels(100n, State_practice_home_view.home.scale);
    }
    let title_y = pager_y - title_block;
    if (title_y < tabs_height + ScalePixels(8n, State_practice_home_view.home.scale)) {
        title_y = tabs_height + ScalePixels(8n, State_practice_home_view.home.scale);
    }
    let primary_width = total_width;
    if (wide) {
        primary_width = (total_width - action_gap * (button_count - 1n)) / button_count;
    }
    let secondary_width = total_width;
    if (wide) {
        secondary_width = primary_width;
    } else if (secondary_row && secondary_count > 0n) {
        secondary_width = (total_width - action_gap * (secondary_count - 1n)) / secondary_count;
    }
    let action_x = view_x + (view_width - total_width) / 2n;
    let pager_width =
        total_width < ScalePixels(480n, State_practice_home_view.home.scale)
            ? total_width
            : ScalePixels(480n, State_practice_home_view.home.scale);
    let pager_x = view_x + (view_width - pager_width) / 2n;
    State_practice_home_view.home.card = hero;
    let swipe = Swipe(
        {
            bounds: hero,
            directions: 3n,
            min_distance: float32(ScalePixels(48n, State_practice_home_view.home.scale)),
            axis_bias: 1.4,
            max_duration: 1.2
        },
        State_practice_home_view.home.swipe,
        State_practice_home_view.home.swipe_frame
    );
    State_practice_home_view.home.swipe = swipe.gesture;
    State_practice_home_view.home.claim_pointer = swipe.claim_pointer;
    State_practice_home_view.home.release_pointer = swipe.release_pointer;
    State_practice_home_view.home.block_click = swipe.capture_input || swipe.consume_release;
    if (
        State_practice_home_view.home.choosing &&
        (swipe.direction === SwipeDirection.SwipeLeft || State_practice_home_view.home.key_right)
    ) {
        State_practice_home_view.home.action = PRACTICE_HOME_STEP;
        State_practice_home_view.home.value = 1n;
    } else if (
        State_practice_home_view.home.choosing &&
        (swipe.direction === SwipeDirection.SwipeRight || State_practice_home_view.home.key_left)
    ) {
        State_practice_home_view.home.action = PRACTICE_HOME_STEP;
        State_practice_home_view.home.value = -1n;
    }
    if (State_practice_home_view.home.banner.count > 0n) {
        <Image
            session={State_practice_home_view.home.session}
            props={{
                asset_path: State_practice_home_view.home.banner,
                bounds: {
                    x: hero.x,
                    y: hero.y,
                    width: hero.width,
                    height:
                        float32(title_y + ScalePixels(8n, State_practice_home_view.home.scale)) -
                        hero.y
                },
                fit: ImageFit.ImageFitCover
            }}
        />;
    } else {
        <Box
            session={State_practice_home_view.home.session}
            props={{ bounds: hero, fill: State_practice_home_view.home.surface_color }}
        />;
    }
    let fade_height = ScalePixels(120n, State_practice_home_view.home.scale);
    <Box
        session={State_practice_home_view.home.session}
        props={{
            bounds: Bounds(view_x, title_y - fade_height, view_width, fade_height),
            fill: Alpha(State_practice_home_view.home.canvas_color, 0.0),
            fill_bottom: State_practice_home_view.home.canvas_color,
            has_fill_bottom: true
        }}
    />;
    <Box
        session={State_practice_home_view.home.session}
        props={{
            bounds: Bounds(view_x, title_y, view_width, hero_height - title_y),
            fill: State_practice_home_view.home.canvas_color
        }}
    />;
    title.title.bounds.y = title.title.bounds.y + float32(title_y);
    let title_props: NativeText.Props = title.title;
    <Text session={State_practice_home_view.home.session} props={title_props} />;
    if (title.subtitle.text.count > 0n) {
        title.subtitle.bounds.y = title.subtitle.bounds.y + float32(title_y);
        let subtitle_props: NativeText.Props = title.subtitle;
        <Text session={State_practice_home_view.home.session} props={subtitle_props} />;
    }
    Status(x, title_y + title.height, content_width);
    TabsView(Bounds(view_x, 0n, view_width, tabs_height));
    CarouselView(Bounds(pager_x, pager_y, pager_width, pager_height));
    State_practice_home_view.home.start = Bounds(action_x, button_y, primary_width, button_height);
    let start_label = Locale("practice_start_button");
    if (State_practice_home_view.home.practice === s32(ExerciseType.EXERCISE_ASTRAL_PROJECTION)) {
        let lesson_label = Locale("astral_choose_lesson");
        if (lesson_label !== "astral_choose_lesson") {
            start_label = lesson_label;
        }
    }
    if (State_practice_home_view.home.offer !== PRACTICE_OFFER_NONE) {
        OfferView(State_practice_home_view.home.start);
    } else if (
        Button({
            session: State_practice_home_view.home.session,
            props: {
                bounds: State_practice_home_view.home.start,
                label: start_label,
                disabled: State_practice_home_view.home.modal_active,
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                size: ControlSize.ControlSizeLarge,
                pill: true
            }
        })
    ) {
        State_practice_home_view.home.action = PRACTICE_HOME_START;
    }
    if (wide) {
        action_x = action_x + (primary_width + action_gap);
    } else {
        button_y = button_y + (button_height + action_gap);
    }
    if (manual) {
        State_practice_home_view.home.manual = Bounds(
            action_x,
            button_y,
            secondary_width,
            button_height
        );
        if (
            Button({
                session: State_practice_home_view.home.session,
                props: {
                    bounds: State_practice_home_view.home.manual,
                    label: Locale("practice_manual_button"),
                    disabled: State_practice_home_view.home.modal_active,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    pill: true
                }
            })
        ) {
            State_practice_home_view.home.action = PRACTICE_HOME_MANUAL;
        }
        if (wide || secondary_row) {
            action_x = action_x + (secondary_width + action_gap);
        } else {
            button_y = button_y + (button_height + action_gap);
        }
    }
    if (config) {
        State_practice_home_view.home.config = Bounds(
            action_x,
            button_y,
            secondary_width,
            button_height
        );
        if (
            Button({
                session: State_practice_home_view.home.session,
                props: {
                    bounds: State_practice_home_view.home.config,
                    label: Locale("practice_configure_button"),
                    disabled: State_practice_home_view.home.modal_active,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    pill: true
                }
            })
        ) {
            State_practice_home_view.home.action = PRACTICE_HOME_CONFIG;
        }
    }
}

export function RecoveryCardView(): void {
    let width = ScalePixels(400n, State_practice_home_view.home.scale);
    let height = ScalePixels(226n, State_practice_home_view.home.scale);
    let frame = ResolvedModal({
        session: State_practice_home_view.home.session,
        props: {
            id: 17402n,
            title: Locale("practice_recovery_title"),
            width: width,
            height: height,
            scale: State_practice_home_view.home.scale,
            strong_title: true,
            title_at_start: true,
            dismiss_disabled: true
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let area = frame.layout.content;
            let gap = float32(ScalePixels(8n, State_practice_home_view.home.scale));
            let button_h = float32(ScalePixels(44n, State_practice_home_view.home.scale));
            let row_y = area.y + area.height - button_h;
            let detail_h = row_y - area.y - gap;
            if (State_practice_home_view.home.note.count > 0n) {
                let note_h = float32(ScalePixels(26n, State_practice_home_view.home.scale));
                <Text
                    session={State_practice_home_view.home.session}
                    props={{
                        text: State_practice_home_view.home.note,
                        size: State_practice_home_view.home.small_font,
                        bounds: { x: area.x, y: row_y - note_h, width: area.width, height: note_h }
                    }}
                />;
                detail_h = detail_h - note_h;
            }
            let left = area.x;
            let available = area.width;
            if (State_practice_home_view.home.banner.count > 0n) {
                let thumb = area.width / 3.2;
                if (thumb > detail_h) {
                    thumb = detail_h;
                }
                if (thumb > gap * 3.0) {
                    <Image
                        session={State_practice_home_view.home.session}
                        props={{
                            asset_path: State_practice_home_view.home.banner,
                            bounds: { x: left, y: area.y, width: thumb, height: thumb },
                            fit: ImageFit.ImageFitCover
                        }}
                    />;
                    left = left + (thumb + gap);
                    available = available - (thumb + gap);
                }
            }
            let title_h = float32(ScalePixels(28n, State_practice_home_view.home.scale));
            let clock_h = float32(ScalePixels(26n, State_practice_home_view.home.scale));
            let y = area.y;
            if (State_practice_home_view.home.title.count > 0n) {
                <Text
                    session={State_practice_home_view.home.session}
                    props={{
                        text: State_practice_home_view.home.title,
                        size: State_practice_home_view.home.font,
                        wrap: Wrap.TextWrapEllipsis,
                        bounds: { x: left, y: y, width: available, height: title_h }
                    }}
                />;
                y = y + title_h;
            }
            if (State_practice_home_view.home.subtitle.count > 0n) {
                let stage_h = detail_h - (y - area.y) - clock_h;
                if (stage_h > title_h * 1.5) {
                    stage_h = title_h * 1.5;
                }
                if (stage_h > 0.0) {
                    <Text
                        session={State_practice_home_view.home.session}
                        props={{
                            text: State_practice_home_view.home.subtitle,
                            size: State_practice_home_view.home.small_font,
                            wrap: Wrap.TextWrapAuto,
                            bounds: { x: left, y: y, width: available, height: stage_h }
                        }}
                    />;
                    y = y + stage_h;
                }
            }
            if (State_practice_home_view.home.status.count > 0n) {
                <Text
                    session={State_practice_home_view.home.session}
                    props={{
                        text: State_practice_home_view.home.status,
                        size: State_practice_home_view.home.small_font,
                        wrap: Wrap.TextWrapEllipsis,
                        bounds: { x: left, y: y, width: available, height: clock_h }
                    }}
                />;
            }
            let button_w = (area.width - gap) / 2.0;
            if (
                Button({
                    session: State_practice_home_view.home.session,
                    props: {
                        id: 17404n,
                        label: Locale("cancel_button"),
                        bounds: {
                            x: area.x,
                            y: row_y,
                            width: State_practice_home_view.home.ready ? button_w : area.width,
                            height: button_h
                        }
                    }
                })
            ) {
                State_practice_home_view.home.action = PRACTICE_HOME_RECOVERY_CANCEL;
            }
            if (
                State_practice_home_view.home.ready &&
                Button({
                    session: State_practice_home_view.home.session,
                    props: {
                        id: 17403n,
                        label: Locale("practice_recovery_continue"),
                        disabled: State_practice_home_view.home.offer_disabled,
                        tone: ButtonTone.ButtonToneAccent,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                        bounds: {
                            x: area.x + button_w + gap,
                            y: row_y,
                            width: button_w,
                            height: button_h
                        }
                    }
                })
            ) {
                State_practice_home_view.home.action = PRACTICE_HOME_RECOVERY_CONTINUE;
            }
        }
    });
}
