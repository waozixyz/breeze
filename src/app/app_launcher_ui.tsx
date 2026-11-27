import { AppLauncherNewSteps } from "app_launcher";
import { AppLauncherNewPinnedSlots } from "app_launcher";
import { AppLauncherNewMore } from "app_launcher";
import { AppLauncherNewPinned } from "app_launcher";
import { AppLauncherNewTyped } from "app_launcher";
import { AppLauncherNewMoreCatalog } from "app_launcher";
import { AppLauncherNewTitles } from "app_launcher";
import { AppLauncherNewItems } from "app_launcher";
import { AppLauncherNewSubtitle } from "app_launcher";
import { AppLauncherNewIdentity } from "app_launcher";
import { ActionModal } from "kryon/tsx/action_modal";
// Authored UI composition; native application state remains in app_launcher.zi.
import * as NativeButton from "kryon/button";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeOverlay from "kryon/overlay";
import * as NativeText from "kryon/text";
import * as NativeSharedLauncher from "apps/launcher";
import * as NativeEditIcon from "mingcute/mingcute_regular_edit";
import * as State_app_launcher from "app_launcher";
import * as State_app_launcher_pins from "app_launcher_pins";
import {
    LauncherLibraryMove,
    LauncherLibraryName,
    LauncherLibrarySort,
    LauncherScreenCards,
    app_launcher_update_drag
} from "app_launcher";
import {
    app_launcher_activate,
    app_launcher_close,
    app_launcher_install,
    app_launcher_is_favorite,
    app_launcher_open_pending,
    app_launcher_pins_changed
} from "app_launcher_state";
import { app_block_current_click } from "app_modal_state";
import {
    app_apply_nav_route,
    app_content_bottom_reserved,
    app_nav_desktop_rail_enabled,
    app_nav_profile_identity,
    app_nav_route_available,
    app_nav_route_label
} from "app_nav_state";
import { AppPropertiesHidden } from "app_properties";
import { save_settings } from "app_settings";
import { GuideOverlayProps, InnerBreeze } from "app_types";
import { app_nav_route_own_shape, app_nav_route_shape, bottom_nav_route_image } from "bottom_nav";
import { app_draw_favorites_dockView as app_draw_favorites_dock } from "bottom_nav_ui";
import { CssClass } from "css/Css";
import { ButtonEmphasis, ButtonTone, IconPlacement } from "kryon/control_props";
import { StyleTokenColor } from "kryon/drawing_props";
import { Rectangle, RectangleIntersection } from "kryon/geometry";
import { GridCellBounds, GridIndexAt, MeasureGrid } from "kryon/grid";
import { PointInBounds } from "kryon/input_protocol";
import { PaintRoundedFill, PaintRoundedOutline } from "kryon/paint_queue";
import { TextAlign } from "kryon/text_align";
import { TextHeight, TextWidth } from "kryon/text_measure";
import { Wrap } from "kryon/text_props";
import { End, TreePushScope, TreeRootBounds } from "kryon/tree";
import { PointerSample } from "kryon/tree_input";
import { Button } from "kryon/tsx/button";
import { DismissibleOverlay } from "kryon/tsx/overlay";
import { Text } from "kryon/tsx/text";
import {
    LauncherPlaceFavorite,
    LauncherRouteName,
    LauncherRoutes,
    LauncherToggleFavorite
} from "launcher_policy";
import { LocaleActiveCode, LocaleText } from "locale";
import { AppFontSize, AppScale, MetricsScale } from "metrics";
import { NativeContext } from "native_flags";
import {
    NodeAppCatalogIcon,
    NodeAppOfferCount,
    NodeAppOfferName,
    NodeAppOfferShown,
    NodeAppSlotFor,
    NodeAppTitle
} from "node_apps";
import { PackageAutomaticUnasked, PackageSetAutomatic } from "package_manager";
import { AppNavNodeSlot, AppNavRoute } from "route_types";
import { AppCopyText, AppTextFromCString, FrameTextHold } from "text_buffers";
import { SampleTextFieldInput, TextInputWriteClipboard } from "text_input_host";
import { ScreenAppSelection } from "types";
import { GuideOverlayStepFor } from "widgets";
import { GuideOverlayView as GuideOverlay } from "widgets_ui";

