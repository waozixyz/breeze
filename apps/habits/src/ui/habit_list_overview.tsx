import * as Shared from "habit_shared";
import * as Model from "habit_list_view";
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
    let released = Model.FollowDrag();
    let active = Model.NewActive();
    let active_count = Model.ActiveIndices(nativeSlice(active));
    let selected_position: s32 = s32(-1n);
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        if (nativeAt(active, position) === list_state.selected) {
            selected_position = position;
        }
    }
    let deactivated_count = Model.row_count - active_count;
    let show_section = Model.row_count > 0n;
    let list_y = summary_y + Model.Scale(54n);
    let list_bottom = y + height;
    let header_height = Model.Scale(Model.LIST_TABLE_HEADER_HEIGHT);
    let rows_y = list_y + header_height;
    if (list_bottom < rows_y) {
        list_bottom = rows_y;
    }
    let viewport = Shared.Bounds(x, rows_y, width, list_bottom - rows_y);
    let row_height = Model.Scale(Model.LIST_ROW_HEIGHT);
    let detail_height: s32 = s32(0n);
    if (selected_position >= 0n) {
        detail_height = Model.RowDetailHeight(nativeAt(active, selected_position));
    }
    let active_height = active_count * row_height + detail_height;
    if (active_count === 0n) {
        active_height = Model.Scale(80n);
    }
    let section_height: s32 = s32(0n);
    let inactive_row_height = Model.Scale(Model.LIST_DEACTIVATED_ROW_HEIGHT);
    if (show_section) {
        section_height = Model.Scale(Model.LIST_INACTIVE_HEADER_HEIGHT);
        if (list_state.show_deactivated) {
            section_height +=
                Model.Scale(Model.LIST_DEACTIVATED_HINT_HEIGHT) +
                deactivated_count * inactive_row_height;
        }
    }
    let content_height = active_height + section_height;
    let keep_scrollbar =
        Model.OpenHeight(nativeSlice(active), active_count, deactivated_count) >
        s32(viewport.height);
    let panel_rows_height = content_height;
    if (panel_rows_height > s32(viewport.height)) {
        panel_rows_height = s32(viewport.height);
    }
    <Box
        session={list_state.session}
        props={{
            bounds: Shared.Bounds(x, list_y, width, header_height + panel_rows_height),
            fill: list_state.surface_color,
            border: Shared.Alpha(list_state.text_color, 0.12),
            radius: float32(Model.Scale(14n))
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
        bounds: Shared.Bounds(x, rows_y, width, panel_rows_height),
        content_height: content_height,
        keep_scrollbar: keep_scrollbar,
        scroll_offset: list_state.scroll
    });
    list_state.scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let pad = Model.Scale(12n);
    let table_x = s32(scrolled.content.x);
    let table_width = s32(scrolled.content.width);
    let name_preferred: s32 = Model.LIST_NAME_PREFERRED_WIDTH;
    if (list_state.name_width > 0n) {
        name_preferred = list_state.name_width;
    }
    if (name_preferred < Model.LIST_NAME_MIN_WIDTH) {
        name_preferred = Model.LIST_NAME_MIN_WIDTH;
    }
    if (name_preferred > Model.LIST_NAME_MAXIMUM_WIDTH) {
        name_preferred = Model.LIST_NAME_MAXIMUM_WIDTH;
    }
    let layout = HabitTableLayoutFor(
        table_width - pad * 2n,
        Model.Scale(name_preferred),
        Model.Scale(Model.LIST_NAME_MIN_WIDTH),
        Model.Scale(Model.LIST_ICON_COLUMN_WIDTH),
        Model.Scale(Model.LIST_DAY_MIN_WIDTH),
        Model.Scale(Model.LIST_DAY_MAX_WIDTH)
    );
    if (active_count === 0n) {
        <Text
            session={list_state.session}
            props={{
                bounds: Shared.Bounds(
                    table_x + pad,
                    s32(scrolled.content.y) + Model.Scale(10n),
                    table_width - pad * 2n,
                    Model.Scale(48n)
                ),
                text: Model.Locale("habit_empty_title"),
                size: list_state.font,
                wrap: NativeText.Wrap.TextWrapNone
            }}
        />;
    }
    let cards = Model.NewCards();
    for (let position = s32(0n); position < active_count; position += s32(1)) {
        let index = nativeAt(active, position);
        let open = position === selected_position;
        let row = Shared.Bounds(
            table_x,
            s32(scrolled.content.y) +
                HabitRowOffset(position, selected_position, row_height, detail_height),
            table_width,
            row_height
        );
        nativeSet(cards, position, row);
        if (position > 0n) {
            Fill(
                Shared.Bounds(table_x + pad, s32(row.y), table_width - pad * 2n, Model.Hairline()),
                0.0,
                Shared.Alpha(list_state.text_color, 0.08)
            );
        }
        if (position === 0n) {
            list_state.anchor_table = row;
        }
        if (Row(index, position === 0n, row, layout, pad, open)) {
            Model.Ask(open ? HABITS_LIST_CLOSE : HABITS_LIST_OPEN, index, 0n);
        }
        if (open) {
            RowDetail(
                index,
                position === 0n,
                Shared.Bounds(table_x, s32(row.y + row.height), table_width, detail_height),
                pad
            );
        }
    }
    let section = Shared.Bounds(
        table_x,
        s32(scrolled.content.y) + active_height,
        table_width,
        section_height
    );
    if (show_section) {
        Fill(
            Shared.Bounds(table_x, s32(section.y), table_width, Model.Hairline()),
            0.0,
            Shared.Alpha(list_state.text_color, 0.12)
        );
        InactiveHeader(
            Shared.Bounds(
                table_x,
                s32(section.y),
                table_width,
                Model.Scale(Model.LIST_INACTIVE_HEADER_HEIGHT)
            ),
            deactivated_count,
            pad
        );
    }
    if (show_section && list_state.show_deactivated) {
        let row_y = s32(section.y) + Model.Scale(Model.LIST_INACTIVE_HEADER_HEIGHT);
        <Text
            session={list_state.session}
            props={{
                bounds: Shared.Bounds(
                    table_x + pad,
                    row_y,
                    table_width - pad * 2n,
                    Model.Scale(Model.LIST_DEACTIVATED_HINT_HEIGHT)
                ),
                text: Model.Locale("habits_deactivated_hint"),
                size: list_state.small_font,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        row_y += Model.Scale(Model.LIST_DEACTIVATED_HINT_HEIGHT);
        for (let index = s32(0n); index < Model.row_count; index += s32(1)) {
            if (nativeAt(rows, index).deactivated) {
                DeactivatedRow(
                    index,
                    Shared.Bounds(table_x, row_y, table_width, inactive_row_height)
                );
                row_y += inactive_row_height;
            }
        }
    }
    End(list_state.session);
    TableHeader(table_x + pad + layout.name_width, list_y, layout, header_height);
    NameResize(table_x + pad + layout.name_width, list_y, header_height, layout.name_width);
    Fill(
        Shared.Bounds(x, rows_y, width, Model.Hairline()),
        0.0,
        Shared.Alpha(list_state.text_color, 0.12)
    );
    Drop(
        viewport,
        scrolled.max_scroll,
        nativeSlice(cards),
        active_count,
        Model.Intersection(section, scrolled.viewport),
        released
    );
}
