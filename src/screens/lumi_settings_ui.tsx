import { Scroll } from "kryon/tsx/scroll";
import { LumiSettingsNewOptions } from "lumi_settings";
import { LumiSettingsNewTyped } from "lumi_settings";
import {
    LumiSettingsApplyField,
    LumiSettingsFieldUpdate,
    LumiSettingsObserveField
} from "lumi_settings";
import { LumiSettingsNewMask } from "lumi_settings";
import { app_content_bottom_reserved } from "app_nav_state";
import { storage_set_setting_text } from "storage_settings";
// Authored UI composition; native application state remains in lumi_settings.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeTitleBar from "kryon/title_bar";
import * as State_lumi_settings from "lumi_settings";
import { InnerBreeze } from "app_types";
import { SecureWipe } from "crypto/wipe";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Text } from "kryon/tsx/text";
import { ControlledTextField } from "kryon/tsx/text_field";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import {
    LUMI_PROVIDER_KEY_MAX,
    LUMI_PROVIDER_MODEL_MAX,
    LUMI_PROVIDER_URL_MAX,
    LumiAiAgreed,
    LumiNodeAgreed,
    LumiOwnProviderReady,
    LumiOwnProviderSelected,
    LumiProviderKeySetting,
    LumiProviderSetting,
    LumiWithdraw
} from "lumi_connection";
import { app_lumi_show_agreement } from "lumi_screen";
import {
    LUMI_SETTINGS_TITLE,
    LumiSettingsField,
    SETTINGS_LUMI_FIELD,
    SETTINGS_LUMI_LABEL,
    lumi_settings_connection_body,
    lumi_settings_content_height,
    lumi_settings_load,
    lumi_settings_save,
    lumi_settings_status,
    lumi_settings_terms_body,
    lumi_settings_text_height
} from "lumi_settings";
import { AppFontSize, AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";

import { settings_section_end, settings_section_inner_width } from "settings_ui";
import { settings_section_beginView as settings_section_begin } from "settings_ui_ui";
import { TextUntilNul } from "std/text_buffer";
import { storage_get_setting_text } from "storage_settings";
import { AppTextFromCString, FrameTextHold } from "text_buffers";
import { SampleTextFieldInput } from "text_input_host";

export function lumi_settings_field(
    app: NativeRef<InnerBreeze>,
    field: NativeRef<LumiSettingsField>,
    id: s32,
    label: string,
    placeholder: string,
    secure: boolean,
    max_bytes: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    <Text
        session={app.ui.session}
        props={{
            text: label,
            size: AppSmallFontSize(),
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(SETTINGS_LUMI_LABEL))
            }
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(SETTINGS_LUMI_LABEL);
    let mask = LumiSettingsNewMask();
    if (secure) {
        let count: s32 = s32(0n);
        for (const byte of AppTextFromCString(
            nativeRef(nativeAt(field.value, 0n)),
            LUMI_PROVIDER_URL_MAX
        )) {
            if ((byte < u8(128n) || byte >= u8(192n)) && count < LUMI_PROVIDER_URL_MAX - 1n) {
                nativeSet(mask, count, u8(42n));
                count = count + 1n;
            }
        }
    }
    let typed = LumiSettingsNewTyped();
    let update: LumiSettingsFieldUpdate = {};
    {
        let input = SampleTextFieldInput(field.focused, nativeSlice(typed));
        if (secure) {
            input.copy = false;
            input.cut = false;
        }
        let result = ControlledTextField({
            session: app.ui.session,
            props: {
                key: u64(id),
                focus_id: id,
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: float32(width),
                    height: float32(AppScale(SETTINGS_LUMI_FIELD))
                },
                value: AppTextFromCString(
                    nativeRef(nativeAt(field.value, 0n)),
                    LUMI_PROVIDER_URL_MAX
                ),
                display_value: secure ? TextUntilNul(nativeSlice(mask)) : "",
                label: label,
                placeholder: placeholder,
                cursor: field.cursor,
                anchor: field.anchor,
                scroll_x: field.scroll_x,
                focused: field.focused,
                composition: field.composition,
                max_bytes: max_bytes,
                max_codepoints: max_bytes,
                secure: secure,
                input: input,
                scale: MetricsScale()
            }
        });
        update = LumiSettingsObserveField(result);
    }
    LumiSettingsApplyField(field, nativeRef(update));
    SecureWipe(nativeSlice(update.replacement));
    SecureWipe(nativeSlice(update.preedit));
    SecureWipe(nativeSlice(typed));
    nativeDeref(y) = nativeDeref(y) + AppScale(SETTINGS_LUMI_FIELD + 10n);
}

