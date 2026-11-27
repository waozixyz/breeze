import { ProfileDewNewLink } from "profile_dew";
import { ProfileDewNewAddress } from "profile_dew";
import { ProfileDewNewUri } from "profile_dew";
import { ProfileDewNewMinimumUsd } from "profile_dew";
import { ProfileDewNewMinimum } from "profile_dew";
import { ProfileDewNewLine384u8 } from "profile_dew";
import { ProfileDewNewDetail } from "profile_dew";
import { ProfileDewNewLabel } from "profile_dew";
import { ProfileDewNewSize } from "profile_dew";
import { ProfileDewNewOptions } from "profile_dew";
import { ProfileDewNewLabels } from "profile_dew";
import { ProfileDewNewLine192u8 } from "profile_dew";
import { ProfileDewNewLine } from "profile_dew";
import { ProfileDewNewLimit } from "profile_dew";
import { ProfileDewNewUsed } from "profile_dew";
// Authored UI composition; native application state remains in profile_dew.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeText from "kryon/text";
import * as State_dew from "dew";
import * as State_profile_dew from "profile_dew";
import * as State_entity_dew_model from "entity/dew_model";
import * as State_dew_payment from "dew_payment";
import { app_close_modal } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { DewBuyStorage, DewRatesRefresh, DewReady } from "dew";
import { DewAppendWorth, DewUsdText } from "dew_worth";
import { DewFormat, DewPlanCount } from "entity/dew_model";
import { DEW_PLAY_PRODUCTS, DewPlayBuy } from "entity/dew_play";
import { DewPlaySavings } from "entity/dew_play_pricing";
import { HostSeconds } from "host_clock";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { DarkenColor, StyleTokenColor, StyleTokenColorOr } from "kryon/drawing_props";
import { OpenUri } from "kryon/open_uri";
import {
    PlayBillingProduct,
    PlayBillingProducts,
    PlayBillingRead,
    PlayBillingState
} from "kryon/play_billing";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { LoadingIndicator } from "kryon/tsx/loading_indicator";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFontSize, AppParagraphHeight, AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import {
    EmptyPlayBillingProduct,
    ProfileDewContent,
    ProfileDewCurrentSize,
    ProfileDewDaysLeft,
    ProfileDewExchangeText,
    ProfileDewFormatDew,
    ProfileDewHeight,
    ProfileDewSizeText,
    ProfileTopUpAddressText,
    ProfileTopUpPlayNotice,
    ProfileTopUpPump,
    TopUpMinimumShown
} from "profile_dew";
import { DrawQrCode } from "qr_code_view";
import { AppRequestSmoothFrames } from "smooth_frames";
import { TextUntilNul } from "std/text_buffer";
import {
    SyncNodeStorage,
    SyncNodeStorageNearlyFull,
    SyncNodeStoragePercent,
    SyncStorageFormatBytes
} from "sync_node_storage";
import {
    AppAppendText,
    AppCopyText,
    FormatArg,
    FormatNumberTemplate,
    FormatTemplate,
    FrameTextHold
} from "text_buffers";
import { TextInputWriteClipboard } from "text_input_host";

export function ProfileDewText(
    app: *InnerBreeze,
    text: string,
    x: s32,
    y: *s32,
    width: s32,
    font: s32,
    draw: boolean
): void {
    let height = AppParagraphHeight(text, width, font, 0n);
    if (draw) {
        <Text
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32((*y)),
                    width: float32(width),
                    height: float32(height)
                },
                text: FrameTextHold(&app.ui.frame_text, text),
                size: font,
                wrap: Wrap.TextWrapAuto
            }}
        />;
    }
    (*y) = (*y) + (height + AppScale(8n));
}

export function ProfileDewButton(
    app: *InnerBreeze,
    label: string,
    x: s32,
    y: *s32,
    width: s32,
    disabled: boolean,
    draw: boolean,
    detail: string = ""
): boolean {
    let height = AppScale(detail.count > 0n ? 58n : 44n);
    let clicked = false;
    if (draw) {
        clicked = (
            <Button
                session={app.ui.session}
                props={{
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(width),
                        height: float32(height)
                    },
                    label: FrameTextHold(&app.ui.frame_text, label),
                    detail: FrameTextHold(&app.ui.frame_text, detail),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: disabled
                }}
            />
        );
    }
    (*y) = (*y) + (height + AppScale(8n));
    return clicked;
}

