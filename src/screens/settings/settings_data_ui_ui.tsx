import { ResolvedModal } from "kryon/tsx/modal";
import { Scroll } from "kryon/tsx/scroll";
import { SettingsDataUiNewActions } from "settings_data_ui";
import { SettingsDataUiNewQueued } from "settings_data_ui";
import { ActionModal } from "kryon/tsx/action_modal";
import { app_reload_after_import } from "application_init";
import { app_open_modal } from "app_modal_state";
import { SettingsReviewClearCachedText, SettingsReviewNoApp } from "settings_data_ui";
import { AccountKeys } from "mesh_client/keys";
// Authored UI composition; native application state remains in settings_data_ui.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import * as State_settings_data_ui from "settings_data_ui";
import { app_close_modal } from "app_modal_state";
import {
    app_request_sync,
    app_sync_resume_after_restore,
    app_sync_status_key,
    app_sync_stop_for_restore
} from "app_sync";
import { InnerBreeze } from "app_types";
import { CssClass } from "css/Css";
import { CurrentApp } from "current_app";
import { data_has_any } from "data";
import { storage_database_damaged, storage_restore_last_good } from "database_backup";
import { storage_data_revision } from "db";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { NextTextLine } from "kryon/text_layout";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppParagraphHeight, AppScale, AppTextLineHeight } from "metrics";
import { ModalType } from "modal_rules";
import { NativeContext, NativePresent } from "native_flags";

import {
    SettingsDataButtonProps,
    SettingsDataExport,
    SettingsDataExportCsv,
    SettingsDataImport,
    SettingsDataRect,
    SettingsDataTextProps,
    SettingsReviewRemovals,
    SettingsReviewReset,
    free
} from "settings_data_ui";
import {
    settings_screen_set_status_error,
    settings_screen_set_status_success
} from "settings_status";
import { settings_screen_draw_status_reserved } from "settings_status_view";
import { sync_account_load } from "sync_account";
import {
    storage_sync_review_clear_if_no_visible_diff,
    storage_sync_review_plan
} from "sync_review";
import { StorageSyncStatus, storage_sync_status } from "sync_state";
import {
    AppTextFromCString,
    FormatNumberTemplate,
    FrameTextHold,
    FrameTextRange,
    FrameTextSave,
    FrameTextRead
} from "text_buffers";

