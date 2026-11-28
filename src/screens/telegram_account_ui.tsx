import { ResolvedModal } from "kryon/tsx/modal";
import { Scroll } from "kryon/tsx/scroll";
import { TelegramAccountNewTyped } from "telegram_account";
import { TelegramAccountNewMask } from "telegram_account";
import { TelegramAccountNewParagraphHeights } from "telegram_account";
import { TelegramAccountNewReviewDisplay } from "telegram_account";
// Authored UI composition; native application state remains in telegram_account.zi.
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeText from "kryon/text";
import { InnerBreeze } from "app_types";
import { SecureWipe } from "crypto/wipe";
import { ButtonEmphasis, ButtonState } from "kryon/control_props";
import { SessionValid } from "kryon/session";
import { StyleKindScroll, StyleKindScrollThumb } from "kryon/style_sheet";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { ControlledTextField } from "kryon/tsx/text_field";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import { PackageFree, PackageText } from "package_files";
import { TextUntilNul } from "std/text_buffer";
import {
    TelegramAccountActionAllowed,
    TelegramAccountActionLabel,
    TelegramAccountApplyPassword,
    TelegramAccountObservePassword,
    TelegramAccountPasswordUpdate,
    TelegramAccountApprovalReady,
    TelegramAccountClearPassword,
    TelegramAccountPasswordMask,
    TelegramAccountReviewText,
    TelegramAccountView
} from "telegram_account";
import { AppCopyText, AppTextFromCString, FrameTextHold } from "text_buffers";
import { SampleTextFieldInput } from "text_input_host";

