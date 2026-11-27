// Authored application UI. Native state and effects live in library_model.zi.
import * as NativeImage from "kryon/image";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as State from "library_model";
import { AppCopyText, AppReplaceText } from "text_buffers";
import {
    AppFieldInputHost,
    AppKeyHost,
    AppLocaleHost,
    Bounds,
    ChapterHeadingProps,
    CloseAppHost,
    EnsureAnnotation,
    LibraryBack,
    LoadPageAnnotations,
    NewMarks,
    NewOptions,
    NumberText,
    OpenBook,
    PageIndicator,
    ReaderAreaBounds,
    ReaderPalette,
    ReaderTypeface,
    ReadingProps,
    Reflow,
    SaveAnnotations,
    SaveReader,
    Scale,
    SetPictureMode,
    SmoothFramesHost,
    TurnPage
} from "library_model";
import {
    BOOK_COUNT,
    BookAuthor,
    BookChapter,
    BookChapterArt,
    BookChapterArtApproved,
    BookChapterTitle,
    BookChapters,
    BookCover,
    BookTitle,
    LibraryOverlaps,
    LibraryPage,
    LibraryPageFor
} from "books";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { ButtonEmphasis, ButtonTone, ContentAlignment, ControlSize } from "kryon/control_props";
import { Dropdown } from "kryon/tsx/dropdown";
import { Scroll } from "kryon/tsx/scroll";
import { GridCellBounds, GridRowCount, MeasureGrid } from "kryon/grid";
import { GridMetrics } from "kryon/grid_props";
import { IconType } from "kryon/icon";
import { Image } from "kryon/tsx/image";
import { KeyLeft, KeyRight } from "kryon/input_protocol";
import { Press } from "kryon/tsx/press";
import { Rectangle } from "kryon/geometry";
import { Color } from "kryon/drawing_props";
import { SamplePointer } from "kryon/pointer_input";
import { Spinbox } from "kryon/tsx/spinbox";
import { Swipe } from "kryon/swipe";
import { SwipeDirection } from "kryon/swipe_props";
import { Text } from "kryon/tsx/text";
import { TextAlign } from "kryon/text_align";
import { TextArea } from "kryon/tsx/text_area";
import { TextHeight } from "kryon/text_measure";
import { TextUntilNul } from "std/text_buffer";
import { Toggle } from "kryon/tsx/toggle";
import { TransitionSmoothProgress } from "kryon/transition";
import { WidgetPaletteRestore, WidgetPaletteUse } from "kryon/widget_palette";

// Place the illustration and title together at the center of the page.
function PicturePageView(chapter: s32): void {
    let area = ReaderAreaBounds();
    let title: NativeText.Props = {
        key: 27501n,
        text: BookChapterTitle(State.book, chapter),
        bounds: area,
        size: Scale(State.font_size + 4n),
        typeface: ReaderTypeface(),
        align: TextAlign.TextAlignCenter,
        wrap: NativeText.Wrap.TextWrapAuto
    };
    let title_height = TextHeight(State.frame.session, title);
    let gap = Scale(24n);
    let side = s32(area.height) - title_height - gap;
    if (side > s32(area.width)) {
        side = s32(area.width);
    }
    if (side < 0n) {
        side = 0n;
    }
    let top = s32(area.y) + (s32(area.height) - side - gap - title_height) / 2n;
    let left = s32(area.x) + (s32(area.width) - side) / 2n;
    <Image
        session={State.frame.session}
        props={{
            key: 27503n,
            asset_path: BookChapterArt(State.book, chapter),
            alt_text: title.text,
            bounds: Bounds(left, top, side, side),
            fit: NativeImage.ImageFit.ImageFitContain,
            smooth: true
        }}
    />;
    title.bounds = Bounds(s32(area.x), top + side + gap, s32(area.width), title_height);
    <Text session={State.frame.session} props={title} />;
}

