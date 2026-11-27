import { SettingsBreaksNewBlockOptions } from "settings_breaks";
import { SettingsBreaksNewSummary48u8 } from "settings_breaks";
import { SettingsBreaksNewPostponed } from "settings_breaks";
import { SettingsBreaksNewSkipped } from "settings_breaks";
import { SettingsBreaksNewTaken } from "settings_breaks";
import { SettingsBreaksNewRows } from "settings_breaks";
import { SettingsBreaksNewSummary } from "settings_breaks";
import { SettingsBreaksNewNames } from "settings_breaks";
import { ArrowDirection } from "kryon/button";
// Authored UI composition; native application state remains in settings_breaks.zi.
import * as NativeButton from "kryon/button";
import * as NativeDropdown from "kryon/dropdown";
import * as NativeProgress from "kryon/progress";
import * as NativeText from "kryon/text";
import * as State_settings_breaks from "settings_breaks";
import { InnerBreeze } from "app_types";
import { BreakFormatDuration, BreakNextDueSeconds, BreakSetMode } from "break_rules";
import { storage_break_history } from "break_stats";
import { BREAK_DAILY, BREAK_REST, BREAK_TYPE_COUNT, BreakModeNormal } from "break_types";
import { ButtonEmphasis, ButtonTone, ContentAlignment } from "kryon/control_props";
import { TextAlign } from "kryon/text_align";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { Progress } from "kryon/tsx/progress";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppScale, AppSmallFontSize } from "metrics";
import {
    SETTINGS_BREAKS_TIMER_ROW,
    settings_breaks_button_row_height,
    settings_breaks_expanded_toggle,
    settings_breaks_general_body,
    settings_breaks_status_body,
    settings_breaks_status_row_height,
    settings_breaks_timer_expanded,
    settings_breaks_timer_header,
    settings_breaks_timer_summary,
    settings_breaks_week_body,
    settings_breaks_week_row_height
} from "settings_breaks";
import { commit_toggle_row, settings_section_end, settings_section_inner_width } from "settings_ui";
import {
    settings_choice_rowView as settings_choice_row,
    settings_row_dividerView as settings_row_divider,
    settings_section_beginView as settings_section_begin
} from "settings_ui_ui";
import { AppTextFromCString, FormatArg, FormatTemplate, FrameTextHold } from "text_buffers";

export function settings_breaks_draw_status(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("settings_breaks_status"),
        settings_breaks_status_body()
    );
    let ix = section.inner_x;
    let iw = section.inner_width;
    let names = SettingsBreaksNewNames();
    nativeSet(names, 0n, LocaleText("break_micro_title"));
    nativeSet(names, 1n, LocaleText("break_rest_title"));
    nativeSet(names, 2n, LocaleText("break_daily_title"));
    let row_h = settings_breaks_status_row_height();
    let bar_width = (iw * 2n) / 5n;
    let due_width = AppScale(72n);
    let bar_x = ix + iw - bar_width;
    let name_width = iw - bar_width - due_width - AppScale(24n);
    nativeDeref(y) = nativeDeref(y) + AppScale(8n);
    for (let index = s32(0); index <= BREAK_TYPE_COUNT - 1n; index += s32(1)) {
        let timer = nativeAt(nativeDeref(app).breaks.timers, index);
        let next = BreakNextDueSeconds(app.breaks, s32(index));
        let due: string = "";
        if (timer.enabled === 0n || next < 0n) {
            due = LocaleText("settings_breaks_timer_off");
        } else if (next === 0n) {
            due = LocaleText("settings_breaks_due_now");
        } else {
            let duration = BreakFormatDuration(next);
            due = FrameTextHold(
                nativeRef(app.ui.frame_text),
                AppTextFromCString(nativeRef(nativeAt(duration.bytes, 0n)), 16n)
            );
        }
        let name_props: NativeText.Props = {};
        name_props.text = nativeAt(names, index);
        name_props.size = AppSmallFontSize();
        name_props.vertical_align = TextAlign.TextAlignCenter;
        name_props.bounds = {
            x: float32(ix),
            y: float32(nativeDeref(y)),
            width: float32(name_width),
            height: float32(row_h)
        };
        <Text session={app.ui.session} props={name_props} />;
        let due_props: NativeText.Props = {};
        due_props.text = due;
        due_props.size = AppSmallFontSize();
        due_props.align = TextAlign.TextAlignEnd;
        due_props.vertical_align = TextAlign.TextAlignCenter;
        due_props.bounds = {
            x: float32(bar_x - AppScale(12n) - due_width),
            y: float32(nativeDeref(y)),
            width: float32(due_width),
            height: float32(row_h)
        };
        <Text session={app.ui.session} props={due_props} />;
        if (timer.limit_s > 0n) {
            let progress: NativeProgress.Props = {};
            progress.bounds = {
                x: float32(bar_x),
                y: float32(nativeDeref(y) + (row_h - AppScale(8n)) / 2n),
                width: float32(bar_width),
                height: float32(AppScale(8n))
            };
            progress.min = 0n;
            progress.max = timer.limit_s;
            progress.value = timer.active_s;
            <Progress session={app.ui.session} props={progress} />;
        }
        nativeDeref(y) = nativeDeref(y) + row_h;
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(8n);
    settings_row_divider(app, section, nativeDeref(y));
    let rest: NativeButton.Props = {};
    rest.id = 545n;
    rest.bounds = {
        x: float32(ix),
        y: float32(nativeDeref(y) + AppScale(10n)),
        width: float32(iw),
        height: float32(AppScale(36n))
    };
    rest.label = LocaleText("settings_breaks_rest_now");
    rest.tone = ButtonTone.ButtonToneNeutral;
    rest.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    if (Button({ session: app.ui.session, props: rest })) {
        app.ui.rest_break_requested = true;
    }
    nativeDeref(y) = nativeDeref(y) + settings_breaks_button_row_height();
    settings_section_end(y);
}

