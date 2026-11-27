// Authored UI composition; native application state remains in settings_theme.zi.
import * as NativeDropdown from "kryon/dropdown";
import * as NativeImage from "kryon/image";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSlider from "kryon/slider";
import { app_block_current_click, app_close_modal } from "app_modal_state";
import { save_settings } from "app_settings";
import { AppThemeMode, AppThemeSource, InnerBreeze } from "app_types";
import { CurrentApp } from "current_app";
import { app_refresh_theme } from "device_preferences";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { PointerSample } from "kryon/tree_input";
import { Button } from "kryon/tsx/button";
import { DiscreteSlider } from "kryon/tsx/slider";
import { Dropdown } from "kryon/tsx/dropdown";
import { Image } from "kryon/tsx/image";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFitFontSize, AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import { settings_appearance_draw } from "settings_appearance_ui";
import {
    NewFollowDeviceLabel,
    NewModeOptions,
    NewPercentage,
    NewPlacements,
    NewThemeOptions,
    ThemeLabel,
    SettingsAppIconAvailable,
    SettingsAppIconLoad,
    SettingsAppIconOpen,
    SettingsAppIconSelect,
    settings_theme_icon_row_height,
    settings_theme_layout_body,
    settings_theme_scale_label_height,
    settings_theme_scale_row_height,
    settings_theme_scale_stacked,
    settings_theme_theme_body,
    theme_picker_content_height
} from "settings_theme";
import { SettingsSection, SettingsThemeState } from "settings_types";
import {
    settings_choice_row,
    settings_row_divider,
    settings_section_begin,
    settings_section_end,
    settings_section_inner_width
} from "settings_ui";
import { AppTextFromCString, FormatArg, FormatTemplate, FrameTextHold } from "text_buffers";
import { ThemeCount } from "theme_catalog";

export function settings_theme_draw(
    app: *InnerBreeze,
    x: s32,
    w: s32,
    y: *s32,
    state: *SettingsThemeState
): void {
    if (!NativePresent(app) || !NativePresent(y) || !NativePresent(state)) {
        return;
    }
    let inner = settings_section_inner_width(w);
    let theme = settings_section_begin(
        app,
        x,
        w,
        y,
        LocaleText("theme_label"),
        settings_theme_theme_body(inner)
    );
    if (SettingsAppIconAvailable()) {
        SettingsAppIconRow(app, theme, y, state);
    }
    if (draw_theme_settings(app, theme, y, state) !== 0n) {
        app_refresh_theme(app);
        app.settings_dirty = 1n;
        app.settings_save_delay_ticks = 18n;
    }
    settings_section_end(y);
    let layout = settings_section_begin(
        app,
        x,
        w,
        y,
        LocaleText("settings_section_layout"),
        settings_theme_layout_body(app, inner)
    );
    draw_scale_row(app, layout.inner_x, layout.inner_width, y, state);
    settings_row_divider(app, layout, (*y));
    let placements = NewPlacements();
    placements[0n].label = LocaleText("navigation_automatic");
    placements[1n].label = LocaleText("navigation_left");
    placements[2n].label = LocaleText("navigation_bottom");
    placements[3n].label = LocaleText("navigation_right");
    placements[4n].label = LocaleText("navigation_top");
    let placement_props: NativeDropdown.Props = {};
    placement_props.id = 149n;
    placement_props.bounds = settings_choice_row(
        app,
        layout.inner_x,
        layout.inner_width,
        y,
        LocaleText("navigation_placement")
    );
    placement_props.selected_index = app.navigation_placement;
    let placement_menu = (
        <Dropdown
            session={app.ui.session}
            props={placement_props}
            options={placements[:]}
        />
    );
    if (placement_menu.changed) {
        app.navigation_placement = placement_menu.selected_index;
        app.settings_scroll = 0n;
        app_block_current_click(app);
        save_settings(app);
    }
    settings_section_end(y);
    settings_appearance_draw(app, x, w, y, state);
}