function BookJacket(index: s32, cover: Rectangle, key: u64): void {
    <Image
        session={State.frame.session}
        props={{
            key: key,
            asset_path: BookCover(index),
            alt_text: BookTitle(index),
            bounds: cover,
            fit: NativeImage.ImageFit.ImageFitStretch,
            smooth: true
        }}
    />;
    if (cover.width < float32(Scale(80n))) {
        return;
    }
    let label_height = s32(cover.height * 0.3);
    <Box
        session={State.frame.session}
        props={{
            key: key + 1n,
            bounds: Bounds(
                s32(cover.x) + Scale(4n),
                s32(cover.y) + Scale(4n),
                s32(cover.width) - Scale(8n),
                label_height
            ),
            fill: { r: 244n, g: 233n, b: 204n, a: 245n },
            fill_bottom: { r: 244n, g: 233n, b: 204n, a: 0n },
            has_fill_bottom: true
        }}
    />;
    let palette = ReaderPalette();
    palette.text = u32(0x40372bffn);
    WidgetPaletteUse(State.frame.session, palette);
    let title_font = s32(cover.width * 0.105);
    let author_font = s32(cover.width * 0.075);
    <Text
        session={State.frame.session}
        props={{
            key: key + 2n,
            text: BookTitle(index),
            size: title_font,
            align: TextAlign.TextAlignCenter,
            bounds: Bounds(
                s32(cover.x) + Scale(8n),
                s32(cover.y) + Scale(12n),
                s32(cover.width) - Scale(16n),
                title_font + Scale(4n)
            )
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: key + 3n,
            text: BookAuthor(index),
            size: author_font,
            align: TextAlign.TextAlignCenter,
            bounds: Bounds(
                s32(cover.x) + Scale(8n),
                s32(cover.y) + Scale(18n) + title_font,
                s32(cover.width) - Scale(16n),
                author_font + Scale(4n)
            )
        }}
    />;
    WidgetPaletteRestore(State.frame.session);
}

function OpeningView(): void {
    let progress = float32((State.frame.now - State.opening_started) / 0.32);
    if (progress >= 1.0) {
        State.opening = false;
        return;
    }
    SmoothFramesHost(2n);
    let width = ReaderAreaBounds().width;
    if (width > float32(Scale(260n))) {
        width = float32(Scale(260n));
    }
    let target: Rectangle = {
        x: (float32(State.frame.width) - width) / 2.0,
        y: float32(State.frame.top) + float32(Scale(24n)),
        width: width,
        height: width * 1.5
    };
    let lift = TransitionSmoothProgress(progress / 0.45);
    let cover: Rectangle = {
        x: State.opening_from.x + (target.x - State.opening_from.x) * lift,
        y: State.opening_from.y + (target.y - State.opening_from.y) * lift,
        width: State.opening_from.width + (target.width - State.opening_from.width) * lift,
        height: State.opening_from.height + (target.height - State.opening_from.height) * lift
    };
    let turn = TransitionSmoothProgress((progress - 0.45) / 0.55);
    cover.width = cover.width * (1.0 - turn);
    if (cover.width > 1.0) {
        BookJacket(State.book, cover, 27800n);
    }
}

function ShelfView(): void {
    let area = Bounds(
        Scale(12n),
        State.frame.top + Scale(12n),
        State.frame.width - Scale(24n),
        State.frame.height - State.frame.bottom - State.frame.top - Scale(24n)
    );
    let grid = MeasureGrid({
        bounds: area,
        min_item_width: Scale(132n),
        max_columns: 5n,
        gap: Scale(28n),
        padding: Scale(20n)
    });
    let cover_width = grid.cell_width - Scale(8n);
    if (cover_width > Scale(160n)) {
        cover_width = Scale(160n);
    }
    let height = (cover_width * 3n) / 2n;
    let row_height = height + Scale(72n);
    let rows = GridRowCount(grid, BOOK_COUNT);
    let visible_rows = (s32(area.height) + row_height - 1n) / row_height;
    if (rows < visible_rows) {
        rows = visible_rows;
    }
    let content_height = rows * row_height + Scale(20n);
    <Box
        session={State.frame.session}
        props={{
            key: 27900n,
            bounds: area,
            fill: { r: 73n, g: 43n, b: 28n, a: 255n },
            fill_bottom: { r: 111n, g: 71n, b: 44n, a: 255n },
            has_fill_bottom: true
        }}
    />;
    let shelf = (
        <Scroll
            session={State.frame.session}
            props={{
                key: 27000n,
                bounds: area,
                content_height: content_height,
                scroll_offset: State.shelf_scroll,
                scale: State.frame.scale
            }}
            children={(scroll: NativeScroll.ScrollResult): void => {
                ShelfRows(scroll, grid, rows, row_height, cover_width, height);
            }}
        />
    );
    State.shelf_scroll = shelf.scroll_offset;
}

