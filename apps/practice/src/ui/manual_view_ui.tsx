// Authored UI composition; native application state remains in manual_view.zi.
import * as NativeImage from "kryon/image";
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as State_manual_view from "manual_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { Swipe } from "kryon/swipe";
import { SwipeDirection } from "kryon/swipe_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Progress } from "kryon/tsx/progress";
import { DiscreteSlider } from "kryon/tsx/slider";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import {
    Alpha,
    Bounds,
    EmptyString,
    Filled,
    FocusId,
    HeaderHeight,
    Hero,
    HeroDots,
    Locale,
    MANUAL_SPEED_ID,
    NewOptions,
    Number,
    Page,
    PageCount,
    PageHeight,
    ParagraphHeight,
    Scale,
    ScrollKey,
    SunBodyKey,
    SunFigure,
    SunStat,
    SunStepLocaleKey,
    SunTitleKey,
    SunVisualHeight,
    Title,
    WhmBodyKey,
    WhmCircle,
    WhmHint,
    WhmSafety,
    WhmTitleKey,
    WhmVisualHeight
} from "manual_view";
import { PRACTICE_MANUAL_CLOSE, PRACTICE_MANUAL_START } from "practice_types";
import { ExerciseType } from "exercise_types";

export function Paragraph(
    text: string,
    x: s32,
    y: NativeRef<s32>,
    width: s32,
    align: TextAlign
): void {
    if (width <= 0n) {
        return;
    }
    let height = ParagraphHeight(text, width);
    <Text
        session={State_manual_view.manual.session}
        props={{
            bounds: Bounds(x, nativeDeref(y), width, height),
            text: text,
            size: State_manual_view.manual.font,
            wrap: Wrap.TextWrapAuto,
            align: align
        }}
    />;
    nativeSet(y, nativeDeref(y) + height);
}

export function Label(text: string, bounds: Rectangle, font: s32, centred: boolean): void {
    <Text
        session={State_manual_view.manual.session}
        props={{
            text: text,
            bounds: bounds,
            size: font,
            wrap: Wrap.TextWrapNone,
            vertical_align: TextAlign.TextAlignCenter,
            align: centred ? TextAlign.TextAlignCenter : TextAlign.TextAlignStart
        }}
    />;
}

export function Panel(bounds: Rectangle, radius: s32, outline: boolean): void {
    <Box
        session={State_manual_view.manual.session}
        props={{
            bounds: bounds,
            fill: State_manual_view.manual.guide_background,
            border: outline ? State_manual_view.manual.guide_foreground : {},
            radius: float32(radius)
        }}
    />;
}

export function Disc(center_x: s32, center_y: s32, radius: s32, color: Color): void {
    <Box
        session={State_manual_view.manual.session}
        props={{
            bounds: Bounds(center_x - radius, center_y - radius, radius * 2n, radius * 2n),
            fill: color,
            radius: float32(radius)
        }}
    />;
}

