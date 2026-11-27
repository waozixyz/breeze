// Authored UI composition; native application state remains in course_view.zi.
import * as NativeShape from "kryon/shape";
import * as NativeImage from "kryon/image";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as State_course_view from "course_view";
import {
    Bounds,
    Locale,
    ParagraphHeight,
    PlanLessonGroup,
    Play,
    ReadPracticeCourseRowHost,
    Scale
} from "course_view";
import { ButtonEmphasis, ButtonTone, ContentAlignment } from "kryon/control_props";
import { Rectangle, Vector2 } from "kryon/geometry";
import { SemanticKind } from "kryon/semantic";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import {
    PRACTICE_COURSE_CLOSE,
    PRACTICE_COURSE_FOUNDATION,
    PRACTICE_COURSE_FULL,
    PRACTICE_COURSE_LESSON
} from "practice_types";
import { PracticeCourseRow } from "practice_ui_types";

export function Section(text: string, bounds: Rectangle): void {
    let strong: [NativeText.Range] = [{ start: 0n, end: s32(text.count) }];
    <Text
        session={State_course_view.course.session}
        props={{
            text: text,
            bounds: bounds,
            size: State_course_view.course.font + Scale(2n),
            strong: nativeSlice(strong),
            semantic_kind: SemanticKind.SemanticHeading,
            heading_level: 2n
        }}
    />;
}

export function LessonCard(
    bounds: Rectangle,
    index: s32,
    artwork: s32,
    row: PracticeCourseRow
): void {
    let activated = Button({
        session: State_course_view.course.session,
        props: {
            key: NativeLayout.KeyHash("inbe/tai_chi/lesson") + u64(index),
            bounds: bounds,
            label: row.title,
            detail: row.detail,
            icon_only: true,
            selected: row.done,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        }
    });
    let inset = float32(Scale(12n));
    let content: Rectangle = {
        x: bounds.x + inset,
        y: bounds.y + inset,
        width: bounds.width - inset * 2.0,
        height: bounds.height - inset * 2.0
    };
    let picture_h = (s32(content.width) * 3n) / 4n;
    if (artwork >= 0n && artwork < 14n) {
        <Image
            session={State_course_view.course.session}
            props={{
                key: NativeLayout.KeyHash("inbe/tai_chi/lesson-image") + u64(index),
                asset_path: nativeAt(State_course_view.lesson_artwork, artwork),
                alt_text: row.title,
                bounds: {
                    x: content.x,
                    y: content.y,
                    width: content.width,
                    height: float32(picture_h)
                },
                radius: float32(Scale(8n)),
                smooth: true,
                tint: row.locked ? u32(0xffffff50n) : u32(0xffffffffn),
                fit: NativeImage.ImageFit.ImageFitCover
            }}
        />;
        if (row.locked) {
            let center: Vector2 = {
                x: content.x + content.width * 0.5,
                y: content.y + float32(picture_h) * 0.5
            };
            let unit = float32(Scale(1n));
            <Box
                session={State_course_view.course.session}
                props={{
                    bounds: {
                        x: center.x - 24.0 * unit,
                        y: center.y - 24.0 * unit,
                        width: 48.0 * unit,
                        height: 48.0 * unit
                    },
                    fill: { r: 28n, g: 36n, b: 40n, a: 224n },
                    radius: 12.0 * unit
                }}
            />;
            NativeShape.Ring(State_course_view.course.session, {
                center: { x: center.x, y: center.y - 5.0 * unit },
                inner_radius: 5.0 * unit,
                outer_radius: 7.0 * unit,
                start_angle: 180.0,
                end_angle: 360.0,
                color: { r: 255n, g: 255n, b: 255n, a: 255n }
            });
            <Box
                session={State_course_view.course.session}
                props={{
                    bounds: {
                        x: center.x - 10.0 * unit,
                        y: center.y - 5.0 * unit,
                        width: 20.0 * unit,
                        height: 17.0 * unit
                    },
                    fill: { r: 255n, g: 255n, b: 255n, a: 255n },
                    radius: 3.0 * unit
                }}
            />;
        }
    }
    content.y = content.y + float32(picture_h + Scale(12n));
    let heading_h = ParagraphHeight(
        row.title,
        s32(content.width),
        State_course_view.course.font + Scale(2n)
    );
    let subtitle_h = ParagraphHeight(
        row.subtitle,
        s32(content.width),
        State_course_view.course.font
    );
    Section(row.title, {
        x: content.x,
        y: content.y,
        width: content.width,
        height: float32(heading_h)
    });
    <Text
        session={State_course_view.course.session}
        props={{
            text: row.subtitle,
            size: State_course_view.course.font,
            bounds: {
                x: content.x,
                y: content.y + float32(heading_h + Scale(6n)),
                width: content.width,
                height: float32(subtitle_h)
            }
        }}
    />;
    <Text
        session={State_course_view.course.session}
        props={{
            text: row.detail,
            size: State_course_view.course.small_font,
            class_name: State_course_view.course.muted_class,
            bounds: {
                x: content.x,
                y: bounds.y + bounds.height - float32(Scale(36n)),
                width: content.width,
                height: float32(Scale(24n))
            }
        }}
    />;
    if (activated) {
        if (row.kind === PRACTICE_COURSE_FOUNDATION) {
            State_course_view.course.lesson = index;
            State_course_view.course.item_scroll = 0n;
        } else {
            Play(row.first);
        }
    }
}