function ShelfRows(
    scroll: NativeScroll.ScrollResult,
    grid: GridMetrics,
    rows: s32,
    row_height: s32,
    cover_width: s32,
    height: s32
): void {
    State.shelf_scroll = scroll.scroll_offset;
    grid.content.y = scroll.content.y + float32(Scale(20n));
    for (let row: s32 = 0n; row < rows; row += s32(1)) {
        let x = s32(scroll.content.x);
        let y = s32(scroll.content.y) + row * row_height;
        let width = s32(scroll.content.width);
        let board = y + height + Scale(20n);
        let key = u64(28000n + row * 32n);
        <Box
            session={State.frame.session}
            props={{
                key: key,
                bounds: Bounds(x + Scale(10n), y, width - Scale(20n), row_height),
                fill: { r: 57n, g: 35n, b: 25n, a: 255n },
                fill_bottom: { r: 126n, g: 87n, b: 55n, a: 255n },
                has_fill_bottom: true
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 1n,
                bounds: Bounds(x + Scale(10n), board - Scale(14n), width - Scale(20n), Scale(14n)),
                fill: { r: 158n, g: 110n, b: 65n, a: 255n },
                fill_bottom: { r: 193n, g: 143n, b: 85n, a: 255n },
                has_fill_bottom: true
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 2n,
                bounds: Bounds(x, board, width, Scale(22n)),
                fill: { r: 163n, g: 111n, b: 63n, a: 255n },
                fill_bottom: { r: 108n, g: 65n, b: 36n, a: 255n },
                has_fill_bottom: true
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 3n,
                bounds: Bounds(x, board, width, Scale(2n)),
                fill: { r: 217n, g: 167n, b: 104n, a: 255n }
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 4n,
                bounds: Bounds(x + Scale(10n), board + Scale(22n), width - Scale(20n), Scale(18n)),
                fill: { r: 25n, g: 15n, b: 10n, a: 120n },
                fill_bottom: { r: 25n, g: 15n, b: 10n, a: 0n },
                has_fill_bottom: true
            }}
        />;
        for (let grain: s32 = 0n; grain <= 3n; grain += s32(1)) {
            <Box
                session={State.frame.session}
                props={{
                    key: key + u64(5n + grain),
                    bounds: Bounds(
                        x + Scale(8n + grain * 13n),
                        board + Scale(5n + grain * 4n),
                        width - Scale(40n + grain * 14n),
                        Scale(1n)
                    ),
                    fill: { r: 75n, g: 43n, b: 24n, a: 65n }
                }}
            />;
        }
    }
    for (let index: s32 = 0n; index < BOOK_COUNT; index += 1n) {
        let cover = GridCellBounds(grid, index, row_height - grid.gap);
        cover.width = float32(cover_width);
        cover.height = float32(height);
        let x = s32(cover.x);
        let y = s32(cover.y);
        let key = u64(29000n + index * 16n);
        <Box
            session={State.frame.session}
            props={{
                key: key,
                bounds: Bounds(x + Scale(6n), y + Scale(8n), cover_width + Scale(8n), height),
                fill: { r: 20n, g: 12n, b: 8n, a: 105n },
                radius: float32(Scale(3n))
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 1n,
                bounds: Bounds(x + Scale(5n), y + Scale(3n), cover_width, height - Scale(3n)),
                fill: { r: 221n, g: 208n, b: 171n, a: 255n },
                border: { r: 121n, g: 101n, b: 66n, a: 255n }
            }}
        />;
        let press = (
            <Press
                session={State.frame.session}
                props={{
                    key: u64(27010n + index),
                    bounds: cover,
                    label: BookTitle(index),
                    now: State.frame.now
                }}
            />
        );
        BookJacket(index, cover, key + 4n);
        <Box
            session={State.frame.session}
            props={{
                key: key + 2n,
                bounds: Bounds(x, y, Scale(5n), height),
                fill: { r: 18n, g: 24n, b: 17n, a: 85n }
            }}
        />;
        <Box
            session={State.frame.session}
            props={{
                key: key + 3n,
                bounds: Bounds(x + Scale(6n), y, Scale(1n), height),
                fill: { r: 255n, g: 243n, b: 192n, a: 75n }
            }}
        />;
        if (press.clicked) {
            State.opening_from = cover;
            OpenBook(index);
        }
    }
}

