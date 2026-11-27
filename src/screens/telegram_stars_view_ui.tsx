import * as StarsState from "telegram_stars";
import * as StarsViewState from "telegram_stars_view";
import { app_content_bottom_reserved } from "app_nav_state";
// Authored UI composition; native application state remains in telegram_stars_view.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeTitleBar from "kryon/title_bar";
import { app_block_current_click } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { StoredDelegateGeneration } from "delegate_store";
import { DewFormat, DewUnits } from "entity/dew_model";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, MetricsScale } from "metrics";
import { ProfileDewFormatDew } from "profile_dew";
import { TextUntilNul } from "std/text_buffer";
import {
    TelegramStarsCancelPurchase,
    TelegramStarsCurrent,
    TelegramStarsLaunch,
    TelegramStarsNetworkBusy,
    TelegramStarsRetry,
    TelegramStarsSelect
} from "telegram_stars";
import {
    TelegramStarsViewNewAmount,
    TelegramStarsViewNewBalance,
    TelegramStarsViewNewOptions,
    TelegramStarsViewNewTerms,
    TelegramStarsViewNewUnits,
    TelegramStarsFooterHeight
} from "telegram_stars_view";
import { AppFormatS64, FormatArg, FormatTemplate, FrameTextHold } from "text_buffers";

export function TelegramStarsFooter(app: NativeRef<InnerBreeze>): void {
    let height = TelegramStarsFooterHeight();
    if (height === 0n) {
        return;
    }
    let column = NativeLayout.CenteredColumnFor(app.ui.view_width, AppScale(720n), AppScale(16n));
    let bottom = app.ui.view_height - app_content_bottom_reserved(app);
    if (
        Button({
            session: app.ui.session,
            props: {
                id: 7930n,
                label: LocaleText("telegram_stars_title"),
                bounds: {
                    x: float32(column.x),
                    y: float32(bottom - height + AppScale(4n)),
                    width: float32(column.width),
                    height: float32(AppScale(48n))
                }
            }
        })
    ) {
        TelegramStarsLaunch();
        StarsState.telegram_stars_visible = StarsState.telegram_stars.requested;
        StarsViewState.telegram_stars_scroll = 0n;
        app_block_current_click(app);
    }
}

