import { BottomNavNewItems } from "bottom_nav";
import { BottomNavNewRoutes } from "bottom_nav";
// Authored UI composition; native application state remains in bottom_nav.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeNavigation from "kryon/navigation";
import { app_launcher_update_drag } from "app_launcher";
import {
    app_launcher_activate,
    app_launcher_open,
    app_launcher_pins_changed
} from "app_launcher_state";
import {
    app_dock_height,
    app_nav_desktop_rail_enabled,
    app_nav_desktop_rail_width,
    app_nav_route_available,
    app_nav_route_label,
    app_navigation_placement
} from "app_nav_state";
import { InnerBreeze, NavigationPlacement } from "app_types";
import { app_nav_route_shape, bottom_nav_route_active, bottom_nav_route_image } from "bottom_nav";
import { CssClass } from "css/Css";
import { StyleTokenColor } from "kryon/drawing_props";
import { PaintRoundedFill } from "kryon/paint_queue";
import { NavigationBar } from "kryon/tsx/navigation";
import { LauncherPlaceFavorite } from "launcher_policy";
import { AppScale } from "metrics";
import { app_return_bar_height } from "return_bar";
import { AppNavRoute } from "route_types";

export function app_draw_favorites_dockView(app: NativeRef<InnerBreeze>): void {
    let desktop = app_nav_desktop_rail_enabled(app) !== 0n;
    let dock_width = app_nav_desktop_rail_width(app);
    let props: NativeNavigation.Props = {};
    props.key = NativeLayout.KeyHash("inbe/apps/dock");
    props.id = 6600n;
    props.compact = true;
    props.fit_items = true;
    props.vertical = desktop;
    props.scale = float32(AppScale(100n)) / 100.0;
    props.item_class_name = CssClass("launcher-dock");
    props.class_name = props.item_class_name;
    props.scroll_offset = app.launcher_dock_scroll;
    props.draggable = app.launcher_open && app.launcher_editing;
    props.dragging = app.launcher_drag_moving;
    props.drag_position = app.launcher_drag_pointer;
    props.footer_count = 1n;
    let height = app_dock_height(app);
    props.bounds = {
        x: 0.0,
        y: float32(app.ui.view_height - height),
        width: float32(app.ui.view_width),
        height: float32(height)
    };
    if (app_navigation_placement(app) === s32(NavigationPlacement.NAVIGATION_TOP)) {
        props.bounds.y = -float32(height + app_return_bar_height(app));
    }
    if (desktop) {
        let x = -dock_width;
        if (app_navigation_placement(app) === s32(NavigationPlacement.NAVIGATION_RIGHT)) {
            x = app.ui.view_width;
        }
        let bar = app_return_bar_height(app);
        props.bounds = {
            x: float32(x),
            y: -float32(bar),
            width: float32(dock_width),
            height: float32(app.ui.view_height + bar)
        };
    }
    let routes = BottomNavNewRoutes();
    let count: s32 = s32(0n);
    for (let index = s32(0n); index < app.launcher_favorite_count; index += s32(1)) {
        let route = nativeAt(app.launcher_favorites, index);
        if (app_nav_route_available(app, route)) {
            nativeSet(routes, count, route);
            count = count + 1n;
        }
    }
    nativeSet(routes, count, s32(AppNavRoute.APP_NAV_ROUTE_APPS));
    count = count + 1n;
    if (desktop) {
        PaintRoundedFill(
            app.ui.session,
            -1n,
            props.bounds,
            0.0,
            4n,
            StyleTokenColor("launcher-canvas")
        );
    }
    let items = BottomNavNewItems();
    for (let index = s32(0n); index < count; index += s32(1)) {
        let route = nativeAt(routes, index);
        nativeAt(items, index).key = u64(6600n + route);
        nativeAt(items, index).route = route;
        nativeAt(items, index).label = app_nav_route_label(route);
        nativeAt(items, index).image = bottom_nav_route_image(route);
        nativeAt(items, index).icon_shape = app_nav_route_shape(route);
        nativeAt(items, index).active = !app.launcher_open && bottom_nav_route_active(app, route);
        nativeAt(items, index).disabled =
            app.modal.active !== 0n || app.blocked_input_frame === app.breathing.frame;
        if (route === s32(AppNavRoute.APP_NAV_ROUTE_APPS)) {
            nativeAt(items, index).active = app.launcher_open;
            nativeAt(items, index).image = {};
            nativeAt(items, index).icon_shape =
                "S1.6rr:M4 4H9V9H4ZM15 4H20V9H15ZM4 15H9V20H4ZM15 15H20V20H15Z";
        }
    }
    let result = NavigationBar({
        session: app.ui.session,
        props: props,
        items: nativeSlice(items, 0n, count)
    });
    app.launcher_dock_scroll = result.scroll_offset;
    app.launcher_dock_drop_index = result.drop_index;
    if (result.drag.started) {
        app.launcher_drag_key = u64(6600n + result.drag_route);
        app.launcher_drag_route = result.drag_route;
        app.launcher_drag_bounds = result.drag_bounds;
        app.launcher_drag_origin = { x: result.drag.x, y: result.drag.y };
        app.launcher_drag_grab = { x: result.drag.grab_x, y: result.drag.grab_y };
        app.launcher_drag_vertical = true;
        app.launcher_drag_moving = false;
    }
    if (result.drag.active || result.drag.ended) {
        app_launcher_update_drag(app, { x: result.drag.x, y: result.drag.y });
        app.launcher_drag_released = result.drag.ended;
    }
    if (result.clicked_route >= 0n && !app.launcher_drag_moving) {
        if (result.clicked_route === s32(AppNavRoute.APP_NAV_ROUTE_APPS)) {
            app_launcher_open(app);
        } else {
            app_launcher_activate(app, result.clicked_route);
        }
    }
    if (!app.launcher_open && app.launcher_drag_released) {
        if (app.launcher_drag_moving && result.drop_index >= 0n) {
            app.launcher_favorite_count = LauncherPlaceFavorite(
                nativeSlice(app.launcher_favorites),
                app.launcher_favorite_count,
                app.launcher_drag_route,
                result.drop_index
            );
            app_launcher_pins_changed(app);
        }
        app.launcher_drag_key = 0n;
        app.launcher_drag_moving = false;
        app.launcher_drag_released = false;
    }
}
