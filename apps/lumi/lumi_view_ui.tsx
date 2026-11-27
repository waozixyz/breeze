// Authored application UI. Native state and effects live in lumi_view.zi.
import * as NativeConfigureIcon from "mingcute/mingcute_regular_tool";
import * as NativeConnectedIcon from "mingcute/mingcute_regular_wifi";
import * as NativeContextMenu from "kryon/context_menu";
import * as NativeDisconnectedIcon from "mingcute/mingcute_regular_wifi_off";
import * as NativeLayout from "kryon/layout";
import * as NativePress from "kryon/press";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as State from "lumi_view";
import {
    ApplyDraftEdit,
    Bounds,
    MessageTextFromBytes,
    ChartDate,
    ChartPointSummary,
    CommandPrefix,
    CommandText,
    CompletionSuggestion,
    CopyChatRow,
    CopyLumiText,
    CountText,
    DraftIntent,
    FillDraft,
    IsSelected,
    LUMI_CANDIDATES_PER_FRAME,
    LUMI_CLOSE_ICON,
    LUMI_COMMANDS_ICON,
    LUMI_COPY_ICON,
    LUMI_DELETE_ICON,
    LUMI_MENU_COMMANDS,
    LUMI_MENU_COPY,
    LUMI_SEND_ICON,
    LUMI_SWIRL_SECONDS,
    LumiAgreementHost,
    LumiDeleteRowHost,
    LumiFeedbackChoiceHost,
    LumiFirstVisibleRowHost,
    LumiLoadOlderHost,
    LumiRowOffsetHost,
    LumiViewLocaleHost,
    MenuCommands,
    MenuOpen,
    NewCorners,
    NewLinkRanges,
    NewMenuMatches,
    NewOptions,
    OpenLinkHost,
    OpenLumiSettingsHost,
    ReadLumiChatRowHost,
    ReadLumiSuggestionHabitHost,
    ReadLumiSuggestionTaskHost,
    ReadLumiUiHost,
    RowSlot,
    RowText,
    Scale,
    SelectedText,
    SelectionClear,
    SelectionSet,
    SetLumiOnlineHost,
    SlotRow,
    SmoothFramesHost,
    SweepStart,
    SweepTo,
    WriteLumiUiHost
} from "lumi_view";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Checkbox } from "kryon/tsx/checkbox";
import { ContextMenu } from "kryon/tsx/context_menu";
import { CosineDegrees, SineDegrees } from "std/math";
import { End } from "kryon/tree";
import { Scroll } from "kryon/tsx/scroll";
import { FlagIntersection, FlagShiftLeft } from "native_flags";
import { Image } from "kryon/tsx/image";
import {
    LUMI_CHAT_FEEDBACK,
    LUMI_CHAT_PROGRESS,
    LUMI_CHAT_TEXT,
    LUMI_COMPLETE_HABIT,
    LUMI_COMPLETE_TODO,
    LUMI_DIARY,
    LUMI_HABITS,
    LUMI_INPUT_MAX,
    LUMI_LISTS,
    LUMI_PRACTICES,
    LUMI_QUOTE_HEIGHT,
    LUMI_REOPEN_TODO,
    LUMI_SEND,
    LUMI_START_PRACTICE,
    LumiCommands,
    LumiMessage
} from "lumi_types";
import { LoadingIndicator } from "kryon/tsx/loading_indicator";
import {
    LumiActionAvailable,
    LumiEqual,
    LumiIntent,
    LumiStarts,
    LumiSuggests,
    LumiTrim
} from "engine";
import { LumiChartRead } from "lumi_chart";
import { LumiChatRow } from "lumi_ui_types";
import { LumiFormatInto } from "message_text";
import { LumiMascotFacingLeft } from "lumi_mascot";
import { Press } from "kryon/tsx/press";
import { Rectangle } from "kryon/geometry";
import { Text } from "kryon/tsx/text";
import { TextAlign } from "kryon/text_align";
import { TextArea } from "kryon/tsx/text_area";
import { TitleBar } from "kryon/tsx/title_bar";

