import { ResolvedModal } from "kryon/tsx/modal";
// Authored UI composition; native application state remains in settings_sync_account_impl.zi.
import * as AccountState from "settings_sync_account_impl";
import * as NativeFieldset from "kryon/fieldset";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeText from "kryon/text";
import * as NativeTextField from "kryon/text_field";
import * as DeviceLinkState from "device_link_session";
import { app_open_modal } from "app_modal_state";
import { app_sync_loading, app_sync_status_key } from "app_sync";
import { InnerBreeze } from "app_types";
import {
    DeviceLinkAccept,
    DeviceLinkCancel,
    DeviceLinkCodeShown,
    DeviceLinkShow,
    DeviceLinkStage
} from "device_link_session";
import { AndroidPlatform } from "environment";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Fieldset } from "kryon/tsx/fieldset";
import { Text } from "kryon/tsx/text";
import { ControlledTextField } from "kryon/tsx/text_field";
import { LocaleText } from "locale";
import { AppScale } from "metrics";
import { ModalType } from "modal_rules";
import { NativePresent } from "native_flags";
import { PackageFree, PackageText } from "package_files";
import { DrawQrCode } from "qr_code_view";
import {
    NewAccountId,
    NewDisplayedId,
    NewTyped,
    PublicIdDisplayGroups,
    SettingsDeviceLinkCodeSide,
    SettingsDeviceLinkDigits,
    SettingsDeviceLinkOpenScanner,
    SettingsDeviceLinkUpdate,
    SettingsSyncButtonProps,
    SettingsSyncLoadAccountId,
    SettingsSyncRect,
    SettingsSyncTextProps
} from "settings_sync_account_impl";
import { settings_screen_draw_status_reserved } from "settings_status_view";
import { storage_get_setting_text } from "storage_settings";
import { SyncNodeCount, SyncNodePrefer, SyncNodeRemove } from "sync_nodes";
import {
    SettingsSyncAliasBusy,
    SettingsSyncAliasValid,
    SettingsSyncCopyId,
    SettingsSyncCreate,
    SettingsSyncDisplayId,
    SettingsSyncEnsureNode,
    SettingsSyncLogout,
    SettingsSyncNodeAddress,
    SettingsSyncNodeHintHeight,
    SettingsSyncNormalizeAlias,
    SettingsSyncNow,
    SettingsSyncOpenAlias,
    SettingsSyncPreferredNode,
    SettingsSyncServerSave,
    SettingsSyncStatusHeight,
    SettingsSyncSubmitAlias,
    SettingsSyncTakeAliasResult
} from "settings_sync_account_impl";
import {
    AppReplaceText,
    AppTextFromCString,
    FrameTextHold,
    FrameTextSave,
    FrameTextRead
} from "text_buffers";
import { SampleTextFieldInput, TextInputWriteClipboard } from "text_input_host";

function SettingsSyncField(
    app: NativeRef<InnerBreeze>,
    value: u8[],
    cursor: NativeRef<s32>,
    focused: NativeRef<s32>,
    anchor: NativeRef<s32>,
    scroll_x: NativeRef<s32>,
    x: s32,
    y: s32,
    width: s32,
    id: s32,
    max_codepoints: s32
): boolean {
    let typed = NewTyped();
    let field: NativeTextField.Props = {};
    field.key = u64(id);
    field.bounds = SettingsSyncRect(x, y, width, AppScale(38n));
    field.value = FrameTextHold(
        nativeRef(app.ui.frame_text),
        AppTextFromCString(nativeRef(nativeAt(value, 0n)), s32(value.count))
    );
    field.cursor = nativeDeref(cursor);
    field.anchor = nativeDeref(anchor);
    field.scroll_x = nativeDeref(scroll_x);
    field.focused = nativeDeref(focused) !== 0n;
    field.focus_id = id;
    field.max_bytes = s32(value.count) - 1n;
    field.max_codepoints = max_codepoints;
    field.input = SampleTextFieldInput(field.focused, nativeSlice(typed));
    let result = ControlledTextField({ session: app.ui.session, props: field });
    if (result.edit.changed) {
        AppReplaceText(value, result.edit.start, result.edit.end, result.edit.replacement);
    }
    nativeDeref(cursor) = result.cursor;
    nativeDeref(anchor) = result.anchor;
    nativeDeref(scroll_x) = result.scroll_x;
    nativeDeref(focused) = result.focused ? 1n : 0n;
    if (result.clipboard_write) {
        TextInputWriteClipboard(result.clipboard_text);
    }
    return result.committed;
}