export function lumi_settings_draw(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    if (!NativePresent(app) || !NativePresent(y)) {
        return;
    }
    lumi_settings_load();
    let inner = settings_section_inner_width(width);
    let terms_body = lumi_settings_terms_body(inner);
    let terms = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("lumi_settings_terms"),
        terms_body
    );
    {
        let status = lumi_settings_status();
        let status_height = lumi_settings_text_height(status, terms.inner_width);
        <Text
            session={app.ui.session}
            props={{
                text: status,
                size: AppFontSize(),
                wrap: Wrap.TextWrapAuto,
                bounds: {
                    x: float32(terms.inner_x),
                    y: float32(nativeDeref(y) + AppScale(6n)),
                    width: float32(terms.inner_width),
                    height: float32(status_height)
                }
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + status_height;
    }
    let agreed = LumiAiAgreed() && LumiNodeAgreed();
    let half = (terms.inner_width - AppScale(8n)) / 2n;
    let read_width = agreed ? half : terms.inner_width;
    if (
        Button({
            session: app.ui.session,
            props: {
                id: 7801n,
                label: LocaleText("lumi_settings_read_terms"),
                bounds: {
                    x: float32(terms.inner_x),
                    y: float32(nativeDeref(y)),
                    width: float32(read_width),
                    height: float32(AppScale(44n))
                },
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        if (LumiOwnProviderSelected() && !LumiOwnProviderReady()) {
            State_lumi_settings.lumi_settings_notice = 2n;
        } else {
            app_lumi_show_agreement(app);
        }
    }
    if (
        agreed &&
        Button({
            session: app.ui.session,
            props: {
                id: 7802n,
                label: LocaleText("lumi_agreement_withdraw"),
                bounds: {
                    x: float32(terms.inner_x + half + AppScale(8n)),
                    y: float32(nativeDeref(y)),
                    width: float32(half),
                    height: float32(AppScale(44n))
                },
                tone: ButtonTone.ButtonToneDanger,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        LumiWithdraw();
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(56n);
    settings_section_end(y);
    let connection_body = lumi_settings_connection_body(inner);
    let connection = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("lumi_settings_connection"),
        connection_body
    );
    {
        let own = LumiOwnProviderSelected();
        let options: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] =
            [
                { label: LocaleText("lumi_settings_node") },
                { label: LocaleText("lumi_settings_own") }
            ];
        let props: NativeSegmentedControl.Props = {};
        props.id = 7803n;
        props.bounds = {
            x: float32(connection.inner_x),
            y: float32(nativeDeref(y) + AppScale(6n)),
            width: float32(connection.inner_width),
            height: float32(AppScale(42n))
        };
        props.height = AppScale(42n);
        props.selected_index = own ? 1n : 0n;
        props.has_selection = true;
        let choice = SegmentedControl({
            session: app.ui.session,
            props: props,
            options: nativeSlice(options)
        });
        if (choice.changed) {
            storage_set_setting_text(
                LumiProviderSetting,
                choice.selected_index === 1n ? "own" : ""
            );
            State_lumi_settings.lumi_settings_notice = 0n;
        }
        nativeDeref(y) = nativeDeref(y) + AppScale(54n);
    }
    if (!LumiOwnProviderSelected()) {
        settings_section_end(y);
        return;
    }
    lumi_settings_field(
        app,
        nativeRef(State_lumi_settings.lumi_settings_url),
        7804n,
        LocaleText("lumi_settings_url"),
        "https://api.openai.com/v1",
        false,
        LUMI_PROVIDER_URL_MAX - 1n,
        connection.inner_x,
        connection.inner_width,
        y
    );
    let key_saved = storage_get_setting_text(LumiProviderKeySetting).count > 0n;
    lumi_settings_field(
        app,
        nativeRef(State_lumi_settings.lumi_settings_key),
        7805n,
        FrameTextHold(nativeRef(app.ui.frame_text), LocaleText("lumi_settings_key")),
        key_saved ? LocaleText("lumi_settings_key_saved") : "",
        true,
        LUMI_PROVIDER_KEY_MAX - 1n,
        connection.inner_x,
        connection.inner_width,
        y
    );
    lumi_settings_field(
        app,
        nativeRef(State_lumi_settings.lumi_settings_model),
        7806n,
        LocaleText("lumi_settings_model"),
        "",
        false,
        LUMI_PROVIDER_MODEL_MAX - 1n,
        connection.inner_x,
        connection.inner_width,
        y
    );
    {
        let note = LocaleText("lumi_settings_own_note");
        let note_height = lumi_settings_text_height(note, connection.inner_width);
        <Text
            session={app.ui.session}
            props={{
                text: note,
                size: AppSmallFontSize(),
                wrap: Wrap.TextWrapAuto,
                bounds: {
                    x: float32(connection.inner_x),
                    y: float32(nativeDeref(y)),
                    width: float32(connection.inner_width),
                    height: float32(note_height)
                }
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + note_height;
    }
    if (State_lumi_settings.lumi_settings_notice !== 0n) {
        let notice = LocaleText(
            State_lumi_settings.lumi_settings_notice === 1n
                ? "lumi_settings_saved"
                : "lumi_settings_invalid"
        );
        let notice_height = lumi_settings_text_height(notice, connection.inner_width);
        <Text
            session={app.ui.session}
            props={{
                text: notice,
                size: AppFontSize(),
                wrap: Wrap.TextWrapAuto,
                bounds: {
                    x: float32(connection.inner_x),
                    y: float32(nativeDeref(y)),
                    width: float32(connection.inner_width),
                    height: float32(notice_height)
                }
            }}
        />;
        nativeDeref(y) = nativeDeref(y) + notice_height;
    }
    half = (connection.inner_width - AppScale(8n)) / 2n;
    let save_width = key_saved ? half : connection.inner_width;
    if (
        Button({
            session: app.ui.session,
            props: {
                id: 7807n,
                label: LocaleText("save_button"),
                bounds: {
                    x: float32(connection.inner_x),
                    y: float32(nativeDeref(y)),
                    width: float32(save_width),
                    height: float32(AppScale(44n))
                },
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled
            }
        })
    ) {
        lumi_settings_save();
    }
    if (
        key_saved &&
        Button({
            session: app.ui.session,
            props: {
                id: 7808n,
                label: LocaleText("lumi_settings_remove_key"),
                bounds: {
                    x: float32(connection.inner_x + half + AppScale(8n)),
                    y: float32(nativeDeref(y)),
                    width: float32(half),
                    height: float32(AppScale(44n))
                },
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        storage_set_setting_text(LumiProviderKeySetting, "");
        State_lumi_settings.lumi_settings_notice = 0n;
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(56n);
    settings_section_end(y);
}

export function lumi_settings_page_draw(
    app: NativeRef<InnerBreeze>,
    scroll: NativeRef<s32>
): boolean {
    let title_h = AppScale(LUMI_SETTINGS_TITLE);
    {
        let bar: NativeTitleBar.Props = {};
        bar.key = NativeLayout.KeyHash("lumi/settings/title");
        bar.title = "Lumi";
        bar.height = title_h;
        bar.bounds = {
            x: 0.0,
            y: 0.0,
            width: float32(app.ui.view_width),
            height: float32(title_h)
        };
        bar.has_leading_action = true;
        bar.leading_label = LocaleText("back_button");
        let options = LumiSettingsNewOptions();
        if (
            TitleBar({ session: app.ui.session, props: bar, options: nativeSlice(options, 0n, 0n) })
                .clicked_leading
        ) {
            return true;
        }
    }
    let column = NativeLayout.CenteredColumnFor(app.ui.view_width, AppScale(720n), AppScale(16n));
    let top = title_h + AppScale(8n);
    let bottom = app.ui.view_height - app_content_bottom_reserved(app);
    let props: NativeScroll.Props = {};
    props.key = NativeLayout.KeyHash("lumi/settings/scroll");
    props.bounds = {
        x: 0.0,
        y: float32(top),
        width: float32(app.ui.view_width),
        height: float32(bottom - top)
    };
    props.content_height = lumi_settings_content_height(column.width) + AppScale(16n);
    props.scroll_offset = nativeDeref(scroll);
    props.scale = MetricsScale();
    let result = Scroll({
        session: app.ui.session,
        props: props,
        children: (result: NativeScroll.ScrollResult): void => {
            nativeDeref(scroll) = result.scroll_offset;
            let y = s32(result.content.y);
            lumi_settings_draw(app, column.x, column.width, nativeRef(y));
        }
    });
    if (!result.opened) {
        nativeDeref(scroll) = result.scroll_offset;
    }
    return false;
}
