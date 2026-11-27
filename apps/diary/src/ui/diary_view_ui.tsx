// Authored application UI. Native state and effects live in diary_view.zi.
import * as NativeCompressionIcon from "mingcute/mingcute_regular_tool";
import * as NativeImage from "kryon/image";
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as NativeTextArea from "kryon/text_area";
import * as State from "diary_view";
import { AppLocale, AppService, AppSupports } from "kryon/app_context";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import {
    DIARY_ATTACHMENT_ICON,
    DIARY_CALENDAR_ICON,
    DIARY_NEXT_ICON,
    DIARY_PHOTO_ICON,
    DIARY_PREVIOUS_ICON,
    DIARY_REDO_ICON,
    DIARY_SPELLING_ICON,
    DIARY_TIME_ICON,
    DIARY_UNDO_ICON,
    DateTitle,
    DiaryControl,
    DiaryDayLabel,
    DiaryDayPhotos,
    DiaryEditorProps,
    DiaryEdited,
    DiaryGalleryOpen,
    DiaryInsertPhoto,
    FinishView,
    HasWords,
    Scale
} from "diary_view";
import { DiaryMessage } from "diary_types";
import { Date, Next, OnOrBefore } from "diary_date";
import { Scroll } from "kryon/tsx/scroll";
import { Image } from "kryon/tsx/image";
import { MarkdownEditor } from "kryon/tsx/markdown_editor";
import { Press } from "kryon/tsx/press";
import { Rectangle } from "kryon/geometry";
import { Text } from "kryon/tsx/text";
import { TextAlign } from "kryon/text_align";
import { TextWidth } from "kryon/text_measure";

function DiaryDayGallery(
    left: float32,
    top: float32,
    width: float32,
    height: float32,
    editable: boolean
): void {
    let gap = float32(Scale(8n));
    let inner = width - float32(Scale(14n));
    let columns = s32((inner + gap) / float32(Scale(112n)));
    if (columns < 1n) {
        columns = 1n;
    }
    let tile = (inner - float32(columns - 1n) * gap) / float32(columns);
    let rows = (State.day_photo_count + columns - 1n) / columns;
    let photos = Scroll({
        session: State.frame.session,
        props: {
            key: 290302n,
            bounds: { x: left, y: top, width: width, height: height },
            scale: State.frame.scale,
            content_height: s32(float32(rows) * (tile + gap)),
            scroll_offset: State.frame.photos_scroll
        },
        children: (strip: NativeScroll.ScrollResult): void => {
            DiaryPhotoTiles(strip, columns, tile, gap, editable);
        }
    });
    State.frame.photos_scroll = photos.scroll_offset;
}

function DiaryPhotoTiles(
    strip: NativeScroll.ScrollResult,
    columns: s32,
    tile: float32,
    gap: float32,
    editable: boolean
): void {
    State.frame.photos_scroll = strip.scroll_offset;
    for (let index: s32 = s32(0n); index < State.day_photo_count; index += 1n) {
        let photo = nativeAt(State.day_photos, index);
        let bounds: Rectangle = {
            x: strip.content.x + float32(index % columns) * (tile + gap),
            y: strip.content.y + float32(index / columns) * (tile + gap),
            width: tile,
            height: tile
        };
        <Box
            session={State.frame.session}
            props={{
                key: u64(292000n + index),
                bounds: bounds,
                fill: { r: 156n, g: 156n, b: 156n, a: 36n },
                radius: float32(Scale(6n))
            }}
        />;
        if (photo.asset.count > 0n) {
            <Image
                session={State.frame.session}
                props={{
                    key: u64(292100n + index),
                    asset_path: photo.asset,
                    alt_text: photo.name,
                    bounds: bounds,
                    fit: NativeImage.ImageFit.ImageFitCover,
                    smooth: true
                }}
            />;
        }
        let press = Press({
            session: State.frame.session,
            props: {
                key: u64(292200n + index),
                id: 292200n + index,
                bounds: bounds,
                label: photo.name,
                now: State.frame.now,
                disabled: !editable
            }
        });
        if (press.clicked && !State.pending) {
            DiaryInsertPhoto(photo.destination, photo.name);
            State.frame.photos_open_day = 0n;
        }
    }
}