function draw_theme_settings(
    app: *InnerBreeze,
    section: SettingsSection,
    y: *s32,
    state: *SettingsThemeState
): s32 {
    let changed: s32 = 0n;
    let theme_options = NewThemeOptions();
    theme_options[0n].label = LocaleText("theme_system");
    {
        let i: s32 = 0n;
        while (i < ThemeCount) {
            theme_options[i + 1n].label = ThemeLabel(i);
            i = i + 1n;
        }
    }
    let theme_index =
        app.theme_source === s32(AppThemeSource.APP_THEME_SOURCE_SYSTEM) ? 0n : app.theme_id + 1n;
    if (theme_index < 0n || theme_index > ThemeCount) {
        theme_index = 1n;
    }
    let color_props: NativeDropdown.Props = {};
    color_props.id = 103n;
    color_props.bounds = settings_choice_row(
        app,
        section.inner_x,
        section.inner_width,
        y,
        LocaleText("theme_color_label")
    );
    color_props.selected_index = theme_index;
    let color_menu = (
        <Dropdown
            session={app.ui.session}
            props={color_props}
            options={theme_options[:]}
        />
    );
    if (color_menu.changed) {
        if (color_menu.selected_index === 0n) {
            app.theme_source = s32(AppThemeSource.APP_THEME_SOURCE_SYSTEM);
            app.theme_mode = s32(AppThemeMode.APP_THEME_SYSTEM);
        } else {
            app.theme_source = s32(AppThemeSource.APP_THEME_SOURCE_APP);
            app.theme_id = color_menu.selected_index - 1n;
        }
        changed = 1n;
    }
    settings_row_divider(app, section, (*y));
    // The dropdown paints after this function returns. Keep its formatted label in frame text.
    let follow_device_label = NewFollowDeviceLabel();
    let follow_args: [FormatArg, FormatArg] = [
        { text: LocaleText("theme_follow_device"), is_text: true },
        { text: LocaleText(app.dark_mode !== 0n ? "theme_dark" : "theme_light"), is_text: true }
    ];
    FormatTemplate(
        "%s (%s)",
        follow_args[:],
        follow_device_label[:]
    );
    let mode_options = NewModeOptions();
    mode_options[0n].label = FrameTextHold(
        &app.ui.frame_text,
        AppTextFromCString(&follow_device_label[0n], s32(follow_device_label.count))
    );
    mode_options[1n].label = LocaleText("theme_light");
    mode_options[2n].label = LocaleText("theme_dark");
    let mode_index = app.theme_mode;
    if (
        mode_index < s32(AppThemeMode.APP_THEME_SYSTEM) ||
        mode_index > s32(AppThemeMode.APP_THEME_DARK)
    ) {
        mode_index = s32(AppThemeMode.APP_THEME_SYSTEM);
    }
    let mode_props: NativeDropdown.Props = {};
    mode_props.id = 102n;
    mode_props.bounds = settings_choice_row(
        app,
        section.inner_x,
        section.inner_width,
        y,
        LocaleText("theme_mode_label")
    );
    mode_props.selected_index = mode_index;
    mode_props.disabled = app.theme_source === s32(AppThemeSource.APP_THEME_SOURCE_SYSTEM);
    let mode_menu = (
        <Dropdown
            session={app.ui.session}
            props={mode_props}
            options={mode_options[:]}
        />
    );
    if (mode_menu.changed) {
        app.theme_mode = mode_menu.selected_index;
        changed = 1n;
    }
    return changed;
}