function SelectionBar(x: s32, top: s32, width: s32): void {
    let control = Scale(44n);
    <Box
        session={State.frame.session}
        props={{
            key: u64(300369n),
            bounds: Bounds(0n, 0n, State.frame.width, top + control + Scale(8n)),
            fill: State.frame.background
        }}
    />;
    if (State.confirm_delete) {
        <Text
            session={State.frame.session}
            props={{
                key: u64(300370n),
                bounds: Bounds(x, top, width - Scale(216n), control),
                text: LumiViewLocaleHost("lumi_delete_confirm"),
                size: State.frame.font,
                wrap: NativeText.Wrap.TextWrapAuto,
                vertical_align: TextAlign.TextAlignCenter
            }}
        />;
        if (
            (
                <Button
                    session={State.frame.session}
                    props={{
                        id: 30020n,
                        bounds: Bounds(x + width - Scale(208n), top, Scale(100n), control),
                        label: LumiViewLocaleHost("cancel_button"),
                        fit_content: true,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            )
        ) {
            State.confirm_delete = false;
        }
        if (
            (
                <Button
                    session={State.frame.session}
                    props={{
                        id: 30021n,
                        bounds: Bounds(x + width - Scale(100n), top, Scale(100n), control),
                        label: LumiViewLocaleHost("delete_button"),
                        fit_content: true,
                        tone: ButtonTone.ButtonToneDanger,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled
                    }}
                />
            )
        ) {
            let index = State.frame.chat_count - 1n;
            while (index >= 0n) {
                if (IsSelected(index)) {
                    LumiDeleteRowHost(index);
                }
                index -= 1n;
            }
            SelectionClear();
        }
        return;
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 30022n,
                    bounds: Bounds(x, top, control, control),
                    label: LumiViewLocaleHost("lumi_cancel_selection"),
                    icon_shape: LUMI_CLOSE_ICON,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        SelectionClear();
        return;
    }
    <Box
        session={State.frame.session}
        props={{
            key: u64(300371n),
            bounds: Bounds(
                x + control + Scale(8n),
                top + Scale(6n),
                Scale(150n),
                control - Scale(12n)
            ),
            fill: { r: 156n, g: 188n, b: 143n, a: 48n },
            radius: float32(control - Scale(12n)) / 2.0
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(300372n),
            bounds: Bounds(x + control + Scale(8n), top, Scale(150n), control),
            text: CountText(LumiViewLocaleHost("lumi_selected_count"), State.selected_count),
            size: State.frame.font,
            wrap: NativeText.Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 30023n,
                    bounds: Bounds(x + width - 2n * control - Scale(4n), top, control, control),
                    label: LumiViewLocaleHost("lumi_copy"),
                    icon_shape: LUMI_COPY_ICON,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        State.pending_copy = SelectedText();
        State.copy_pending = true;
        SelectionClear();
        return;
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 30024n,
                    bounds: Bounds(x + width - control, top, control, control),
                    label: LumiViewLocaleHost("delete_button"),
                    icon_shape: LUMI_DELETE_ICON,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneDanger,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        State.confirm_delete = true;
    }
}

function Suggestion(id: s32, text: string, bounds: Rectangle, label: string = ""): boolean {
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: id,
                    bounds: bounds,
                    label: label.count > 0n ? label : text,
                    pill: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        FillDraft(text);
        return true;
    }
    return false;
}

function ProgressCard(row: LumiChatRow, index: s32, x: s32, y: s32, width: s32): void {
    let chart = LumiChartRead(row.payload);
    if (!chart.valid) {
        return;
    }
    let key = 330000n + index * 64n;
    let selection_key = NativeLayout.KeyHash(row.payload);
    let selected = State.chart_selected_key === selection_key ? State.chart_selected_point : 0n;
    if (selected < 0n || selected >= chart.count) {
        selected = 0n;
    }
    let plot_y = y + Scale(30n);
    let plot_height = Scale(130n);
    let step = float32(width) / float32(chart.count);
    for (let point: s32 = 0n; point < chart.count; point += s32(1)) {
        let left = x + s32(float32(point) * step);
        let bar_width = s32(step) - Scale(2n);
        if (bar_width < 1n) {
            bar_width = 1n;
        }
        let bar_height: s32 = 0n;
        if (chart.maximum > 0n) {
            bar_height = s32(
                (float64(chart.values[point]) / float64(chart.maximum)) * float64(plot_height)
            );
        }
        if (
            (
                <Button
                    session={State.frame.session}
                    props={{
                        id: 310000n + index * 32n + point,
                        bounds: Bounds(left, plot_y, s32(step), plot_height),
                        invisible: true
                    }}
                />
            )
        ) {
            selected = point;
            State.chart_selected_key = selection_key;
            State.chart_selected_point = point;
        }
        <Box
            session={State.frame.session}
            props={{
                key: u64(key + point),
                bounds: Bounds(left, plot_y + plot_height - bar_height, bar_width, bar_height),
                fill:
                    selected === point
                        ? { r: 93n, g: 148n, b: 110n, a: 255n }
                        : { r: 156n, g: 188n, b: 143n, a: 200n },
                radius: float32(Scale(2n))
            }}
        />;
    }
    <Box
        session={State.frame.session}
        props={{
            key: u64(key + 31n),
            bounds: Bounds(x, plot_y + plot_height, width, Scale(1n)),
            fill: { r: 156n, g: 156n, b: 156n, a: 120n }
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(key + 32n),
            bounds: Bounds(x, y, width, Scale(24n)),
            text: ChartPointSummary(chart.dates[selected], chart.values[selected]),
            size: Scale(14n)
        }}
    />;
    let half = width / 2n;
    <Text
        session={State.frame.session}
        props={{
            key: u64(key + 33n),
            bounds: Bounds(x, plot_y + plot_height + Scale(6n), half, Scale(22n)),
            text: ChartDate(chart.dates[0n]),
            size: Scale(12n)
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(key + 34n),
            bounds: Bounds(x + half, plot_y + plot_height + Scale(6n), width - half, Scale(22n)),
            text: ChartDate(chart.dates[chart.count - 1n]),
            size: Scale(12n)
        }}
    />;
    if (chart.maximum === 0n) {
        <Text
            session={State.frame.session}
            props={{
                key: u64(key + 35n),
                bounds: Bounds(x, y + Scale(196n), width, Scale(40n)),
                text: LumiViewLocaleHost("lumi_chart_empty"),
                size: Scale(14n)
            }}
        />;
    }
}

// Developer replies show the title of the feedback they answer.
function FeedbackQuote(row: LumiChatRow, index: s32, x: s32, y: s32, width: s32): void {
    let key = 440000n + index * 4n;
    let quote_height = Scale(LUMI_QUOTE_HEIGHT - 8n);
    <Box
        session={State.frame.session}
        props={{
            key: u64(key),
            bounds: Bounds(x + Scale(12n), y, width - Scale(24n), quote_height),
            fill: { r: 93n, g: 148n, b: 110n, a: 40n },
            radius: float32(Scale(6n))
        }}
    />;
    <Box
        session={State.frame.session}
        props={{
            key: u64(key + 1n),
            bounds: Bounds(x + Scale(12n), y, Scale(3n), quote_height),
            fill: { r: 93n, g: 148n, b: 110n, a: 255n },
            radius: float32(Scale(2n))
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(key + 2n),
            bounds: Bounds(x + Scale(24n), y + Scale(3n), width - Scale(40n), Scale(16n)),
            text: LumiViewLocaleHost("lumi_your_feedback"),
            size: Scale(12n),
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(key + 3n),
            bounds: Bounds(x + Scale(24n), y + Scale(20n), width - Scale(40n), Scale(18n)),
            text: row.quote,
            size: Scale(13n),
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
}

// The dots brighten and rise in the bubble that will hold the reply.
function TypingDots(x: s32, top: s32): void {
    let left = x + Scale(48n);
    let corners = NewCorners();
    <Image
        session={State.frame.session}
        props={LumiMascotFacingLeft(
            u64(300380n),
            Bounds(x, top + Scale(16n), Scale(40n), Scale(40n)),
            corners[:]
        )}
    />;
    <Box
        session={State.frame.session}
        props={{
            key: u64(300381n),
            bounds: Bounds(left, top, Scale(96n), Scale(60n)),
            fill: { r: 156n, g: 156n, b: 156n, a: 24n },
            radius: float32(Scale(16n))
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            key: u64(300382n),
            bounds: Bounds(left + Scale(14n), top + Scale(8n), Scale(68n), Scale(20n)),
            text: "Lumi",
            size: Scale(12n)
        }}
    />;
    <LoadingIndicator
        session={State.frame.session}
        props={{
            key: u64(300383n),
            bounds: Bounds(left + Scale(16n), top + Scale(34n), Scale(36n), Scale(12n)),
            now: State.frame.now,
            scale: State.frame.scale
        }}
    />;
}

function LumiAvatar(index: s32, x: s32, y: s32): void {
    let bounds = Bounds(x, y, Scale(40n), Scale(40n));
    if (State.swirl_row === index) {
        let t = (State.frame.now - State.swirl_started) / LUMI_SWIRL_SECONDS;
        if (t < 0.0 || t >= 1.0) {
            State.swirl_row = -1n;
        } else {
            let eased = t * t * (3.0 - 2.0 * t);
            let angle = float32(eased * 720.0);
            let radius = float32(Scale(14n)) * SineDegrees(float32(t * 180.0));
            bounds.x = bounds.x + radius * SineDegrees(angle);
            bounds.y = bounds.y - (radius - radius * CosineDegrees(angle));
        }
    }
    let corners = NewCorners();
    <Image
        session={State.frame.session}
        props={LumiMascotFacingLeft(u64(300400n + index * 4n), bounds, corners[:])}
    />;
    let press = (
        <Press
            session={State.frame.session}
            props={{
                key: u64(430000n + RowSlot(index) + 1n),
                bounds: Bounds(x, y, Scale(40n), Scale(40n)),
                label: "Lumi",
                now: State.frame.now
            }}
        />
    );
    if (press.clicked) {
        State.swirl_row = index;
        State.swirl_started = State.frame.now;
        SmoothFramesHost(80n);
    }
}

// A hold starts selection. While selecting, a press can sweep across several messages.
function RowPress(index: s32, bounds: Rectangle, content_y: float32): NativePress.PressResult {
    let key = index === 0n ? 0n : RowSlot(index) + 1n;
    let press = (
        <Press
            session={State.frame.session}
            props={{
                key: u64(410000n + key),
                bounds: bounds,
                label: LumiViewLocaleHost("lumi_message"),
                now: State.frame.now,
                capture: State.selecting
            }}
        />
    );
    if (!State.selecting && press.held) {
        State.selecting = true;
        State.confirm_delete = false;
        SweepStart(index, true);
    } else if (State.selecting && press.down && !State.sweeping) {
        SweepStart(index, !IsSelected(index));
    }
    if (State.sweeping && press.down) {
        State.sweep_seen = true;
        State.sweep_pointer_y = press.y;
        SweepTo(LumiFirstVisibleRowHost(s32(press.y - content_y)));
    }
    if (press.released) {
        State.sweeping = false;
    }
    if (press.right_clicked && !State.selecting) {
        State.row_menu_open = true;
        State.row_menu_slot = RowSlot(index);
        State.row_menu_x = press.x;
        State.row_menu_y = press.y;
    }
    return press;
}

// Returns the row whose text Copy selects, or -1.
function RowMenu(): s32 {
    if (!State.row_menu_open) {
        return -1n;
    }
    let index = SlotRow(State.row_menu_slot);
    if (State.selecting || index < 0n || index >= State.frame.chat_count) {
        State.row_menu_open = false;
        return -1n;
    }
    let items: [NativeContextMenu.ContextMenuItem] = [
        { id: LUMI_MENU_COPY, label: LumiViewLocaleHost("lumi_copy") }
    ];
    let menu = (
        <ContextMenu
            session={State.frame.session}
            props={{
                key: u64(380000n),
                open: true,
                x: State.row_menu_x,
                y: State.row_menu_y,
                scale: State.frame.scale
            }}
            items={items[:]}
        />
    );
    if (!menu.open) {
        State.row_menu_open = false;
    }
    return menu.activated_id === LUMI_MENU_COPY ? index : -1n;
}

function LumiTitleBar(): s32 {
    let height = Scale(52n);
    let button = Scale(40n);
    let gap = Scale(4n);
    let trailing = State.frame.connection ? 2n * button + gap : 0n;
    let options = NewOptions();
    let bar = (
        <TitleBar
            session={State.frame.session}
            props={{
                key: u64(300400n),
                title: "Lumi",
                bounds: Bounds(0n, 0n, State.frame.width, height),
                height: height,
                scale: State.frame.scale,
                trailing_width: trailing
            }}
            options={options[0n:0n]}
        />
    );
    if (!State.frame.connection || bar.trailing_bounds.width <= 0.0) {
        return height;
    }
    let area = bar.trailing_bounds;
    let top = area.y + (area.height - float32(button)) / 2.0;
    let size = float32(button);
    let state = State.frame.online ? "lumi_toggle_online" : "lumi_toggle_offline";
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    key: u64(300401n),
                    id: 30040n,
                    bounds: {
                        x: area.x + area.width - 2.0 * size - float32(gap),
                        y: top,
                        width: size,
                        height: size
                    },
                    label: LumiViewLocaleHost(state),
                    selected: State.frame.online,
                    icon_shape: State.frame.online
                        ? NativeConnectedIcon.Shape
                        : NativeDisconnectedIcon.Shape,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        SetLumiOnlineHost(!State.frame.online);
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    key: u64(300390n),
                    id: 30043n,
                    bounds: { x: area.x + area.width - size, y: top, width: size, height: size },
                    label: LumiViewLocaleHost("settings_title"),
                    icon_shape: NativeConfigureIcon.Shape,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        OpenLumiSettingsHost();
    }
    return height;
}

function LumiAgreementView(top: s32): void {
    let column = NativeLayout.CenteredColumnFor(State.frame.width, Scale(720n), Scale(16n));
    let buttons_top = State.frame.height - State.frame.bottom - Scale(16n) - Scale(48n);
    let area_height = buttons_top - Scale(12n) - top;
    if (area_height < Scale(60n)) {
        area_height = Scale(60n);
    }
    let counts = LumiFormatInto(
        State.frame.agreement_text,
        true,
        State.agreement_bytes[:],
        State.agreement_strong[:]
    );
    let width = column.width;
    let panel = (
        <Scroll
            session={State.frame.session}
            props={{
                key: 300410n,
                bounds: Bounds(column.x, top, width, area_height),
                content_height: State.frame.agreement_height,
                scroll_offset: State.agreement_scroll,
                scale: State.frame.scale
            }}
            children={(scroll: NativeScroll.ScrollResult): void => {
                LumiAgreementText(scroll, width, counts.count, counts.strong_count);
            }}
        />
    );
    State.agreement_scroll = panel.scroll_offset;
    let reading = State.frame.agreement === 2n;
    let half = (column.width - Scale(12n)) / 2n;
    let first = reading ? "lumi_agreement_withdraw" : "lumi_agreement_agree";
    let second = reading ? "close_button" : "lumi_agreement_later";
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 30041n,
                    bounds: Bounds(column.x, buttons_top, half, Scale(48n)),
                    label: LumiViewLocaleHost(first),
                    tone: reading ? ButtonTone.ButtonToneDanger : ButtonTone.ButtonToneAccent,
                    emphasis: reading
                        ? ButtonEmphasis.ButtonEmphasisSoft
                        : ButtonEmphasis.ButtonEmphasisFilled
                }}
            />
        )
    ) {
        State.agreement_scroll = 0n;
        LumiAgreementHost(reading ? 3n : 1n);
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 30042n,
                    bounds: Bounds(column.x + half + Scale(12n), buttons_top, half, Scale(48n)),
                    label: LumiViewLocaleHost(second),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        State.agreement_scroll = 0n;
        LumiAgreementHost(reading ? 4n : 2n);
    }
}