function DiaryAction(
    id: s32,
    label: string,
    bounds: Rectangle,
    enabled: boolean = true,
    icon: string = "",
    selected: boolean = false,
    loading: boolean = false
): void {
    if (
        Button({
            session: State.frame.session,
            props: {
                id: id,
                bounds: bounds,
                label: label,
                disabled: !enabled,
                selected: selected,
                loading: loading,
                icon_shape: icon,
                icon_only: icon !== "",
                fit_content: true,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis:
                    icon !== ""
                        ? ButtonEmphasis.ButtonEmphasisGhost
                        : ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        DiaryControl(id);
    }
}

export function DiaryViewComposition(today: Date): DiaryMessage {
    let column = NativeLayout.CenteredColumnFor(State.frame.width, Scale(640n), Scale(16n));
    let left = float32(column.x + State.frame.origin_x);
    let width = float32(column.width);
    let part = (width - float32(Scale(12n))) / 3.0;
    let compact = State.frame.height < Scale(480n);
    let top = float32(State.frame.origin_y + (compact ? Scale(4n) : Scale(12n)));
    let control = float32(Scale(44n));
    let gap = float32(Scale(8n));
    let title = DateTitle(State.state.year, State.state.month, State.state.day);
    let title_font = State.frame.font + Scale(4n);
    let title_width = float32(TextWidth(State.frame.session, { text: title, size: title_font }));
    if (title_width > width - 2.0 * (control + gap)) {
        title_width = width - 2.0 * (control + gap);
    }
    let title_left = left + (width - title_width) / 2.0;
    let compression = AppSupports("media.compression.open");
    if (compression) {
        title_width = title_width - control - gap;
        if (title_width < control) {
            title_width = control;
        }
        title_left = left + (width - control - gap - title_width) / 2.0;
        if (
            Button({
                session: State.frame.session,
                props: {
                    id: 29018n,
                    bounds: {
                        x: left + width - control,
                        y: top,
                        width: control,
                        height: control
                    },
                    label: AppLocale("media_compression_title"),
                    icon_only: true,
                    icon_shape: NativeCompressionIcon.Shape,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }
            })
        ) {
            AppService("media.compression.open", "");
        }
    }
    DiaryAction(
        29001n,
        "‹",
        { x: title_left - gap - control, y: top, width: control, height: control },
        true,
        DIARY_PREVIOUS_ICON
    );
    DiaryAction(
        29002n,
        "›",
        { x: title_left + title_width + gap, y: top, width: control, height: control },
        OnOrBefore(
            Next({ year: State.state.year, month: State.state.month, day: State.state.day }, 1n),
            today
        ) &&
            !OnOrBefore(today, {
                year: State.state.year,
                month: State.state.month,
                day: State.state.day
            }),
        DIARY_NEXT_ICON
    );
    let title_strong: [NativeText.Range] = [{ start: 0n, end: s32(title.count) }];
    <Text
        session={State.frame.session}
        props={{
            bounds: { x: title_left, y: top, width: title_width, height: control },
            text: title,
            size: title_font,
            strong: nativeSlice(title_strong),
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let tools = top + control + gap;
    let tool_gap = float32(Scale(4n));
    let tool = control;
    let today_width = float32(Scale(96n));
    let stacked = width < today_width + gap + 7.0 * tool + 6.0 * tool_gap;
    let edit_tools = tools;
    if (stacked && !State.state.calendar) {
        edit_tools += control + tool_gap;
    }
    DiaryAction(29004n, AppLocale("diary_today"), {
        x: left,
        y: tools,
        width: today_width,
        height: control
    });
    DiaryAction(
        29003n,
        AppLocale("tab_diary_calendar"),
        { x: left + today_width + gap, y: tools, width: tool, height: control },
        true,
        DIARY_CALENDAR_ICON,
        State.state.calendar
    );
    let editable = !State.state.load_error && State.state.year > 0n;
    if (!State.state.calendar) {
        let idle = editable && !State.frame.spelling_busy;
        DiaryAction(
            29014n,
            AppLocale("diary_undo"),
            {
                x: left + width - 6.0 * tool - 5.0 * tool_gap,
                y: edit_tools,
                width: tool,
                height: control
            },
            idle && State.frame.can_undo,
            DIARY_UNDO_ICON
        );
        DiaryAction(
            29015n,
            AppLocale("diary_redo"),
            {
                x: left + width - 5.0 * tool - 4.0 * tool_gap,
                y: edit_tools,
                width: tool,
                height: control
            },
            idle && State.frame.can_redo,
            DIARY_REDO_ICON
        );
        DiaryAction(
            29016n,
            AppLocale("diary_check_spelling"),
            {
                x: left + width - 4.0 * tool - 3.0 * tool_gap,
                y: edit_tools,
                width: tool,
                height: control
            },
            idle && HasWords(State.state.text) && AppSupports("text.correct.start"),
            DIARY_SPELLING_ICON,
            false,
            State.frame.spelling_busy
        );
        DiaryAction(
            29013n,
            AppLocale("diary_insert_time"),
            {
                x: left + width - 3.0 * tool - 2.0 * tool_gap,
                y: edit_tools,
                width: tool,
                height: control
            },
            !State.frame.spelling_busy,
            DIARY_TIME_ICON
        );
        DiaryAction(
            29005n,
            AppLocale("diary_attach_photo"),
            {
                x: left + width - 2.0 * tool - tool_gap,
                y: edit_tools,
                width: tool,
                height: control
            },
            AppSupports("media.pick"),
            DIARY_ATTACHMENT_ICON
        );
        DiaryDayPhotos(State.state.text);
        let gallery_label = AppLocale("diary_show_gallery");
        if (DiaryGalleryOpen()) {
            gallery_label = AppLocale("diary_hide_gallery");
        }
        DiaryAction(
            29017n,
            gallery_label,
            { x: left + width - tool, y: edit_tools, width: tool, height: control },
            editable && State.day_photo_count > 0n,
            DIARY_PHOTO_ICON,
            DiaryGalleryOpen()
        );
    }
    let content = edit_tools + control + float32(Scale(12n));
    let content_height =
        float32(State.frame.height - State.frame.bottom) - content - float32(Scale(16n));
    if (!State.state.calendar && DiaryGalleryOpen()) {
        DiaryDayGallery(
            left,
            content,
            width,
            content_height,
            editable && !State.frame.spelling_busy
        );
        return FinishView();
    }
    if (State.state.calendar) {
        let calendar = Scroll({
            session: State.frame.session,
            props: {
                key: 290300n,
                bounds: { x: left, y: content, width: width, height: content_height },
                content_height: Scale(344n),
                scroll_offset: State.frame.calendar_scroll
            },
            children: (scroll: NativeScroll.ScrollResult): void => {
                DiaryCalendar(scroll, left, width, part, today);
            }
        });
        State.frame.calendar_scroll = calendar.scroll_offset;
        return FinishView();
    }
    let notice =
        State.frame.photo_error || State.state.load_error || State.frame.spelling_notice !== "";
    let notice_room = notice ? Scale(60n) : 0n;
    let editor_height = s32(content_height) - notice_room;
    if (editor_height < Scale(120n)) {
        editor_height = Scale(120n);
    }
    let viewport = Scroll({
        session: State.frame.session,
        props: {
            key: 290301n,
            bounds: { x: left, y: content, width: width, height: content_height },
            content_height: editor_height + notice_room,
            scroll_offset: State.frame.page_scroll,
            scale: State.frame.scale
        },
        children: (page: NativeScroll.ScrollResult): void => {
            DiaryEditor(page, left, width, editor_height, editable, notice);
        }
    });
    State.frame.page_scroll = viewport.scroll_offset;
    return FinishView();
}

function DiaryCalendar(
    scroll: NativeScroll.ScrollResult,
    left: float32,
    width: float32,
    part: float32,
    today: Date
): void {
    State.frame.calendar_scroll = scroll.scroll_offset;
    let origin = scroll.content.y;
    DiaryAction(29011n, "‹", { x: left, y: origin, width: part, height: float32(Scale(44n)) });
    DiaryAction(
        29012n,
        "›",
        {
            x: left + 2.0 * (part + float32(Scale(6n))),
            y: origin,
            width: part,
            height: float32(Scale(44n))
        },
        State.state.month_year < today.year ||
            (State.state.month_year === today.year && State.state.month_number < today.month)
    );
    <Text
        session={State.frame.session}
        props={{
            bounds: {
                x: left + part,
                y: origin + float32(Scale(8n)),
                width: part,
                height: float32(Scale(32n))
            },
            text: DateTitle(State.state.month_year, State.state.month_number, 0n),
            size: State.frame.font
        }}
    />;
    let weekdays: [string, string, string, string, string, string, string] = [
        "habit_day_mon",
        "habit_day_tue",
        "habit_day_wed",
        "habit_day_thu",
        "habit_day_fri",
        "habit_day_sat",
        "habit_day_sun"
    ];
    for (let day: s32 = s32(0n); day <= s32(6n); day += s32(1)) {
        <Text
            session={State.frame.session}
            props={{
                bounds: {
                    x: left + (float32(day) * width) / 7.0,
                    y: origin + float32(Scale(52n)),
                    width: width / 7.0,
                    height: float32(Scale(24n))
                },
                text: AppLocale(nativeAt(weekdays, day)),
                size: State.frame.font
            }}
        />;
    }
    for (let day: s32 = s32(1n); day <= State.state.month_days; day += s32(1)) {
        let position = State.state.month_weekday + day - 1n;
        let day_title = DiaryDayLabel(day);
        let cell = width / 7.0;
        DiaryAction(
            29100n + day,
            day_title,
            {
                x: left + float32(position % 7n) * cell,
                y: origin + float32(Scale(80n + (position / 7n) * 44n)),
                width: cell - 2.0,
                height: float32(Scale(42n))
            },
            OnOrBefore(
                { year: State.state.month_year, month: State.state.month_number, day: day },
                today
            )
        );
    }
}

function DiaryEditor(
    page: NativeScroll.ScrollResult,
    left: float32,
    width: float32,
    editor_height: s32,
    editable: boolean,
    notice: boolean
): void {
    State.frame.page_scroll = page.scroll_offset;
    let area: NativeTextArea.Props = {};
    area.key = u64(290200n);
    area.focus_id = 29020n;
    area.bounds = { x: left, y: page.content.y, width: width, height: float32(editor_height) };
    area.value = State.state.text;
    area.label = AppLocale("tab_diary");
    area.wrap = true;
    area.scale = State.frame.scale;
    area.cursor = State.state.cursor;
    area.anchor = State.state.anchor;
    area.scroll_y = State.frame.scroll;
    area.focused = State.frame.focused;
    area.selecting = State.frame.selecting;
    area.read_only = !editable || State.frame.spelling_busy;
    area.max_bytes = 2147483646n;
    area.max_codepoints = 2147483646n;
    area.input = State.frame.input;
    let edited = MarkdownEditor({ session: State.frame.session, props: DiaryEditorProps(area) });
    DiaryEdited(edited);
    if (notice) {
        let status = State.frame.spelling_notice;
        if (State.state.load_error) {
            status = "diary_read_error";
        }
        if (State.frame.photo_error) {
            status = "diary_photo_error";
        }
        <Text
            session={State.frame.session}
            props={{
                bounds: {
                    x: left,
                    y: area.bounds.y + area.bounds.height + float32(Scale(12n)),
                    width: width,
                    height: float32(Scale(40n))
                },
                text: AppLocale(status),
                size: State.frame.font
            }}
        />;
    }
}
