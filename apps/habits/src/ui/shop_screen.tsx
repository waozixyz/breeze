import * as Cards from "habit_cards";
import * as Shared from "habit_shared";
// The habit shop: the coins the habits earned and the rewards the person
// sets, each with its symbol and its price in coins, to spend them on. A
// reward is added or changed in the form under the list; a tap on a
// reward's name opens it there, and Buy asks before it spends the coins.
// The host keeps the coins, the rewards and the form's state; the page
// draws them and asks the host to save, delete or buy a reward.
import { HabitDailyRewardCoins, HabitRewardIconClamp, HabitRewardPriceClamp } from "habit_coins";
import { HABIT_REWARD_NAME_SIZE, HABIT_REWARD_PRICE_MAX } from "habit_types";
import * as Habits from "habits_types";
import * as NativeButton from "kryon/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import { SemanticKind } from "kryon/semantic";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { SvgIcon } from "kryon/tsx/svg_icon";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { ControlledTextField } from "kryon/tsx/text_field";
import * as NativeCoinIcon from "mingcute/mingcute_filled_copper_coin";
import {
    REWARD_ICON_COUNT,
    RewardIconAsset,
    RewardIconLabelKey,
    RewardIconShape
} from "reward_icons";
import * as Model from "shop_view";

export function RewardSymbol(icon: s32, bounds: Rectangle): void {
    const shop_state = Model.CurrentShop();
    if (RewardIconAsset(icon).count > 0n) {
        let picture = Model.RewardImage(icon);
        picture.bounds = bounds;
        <Image session={shop_state.session} props={picture} />;
    } else {
        <SvgIcon
            session={shop_state.session}
            props={{ bounds: bounds, shape: RewardIconShape(icon), color: shop_state.text_color }}
        />;
    }
}

function Coin(bounds: Rectangle): void {
    const shop_state = Model.CurrentShop();
    <SvgIcon
        session={shop_state.session}
        props={{ bounds: bounds, shape: NativeCoinIcon.Shape, color: Model.CoinColor() }}
    />;
}

export function Card(bounds: Rectangle, key: string): void {
    const shop_state = Model.CurrentShop();
    <Box
        session={shop_state.session}
        props={{
            key: key.count > 0n ? NativeLayout.KeyHash(key) : u64(0n),
            bounds: bounds,
            fill: shop_state.card_fill,
            border: shop_state.card_border,
            radius: float32(shop_state.card_radius)
        }}
    />;
}

// A coin and its amount, centred on the bounds' height from their left.
function CoinAmount(amount: string, bounds: Rectangle, font: s32): void {
    Cards.CoinAmount(Model.SurfaceStyle(), amount, bounds, font, NativeText.Wrap.TextWrapNone);
}

function ShopActionProps(
    id: s32,
    label: string,
    bounds: Rectangle,
    tone: ButtonTone,
    emphasis: ButtonEmphasis,
    disabled: boolean
): NativeButton.Props {
    return {
        id: id,
        bounds: bounds,
        label: label,
        tone: tone,
        emphasis: emphasis,
        fit_content: true,
        disabled: disabled || Model.CurrentShop().modal_active
    };
}

function NameField(bounds: Rectangle): boolean {
    const shop_state = Model.CurrentShop();
    let binding = Shared.BindText(
        nativeRef(shop_state.name_cursor),
        nativeRef(shop_state.name_anchor),
        nativeRef(shop_state.name_scroll_x)
    );
    let props = Shared.InputProps(
        binding,
        {
            key: NativeLayout.KeyHash("inbe/habits/shop/name"),
            bounds: bounds,
            value: shop_state.name,
            placeholder: Model.Locale("habit_shop_name_placeholder"),
            focused: shop_state.name_focused,
            focus_id: 8411n,
            max_bytes: HABIT_REWARD_NAME_SIZE - 1n,
            disabled: shop_state.modal_active
        },
        shop_state.input
    );
    let result = ControlledTextField({ session: shop_state.session, props: props });
    Shared.AcceptText(binding, result);
    shop_state.name = Shared.EditedText(shop_state.name, result.edit, props.max_bytes);
    Model.Clipboard(result);
    shop_state.name_focused = result.focused;
    if (result.focused) {
        shop_state.price_focused = false;
        shop_state.borrow_focused = false;
    }
    return result.committed;
}

