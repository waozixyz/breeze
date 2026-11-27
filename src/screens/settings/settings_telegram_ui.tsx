import * as State_lumi_telegram from "lumi_telegram";
import { app_apply_nav_route } from "app_nav_state";
// Authored UI composition; native application state remains in settings_telegram.zi.
import * as NativeText from "kryon/text";
import * as State_lumi_authorization from "lumi_authorization";
import * as State_settings_telegram from "settings_telegram";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis } from "kryon/control_props";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    LumiAuthorizationApprove,
    LumiAuthorizationBusy,
    LumiAuthorizationCanRequest,
    LumiAuthorizationCancel,
    LumiAuthorizationRequest,
    LumiAuthorizationStatusKey
} from "lumi_authorization";
import { LumiNodeTrafficAllowed } from "lumi_connection";
import {
    LumiTelegramBusy,
    LumiTelegramDisconnect,
    LumiTelegramLink,
    LumiTelegramOpen,
    LumiTelegramStatusKey
} from "lumi_telegram";
import { AppFontSize, AppScale } from "metrics";
import { PackageFree } from "package_files";
import { AppNavRoute } from "route_types";
import {
    settings_telegram_authorization_active,
    settings_telegram_review_text,
    settings_telegram_stars_ready,
    settings_telegram_text_height
} from "settings_telegram";
import { storage_get_setting_text } from "storage_settings";
import { storage_has_sync_account } from "sync_state";
import { FrameTextHold } from "text_buffers";