function SettingsDeviceLinkText(
    app: NativeRef<InnerBreeze>,
    value: string,
    x: s32,
    y: NativeRef<s32>,
    width: s32,
    height: s32
): void {
    let props: NativeText.Props = SettingsSyncTextProps(
        value,
        x,
        nativeDeref(y),
        width,
        height,
        true
    );
    props.wrap = Wrap.TextWrapAuto;
    <Text session={app.ui.session} props={props} />;
    nativeDeref(y) = nativeDeref(y) + height;
}

function SettingsDeviceLinkDraw(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    has_account: boolean
): void {
    SettingsDeviceLinkUpdate(app);
    let button_h = AppScale(48n);
    let half = (width - AppScale(10n)) / 2n;
    <Text
        session={app.ui.session}
        props={SettingsSyncTextProps(
            LocaleText("device_link_title"),
            x,
            nativeDeref(y),
            width,
            AppScale(28n),
            false
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(30n);
    let stage = DeviceLinkState.device_link.stage;
    if (stage === DeviceLinkStage.DeviceLinkShowing) {
        let hint = DeviceLinkState.device_link.sends
            ? "device_link_show_hint_send"
            : "device_link_show_hint_receive";
        SettingsDeviceLinkText(app, LocaleText(hint), x, y, width, AppScale(56n));
        let side = SettingsDeviceLinkCodeSide(width);
        DrawQrCode(app.ui.session, DeviceLinkCodeShown(), {
            x: float32(x),
            y: float32(nativeDeref(y)),
            width: float32(width),
            height: float32(side)
        });
        nativeDeref(y) = nativeDeref(y) + (side + AppScale(10n));
        if (
            Button({
                session: app.ui.session,
                props: SettingsSyncButtonProps(
                    LocaleText("cancel_button"),
                    x,
                    nativeDeref(y),
                    width,
                    button_h,
                    5280n,
                    false
                )
            })
        ) {
            DeviceLinkCancel();
        }
        nativeDeref(y) = nativeDeref(y) + button_h;
        return;
    }
    if (
        stage === DeviceLinkStage.DeviceLinkConfirm ||
        stage === DeviceLinkStage.DeviceLinkWaiting
    ) {
        let hint =
            stage === DeviceLinkStage.DeviceLinkConfirm
                ? "device_link_compare"
                : "device_link_waiting_compare";
        SettingsDeviceLinkText(app, LocaleText(hint), x, y, width, AppScale(52n));
        let digits = SettingsDeviceLinkDigits(app, DeviceLinkState.device_link.confirmation);
        let number: NativeText.Props = SettingsSyncTextProps(
            digits,
            x,
            nativeDeref(y),
            width,
            AppScale(56n),
            false
        );
        number.size = AppScale(40n);
        <Text session={app.ui.session} props={number} />;
        nativeDeref(y) = nativeDeref(y) + AppScale(60n);
        if (stage === DeviceLinkStage.DeviceLinkConfirm) {
            if (
                Button({
                    session: app.ui.session,
                    props: SettingsSyncButtonProps(
                        LocaleText("device_link_connect"),
                        x,
                        nativeDeref(y),
                        half,
                        button_h,
                        5281n,
                        true
                    )
                })
            ) {
                DeviceLinkAccept();
            }
            if (
                Button({
                    session: app.ui.session,
                    props: SettingsSyncButtonProps(
                        LocaleText("cancel_button"),
                        x + half + AppScale(10n),
                        nativeDeref(y),
                        half,
                        button_h,
                        5282n,
                        false
                    )
                })
            ) {
                DeviceLinkCancel();
            }
        } else {
            if (
                Button({
                    session: app.ui.session,
                    props: SettingsSyncButtonProps(
                        LocaleText("cancel_button"),
                        x,
                        nativeDeref(y),
                        width,
                        button_h,
                        5282n,
                        false
                    )
                })
            ) {
                DeviceLinkCancel();
            }
        }
        nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(10n));
        return;
    }
    if (stage === DeviceLinkStage.DeviceLinkAsk) {
        SettingsDeviceLinkText(app, LocaleText("device_link_ask"), x, y, width, AppScale(52n));
        if (
            Button({
                session: app.ui.session,
                props: SettingsSyncButtonProps(
                    LocaleText("device_link_connect"),
                    x,
                    nativeDeref(y),
                    half,
                    button_h,
                    5283n,
                    true
                )
            })
        ) {
            DeviceLinkAccept();
        }
        if (
            Button({
                session: app.ui.session,
                props: SettingsSyncButtonProps(
                    LocaleText("cancel_button"),
                    x + half + AppScale(10n),
                    nativeDeref(y),
                    half,
                    button_h,
                    5284n,
                    false
                )
            })
        ) {
            DeviceLinkCancel();
        }
        nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(10n));
        return;
    }
    if (
        stage === DeviceLinkStage.DeviceLinkWorking ||
        stage === DeviceLinkStage.DeviceLinkReceived ||
        stage === DeviceLinkStage.DeviceLinkConnected ||
        stage === DeviceLinkStage.DeviceLinkFailed
    ) {
        let message = "device_link_working";
        if (stage === DeviceLinkStage.DeviceLinkConnected) {
            message = "device_link_connected";
        }
        if (stage === DeviceLinkStage.DeviceLinkFailed) {
            message = DeviceLinkState.device_link.error;
        }
        SettingsDeviceLinkText(app, LocaleText(message), x, y, width, AppScale(52n));
        if (
            stage === DeviceLinkStage.DeviceLinkWorking ||
            stage === DeviceLinkStage.DeviceLinkReceived
        ) {
            nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(10n));
            return;
        }
        if (
            Button({
                session: app.ui.session,
                props: SettingsSyncButtonProps(
                    LocaleText("done_button"),
                    x,
                    nativeDeref(y),
                    width,
                    button_h,
                    5285n,
                    false
                )
            })
        ) {
            DeviceLinkCancel();
        }
        nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(10n));
        return;
    }
    let hint = has_account ? "device_link_intro_send" : "device_link_intro_receive";
    SettingsDeviceLinkText(app, LocaleText(hint), x, y, width, AppScale(52n));
    let scan_supported = AndroidPlatform() !== 0n;
    let show_width = scan_supported ? half : width;
    if (
        Button({
            session: app.ui.session,
            props: SettingsSyncButtonProps(
                LocaleText("device_link_show"),
                x,
                nativeDeref(y),
                show_width,
                button_h,
                5286n,
                !scan_supported
            )
        })
    ) {
        DeviceLinkShow();
    }
    if (scan_supported) {
        if (
            Button({
                session: app.ui.session,
                props: SettingsSyncButtonProps(
                    LocaleText("device_link_scan"),
                    x + half + AppScale(10n),
                    nativeDeref(y),
                    half,
                    button_h,
                    5287n,
                    true
                )
            })
        ) {
            SettingsDeviceLinkOpenScanner();
        }
    }
    nativeDeref(y) = nativeDeref(y) + (button_h + AppScale(10n));
}