export function DrawTelegramAccount(
    app: NativeRef<InnerBreeze>,
    view: NativeRef<TelegramAccountView>
): s32 {
    if (
        !NativePresent(app) ||
        !NativePresent(view) ||
        !view.visible ||
        !SessionValid(app.ui.session)
    ) {
        return 0n;
    }
    if (
        TextUntilNul(nativeSlice(view.seen_review_id)) !== view.review_id ||
        TextUntilNul(nativeSlice(view.seen_review_details)) !== view.details
    ) {
        view.review_seen = false;
        view.scroll_offset = 0n;
        AppCopyText(view.review_id, nativeSlice(view.seen_review_id));
        AppCopyText(view.details, nativeSlice(view.seen_review_details));
    }
    let width = app.ui.view_width - AppScale(24n);
    if (width > AppScale(520n)) {
        width = AppScale(520n);
    }
    let height = app.ui.view_height - AppScale(24n);
    if (width < AppScale(120n) || height < AppScale(120n)) {
        return 0n;
    }
    let password_label = PackageText(
        view.password_label.count > 0n
            ? view.password_label
            : LocaleText("telegram_account_passphrase"),
        ""
    );
    let cancel_allowed = TelegramAccountActionAllowed(view, 4n);
    let title_key = view.title_key.count > 0n ? view.title_key : "telegram_account_title";
    let result: s32 = s32(0n);
    const result_ref = nativeRef(result);
    let frame = ResolvedModal({
        session: app.ui.session,
        props: {
            key: u64(76600n),
            title: FrameTextHold(nativeRef(app.ui.frame_text), LocaleText(title_key)),
            width: width,
            height: height,
            scale: MetricsScale(),
            has_right_action: cancel_allowed,
            right_label: LocaleText("cancel_button"),
            dismiss_disabled: !cancel_allowed
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let content_width = s32(frame.layout.content.width);
            let message_key = view.message_key;
            if (message_key.count === 0n) {
                if (TelegramAccountActionAllowed(view, 1n)) {
                    message_key = "telegram_account_create_body";
                } else if (
                    TelegramAccountActionAllowed(view, 2n) ||
                    TelegramAccountActionAllowed(view, 7n)
                ) {
                    message_key = "telegram_account_restore_body";
                } else {
                    message_key = "telegram_account_connect_body";
                }
            }
            let message = PackageText(LocaleText(message_key), "");
            let status = PackageText(
                view.restore_failed ? LocaleText("telegram_account_restore_failed") : view.status,
                ""
            );
            let track = NativeScroll.ScrollFace(
                StyleKindScroll(),
                0n,
                false,
                s32(s32(ButtonState.ButtonStateNormal)),
                10.0
            );
            let thumb = NativeScroll.ScrollFace(
                StyleKindScrollThumb(),
                0n,
                false,
                s32(s32(ButtonState.ButtonStateNormal)),
                10.0
            );
            let scroll_metrics = NativeScroll.ScrollMetricsFor(MetricsScale(), track, thumb);
            let review_display = TelegramAccountNewReviewDisplay();
            let review = "";
            let paragraphs: [string, string, string] = [message, status, ""];
            if (nativeAt(paragraphs, 1n).count > 1024n) {
                nativeSet(paragraphs, 1n, "");
            }
            let paragraph_heights = TelegramAccountNewParagraphHeights();
            let password_label_height: s32 = s32(0n);
            let content_height: s32 = s32(0n);
            for (let pass = s32(0); pass <= 1n; pass += s32(1)) {
                content_height = AppScale(16n);
                review = "";
                if (
                    TelegramAccountReviewText(
                        view.details,
                        content_width,
                        nativeSlice(review_display)
                    )
                ) {
                    review = TextUntilNul(nativeSlice(review_display));
                }
                nativeSet(paragraphs, 2n, review);
                for (let index = s32(0); index <= 2n; index += s32(1)) {
                    nativeSet(paragraph_heights, index, 0n);
                    if (nativeAt(paragraphs, index).count > 0n) {
                        let prepared = NativeText.PrepareText(
                            {
                                text: nativeAt(paragraphs, index),
                                size: AppFontSize(),
                                bounds: {
                                    x: 0.0,
                                    y: 0.0,
                                    width: float32(content_width),
                                    height: 0.0
                                },
                                wrap: Wrap.TextWrapAuto
                            },
                            NativeText.DefaultTextFace()
                        );
                        nativeSet(
                            paragraph_heights,
                            index,
                            s32(prepared.bounds.height) + AppScale(16n)
                        );
                        content_height = content_height + nativeAt(paragraph_heights, index);
                    }
                }
                if (NativePresent(view.password)) {
                    let prepared = NativeText.PrepareText(
                        {
                            text: password_label,
                            size: AppFontSize(),
                            bounds: { x: 0.0, y: 0.0, width: float32(content_width), height: 0.0 },
                            wrap: Wrap.TextWrapAuto
                        },
                        NativeText.DefaultTextFace()
                    );
                    password_label_height = s32(prepared.bounds.height) + AppScale(8n);
                    content_height = content_height + (password_label_height + AppScale(64n));
                }
                for (let action = s32(1n); action <= 7n; action += s32(1)) {
                    if (TelegramAccountActionAllowed(view, action)) {
                        content_height = content_height + AppScale(56n);
                    }
                }
                if (pass === 0n && float32(content_height) > frame.layout.content.height) {
                    let narrowed = NativeScroll.ScrollContentBounds(
                        frame.layout.content,
                        true,
                        scroll_metrics
                    );
                    content_width = s32(narrowed.width);
                } else {
                    break;
                }
            }
            let scroll = Scroll({
                session: app.ui.session,
                props: {
                    key: u64(76601n),
                    bounds: frame.layout.content,
                    content_height: content_height,
                    scroll_offset: view.scroll_offset,
                    scale: MetricsScale(),
                    metrics: scroll_metrics
                },
                children: (scroll: NativeScroll.ScrollResult): void => {
                    nativeDeref(view).scroll_offset = scroll.scroll_offset;
                    let x = s32(scroll.content.x);
                    let y = s32(scroll.content.y) + AppScale(8n);
                    let review_retained = false;
                    for (let index = s32(0); index <= 2n; index += s32(1)) {
                        if (nativeAt(paragraphs, index).count > 0n) {
                            let held = FrameTextHold(
                                nativeRef(app.ui.frame_text),
                                nativeAt(paragraphs, index)
                            );
                            <Text
                                session={app.ui.session}
                                props={{
                                    text: held,
                                    size: AppFontSize(),
                                    bounds: {
                                        x: float32(x),
                                        y: float32(y),
                                        width: float32(content_width),
                                        height: float32(nativeAt(paragraph_heights, index))
                                    },
                                    wrap: Wrap.TextWrapAuto
                                }}
                            />;
                            y = y + nativeAt(paragraph_heights, index);
                            if (index === 2n) {
                                review_retained = held.count === review.count && held.count > 0n;
                                if (
                                    review_retained &&
                                    float32(y - AppScale(16n)) <=
                                        scroll.viewport.y + scroll.viewport.height
                                ) {
                                    nativeDeref(view).review_seen = true;
                                }
                            }
                        }
                    }
                    let password_valid = false;
                    if (NativePresent(view.password)) {
                        let held_label = FrameTextHold(
                            nativeRef(app.ui.frame_text),
                            password_label
                        );
                        <Text
                            session={app.ui.session}
                            props={{
                                text: held_label,
                                size: AppFontSize(),
                                bounds: {
                                    x: float32(x),
                                    y: float32(y),
                                    width: float32(content_width),
                                    height: float32(password_label_height)
                                },
                                wrap: Wrap.TextWrapAuto
                            }}
                        />;
                        y = y + password_label_height;
                        let password = view.password;
                        let mask = TelegramAccountNewMask();
                        password_valid =
                            held_label.count === password_label.count &&
                            held_label.count > 0n &&
                            TelegramAccountPasswordMask(password, nativeSlice(mask));
                        if (password_valid) {
                            let typed = TelegramAccountNewTyped();
                            let update: TelegramAccountPasswordUpdate = {};
                            {
                                let input = SampleTextFieldInput(
                                    password.focused && !view.busy,
                                    nativeSlice(typed)
                                );
                                input.copy = false;
                                input.cut = false;
                                let field = ControlledTextField({
                                    session: app.ui.session,
                                    props: {
                                        key: u64(76602n),
                                        bounds: {
                                            x: float32(x),
                                            y: float32(y),
                                            width: float32(content_width),
                                            height: float32(AppScale(48n))
                                        },
                                        value: AppTextFromCString(
                                            nativeRef(nativeAt(password.value, 0n)),
                                            257n
                                        ),
                                        display_value: TextUntilNul(nativeSlice(mask)),
                                        label: held_label,
                                        cursor: password.cursor,
                                        anchor: password.anchor,
                                        scroll_x: password.scroll_x,
                                        focused: password.focused,
                                        composition: password.composition,
                                        focus_id: 76602n,
                                        max_bytes: 256n,
                                        max_codepoints: 256n,
                                        secure: true,
                                        disabled:
                                            view.busy ||
                                            held_label.count !== password_label.count ||
                                            held_label.count === 0n,
                                        input: input,
                                        scale: MetricsScale()
                                    }
                                });
                                update = TelegramAccountObservePassword(field);
                            }
                            TelegramAccountApplyPassword(password, nativeRef(update));
                            SecureWipe(nativeSlice(update.replacement));
                            SecureWipe(nativeSlice(update.preedit));
                            SecureWipe(nativeSlice(typed));
                            if (update.escaped && cancel_allowed) {
                                TelegramAccountClearPassword(password);
                                nativeDeref(result_ref) = 4n;
                            }
                        }
                        y = y + AppScale(64n);
                    }
                    for (let action = s32(1n); action <= 7n; action += s32(1)) {
                        if (!TelegramAccountActionAllowed(view, action)) {
                            continue;
                        }
                        let disabled = view.busy && action !== 4n;
                        if (action === 6n && !TelegramAccountApprovalReady(view, review_retained)) {
                            disabled = true;
                        }
                        if (
                            NativePresent(view.password) &&
                            (action === 5n || action === 7n) &&
                            (!password_valid ||
                                nativeAt(view.password.value, 0n) === u8(0n) ||
                                password_label.count === 0n)
                        ) {
                            disabled = true;
                        }
                        const customLabel = nativeAt(view.action_labels, action).count > 0n;
                        const label = customLabel
                            ? FrameTextHold(
                                  nativeRef(app.ui.frame_text),
                                  nativeAt(view.action_labels, action)
                              )
                            : TelegramAccountActionLabel(action);
                        if (customLabel && label.count === 0n) {
                            disabled = true;
                        }
                        if (
                            Button({
                                session: app.ui.session,
                                props: {
                                    id: 76610n + action,
                                    bounds: {
                                        x: float32(x),
                                        y: float32(y),
                                        width: float32(content_width),
                                        height: float32(AppScale(48n))
                                    },
                                    label: label,
                                    disabled: disabled,
                                    loading: view.busy && action !== 4n,
                                    emphasis:
                                        action === 4n
                                            ? ButtonEmphasis.ButtonEmphasisGhost
                                            : ButtonEmphasis.ButtonEmphasisFilled
                                }
                            }) &&
                            nativeDeref(result_ref) === 0n &&
                            !disabled
                        ) {
                            nativeDeref(result_ref) = action;
                            if (action === 4n) {
                                TelegramAccountClearPassword(view.password);
                            }
                        }
                        y = y + AppScale(56n);
                    }
                }
            });
            if (!scroll.opened) {
                nativeDeref(view).scroll_offset = scroll.scroll_offset;
            }
            PackageFree(message);
            PackageFree(status);
        }
    });
    PackageFree(password_label);
    if (frame.dismissed || frame.right_clicked) {
        if (cancel_allowed) {
            TelegramAccountClearPassword(view.password);
            return 4n;
        }
        return 0n;
    }
    return result;
}
