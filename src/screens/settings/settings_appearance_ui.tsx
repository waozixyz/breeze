import { SettingsAppearanceNewStates } from "settings_appearance";
import { SettingsAppearanceNewTargets } from "settings_appearance";
import { SettingsAppearanceNewByteBuffer } from "settings_appearance";
import { SettingsAppearanceNewBytes } from "settings_appearance";
import { SettingsAppearanceNewTyped } from "settings_appearance";
import { SettingsAppearanceNewSources } from "settings_appearance";
import { SettingsAppearanceNewScopes } from "settings_appearance";
import { AppearanceErrorText } from "settings_appearance";
// Authored UI composition; native application state remains in settings_appearance.zi.
import * as NativeDropdown from "kryon/dropdown";
import * as NativeTextArea from "kryon/text_area";
import * as State_style_customization from "style_customization";
import * as State_settings_appearance from "settings_appearance";
import * as State_app_style from "app_style";
import { StyleImport, app_apply_style } from "app_style";
import { InnerBreeze } from "app_types";
import {
    AppearanceDiscard,
    AppearanceFormat,
    AppearanceInspection,
    AppearancePreview,
    AppearanceReset,
    AppearanceSave,
    AppearanceUndo
} from "appearance_actions";
import { HostSeconds } from "host_clock";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { Text } from "kryon/tsx/text";
import { TextArea } from "kryon/tsx/text_area";
import { LocaleText } from "locale";
import { AppearanceAskLumi } from "lumi_screen";
import { AppFontSize, AppParagraphHeight, AppScale, AppSmallFontSize } from "metrics";
import { PackageFree } from "package_files";
import {
    AppearanceActionColumns,
    AppearanceTarget,
    AppearanceTargetClass,
    AppearanceTargetState
} from "settings_appearance";
import { SettingsThemeState } from "settings_types";
import { settings_choice_rowView as settings_choice_row } from "settings_ui_ui";
import { Vec } from "std/vec";
import {
    StyleDraftSource,
    StyleSavedSource,
    StyleScopeName,
    StyleSetDraft,
    StyleSourceCapacity
} from "style_customization";
import {
    AppCopyText,
    AppReplaceText,
    AppTextFromCString,
    CopyTextToBuffer,
    FrameTextHold
} from "text_buffers";
import { SampleTextAreaInput, TextInputWriteClipboard } from "text_input_host";