function SettingsSyncModalProps(
    app: NativeRef<InnerBreeze>,
    key: string,
    title: string,
    height: s32
): NativeModal.Props {
    let width = app.ui.view_width - AppScale(32n);
    if (width > AppScale(400n)) {
        width = AppScale(400n);
    }
    return {
        key: NativeLayout.KeyHash(key),
        title: title,
        width: width,
        height: height
    };
}

export function SettingsSyncPublicIdModal(
    app: NativeRef<InnerBreeze>,
    public_id: string = ""
): s32 {
    if (!NativePresent(app)) {
        return 1n;
    }
    let loadedId = NewAccountId();
    let account_id = public_id;
    if (account_id.count === 0n) {
        if (!SettingsSyncLoadAccountId(nativeSlice(loadedId))) {
            return 1n;
        }
        account_id = AppTextFromCString(nativeRef(nativeAt(loadedId, 0n)), s32(loadedId.count));
    }
    let result: s32 = s32(0n);
    const result_ref = nativeRef(result);
    let frame = ResolvedModal({
        session: app.ui.session,
        props: SettingsSyncModalProps(
            app,
            "inbe/account/public-id",
            LocaleText("sync_public_id_full_title"),
            AppScale(300n)
        ),
        children: (frame: NativeModal.ModalFrameResult): void => {
            let content = frame.layout.content;
            let x = s32(content.x);
            let y = s32(content.y);
            let width = s32(content.width);
            <Text
                session={app.ui.session}
                props={SettingsSyncTextProps(
                    LocaleText("sync_public_id_full_message"),
                    x,
                    y,
                    width,
                    AppScale(30n),
                    false
                )}
            />;
            y = y + AppScale(38n);
            let displayed_id = NewDisplayedId();
            let id = PublicIdDisplayGroups(account_id, nativeSlice(displayed_id));
            let field: NativeFieldset.Props = {};
            field.bounds = SettingsSyncRect(x, y, width, AppScale(70n));
            <Fieldset session={app.ui.session} props={field} />;
            let id_props: NativeText.Props = SettingsSyncTextProps(
                id,
                x + AppScale(10n),
                y + AppScale(15n),
                width - AppScale(20n),
                AppScale(40n),
                true
            );
            id_props.align = TextAlign.TextAlignCenter;
            id_props.wrap = Wrap.TextWrapAuto;
            <Text session={app.ui.session} props={id_props} />;
            y = y + AppScale(86n);
            if (
                Button({
                    session: app.ui.session,
                    props: SettingsSyncButtonProps(
                        LocaleText("sync_copy_id_button"),
                        x,
                        y,
                        width,
                        AppScale(38n),
                        5250n,
                        false
                    )
                })
            ) {
                SettingsSyncCopyId(account_id);
            }
            y = y + AppScale(47n);
            if (
                Button({
                    session: app.ui.session,
                    props: SettingsSyncButtonProps(
                        LocaleText("close_button"),
                        x,
                        y,
                        width,
                        AppScale(38n),
                        5251n,
                        false
                    )
                })
            ) {
                nativeDeref(result_ref) = 1n;
            }
        }
    });
    if (frame.dismissed) {
        return 1n;
    }
    return result;
}

