import * as Model from "habit_list_view";
import {
    ActiveIndices,
    Alpha,
    Ask,
    Bounds,
    FollowDrag,
    Hairline,
    Intersection,
    LIST_DAY_MAX_WIDTH,
    LIST_DAY_MIN_WIDTH,
    LIST_DEACTIVATED_HINT_HEIGHT,
    LIST_DEACTIVATED_ROW_HEIGHT,
    LIST_ICON_COLUMN_WIDTH,
    LIST_INACTIVE_HEADER_HEIGHT,
    LIST_NAME_MAXIMUM_WIDTH,
    LIST_NAME_MIN_WIDTH,
    LIST_NAME_PREFERRED_WIDTH,
    LIST_ROW_HEIGHT,
    LIST_TABLE_HEADER_HEIGHT,
    Locale,
    NewActive,
    NewCards,
    OpenHeight,
    RowDetailHeight,
    Scale
} from "habit_list_view";
import { HABITS_LIST_CLOSE, HABITS_LIST_NONE, HABITS_LIST_OPEN } from "habits_types";
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Text } from "kryon/tsx/text";
import { HabitRowOffset, HabitTableLayoutFor } from "table_layout";
import { Fill } from "habit_list_visuals";
import { TableHeader, NameResize, Row, RowDetail } from "habit_list_rows";
import { DeactivatedRow, InactiveHeader, Drop } from "habit_list_drag";
import { DrawHabitsSummary } from "habit_list_summary";