export function FoundationHeader(bounds: Rectangle): void {
    let activated = Button({
        session: State_course_view.course.session,
        props: {
            key: NativeLayout.KeyHash("inbe/tai_chi/foundations-toggle"),
            bounds: bounds,
            label: Locale("tai_chi_foundations"),
            icon_only: true,
            selected: State_course_view.foundations_open,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        }
    });
    if (activated) {
        State_course_view.foundations_open = !State_course_view.foundations_open;
    }
    let inset = float32(Scale(12n));
    <Image
        session={State_course_view.course.session}
        props={{
            key: NativeLayout.KeyHash("inbe/tai_chi/foundations-cover"),
            asset_path: nativeAt(State_course_view.lesson_artwork, 8n),
            alt_text: Locale("tai_chi_foundations"),
            bounds: {
                x: bounds.x + inset,
                y: bounds.y + (bounds.height - float32(Scale(72n))) * 0.5,
                width: float32(Scale(96n)),
                height: float32(Scale(72n))
            },
            radius: float32(Scale(8n)),
            smooth: true,
            tint: u32(0xffffffffn),
            fit: NativeImage.ImageFit.ImageFitCover
        }}
    />;
    Section(Locale("tai_chi_foundations"), {
        x: bounds.x + float32(Scale(120n)),
        y: bounds.y + inset,
        width: bounds.width - float32(Scale(152n)),
        height: bounds.height - inset * 2.0
    });
    let center: Vector2 = {
        x: bounds.x + bounds.width - float32(Scale(20n)),
        y: bounds.y + bounds.height * 0.5
    };
    let half = float32(Scale(5n));
    let direction: float32 = State_course_view.foundations_open ? -1.0 : 1.0;
    for (let side = s32(0n); side <= s32(1n); side += s32(1)) {
        let sign: float32 = side === 0n ? -1.0 : 1.0;
        <Shape
            session={State_course_view.course.session}
            props={{
                key: NativeLayout.KeyHash("inbe/tai_chi/foundations-chevron") + u64(side),
                start: { x: center.x + sign * half, y: center.y - direction * half * 0.5 },
                end: { x: center.x, y: center.y + direction * half * 0.5 },
                thickness: float32(Scale(2n)),
                color: { r: 135n, g: 156n, b: 145n, a: 255n }
            }}
        />;
    }
}