export function TelegramStarsText(
    app: NativeRef<InnerBreeze>,
    value: string,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    height: s32
): void {
    <Text
        session={app.ui.session}
        props={{
            text: FrameTextHold(nativeRef(app.ui.frame_text), value),
            size: AppFontSize(),
            wrap: Wrap.TextWrapAuto,
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(height)
            }
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + height;
}

export function TelegramStarsPage(app: NativeRef<InnerBreeze>): boolean {
    let flow = nativeRef(StarsState.telegram_stars);
    if (
        !StarsState.telegram_stars_visible ||
        !TelegramStarsCurrent() ||
        flow.generation !== StoredDelegateGeneration()
    ) {
        return false;
    }
    let top = AppScale(52n);
    let bar: NativeTitleBar.Props = {
        key: NativeLayout.KeyHash("inbe/telegram/stars/title"),
        title: LocaleText("telegram_stars_title"),
        height: top,
        bounds: { x: 0.0, y: 0.0, width: float32(app.ui.view_width), height: float32(top) },
        has_leading_action: true,
        leading_label: LocaleText("back_button")
    };
    let options = TelegramStarsViewNewOptions();
    if (
        TitleBar({ session: app.ui.session, props: bar, options: nativeSlice(options, 0n, 0n) })
            .clicked_leading
    ) {
        StarsState.telegram_stars_visible = false;
        app_block_current_click(app);
        return true;
    }
    let column = NativeLayout.CenteredColumnFor(app.ui.view_width, AppScale(620n), AppScale(16n));
    let bottom = app.ui.view_height - app_content_bottom_reserved(app);
    let busy = TelegramStarsNetworkBusy() || flow.sheet;
    let can_retry =
        !busy &&
        (flow.notice === "telegram_stars_error" || flow.notice === "telegram_stars_pending");
    let can_cancel = !busy && nativeAt(flow.invoice.invoice_id, 0n) !== 0n;
    let panel = NativeScroll.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("inbe/telegram/stars/scroll"),
        bounds: {
            x: 0.0,
            y: float32(top),
            width: float32(app.ui.view_width),
            height: float32(bottom - top)
        },
        content_height: AppScale(166n + flow.catalog.count * 86n),
        scroll_offset: StarsViewState.telegram_stars_scroll,
        scale: MetricsScale()
    });
    StarsViewState.telegram_stars_scroll = panel.scroll_offset;
    if (!panel.opened) {
        return true;
    }
    let y = s32(panel.content.y) + AppScale(8n);
    if (flow.balance_known) {
        let balance = TelegramStarsViewNewBalance();
        ProfileDewFormatDew(
            flow.balance,
            LocaleText("profile_dew_balance_line"),
            nativeSlice(balance)
        );
        TelegramStarsText(
            app,
            TextUntilNul(nativeSlice(balance)),
            column.x,
            column.width,
            nativeRef(y),
            AppScale(32n)
        );
    }
    if (flow.notice !== "") {
        TelegramStarsText(
            app,
            LocaleText(flow.notice),
            column.x,
            column.width,
            nativeRef(y),
            AppScale(64n)
        );
    }
    if (can_retry || can_cancel) {
        let width = can_retry && can_cancel ? (column.width - AppScale(8n)) / 2n : column.width;
        if (
            can_retry &&
            Button({
                session: app.ui.session,
                props: {
                    id: 7931n,
                    label: LocaleText("retry_button"),
                    bounds: {
                        x: float32(column.x),
                        y: float32(y),
                        width: float32(width),
                        height: float32(AppScale(48n))
                    }
                }
            })
        ) {
            TelegramStarsRetry();
        }
        let cancel_x = can_retry ? column.x + width + AppScale(8n) : column.x;
        if (
            can_cancel &&
            Button({
                session: app.ui.session,
                props: {
                    id: 7932n,
                    label: LocaleText("cancel_button"),
                    bounds: {
                        x: float32(cancel_x),
                        y: float32(y),
                        width: float32(width),
                        height: float32(AppScale(48n))
                    }
                }
            })
        ) {
            TelegramStarsCancelPurchase();
        }
        y = y + AppScale(56n);
    }
    for (let index = s32(0n); index < flow.catalog.count; index += s32(1)) {
        let product = nativeRef(nativeAt(flow.catalog.products, index));
        let units = TelegramStarsViewNewUnits();
        let amount = TelegramStarsViewNewAmount();
        DewFormat(product.units, DewUnits, nativeSlice(units));
        AppFormatS64(product.amount, nativeSlice(amount));
        let terms = TelegramStarsViewNewTerms();
        let values: [FormatArg, FormatArg] = [
            { text: TextUntilNul(nativeSlice(units)), is_text: true },
            { text: TextUntilNul(nativeSlice(amount)), is_text: true }
        ];
        if (
            FormatTemplate(
                LocaleText("telegram_stars_product_terms"),
                nativeSlice(values),
                nativeSlice(terms)
            )
        ) {
            TelegramStarsText(
                app,
                TextUntilNul(nativeSlice(terms)),
                column.x,
                column.width,
                nativeRef(y),
                AppScale(32n)
            );
        }
        if (
            Button({
                session: app.ui.session,
                props: {
                    id: 7940n + index,
                    label: TextUntilNul(nativeSlice(product.title)),
                    bounds: {
                        x: float32(column.x),
                        y: float32(y),
                        width: float32(column.width),
                        height: float32(AppScale(46n))
                    },
                    disabled: busy || nativeAt(flow.nonce, 0n) !== 0n
                }
            })
        ) {
            TelegramStarsSelect(index);
        }
        y = y + AppScale(54n);
    }
    End(app.ui.session);
    return true;
}