// The price as typed; an empty or zero entry keeps the last price until
// the field is left.
function PriceField(bounds: Rectangle): boolean {
    const shop_state = Model.CurrentShop();
    if (!shop_state.price_focused) {
        Model.PriceText();
    }
    let binding = Shared.BindText(
        nativeRef(shop_state.price_cursor),
        nativeRef(shop_state.price_anchor),
        nativeRef(shop_state.price_scroll_x)
    );
    let props = Shared.InputProps(
        binding,
        {
            key: NativeLayout.KeyHash("inbe/habits/shop/price"),
            bounds: bounds,
            value: shop_state.price_text,
            focused: shop_state.price_focused,
            focus_id: 8412n,
            numeric: true,
            max_bytes: 4n,
            disabled: shop_state.modal_active
        },
        shop_state.input
    );
    let result = ControlledTextField({ session: shop_state.session, props: props });
    Shared.AcceptText(binding, result);
    shop_state.price_text = Shared.EditedText(shop_state.price_text, result.edit, props.max_bytes);
    Model.Clipboard(result);
    if (result.edit.changed) {
        let value: s32 = s32(0n);
        let index: s64 = 0n;
        while (index < shop_state.price_text.count) {
            let digit = s32(nativeAt(shop_state.price_text, index)) - 48n;
            if (digit >= 0n && digit <= 9n) {
                value = value * 10n + digit;
            }
            index += 1n;
        }
        if (value > 0n) {
            shop_state.price = HabitRewardPriceClamp(value);
        }
    }
    shop_state.price_focused = result.focused;
    if (result.focused) {
        shop_state.name_focused = false;
        shop_state.borrow_focused = false;
    }
    return result.committed;
}

// The limit as typed; an empty field means no borrowing.
function BorrowField(bounds: Rectangle): void {
    const shop_state = Model.CurrentShop();
    if (!shop_state.borrow_focused) {
        Model.BorrowText();
    }
    let binding = Shared.BindText(
        nativeRef(shop_state.borrow_cursor),
        nativeRef(shop_state.borrow_anchor),
        nativeRef(shop_state.borrow_scroll_x)
    );
    let props = Shared.InputProps(
        binding,
        {
            key: NativeLayout.KeyHash("inbe/habits/shop/borrow"),
            bounds: bounds,
            value: shop_state.borrow_text,
            focused: shop_state.borrow_focused,
            focus_id: 8413n,
            numeric: true,
            max_bytes: 4n,
            disabled: shop_state.modal_active
        },
        shop_state.input
    );
    let result = ControlledTextField({ session: shop_state.session, props: props });
    Shared.AcceptText(binding, result);
    shop_state.borrow_text = Shared.EditedText(
        shop_state.borrow_text,
        result.edit,
        props.max_bytes
    );
    Model.Clipboard(result);
    if (result.edit.changed) {
        let value: s32 = s32(0n);
        let index: s64 = 0n;
        while (index < shop_state.borrow_text.count) {
            let digit = s32(nativeAt(shop_state.borrow_text, index)) - 48n;
            if (digit >= 0n && digit <= 9n) {
                value = value * 10n + digit;
            }
            index += 1n;
        }
        if (value > Model.SHOP_BORROW_LIMIT_MAX) {
            value = Model.SHOP_BORROW_LIMIT_MAX;
        }
        shop_state.borrow_limit = value;
    }
    shop_state.borrow_focused = result.focused;
    if (result.focused) {
        shop_state.name_focused = false;
        shop_state.price_focused = false;
    }
}

// Back, then the page's title, strong, with its subtitle muted below it.
// Returns the y below it, or -1 when Back was pressed.
export function PageHeader(x: s32, y: s32, width: s32, title_text: string, subtitle: string): s32 {
    return Cards.PageHeader(
        Model.SurfaceStyle(),
        Shared.Bounds(x, y, width, 0n),
        8400n,
        title_text,
        subtitle,
        false,
        Model.Locale("back_button")
    );
}

