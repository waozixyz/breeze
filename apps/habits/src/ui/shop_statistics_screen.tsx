import * as Shared from "habit_shared";
// A separate, read-only view of the persisted shop purchase history.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import { Box } from "kryon/tsx/box";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import * as Shop from "shop_view";
import {
    Filled,
    ParagraphHeight,
    SHOP_COLUMN_MAX,
    SHOP_GAP,
    SHOP_SCROLLBAR_ROOM,
    Scale
} from "shop_view";
import { HABITS_SHOP_NONE, HABITS_SHOP_STATS_BACK, HabitsMessage } from "habits_types";
import {
    PurchaseDate,
    ReadHabitRewardHost,
    ReadHabitsShopHost,
    RewardStatisticsText,
    StatisticsCardHeight,
    StatisticsColor,
    StatisticsColumns,
    StatisticsHeight,
    StatisticsLabel,
    StatisticsNumberHeight,
    StatisticsRewardHeight,
    StatisticsValue,
    WriteHabitsShopHost
} from "shop_stats_view";
import { Card, PageHeader, SectionTitle } from "shop_screen";

function Statistics(x: s32, y: s32, width: s32): void {
    const shop_state = Shop.CurrentShop();
    y += SectionTitle(Shop.Locale("habit_shop_stats_title"), x, y, width) + Scale(10n);
    if (shop_state.statistics.purchase_count === 0n) {
        let text = Shop.Locale("habit_shop_stats_empty");
        <Text
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(
                    x,
                    y,
                    width,
                    ParagraphHeight(text, width, shop_state.small_font)
                ),
                text: text,
                size: shop_state.small_font,
                class_name: shop_state.muted_class,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        return;
    }
    let columns = StatisticsColumns(width);
    let card_w = (width - Scale(8n) * (columns - 1n)) / columns;
    let card_h = StatisticsCardHeight(width);
    let number_h = StatisticsNumberHeight(width);
    for (let index = s32(0n); index <= 3n; index += s32(1)) {
        let card_x = x + (index % columns) * (card_w + Scale(8n));
        let card_y = y + (index / columns) * (card_h + Scale(8n));
        Card(Shared.Bounds(card_x, card_y, card_w, card_h), "");
        <Box
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(card_x, card_y + Scale(12n), Scale(4n), card_h - Scale(24n)),
                fill: StatisticsColor(index)
            }}
        />;
        let value = StatisticsValue(index);
        let strong = Shared.NewStrong();
        nativeSet(strong, 0n, { start: 0n, end: s32(value.count) });
        <Text
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(
                    card_x + Scale(16n),
                    card_y + Scale(12n),
                    card_w - Scale(32n),
                    number_h
                ),
                text: value,
                size: shop_state.font + Scale(6n),
                strong: nativeSlice(strong),
                wrap: NativeText.Wrap.TextWrapAnywhere
            }}
        />;
        <Text
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(
                    card_x + Scale(16n),
                    card_y + number_h + Scale(18n),
                    card_w - Scale(32n),
                    card_h - number_h - Scale(30n)
                ),
                text: StatisticsLabel(index),
                size: shop_state.small_font,
                class_name: shop_state.muted_class,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
    }
    let last = Filled(
        Shop.Locale("habit_shop_stats_last"),
        PurchaseDate(shop_state.statistics.last_date)
    );
    let last_y = y + (4n / columns) * (card_h + Scale(8n));
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(
                x,
                last_y,
                width,
                ParagraphHeight(last, width, shop_state.small_font)
            ),
            text: last,
            size: shop_state.small_font,
            class_name: shop_state.muted_class,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
}

function StatisticsReward(index: s32, x: s32, y: s32, width: s32): s32 {
    const shop_state = Shop.CurrentShop();
    let reward = ReadHabitRewardHost(index);
    let height = StatisticsRewardHeight(index, width);
    Card(Shared.Bounds(x, y, width, height), "");
    let pad = Scale(16n);
    let inner = width - pad * 2n;
    let name_h = ParagraphHeight(reward.name, inner, shop_state.font);
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(x + pad, y + pad, inner, name_h),
            text: reward.name,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    let text = RewardStatisticsText(reward);
    let text_h = ParagraphHeight(text, inner, shop_state.small_font);
    let line_y = y + pad + name_h + Scale(8n);
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(x + pad, line_y, inner, text_h),
            text: text,
            size: shop_state.small_font,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    if (reward.statistics.purchase_count > 0n) {
        let last = Filled(
            Shop.Locale("habit_shop_stats_last"),
            PurchaseDate(reward.statistics.last_date)
        );
        <Text
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(
                    x + pad,
                    line_y + text_h + Scale(4n),
                    inner,
                    ParagraphHeight(last, inner, shop_state.small_font)
                ),
                text: last,
                size: shop_state.small_font,
                class_name: shop_state.muted_class,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
    }
    return height;
}

function ShopStatisticsPage(): void {
    const shop_state = Shop.CurrentShop();
    let bounds = shop_state.bounds;
    let width = s32(bounds.width);
    let x = s32(bounds.x);
    if (width > Scale(SHOP_COLUMN_MAX)) {
        x += (width - Scale(SHOP_COLUMN_MAX)) / 2n;
        width = Scale(SHOP_COLUMN_MAX);
    }
    let top = PageHeader(x, s32(bounds.y), width, Shop.Locale("habit_shop_stats_title"), "");
    if (top < 0n) {
        shop_state.action = HABITS_SHOP_STATS_BACK;
        return;
    }
    let content_width = width - Scale(SHOP_SCROLLBAR_ROOM);
    let gap = Scale(SHOP_GAP);
    let content_h = StatisticsHeight(content_width) + gap;
    for (let index = s32(0n); index < shop_state.reward_count; index += s32(1)) {
        content_h += StatisticsRewardHeight(index, content_width) + gap;
    }
    const scrolled = Scroll({
        session: shop_state.session,
        props: {
            key: NativeLayout.KeyHash("inbe/habits/shop/statistics"),
            bounds: Shared.Bounds(x, top, width, s32(bounds.y + bounds.height) - top),
            content_height: content_h,
            scroll_offset: shop_state.scroll
        },
        children: (scrolled: NativeScroll.ScrollResult): void => {
            const shop_state = Shop.CurrentShop();
            shop_state.scroll = scrolled.scroll_offset;
            let y = s32(scrolled.content.y);
            Statistics(x, y, content_width);
            y += StatisticsHeight(content_width) + gap;
            for (let index = s32(0n); index < shop_state.reward_count; index += s32(1)) {
                y += StatisticsReward(index, x, y, content_width) + gap;
            }
        }
    });
    if (!scrolled.opened) {
        shop_state.scroll = scrolled.scroll_offset;
    }
}

export function HabitsShopStatisticsView(message: HabitsMessage): HabitsMessage {
    const shop_state = Shop.CurrentShop();
    Shop.SetShop(ReadHabitsShopHost());
    shop_state.action = HABITS_SHOP_NONE;
    shop_state.clipboard_write = false;
    ShopStatisticsPage();
    WriteHabitsShopHost(nativeDeref(shop_state));
    message.succeeded = true;
    return message;
}
