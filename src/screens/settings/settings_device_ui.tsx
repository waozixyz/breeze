import { SettingsDeviceNewCloseOptions } from "settings_device";
import { SettingsDeviceNewStartupOptions } from "settings_device";
import { SettingsDeviceNewOrientationOptions } from "settings_device";
// Authored UI composition; native application state remains in settings_device.zi.
import * as NativeDropdown from "kryon/dropdown";
import { save_settings } from "app_settings";
import { AppOrientationMode, InnerBreeze } from "app_types";
import { app_desktop_set_fullscreen } from "device_preferences";
import { DesktopPlatform } from "environment";
import { Dropdown } from "kryon/tsx/dropdown";
import { LocaleText } from "locale";
import {
    settings_device_clamp,
    settings_device_display_body,
    settings_device_orientation_option_count,
    settings_device_window_body
} from "settings_device";
import { SettingsDeviceState } from "settings_types";
import { commit_toggle_row, settings_section_end, settings_section_inner_width } from "settings_ui";
import {
    settings_choice_rowView as settings_choice_row,
    settings_row_dividerView as settings_row_divider,
    settings_section_beginView as settings_section_begin
} from "settings_ui_ui";

export function settings_device_draw_display(
    app: *InnerBreeze,
    x: s32,
    width: s32,
    y: *s32,
    state: *SettingsDeviceState
): void {
    let desktop = DesktopPlatform() !== 0n;
    let inner = settings_section_inner_width(width);
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("settings_section_display"),
        settings_device_display_body(inner)
    );
    let orientation_count = settings_device_orientation_option_count();
    app.orientation_mode = settings_device_clamp(
        app.orientation_mode,
        s32(s32(AppOrientationMode.APP_ORIENTATION_SYSTEM)),
        orientation_count - 1n
    );
    let orientation_options = SettingsDeviceNewOrientationOptions();
    orientation_options[0n].label = LocaleText("orientation_system");
    orientation_options[1n].label = LocaleText("orientation_portrait");
    orientation_options[2n].label = LocaleText("orientation_landscape");
    orientation_options[3n].label = LocaleText("orientation_sensor");
    let orientation: NativeDropdown.Props = {};
    orientation.id = 103n;
    orientation.bounds = settings_choice_row(
        app,
        section.inner_x,
        section.inner_width,
        y,
        LocaleText("orientation_label")
    );
    orientation.selected_index = app.orientation_mode;
    let orientation_settings_menu = (
        <Dropdown
            session={app.ui.session}
            props={orientation}
            options={orientation_options[:orientation_count]}
        />
    );
    if (orientation_settings_menu.changed) {
        app.orientation_mode = orientation_settings_menu.selected_index;
        state.orientation_changed = 1n;
    }
    if (desktop) {
        settings_row_divider(app, section, (*y));
        let fullscreen = app.fullscreen_enabled;
        if (
            commit_toggle_row(
                app,
                section.inner_x,
                section.inner_width,
                y,
                LocaleText("fullscreen_label"),
                &fullscreen,
                0n
            ) !== 0n
        ) {
            app.fullscreen_enabled = fullscreen;
            app_desktop_set_fullscreen(app.fullscreen_enabled);
        }
        settings_row_divider(app, section, (*y));
        let keyboard = app.on_screen_keyboard_enabled;
        if (
            commit_toggle_row(
                app,
                section.inner_x,
                section.inner_width,
                y,
                LocaleText("on_screen_keyboard_label"),
                &keyboard,
                0n
            ) !== 0n
        ) {
            app.on_screen_keyboard_enabled = keyboard;
        }
    }
    settings_section_end(y);
}

export function settings_device_draw_window(
    app: *InnerBreeze,
    x: s32,
    width: s32,
    y: *s32
): void {
    let inner = settings_section_inner_width(width);
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("settings_section_window"),
        settings_device_window_body(inner)
    );
    let startup_options = SettingsDeviceNewStartupOptions();
    startup_options[0n].label = LocaleText("desktop_startup_mode_normal");
    startup_options[1n].label = LocaleText("desktop_startup_mode_minimized");
    let startup: NativeDropdown.Props = {};
    startup.id = 104n;
    startup.bounds = settings_choice_row(
        app,
        section.inner_x,
        section.inner_width,
        y,
        LocaleText("desktop_startup_mode_label")
    );
    startup.selected_index = app.desktop_startup_mode;
    let startup_settings_menu = (
        <Dropdown
            session={app.ui.session}
            props={startup}
            options={startup_options[:]}
        />
    );
    if (startup_settings_menu.changed) {
        app.desktop_startup_mode = startup_settings_menu.selected_index;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    settings_row_divider(app, section, (*y));
    let close_options = SettingsDeviceNewCloseOptions();
    close_options[0n].label = LocaleText("desktop_close_action_ask");
    close_options[1n].label = LocaleText("desktop_close_action_keep_running");
    close_options[2n].label = LocaleText("desktop_close_action_quit");
    let close: NativeDropdown.Props = {};
    close.id = 105n;
    close.bounds = settings_choice_row(
        app,
        section.inner_x,
        section.inner_width,
        y,
        LocaleText("desktop_close_action_label")
    );
    close.selected_index = app.desktop_close_action;
    let close_settings_menu = (
        <Dropdown
            session={app.ui.session}
            props={close}
            options={close_options[:]}
        />
    );
    if (close_settings_menu.changed) {
        app.desktop_close_action = close_settings_menu.selected_index;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    settings_section_end(y);
}