export function SettingsSyncAccountConfig(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app) || !NativePresent(y)) {
        return;
    }
    const session = app.ui.session;
    const buttonHeight = AppScale(38n);
    const gap = AppScale(10n);
    let accountId = NewAccountId();
    let hasAccount = SettingsSyncLoadAccountId(nativeSlice(accountId));
    if (!hasAccount) {
        if (
            Button({
                session: session,
                props: SettingsSyncButtonProps(
                    LocaleText("sync_create_account_button"),
                    x,
                    nativeDeref(y),
                    width,
                    buttonHeight,
                    5201n,
                    true
                )
            })
        ) {
            if (SettingsSyncCreate(app) !== 0n) {
                hasAccount = SettingsSyncLoadAccountId(nativeSlice(accountId));
            }
        }
        nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
        if (!hasAccount) {
            nativeDeref(y) = nativeDeref(y) + AppScale(8n);
            SettingsDeviceLinkDraw(app, x, width, y, false);
            hasAccount = SettingsSyncLoadAccountId(nativeSlice(accountId));
        }
        if (!hasAccount) {
            settings_screen_draw_status_reserved(x, y, AppScale(42n));
            return;
        }
    }
    SettingsSyncEnsureNode();
    <Text
        session={session}
        props={SettingsSyncTextProps(
            LocaleText("sync_account_title"),
            x,
            nativeDeref(y),
            width,
            AppScale(28n),
            false
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(30n);
    {
        const displayId = SettingsSyncDisplayId(
            app,
            AppTextFromCString(nativeRef(nativeAt(accountId, 0n)), s32(accountId.count))
        );
        <Text
            session={session}
            props={SettingsSyncTextProps(displayId, x, nativeDeref(y), width, AppScale(32n), false)}
        />;
        nativeDeref(y) = nativeDeref(y) + AppScale(36n);
    }
    const statusHeight = SettingsSyncStatusHeight(width);
    {
        let status = SettingsSyncTextProps(
            LocaleText(app_sync_status_key()),
            x,
            nativeDeref(y),
            width,
            statusHeight,
            true
        );
        status.wrap = Wrap.TextWrapAuto;
        <Text session={session} props={status} />;
    }
    nativeDeref(y) = nativeDeref(y) + statusHeight + AppScale(8n);
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_now_button"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5204n,
                true
            )
        })
    ) {
        SettingsSyncNow(app);
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap + AppScale(8n);
    SettingsDeviceLinkDraw(app, x, width, y, true);
    nativeDeref(y) = nativeDeref(y) + AppScale(8n);
    <Text
        session={session}
        props={SettingsSyncTextProps(
            LocaleText("sync_nodes_title"),
            x,
            nativeDeref(y),
            width,
            AppScale(28n),
            false
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(30n);
    const hintHeight = SettingsSyncNodeHintHeight(width);
    {
        let hint = SettingsSyncTextProps(
            LocaleText("sync_nodes_hint"),
            x,
            nativeDeref(y),
            width,
            hintHeight,
            true
        );
        hint.wrap = Wrap.TextWrapAuto;
        <Text session={session} props={hint} />;
    }
    nativeDeref(y) = nativeDeref(y) + hintHeight + AppScale(8n);
    const preferred = SettingsSyncPreferredNode();
    const busy = app_sync_loading() !== 0n;
    const count = SyncNodeCount();
    for (let index: s32 = s32(0n); index < count; index += 1n) {
        const address = SettingsSyncNodeAddress(index);
        const selected = address === preferred;
        let node = SettingsSyncButtonProps(
            address,
            x,
            nativeDeref(y),
            width - AppScale(48n),
            AppScale(52n),
            5250n + index,
            selected
        );
        node.disabled = busy;
        node.fit_content = true;
        if (selected) {
            node.icon_shape = "S1.6rr:M12 3L15 9L22 10L17 15L18 22L12 18L6 22L7 15L2 10L9 9Z";
        }
        if (Button({ session: session, props: node }) && SyncNodePrefer(address)) {
            SettingsSyncNow(app);
        }
        let removeClicked = false;
        {
            let remove = SettingsSyncButtonProps(
                LocaleText("launcher_uninstall"),
                x + width - AppScale(44n),
                nativeDeref(y),
                AppScale(44n),
                AppScale(52n),
                5260n + index,
                false
            );
            remove.icon_only = true;
            remove.icon_shape = "S1.6rr:M3 6H21M9 6V3H15V6M5 6L6 21H18L19 6M10 10V17M14 10V17";
            remove.disabled = busy || SyncNodeCount() <= 1n;
            removeClicked = Button({ session: session, props: remove });
        }
        PackageFree(address);
        if (removeClicked) {
            SyncNodeRemove(index);
            break;
        }
        nativeDeref(y) = nativeDeref(y) + AppScale(60n);
    }
    PackageFree(preferred);
    <Text
        session={session}
        props={SettingsSyncTextProps(
            LocaleText("sync_remote_label"),
            x,
            nativeDeref(y),
            width,
            AppScale(24n),
            true
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(25n);
    if (
        SettingsSyncField(
            app,
            nativeSlice(app.sync_server_url),
            nativeRef(app.sync_server_url_cursor),
            nativeRef(app.sync_server_url_focused),
            nativeRef(AccountState.server_anchor),
            nativeRef(AccountState.server_scroll_x),
            x,
            nativeDeref(y),
            width - AppScale(84n),
            5207n,
            255n
        ) &&
        !busy
    ) {
        SettingsSyncServerSave(app);
    }
    let add_clicked = false;
    {
        let add = SettingsSyncButtonProps(
            LocaleText("sync_nodes_add"),
            x + width - AppScale(78n),
            nativeDeref(y),
            AppScale(78n),
            buttonHeight,
            5208n,
            false
        );
        add.disabled = busy;
        add_clicked = Button({ session: session, props: add });
    }
    if (add_clicked) {
        SettingsSyncServerSave(app);
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + AppScale(20n);
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_account_options"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5240n,
                false
            )
        })
    ) {
        AccountState.sync_account_details = !AccountState.sync_account_details;
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
    if (!AccountState.sync_account_details) {
        settings_screen_draw_status_reserved(x, y, AppScale(42n));
        return;
    }
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_copy_id_button"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5205n,
                false
            )
        })
    ) {
        SettingsSyncCopyId(
            AppTextFromCString(nativeRef(nativeAt(accountId, 0n)), s32(accountId.count))
        );
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_alias_button"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5206n,
                false
            )
        })
    ) {
        SettingsSyncOpenAlias(app);
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_logout_button"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5209n,
                false
            )
        })
    ) {
        SettingsSyncLogout();
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
    if (
        Button({
            session: session,
            props: SettingsSyncButtonProps(
                LocaleText("sync_clear_remote_data_button"),
                x,
                nativeDeref(y),
                width,
                buttonHeight,
                5210n,
                false
            )
        })
    ) {
        app_open_modal(app, ModalType.ModalConfirmDeleteSyncAccount);
    }
    nativeDeref(y) = nativeDeref(y) + buttonHeight + gap;
    settings_screen_draw_status_reserved(x, y, AppScale(42n));
}