// The coins to spend, large beside a gold coin, and how habits earn them.
function BalanceCard(x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let height = Model.Scale(Model.SHOP_BALANCE_HEIGHT);
    Card(Shared.Bounds(x, y, width, height), "inbe/habits/shop/balance");
    let coin = Model.Scale(48n);
    let pad = Model.Scale(Model.SHOP_CARD_PADDING);
    Coin(Shared.Bounds(x + pad, y + (height - coin) / 2n, coin, coin));
    let text_x = x + pad + coin + Model.Scale(14n);
    let text_w = width - (text_x - x) - pad;
    let amount = Shared.Coins(shop_state.halves);
    let strong = Shared.NewStrong();
    nativeSet(strong, 0n, { start: 0n, end: s32(amount.count) });
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(text_x, y + Model.Scale(14n), text_w, Model.Scale(40n)),
            text: amount,
            size: shop_state.font + Model.Scale(16n),
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(text_x, y + Model.Scale(54n), text_w, Model.Scale(24n)),
            text: Model.Locale("habit_shop_balance_label"),
            size: shop_state.small_font,
            class_name: shop_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    return height;
}

function DailyCard(x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let height = Model.DailyCardHeight();
    if (shop_state.daily_claimed) {
        <Text
            session={shop_state.session}
            props={{
                bounds: Shared.Bounds(x, y, width, height),
                text: Model.Locale("habit_shop_daily_claimed"),
                class_name: shop_state.muted_class,
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapEllipsis
            }}
        />;
        return height;
    }
    let label = Model.Filled(
        Model.Locale("habit_shop_daily_claim"),
        Shared.Number(s64(HabitDailyRewardCoins(shop_state.daily_day)))
    );
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8450n,
                label,
                Shared.Bounds(x, y, width, height),
                ButtonTone.ButtonToneAccent,
                ButtonEmphasis.ButtonEmphasisFilled,
                false
            )
        })
    ) {
        shop_state.name_focused = false;
        shop_state.price_focused = false;
        shop_state.borrow_focused = false;
        shop_state.action = Habits.HABITS_SHOP_DAILY_CLAIM;
    }
    return height;
}

// How far the balance may go below zero, as whole coins the shop lends.
function BorrowRow(x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let pad = Model.Scale(10n);
    let height = Model.BorrowRowHeight();
    Card(Shared.Bounds(x, y, width, height), "inbe/habits/shop/borrow-card");
    let field_h = Model.Scale(Model.SHOP_FIELD_HEIGHT);
    let field_y = y + pad;
    let inner_x = x + pad;
    let coin = Model.Scale(22n);
    let step = Model.Scale(44n);
    let controls_w =
        step + Model.Scale(6n) + Model.Scale(64n) + Model.Scale(6n) + step + Model.Scale(8n) + coin;
    let label_w = width - pad * 2n - controls_w;
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(inner_x, field_y, label_w, field_h),
            text: Model.Locale("habit_shop_borrow_label"),
            class_name: shop_state.muted_class,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let control_x = inner_x + label_w;
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8440n,
                "-",
                Shared.Bounds(control_x, field_y, step, field_h),
                ButtonTone.ButtonToneNeutral,
                ButtonEmphasis.ButtonEmphasisSoft,
                shop_state.borrow_limit <= 0n
            )
        })
    ) {
        shop_state.borrow_limit = shop_state.borrow_limit - 1n;
        Model.BorrowText();
    }
    BorrowField(
        Shared.Bounds(control_x + step + Model.Scale(6n), field_y, Model.Scale(64n), field_h)
    );
    let plus_x = control_x + step + Model.Scale(70n);
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8441n,
                "+",
                Shared.Bounds(plus_x, field_y, step, field_h),
                ButtonTone.ButtonToneNeutral,
                ButtonEmphasis.ButtonEmphasisSoft,
                shop_state.borrow_limit >= Model.SHOP_BORROW_LIMIT_MAX
            )
        })
    ) {
        shop_state.borrow_limit = shop_state.borrow_limit + 1n;
        Model.BorrowText();
    }
    Coin(
        Shared.Bounds(plus_x + step + Model.Scale(8n), field_y + (field_h - coin) / 2n, coin, coin)
    );
    return height;
}

