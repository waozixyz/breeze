import { SettingsScreenNewOptions } from "settings_screen";
// Authored UI composition; native application state remains in settings_screen.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeTitleBar from "kryon/title_bar";
import { app_block_current_click } from "app_modal_state";
import { app_content_bottom_reserved, app_settings_back } from "app_nav_state";
import {
    InnerBreeze,
    SETTINGS_TAB_AUDIO,
    SETTINGS_TAB_BREAKS,
    SETTINGS_TAB_DEVICE,
    SETTINGS_TAB_NOTIFICATIONS,
    SETTINGS_TAB_THEME
} from "app_types";
import { ButtonEmphasis, ButtonState } from "kryon/control_props";
import { DarkenColor, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { PaintRoundedFill } from "kryon/paint_queue";
import { StyleKindScroll, StyleKindScrollThumb } from "kryon/style_sheet";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import { AppScale, AppTitleBarHeight } from "metrics";
import { settings_about_draw } from "settings_about_ui";
import { settings_audio_draw } from "settings_audio";
import { settings_device_draw, settings_device_handle_overlays } from "settings_device";
import { settings_notifications_draw } from "settings_notifications";
import { settings_notifications_handle_overlaysView as settings_notifications_handle_overlays } from "settings_notifications_ui";
import {
    SettingsScreenBreaks,
    SettingsScreenRect,
    SettingsScreenTabAt,
    SettingsScreenTabCount,
    SettingsScreenTabProps,
    settings_screen_tab_label,
    settings_tab_content_height
} from "settings_screen";
import { settings_theme_draw } from "settings_theme_ui";
import { SettingsDeviceState } from "settings_types";

export function SettingsScreenPanel(
    app: NativeRef<InnerBreeze>,
    tab: s32,
    bounds: Rectangle
): void {
    if (bounds.width <= 0.0 || bounds.height <= 0.0) {
        return;
    }
    let padding = AppScale(bounds.width < 240.0 ? 8n : 16n);
    let column = NativeLayout.CenteredColumnFor(s32(bounds.width), AppScale(760n), padding);
    let content_height = settings_tab_content_height(app, tab, column.width) + AppScale(24n);
    let key = NativeLayout.KeyHash("inbe/settings/panel");
    let props: NativeScroll.Props = {};
    props.key = key;
    props.bounds = bounds;
    if (content_height > s32(bounds.height)) {
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
        props.metrics = NativeScroll.ScrollMetricsFor(1.0, track, thumb);
        let content = NativeScroll.ScrollContentBounds(bounds, true, props.metrics);
        column = NativeLayout.CenteredColumnFor(s32(content.width), AppScale(760n), padding);
        content_height = settings_tab_content_height(app, tab, column.width) + AppScale(24n);
    }
    props.content_height = content_height;
    props.scroll_offset = app.settings_scroll;
    let scrolled = NativeScroll.Draw(app.ui.session, props);
    app.settings_scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let x = s32(scrolled.content.x) + column.x;
    let width = column.width;
    let y = s32(scrolled.content.y) + AppScale(12n);
    let device_state: SettingsDeviceState = {};
    if (tab === SETTINGS_TAB_DEVICE) {
        settings_device_draw(app, x, width, nativeRef(y), nativeRef(device_state));
    } else if (tab === SETTINGS_TAB_AUDIO) {
        settings_audio_draw(app, x, width, nativeRef(y));
    } else if (tab === SETTINGS_TAB_BREAKS) {
        SettingsScreenBreaks(app, x, width, nativeRef(y));
    } else if (tab === SETTINGS_TAB_NOTIFICATIONS) {
        settings_notifications_draw(app, x, width, nativeRef(y));
    } else if (tab === SETTINGS_TAB_THEME) {
        settings_theme_draw(app, x, width, nativeRef(y), nativeRef(app.theme_state));
    } else {
        settings_about_draw(app, x, width, nativeRef(y));
    }
    End(app.ui.session);
    if (tab === SETTINGS_TAB_DEVICE) {
        settings_device_handle_overlays(app, nativeRef(device_state));
    } else if (tab === SETTINGS_TAB_NOTIFICATIONS) {
        settings_notifications_handle_overlays(app);
    }
}

export function SettingsScreenMobileHub(app: NativeRef<InnerBreeze>): void {
    let width = app.ui.view_width;
    let height = app.ui.view_height - app_content_bottom_reserved(app);
    let column = NativeLayout.CenteredColumnFor(width, AppScale(560n), AppScale(16n));
    let title_height = AppTitleBarHeight();
    let bar: NativeTitleBar.Props = {};
    bar.bounds = SettingsScreenRect(0n, 0n, width, title_height);
    bar.title = LocaleText("settings_title");
    bar.height = title_height;
    bar.has_leading_action = app.modal.active === 0n;
    bar.leading_label = LocaleText("back_button");
    let options = SettingsScreenNewOptions();
    let result = TitleBar({
        session: app.ui.session,
        props: bar,
        options: nativeSlice(options, 0n, 0n)
    });
    if (result.clicked_leading) {
        app_block_current_click(app);
        app_settings_back(app);
        return;
    }
    let top = title_height + AppScale(12n);
    let row_h = AppScale(52n);
    let content_height = SettingsScreenTabCount() * row_h + AppScale(12n);
    let viewport = SettingsScreenRect(column.x, top, column.width, height - top - AppScale(12n));
    let key = NativeLayout.KeyHash("inbe/settings/mobile-hub");
    let props: NativeScroll.Props = {};
    props.key = key;
    props.bounds = viewport;
    props.content_height = content_height;
    props.scroll_offset = app.settings_scroll;
    let scrolled = NativeScroll.Draw(app.ui.session, props);
    app.settings_scroll = scrolled.scroll_offset;
    if (!scrolled.opened) {
        return;
    }
    let y = s32(scrolled.content.y);
    let surface = DarkenColor(StyleTokenColor("canvas"), 5n);
    let divider = DarkenColor(StyleTokenColor("canvas"), 18n);
    let tabs_bounds = SettingsScreenRect(
        column.x,
        y,
        column.width,
        SettingsScreenTabCount() * row_h
    );
    PaintRoundedFill(app.ui.session, -1n, tabs_bounds, float32(AppScale(14n)), 12n, surface);
    let position: s32 = s32(0n);
    while (position < SettingsScreenTabCount()) {
        if (position > 0n) {
            PaintRoundedFill(
                app.ui.session,
                -1n,
                SettingsScreenRect(
                    column.x + AppScale(16n),
                    y,
                    column.width - AppScale(32n),
                    AppScale(1n)
                ),
                0.0,
                4n,
                divider
            );
        }
        let tab = SettingsScreenTabAt(position);
        let tab_props = SettingsScreenTabProps(
            app,
            tab,
            column.x,
            y,
            column.width,
            row_h,
            7510n + position
        );
        tab_props.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
        if (Button({ session: app.ui.session, props: tab_props })) {
            app.settings_tab = tab;
            app.settings_overview = 0n;
            app.settings_scroll = 0n;
        }
        y = y + row_h;
        position = position + 1n;
    }
    End(app.ui.session);
}

export function SettingsScreenDesktop(app: NativeRef<InnerBreeze>): void {
    let width = app.ui.view_width;
    let height = app.ui.view_height - app_content_bottom_reserved(app);
    let outer = AppScale(20n);
    let nav_width = AppScale(220n);
    let gap = AppScale(20n);
    if (width < AppScale(780n)) {
        nav_width = AppScale(170n);
        gap = AppScale(12n);
    }
    let title_height = AppTitleBarHeight();
    let bar: NativeTitleBar.Props = {};
    bar.bounds = SettingsScreenRect(0n, 0n, width, title_height);
    bar.title = LocaleText("settings_title");
    bar.height = title_height;
    bar.has_leading_action = app.modal.active === 0n;
    bar.leading_label = LocaleText("back_button");
    let options = SettingsScreenNewOptions();
    let result = TitleBar({
        session: app.ui.session,
        props: bar,
        options: nativeSlice(options, 0n, 0n)
    });
    if (result.clicked_leading) {
        app_block_current_click(app);
        app_settings_back(app);
        return;
    }
    let top = title_height + AppScale(12n);
    let nav_y = top;
    let position: s32 = s32(0n);
    while (position < SettingsScreenTabCount()) {
        let tab = SettingsScreenTabAt(position);
        let tab_props = SettingsScreenTabProps(
            app,
            tab,
            outer,
            nav_y,
            nav_width,
            AppScale(48n),
            7600n + position
        );
        if (!tab_props.selected) {
            tab_props.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
        }
        if (Button({ session: app.ui.session, props: tab_props })) {
            app.settings_tab = tab;
            app.settings_scroll = 0n;
        }
        nav_y = nav_y + AppScale(56n);
        position = position + 1n;
    }
    let panel_x = outer + nav_width + gap;
    let panel = SettingsScreenRect(panel_x, top, width - panel_x - outer, height - top - outer);
    SettingsScreenPanel(app, app.settings_tab, panel);
}

export function SettingsScreenMobileDetail(app: NativeRef<InnerBreeze>): void {
    let title = settings_screen_tab_label(app.settings_tab);
    let title_height = AppTitleBarHeight();
    let bar: NativeTitleBar.Props = {};
    bar.bounds = SettingsScreenRect(0n, 0n, app.ui.view_width, title_height);
    bar.title = title;
    bar.height = title_height;
    bar.has_leading_action = app.modal.active === 0n;
    bar.leading_label = LocaleText("back_button");
    let options = SettingsScreenNewOptions();
    let result = TitleBar({
        session: app.ui.session,
        props: bar,
        options: nativeSlice(options, 0n, 0n)
    });
    if (result.clicked_leading) {
        app_block_current_click(app);
        app_settings_back(app);
        return;
    }
    let top = title_height + AppScale(8n);
    let height = app.ui.view_height - top - app_content_bottom_reserved(app);
    SettingsScreenPanel(
        app,
        app.settings_tab,
        SettingsScreenRect(0n, top, app.ui.view_width, height)
    );
}