export function SettingsSyncAliasModal(app: NativeRef<InnerBreeze>): s32 {
    if (!NativePresent(app)) {
        return 3n;
    }
    const pending = SettingsSyncTakeAliasResult(app);
    if (pending !== 0n) {
        return pending;
    }
    const stored = PackageText(storage_get_setting_text(AccountState.sync_account_alias_key), "");
    const hasAlias = stored.count !== 0n;
    const title_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText(hasAlias ? "sync_alias_change_title" : "sync_alias_title")
    );
    const message_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText(hasAlias ? "sync_alias_change_message" : "sync_alias_message")
    );
    let result: s32 = s32(0n);
    const result_ref = nativeRef(result);
    const frame = ResolvedModal({
        session: app.ui.session,
        props: SettingsSyncModalProps(
            app,
            "inbe/account/alias",
            FrameTextRead(nativeRef(app.ui.frame_text), title_range),
            AppScale(280n)
        ),
        children: (frame: NativeModal.ModalFrameResult): void => {
            const session = app.ui.session;
            const content = frame.layout.content;
            const x = s32(content.x);
            const width = s32(content.width);
            let y = s32(content.y);
            <Text
                session={session}
                props={SettingsSyncTextProps(
                    FrameTextRead(nativeRef(app.ui.frame_text), message_range),
                    x,
                    y,
                    width,
                    AppScale(48n),
                    false
                )}
            />;
            y += AppScale(54n);
            const committed = SettingsSyncField(
                app,
                nativeSlice(app.sync_alias_input),
                nativeRef(app.sync_alias_cursor),
                nativeRef(app.sync_alias_focused),
                nativeRef(AccountState.alias_anchor),
                nativeRef(AccountState.alias_scroll_x),
                x,
                y,
                width,
                5240n,
                32n
            );
            SettingsSyncNormalizeAlias(app);
            y += AppScale(45n);
            <Text
                session={session}
                props={SettingsSyncTextProps(
                    LocaleText("sync_alias_rule"),
                    x,
                    y,
                    width,
                    AppScale(36n),
                    true
                )}
            />;
            y += AppScale(46n);
            if (
                Button({
                    session: session,
                    props: SettingsSyncButtonProps(
                        LocaleText("close_button"),
                        x,
                        y,
                        width,
                        AppScale(38n),
                        5241n,
                        false
                    )
                })
            ) {
                nativeDeref(result_ref) = 3n;
            }
            y += AppScale(47n);
            const saveLabel = LocaleText(
                hasAlias ? "sync_alias_save_button" : "sync_alias_register_button"
            );
            let save = SettingsSyncButtonProps(saveLabel, x, y, width, AppScale(38n), 5242n, true);
            save.disabled = SettingsSyncAliasBusy();
            const alias = AppTextFromCString(nativeRef(nativeAt(app.sync_alias_input, 0n)), 40n);
            if (
                (Button({ session: session, props: save }) || (committed && !save.disabled)) &&
                SettingsSyncAliasValid(alias) &&
                alias !== stored
            ) {
                const saved = SettingsSyncSubmitAlias(app, alias);
                if (saved !== 0n) {
                    nativeDeref(result_ref) = saved;
                }
            }
        }
    });
    PackageFree(stored);
    if (frame.dismissed) {
        return 3n;
    }
    return result;
}