export function ProfileDewUsage(
    app: *InnerBreeze,
    x: s32,
    y: *s32,
    width: s32,
    draw: boolean
): void {
    if (State_dew.dew_account.limit_bytes <= 0n) {
        return;
    }
    let storage: SyncNodeStorage = {
        known: true,
        used_bytes: State_dew.dew_account.used_bytes,
        limit_bytes: State_dew.dew_account.limit_bytes
    };
    let bar_h = AppScale(8n);
    if (draw) {
        <Box
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32((*y)),
                    width: float32(width),
                    height: float32(bar_h)
                },
                fill: DarkenColor(StyleTokenColor("canvas"), 18n),
                radius: float32(bar_h) / 2.0
            }}
        />;
        let fill_w = s32((s64(width) * s64(SyncNodeStoragePercent(storage))) / 100n);
        if (storage.used_bytes > 0n && fill_w < bar_h) {
            fill_w = bar_h;
        }
        let color = StyleTokenColor("accent");
        if (storage.used_bytes >= storage.limit_bytes) {
            color = StyleTokenColorOr("storage-full", { r: 179n, g: 38n, b: 30n, a: 255n });
        } else if (SyncNodeStorageNearlyFull(storage)) {
            color = StyleTokenColorOr("storage-warning", { r: 163n, g: 98n, b: 0n, a: 255n });
        }
        if (fill_w > 0n) {
            <Box
                session={app.ui.session}
                props={{
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(fill_w),
                        height: float32(bar_h)
                    },
                    fill: color,
                    radius: float32(bar_h) / 2.0
                }}
            />;
        }
    }
    (*y) = (*y) + (bar_h + AppScale(8n));
    let used = ProfileDewNewUsed();
    let limit = ProfileDewNewLimit();
    let line = ProfileDewNewLine();
    SyncStorageFormatBytes(storage.used_bytes, used[:]);
    SyncStorageFormatBytes(storage.limit_bytes, limit[:]);
    let arguments: [FormatArg, FormatArg] = [
        { text: TextUntilNul(used[:]), is_text: true },
        { text: TextUntilNul(limit[:]), is_text: true }
    ];
    FormatTemplate(
        LocaleText("profile_node_storage_used_of"),
        arguments[:],
        line[:]
    );
    ProfileDewText(
        app,
        TextUntilNul(line[:]),
        x,
        y,
        width,
        AppSmallFontSize(),
        draw
    );
}

export function ProfileDewDraw(
    app: *InnerBreeze,
    x: s32,
    y: *s32,
    width: s32
): void {
    let height = ProfileDewHeight(app, width);
    if (height === 0n) {
        return;
    }
    if (State_dew.dew_account.known && DewReady()) {
        DewRatesRefresh();
    }
    <Box
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32((*y)),
                width: float32(width),
                height: float32(height - AppScale(8n))
            },
            fill: DarkenColor(StyleTokenColor("canvas"), 7n),
            radius: float32(AppScale(12n))
        }}
    />;
    let inner = (*y) + AppScale(14n);
    ProfileDewContent(app, x + AppScale(14n), &inner, width - AppScale(28n), true);
    (*y) = (*y) + height;
}