export function settings_breaks_draw_timer_row(
    app: NativeRef<InnerBreeze>,
    index: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let summary = SettingsBreaksNewSummary();
    let expanded = settings_breaks_timer_expanded(index);
    let row: NativeButton.Props = {};
    row.id = 546n + index;
    row.key = u64(546n + index);
    row.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y)),
        width: float32(width),
        height: float32(AppScale(SETTINGS_BREAKS_TIMER_ROW))
    };
    row.label = settings_breaks_timer_header(index);
    row.detail = settings_breaks_timer_summary(app, index, nativeSlice(summary));
    row.content_alignment = ContentAlignment.ContentAlignmentStart;
    row.tone = ButtonTone.ButtonToneNeutral;
    row.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    row.arrow = true;
    row.direction = expanded ? ArrowDirection.ArrowDown : ArrowDirection.ArrowRight;
    if (Button({ session: app.ui.session, props: row })) {
        State_settings_breaks.settings_breaks_expanded = settings_breaks_expanded_toggle(
            State_settings_breaks.settings_breaks_expanded,
            index
        );
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(SETTINGS_BREAKS_TIMER_ROW);
}

export function settings_breaks_draw_week(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let rows = SettingsBreaksNewRows();
    let count = storage_break_history(7n, nativeRef(nativeAt(rows, 0n)), 42n);
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("settings_breaks_week_stats"),
        settings_breaks_week_body(count > 0n)
    );
    let ix = section.inner_x;
    let iw = section.inner_width;
    let row_h = settings_breaks_week_row_height();
    nativeDeref(y) = nativeDeref(y) + AppScale(6n);
    if (count <= 0n) {
        let empty: NativeText.Props = {};
        empty.text = LocaleText("settings_breaks_no_data");
        empty.size = AppSmallFontSize();
        empty.vertical_align = TextAlign.TextAlignCenter;
        empty.bounds = {
            x: float32(ix),
            y: float32(nativeDeref(y)),
            width: float32(iw),
            height: float32(row_h)
        };
        <Text session={app.ui.session} props={empty} />;
        nativeDeref(y) = nativeDeref(y) + (row_h + AppScale(6n));
        settings_section_end(y);
        return;
    }
    let taken = SettingsBreaksNewTaken();
    let skipped = SettingsBreaksNewSkipped();
    let postponed = SettingsBreaksNewPostponed();
    let index: s32 = s32(0n);
    while (index < count) {
        let kind = nativeAt(rows, index).break_type;
        if (kind >= 0n && kind < BREAK_TYPE_COUNT) {
            nativeSet(
                taken,
                kind,
                nativeAt(taken, kind) +
                    (nativeAt(rows, index).taken + nativeAt(rows, index).natural)
            );
            nativeSet(skipped, kind, nativeAt(skipped, kind) + nativeAt(rows, index).skipped);
            nativeSet(postponed, kind, nativeAt(postponed, kind) + nativeAt(rows, index).postponed);
        }
        index = index + 1n;
    }
    for (let kind = s32(0); kind <= BREAK_TYPE_COUNT - 1n; kind += s32(1)) {
        let name: string = LocaleText("break_micro_title");
        if (kind === BREAK_REST) {
            name = LocaleText("break_rest_title");
        }
        if (kind === BREAK_DAILY) {
            name = LocaleText("break_daily_title");
        }
        let summary = SettingsBreaksNewSummary48u8();
        let summary_args: [FormatArg, FormatArg, FormatArg] = [
            { number: nativeAt(taken, kind) },
            { number: nativeAt(skipped, kind) },
            { number: nativeAt(postponed, kind) }
        ];
        FormatTemplate("%d / %d / %d", nativeSlice(summary_args), nativeSlice(summary));
        let name_props: NativeText.Props = {};
        name_props.text = name;
        name_props.size = AppSmallFontSize();
        name_props.vertical_align = TextAlign.TextAlignCenter;
        name_props.bounds = {
            x: float32(ix),
            y: float32(nativeDeref(y)),
            width: float32(iw / 2n),
            height: float32(row_h)
        };
        <Text session={app.ui.session} props={name_props} />;
        let value_props: NativeText.Props = {};
        value_props.text = AppTextFromCString(nativeRef(nativeAt(summary, 0n)), 48n);
        value_props.size = AppSmallFontSize();
        value_props.align = TextAlign.TextAlignEnd;
        value_props.vertical_align = TextAlign.TextAlignCenter;
        value_props.bounds = {
            x: float32(ix + iw / 2n),
            y: float32(nativeDeref(y)),
            width: float32(iw - iw / 2n),
            height: float32(row_h)
        };
        <Text session={app.ui.session} props={value_props} />;
        nativeDeref(y) = nativeDeref(y) + row_h;
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(6n);
    settings_section_end(y);
}