export function settings_appearance_draw(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    state: NativeRef<SettingsThemeState>
): void {
    if (
        Button({
            session: app.ui.session,
            props: {
                id: 7850n,
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: float32(width),
                    height: float32(AppScale(48n))
                },
                label: LocaleText("appearance_css_advanced"),
                selected: State_style_customization.style_editor_open,
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                disabled: app.modal.active !== 0n
            }
        })
    ) {
        State_style_customization.style_editor_open = !State_style_customization.style_editor_open;
        state.custom_focused = false;
        app_apply_style(app);
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(64n);
    if (!State_style_customization.style_editor_open) {
        return;
    }
    let hint_height = AppParagraphHeight(
        LocaleText("appearance_css_hint"),
        width,
        AppFontSize(),
        0n
    );
    <Text
        session={app.ui.session}
        props={{
            text: LocaleText("appearance_css_hint"),
            size: AppFontSize(),
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(hint_height)
            },
            wrap: Wrap.TextWrapAuto
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + (hint_height + AppScale(16n));
    let scopes = SettingsAppearanceNewScopes();
    nativeAt(scopes, 0n).label = LocaleText("appearance_css_all");
    nativeAt(scopes, 1n).label = LocaleText("tab_elist");
    nativeAt(scopes, 2n).label = LocaleText("tab_habits");
    nativeAt(scopes, 3n).label = LocaleText("tab_practices");
    nativeAt(scopes, 4n).label = LocaleText("tab_diary");
    nativeAt(scopes, 5n).label = "Lumi";
    let scope_props: NativeDropdown.Props = {};
    scope_props.id = 7851n;
    scope_props.bounds = settings_choice_row(app, x, width, y, LocaleText("appearance_css_scope"));
    scope_props.selected_index = State_style_customization.style_editor_scope;
    let custom_scope_menu = Dropdown({
        session: app.ui.session,
        props: scope_props,
        options: nativeSlice(scopes)
    });
    if (custom_scope_menu.changed) {
        State_style_customization.style_editor_scope = custom_scope_menu.selected_index;
        state.custom_cursor = 0n;
        state.custom_anchor = 0n;
        state.custom_scroll = 0n;
        state.custom_focused = false;
        state.custom_pending = false;
        app_apply_style(app);
    }
    let sources = SettingsAppearanceNewSources();
    nativeAt(sources, 0n).label = LocaleText("appearance_css_custom");
    nativeAt(sources, 1n).label = LocaleText("appearance_css_defaults");
    nativeAt(sources, 2n).label = LocaleText("appearance_css_pack");
    let source_props: NativeDropdown.Props = {};
    source_props.id = 7852n;
    source_props.bounds = settings_choice_row(
        app,
        x,
        width,
        y,
        LocaleText("appearance_css_source")
    );
    source_props.selected_index = state.custom_source_view;
    let custom_source_menu = Dropdown({
        session: app.ui.session,
        props: source_props,
        options: nativeSlice(sources)
    });
    if (custom_source_menu.changed) {
        state.custom_source_view = custom_source_menu.selected_index;
        state.custom_cursor = 0n;
        state.custom_anchor = 0n;
        state.custom_scroll = 0n;
    }
    let source = StyleDraftSource(State_style_customization.style_editor_scope);
    if (state.custom_source_view === 1n) {
        source = StyleImport("inbe").data;
    } else if (state.custom_source_view === 2n) {
        source = StyleImport("material").data;
    }
    let typed = SettingsAppearanceNewTyped();
    let area: NativeTextArea.Props = {};
    area.key = u64(785300n);
    area.focus_id = 7853n;
    area.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y)),
        width: float32(width),
        height: float32(AppScale(300n))
    };
    area.value = source;
    if (state.custom_source_view === 0n) {
        area.value = FrameTextHold(nativeRef(app.ui.frame_text), source);
    }
    area.label = LocaleText("appearance_css_custom");
    area.placeholder = "Button { radius: 24; }";
    area.cursor = state.custom_cursor;
    area.anchor = state.custom_anchor;
    area.scroll_y = state.custom_scroll;
    area.focused = state.custom_focused;
    area.selecting = state.custom_selecting;
    area.preferred_x = state.custom_preferred_x;
    area.preferred_x_valid = state.custom_preferred_x_valid;
    area.wrap = true;
    area.read_only = state.custom_source_view !== 0n;
    area.max_bytes = StyleSourceCapacity - 1n;
    area.max_codepoints = StyleSourceCapacity - 1n;
    area.input = SampleTextAreaInput(area.focused, nativeSlice(typed));
    let edited = TextArea({ session: app.ui.session, props: area });
    state.custom_cursor = edited.cursor;
    state.custom_anchor = edited.anchor;
    state.custom_scroll = edited.scroll_y;
    state.custom_focused = edited.focused;
    state.custom_selecting = edited.selecting;
    state.custom_preferred_x = edited.preferred_x;
    state.custom_preferred_x_valid = edited.preferred_x_valid;
    if (edited.clipboard_write) {
        TextInputWriteClipboard(edited.clipboard_text);
    }
    if (edited.edit.changed && state.custom_source_view === 0n) {
        let bytes = SettingsAppearanceNewBytes();
        AppCopyText(source, nativeSlice(bytes));
        if (
            AppReplaceText(
                nativeSlice(bytes),
                edited.edit.start,
                edited.edit.end,
                edited.edit.replacement
            )
        ) {
            StyleSetDraft(
                State_style_customization.style_editor_scope,
                AppTextFromCString(nativeRef(nativeAt(bytes, 0n)), StyleSourceCapacity)
            );
            state.custom_pending = true;
            state.custom_preview_at = HostSeconds() + 0.25;
        }
    }
    if (state.custom_pending && HostSeconds() >= state.custom_preview_at) {
        AppearancePreview(app, State_style_customization.style_editor_scope);
        state.custom_pending = false;
    }
    nativeDeref(y) = nativeDeref(y) + AppScale(312n);
    let error = AppTextFromCString(
        nativeRef(nativeAt(State_style_customization.style_error, 0n)),
        256n
    );
    let status =
        StyleDraftSource(State_style_customization.style_editor_scope) ===
        StyleSavedSource(State_style_customization.style_editor_scope)
            ? LocaleText("appearance_css_saved")
            : LocaleText("appearance_css_preview");
    if (error.count > 0n) {
        status = AppearanceErrorText(app, error);
    }
    <Text
        session={app.ui.session}
        props={{
            text: status,
            bounds: {
                x: float32(x),
                y: float32(nativeDeref(y)),
                width: float32(width),
                height: float32(AppScale(66n))
            },
            size: AppSmallFontSize(),
            wrap: Wrap.TextWrapAuto
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(74n);
    let labels: [string, string, string, string, string, string] = [
        LocaleText("save_button"),
        LocaleText("appearance_css_format"),
        LocaleText("appearance_css_undo"),
        LocaleText("discard_button"),
        LocaleText("reset_to_defaults_label"),
        LocaleText("appearance_css_lumi")
    ];
    let columns = AppearanceActionColumns(width);
    let gap = AppScale(8n);
    let button_width = (width - gap * (columns - 1n)) / columns;
    for (let index = s32(0n); index <= s32(5n); index += s32(1)) {
        if (
            Button({
                session: app.ui.session,
                props: {
                    id: 7860n + index,
                    bounds: {
                        x: float32(x + (index % columns) * (button_width + gap)),
                        y: float32(nativeDeref(y) + (index / columns) * AppScale(52n)),
                        width: float32(button_width),
                        height: float32(AppScale(44n))
                    },
                    label: nativeAt(labels, index),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: app.modal.active !== 0n
                }
            })
        ) {
            if (index === 0n) {
                AppearanceSave(app, State_style_customization.style_editor_scope);
            } else if (index === 1n) {
                AppearanceFormat(app, State_style_customization.style_editor_scope);
            } else if (index === 2n) {
                AppearanceUndo(app, State_style_customization.style_editor_scope);
            } else if (index === 3n) {
                AppearanceDiscard(app, State_style_customization.style_editor_scope);
            } else if (index === 4n) {
                AppearanceReset(app, State_style_customization.style_editor_scope);
            } else {
                AppearanceAskLumi(
                    app,
                    StyleScopeName(State_style_customization.style_editor_scope)
                );
            }
            state.custom_pending = false;
        }
    }
    nativeDeref(y) = nativeDeref(y) + ((6n + columns - 1n) / columns) * AppScale(52n);
    let targets = SettingsAppearanceNewTargets();
    let labels_target: [
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string
    ] = [
        "Button",
        "Text",
        "Card",
        "TextArea",
        "TextField",
        "NavigationBarItem.launcher-dock",
        "Button.profile-header",
        "Button.practice-pager",
        "Button.launcher-tile",
        "Image.pose-muted"
    ];
    for (let index = s32(0n); index <= s32(9n); index += s32(1)) {
        nativeAt(targets, index).label = nativeAt(labels_target, index);
    }
    let target_props: NativeDropdown.Props = {};
    target_props.id = 7870n;
    target_props.bounds = settings_choice_row(
        app,
        x,
        width,
        y,
        LocaleText("appearance_css_inspect")
    );
    target_props.selected_index = state.custom_target;
    let custom_target_menu = Dropdown({
        session: app.ui.session,
        props: target_props,
        options: nativeSlice(targets)
    });
    if (custom_target_menu.changed) {
        state.custom_target = custom_target_menu.selected_index;
    }
    let states = SettingsAppearanceNewStates();
    for (let index = s32(0n); index <= s32(5n); index += s32(1)) {
        nativeAt(states, index).label = AppearanceTargetState(index);
    }
    let state_props: NativeDropdown.Props = {};
    state_props.id = 7871n;
    state_props.bounds = settings_choice_row(app, x, width, y, LocaleText("appearance_css_state"));
    state_props.selected_index = state.custom_state;
    let custom_state_menu = Dropdown({
        session: app.ui.session,
        props: state_props,
        options: nativeSlice(states)
    });
    if (custom_state_menu.changed) {
        state.custom_state = custom_state_menu.selected_index;
    }
    if (
        State_settings_appearance.appearance_inspector_revision !==
            State_app_style.style_generation ||
        State_settings_appearance.appearance_inspector_target !== state.custom_target ||
        State_settings_appearance.appearance_inspector_state !== state.custom_state ||
        State_settings_appearance.appearance_inspector_scope !==
            State_style_customization.style_editor_scope
    ) {
        let report = AppearanceInspection(
            AppearanceTarget(state.custom_target),
            AppearanceTargetClass(state.custom_target),
            AppearanceTargetState(state.custom_state)
        );
        CopyTextToBuffer(
            nativeRef(nativeAt(State_settings_appearance.appearance_inspector, 0n)),
            8192n,
            report
        );
        PackageFree(report);
        State_settings_appearance.appearance_inspector_revision = State_app_style.style_generation;
        State_settings_appearance.appearance_inspector_target = state.custom_target;
        State_settings_appearance.appearance_inspector_state = state.custom_state;
        State_settings_appearance.appearance_inspector_scope =
            State_style_customization.style_editor_scope;
    }
    let inspection: NativeTextArea.Props = {};
    inspection.key = u64(787200n);
    inspection.focus_id = 7872n;
    inspection.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y)),
        width: float32(width),
        height: float32(AppScale(210n))
    };
    inspection.value = AppTextFromCString(
        nativeRef(nativeAt(State_settings_appearance.appearance_inspector, 0n)),
        8192n
    );
    inspection.label = LocaleText("appearance_css_inspect");
    inspection.read_only = true;
    inspection.wrap = true;
    inspection.scroll_y = state.custom_inspector_scroll;
    let result = TextArea({ session: app.ui.session, props: inspection });
    state.custom_inspector_scroll = result.scroll_y;
    nativeDeref(y) = nativeDeref(y) + AppScale(234n);
}