export function settings_telegram_draw(
    app: *InnerBreeze,
    x: s32,
    width: s32,
    y: *s32
): void {
    let key = LumiTelegramStatusKey();
    let height = settings_telegram_text_height(key, width);
    <Text
        session={app.ui.session}
        props={{
            text: LocaleText(key),
            size: AppFontSize(),
            bounds: {
                x: float32(x),
                y: float32((*y)),
                width: float32(width),
                height: float32(height)
            },
            wrap: Wrap.TextWrapAuto
        }}
    />;
    (*y) = (*y) + height;
    let has_account =
        storage_has_sync_account() !== 0n &&
        storage_get_setting_text("sync_private_key").count > 0n;
    let linked = State_lumi_telegram.lumi_telegram_connection.linked && has_account;
    let label = "lumi_telegram_connect";
    if (!has_account) {
        label = "sync_connect_account_button";
    } else if (linked) {
        label = "lumi_telegram_open";
    }
    if (
        (
            <Button
                session={app.ui.session}
                props={{
                    id: 7650n,
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(width),
                        height: float32(AppScale(48n))
                    },
                    label: LocaleText(label),
                    loading: LumiTelegramBusy(),
                    disabled:
                        LumiTelegramBusy() || (has_account && !linked && !LumiNodeTrafficAllowed())
                }}
            />
        )
    ) {
        if (!has_account) {
            app_apply_nav_route(app, s32(s32(AppNavRoute.APP_NAV_ROUTE_ACCOUNT)));
        } else if (linked) {
            if (!LumiTelegramOpen()) {
                State_lumi_telegram.lumi_telegram_connection.error = true;
            }
        } else {
            LumiTelegramLink();
        }
    }
    (*y) = (*y) + AppScale(56n);
    if (!linked || !State_lumi_authorization.lumi_authorization_ready) {
        State_settings_telegram.settings_telegram_stars_review[0n] = 0n;
    }
    if (linked && settings_telegram_authorization_active()) {
        let status_height = settings_telegram_text_height(LumiAuthorizationStatusKey(), width);
        <Text
            session={app.ui.session}
            props={{
                text: LocaleText(LumiAuthorizationStatusKey()),
                size: AppFontSize(),
                bounds: {
                    x: float32(x),
                    y: float32((*y)),
                    width: float32(width),
                    height: float32(status_height)
                },
                wrap: Wrap.TextWrapAuto
            }}
        />;
        (*y) = (*y) + status_height;
        let review_visible = false;
        let held_review = "";
        let review = settings_telegram_review_text(width);
        if (review.count > 0n) {
            let prepared = NativeText.PrepareText(
                {
                    text: review,
                    size: AppFontSize(),
                    bounds: { x: 0.0, y: 0.0, width: float32(width), height: 0.0 },
                    wrap: Wrap.TextWrapAuto
                },
                NativeText.DefaultTextFace()
            );
            let review_height = s32(prepared.bounds.height) + AppScale(16n);
            held_review = FrameTextHold(&app.ui.frame_text, review);
            review_visible = held_review.count === review.count && held_review.count > 0n;
            <Text
                session={app.ui.session}
                props={{
                    text: held_review,
                    size: AppFontSize(),
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(width),
                        height: float32(review_height)
                    },
                    wrap: Wrap.TextWrapAuto
                }}
            />;
            (*y) = (*y) + review_height;
            PackageFree(review);
        }
        if (State_lumi_authorization.lumi_authorization_ready) {
            if (
                (
                    <Button
                        session={app.ui.session}
                        props={{
                            id: 7652n,
                            bounds: {
                                x: float32(x),
                                y: float32((*y)),
                                width: float32(width),
                                height: float32(AppScale(48n))
                            },
                            label: LocaleText("lumi_authorization_approve"),
                            disabled: LumiAuthorizationBusy() || !review_visible,
                            loading: LumiAuthorizationBusy()
                        }}
                    />
                )
            ) {
                LumiAuthorizationApprove();
            }
            (*y) = (*y) + AppScale(56n);
            let disclosure = "lumi_authorization_stars_disclosure";
            let stars_height = settings_telegram_text_height(disclosure, width);
            <Text
                session={app.ui.session}
                props={{
                    text: LocaleText(disclosure),
                    size: AppFontSize(),
                    bounds: {
                        x: float32(x),
                        y: float32((*y)),
                        width: float32(width),
                        height: float32(stars_height)
                    },
                    wrap: Wrap.TextWrapAuto
                }}
            />;
            (*y) = (*y) + stars_height;
            let stars_label = LocaleText("lumi_authorization_approve_stars");
            let stars_review = review_visible ? held_review : "";
            let stars_ready = settings_telegram_stars_ready(
                stars_review,
                LocaleText(disclosure),
                stars_label
            );
            if (
                (
                    <Button
                        session={app.ui.session}
                        props={{
                            id: 7656n,
                            key: State_settings_telegram.settings_telegram_stars_key,
                            bounds: {
                                x: float32(x),
                                y: float32((*y)),
                                width: float32(width),
                                height: float32(AppScale(48n))
                            },
                            label: stars_label,
                            disabled: !stars_ready
                        }}
                    />
                ) &&
                stars_ready
            ) {
                State_settings_telegram.settings_telegram_stars_review[0n] = 0n;
                LumiAuthorizationApprove(true);
            }
            (*y) = (*y) + AppScale(56n);
        }
        if (State_lumi_authorization.lumi_authorization_pending.request_id[0n] !== u8(0n)) {
            if (
                (
                    <Button
                        session={app.ui.session}
                        props={{
                            id: 7654n,
                            bounds: {
                                x: float32(x),
                                y: float32((*y)),
                                width: float32(width),
                                height: float32(AppScale(48n))
                            },
                            label: LocaleText("cancel_button"),
                            disabled: LumiAuthorizationBusy(),
                            emphasis: ButtonEmphasis.ButtonEmphasisGhost
                        }}
                    />
                )
            ) {
                LumiAuthorizationCancel();
            }
            (*y) = (*y) + AppScale(56n);
        }
    }
    if (linked) {
        if (
            (
                <Button
                    session={app.ui.session}
                    props={{
                        id: 7657n,
                        bounds: {
                            x: float32(x),
                            y: float32((*y)),
                            width: float32(width),
                            height: float32(AppScale(48n))
                        },
                        label: LocaleText("lumi_authorization_request"),
                        disabled: !LumiNodeTrafficAllowed() || !LumiAuthorizationCanRequest()
                    }}
                />
            ) &&
            LumiNodeTrafficAllowed()
        ) {
            LumiAuthorizationRequest();
        }
        (*y) = (*y) + AppScale(56n);
        if (
            (
                <Button
                    session={app.ui.session}
                    props={{
                        id: 7651n,
                        bounds: {
                            x: float32(x),
                            y: float32((*y)),
                            width: float32(width),
                            height: float32(AppScale(48n))
                        },
                        label: LocaleText("lumi_telegram_disconnect"),
                        disabled: LumiTelegramBusy(),
                        emphasis: ButtonEmphasis.ButtonEmphasisGhost
                    }}
                />
            )
        ) {
            LumiTelegramDisconnect();
        }
        (*y) = (*y) + AppScale(56n);
    }
}