// Narrow rows put the day below the name, leaving the amount on the right.
function ActivityRow(index: s32, x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let line = Model.ReadHabitActivityHost(index);
    let height = Model.ActivityRowHeight(index, width);
    let stacked = Model.ActivityStacked(line, width);
    let first_height = stacked ? height - Model.Scale(32n) : height;
    let symbol = Model.Scale(20n);
    let icon_height = stacked ? Model.Scale(24n) : height;
    let symbol_bounds = Shared.Bounds(x, y + (icon_height - symbol) / 2n, symbol, symbol);
    if (line.icon > 0n) {
        RewardSymbol(HabitRewardIconClamp(line.icon), symbol_bounds);
    } else {
        <SvgIcon
            session={shop_state.session}
            props={{
                bounds: symbol_bounds,
                shape: Model.SHOP_DONE_SHAPE,
                color: shop_state.text_color
            }}
        />;
    }
    let amount = Model.ActivityAmount(line);
    let amount_w = Model.CoinAmountWidth(amount, shop_state.font);
    let day_w = Model.Width(line.day, shop_state.small_font) + Model.Scale(12n);
    let name_x = x + symbol + Model.Scale(12n);
    let amount_x = x + width - amount_w;
    let day_x = stacked ? name_x : amount_x - Model.Scale(12n) - day_w;
    let name_w = stacked ? amount_x - Model.Scale(12n) - name_x : day_x - name_x;
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(name_x, y, name_w, first_height),
            text: line.name,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: stacked ? NativeText.Wrap.TextWrapAuto : NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(
                day_x,
                stacked ? y + first_height : y,
                day_w,
                stacked ? Model.Scale(24n) : height
            ),
            text: line.day,
            size: shop_state.small_font,
            class_name: shop_state.muted_class,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    CoinAmount(
        amount,
        Shared.Bounds(amount_x, y, amount_w, stacked ? Model.Scale(24n) : height),
        shop_state.font
    );
    return height;
}

export function SectionTitle(title: string, x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let height = Model.SectionTitleHeight(title, width);
    let strong = Shared.NewStrong();
    nativeSet(strong, 0n, { start: 0n, end: s32(title.count) });
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(x, y, width, height),
            text: title,
            size: shop_state.font + Model.Scale(2n),
            strong: nativeSlice(strong),
            semantic_kind: SemanticKind.SemanticHeading,
            heading_level: 2n,
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    return height;
}

function RewardRow(index: s32, x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let reward = Model.ReadHabitRewardHost(index);
    let height = Model.RewardRowHeight(index, width);
    let main_height = Model.RewardMainHeight(reward, width);
    let stacked = Model.RewardStacked(reward, width);
    Card(Shared.Bounds(x, y, width, height), index === 0n ? "inbe/habits/shop/first-reward" : "");
    let pad = Model.Scale(Model.SHOP_CARD_PADDING);
    let buy_label = Model.Locale("habit_shop_buy_button");
    let buy_w = Model.RewardBuyWidth();
    let price = Shared.Number(s64(reward.price));
    let price_w = Model.CoinAmountWidth(price, shop_state.font);
    let buy_x = x + width - pad - buy_w;
    let price_x = stacked ? x + pad : buy_x - Model.Scale(14n) - price_w;
    let symbol = Model.Scale(26n);
    let name_x = x + pad + symbol + Model.Scale(12n);
    let name_w = stacked ? x + width - pad - name_x : price_x - name_x - Model.Scale(10n);
    let name_y = stacked ? y + pad : y;
    let name_h = stacked ? main_height - pad * 2n - Model.Scale(48n) : main_height;
    if (
        Button({
            session: shop_state.session,
            props: {
                id: 8500n + index,
                bounds: Shared.Bounds(x, name_y, stacked ? width : price_x - x, name_h),
                invisible: true,
                label: reward.name,
                disabled: shop_state.modal_active
            }
        })
    ) {
        Model.FormEdit(reward);
    }
    RewardSymbol(
        HabitRewardIconClamp(reward.icon),
        Shared.Bounds(x + pad, name_y + (name_h - symbol) / 2n, symbol, symbol)
    );
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(name_x, name_y, name_w, name_h),
            text: reward.name,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: stacked ? NativeText.Wrap.TextWrapAuto : NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let controls_y = stacked
        ? y + main_height - pad - Model.Scale(40n)
        : y + (main_height - Model.Scale(40n)) / 2n;
    CoinAmount(
        price,
        Shared.Bounds(price_x, controls_y, price_w, Model.Scale(40n)),
        shop_state.font
    );
    let affordable =
        shop_state.halves + s64(shop_state.borrow_limit) * 2n >= s64(reward.price) * 2n;
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8600n + index,
                buy_label,
                Shared.Bounds(buy_x, controls_y, buy_w, Model.Scale(40n)),
                affordable ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
                affordable
                    ? ButtonEmphasis.ButtonEmphasisFilled
                    : ButtonEmphasis.ButtonEmphasisSoft,
                !affordable
            )
        })
    ) {
        shop_state.buying = reward;
        shop_state.name_focused = false;
        shop_state.price_focused = false;
        shop_state.action = Habits.HABITS_SHOP_BUY;
    }
    return height;
}