function AnnotationPanel(bounds: Rectangle): void {
    let y = s32(bounds.y);
    let width = s32(bounds.width);
    let current = State.pages[State.page_index];
    let input = AppFieldInputHost();
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_select_passage"),
            size: State.frame.font,
            bounds: Bounds(s32(bounds.x), y, width, Scale(32n))
        }}
    />;
    y += Scale(40n);
    let previous_start =
        State.passage_state.anchor < State.passage_state.cursor
            ? State.passage_state.anchor
            : State.passage_state.cursor;
    let previous_end =
        State.passage_state.anchor > State.passage_state.cursor
            ? State.passage_state.anchor
            : State.passage_state.cursor;
    State.passage_state = (
        <TextArea
            session={State.frame.session}
            props={{
                key: 27619n,
                focus_id: 27619n,
                bounds: Bounds(s32(bounds.x), y, width, Scale(168n)),
                value: BookChapter(State.book, current.chapter)[current.start:current.end],
                label: AppLocaleHost("library_select_passage"),
                read_only: true,
                wrap: true,
                cursor: State.passage_state.cursor,
                anchor: State.passage_state.anchor,
                focused: State.passage_state.focused,
                scroll_y: State.passage_state.scroll_y,
                selecting: State.passage_state.selecting,
                scale: State.frame.scale,
                input: {
                    left: input.left,
                    right: input.right,
                    home: input.home,
                    end: input.end,
                    shift: input.shift,
                    select_all: input.select_all,
                    copy: input.copy,
                    now_seconds: State.frame.now
                }
            }}
        />
    );
    let start =
        State.passage_state.anchor < State.passage_state.cursor
            ? State.passage_state.anchor
            : State.passage_state.cursor;
    let end =
        State.passage_state.anchor > State.passage_state.cursor
            ? State.passage_state.anchor
            : State.passage_state.cursor;
    if (end > start && (start !== previous_start || end !== previous_end) && SaveAnnotations()) {
        State.annotation_index = -1n;
        for (let index: s32 = 0n; index < State.annotation_count; index += 1n) {
            if (
                State.annotations[index].start === current.start + start &&
                State.annotations[index].end === current.start + end
            ) {
                State.annotation_index = index;
            }
        }
        State.note[0n] = 0n;
        if (State.annotation_index >= 0n) {
            AppCopyText(State.annotations[State.annotation_index].note, State.note[:]);
        }
        State.note_state = {};
    }
    y += Scale(184n);
    let selected = end > start || State.annotation_index >= 0n;
    let highlighted =
        State.annotation_index >= 0n && State.annotations[State.annotation_index].highlighted;
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_highlight"),
            size: State.frame.font,
            bounds: Bounds(s32(bounds.x), y, width - Scale(72n), Scale(48n))
        }}
    />;
    let toggle = (
        <Toggle
            session={State.frame.session}
            props={{
                key: 27620n,
                bounds: Bounds(s32(bounds.x) + width - Scale(64n), y, Scale(64n), Scale(48n)),
                label: AppLocaleHost("library_highlight"),
                value: highlighted,
                disabled: !selected
            }}
        />
    );
    if (toggle.changed && EnsureAnnotation()) {
        State.annotations[State.annotation_index].highlighted = toggle.value;
        State.annotation_dirty = true;
        SaveReader();
    }
    y += Scale(64n);
    let edit = (
        <TextArea
            session={State.frame.session}
            props={{
                key: 27621n,
                focus_id: 27621n,
                bounds: Bounds(s32(bounds.x), y, width, Scale(160n)),
                value: TextUntilNul(State.note[:]),
                label: AppLocaleHost("library_note"),
                placeholder: AppLocaleHost("library_note"),
                max_bytes: 2048n,
                max_codepoints: 2048n,
                cursor: State.note_state.cursor,
                anchor: State.note_state.anchor,
                scroll_y: State.note_state.scroll_y,
                focused: State.note_state.focused,
                composition: State.note_state.composition,
                wrap: true,
                scale: State.frame.scale,
                disabled: !selected,
                input: {
                    text: input.text,
                    paste_text: input.paste_text,
                    composition_event: input.composition_event,
                    left: input.left,
                    right: input.right,
                    home: input.home,
                    end: input.end,
                    shift: input.shift,
                    backspace: input.backspace,
                    delete_forward: input.delete_forward,
                    select_all: input.select_all,
                    copy: input.copy,
                    cut: input.cut,
                    paste: input.paste,
                    enter: input.commit,
                    escape: input.escape,
                    now_seconds: State.frame.now
                }
            }}
        />
    );
    State.note_state = edit;
    if (edit.edit.changed && EnsureAnnotation()) {
        if (
            AppReplaceText(
                State.note[:],
                edit.edit.start,
                edit.edit.end,
                edit.edit.replacement
            )
        ) {
            State.annotation_dirty = true;
        }
    }
    y += Scale(176n);
    for (let index: s32 = 0n; index < State.annotation_count; index += 1n) {
        if (
            index !== State.annotation_index &&
            LibraryOverlaps(current, State.annotations[index]) &&
            State.annotations[index].note !== ""
        ) {
            <Text
                session={State.frame.session}
                props={{
                    text: State.annotations[index].note,
                    size: State.frame.font,
                    bounds: Bounds(s32(bounds.x), y, width, Scale(100n))
                }}
            />;
            y += Scale(112n);
        }
    }
}