export function Overview(): void {
    const rows = Model.Rows();
    const list_state = Model.CurrentList();
    let x = s32(list_state.bounds.x);
    let y = s32(list_state.bounds.y);
    let width = s32(list_state.bounds.width);
    let height = s32(list_state.bounds.height);
    let summary_y = DrawHabitsSummary(x, y, width);
    if (list_state.action !== HABITS_LIST_NONE) {
        return;
    }
    let released = FollowDrag();
    let active = NewActive();
    let active_count = ActiveIndices(active[:]);
    let selected_position: s32 = -1n;
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        if (active[position] === list_state.selected) {
            selected_position = position;
        }
    }
    let deactivated_count = Model.row_count - active_count;
    let show_section = Model.row_count > 0n;
    let list_y = summary_y + Scale(54n);
    let list_bottom = y + height;
    let header_height = Scale(LIST_TABLE_HEADER_HEIGHT);
    let rows_y = list_y + header_height;
    if (list_bottom < rows_y) {
        list_bottom = rows_y;
    }
    let viewport = Bounds(x, rows_y, width, list_bottom - rows_y);
    let row_height = Scale(LIST_ROW_HEIGHT);
    let detail_height: s32 = 0n;
    if (selected_position >= 0n) {
        detail_height = RowDetailHeight(active[selected_position]);
    }
    let active_height = active_count * row_height + detail_height;
    if (active_count === 0n) {
        active_height = Scale(80n);
    }
    let section_height: s32 = 0n;
    let inactive_row_height = Scale(LIST_DEACTIVATED_ROW_HEIGHT);
    if (show_section) {
        section_height = Scale(LIST_INACTIVE_HEADER_HEIGHT);
        if (list_state.show_deactivated) {
            section_height +=
                Scale(LIST_DEACTIVATED_HINT_HEIGHT) + deactivated_count * inactive_row_height;
        }
    }
    let content_height = active_height + section_height;
    let keep_scrollbar =
        OpenHeight(active[:], active_count, deactivated_count) >
        s32(viewport.height);
    let panel_rows_height = content_height;
    if (panel_rows_height > s32(viewport.height)) {
        panel_rows_height = s32(viewport.height);
    }
    <Box
        session={list_state.session}
        props={{
            bounds: Bounds(x, list_y, width, header_height + panel_rows_height),
            fill: list_state.surface_color,
            border: Alpha(list_state.text_color, 0.12),
            radius: float32(Scale(14n))
        }}
    />;
    if (list_state.reveal_selected) {
        list_state.reveal_selected = false;
        if (selected_position >= 0n) {
            let card_top = HabitRowOffset(
                selected_position,
                selected_position,
                row_height,
                detail_height
            );
            let card_bottom = card_top + row_height + detail_height;
            let view_height = s32(viewport.height);
            if (card_bottom - list_state.scroll > view_height) {
                list_state.scroll = card_bottom - view_height;
            }
            if (card_top < list_state.scroll) {
                list_state.scroll = card_top;
            }
            if (list_state.scroll > content_height - view_height) {
                list_state.scroll = content_height - view_height;
            }
            if (list_state.scroll < 0n) {
                list_state.scroll = 0n;
            }
        }
    }
    let scrolled = NativeScroll.Draw(list_state.session, {
        key: NativeLayout.KeyHash("inbe/habits/overview"),
        bounds: Bounds(x, rows_y, width, panel_rows_height),
        content_height: content_height,
        keep_scrollbar: keep_scrollbar,
        scroll_offset: list_state.scroll
    });
    list_state.scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let pad = Scale(12n);
    let table_x = s32(scrolled.content.x);
    let table_width = s32(scrolled.content.width);
    let name_preferred: s32 = LIST_NAME_PREFERRED_WIDTH;
    if (list_state.name_width > 0n) {
        name_preferred = list_state.name_width;
    }
    if (name_preferred < LIST_NAME_MIN_WIDTH) {
        name_preferred = LIST_NAME_MIN_WIDTH;
    }
    if (name_preferred > LIST_NAME_MAXIMUM_WIDTH) {
        name_preferred = LIST_NAME_MAXIMUM_WIDTH;
    }
    let layout = HabitTableLayoutFor(
        table_width - pad * 2n,
        Scale(name_preferred),
        Scale(LIST_NAME_MIN_WIDTH),
        Scale(LIST_ICON_COLUMN_WIDTH),
        Scale(LIST_DAY_MIN_WIDTH),
        Scale(LIST_DAY_MAX_WIDTH)
    );
    if (active_count === 0n) {
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(
                    table_x + pad,
                    s32(scrolled.content.y) + Scale(10n),
                    table_width - pad * 2n,
                    Scale(48n)
                ),
                text: Locale("habit_empty_title"),
                size: list_state.font,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    let cards = NewCards();
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        let index = active[position];
        let open = position === selected_position;
        let row = Bounds(
            table_x,
            s32(scrolled.content.y) +
                HabitRowOffset(position, selected_position, row_height, detail_height),
            table_width,
            row_height
        );
        cards[position] = row;
        if (position > 0n) {
            Fill(
                Bounds(table_x + pad, s32(row.y), table_width - pad * 2n, Hairline()),
                0.0,
                Alpha(list_state.text_color, 0.08)
            );
        }
        if (position === 0n) {
            list_state.anchor_table = row;
        }
        if (Row(index, position === 0n, row, layout, pad, open)) {
            Ask(open ? HABITS_LIST_CLOSE : HABITS_LIST_OPEN, index, 0n);
        }
        if (open) {
            RowDetail(
                index,
                position === 0n,
                Bounds(table_x, s32(row.y + row.height), table_width, detail_height),
                pad
            );
        }
    }
    let section = Bounds(
        table_x,
        s32(scrolled.content.y) + active_height,
        table_width,
        section_height
    );
    if (show_section) {
        Fill(
            Bounds(table_x, s32(section.y), table_width, Hairline()),
            0.0,
            Alpha(list_state.text_color, 0.12)
        );
        InactiveHeader(
            Bounds(table_x, s32(section.y), table_width, Scale(LIST_INACTIVE_HEADER_HEIGHT)),
            deactivated_count,
            pad
        );
    }
    if (show_section && list_state.show_deactivated) {
        let row_y = s32(section.y) + Scale(LIST_INACTIVE_HEADER_HEIGHT);
        <Text
            session={list_state.session}
            props={{
                bounds: Bounds(
                    table_x + pad,
                    row_y,
                    table_width - pad * 2n,
                    Scale(LIST_DEACTIVATED_HINT_HEIGHT)
                ),
                text: Locale("habits_deactivated_hint"),
                size: list_state.small_font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        row_y += Scale(LIST_DEACTIVATED_HINT_HEIGHT);
        for (let index = s32(0n); index < Model.row_count; index += s32(1)) {
            if (rows[index].deactivated) {
                DeactivatedRow(index, Bounds(table_x, row_y, table_width, inactive_row_height));
                row_y += inactive_row_height;
            }
        }
    }
    End(list_state.session);
    TableHeader(table_x + pad + layout.name_width, list_y, layout, header_height);
    NameResize(table_x + pad + layout.name_width, list_y, header_height, layout.name_width);
    Fill(Bounds(x, rows_y, width, Hairline()), 0.0, Alpha(list_state.text_color, 0.12));
    Drop(
        viewport,
        scrolled.max_scroll,
        cards[:],
        active_count,
        Intersection(section, scrolled.viewport),
        released
    );
}