// The reward's symbol before its name. A tap opens the grid of symbols
// under the name, or closes it again.
function RewardIconChooser(bounds: Rectangle): void {
    const shop_state = Model.CurrentShop();
    if (
        Button({
            session: shop_state.session,
            props: {
                id: 8425n,
                bounds: bounds,
                label: Model.Locale("habit_icon_label"),
                icon_shape:
                    RewardIconAsset(shop_state.icon).count > 0n
                        ? ""
                        : RewardIconShape(shop_state.icon),
                image: Model.RewardImage(shop_state.icon),
                icon_only: true,
                selected: shop_state.icon_open,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: shop_state.icon_open
                    ? ButtonEmphasis.ButtonEmphasisOutline
                    : ButtonEmphasis.ButtonEmphasisSoft,
                disabled: shop_state.modal_active
            }
        })
    ) {
        shop_state.icon_open = !shop_state.icon_open;
        shop_state.name_focused = false;
        shop_state.price_focused = false;
    }
}

// Every symbol a reward can have, as the habit editor offers its icons. A
// tap chooses one and closes the grid.
function IconGrid(x: s32, y: s32, width: s32): void {
    const shop_state = Model.CurrentShop();
    let columns = Model.IconColumns(width);
    let icon: s32 = s32(1n);
    while (icon <= REWARD_ICON_COUNT) {
        let index = icon - 1n;
        let selected = shop_state.icon === icon;
        if (
            Button({
                session: shop_state.session,
                props: {
                    id: 8700n + icon,
                    bounds: Shared.Bounds(
                        x +
                            (index % columns) * Model.Scale(Model.SHOP_ICON_STEP_X) +
                            Model.Scale(4n),
                        y +
                            (index / columns) * Model.Scale(Model.SHOP_ICON_STEP_Y) +
                            Model.Scale(2n),
                        Model.Scale(Model.SHOP_ICON_SIZE),
                        Model.Scale(Model.SHOP_ICON_SIZE)
                    ),
                    circle: true,
                    label: Model.Locale(RewardIconLabelKey(icon)),
                    icon_shape: RewardIconAsset(icon).count > 0n ? "" : RewardIconShape(icon),
                    image: Model.RewardImage(icon),
                    icon_only: true,
                    selected: selected,
                    tone: selected ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
                    emphasis: selected
                        ? ButtonEmphasis.ButtonEmphasisFilled
                        : ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: shop_state.modal_active
                }
            })
        ) {
            shop_state.icon = icon;
            shop_state.icon_open = false;
        }
        icon += 1n;
    }
}