function draw_scale_row(
    app: *InnerBreeze,
    x: s32,
    w: s32,
    y: *s32,
    state: *SettingsThemeState
): void {
    if (!state.scale_editing) {
        state.scale_preview = app.ui_scale_tenths;
    }
    let label = LocaleText("appearance_scale_label");
    let percentage = NewPercentage();
    let percentage_args: [FormatArg] = [{ number: state.scale_preview * 10n }];
    FormatTemplate(
        "%d%%",
        percentage_args[:],
        percentage[:]
    );
    let value = FrameTextHold(
        &app.ui.frame_text,
        AppTextFromCString(&percentage[0n], s32(percentage.count))
    );
    let value_width = AppScale(64n);
    let label_height = AppScale(22n);
    let label_width = w - value_width;
    let value_y = (*y) + AppScale(10n);
    let slider_y = (*y) + AppScale(38n);
    if (settings_theme_scale_stacked(w)) {
        label_width = w;
        label_height = settings_theme_scale_label_height(w);
        value_y = value_y + (label_height + AppScale(6n));
        slider_y = slider_y + (label_height + AppScale(6n));
    }
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x),
                y: float32((*y) + AppScale(10n)),
                width: float32(label_width),
                height: float32(label_height)
            },
            text: label,
            wrap: Wrap.TextWrapAuto
        }}
    />;
    <Text
        session={app.ui.session}
        props={{
            bounds: {
                x: float32(x + w - value_width),
                y: float32(value_y),
                width: float32(value_width),
                height: float32(AppScale(22n))
            },
            text: value,
            align: TextAlign.TextAlignEnd,
            wrap: Wrap.TextWrapNone
        }}
    />;
    let slider: NativeSlider.DiscreteSliderProps = {};
    slider.id = 140n;
    slider.bounds = {
        x: float32(x),
        y: float32(slider_y),
        width: float32(w),
        height: float32(AppScale(36n))
    };
    slider.semantic_label = label;
    slider.value = state.scale_preview;
    slider.min = 5n;
    slider.max = 25n;
    let result = <DiscreteSlider session={app.ui.session} props={slider} />;
    if (result.changed) {
        state.scale_preview = result.value;
        state.scale_editing = true;
    }
    // Keep the layout and hit targets fixed through the drag, including focus loss.
    let pointer = PointerSample(app.ui.session);
    if (state.scale_editing && !pointer.down) {
        state.scale_editing = false;
        app.ui_scale_tenths = state.scale_preview;
        app.settings_dirty = 1n;
        app_block_current_click(app);
        save_settings(app);
    }
    (*y) = (*y) + settings_theme_scale_row_height(w);
}