function LumiAgreementText(
    scroll: NativeScroll.ScrollResult,
    width: s32,
    count: s32,
    strong_count: s32
): void {
    State.agreement_scroll = scroll.scroll_offset;
    <Text
        session={State.frame.session}
        props={{
            key: u64(300411n),
            bounds: {
                x: scroll.content.x,
                y: scroll.content.y,
                width: float32(width - Scale(24n)),
                height: float32(State.frame.agreement_height)
            },
            text: MessageTextFromBytes(State.agreement_bytes[:count]),
            size: State.frame.font,
            strong: State.agreement_strong[:strong_count],
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
}

function SetHistoryScroll(history: NativeScroll.ScrollResult): void {
    State.frame.scroll = history.scroll_offset;
    State.frame.follow_end = history.scroll_offset === history.max_scroll;
}

function ChatHistory(
    history: NativeScroll.ScrollResult,
    x: s32,
    width: s32,
    bottom: s32,
    typing: boolean
): void {
    SetHistoryScroll(history);
    let anchor_drawn = false;
    let first = LumiFirstVisibleRowHost(history.scroll_offset);
    let top = s32(history.content.y) + LumiRowOffsetHost(first);
    for (let index = first; index < State.frame.chat_count; index += 1n) {
        if (top > bottom) {
            break;
        }
        let row = ReadLumiChatRowHost(index);
        let row_height = row.height;
        let bubble_width = width - Scale(row.user ? 60n : 80n);
        let left = x + Scale(48n);
        let row_press = RowPress(
            index,
            Bounds(x, top, width, row_height - Scale(10n)),
            history.content.y
        );
        if (RowSlot(index) === State.sweep_anchor) {
            anchor_drawn = true;
        }
        if (State.selecting) {
            let checked = IsSelected(index);
            let toggled = (
                <Checkbox
                    session={State.frame.session}
                    props={{
                        key: u64(420000n + RowSlot(index) + 1n),
                        bounds: Bounds(
                            x + Scale(8n),
                            top + (row_height - Scale(10n)) / 2n - Scale(12n),
                            Scale(24n),
                            Scale(24n)
                        ),
                        label: LumiViewLocaleHost("lumi_message"),
                        checked: checked
                    }}
                />
            );
            if (toggled.changed) {
                SelectionSet(index, toggled.checked);
            }
        } else if (!row.user && !row.developer) {
            LumiAvatar(index, x, top + row_height - Scale(54n));
        }
        <Box
            session={State.frame.session}
            props={{
                key: u64(300401n + index * 4n),
                bounds: Bounds(left, top, bubble_width, row_height - Scale(10n)),
                fill: row.user
                    ? { r: 156n, g: 188n, b: 143n, a: 48n }
                    : { r: 156n, g: 156n, b: 156n, a: 24n },
                radius: float32(Scale(16n))
            }}
        />;
        if (!row.user) {
            <Text
                session={State.frame.session}
                props={{
                    key: u64(300402n + index * 4n),
                    bounds: Bounds(
                        left + Scale(14n),
                        top + Scale(8n),
                        bubble_width - Scale(28n),
                        Scale(20n)
                    ),
                    text: row.developer ? LumiViewLocaleHost("lumi_developer") : "Lumi",
                    size: Scale(12n)
                }}
            />;
        }
        let from_telegram = row.user && row.kind === LUMI_CHAT_TEXT && row.payload === "telegram";
        if (from_telegram) {
            <Text
                session={State.frame.session}
                props={{
                    key: u64(300408n + index * 4n),
                    bounds: Bounds(
                        left + Scale(14n),
                        top + Scale(8n),
                        bubble_width - Scale(28n),
                        Scale(16n)
                    ),
                    text: LumiViewLocaleHost("lumi_from_telegram"),
                    size: Scale(11n)
                }}
            />;
        }
        let text_top = Scale(32n);
        if (row.user) {
            text_top = Scale(from_telegram ? 30n : 12n);
        }
        if (row.developer && row.quote.count > 0n) {
            FeedbackQuote(row, index, left, top + text_top, bubble_width);
            text_top += Scale(LUMI_QUOTE_HEIGHT);
        }
        let card_height = Scale(
            row.kind === LUMI_CHAT_PROGRESS ? 242n : row.kind === LUMI_CHAT_FEEDBACK ? 54n : 0n
        );
        let text_height = row_height - text_top - Scale(16n) - card_height;
        let props: NativeText.Props = {
            key: u64(300403n + index * 4n),
            bounds: Bounds(
                left + Scale(14n),
                top + text_top,
                bubble_width - Scale(28n),
                text_height
            ),
            text: row.text,
            size: State.frame.font,
            selectable: !State.selecting,
            wrap: NativeText.Wrap.TextWrapAuto
        };
        let drawn = RowText(index, row.text, !row.user);
        props.text = MessageTextFromBytes(drawn.text.bytes[:drawn.text.count]);
        props.strong = drawn.text.strong[:drawn.text.strong_count];
        let links = drawn.links;
        let link_ranges = NewLinkRanges();
        for (let link: s32 = 0n; link < links.count; link += s32(1)) {
            link_ranges[link] = { start: links.items[link].start, end: links.items[link].end };
        }
        props.links = link_ranges[:links.count];
        <Text session={State.frame.session} props={props} />;
        if (row_press.clicked && !State.selecting && links.count > 0n) {
            let tapped = NativeText.TextLinkAt(
                State.frame.session,
                props,
                row_press.x,
                row_press.y
            );
            if (tapped >= 0n) {
                OpenLinkHost(props.text[link_ranges[tapped].start:link_ranges[tapped].end]);
            }
        }
        let card_top = top + text_top + text_height + Scale(8n);
        if (row.kind === LUMI_CHAT_PROGRESS) {
            ProgressCard(row, index, left + Scale(14n), card_top, bubble_width - Scale(28n));
        } else if (row.kind === LUMI_CHAT_FEEDBACK) {
            let pending = LumiFeedbackChoiceHost(row.payload, 0n);
            if (
                (
                    <Button
                        session={State.frame.session}
                        props={{
                            id: 351000n + index * 2n,
                            bounds: Bounds(left + Scale(14n), card_top, Scale(88n), Scale(44n)),
                            label: LumiViewLocaleHost("lumi_feedback_yes"),
                            disabled: !pending
                        }}
                    />
                )
            ) {
                LumiFeedbackChoiceHost(row.payload, 1n);
            }
            if (
                (
                    <Button
                        session={State.frame.session}
                        props={{
                            id: 351001n + index * 2n,
                            bounds: Bounds(left + Scale(108n), card_top, Scale(88n), Scale(44n)),
                            label: LumiViewLocaleHost("lumi_feedback_no"),
                            disabled: !pending
                        }}
                    />
                )
            ) {
                LumiFeedbackChoiceHost(row.payload, 2n);
            }
        }
        top += row_height;
    }
    if (typing) {
        TypingDots(x, s32(history.content.y) + State.frame.history_height);
    }
    if (State.sweeping && !anchor_drawn) {
        let anchor = SlotRow(State.sweep_anchor);
        if (anchor >= 0n && anchor < State.frame.chat_count) {
            let anchor_top = s32(history.content.y) + LumiRowOffsetHost(anchor);
            RowPress(
                anchor,
                Bounds(x, anchor_top, width, ReadLumiChatRowHost(anchor).height - Scale(10n)),
                history.content.y
            );
        }
    }
}

export function LumiViewComposition(
    message: LumiMessage,
    commands: LumiCommands,
    revision: s64
): LumiMessage {
    State.frame = ReadLumiUiHost();
    let title_height = LumiTitleBar();
    if (State.frame.agreement !== 0n) {
        LumiAgreementView(title_height + Scale(8n));
        WriteLumiUiHost(State.frame);
        return message;
    }
    let column = NativeLayout.CenteredColumnFor(State.frame.width, Scale(720n), Scale(16n));
    let x = column.x;
    let width = column.width;
    let input_height = Scale(48n);
    let measured_height = State.frame.draft_height + Scale(24n);
    if (measured_height > input_height) {
        input_height = measured_height;
    }
    if (input_height > Scale(144n)) {
        input_height = Scale(144n);
    }
    let footer = State.frame.height - State.frame.bottom - Scale(16n) - input_height;
    let suggestions_top = footer - Scale(LumiTrim(State.frame.value).count > 0n ? 46n : 0n);
    let history_top = title_height + Scale(8n);
    let menu = MenuCommands(revision);
    let menu_matches = NewMenuMatches();
    let menu_count: s32 = 0n;
    let menu_target: s32 = -1n;
    if (MenuOpen(State.frame.value)) {
        for (let index: s32 = 0n; index < LUMI_MENU_COMMANDS; index += 1n) {
            let command = menu[index];
            if (
                (command.requirement !== 0n &&
                    FlagIntersection(State.frame.available_apps, command.requirement) === 0n) ||
                (command.choice_only &&
                    !State.frame.choosing_habit &&
                    !State.frame.choosing_diary) ||
                !LumiStarts(command.name, State.frame.value)
            ) {
                continue;
            }
            if (menu_target < 0n || LumiEqual(command.name, State.frame.value)) {
                menu_target = menu_count;
            }
            menu_matches[menu_count] = index;
            menu_count += 1n;
        }
    }
    let menu_row = Scale(44n);
    let menu_height = menu_count * menu_row;
    if (menu_height > (menu_row * 9n) / 2n) {
        menu_height = (menu_row * 9n) / 2n;
    }
    if (menu_count > 0n && footer - Scale(8n) - menu_height - history_top < Scale(68n)) {
        menu_height = footer - Scale(8n) - history_top - Scale(68n);
        if (menu_height < menu_row) {
            menu_height = menu_row;
        }
    }
    let menu_top = footer - Scale(8n) - menu_height;
    if (menu_count > 0n) {
        suggestions_top = menu_top;
    } else {
        State.menu_scroll = 0n;
    }
    let chat_height = suggestions_top - history_top - Scale(8n);
    if (chat_height < Scale(60n)) {
        chat_height = Scale(60n);
    }
    if (State.frame.follow_end) {
        State.frame.scroll = 1000000n;
    }
    let typing = State.frame.waiting && !State.frame.typing_pause;
    let typing_height = typing ? Scale(70n) : 0n;
    let history = (
        <Scroll
            session={State.frame.session}
            props={{
                key: 300100n,
                bounds: Bounds(x, history_top, width, chat_height),
                content_height: State.frame.history_height + typing_height,
                scroll_offset: State.frame.scroll,
                scale: State.frame.scale
            }}
            children={(scroll: NativeScroll.ScrollResult): void => {
                ChatHistory(scroll, x, width, history_top + chat_height, typing);
            }}
        />
    );
    if (!history.opened) {
        SetHistoryScroll(history);
    }
    let load_older =
        State.frame.has_older &&
        (history.max_scroll <= 0n || (!State.frame.follow_end && State.frame.scroll <= Scale(96n)));
    if (State.sweeping && State.sweep_seen) {
        let edge = float32(Scale(56n));
        let top_edge = float32(Scale(60n)) + edge;
        let bottom_edge = float32(history_top + chat_height) - edge;
        if (State.sweep_pointer_y < top_edge) {
            let step = s32((top_edge - State.sweep_pointer_y) / 3.0) + Scale(4n);
            if (step > Scale(40n)) {
                step = Scale(40n);
            }
            State.frame.scroll = State.frame.scroll - step;
            if (State.frame.scroll < 0n) {
                State.frame.scroll = 0n;
            }
            State.frame.follow_end = false;
        } else if (State.sweep_pointer_y > bottom_edge) {
            let step = s32((State.sweep_pointer_y - bottom_edge) / 3.0) + Scale(4n);
            if (step > Scale(40n)) {
                step = Scale(40n);
            }
            State.frame.scroll = State.frame.scroll + step;
        }
    }
    State.sweep_seen = false;
    if (State.selecting && State.selected_count <= 0n && !State.sweeping) {
        SelectionClear();
    }
    if (State.selecting) {
        SelectionBar(x, Scale(12n), width);
    }
    let typed = LumiTrim(State.frame.value);
    let candidates: [
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string
    ] = [
        commands.start_whm,
        commands.complete_habit,
        commands.start_meditation,
        commands.start_sun,
        commands.start_patterns,
        commands.add,
        commands.complete,
        commands.reopen,
        commands.lists,
        commands.habits,
        commands.practices,
        commands.diary,
        commands.settings,
        commands.appearance,
        commands.dark,
        commands.light,
        commands.system,
        commands.write_diary,
        commands.progress,
        commands.start_taichi
    ];
    let requirements: [
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32,
        s32
    ] = [
        LUMI_PRACTICES,
        LUMI_HABITS,
        LUMI_PRACTICES,
        LUMI_PRACTICES,
        LUMI_PRACTICES,
        LUMI_LISTS,
        LUMI_LISTS,
        LUMI_LISTS,
        LUMI_LISTS,
        LUMI_HABITS,
        LUMI_PRACTICES,
        LUMI_DIARY,
        0n,
        0n,
        0n,
        0n,
        0n,
        LUMI_DIARY,
        LUMI_PRACTICES,
        LUMI_PRACTICES
    ];
    let suggestion_count: s32 = 0n;
    let selected: boolean = false;
    let limit: s32 = menu_count > 0n ? 0n : 2n;
    let chip_width = (width - Scale(8n)) / 2n;
    let action = DraftIntent(typed, commands, revision);
    if (action.kind === 0n && State.frame.choosing_habit) {
        action = { kind: LUMI_COMPLETE_HABIT, title: typed };
    }
    if (
        typed.count > 0n &&
        !State.frame.choosing_diary &&
        LumiActionAvailable(action, State.frame.available_apps) &&
        (action.kind === LUMI_COMPLETE_TODO ||
            action.kind === LUMI_REOPEN_TODO ||
            action.kind === LUMI_COMPLETE_HABIT)
    ) {
        let count =
            action.kind === LUMI_COMPLETE_HABIT ? State.frame.habit_count : State.frame.task_count;
        for (let index: s32 = 0n; index < count; index += 1n) {
            if (suggestion_count >= limit) {
                break;
            }
            let task =
                action.kind === LUMI_COMPLETE_HABIT
                    ? ReadLumiSuggestionHabitHost(index)
                    : ReadLumiSuggestionTaskHost(index);
            let eligible =
                action.kind === LUMI_COMPLETE_HABIT ||
                (action.kind === LUMI_COMPLETE_TODO && !task.done) ||
                (action.kind === LUMI_REOPEN_TODO && task.done);
            if (!eligible || !LumiStarts(task.title, action.title) || suggestion_count >= limit) {
                continue;
            }
            let command = commands.reopen;
            if (action.kind === LUMI_COMPLETE_HABIT) {
                command = commands.complete_habit;
            } else if (action.kind === LUMI_COMPLETE_TODO) {
                command = commands.complete;
            }
            let completion = CompletionSuggestion(command, task.title);
            selected =
                Suggestion(
                    30020n + suggestion_count,
                    completion,
                    Bounds(
                        x + suggestion_count * (chip_width + Scale(8n)),
                        suggestions_top,
                        chip_width,
                        Scale(36n)
                    ),
                    task.title
                ) || selected;
            suggestion_count += 1n;
        }
    }
    if (revision !== State.candidate_revision) {
        State.candidate_revision = revision;
        State.candidate_ready = 0n;
    }
    if (typed.count > 0n) {
        let prepared: s32 = 0n;
        while (
            State.candidate_ready < s32(candidates.count) &&
            prepared < LUMI_CANDIDATES_PER_FRAME
        ) {
            State.candidate_actions[State.candidate_ready] = LumiIntent(
                candidates[State.candidate_ready],
                commands
            );
            State.candidate_ready = State.candidate_ready + 1n;
            prepared += 1n;
        }
    }
    for (let index: s32 = 0n; index < s32(candidates.count); index += 1n) {
        if (
            typed.count === 0n ||
            State.frame.choosing_diary ||
            action.kind === LUMI_COMPLETE_HABIT ||
            suggestion_count >= limit ||
            index >= State.candidate_ready
        ) {
            break;
        }
        let candidate_action = State.candidate_actions[index];
        let practice_match =
            action.kind === LUMI_START_PRACTICE &&
            candidate_action.kind === LUMI_START_PRACTICE &&
            action.practice === candidate_action.practice;
        let hidden_practice =
            candidate_action.kind === LUMI_START_PRACTICE &&
            FlagIntersection(
                State.frame.practices_hidden,
                FlagShiftLeft(s32(1n), candidate_action.practice)
            ) !== 0n;
        if (
            hidden_practice ||
            (requirements[index] !== 0n &&
                FlagIntersection(State.frame.available_apps, requirements[index]) === 0n) ||
            suggestion_count >= limit ||
            (typed.count > 0n && !LumiSuggests(candidates[index], typed) && !practice_match)
        ) {
            continue;
        }
        let text = candidates[index];
        if (index === 1n || (index >= 5n && index <= 7n)) {
            text = CommandPrefix(text);
        }
        selected =
            Suggestion(
                30030n + index,
                text,
                Bounds(
                    x + suggestion_count * (chip_width + Scale(8n)),
                    suggestions_top,
                    chip_width,
                    Scale(36n)
                )
            ) || selected;
        suggestion_count += 1n;
    }
    let chosen: s32 = -1n;
    if (menu_count > 0n) {
        <Box
            session={State.frame.session}
            props={{
                key: u64(360000n),
                bounds: Bounds(x, menu_top, width, menu_height),
                fill: { r: 156n, g: 156n, b: 156n, a: 24n },
                radius: float32(Scale(12n))
            }}
        />;
        let menu_list = NativeScroll.Draw(State.frame.session, {
            key: u64(360001n),
            bounds: Bounds(x, menu_top, width, menu_height),
            content_height: menu_count * menu_row,
            scroll_offset: State.menu_scroll,
            scale: State.frame.scale
        });
        State.menu_scroll = menu_list.scroll_offset;
        if (menu_list.opened) {
            let name_width = Scale(104n);
            for (let row: s32 = 0n; row < menu_count; row += s32(1)) {
                let top = s32(menu_list.content.y) + row * menu_row;
                if (top + menu_row < menu_top || top > menu_top + menu_height) {
                    continue;
                }
                let index = menu_matches[row];
                let command = menu[index];
                let key = 360100n + index * 4n;
                if (row === menu_target) {
                    <Box
                        session={State.frame.session}
                        props={{
                            key: u64(key),
                            bounds: Bounds(x, top, width, menu_row),
                            fill: { r: 156n, g: 188n, b: 143n, a: 48n },
                            radius: float32(Scale(12n))
                        }}
                    />;
                }
                if (
                    (
                        <Button
                            session={State.frame.session}
                            props={{
                                id: 360200n + index,
                                bounds: Bounds(x, top, width, menu_row),
                                invisible: true,
                                label: command.description
                            }}
                        />
                    )
                ) {
                    chosen = index;
                }
                let strong: [NativeText.Range] = [{ start: 0n, end: s32(command.name.count) }];
                <Text
                    session={State.frame.session}
                    props={{
                        key: u64(key + 1n),
                        bounds: Bounds(x + Scale(16n), top, name_width, menu_row),
                        text: command.name,
                        size: State.frame.font,
                        strong: strong[:],
                        wrap: NativeText.Wrap.TextWrapNone,
                        vertical_align: TextAlign.TextAlignCenter
                    }}
                />;
                <Text
                    session={State.frame.session}
                    props={{
                        key: u64(key + 2n),
                        bounds: Bounds(
                            x + Scale(16n) + name_width,
                            top,
                            width - Scale(32n) - name_width,
                            menu_row
                        ),
                        text: command.description,
                        size: Scale(14n),
                        wrap: NativeText.Wrap.TextWrapAuto,
                        vertical_align: TextAlign.TextAlignCenter
                    }}
                />;
            }
            End(State.frame.session);
        }
    }
    let show_commands = LumiTrim(State.frame.value).count === 0n;
    if (
        show_commands && (
            <Button
                session={State.frame.session}
                props={{
                    id: 30012n,
                    bounds: Bounds(x + width - Scale(48n), footer, Scale(48n), Scale(48n)),
                    label: LumiViewLocaleHost("lumi_commands"),
                    icon_shape: LUMI_COMMANDS_ICON,
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }}
            />
        )
    ) {
        FillDraft("/");
        selected = true;
    }
    if (selected || chosen >= 0n) {
        State.focus_request = 2n;
    }
    let field_input = State.frame.input;
    if (State.focus_request > 0n) {
        field_input.focus = true;
        State.focus_request = State.focus_request - 1n;
    }
    let field = (
        <TextArea
            session={State.frame.session}
            props={{
                key: u64(300200n),
                focus_id: 30010n,
                bounds: Bounds(x, footer, width - Scale(56n), input_height),
                value: State.frame.value,
                placeholder: LumiViewLocaleHost("lumi_placeholder"),
                label: "Lumi",
                cursor: State.frame.cursor,
                anchor: State.frame.anchor,
                scroll_y: State.frame.input_scroll,
                selecting: State.frame.selecting,
                preferred_x: State.frame.preferred_x,
                preferred_x_valid: State.frame.preferred_x_valid,
                wrap: true,
                focused: State.frame.focused,
                input: field_input,
                max_bytes: LUMI_INPUT_MAX - 1n,
                max_codepoints: LUMI_INPUT_MAX - 1n
            }}
        />
    );
    if (!selected) {
        if (
            field.edit.changed &&
            field.edit.start >= 0n &&
            field.edit.end >= field.edit.start &&
            field.edit.end <= State.frame.value.count
        ) {
            let replacement = ApplyDraftEdit(
                field.edit.start,
                field.edit.end,
                field.edit.replacement
            );
            if (replacement.count < LUMI_INPUT_MAX) {
                State.frame.value = replacement;
            }
        }
        State.frame.cursor = field.cursor;
        State.frame.anchor = field.anchor;
        State.frame.input_scroll = field.scroll_y;
        State.frame.selecting = field.selecting;
        State.frame.preferred_x = field.preferred_x;
        State.frame.preferred_x_valid = field.preferred_x_valid;
        State.frame.focused = field.focused;
    }
    let copy_row = RowMenu();
    State.frame.clipboard_write = field.clipboard_write;
    State.frame.clipboard_text = field.clipboard_text;
    if (State.copy_pending) {
        State.frame.clipboard_write = true;
        State.frame.clipboard_text = State.pending_copy;
        State.copy_pending = false;
    }
    if (copy_row >= 0n) {
        CopyChatRow(copy_row);
    }
    let send = !show_commands && (
        <Button
            session={State.frame.session}
            props={{
                id: 30011n,
                bounds: Bounds(x + width - Scale(48n), footer, Scale(48n), Scale(48n)),
                label: LumiViewLocaleHost("lumi_send"),
                icon_shape: LUMI_SEND_ICON,
                icon_only: true,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }}
        />
    );
    if (chosen < 0n && field.committed && !send && menu_target >= 0n && !selected) {
        chosen = menu_matches[menu_target];
    }
    let submit = "";
    if (chosen >= 0n) {
        let text = CommandText(menu[chosen]);
        if (menu[chosen].needs_text) {
            FillDraft(text);
        } else {
            submit = text;
        }
    } else if ((send || field.committed) && LumiTrim(State.frame.value).count > 0n && !selected) {
        submit = State.frame.value;
    }
    if (submit.count > 0n) {
        message.action = LUMI_SEND;
        message.input = CopyLumiText(submit);
        State.frame.value = "";
        State.frame.cursor = 0n;
        State.frame.anchor = 0n;
        State.frame.input_scroll = 0n;
        State.frame.selecting = false;
        State.frame.preferred_x_valid = false;
        State.frame.focused = true;
        State.focus_request = 2n;
        State.frame.scroll = 1000000n;
        State.frame.follow_end = true;
    }
    WriteLumiUiHost(State.frame);
    if (message.action !== LUMI_SEND && load_older) {
        LumiLoadOlderHost();
    }
    return message;
}