// The form that adds a reward, or changes the one opened from the list.
function Form(x: s32, y: s32, width: s32): void {
    const shop_state = Model.CurrentShop();
    let editing = Model.Editing();
    Card(Shared.Bounds(x, y, width, Model.FormHeight(width)), "inbe/habits/shop/form");
    let pad = Model.Scale(Model.SHOP_FORM_PADDING);
    let inner_x = x + pad;
    let inner_w = width - pad * 2n;
    let row_y = y + pad;
    let title_text = Model.Locale(editing ? "habit_shop_edit_title" : "habit_shop_add_title");
    let strong = Shared.NewStrong();
    nativeSet(strong, 0n, { start: 0n, end: s32(title_text.count) });
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(inner_x, row_y, inner_w, Model.Scale(26n)),
            text: title_text,
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    row_y += Model.Scale(30n);
    let field_h = Model.Scale(Model.SHOP_FIELD_HEIGHT);
    // The symbol, then the name.
    RewardIconChooser(Shared.Bounds(inner_x, row_y, field_h, field_h));
    let name_x = inner_x + field_h + Model.Scale(10n);
    let submit = NameField(Shared.Bounds(name_x, row_y, inner_x + inner_w - name_x, field_h));
    row_y += field_h + Model.Scale(10n);
    if (shop_state.icon_open) {
        IconGrid(inner_x, row_y, inner_w);
        row_y += Model.IconGridHeight(inner_w) + Model.Scale(10n);
    }
    // Price − [n] + with a coin, then Add or Save at the row's end.
    let label = Model.Locale("habit_shop_price_label");
    let label_w = Model.Width(label, shop_state.font) + Model.Scale(10n);
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(inner_x, row_y, label_w, field_h),
            text: label,
            class_name: shop_state.muted_class,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapNone
        }}
    />;
    let step = Model.Scale(44n);
    let control_x = inner_x + label_w;
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8420n,
                "-",
                Shared.Bounds(control_x, row_y, step, field_h),
                ButtonTone.ButtonToneNeutral,
                ButtonEmphasis.ButtonEmphasisSoft,
                shop_state.price <= 1n
            )
        })
    ) {
        shop_state.price = HabitRewardPriceClamp(shop_state.price - 1n);
        Model.PriceText();
    }
    if (
        PriceField(
            Shared.Bounds(control_x + step + Model.Scale(6n), row_y, Model.Scale(64n), field_h)
        )
    ) {
        submit = true;
    }
    let plus_x = control_x + step + Model.Scale(76n);
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8421n,
                "+",
                Shared.Bounds(plus_x, row_y, step, field_h),
                ButtonTone.ButtonToneNeutral,
                ButtonEmphasis.ButtonEmphasisSoft,
                shop_state.price >= HABIT_REWARD_PRICE_MAX
            )
        })
    ) {
        shop_state.price = HabitRewardPriceClamp(shop_state.price + 1n);
        Model.PriceText();
    }
    let coin = Model.Scale(22n);
    Coin(Shared.Bounds(plus_x + step + Model.Scale(8n), row_y + (field_h - coin) / 2n, coin, coin));
    let action_label = Model.ActionLabel();
    let action_w = Model.ActionWidth(action_label);
    let action_x = inner_x + inner_w - action_w;
    if (Model.FormWraps(width)) {
        // A narrow screen puts Add or Save on the next line.
        row_y += field_h + Model.Scale(10n);
    }
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8422n,
                action_label,
                Shared.Bounds(action_x, row_y, action_w, field_h),
                ButtonTone.ButtonToneAccent,
                ButtonEmphasis.ButtonEmphasisFilled,
                Model.TypedName().count === 0n
            )
        })
    ) {
        submit = true;
    }
    if (submit && !shop_state.modal_active) {
        Model.FormSubmit();
        return;
    }
    if (!editing) {
        return;
    }
    row_y += field_h + Model.Scale(10n);
    let half = (inner_w - Model.Scale(10n)) / 2n;
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8423n,
                Model.Locale("delete_button"),
                Shared.Bounds(inner_x, row_y, half, Model.Scale(42n)),
                ButtonTone.ButtonToneDanger,
                ButtonEmphasis.ButtonEmphasisSoft,
                false
            )
        })
    ) {
        Model.DeleteHabitRewardHost(shop_state.editing);
        Model.FormReset();
        return;
    }
    if (
        Button({
            session: shop_state.session,
            props: ShopActionProps(
                8424n,
                Model.Locale("cancel_button"),
                Shared.Bounds(inner_x + half + Model.Scale(10n), row_y, half, Model.Scale(42n)),
                ButtonTone.ButtonToneNeutral,
                ButtonEmphasis.ButtonEmphasisOutline,
                false
            )
        })
    ) {
        Model.FormReset();
    }
}

function ActivityHeader(x: s32, y: s32, width: s32): s32 {
    const shop_state = Model.CurrentShop();
    let height = Model.ActivityHeaderHeight(width);
    SectionTitle(
        Model.Locale("profile_progress_title"),
        x,
        y +
            (height -
                Model.SectionTitleHeight(
                    Model.Locale("profile_progress_title"),
                    width - Model.Scale(52n)
                )) /
                2n,
        width - Model.Scale(52n)
    );
    if (
        Button({
            session: shop_state.session,
            props: {
                id: 8430n,
                bounds: Shared.Bounds(
                    x + width - Model.Scale(44n),
                    y,
                    Model.Scale(44n),
                    Model.Scale(44n)
                ),
                label: Model.Locale("habit_shop_stats_title"),
                icon_shape: "S1.8rr:M4 3V20H21M7 15L11 10L15 13L20 6",
                icon_only: true,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: shop_state.modal_active
            }
        })
    ) {
        shop_state.name_focused = false;
        shop_state.price_focused = false;
        shop_state.borrow_focused = false;
        shop_state.action = Habits.HABITS_SHOP_STATS_OPEN;
    }
    return height;
}