export function SettingsThemePickerModal(app: *InnerBreeze): void {
    let modal_w = AppScale(320n);
    let modal_h = AppScale(360n);
    let title = LocaleText("theme_picker_title");
    let frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("settings/theme-picker"),
        title: title,
        width: modal_w,
        height: modal_h,
        scale: MetricsScale(),
        has_right_action: true,
        right_label: LocaleText("close_button")
    });
    if (frame.dismissed || frame.right_clicked) {
        app_close_modal(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    const content = frame.layout.content;
    <Scroll
        session={CurrentApp().ui.session}
        props={{
            key: NativeLayout.KeyHash("inbe/screens/settings/settings_theme/scroll/1"),
            bounds: content,
            content_height: theme_picker_content_height(s32(content.width)),
            scroll_offset: app.theme_state.theme_picker_scroll
        }}
        children={(view: NativeScroll.ScrollResult): void => {
            SettingsThemePickerRows(app, view);
        }}
    />;
    End(app.ui.session);
}

function SettingsThemePickerRows(app: *InnerBreeze, view: NativeScroll.ScrollResult): void {
    app.theme_state.theme_picker_scroll = view.scroll_offset;
    const picker = view.content;
    if (draw_theme_picker(s32(picker.x), s32(picker.y), s32(picker.width), &app.theme_id) === 0n) {
        return;
    }
    if (app.theme_id < 0n) {
        app.theme_id = 0n;
    }
    if (app.theme_id >= ThemeCount) {
        app.theme_id = ThemeCount - 1n;
    }
    app.theme_source = s32(AppThemeSource.APP_THEME_SOURCE_APP);
    app_refresh_theme(app);
    app.settings_dirty = 1n;
    save_settings(app);
    app_close_modal(app);
}

function draw_theme_picker(
    x: s32,
    y: s32,
    w: s32,
    theme_id: *s32
): s32 {
    let selected: s32 = 0n;
    if (NativePresent(theme_id)) {
        selected = (*theme_id);
    }
    let changed: s32 = 0n;
    {
        let i: s32 = 0n;
        while (i < ThemeCount) {
            if (
                (
                    <Button
                        session={CurrentApp().ui.session}
                        props={{
                            id: s32(51000n) + i,
                            bounds: {
                                x: float32(x),
                                y: float32(y + i * AppScale(46n)),
                                width: float32(w),
                                height: float32(AppScale(40n))
                            },
                            label: ThemeLabel(i),
                            tone:
                                selected === i
                                    ? ButtonTone.ButtonToneAccent
                                    : ButtonTone.ButtonToneNeutral,
                            emphasis:
                                selected === i
                                    ? ButtonEmphasis.ButtonEmphasisFilled
                                    : ButtonEmphasis.ButtonEmphasisSoft
                        }}
                    />
                )
            ) {
                if (NativePresent(theme_id)) {
                    (*theme_id) = i;
                }
                changed = 1n;
            }
            i = i + 1n;
        }
    }
    return changed;
}

function AppIconPreview(icon: s32): string {
    return icon === 1n ? "assets/app/icon-ink-and-air.webp" : "assets/app/icon-sky-cradle.webp";
}

function SettingsAppIconRow(
    app: *InnerBreeze,
    section: SettingsSection,
    y: *s32,
    state: *SettingsThemeState
): void {
    SettingsAppIconLoad(state);
    const rowHeight = settings_theme_icon_row_height();
    const iconSize = AppScale(48n);
    const session = app.ui.session;
    if (
        (
            <Button
                session={session}
                props={{
                    id: 152n,
                    bounds: {
                        x: float32(section.inner_x),
                        y: float32((*y) + AppScale(6n)),
                        width: float32(section.inner_width),
                        height: float32(rowHeight - AppScale(12n))
                    },
                    label: LocaleText("app_icon_label"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                    disabled: app.modal.active !== 0n
                }}
            />
        )
    ) {
        SettingsAppIconOpen(app, state);
    }
    <Image
        session={session}
        props={{
            asset_path: AppIconPreview(state.app_icon),
            bounds: {
                x: float32(section.inner_x + AppScale(8n)),
                y: float32((*y) + (rowHeight - iconSize) / 2n),
                width: float32(iconSize),
                height: float32(iconSize)
            },
            fit: NativeImage.ImageFit.ImageFitContain
        }}
    />;
    (*y) = (*y) + rowHeight;
    settings_row_divider(app, section, (*y));
}

export function SettingsAppIconModal(app: *InnerBreeze): void {
    const state = &app.theme_state;
    const frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("settings/app-icon"),
        title: LocaleText("app_icon_label"),
        width: AppScale(360n),
        height: AppScale(300n),
        scale: MetricsScale(),
        has_right_action: true,
        right_label: LocaleText("close_button")
    });
    if (frame.dismissed || frame.right_clicked) {
        app_close_modal(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    const content = frame.layout.content;
    const contentX = s32(content.x);
    const contentY = s32(content.y);
    const contentWidth = s32(content.width);
    const gap = AppScale(12n);
    const choiceWidth = (contentWidth - gap) / 2n;
    const session = CurrentApp().ui.session;
    for (let icon: s32 = 0n; icon < 2n; icon += 1n) {
        const x = contentX + icon * (choiceWidth + gap);
        const name = LocaleText(icon === 0n ? "app_icon_sky_cradle" : "app_icon_ink_and_air");
        <Image
            session={session}
            props={{
                asset_path: AppIconPreview(icon),
                alt_text: name,
                bounds: {
                    x: float32(x),
                    y: float32(contentY),
                    width: float32(choiceWidth),
                    height: float32(AppScale(120n))
                },
                fit: NativeImage.ImageFit.ImageFitContain
            }}
        />;
        if (
            (
                <Button
                    session={session}
                    props={{
                        id: 153n + icon,
                        bounds: {
                            x: float32(x),
                            y: float32(contentY + AppScale(128n)),
                            width: float32(choiceWidth),
                            height: float32(AppScale(44n))
                        },
                        label: name,
                        tone:
                            state.app_icon === icon
                                ? ButtonTone.ButtonToneAccent
                                : ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }}
                />
            ) &&
            SettingsAppIconSelect(app, state, icon)
        ) {
            End(app.ui.session);
            app_close_modal(app);
            return;
        }
    }
    const message = LocaleText(state.app_icon_error !== 0n ? "app_icon_error" : "app_icon_hint");
    <Text
        session={session}
        props={{
            bounds: {
                x: float32(contentX),
                y: float32(contentY + AppScale(184n)),
                width: float32(contentWidth),
                height: float32(AppScale(30n))
            },
            text: message,
            wrap: Wrap.TextWrapNone,
            size: AppFitFontSize(message, contentWidth, AppSmallFontSize(), AppScale(8n))
        }}
    />;
    End(app.ui.session);
}