export function settings_breaks_draw_general(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let inner = settings_section_inner_width(width);
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("settings_tab_breaks"),
        settings_breaks_general_body(inner)
    );
    let ix = section.inner_x;
    let iw = section.inner_width;
    let enabled = app.breaks_enabled;
    let sounds = app.break_sounds_enabled;
    let reading = app.breaks.reading_mode;
    let micro_counts = app.breaks.micro_counts_as_activity;
    if (
        commit_toggle_row(
            app,
            ix,
            iw,
            y,
            LocaleText("settings_breaks_enabled"),
            nativeRef(enabled),
            0n
        ) !== 0n
    ) {
        app.breaks_enabled = enabled;
        if (enabled === 0n) {
            app.breaks = BreakSetMode(app.breaks, BreakModeNormal, 0n);
        }
    }
    settings_row_divider(app, section, nativeDeref(y));
    let block_options = SettingsBreaksNewBlockOptions();
    nativeAt(block_options, 0n).label = LocaleText("settings_breaks_block_off");
    nativeAt(block_options, 1n).label = LocaleText("settings_breaks_block_input");
    nativeAt(block_options, 2n).label = LocaleText("settings_breaks_block_screen");
    let block: NativeDropdown.Props = {};
    block.id = 540n;
    block.bounds = settings_choice_row(app, ix, iw, y, LocaleText("settings_breaks_block_mode"));
    block.selected_index = app.break_block_mode;
    let break_mode_settings_menu = Dropdown({
        session: app.ui.session,
        props: block,
        options: nativeSlice(block_options)
    });
    if (break_mode_settings_menu.changed) {
        app.break_block_mode = break_mode_settings_menu.selected_index;
        app.settings_dirty = 1n;
    }
    settings_row_divider(app, section, nativeDeref(y));
    if (
        commit_toggle_row(
            app,
            ix,
            iw,
            y,
            LocaleText("settings_breaks_sounds"),
            nativeRef(sounds),
            0n
        ) !== 0n
    ) {
        app.break_sounds_enabled = sounds;
    }
    settings_row_divider(app, section, nativeDeref(y));
    if (
        commit_toggle_row(
            app,
            ix,
            iw,
            y,
            LocaleText("settings_breaks_reading_mode"),
            nativeRef(reading),
            0n
        ) !== 0n
    ) {
        app.breaks.reading_mode = reading;
    }
    settings_row_divider(app, section, nativeDeref(y));
    if (
        commit_toggle_row(
            app,
            ix,
            iw,
            y,
            LocaleText("settings_breaks_micro_counts"),
            nativeRef(micro_counts),
            0n
        ) !== 0n
    ) {
        app.breaks.micro_counts_as_activity = micro_counts;
    }
    settings_section_end(y);
}
