import * as Model from "habit_list_view";
import {
    Alpha,
    Ask,
    Bounds,
    Coins,
    Filled,
    Locale,
    NewHeadingStrong,
    Scale,
    TitleFont,
    Width
} from "habit_list_view";
import { HABITS_LIST_ADD, HABITS_LIST_ALL_STATISTICS, HABITS_LIST_SHOP } from "habits_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import * as NativeText from "kryon/text";
import { Button } from "kryon/tsx/button";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Text } from "kryon/tsx/text";
import * as NativeStatisticsIcon from "mingcute/mingcute_regular_chart_line";
import * as NativeShopIcon from "mingcute/mingcute_regular_shop";
import { Fill, CoinAmount } from "habit_list_visuals";

export function DrawHabitsSummary(x: s32, y: s32, width: s32): s32 {
    const list_state = Model.CurrentList();
    let heading_height = Scale(34n);
    let button_height = Scale(42n);
    let gap = Scale(12n);
    let add_label = Locale("habit_new_button");
    let add_width = Width(add_label, list_state.font) + Scale(40n);
    if (add_width < Scale(120n)) {
        add_width = Scale(120n);
    }
    if (add_width > (width * 2n) / 3n) {
        add_width = (width * 2n) / 3n;
    }
    let heading = Locale("tab_habits");
    let heading_strong = NewHeadingStrong();
    heading_strong[0n] = { start: 0n, end: s32(heading.count) };
    let heading_width = width - add_width - gap;
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(x, y, heading_width, heading_height),
            text: heading,
            size: TitleFont(heading, heading_width),
            strong: heading_strong[:],
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4100n,
                    bounds: Bounds(x + width - add_width, y, add_width, button_height),
                    label: add_label,
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                    pill: true,
                    disabled: list_state.modal_active || Model.row_count >= list_state.habit_limit
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_ADD, -1n, 0n);
        return 0n;
    }
    let summary_y = y + heading_height + gap;
    let coins = Coins(list_state.halves);
    let coins_width = list_state.font + Scale(6n) + Width(coins, list_state.font);
    let minimum_action_size: s32 = 44n;
    let action_size = Scale(minimum_action_size);
    let action_gap = Scale(8n);
    let coin_padding = Scale(6n);
    let coin_gap = Scale(10n);
    let wide_actions_width =
        coins_width + coin_padding + coin_gap + action_gap + 2n * minimum_action_size;
    if (action_size < minimum_action_size && width >= wide_actions_width) {
        action_size = minimum_action_size;
    }
    let icon_size = Scale(20n);
    let icon_inset = (action_size - icon_size) / 2n;
    let statistics_x = x + width - action_size;
    let shop_right = statistics_x - action_gap;
    let shop_icon_x = shop_right - action_size + icon_inset;
    let shop_x = shop_icon_x - coins_width - coin_gap - coin_padding;
    if (shop_x < x) {
        shop_x = x;
        coin_padding = 0n;
        coins_width = shop_icon_x - x - Scale(5n);
    }
    let action_y = summary_y + (Scale(34n) - action_size) / 2n;
    let summary_width = shop_x - x - gap;
    let due: s32 = 0n;
    let done: s32 = 0n;
    const today_days = Model.TodayDays();
    for (let index = s32(0n); index < Model.row_count; index += s32(1)) {
        if (today_days[index].planned) {
            due += 1n;
            if (today_days[index].complete) {
                done += 1n;
            }
        }
    }
    let summary = Filled(Locale("habits_done_count_label"), done, due);
    if (summary_width < Width(summary, list_state.font)) {
        action_y = summary_y;
        summary_y += action_size + Scale(6n);
        summary_width = width;
    }
    let shop_bounds = Bounds(shop_x, action_y, shop_right - shop_x, action_size);
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4120n,
                    bounds: shop_bounds,
                    label: Locale("habits_shop_button"),
                    invisible: true,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_SHOP, -1n, 0n);
        return 0n;
    }
    if (
        (
            <Button
                session={list_state.session}
                props={{
                    id: 4121n,
                    bounds: Bounds(statistics_x, action_y, action_size, action_size),
                    label: Locale("habit_statistics_title"),
                    icon_only: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost,
                    disabled: list_state.modal_active
                }}
            />
        )
    ) {
        Ask(HABITS_LIST_ALL_STATISTICS, -1n, 0n);
        return 0n;
    }
    CoinAmount(
        coins,
        Bounds(shop_x + coin_padding, action_y, coins_width, action_size),
        list_state.font
    );
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: Bounds(shop_icon_x, action_y + icon_inset, icon_size, icon_size),
            shape: NativeShopIcon.Shape,
            color: list_state.text_color
        }}
    />;
    <SvgIcon
        session={list_state.session}
        props={{
            bounds: Bounds(statistics_x + icon_inset, action_y + icon_inset, icon_size, icon_size),
            shape: NativeStatisticsIcon.Shape,
            color: list_state.text_color
        }}
    />;
    list_state.anchor_coins = shop_bounds;
    let progress_y = summary_y + Scale(28n);
    let progress_height = Scale(6n);
    <Text
        session={list_state.session}
        props={{
            bounds: Bounds(x, summary_y, summary_width, Scale(24n)),
            text: summary,
            size: list_state.font,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    list_state.anchor_progress = Bounds(x, summary_y, summary_width, Scale(24n));
    let progress_width = summary_width;
    if (progress_width > Scale(420n)) {
        progress_width = Scale(420n);
    }
    Fill(
        Bounds(x, progress_y, progress_width, progress_height),
        float32(Scale(3n)),
        Alpha(list_state.text_color, 0.12)
    );
    if (due > 0n && done > 0n) {
        let progress_fill = (progress_width * done) / due;
        if (progress_fill > progress_width) {
            progress_fill = progress_width;
        }
        Fill(
            Bounds(x, progress_y, progress_fill, progress_height),
            float32(Scale(3n)),
            list_state.accent_color
        );
    }
    return summary_y;
}