export function Header(title: string, x: s32, y: NativeRef<s32>, width: s32): void {
    let page = State_manual_view.manual.page;
    <Text
        session={State_manual_view.manual.session}
        props={{
            bounds: Bounds(x, nativeDeref(y), width, Scale(42n)),
            text: title,
            wrap: Wrap.TextWrapNone,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    <Text
        session={State_manual_view.manual.session}
        props={{
            bounds: Bounds(x, nativeDeref(y) + Scale(52n), width, Scale(24n)),
            text: Filled(Locale("tutorial_step_progress"), page + 1n, PageCount()),
            wrap: Wrap.TextWrapNone
        }}
    />;
    nativeSet(y, nativeDeref(y) + HeaderHeight());
}

export function Picture(
    asset: string,
    alt: string,
    bounds: Rectangle,
    fit: NativeImage.ImageFit
): void {
    <Image
        session={State_manual_view.manual.session}
        props={{ asset_path: asset, alt_text: alt, bounds: bounds, fit: fit }}
    />;
}

export function CustomizeRing(hero: Rectangle, label: string): void {
    <Box
        session={State_manual_view.manual.session}
        props={{
            bounds: hero,
            fill: State_manual_view.manual.guide_background,
            radius: float32(Scale(14n))
        }}
    />;
    let center_x = s32(hero.x + hero.width / 2.0);
    let center_y = s32(hero.y + hero.height / 2.0);
    Disc(center_x, center_y, Scale(68n), Alpha(State_manual_view.manual.guide_foreground, 0.24));
    Disc(center_x, center_y, Scale(48n), State_manual_view.manual.guide_background);
    let inner = Scale(48n);
    <Text
        session={State_manual_view.manual.session}
        props={{
            bounds: Bounds(center_x - inner, center_y - inner, inner * 2n, inner * 2n),
            text: label,
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}

export function WhmSpeed(x: s32, width: s32, y: NativeRef<s32>): void {
    let height = Scale(86n);
    Panel(Bounds(x, nativeDeref(y), width, height), Scale(14n), false);
    let row_x = x + Scale(18n);
    let row_width = width - Scale(36n);
    let row_y = nativeDeref(y) + Scale(9n);
    let label = Locale("speed_label");
    <Text
        session={State_manual_view.manual.session}
        props={{
            text: label,
            size: State_manual_view.manual.small_font,
            wrap: Wrap.TextWrapNone,
            bounds: Bounds(row_x, row_y, row_width - Scale(64n), Scale(20n))
        }}
    />;
    <Text
        session={State_manual_view.manual.session}
        props={{
            text: Number(State_manual_view.manual.speed),
            size: State_manual_view.manual.small_font,
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignEnd,
            bounds: Bounds(row_x + row_width - Scale(64n), row_y, Scale(64n), Scale(20n))
        }}
    />;
    let step = DiscreteSlider({
        session: State_manual_view.manual.session,
        props: {
            id: MANUAL_SPEED_ID,
            bounds: Bounds(row_x, row_y + Scale(20n), row_width, Scale(36n)),
            semantic_label: label,
            value: State_manual_view.manual.speed,
            min: State_manual_view.manual.speed_min,
            max: State_manual_view.manual.speed_max
        }
    });
    if (step.changed && step.value !== State_manual_view.manual.speed) {
        State_manual_view.manual.speed = step.value;
        State_manual_view.manual.speed_changed = true;
    }
    nativeSet(y, nativeDeref(y) + height);
}

export function WhmPage(x: s32, width: s32, y: NativeRef<s32>): void {
    let page = State_manual_view.manual.page;
    let height = WhmVisualHeight(page);
    let hero = Hero(x, width, nativeDeref(y), height);
    if (page === 0n || page === 3n) {
        Picture(
            page === 3n ? "assets/practices/whm/2.webp" : "assets/practices/whm/1.webp",
            Locale(WhmTitleKey(page)),
            hero,
            NativeImage.ImageFit.ImageFitContain
        );
        HeroDots(hero);
        nativeSet(y, nativeDeref(y) + (height + Scale(16n)));
    } else {
        Panel(hero, Scale(16n), false);
        let center_x = x + width / 2n;
        let center_y = nativeDeref(y) + height / 2n - Scale(8n);
        if (page === 1n) {
            WhmCircle(center_x, center_y, State_manual_view.manual.breath_radius, EmptyString());
        } else {
            WhmCircle(center_x, center_y, Scale(68n), "0:00");
            <Progress
                session={State_manual_view.manual.session}
                props={{
                    bounds: Bounds(
                        x + Scale(36n),
                        nativeDeref(y) + height - Scale(34n),
                        width - Scale(72n),
                        Scale(5n)
                    ),
                    min: 0n,
                    max: 60n,
                    value: State_manual_view.manual.hold_progress
                }}
            />;
        }
        HeroDots(hero);
        nativeSet(y, nativeDeref(y) + (height + Scale(18n)));
    }
    Header(Locale(WhmTitleKey(page)), x, y, width);
    Paragraph(Locale(WhmBodyKey(page)), x, y, width, TextAlign.TextAlignStart);
    if (page === 0n) {
        nativeSet(y, nativeDeref(y) + Scale(34n));
        WhmSafety(x, width, y);
    } else if (page === 1n) {
        nativeSet(y, nativeDeref(y) + Scale(24n));
        WhmSpeed(x, width, y);
    } else {
        nativeSet(y, nativeDeref(y) + Scale(24n));
        WhmHint(x, width, y);
    }
}

export function PatternsPanel(bounds: Rectangle, radius: s32, selected: boolean): void {
    <Box
        session={State_manual_view.manual.session}
        props={{
            bounds: bounds,
            fill: State_manual_view.manual.guide_background,
            border: selected
                ? State_manual_view.manual.guide_foreground
                : State_manual_view.manual.guide_border,
            radius: float32(radius)
        }}
    />;
}

export function SunPage(x: s32, width: s32, y: NativeRef<s32>): void {
    let height = SunVisualHeight(width);
    let hero = Hero(x, width, nativeDeref(y), height);
    Panel(hero, Scale(16n), false);
    x = s32(hero.x);
    width = s32(hero.width);
    if (State_manual_view.manual.page === 0n) {
        let gap = Scale(8n);
        let inset = Scale(10n);
        let card_w = (width - inset * 2n - gap * 2n) / 3n;
        let card_h = (card_w * 4n) / 3n;
        let number_h = Scale(22n);
        let name_h = Scale(38n);
        let card_color = State_manual_view.manual.guide_background;
        card_color.r = card_color.r > 8n ? card_color.r - u8(8n) : u8(0n);
        card_color.g = card_color.g > 8n ? card_color.g - u8(8n) : u8(0n);
        card_color.b = card_color.b > 8n ? card_color.b - u8(8n) : u8(0n);
        for (let step = s32(0n); step <= 11n; step += s32(1)) {
            let card = Bounds(
                x + inset + (step % 3n) * (card_w + gap),
                nativeDeref(y) + inset + (step / 3n) * (card_h + gap),
                card_w,
                card_h
            );
            <Box
                session={State_manual_view.manual.session}
                props={{ bounds: card, fill: card_color, radius: float32(Scale(12n)) }}
            />;
            Label(
                Number(step + 1n),
                {
                    x: card.x + float32(Scale(8n)),
                    y: card.y + float32(Scale(4n)),
                    width: card.width - float32(Scale(16n)),
                    height: float32(number_h)
                },
                State_manual_view.manual.small_font,
                false
            );
            let name = Locale(SunStepLocaleKey(step));
            SunFigure(
                step,
                {
                    x: card.x + float32(Scale(4n)),
                    y: card.y + float32(number_h),
                    width: card.width - float32(Scale(8n)),
                    height: card.height - float32(number_h + name_h)
                },
                NativeLayout.KeyHash("sun-salutation/manual/chart") + u64(step) * u64(4096n),
                name
            );
            <Text
                session={State_manual_view.manual.session}
                props={{
                    text: name,
                    size: State_manual_view.manual.small_font,
                    align: TextAlign.TextAlignCenter,
                    bounds: {
                        x: card.x + float32(Scale(4n)),
                        y: card.y + card.height - float32(name_h),
                        width: card.width - float32(Scale(8n)),
                        height: float32(name_h)
                    }
                }}
            />;
        }
    } else if (State_manual_view.manual.page === 1n) {
        let pose_width = (width - Scale(36n)) / 3n;
        let steps: [s32, s32, s32] = [0n, 3n, 7n];
        let keys: [string, string, string] = [
            "sun-salutation/manual/first",
            "sun-salutation/manual/middle",
            "sun-salutation/manual/last"
        ];
        for (let index = s32(0n); index <= 2n; index += s32(1)) {
            let pose_bounds = Bounds(
                x + Scale(10n) + index * (pose_width + Scale(8n)),
                nativeDeref(y) + Scale(24n),
                pose_width,
                Scale(112n)
            );
            SunFigure(
                nativeAt(steps, index),
                pose_bounds,
                NativeLayout.KeyHash(nativeAt(keys, index)),
                Locale("exercise_sun_salutation")
            );
            Disc(
                s32(pose_bounds.x + pose_bounds.width / 2.0),
                nativeDeref(y) + Scale(151n),
                Scale(4n),
                index === 1n
                    ? State_manual_view.manual.guide_foreground
                    : State_manual_view.manual.guide_border
            );
        }
    } else {
        let row_y = nativeDeref(y) + Scale(24n);
        SunStat(
            Locale("sun_salutation_repetitions_label"),
            Filled("%dx", State_manual_view.manual.sun_repetitions, 0n),
            x,
            row_y,
            width
        );
        row_y = row_y + Scale(45n);
        SunStat(
            Locale("sun_salutation_start_speed_label"),
            Filled("%d s", State_manual_view.manual.sun_start_seconds, 0n),
            x,
            row_y,
            width
        );
        row_y = row_y + Scale(45n);
        SunStat(
            Locale("sun_salutation_end_speed_label"),
            Filled("%d s", State_manual_view.manual.sun_end_seconds, 0n),
            x,
            row_y,
            width
        );
    }
    nativeSet(y, nativeDeref(y) + (height + Scale(18n)));
    HeroDots(hero);
    Header(Locale(SunTitleKey()), x, y, width);
    Paragraph(Locale(SunBodyKey()), x, y, width, TextAlign.TextAlignStart);
}

export function Pager(nav_y: s32, nav_height: s32, content_y: s32, content_height: s32): void {
    let count = PageCount();
    let swipe = Swipe(
        {
            bounds: Bounds(0n, content_y, State_manual_view.manual.view_width, content_height),
            directions: u32(s32(SwipeDirection.SwipeHorizontal)),
            min_distance: float32(Scale(48n)),
            axis_bias: 1.25,
            max_duration: 0.8
        },
        State_manual_view.manual.swipe,
        State_manual_view.manual.swipe_frame
    );
    State_manual_view.manual.swipe = swipe.gesture;
    State_manual_view.manual.claim_pointer = swipe.claim_pointer;
    State_manual_view.manual.release_pointer = swipe.release_pointer;
    State_manual_view.manual.block_click = swipe.capture_input || swipe.consume_release;
    let previous =
        State_manual_view.manual.previous || swipe.direction === SwipeDirection.SwipeRight;
    let next = State_manual_view.manual.next || swipe.direction === SwipeDirection.SwipeLeft;
    let finish = State_manual_view.manual.finish;
    let close = State_manual_view.manual.close;
    let padding = Scale(12n);
    let content_width =
        State_manual_view.manual.view_width - Scale(State_manual_view.MANUAL_SIDE_PADDING) * 2n;
    if (content_width > Scale(State_manual_view.MANUAL_MAX_WIDTH)) {
        content_width = Scale(State_manual_view.MANUAL_MAX_WIDTH);
    }
    let content_x = (State_manual_view.manual.view_width - content_width) / 2n;
    let width = (content_width - padding) / 2n;
    let height = nav_height - padding * 2n;
    if (height > Scale(48n)) {
        height = Scale(48n);
    }
    if (!close && width > 0n && height > 0n) {
        <Box
            session={State_manual_view.manual.session}
            props={{
                bounds: Bounds(0n, nav_y, State_manual_view.manual.view_width, nav_height),
                fill: State_manual_view.manual.guide_background
            }}
        />;
        let button_y = nav_y + (nav_height - height) / 2n;
        if (
            Button({
                session: State_manual_view.manual.session,
                props: {
                    id: FocusId(),
                    bounds: Bounds(content_x, button_y, width, height),
                    label: Locale("back_button"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }
            })
        ) {
            if (State_manual_view.manual.page === 0n) {
                close = true;
            } else {
                previous = true;
            }
        }
        if (
            Button({
                session: State_manual_view.manual.session,
                props: {
                    id: FocusId() + 1n,
                    bounds: Bounds(content_x + padding + width, button_y, width, height),
                    label: Locale(
                        State_manual_view.manual.page === count - 1n
                            ? "practice_start_button"
                            : "next_button"
                    ),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }
            })
        ) {
            finish = true;
        }
    }
    if (finish && State_manual_view.manual.page < count - 1n) {
        next = true;
        finish = false;
    }
    if (close) {
        State_manual_view.manual.action = PRACTICE_MANUAL_CLOSE;
        State_manual_view.manual.block_click = true;
    } else if (finish) {
        State_manual_view.manual.action = PRACTICE_MANUAL_START;
        State_manual_view.manual.block_click = true;
    } else if (previous && State_manual_view.manual.page > 0n) {
        State_manual_view.manual.page = State_manual_view.manual.page - 1n;
        State_manual_view.manual.scroll = 0n;
    } else if (next && State_manual_view.manual.page < count - 1n) {
        State_manual_view.manual.page = State_manual_view.manual.page + 1n;
        State_manual_view.manual.scroll = 0n;
    } else if (next && State_manual_view.manual.page === count - 1n) {
        State_manual_view.manual.action = PRACTICE_MANUAL_START;
        State_manual_view.manual.block_click = true;
    }
}

export function Manual(): void {
    let count = PageCount();
    if (State_manual_view.manual.page < 0n) {
        State_manual_view.manual.page = 0n;
    }
    if (State_manual_view.manual.page >= count) {
        State_manual_view.manual.page = count - 1n;
    }
    if (State_manual_view.manual.title_height > 0n) {
        let options = NewOptions();
        let bar = TitleBar({
            session: State_manual_view.manual.session,
            props: {
                title: Title(),
                height: State_manual_view.manual.title_height,
                bounds: Bounds(
                    0n,
                    0n,
                    State_manual_view.manual.view_width,
                    State_manual_view.manual.title_height
                ),
                has_leading_action: true,
                leading_label: Locale("back_button")
            },
            options: nativeSlice(options, 0n, 0n)
        });
        if (bar.clicked_leading) {
            State_manual_view.manual.action = PRACTICE_MANUAL_CLOSE;
            State_manual_view.manual.block_click = true;
            return;
        }
    }
    let nav_height = count > 1n ? Scale(State_manual_view.MANUAL_NAV_HEIGHT) : 0n;
    let content_y = State_manual_view.manual.title_height + Scale(State_manual_view.MANUAL_TOP_GAP);
    let nav_y = State_manual_view.manual.view_height - State_manual_view.manual.bottom - nav_height;
    let content_height = nav_y - content_y;
    let minimum =
        State_manual_view.manual.practice === s32(ExerciseType.EXERCISE_WIM_HOF) ? 0n : Scale(120n);
    if (content_height < minimum) {
        content_height = minimum;
    }
    let max_width = s32(float32(State_manual_view.manual.view_width) * 0.96);
    if (max_width > Scale(State_manual_view.MANUAL_MAX_WIDTH)) {
        max_width = Scale(State_manual_view.MANUAL_MAX_WIDTH);
    }
    let least =
        State_manual_view.manual.practice === s32(ExerciseType.EXERCISE_WIM_HOF)
            ? Scale(280n)
            : Scale(200n);
    if (max_width < least) {
        max_width = least;
    }
    let column = NativeLayout.CenteredColumnFor(
        State_manual_view.manual.view_width,
        max_width,
        Scale(State_manual_view.MANUAL_SIDE_PADDING)
    );
    let scrolled = NativeScroll.Draw(State_manual_view.manual.session, {
        key: ScrollKey(),
        bounds: Bounds(0n, content_y, State_manual_view.manual.view_width, content_height),
        content_height: PageHeight(column.width),
        scroll_offset: State_manual_view.manual.scroll,
        scale: State_manual_view.manual.scale
    });
    State_manual_view.manual.scroll = scrolled.scroll_offset;
    if (scrolled.opened) {
        Page(column.x, column.width, s32(scrolled.content.y));
        End(State_manual_view.manual.session);
    }
    Pager(nav_y, nav_height, content_y, content_height);
}