function FontPanel(bounds: Rectangle): void {
    let x = s32(bounds.x);
    let y = s32(bounds.y);
    let width = s32(bounds.width);
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_font_size"),
            size: State.frame.font,
            bounds: Bounds(x, y, width, Scale(28n))
        }}
    />;
    let size = (
        <Spinbox
            session={State.frame.session}
            props={{
                key: 27630n,
                bounds: Bounds(x, y + Scale(32n), width, Scale(56n)),
                label: AppLocaleHost("library_font_size"),
                min: 14n,
                max: 36n,
                step: 1n,
                value: State.font_size,
                value_text: NumberText(State.font_size)
            }}
        />
    );
    if (size.changed) {
        State.font_size = size.value;
        State.layout_width = 0n;
        State.settings_dirty = true;
    }
    let options = NewOptions();
    options[0n].label = AppLocaleHost("library_font_system");
    options[1n].label = "Noto Sans";
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_typeface"),
            size: State.frame.font,
            bounds: Bounds(x, y + Scale(112n), width, Scale(28n))
        }}
    />;
    let face = (
        <Dropdown
            session={State.frame.session}
            props={{
                key: 27631n,
                bounds: Bounds(x, y + Scale(144n), width, Scale(48n)),
                placeholder: AppLocaleHost("library_typeface"),
                selected_index: State.font_face,
                scale: State.frame.scale
            }}
            options={options[:]}
        />
    );
    if (face.changed) {
        State.font_face = face.selected_index;
        State.layout_width = 0n;
        State.settings_dirty = true;
    }
    SaveReader();
}