export function Lessons(bounds: Rectangle): void {
    let width = s32(bounds.width) - Scale(10n);
    let columns: s32 = width >= Scale(640n) ? 3n : 2n;
    let expanded = State_course_view.foundations_open;
    State_course_view.lesson_total = 0n;
    let foundation_count: s32 = s32(0n);
    for (let index = s32(0n); index < State_course_view.course.lesson_count; index += s32(1)) {
        if (nativeAt(State_course_view.course_lessons, index).kind === PRACTICE_COURSE_FOUNDATION) {
            nativeSet(State_course_view.lesson_indices, State_course_view.lesson_total, index);
            nativeSet(State_course_view.lesson_artwork_indices, index, 8n + foundation_count);
            State_course_view.lesson_total = State_course_view.lesson_total + 1n;
            foundation_count = foundation_count + 1n;
        }
    }
    let artwork: s32 = s32(0n);
    let full: s32 = s32(-1n);
    for (let index = s32(0n); index < State_course_view.course.lesson_count; index += s32(1)) {
        let row = nativeAt(State_course_view.course_lessons, index);
        if (row.kind === PRACTICE_COURSE_LESSON) {
            nativeSet(State_course_view.lesson_indices, State_course_view.lesson_total, index);
            nativeSet(State_course_view.lesson_artwork_indices, index, artwork);
            State_course_view.lesson_total = State_course_view.lesson_total + 1n;
            artwork = artwork + 1n;
        } else if (row.kind === PRACTICE_COURSE_FULL) {
            full = index;
        }
    }
    if (full >= 0n) {
        nativeSet(State_course_view.lesson_indices, State_course_view.lesson_total, full);
        nativeSet(State_course_view.lesson_artwork_indices, full, 7n);
        State_course_view.lesson_total = State_course_view.lesson_total + 1n;
    }
    let header_h = Scale(96n);
    let heading_h =
        ParagraphHeight(
            Locale("tai_chi_foundations"),
            width - Scale(152n),
            State_course_view.course.font + Scale(2n)
        ) + Scale(24n);
    if (heading_h > header_h) {
        header_h = heading_h;
    }
    let y = header_h + Scale(12n);
    if (expanded) {
        y = PlanLessonGroup(0n, foundation_count, columns, width, y);
        y = y + Scale(12n);
    }
    let content_height = PlanLessonGroup(
        foundation_count,
        State_course_view.lesson_total - foundation_count,
        columns,
        width,
        y
    );
    let scrolled = NativeScroll.Draw(State_course_view.course.session, {
        key: NativeLayout.KeyHash("inbe/tai_chi/lessons"),
        bounds: bounds,
        content_height: content_height,
        scroll_offset: State_course_view.course.lesson_scroll
    });
    State_course_view.course.lesson_scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    FoundationHeader(Bounds(s32(scrolled.content.x), s32(scrolled.content.y), width, header_h));
    let first = expanded ? 0n : foundation_count;
    for (let position = s32(first); position < State_course_view.lesson_total; position += s32(1)) {
        let index = nativeAt(State_course_view.lesson_indices, position);
        let card = nativeAt(State_course_view.lesson_bounds, index);
        card.x = card.x + scrolled.content.x;
        card.y = card.y + scrolled.content.y;
        if (card.y + card.height >= bounds.y && card.y <= bounds.y + bounds.height) {
            LessonCard(
                card,
                index,
                nativeAt(State_course_view.lesson_artwork_indices, index),
                nativeAt(State_course_view.course_lessons, index)
            );
        }
    }
    End(State_course_view.course.session);
}