// Draws the shop in the frame's bounds.
function ShopPage(): void {
    const shop_state = Model.CurrentShop();
    let bounds = shop_state.bounds;
    let width = s32(bounds.width);
    let x = s32(bounds.x);
    if (width > Model.Scale(Model.SHOP_COLUMN_MAX)) {
        x += (width - Model.Scale(Model.SHOP_COLUMN_MAX)) / 2n;
        width = Model.Scale(Model.SHOP_COLUMN_MAX);
    }
    let top = PageHeader(
        x,
        s32(bounds.y),
        width,
        Model.Locale("habit_shop_title"),
        Model.Locale("habit_shop_subtitle")
    );
    if (top < 0n) {
        shop_state.name_focused = false;
        shop_state.price_focused = false;
        shop_state.action = Habits.HABITS_SHOP_BACK;
        return;
    }
    let gap = Model.Scale(Model.SHOP_GAP);
    let row_gap = Model.Scale(Model.SHOP_ROW_GAP);
    // The scroll bar takes the right edge; the cards stop short of it.
    let content_width = width - Model.Scale(Model.SHOP_SCROLLBAR_ROOM);
    let rewards_title = Model.Locale("habit_shop_rewards_title");
    let title_h = Model.SectionTitleHeight(rewards_title, content_width);
    let empty_text = Model.Locale("habit_shop_empty");
    let list_h: s32 = s32(0n);
    for (let index = s32(0n); index < shop_state.reward_count; index += s32(1)) {
        list_h += Model.RewardRowHeight(index, content_width) + row_gap;
    }
    if (shop_state.reward_count === 0n) {
        list_h = Model.ParagraphHeight(empty_text, content_width, shop_state.font) + row_gap;
    }
    let form_h = Model.FormHeight(content_width);
    let content_h =
        Model.Scale(Model.SHOP_BALANCE_HEIGHT) +
        Model.Scale(10n) +
        Model.BorrowRowHeight() +
        gap +
        title_h +
        Model.Scale(10n) +
        list_h +
        gap +
        form_h +
        gap;
    // Today's daily reward, to claim or claimed.
    if (shop_state.daily_day > 0n) {
        content_h += Model.DailyCardHeight() + Model.Scale(10n);
    }
    // The latest coins earned and spent, once there are any.
    content_h += Model.ActivityHeaderHeight(content_width) + Model.Scale(6n) + gap;
    if (shop_state.activity_count > 0n) {
        for (let index = s32(0n); index < shop_state.activity_count; index += s32(1)) {
            content_h += Model.ActivityRowHeight(index, content_width);
        }
    }
    const scrolled = Scroll({
        session: shop_state.session,
        props: {
            key: NativeLayout.KeyHash("inbe/habits/shop"),
            bounds: {
                x: float32(x),
                y: float32(top),
                width: float32(width),
                height: bounds.y + bounds.height - float32(top)
            },
            content_height: content_h,
            scroll_offset: shop_state.scroll
        },
        children: (scrolled: NativeScroll.ScrollResult): void => {
            const shop_state = Model.CurrentShop();
            shop_state.scroll = scrolled.scroll_offset;
            let y = s32(scrolled.content.y);
            y += BalanceCard(x, y, content_width) + Model.Scale(10n);
            if (shop_state.daily_day > 0n) {
                y += DailyCard(x, y, content_width) + Model.Scale(10n);
            }
            y += BorrowRow(x, y, content_width) + gap;
            y += SectionTitle(rewards_title, x, y, content_width) + Model.Scale(10n);
            if (shop_state.reward_count === 0n) {
                <Text
                    session={shop_state.session}
                    props={{
                        bounds: Shared.Bounds(x, y, content_width, list_h - row_gap),
                        text: empty_text,
                        class_name: shop_state.muted_class,
                        wrap: NativeText.Wrap.TextWrapAuto
                    }}
                />;
            }
            let reward_y = y;
            let index: s32 = s32(0n);
            while (index < shop_state.reward_count) {
                reward_y += RewardRow(index, x, reward_y, content_width) + row_gap;
                index += 1n;
            }
            y += list_h + gap;
            Form(x, y, content_width);
            y += form_h + gap;
            // Activity sits below the form that adds a reward.
            y += ActivityHeader(x, y, content_width) + Model.Scale(6n);
            if (shop_state.activity_count > 0n) {
                for (let index = s32(0n); index < shop_state.activity_count; index += s32(1)) {
                    y += ActivityRow(index, x, y, content_width);
                }
            }
        }
    });
    if (!scrolled.opened) {
        shop_state.scroll = scrolled.scroll_offset;
    }
}