function LayoutPanel(bounds: Rectangle): void {
    let x = s32(bounds.x);
    let y = s32(bounds.y);
    let width = s32(bounds.width);
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_margins"),
            size: State.frame.font,
            bounds: Bounds(x, y, width, Scale(28n))
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            text: AppLocaleHost("library_line_spacing"),
            size: State.frame.font,
            bounds: Bounds(x, y + Scale(112n), width, Scale(28n))
        }}
    />;
    let inset = (
        <Spinbox
            session={State.frame.session}
            props={{
                key: 27640n,
                bounds: Bounds(x, y + Scale(32n), width, Scale(56n)),
                label: AppLocaleHost("library_margins"),
                min: 12n,
                max: 56n,
                step: 4n,
                value: State.margin,
                value_text: NumberText(State.margin)
            }}
        />
    );
    let gap = (
        <Spinbox
            session={State.frame.session}
            props={{
                key: 27641n,
                bounds: Bounds(x, y + Scale(144n), width, Scale(56n)),
                label: AppLocaleHost("library_line_spacing"),
                min: 2n,
                max: 20n,
                step: 2n,
                value: State.line_gap,
                value_text: NumberText(State.line_gap)
            }}
        />
    );
    if (inset.changed || gap.changed) {
        State.margin = inset.value;
        State.line_gap = gap.value;
        State.layout_width = 0n;
        State.settings_dirty = true;
    }
    SaveReader();
}