export function ProfileStoragePlansContent(
    app: *InnerBreeze,
    x: s32,
    y: *s32,
    width: s32,
    draw: boolean
): void {
    let line = ProfileDewNewLine192u8();
    ProfileDewFormatDew(
        State_dew.dew_account.balance,
        LocaleText("profile_dew_balance_line"),
        line[:]
    );
    ProfileDewText(
        app,
        TextUntilNul(line[:]),
        x,
        y,
        width,
        AppSmallFontSize(),
        draw
    );
    ProfileDewUsage(app, x, y, width, draw);
    let labels = ProfileDewNewLabels();
    AppCopyText(LocaleText("profile_dew_plan_free"), labels[0n][:]);
    for (let index = s32(0n); index < DewPlanCount; index += s32(1)) {
        ProfileDewSizeText(
            State_dew.dew_account.plans[index].limit_bytes,
            labels[index + 1n][:]
        );
    }
    if (draw) {
        let options = ProfileDewNewOptions();
        for (let index = s32(0n); index <= DewPlanCount; index += s32(1)) {
            options[index].label = FrameTextHold(
                &app.ui.frame_text,
                TextUntilNul(labels[index][:])
            );
        }
        let props: NativeSegmentedControl.Props = {};
        props.key = NativeLayout.KeyHash("profile/storage/tabs");
        props.bounds = {
            x: float32(x),
            y: float32((*y)),
            width: float32(width),
            height: float32(AppScale(42n))
        };
        props.height = AppScale(42n);
        props.selected_index = State_profile_dew.profile_storage_tab;
        props.has_selection = true;
        let choice = (
            <SegmentedControl
                session={app.ui.session}
                props={props}
                options={options[:]}
            />
        );
        if (choice.changed) {
            State_profile_dew.profile_storage_tab = choice.selected_index;
            State_dew.dew_notice = "";
        }
    }
    (*y) = (*y) + AppScale(54n);
    let tab = State_profile_dew.profile_storage_tab;
    let size = ProfileDewNewSize();
    if (tab === 0n) {
        ProfileDewSizeText(State_dew.dew_account.free_bytes, size[:]);
    } else {
        AppCopyText(
            TextUntilNul(labels[tab][:]),
            size[:]
        );
    }
    ProfileDewText(
        app,
        TextUntilNul(size[:]),
        x,
        y,
        width,
        AppScale(NativeText.Text24),
        draw
    );
    let current = ProfileDewCurrentSize();
    if (tab === current) {
        if (current === 0n) {
            AppCopyText(LocaleText("profile_dew_plan_current"), line[:]);
        } else {
            FormatNumberTemplate(
                LocaleText("profile_dew_plan_current_days"),
                ProfileDewDaysLeft(),
                line[:]
            );
        }
        ProfileDewText(
            app,
            TextUntilNul(line[:]),
            x,
            y,
            width,
            AppFontSize(),
            draw
        );
    } else if (tab === 0n) {
        ProfileDewText(
            app,
            LocaleText("profile_dew_plan_free_after"),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
    } else if (current > 0n) {
        ProfileDewText(
            app,
            LocaleText("profile_dew_plan_switch"),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
    }
    if (State_dew.dew_notice.count > 0n) {
        ProfileDewText(
            app,
            LocaleText(State_dew.dew_notice),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
    }
    if (tab === 0n) {
        return;
    }
    if (!State_dew.dew_account.enabled) {
        ProfileDewText(
            app,
            LocaleText("profile_dew_disabled"),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
        return;
    }
    let busy = State_dew.dew_operation.active;
    if (State_dew.dew_attempt[0n] !== u8(0n)) {
        if (ProfileDewButton(app, LocaleText("profile_dew_retry"), x, y, width, busy, draw)) {
            DewBuyStorage("", "");
        }
    } else {
        let offer = State_dew.dew_account.plans[tab - 1n];
        ProfileDewFormatDew(
            offer.monthly_units,
            LocaleText("profile_dew_month"),
            line[:]
        );
        if (
            ProfileDewButton(
                app,
                TextUntilNul(line[:]),
                x,
                y,
                width,
                busy,
                draw
            )
        ) {
            DewBuyStorage(State_entity_dew_model.DewPlanSizes[tab - 1n], "monthly");
        }
        ProfileDewFormatDew(
            offer.yearly_units,
            LocaleText("profile_dew_year"),
            line[:]
        );
        if (
            ProfileDewButton(
                app,
                TextUntilNul(line[:]),
                x,
                y,
                width,
                busy,
                draw
            )
        ) {
            DewBuyStorage(State_entity_dew_model.DewPlanSizes[tab - 1n], "yearly");
        }
    }
    ProfileDewText(app, LocaleText("profile_dew_rates"), x, y, width, AppSmallFontSize(), draw);
}

export function ProfileStoragePlansModalDraw(app: *InnerBreeze): void {
    let width = app.ui.view_width - AppScale(32n);
    if (width > AppScale(520n)) {
        width = AppScale(520n);
    }
    if (
        State_profile_dew.profile_storage_tab < 0n ||
        State_profile_dew.profile_storage_tab > DewPlanCount
    ) {
        State_profile_dew.profile_storage_tab = 0n;
    }
    let chosen = State_profile_dew.profile_storage_tab;
    let tallest: s32 = 0n;
    for (let tab = s32(0n); tab <= DewPlanCount; tab += s32(1)) {
        State_profile_dew.profile_storage_tab = tab;
        let measured: s32 = 0n;
        ProfileStoragePlansContent(app, 0n, &measured, width - AppScale(46n), false);
        if (measured > tallest) {
            tallest = measured;
        }
    }
    State_profile_dew.profile_storage_tab = chosen;
    let height = tallest + AppScale(96n);
    if (height > app.ui.view_height - AppScale(48n)) {
        height = app.ui.view_height - AppScale(48n);
    }
    DewRatesRefresh();
    let frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("profile/storage/modal"),
        title: LocaleText("profile_dew_plans"),
        width: width,
        height: height,
        scale: MetricsScale(),
        title_at_start: true,
        strong_title: true,
        has_right_action: true,
        right_label: LocaleText("close_button")
    });
    if (frame.dismissed || frame.right_clicked || !DewReady() || !State_dew.dew_account.known) {
        app_close_modal(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content_w = s32(frame.layout.content.width) - AppScale(10n);
    let content_h: s32 = 0n;
    ProfileStoragePlansContent(app, 0n, &content_h, content_w, false);
    let scroll = NativeScroll.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("profile/storage/scroll"),
        bounds: frame.layout.content,
        content_height: content_h,
        scroll_offset: State_profile_dew.profile_storage_scroll
    });
    State_profile_dew.profile_storage_scroll = scroll.scroll_offset;
    if (scroll.opened) {
        let y = s32(scroll.content.y);
        ProfileStoragePlansContent(app, s32(scroll.content.x), &y, content_w, true);
        End(app.ui.session);
    }
    End(app.ui.session);
}

export function ProfileTopUpPlayContent(
    app: *InnerBreeze,
    x: s32,
    y: *s32,
    width: s32,
    draw: boolean
): void {
    let billing: PlayBillingState = {};
    PlayBillingRead(
        TextUntilNul(State_dew_payment.dew_play.state[:]),
        &billing
    );
    let busy =
        State_dew.dew_operation.active ||
        TextUntilNul(State_dew_payment.dew_play.status[:]) === "verifying";
    let packs: [string, string, string, string, string] = [
        "dew_10",
        "dew_100",
        "dew_500",
        "dew_1000",
        "dew_5000"
    ];
    let shown: s32 = 0n;
    let savings_shown = false;
    for (const pack of packs) {
        let product: *PlayBillingProduct = EmptyPlayBillingProduct();
        for (let index = s32(0n); index <= 7n; index += s32(1)) {
            if (index >= billing.product_count) {
                break;
            }
            let candidate = &billing.products[index];
            if (TextUntilNul(candidate.id[:]) === pack) {
                product = candidate;
            }
        }
        if (!NativePresent(product)) {
            continue;
        }
        let label = ProfileDewNewLabel();
        let arguments: [FormatArg] = [{ text: pack[4n:], is_text: true }];
        FormatTemplate(
            LocaleText("profile_dew_play_pack"),
            arguments[:],
            label[:]
        );
        let price = TextUntilNul(product.price[:]);
        let detail = ProfileDewNewDetail();
        AppCopyText(price, detail[:]);
        let savings = DewPlaySavings(
            TextUntilNul(State_dew_payment.dew_play.state[:]),
            pack
        );
        if (savings > 0n) {
            let detail_args: [FormatArg, FormatArg] = [
                { text: price, is_text: true },
                { number: savings }
            ];
            FormatTemplate(
                "%s · −%d%%",
                detail_args[:],
                detail[:]
            );
            savings_shown = true;
        }
        if (
            ProfileDewButton(
                app,
                TextUntilNul(label[:]),
                x,
                y,
                width,
                busy,
                draw,
                TextUntilNul(detail[:])
            )
        ) {
            DewPlayBuy(
                &State_dew_payment.dew_play,
                pack,
                TextUntilNul(State_dew.dew_identity[:])
            );
        }
        shown = shown + 1n;
    }
    if (savings_shown) {
        ProfileDewText(
            app,
            LocaleText("profile_dew_play_comparison"),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
    }
    let notice = ProfileTopUpPlayNotice(&billing, shown);
    if (notice !== "") {
        ProfileDewText(app, notice, x, y, width, AppSmallFontSize(), draw);
    }
    if (shown === 0n && notice === LocaleText("profile_dew_play_unavailable")) {
        if (ProfileDewButton(app, LocaleText("retry_button"), x, y, width, busy, draw)) {
            State_profile_dew.profile_play_prices_deadline = HostSeconds() + 15.0;
            PlayBillingProducts(
                DEW_PLAY_PRODUCTS,
                State_dew_payment.dew_play.state[:]
            );
        }
    } else if (shown === 0n && notice === LocaleText("profile_dew_play_loading")) {
        if (draw) {
            <LoadingIndicator
                session={app.ui.session}
                props={{
                    key: NativeLayout.KeyHash("profile/dew/play/loading"),
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(width),
                        height: float32(AppScale(28n))
                    },
                    now: HostSeconds(),
                    scale: MetricsScale() * 0.7
                }}
            />;
            AppRequestSmoothFrames(2n);
        }
        (*y) = (*y) + AppScale(36n);
    }
}

export function ProfileTopUpContent(
    app: *InnerBreeze,
    x: s32,
    y: *s32,
    width: s32,
    draw: boolean
): void {
    let line = ProfileDewNewLine384u8();
    ProfileDewFormatDew(
        State_dew.dew_account.balance,
        LocaleText("profile_dew_balance_line"),
        line[:]
    );
    if (State_dew_payment.dew_play.enabled) {
        ProfileDewText(
            app,
            TextUntilNul(line[:]),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
        ProfileTopUpPlayContent(app, x, y, width, draw);
        return;
    }
    DewAppendWorth(State_dew.dew_account.balance, line[:]);
    ProfileDewText(
        app,
        TextUntilNul(line[:]),
        x,
        y,
        width,
        AppSmallFontSize(),
        draw
    );
    if (ProfileDewExchangeText(line[:])) {
        ProfileDewText(
            app,
            TextUntilNul(line[:]),
            x,
            y,
            width,
            AppSmallFontSize(),
            draw
        );
    }
    if (State_dew.dew_address[0n] === u8(0n)) {
        if (State_profile_dew.profile_topup_failed) {
            ProfileDewText(
                app,
                LocaleText("profile_dew_topup_error"),
                x,
                y,
                width,
                AppFontSize(),
                draw
            );
            if (
                ProfileDewButton(
                    app,
                    LocaleText("retry_button"),
                    x,
                    y,
                    width,
                    State_dew.dew_operation.active,
                    draw
                )
            ) {
                State_profile_dew.profile_topup_started = false;
                State_profile_dew.profile_topup_failed = false;
            }
        } else {
            ProfileDewText(
                app,
                LocaleText("profile_dew_topup_loading"),
                x,
                y,
                width,
                AppFontSize(),
                draw
            );
        }
        return;
    }
    line = {};
    if (State_dew.dew_minimum_atomic >= TopUpMinimumShown) {
        let minimum = ProfileDewNewMinimum();
        DewFormat(
            State_dew.dew_minimum_atomic,
            s64(1000000000000n),
            minimum[:]
        );
        let minimum_usd = ProfileDewNewMinimumUsd();
        if (DewUsdText(State_dew.dew_minimum_atomic, minimum_usd[:])) {
            let hint_arguments: [FormatArg, FormatArg, FormatArg] = [
                { text: TextUntilNul(minimum[:]), is_text: true },
                { text: TextUntilNul(minimum_usd[:]), is_text: true },
                { number: s32(State_dew.dew_confirmations) }
            ];
            FormatTemplate(
                LocaleText("profile_dew_topup_hint_usd"),
                hint_arguments[:],
                line[:]
            );
        } else {
            let hint_arguments: [FormatArg, FormatArg] = [
                { text: TextUntilNul(minimum[:]), is_text: true },
                { number: s32(State_dew.dew_confirmations) }
            ];
            FormatTemplate(
                LocaleText("profile_dew_topup_hint"),
                hint_arguments[:],
                line[:]
            );
        }
    } else {
        let send_arguments: [FormatArg] = [{ number: s32(State_dew.dew_confirmations) }];
        FormatTemplate(
            LocaleText("profile_dew_topup_send"),
            send_arguments[:],
            line[:]
        );
    }
    ProfileDewText(
        app,
        TextUntilNul(line[:]),
        x,
        y,
        width,
        AppSmallFontSize(),
        draw
    );
    let side = width;
    if (side > AppScale(220n)) {
        side = AppScale(220n);
    }
    let uri = ProfileDewNewUri();
    AppCopyText("monero:", uri[:]);
    AppAppendText(
        TextUntilNul(State_dew.dew_address[:]),
        uri[:]
    );
    if (draw) {
        DrawQrCode(app.ui.session, TextUntilNul(uri[:]), {
            x: float32(x + (width - side) / 2n),
            y: float32((*y)),
            width: float32(side),
            height: float32(side)
        });
    }
    (*y) = (*y) + (side + AppScale(12n));
    let address = ProfileDewNewAddress();
    ProfileTopUpAddressText(address[:]);
    let address_text = TextUntilNul(address[:]);
    let address_height = AppParagraphHeight(address_text, width, AppSmallFontSize(), 0n);
    if (draw) {
        <Text
            session={app.ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32((*y)),
                    width: float32(width),
                    height: float32(address_height)
                },
                text: FrameTextHold(&app.ui.frame_text, address_text),
                size: AppSmallFontSize(),
                wrap: Wrap.TextWrapAuto,
                align: TextAlign.TextAlignCenter
            }}
        />;
    }
    (*y) = (*y) + (address_height + AppScale(16n));
    let half = (width - AppScale(8n)) / 2n;
    let row_y = (*y);
    let copy_y = row_y;
    if (
        ProfileDewButton(
            app,
            LocaleText(
                State_profile_dew.profile_topup_copied ? "address_copied" : "copy_address_button"
            ),
            x,
            &copy_y,
            half,
            false,
            draw
        )
    ) {
        State_profile_dew.profile_topup_copied = TextInputWriteClipboard(
            TextUntilNul(State_dew.dew_address[:])
        );
    }
    let wallet_y = row_y;
    if (
        ProfileDewButton(
            app,
            LocaleText("open_wallet_button"),
            x + width - half,
            &wallet_y,
            half,
            false,
            draw
        )
    ) {
        OpenUri(TextUntilNul(uri[:]));
    }
    (*y) = copy_y;
    if (ProfileDewButton(app, LocaleText("dew_other_coin_button"), x, y, width, false, draw)) {
        let link = ProfileDewNewLink();
        AppCopyText("https://dew.waozi.xyz/?account=", link[:]);
        AppAppendText(
            TextUntilNul(State_dew.dew_identity[:]),
            link[:]
        );
        OpenUri(TextUntilNul(link[:]));
    }
}

export function ProfileTopUpModalDraw(app: *InnerBreeze): void {
    if (!State_dew_payment.dew_play.enabled) {
        ProfileTopUpPump();
        DewRatesRefresh();
    }
    let width = app.ui.view_width - AppScale(32n);
    if (width > AppScale(480n)) {
        width = AppScale(480n);
    }
    let measured: s32 = 0n;
    ProfileTopUpContent(app, 0n, &measured, width - AppScale(46n), false);
    let height = measured + AppScale(96n);
    if (height > app.ui.view_height - AppScale(48n)) {
        height = app.ui.view_height - AppScale(48n);
    }
    let frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("profile/topup/modal"),
        title: LocaleText("profile_dew_topup_title"),
        width: width,
        height: height,
        scale: MetricsScale(),
        title_at_start: true,
        strong_title: true,
        has_right_action: true,
        right_label: LocaleText("close_button")
    });
    if (frame.dismissed || frame.right_clicked || !DewReady() || !State_dew.dew_account.known) {
        app_close_modal(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content_w = s32(frame.layout.content.width) - AppScale(10n);
    let content_h: s32 = 0n;
    ProfileTopUpContent(app, 0n, &content_h, content_w, false);
    let scroll = NativeScroll.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("profile/topup/scroll"),
        bounds: frame.layout.content,
        content_height: content_h,
        scroll_offset: State_profile_dew.profile_topup_scroll
    });
    State_profile_dew.profile_topup_scroll = scroll.scroll_offset;
    if (scroll.opened) {
        let y = s32(scroll.content.y);
        ProfileTopUpContent(app, s32(scroll.content.x), &y, content_w, true);
        End(app.ui.session);
    }
    End(app.ui.session);
}
