// Authored UI composition; native application state remains in node_app_screen.zi.
import * as NativeLayout from "kryon/layout";
import { InnerBreeze } from "app_types";
import { app_nav_route_shape } from "bottom_nav";
import { HostSeconds } from "host_clock";
import { StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { Box } from "kryon/tsx/box";
import { LoadingScreen } from "kryon/tsx/loading_screen";
import { LocaleText } from "locale";
import { MetricsScale } from "metrics";
import { PackageText, PackageFree } from "package_files";
import { app_main_tab_route } from "navigation_routes";
import { NodeScreenPictures } from "node_app_screen";
import { NODE_APP_GENERIC_ICON, NodeAppIconShape, NodeAppName, NodeAppTitle } from "node_apps";
import { AppRequestSmoothFrames } from "smooth_frames";
import { ScreenNodeApp } from "types";
import { FrameTextHold } from "text_buffers";

export function NodeScreenProgress(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    title: string,
    stage: string,
    done: s32,
    total: s32,
    known_progress: boolean = false
): void {
    let route = app_main_tab_route(app.main_tab);
    let shape =
        app.breathing.screen === ScreenNodeApp
            ? NodeAppIconShape(app.node_app_slot)
            : app_nav_route_shape(route);
    if (shape.count === 0n) {
        shape = NODE_APP_GENERIC_ICON;
    }
    <LoadingScreen
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("inbe/app/loading"),
            bounds: area,
            title: title,
            detail: stage,
            icon_shape: shape,
            now: HostSeconds(),
            scale: MetricsScale(),
            has_progress: known_progress && total > 0n,
            completed: done,
            total: total
        }}
    />;
    AppRequestSmoothFrames(2n);
}

export function NodeScreenCover(
    app: NativeRef<InnerBreeze>,
    area: Rectangle,
    pictures: NodeScreenPictures
): void {
    <Box
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("inbe/node-app/cover"),
            bounds: area,
            fill: StyleTokenColor("canvas")
        }}
    />;
    let title = PackageText(NodeAppTitle(NodeAppName(app.node_app_slot)), "");
    NodeScreenProgress(
        app,
        area,
        title,
        FrameTextHold(nativeRef(app.ui.frame_text), LocaleText("app_loading_pictures")),
        pictures.ready,
        pictures.total,
        true
    );
    PackageFree(title);
}