function ContentsPanel(bounds: Rectangle): void {
    for (let chapter: s32 = 1n; chapter <= BookChapters(State.book); chapter += s32(1)) {
        if (
            (
                <Button
                    session={State.frame.session}
                    props={{
                        id: 27200n + chapter,
                        bounds: Bounds(
                            s32(bounds.x),
                            s32(bounds.y) + (chapter - 1n) * Scale(56n),
                            s32(bounds.width),
                            Scale(48n)
                        ),
                        label: BookChapterTitle(State.book, chapter),
                        content_alignment: ContentAlignment.ContentAlignmentStart,
                        fit_content: true,
                        size: ControlSize.ControlSizeLarge,
                        selected: chapter === State.pages[State.page_index].chapter,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            TurnPage(LibraryPageFor(State.pages[:State.page_count], chapter, 0n, true));
            if (!State.save_failed) {
                State.panel_open = false;
            }
        }
    }
}

function ReaderToolbar(): void {
    let icons: [s32, s32, s32, s32] = [
        s32(IconType.IconPencil),
        s32(IconType.IconText),
        s32(IconType.IconGear),
        s32(IconType.IconManual)
    ];
    let labels: [string, string, string, string] = [
        "library_annotations",
        "library_font",
        "library_layout",
        "library_contents"
    ];
    let size = State.frame.width < Scale(360n) ? Scale(40n) : Scale(44n);
    let gap = Scale(2n);
    let left = State.frame.width - Scale(12n) - size * 6n - gap * 5n;
    for (let index: s32 = 0n; index <= 3n; index += 1n) {
        if (
            (
                <Button
                    session={State.frame.session}
                    props={{
                        id: 27700n + index,
                        bounds: Bounds(left + index * (size + gap), Scale(6n), size, size),
                        label: AppLocaleHost(labels[index]),
                        icon_type: icons[index],
                        icon_only: true,
                        size: ControlSize.ControlSizeLarge,
                        selected: State.panel_open && State.panel_tab === index,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisGhost
                    }}
                />
            ) &&
            SaveReader()
        ) {
            State.panel_open = !State.panel_open || State.panel_tab !== index;
            State.panel_tab = index;
            State.panel_scroll = 0n;
            State.reader_swipe = {};
            LoadPageAnnotations();
        }
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 27704n,
                    bounds: Bounds(left + 4n * (size + gap), Scale(6n), size, size),
                    label: AppLocaleHost(State.book_dark ? "theme_light" : "theme_dark"),
                    icon_type: s32(State.book_dark ? IconType.IconSun : IconType.IconMoon),
                    icon_only: true,
                    size: ControlSize.ControlSizeLarge,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        State.book_dark = !State.book_dark;
        State.settings_dirty = true;
        SaveReader();
    }
    if (
        BookChapterArtApproved(State.book) && (
            <Button
                session={State.frame.session}
                props={{
                    id: 27705n,
                    bounds: Bounds(left + 5n * (size + gap), Scale(6n), size, size),
                    label: AppLocaleHost(
                        State.picture_book ? "library_hide_images" : "library_show_images"
                    ),
                    icon_type: s32(IconType.IconStack),
                    icon_only: true,
                    selected: State.picture_book,
                    size: ControlSize.ControlSizeLarge,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        SetPictureMode(!State.picture_book);
    }
}

function ReaderPanel(): void {
    let bounds = ReaderAreaBounds();
    bounds.y = float32(State.frame.top + Scale(16n));
    bounds.height = float32(State.frame.height - State.frame.bottom - s32(bounds.y) - Scale(48n));
    <Text
        session={State.frame.session}
        props={{
            key: 27600n,
            text: AppLocaleHost(
                State.panel_tab === 0n
                    ? "library_annotations"
                    : State.panel_tab === 1n
                      ? "library_font"
                      : State.panel_tab === 2n
                        ? "library_layout"
                        : "library_contents"
            ),
            size: State.frame.font,
            bounds: bounds
        }}
    />;
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 27601n,
                    bounds: Bounds(
                        s32(bounds.x + bounds.width) - Scale(44n),
                        s32(bounds.y) - Scale(8n),
                        Scale(44n),
                        Scale(44n)
                    ),
                    label: AppLocaleHost("close_button"),
                    icon_type: s32(IconType.IconCheck),
                    icon_only: true,
                    size: ControlSize.ControlSizeLarge,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        ) &&
        SaveReader()
    ) {
        State.panel_open = false;
    }
    bounds.y = bounds.y + float32(Scale(48n));
    bounds.height = bounds.height - float32(Scale(48n));
    let content_height = State.panel_tab === 0n ? Scale(600n) : Scale(420n);
    if (State.panel_tab === 0n) {
        for (let index: s32 = 0n; index < State.annotation_count; index += 1n) {
            if (
                index !== State.annotation_index &&
                LibraryOverlaps(State.pages[State.page_index], State.annotations[index]) &&
                State.annotations[index].note !== ""
            ) {
                content_height += Scale(112n);
            }
        }
    }
    if (State.panel_tab === 3n) {
        content_height = BookChapters(State.book) * Scale(56n) - Scale(8n);
    }
    let tab = State.panel_tab;
    let panel = (
        <Scroll
            session={State.frame.session}
            props={{
                key: u64(27602n + State.panel_tab),
                bounds: bounds,
                content_height: content_height,
                scroll_offset: State.panel_scroll,
                scale: State.frame.scale
            }}
            children={(scroll: NativeScroll.ScrollResult): void => {
                ReaderTools(scroll, tab);
            }}
        />
    );
    State.panel_scroll = panel.scroll_offset;
}

function ReaderTools(scroll: NativeScroll.ScrollResult, tab: s32): void {
    State.panel_scroll = scroll.scroll_offset;
    if (tab === 0n) {
        AnnotationPanel(scroll.content);
    } else if (tab === 1n) {
        FontPanel(scroll.content);
    } else if (tab === 2n) {
        LayoutPanel(scroll.content);
    } else {
        ContentsPanel(scroll.content);
    }
}

function ChapterTextView(current: LibraryPage): void {
    let props: NativeText.Props = ReadingProps(current.chapter);
    props.text = BookChapter(State.book, current.chapter)[current.start:current.end];
    props.key = 27502n;
    let marks = NewMarks();
    let mark_count: s32 = s32(0);
    for (const annotation of State.annotations[:State.annotation_count]) {
        if (!annotation.highlighted || !LibraryOverlaps(current, annotation)) {
            continue;
        }
        let start = annotation.start > current.start ? annotation.start - current.start : 0n;
        let end =
            annotation.end < current.end
                ? annotation.end - current.start
                : current.end - current.start;
        let place = mark_count;
        while (place > 0n && marks[place - 1n].start > start) {
            marks[place] = marks[place - 1n];
            place -= 1n;
        }
        marks[place] = { start: start, end: end };
        mark_count += 1n;
    }
    let merged: s32 = s32(0);
    for (let index: s32 = 0n; index < mark_count; index += 1n) {
        if (merged > 0n && marks[index].start <= marks[merged - 1n].end) {
            if (marks[index].end > marks[merged - 1n].end) {
                marks[merged - 1n].end = marks[index].end;
            }
        } else {
            marks[merged] = marks[index];
            merged += 1n;
        }
    }
    props.strong = marks[:merged];
    <Text session={State.frame.session} props={ChapterHeadingProps(current.chapter)} />;
    <Text session={State.frame.session} props={props} />;
}

function ReaderView(): void {
    WidgetPaletteUse(State.frame.session, ReaderPalette());
    let paper: Color = State.book_dark
        ? { r: 40n, g: 35n, b: 29n, a: 255n }
        : { r: 248n, g: 241n, b: 224n, a: 255n };
    <Box
        session={State.frame.session}
        props={{
            key: 27500n,
            bounds: Bounds(0n, 0n, State.frame.width, State.frame.height),
            fill: paper
        }}
    />;
    if (State.opening) {
        OpeningView();
        WidgetPaletteUse(State.frame.session, ReaderPalette());
        if (State.opening) {
            return;
        }
    }
    if (!State.panel_open) {
        let previous_width = State.layout_width;
        let previous_height = State.layout_height;
        let previous_scale = State.layout_scale;
        Reflow();
        if (
            State.page_count > 0n &&
            (State.layout_width !== previous_width ||
                State.layout_height !== previous_height ||
                State.layout_scale !== previous_scale)
        ) {
            LoadPageAnnotations();
        }
    }
    if (State.page_count <= 0n) {
        return;
    }
    if (!State.panel_open && !State.opening) {
        let pointer = SamplePointer();
        let swipe = Swipe(
            {
                bounds: ReaderAreaBounds(),
                directions: u32(SwipeDirection.SwipeHorizontal),
                min_distance: float32(Scale(48n)),
                axis_bias: 1.5
            },
            State.reader_swipe,
            {
                pointer: { x: pointer.x, y: pointer.y },
                pressed: pointer.pressed,
                down: pointer.down,
                released: pointer.released,
                input_clear: true,
                owner_clear: true,
                now_seconds: State.frame.now,
                scale: State.frame.scale
            }
        );
        State.reader_swipe = swipe.gesture;
        let key = AppKeyHost();
        if (swipe.direction === SwipeDirection.SwipeLeft || key === KeyRight) {
            TurnPage(State.page_index + 1n);
        } else if (swipe.direction === SwipeDirection.SwipeRight || key === KeyLeft) {
            TurnPage(State.page_index - 1n);
        }
    }
    let current = State.pages[State.page_index];
    if (!State.panel_open) {
        if (current.picture) {
            PicturePageView(current.chapter);
        } else {
            ChapterTextView(current);
        }
    }
    ReaderToolbar();
    <Text
        session={State.frame.session}
        props={{
            key: 27511n,
            text: PageIndicator(),
            size: State.frame.font - Scale(2n),
            align: TextAlign.TextAlignCenter,
            bounds: Bounds(
                0n,
                State.frame.height - State.frame.bottom - Scale(40n),
                State.frame.width,
                Scale(32n)
            )
        }}
    />;
    if (State.panel_open) {
        ReaderPanel();
    }
    WidgetPaletteUse(State.frame.session, ReaderPalette());
    if (State.save_failed) {
        <Text
            session={State.frame.session}
            props={{
                text: AppLocaleHost("library_save_failed"),
                size: State.frame.font,
                bounds: Bounds(
                    Scale(16n),
                    State.frame.top + Scale(8n),
                    State.frame.width - Scale(216n),
                    Scale(48n)
                )
            }}
        />;
    }
}

export function LibraryViewComposition(): void {
    if (State.reading) {
        ReaderView();
    } else {
        ShelfView();
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 27710n,
                    bounds: Bounds(Scale(8n), Scale(6n), Scale(44n), Scale(44n)),
                    label: AppLocaleHost("back_button"),
                    icon_type: s32(IconType.IconLeft),
                    icon_only: true,
                    size: ControlSize.ControlSizeLarge,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        if (!LibraryBack()) {
            CloseAppHost();
        }
    }
    WidgetPaletteRestore(State.frame.session);
}