export function Foundations(bounds: Rectangle): void {
    let gap = Scale(10n);
    if (
        Button({
            session: State_course_view.course.session,
            props: {
                key: NativeLayout.KeyHash("inbe/tai_chi/back"),
                bounds: {
                    x: bounds.x,
                    y: bounds.y,
                    width: bounds.width,
                    height: float32(Scale(44n))
                },
                label: Locale("back_button"),
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        State_course_view.course.lesson = -1n;
        return;
    }
    bounds.y = bounds.y + float32(Scale(44n) + gap);
    bounds.height = bounds.height - float32(Scale(44n) + gap);
    let row = nativeAt(State_course_view.course_lessons, State_course_view.course.lesson);
    let width = bounds.width - float32(Scale(12n));
    let picture_h = (s32(width) * 3n) / 4n;
    if (picture_h > Scale(220n)) {
        picture_h = Scale(220n);
    }
    let summary_h = ParagraphHeight(row.summary, s32(width), State_course_view.course.font);
    let content_h = picture_h + gap + summary_h + gap + row.count * (Scale(64n) + gap);
    let scrolled = NativeScroll.Draw(State_course_view.course.session, {
        key: NativeLayout.KeyHash("inbe/tai_chi/foundation-list"),
        bounds: bounds,
        content_height: content_h,
        scroll_offset: State_course_view.course.item_scroll
    });
    State_course_view.course.item_scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let artwork: s32 = s32(8n);
    for (let index = s32(0n); index < State_course_view.course.lesson; index += s32(1)) {
        if (nativeAt(State_course_view.course_lessons, index).kind === PRACTICE_COURSE_FOUNDATION) {
            artwork = artwork + 1n;
        }
    }
    if (artwork >= 14n) {
        artwork = 8n;
    }
    let y = scrolled.content.y;
    <Image
        session={State_course_view.course.session}
        props={{
            key:
                NativeLayout.KeyHash("inbe/tai_chi/foundation-detail-cover") +
                u64(State_course_view.course.lesson),
            asset_path: nativeAt(State_course_view.lesson_artwork, artwork),
            alt_text: row.title,
            bounds: { x: scrolled.content.x, y: y, width: width, height: float32(picture_h) },
            radius: float32(Scale(8n)),
            smooth: true,
            tint: u32(0xffffffffn),
            fit: NativeImage.ImageFit.ImageFitCover
        }}
    />;
    y = y + float32(picture_h + gap);
    <Text
        session={State_course_view.course.session}
        props={{
            text: row.summary,
            size: State_course_view.course.font,
            bounds: { x: scrolled.content.x, y: y, width: width, height: float32(summary_h) }
        }}
    />;
    y = y + float32(summary_h + gap);
    for (let offset = s32(0n); offset < row.count; offset += s32(1)) {
        let item = row.first + offset;
        if (y + float32(Scale(64n)) >= bounds.y && y <= bounds.y + bounds.height) {
            let detail = ReadPracticeCourseRowHost(false, item);
            if (
                Button({
                    session: State_course_view.course.session,
                    props: {
                        key: NativeLayout.KeyHash("inbe/tai_chi/foundation") + u64(item),
                        bounds: {
                            x: scrolled.content.x,
                            y: y,
                            width: width,
                            height: float32(Scale(64n))
                        },
                        label: detail.title,
                        detail: detail.detail,
                        selected: detail.done,
                        content_alignment: ContentAlignment.ContentAlignmentStart,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }
                })
            ) {
                Play(item);
            }
        }
        y = y + float32(Scale(64n) + gap);
    }
    End(State_course_view.course.session);
}

export function Course(): void {
    let width = State_course_view.course.view_width - Scale(32n);
    if (width > Scale(940n)) {
        width = Scale(940n);
    }
    let height = State_course_view.course.view_height - Scale(48n);
    if (height > Scale(740n)) {
        height = Scale(740n);
    }
    let title =
        State_course_view.course.lesson < 0n
            ? Locale("tai_chi_course_title")
            : nativeAt(State_course_view.course_lessons, State_course_view.course.lesson).title;
    let frame = NativeModal.Draw(State_course_view.course.session, {
        key: NativeLayout.KeyHash("inbe/tai_chi/modal"),
        title: title,
        width: width,
        height: height,
        scale: State_course_view.course.scale,
        title_at_start: true,
        strong_title: true,
        dismiss_on_outside: true,
        has_right_action: true,
        right_label: Locale("close_button")
    });
    if (frame.dismissed || frame.right_clicked) {
        State_course_view.course.action = PRACTICE_COURSE_CLOSE;
        return;
    }
    if (!frame.opened) {
        return;
    }
    let bounds = frame.layout.content;
    if (State_course_view.course.lesson < 0n) {
        if (!State_course_view.course.owned) {
            let intro = Locale("tai_chi_course_intro");
            let intro_h = ParagraphHeight(intro, s32(bounds.width), State_course_view.course.font);
            <Text
                session={State_course_view.course.session}
                props={{
                    text: intro,
                    size: State_course_view.course.font,
                    bounds: {
                        x: bounds.x,
                        y: bounds.y,
                        width: bounds.width,
                        height: float32(intro_h)
                    }
                }}
            />;
            bounds.y = bounds.y + float32(intro_h + Scale(12n));
            bounds.height = bounds.height - float32(intro_h + Scale(12n));
        }
        <Text
            session={State_course_view.course.session}
            props={{
                text: State_course_view.course.progress,
                size: State_course_view.course.small_font,
                class_name: State_course_view.course.muted_class,
                bounds: {
                    x: bounds.x,
                    y: bounds.y,
                    width: bounds.width,
                    height: float32(Scale(28n))
                }
            }}
        />;
        bounds.y = bounds.y + float32(Scale(36n));
        bounds.height = bounds.height - float32(Scale(36n));
        Lessons(bounds);
    } else {
        Foundations(bounds);
    }
    End(State_course_view.course.session);
}