// Asks before a reward's price is spent: the reward, its price and the
// coins left after it.
function BuyDialog(): void {
    const shop_state = Model.CurrentShop();
    let reward = shop_state.buying;
    let width = shop_state.view_width - Model.Scale(32n);
    if (width > Model.Scale(380n)) {
        width = Model.Scale(380n);
    }
    let frame = NativeModal.Draw(shop_state.session, {
        key: NativeLayout.KeyHash("inbe/habits/shop/buy"),
        title: Model.Locale("habit_shop_buy_title"),
        width: width,
        height: Model.Scale(250n),
        scale: shop_state.scale
    });
    if (frame.dismissed) {
        shop_state.action = Habits.HABITS_SHOP_CLOSE;
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content = frame.layout.content;
    let x = s32(content.x);
    let y = s32(content.y);
    let inner_w = s32(content.width);
    let symbol = Model.Scale(30n);
    RewardSymbol(HabitRewardIconClamp(reward.icon), Shared.Bounds(x, y, symbol, symbol));
    let strong = Shared.NewStrong();
    nativeSet(strong, 0n, { start: 0n, end: s32(reward.name.count) });
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(
                x + symbol + Model.Scale(10n),
                y,
                inner_w - symbol - Model.Scale(10n),
                Model.Scale(30n)
            ),
            text: reward.name,
            strong: nativeSlice(strong),
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    y += Model.Scale(34n);
    CoinAmount(
        Shared.Number(s64(reward.price)),
        Shared.Bounds(x, y, inner_w, Model.Scale(30n)),
        shop_state.font + Model.Scale(4n)
    );
    y += Model.Scale(36n);
    let left = shop_state.halves - s64(reward.price) * 2n;
    <Text
        session={shop_state.session}
        props={{
            bounds: Shared.Bounds(x, y, inner_w, Model.Scale(24n)),
            text: Model.Filled(Model.Locale("habit_shop_buy_left"), Shared.Coins(left)),
            size: shop_state.small_font,
            class_name: shop_state.muted_class,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let button_y = s32(content.y + content.height) - Model.Scale(44n);
    let half = (inner_w - Model.Scale(10n)) / 2n;
    let cancelled = Button({
        session: shop_state.session,
        props: {
            id: 8430n,
            bounds: Shared.Bounds(x, button_y, half, Model.Scale(42n)),
            label: Model.Locale("cancel_button"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisOutline,
            fit_content: true
        }
    });
    let bought = Button({
        session: shop_state.session,
        props: {
            id: 8431n,
            bounds: Shared.Bounds(x + half + Model.Scale(10n), button_y, half, Model.Scale(42n)),
            label: Model.Locale("habit_shop_buy_button"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
            fit_content: true,
            disabled: left < -s64(shop_state.borrow_limit) * 2n
        }
    });
    End(shop_state.session);
    if (cancelled) {
        shop_state.action = Habits.HABITS_SHOP_CLOSE;
        return;
    }
    if (bought) {
        Model.BuyHabitRewardHost(reward);
        shop_state.action = Habits.HABITS_SHOP_CLOSE;
    }
}

export function HabitsShopView(message: Habits.HabitsMessage): Habits.HabitsMessage {
    const shop_state = Model.CurrentShop();
    Model.SetShop(Model.ReadHabitsShopHost());
    shop_state.action = Habits.HABITS_SHOP_NONE;
    shop_state.clipboard_write = false;
    if (message.action === Habits.HABITS_SHOP_BUY_DIALOG) {
        BuyDialog();
    } else {
        ShopPage();
    }
    Model.WriteHabitsShopHost(nativeDeref(shop_state));
    message.succeeded = true;
    return message;
}