export function settings_data_draw_actionsView(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app) || !NativePresent(y)) {
        return;
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(8n);
    if (storage_database_damaged() !== 0n) {
        let props = SettingsDataTextProps(
            LocaleText("database_damaged_message"),
            x,
            nativeDeref(y),
            width,
            AppScale(70n)
        );
        props.wrap = Wrap.TextWrapAuto;
        <Text session={app.ui.session} props={props} />;
        nativeDeref(y) = nativeDeref(y) + AppScale(78n);
    }
    {
        let restore_button = SettingsDataButtonProps(
            LocaleText("restore_last_good_button"),
            x,
            nativeDeref(y),
            width,
            5305n,
            false
        );
        restore_button.disabled = State_settings_data_ui.restore_last_good_requested;
        if (Button({ session: app.ui.session, props: restore_button })) {
            State_settings_data_ui.restore_last_good_requested = true;
        }
    }
    if (State_settings_data_ui.restore_last_good_requested && app_sync_stop_for_restore(app)) {
        State_settings_data_ui.restore_last_good_requested = false;
        let restored = storage_restore_last_good() !== 0n;
        app_sync_resume_after_restore();
        if (restored) {
            app_reload_after_import(app, 1n);
            app_request_sync(app);
            settings_screen_set_status_success(LocaleText("restore_last_good_success"), "");
        } else {
            settings_screen_set_status_error(LocaleText("restore_last_good_failed"));
        }
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(50n);
    if (
        Button({
            session: app.ui.session,
            props: SettingsDataButtonProps(
                LocaleText("import_data_button"),
                x,
                nativeDeref(y),
                width,
                5301n,
                true
            )
        })
    ) {
        SettingsDataImport(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(50n);
    if (
        Button({
            session: app.ui.session,
            props: SettingsDataButtonProps(
                LocaleText("export_data_button"),
                x,
                nativeDeref(y),
                width,
                5302n,
                true
            )
        })
    ) {
        SettingsDataExport(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(50n);
    if (
        Button({
            session: app.ui.session,
            props: SettingsDataButtonProps(
                LocaleText("export_csv_button"),
                x,
                nativeDeref(y),
                width,
                5303n,
                false
            )
        })
    ) {
        SettingsDataExportCsv(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(50n);
    let account: AccountKeys = {};
    if (sync_account_load(nativeRef(account)) === 0n) {
        if (
            Button({
                session: app.ui.session,
                props: SettingsDataButtonProps(
                    LocaleText("clear_local_data_button"),
                    x,
                    nativeDeref(y),
                    width,
                    5304n,
                    false
                )
            })
        ) {
            if (data_has_any() !== 0n) {
                app_open_modal(app, ModalType.ModalConfirmDeleteData);
            } else {
                settings_screen_set_status_error(LocaleText("no_data_to_delete"));
            }
        }
        nativeDeref(y) = nativeDeref(y) + AppScale(50n);
    }
    settings_screen_draw_status_reserved(x, y, AppScale(42n));
}

export function settings_data_draw_sync_statusView(x: s32, width: s32, y: NativeRef<s32>): void {
    let app = CurrentApp();
    if (!NativePresent(app) || !NativePresent(y)) {
        return;
    }
    let status: StorageSyncStatus = {};
    if (storage_sync_status(nativeRef(status)) === 0n || status.has_account === 0n) {
        return;
    }
    <Text
        session={app.ui.session}
        props={SettingsDataTextProps(
            LocaleText("sync_status_title"),
            x,
            nativeDeref(y),
            width,
            AppScale(26n)
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(28n);
    let queued = SettingsDataUiNewQueued();
    FormatNumberTemplate(
        LocaleText("sync_status_queued"),
        s32(status.queued_changes),
        nativeSlice(queued)
    );
    <Text
        session={app.ui.session}
        props={SettingsDataTextProps(
            FrameTextHold(
                nativeRef(app.ui.frame_text),
                AppTextFromCString(nativeRef(nativeAt(queued, 0n)), 64n)
            ),
            x,
            nativeDeref(y),
            width,
            AppScale(24n)
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(28n);
    <Text
        session={app.ui.session}
        props={SettingsDataTextProps(
            LocaleText(app_sync_status_key()),
            x,
            nativeDeref(y),
            width,
            AppScale(48n)
        )}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(52n);
}

export function SettingsDataPrompt(
    app: NativeRef<InnerBreeze>,
    key: string,
    title_key: string,
    message_key: string,
    label_keys: string[]
): s32 {
    let title_range = FrameTextSave(nativeRef(app.ui.frame_text), LocaleText(title_key));
    let message_range = FrameTextSave(nativeRef(app.ui.frame_text), LocaleText(message_key));
    let label_ranges: [FrameTextRange, FrameTextRange, FrameTextRange] = [{}, {}, {}];
    for (let i = s32(0n); i < s32(label_keys.count) && i < 3n; i += 1n) {
        nativeSet(
            label_ranges,
            i,
            FrameTextSave(nativeRef(app.ui.frame_text), LocaleText(nativeAt(label_keys, i)))
        );
    }
    let actions = SettingsDataUiNewActions();
    let index: s32 = s32(0n);
    while (index < s32(label_keys.count) && index < 3n) {
        nativeAt(actions, index).label = FrameTextRead(
            nativeRef(app.ui.frame_text),
            nativeAt(label_ranges, index)
        );
        nativeAt(actions, index).tone =
            index === 0n ? ButtonTone.ButtonToneNeutral : ButtonTone.ButtonToneAccent;
        nativeAt(actions, index).emphasis =
            index === 0n ? ButtonEmphasis.ButtonEmphasisSoft : ButtonEmphasis.ButtonEmphasisFilled;
        index = index + 1n;
    }
    let props: NativeModal.ActionModalProps = {};
    props.key = NativeLayout.KeyHash(key);
    props.title = FrameTextRead(nativeRef(app.ui.frame_text), title_range);
    props.message = FrameTextRead(nativeRef(app.ui.frame_text), message_range);
    props.max_width = AppScale(440n);
    let result = ActionModal({
        session: app.ui.session,
        props: props,
        actions: nativeSlice(actions, 0n, label_keys.count)
    });
    return result.action === -1n ? 1n : result.action;
}

export function SettingsReviewLines(
    app: NativeRef<InnerBreeze>,
    value: string,
    bounds: Rectangle,
    offset: s32,
    font: s32,
    line_height: s32,
    initial_class: string
): s32 {
    let start: s32 = s32(0n);
    let y = s32(bounds.y) - offset;
    let action_class = initial_class;
    while (start < s32(value.count)) {
        let end = start;
        while (end < s32(value.count) && nativeAt(value, end) !== u8(10)) {
            end = end + 1n;
        }
        let logical_line = nativeSlice(value, start, end);
        if (logical_line === LocaleText("review_added")) {
            action_class = "review-added";
        } else if (logical_line === LocaleText("review_removed")) {
            action_class = "review-removed";
        } else if (logical_line === LocaleText("review_changed")) {
            action_class = "review-changed";
        }
        let indent: s32 = s32(0n);
        while (indent < s32(logical_line.count) && nativeAt(logical_line, indent) === u8(32)) {
            indent = indent + 1n;
        }
        let class_name = action_class;
        if (indent >= 6n) {
            class_name = "review-detail";
        }
        let inset: s32 = s32(0n);
        if (indent >= 2n) {
            inset = AppScale(12n);
        }
        if (indent >= 6n) {
            inset = AppScale(24n);
        }
        let visible_line = nativeSlice(logical_line, indent);
        let wrapped_start: s32 = s32(0n);
        while (wrapped_start < s32(visible_line.count)) {
            let line = NextTextLine(
                visible_line,
                wrapped_start,
                bounds.width - float32(AppScale(12n) + inset),
                Wrap.TextWrapAuto,
                font,
                "ui"
            );
            if (
                NativePresent(app) &&
                y + line_height >= s32(bounds.y) &&
                y < s32(bounds.y + bounds.height)
            ) {
                let props = SettingsDataTextProps(
                    nativeSlice(visible_line, line.start, line.end),
                    s32(bounds.x) + inset,
                    y,
                    s32(bounds.width) - AppScale(12n) - inset,
                    line_height
                );
                props.size = font;
                props.wrap = Wrap.TextWrapNone;
                props.class_name = CssClass(class_name);
                <Text session={app.ui.session} props={props} />;
            }
            y = y + line_height;
            if (line.next <= wrapped_start) {
                break;
            }
            wrapped_start = line.next;
        }
        if (visible_line.count === 0n) {
            y = y + line_height;
        }
        start = end + 1n;
    }
    return y - s32(bounds.y) + offset;
}

export function SettingsDataReviewModal(app: NativeRef<InnerBreeze>): s32 {
    if (
        State_settings_data_ui.review_cached_revision !== storage_data_revision() &&
        storage_sync_review_clear_if_no_visible_diff() !== 0n
    ) {
        SettingsReviewReset();
        app_close_modal(app);
        app_reload_after_import(app, 0n);
        return 0n;
    }
    let width = app.ui.view_width - AppScale(32n);
    if (width > AppScale(680n)) {
        width = AppScale(680n);
    }
    let height = app.ui.view_height - AppScale(32n);
    if (height > AppScale(720n)) {
        height = AppScale(720n);
    }
    let decision: s32 = s32(0n);
    const decision_ref = nativeRef(decision);
    let review_title_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("sync_review_title")
    );
    let review_cancel_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("cancel_button")
    );
    let review_unavailable_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("review_unavailable")
    );
    let review_explanation_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("review_merge_detail")
    );
    let review_direction_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("review_merge")
    );
    let review_replacement_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        LocaleText("review_replace_detail")
    );
    let frame = ResolvedModal({
        session: app.ui.session,
        props: {
            key: NativeLayout.KeyHash("inbe/data/sync-review"),
            title: FrameTextRead(nativeRef(app.ui.frame_text), review_title_range),
            width: width,
            height: height,
            has_right_action: true,
            right_label: FrameTextRead(nativeRef(app.ui.frame_text), review_cancel_range)
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let content = frame.layout.content;
            let x = s32(content.x);
            let y = s32(content.y);
            let text_width = s32(content.width);
            let revision = storage_data_revision();
            if (State_settings_data_ui.review_cached_revision !== revision) {
                SettingsReviewClearCachedText();
                State_settings_data_ui.review_cached_available =
                    storage_sync_review_plan(
                        2n,
                        nativeRef(State_settings_data_ui.review_cached_text)
                    ) !== 0n;
                State_settings_data_ui.review_cached_replace_available =
                    storage_sync_review_plan(
                        1n,
                        nativeRef(State_settings_data_ui.review_cached_replace_text)
                    ) !== 0n;
                State_settings_data_ui.review_cached_revision = storage_data_revision();
            }
            let value = State_settings_data_ui.review_cached_available
                ? AppTextFromCString(State_settings_data_ui.review_cached_text, 2147483647n)
                : FrameTextRead(nativeRef(app.ui.frame_text), review_unavailable_range);
            let explanation = FrameTextRead(nativeRef(app.ui.frame_text), review_explanation_range);
            let font = AppScale(16n);
            let line_height = AppTextLineHeight(font);
            let direction = FrameTextRead(nativeRef(app.ui.frame_text), review_direction_range);
            let direction_height = AppParagraphHeight(direction, text_width, font, 0n);
            let direction_props: NativeText.Props = SettingsDataTextProps(
                direction,
                x,
                y,
                text_width,
                direction_height
            );
            direction_props.size = font;
            direction_props.wrap = Wrap.TextWrapAuto;
            direction_props.class_name = CssClass("review-heading");
            <Text session={app.ui.session} props={direction_props} />;
            y = y + (direction_height + AppScale(8n));
            let view = SettingsDataRect(
                x,
                y,
                text_width,
                s32(content.y + content.height) - y - AppScale(140n)
            );
            let explanation_height =
                SettingsReviewLines(
                    SettingsReviewNoApp(),
                    explanation,
                    view,
                    0n,
                    font,
                    line_height,
                    "review-detail"
                ) + line_height;
            let props: NativeScroll.Props = {};
            props.key = NativeLayout.KeyHash("inbe/data/sync-review/details");
            props.bounds = view;
            let merge_height = SettingsReviewLines(
                SettingsReviewNoApp(),
                value,
                view,
                0n,
                font,
                line_height,
                ""
            );
            let removals = SettingsReviewRemovals(
                AppTextFromCString(State_settings_data_ui.review_cached_replace_text, 2147483647n)
            );
            let replacement =
                removals.count > 0n
                    ? FrameTextRead(nativeRef(app.ui.frame_text), review_replacement_range)
                    : "";
            let replacement_height: s32 = s32(0n);
            if (removals.count > 0n) {
                replacement_height =
                    SettingsReviewLines(
                        SettingsReviewNoApp(),
                        replacement,
                        view,
                        0n,
                        font,
                        line_height,
                        "review-removed"
                    ) + line_height;
            }
            props.content_height =
                explanation_height +
                merge_height +
                replacement_height +
                SettingsReviewLines(
                    SettingsReviewNoApp(),
                    removals,
                    view,
                    0n,
                    font,
                    line_height,
                    "review-removed"
                );
            props.scroll_offset = State_settings_data_ui.review_scroll;
            let scrolled = Scroll({
                session: app.ui.session,
                props: props,
                children: (scrolled: NativeScroll.ScrollResult): void => {
                    State_settings_data_ui.review_scroll = scrolled.scroll_offset;
                    SettingsReviewLines(
                        app,
                        explanation,
                        view,
                        State_settings_data_ui.review_scroll,
                        font,
                        line_height,
                        "review-detail"
                    );
                    SettingsReviewLines(
                        app,
                        value,
                        view,
                        State_settings_data_ui.review_scroll - explanation_height,
                        font,
                        line_height,
                        ""
                    );
                    if (removals.count > 0n) {
                        let replacement_offset =
                            State_settings_data_ui.review_scroll -
                            explanation_height -
                            merge_height;
                        SettingsReviewLines(
                            app,
                            replacement,
                            view,
                            replacement_offset,
                            font,
                            line_height,
                            "review-removed"
                        );
                        SettingsReviewLines(
                            app,
                            removals,
                            view,
                            replacement_offset - replacement_height,
                            font,
                            line_height,
                            "review-removed"
                        );
                    }
                }
            });
            if (!scrolled.opened) {
                State_settings_data_ui.review_scroll = scrolled.scroll_offset;
            }
            let options: [string, string, string] = [
                "review_merge",
                "sync_review_keep_local",
                "sync_review_use_remote"
            ];
            let modes: [s32, s32, s32] = [2n, 0n, 1n];
            y = s32(content.y + content.height) - AppScale(132n);
            let index: s32 = s32(0n);
            while (index < 3n) {
                let button = SettingsDataButtonProps(
                    LocaleText(nativeAt(options, index)),
                    x,
                    y,
                    text_width,
                    5351n + index,
                    index === 0n
                );
                if (index === 0n) {
                    button.disabled = !State_settings_data_ui.review_cached_available;
                } else if (index === 2n) {
                    button.disabled = !State_settings_data_ui.review_cached_replace_available;
                    button.tone = ButtonTone.ButtonToneDanger;
                }
                if (Button({ session: app.ui.session, props: button })) {
                    nativeDeref(decision_ref) = nativeAt(modes, index) + 1n;
                }
                y = y + AppScale(44n);
                index = index + 1n;
            }
        }
    });
    if (frame.dismissed || frame.right_clicked) {
        SettingsReviewReset();
        app_close_modal(app);
        return 0n;
    }
    return decision;
}