export function app_draw_launcherView(app: *InnerBreeze, dock_drawn: boolean): void {
    app.launcher_panel_node = -1n;
    if (!app.launcher_open || app.host_feature !== 0n) {
        return;
    }
    if (app.modal.active !== 0n) {
        app_launcher_close(app);
        return;
    }
    app_launcher_open_pending(app);
    if (!app.launcher_open) {
        return;
    }
    let pointer = PointerSample(app.ui.session);
    if (app.launcher_drag_key !== 0n) {
        if (app.launcher_drag_route < 0n) {
            let found = false;
            for (let offer = s32(0n); offer < NodeAppOfferCount(); offer += s32(1)) {
                if (
                    NodeAppOfferName(offer) ===
                    AppTextFromCString(&app.launcher_drag_name[0n], 25n)
                ) {
                    app.launcher_drag_route = -offer - 2n;
                    found = true;
                    break;
                }
            }
            if (!found) {
                app.launcher_drag_key = 0n;
                app.launcher_drag_moving = false;
            }
        }
        if (!pointer.down && !pointer.released) {
            app.launcher_drag_key = 0n;
            app.launcher_drag_moving = false;
        } else {
            app_launcher_update_drag(app, { x: pointer.x, y: pointer.y });
        }
    }
    let desktop = app_nav_desktop_rail_enabled(app) !== 0n;
    let panel: Rectangle = {
        x: 0.0,
        y: 0.0,
        width: float32(app.ui.view_width),
        height: float32(app.ui.view_height)
    };
    let overlay: NativeOverlay.Props = {};
    overlay.key = NativeLayout.KeyHash("inbe/apps/overlay");
    overlay.bounds = TreeRootBounds(app.ui.session);
    overlay.dismiss_disabled = app.breathing.screen === ScreenAppSelection;
    let result = <DismissibleOverlay session={app.ui.session} props={overlay} />;
    if (result.closed) {
        app_launcher_close(app);
        return;
    }
    if (result.panel_node < 0n || !TreePushScope(app.ui.session, result.panel_node)) {
        return;
    }
    app.launcher_panel_node = result.panel_node;
    PaintRoundedFill(
        app.ui.session,
        result.panel_node,
        panel,
        0.0,
        4n,
        StyleTokenColor("launcher-canvas")
    );
    let margin = AppScale(20n);
    let x = s32(panel.x) + margin;
    let width = s32(panel.width) - margin * 2n;
    let title_y = AppScale(24n);
    let compact_header = width < AppScale(500n);
    let identity = AppLauncherNewIdentity();
    let subtitle = AppLauncherNewSubtitle();
    app_nav_profile_identity(
        app,
        identity[:],
        identity.count,
        subtitle[:],
        subtitle.count
    );
    let account: NativeButton.Props = {};
    account.key = NativeLayout.KeyHash("inbe/apps/profile");
    account.id = 6792n;
    account.label = FrameTextHold(
        &app.ui.frame_text,
        AppTextFromCString(&identity[0n], s32(identity.count))
    );
    account.icon_shape = compact_header
        ? ""
        : app_nav_route_own_shape(s32(AppNavRoute.APP_NAV_ROUTE_PROFILE));
    account.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    account.bounds.height = float32(AppScale(44n));
    let profile_w = s32(NativeButton.ButtonMeasure(account).width);
    if (profile_w < AppScale(44n)) {
        profile_w = AppScale(44n);
    }
    let edit: NativeButton.Props = {};
    edit.key = NativeLayout.KeyHash("inbe/apps/edit");
    edit.label = LocaleText(app.launcher_editing ? "done_button" : "launcher_edit_apps");
    edit.icon_shape = NativeEditIcon.Shape;
    edit.icon_only = compact_header;
    edit.selected = app.launcher_editing;
    edit.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    edit.bounds.height = float32(AppScale(44n));
    let edit_w = s32(NativeButton.ButtonMeasure(edit).width);
    if (edit_w < AppScale(44n)) {
        edit_w = AppScale(44n);
    }
    let header_gap = AppScale(8n);
    let title: NativeText.Props = {};
    title.text = LocaleText("launcher_title");
    title.size = AppScale(28n);
    title.wrap = Wrap.TextWrapNone;
    title.class_name = CssClass("launcher-title");
    let title_w = TextWidth(app.ui.session, title);
    let controls_y = title_y;
    let profile_x = x + width - AppScale(52n) - edit_w - header_gap - profile_w;
    if (profile_x < x + title_w + header_gap) {
        controls_y = controls_y + AppScale(56n);
        profile_x = x;
    }
    let profile_max = width - edit_w - header_gap;
    let wrapped_account = profile_w > profile_max;
    let account_h = AppScale(44n);
    let account_text: NativeText.Props = {};
    if (wrapped_account) {
        profile_w = profile_max;
        account.icon_shape = "";
        account.icon_only = true;
        account_text.text = account.label;
        account_text.size = AppScale(16n);
        account_text.wrap = Wrap.TextWrapAnywhere;
        account_text.align = TextAlign.TextAlignCenter;
        account_text.vertical_align = TextAlign.TextAlignCenter;
        account_text.bounds.width = float32(profile_w - AppScale(24n));
        account_h = TextHeight(app.ui.session, account_text) + AppScale(20n);
        if (account_h < AppScale(44n)) {
            account_h = AppScale(44n);
        }
    }
    title.bounds = {
        x: float32(x),
        y: float32(title_y),
        width: float32(controls_y === title_y ? profile_x - x - header_gap : width - AppScale(52n)),
        height: float32(AppScale(40n))
    };
    <Text session={app.ui.session} props={title} />;
    account.bounds = {
        x: float32(profile_x),
        y: float32(controls_y),
        width: float32(profile_w),
        height: float32(account_h)
    };
    if ((<Button session={app.ui.session} props={account} />)) {
        app_launcher_activate(app, s32(AppNavRoute.APP_NAV_ROUTE_PROFILE));
        End(app.ui.session);
        return;
    }
    if (wrapped_account) {
        account_text.bounds.x = account.bounds.x + float32(AppScale(12n));
        account_text.bounds.y = account.bounds.y;
        account_text.bounds.height = account.bounds.height;
        <Text session={app.ui.session} props={account_text} />;
    }
    edit.bounds = {
        x: float32(profile_x + profile_w + header_gap),
        y: float32(controls_y),
        width: float32(edit_w),
        height: float32(AppScale(44n))
    };
    if ((<Button session={app.ui.session} props={edit} />)) {
        app.launcher_editing = !app.launcher_editing;
        app.launcher_drag_key = 0n;
        app.launcher_drag_moving = false;
        app_block_current_click(app);
    }
    let settings: NativeButton.Props = {};
    settings.key = NativeLayout.KeyHash("inbe/apps/settings");
    settings.label = LocaleText("settings_title");
    settings.icon_shape = app_nav_route_own_shape(s32(AppNavRoute.APP_NAV_ROUTE_SETTINGS));
    settings.icon_only = true;
    settings.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    settings.bounds = {
        x: float32(x + width - AppScale(44n)),
        y: float32(title_y),
        width: float32(AppScale(44n)),
        height: float32(AppScale(44n))
    };
    if ((<Button session={app.ui.session} props={settings} />)) {
        app_launcher_close(app);
        app_apply_nav_route(app, s32(AppNavRoute.APP_NAV_ROUTE_SETTINGS));
        End(app.ui.session);
        return;
    }
    let search_y = controls_y + account_h + AppScale(12n);
    State_app_launcher.launcher_screen.query = app.launcher_search;
    State_app_launcher.launcher_screen.cursor = app.launcher_search_cursor;
    State_app_launcher.launcher_screen.anchor = app.launcher_search_anchor;
    State_app_launcher.launcher_screen.scroll_x = app.launcher_search_scroll;
    State_app_launcher.launcher_screen.focused = app.launcher_search_focused;
    State_app_launcher.launcher_screen.grid = app.launcher_grid_view;
    State_app_launcher.launcher_screen.scroll = app.launcher_scroll;
    let items = AppLauncherNewItems();
    let titles = AppLauncherNewTitles();
    let routes = LauncherRoutes();
    let canonical: [string, string, string, string, string, string] = [
        "Diary",
        "Habits",
        "Lists",
        "Lumi",
        "Practice",
        "Leaderboard"
    ];
    let count: s32 = s32(0);
    for (let index = s32(0n); index < app.launcher_favorite_count; index += s32(1)) {
        if (
            !app.launcher_editing &&
            AppPropertiesHidden(LauncherRouteName(app.launcher_favorites[index]))
        ) {
            continue;
        }
        State_app_launcher.launcher_screen_routes[count] = app.launcher_favorites[index];
        count = count + 1n;
    }
    let more_catalog = AppLauncherNewMoreCatalog();
    let more_catalog_count: s32 = s32(0);
    for (const route of routes) {
        if (
            app_launcher_is_favorite(app, route) ||
            (AppNavNodeSlot(route) >= 0n && !app_nav_route_available(app, route))
        ) {
            continue;
        }
        if (!app.launcher_editing && AppPropertiesHidden(LauncherRouteName(route))) {
            continue;
        }
        more_catalog[more_catalog_count] = route;
        more_catalog_count = more_catalog_count + 1n;
    }
    for (let offer = s32(0n); offer < NodeAppOfferCount(); offer += s32(1)) {
        let name = NodeAppOfferName(offer);
        if (
            NodeAppOfferShown(offer) &&
            name !== "arcade" &&
            NodeAppSlotFor(name) < 0n &&
            (app.launcher_editing || !AppPropertiesHidden(name))
        ) {
            more_catalog[more_catalog_count] = -offer - 2n;
            more_catalog_count = more_catalog_count + 1n;
        }
    }
    LauncherLibrarySort(app, more_catalog[:more_catalog_count]);
    for (let index = s32(0n); index < more_catalog_count; index += s32(1)) {
        State_app_launcher.launcher_screen_routes[count] = more_catalog[index];
        count = count + 1n;
    }
    for (let index = s32(0n); index < count; index += s32(1)) {
        let route = State_app_launcher.launcher_screen_routes[index];
        let title =
            route >= 0n ? app_nav_route_label(route) : NodeAppTitle(LauncherLibraryName(route));
        AppCopyText(title, titles[index][:]);
        let search = LauncherLibraryName(route);
        for (let at = s32(0n); at <= 5n; at += s32(1)) {
            if (routes[at] === route) {
                search = canonical[at];
            }
        }
        items[index] = {
            title: AppTextFromCString(&titles[index][0n], 256n),
            search: search,
            favorite: route >= 0n && app_launcher_is_favorite(app, route)
        };
    }
    let bottom_dock = app_content_bottom_reserved(app);
    let status = "";
    if (State_app_launcher_pins.launcher_pin_status >= 0n) {
        let status_key =
            State_app_launcher_pins.launcher_pin_status === 2n
                ? "launcher_pin_added"
                : "launcher_pin_requested";
        if (State_app_launcher_pins.launcher_pin_status === 0n) {
            status_key = "launcher_pin_failed";
        }
        status = LocaleText(status_key);
    }
    let typed = AppLauncherNewTyped();
    let input = SampleTextFieldInput(true, typed[:]);
    let layout = NativeSharedLauncher.AppLauncherScreen(
        app.ui.session,
        &State_app_launcher.launcher_screen,
        {
            bounds: {
                x: float32(x),
                y: float32(search_y),
                width: float32(width),
                height: float32(app.ui.view_height - bottom_dock - AppScale(12n) - search_y)
            },
            scale: MetricsScale(),
            locale: LocaleActiveCode(),
            input: input,
            search_class: CssClass("launcher-search"),
            heading_class: CssClass("launcher-heading"),
            muted_class: CssClass("launcher-muted"),
            empty_favorites: true,
            status: status,
            context: NativeContext(app),
            cards: LauncherScreenCards
        },
        items[:count]
    );
    app.launcher_search = State_app_launcher.launcher_screen.query;
    app.launcher_search_cursor = State_app_launcher.launcher_screen.cursor;
    app.launcher_search_anchor = State_app_launcher.launcher_screen.anchor;
    app.launcher_search_scroll = State_app_launcher.launcher_screen.scroll_x;
    app.launcher_search_focused = State_app_launcher.launcher_screen.focused;
    app.launcher_scroll = State_app_launcher.launcher_screen.scroll;
    if (layout.clipboard_write) {
        TextInputWriteClipboard(AppTextFromCString(&layout.clipboard_text[0n], 128n));
    }
    if (layout.changed) {
        app.launcher_grid_view = State_app_launcher.launcher_screen.grid;
        app.launcher_drag_key = 0n;
        app.launcher_drag_moving = false;
        save_settings(app);
        app_block_current_click(app);
    }
    let pinned_count = State_app_launcher.launcher_screen.favorites;
    let more_count = State_app_launcher.launcher_screen.count - pinned_count;
    let pinned = AppLauncherNewPinned();
    let more = AppLauncherNewMore();
    for (let index = s32(0n); index < pinned_count; index += s32(1)) {
        pinned[index] =
            State_app_launcher.launcher_screen_routes[
                State_app_launcher.launcher_screen.visible[index]
            ];
    }
    for (let index = s32(0n); index < more_count; index += s32(1)) {
        more[index] =
            State_app_launcher.launcher_screen_routes[
                State_app_launcher.launcher_screen.visible[pinned_count + index]
            ];
    }
    let scrolled = layout.scrolled;
    let pinned_bounds = layout.favorites_bounds;
    let more_bounds = layout.library_bounds;
    let tile_height = layout.tile_height;
    let gap = layout.gap;
    let pinned_cells = MeasureGrid({
        columns: layout.columns,
        gap: gap,
        bounds: {
            x: pinned_bounds.x,
            y: pinned_bounds.y + float32(AppScale(36n)),
            width: pinned_bounds.width,
            height: 0.0
        }
    });
    let more_cells = MeasureGrid({
        columns: layout.columns,
        gap: gap,
        bounds: {
            x: more_bounds.x,
            y: more_bounds.y + float32(AppScale(36n)),
            width: more_bounds.width,
            height: 0.0
        }
    });
    let pinned_slots = AppLauncherNewPinnedSlots();
    for (let index = s32(0n); index < pinned_count; index += s32(1)) {
        pinned_slots[index] = GridCellBounds(pinned_cells, index, tile_height);
    }
    let query = AppTextFromCString(&app.launcher_search[0n], 128n);
    if (!dock_drawn) {
        app_draw_favorites_dock(app);
    }
    if (app.launcher_drag_key !== 0n && app.launcher_drag_moving) {
        let point = app.launcher_drag_pointer;
        let target = app.launcher_dock_drop_index;
        if (
            query.count === 0n &&
            scrolled.opened &&
            PointInBounds(point.x, point.y, scrolled.viewport) &&
            PointInBounds(point.x, point.y, pinned_bounds)
        ) {
            target = GridIndexAt(
                pinned_cells,
                point.x,
                point.y,
                tile_height,
                app.launcher_favorite_count
            );
            let highlight = pinned_bounds;
            if (target < pinned_count) {
                highlight = pinned_slots[target];
            }
            highlight = RectangleIntersection(highlight, scrolled.viewport);
            PaintRoundedOutline(
                app.ui.session,
                -1n,
                highlight,
                float32(AppScale(12n)),
                12n,
                float32(AppScale(2n)),
                StyleTokenColor("accent")
            );
        }
        if (app.launcher_drag_released) {
            if (target >= 0n) {
                if (
                    app.launcher_drag_route >= 0n &&
                    app_launcher_install(app, app.launcher_drag_route)
                ) {
                    app.launcher_favorite_count = LauncherPlaceFavorite(
                        app.launcher_favorites[:],
                        app.launcher_favorite_count,
                        app.launcher_drag_route,
                        target
                    );
                    app_launcher_pins_changed(app);
                }
            } else if (
                query.count === 0n &&
                scrolled.opened &&
                PointInBounds(point.x, point.y, scrolled.viewport) &&
                PointInBounds(point.x, point.y, more_bounds)
            ) {
                if (
                    app.launcher_drag_route >= 0n &&
                    app_launcher_is_favorite(app, app.launcher_drag_route)
                ) {
                    app.launcher_favorite_count = LauncherToggleFavorite(
                        app.launcher_favorites[:],
                        app.launcher_favorite_count,
                        app.launcher_drag_route
                    );
                    app_launcher_pins_changed(app);
                }
                target = GridIndexAt(more_cells, point.x, point.y, tile_height, more_count);
                LauncherLibraryMove(
                    app,
                    more[:more_count],
                    app.launcher_drag_route,
                    target
                );
            }
            app.launcher_drag_key = 0n;
            app.launcher_drag_moving = false;
            app_block_current_click(app);
        } else {
            if (scrolled.opened && PointInBounds(point.x, point.y, scrolled.viewport)) {
                let margin = float32(AppScale(32n));
                if (point.y < scrolled.viewport.y + margin) {
                    app.launcher_scroll = app.launcher_scroll - AppScale(8n);
                } else if (point.y > scrolled.viewport.y + scrolled.viewport.height - margin) {
                    app.launcher_scroll = app.launcher_scroll + AppScale(8n);
                }
                if (app.launcher_scroll < 0n) {
                    app.launcher_scroll = 0n;
                }
                if (app.launcher_scroll > scrolled.max_scroll) {
                    app.launcher_scroll = scrolled.max_scroll;
                }
            }
            let preview: NativeButton.Props = {};
            preview.id = 7290n;
            if (app.launcher_drag_route >= 0n) {
                preview.label = app_nav_route_label(app.launcher_drag_route);
                preview.image = bottom_nav_route_image(app.launcher_drag_route);
                preview.icon_shape = app_nav_route_shape(app.launcher_drag_route);
            } else {
                preview.label = NodeAppTitle(LauncherLibraryName(app.launcher_drag_route));
                preview.icon_shape = NodeAppCatalogIcon(
                    LauncherLibraryName(app.launcher_drag_route)
                );
            }
            preview.bounds = app.launcher_drag_bounds;
            preview.bounds.x = point.x - app.launcher_drag_grab.x;
            preview.bounds.y = point.y - app.launcher_drag_grab.y;
            preview.icon_placement = app.launcher_drag_vertical
                ? IconPlacement.IconPlacementAbove
                : IconPlacement.IconPlacementLeading;
            preview.class_name = CssClass("launcher-tile");
            preview.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
            preview.selected = true;
            preview.disabled = true;
            PaintRoundedFill(
                app.ui.session,
                -1n,
                preview.bounds,
                float32(AppScale(12n)),
                12n,
                StyleTokenColor("launcher-canvas")
            );
            <Button session={app.ui.session} props={preview} />;
        }
    } else if (app.launcher_drag_released) {
        app.launcher_drag_key = 0n;
    }
    End(app.ui.session);
    if (app.launcher_guide_seen === 0n) {
        let steps = AppLauncherNewSteps();
        steps[0n] = GuideOverlayStepFor(layout.search_bounds, "launcher_guide_find");
        let guide: GuideOverlayProps = {};
        guide.steps = &steps[0n];
        guide.count = 1n;
        app.launcher_guide_step = 0n;
        guide.step = &app.launcher_guide_step;
        guide.view_width = app.ui.view_width;
        guide.view_height = app.ui.view_height;
        guide.reserved_bottom = bottom_dock;
        guide.max_width = AppScale(320n);
        guide.paragraph_font = AppFontSize();
        guide.previous_requested = app.ui.manual_previous;
        guide.next_requested = app.ui.manual_next;
        guide.close_requested = app.ui.manual_close;
        let result = GuideOverlay(guide);
        if (result.finished !== 0n || result.closed !== 0n) {
            app.launcher_guide_seen = 1n;
            save_settings(app);
            app_block_current_click(app);
        }
    } else {
        app_launcher_ask_package_updates(app);
    }
}

export function app_launcher_ask_package_updates(app: *InnerBreeze): void {
    if (State_app_launcher.launcher_package_updates_closed || !PackageAutomaticUnasked()) {
        return;
    }
    let actions: [NativeModal.ActionModalAction, NativeModal.ActionModalAction] = [
        {
            label: LocaleText("package_updates_decline"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        },
        {
            label: LocaleText("package_updates_allow"),
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisSoft
        }
    ];
    let props: NativeModal.ActionModalProps = {};
    props.key = NativeLayout.KeyHash("inbe/apps/package-updates");
    props.title = LocaleText("package_updates_title");
    props.message = LocaleText("package_updates_message");
    props.max_width = 420n;
    let answer = (
        <ActionModal
            session={app.ui.session}
            props={props}
            actions={actions[:2n]}
        />
    ).action;
    if (answer === 0n) {
        return;
    }
    if (answer === 1n) {
        PackageSetAutomatic(false);
    } else if (answer === 2n) {
        PackageSetAutomatic(true);
    } else {
        State_app_launcher.launcher_package_updates_closed = true;
    }
    app_block_current_click(app);
}
