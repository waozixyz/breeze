import { app_content_bottom_reserved } from "app_nav_state";
// Authored UI composition; native application state remains in lumi_screen.zi.
import * as NativeLayout from "kryon/layout";
import * as State_lumi_screen from "lumi_screen";
import { app_nav_route_label } from "app_nav_state";
import { InnerBreeze } from "app_types";
import { AssetRead } from "assets";
import { HostSeconds } from "host_clock";
import { Rectangle } from "kryon/geometry";
import { LoadingScreen } from "kryon/tsx/loading_screen";
import { LocaleText } from "locale";
import { MetricsScale } from "metrics";

import { AppNavRoute } from "route_types";
import { AppRequestSmoothFrames } from "smooth_frames";

export function LumiDrawLoading(app: *InnerBreeze): void {
    let area: Rectangle = {
        x: 0.0,
        y: 0.0,
        width: float32(app.ui.view_width),
        height: float32(app.ui.view_height - app_content_bottom_reserved(app))
    };
    <LoadingScreen
        session={app.ui.session}
        props={{
            key: NativeLayout.KeyHash("inbe/lumi/loading"),
            bounds: area,
            title: app_nav_route_label(s32(AppNavRoute.APP_NAV_ROUTE_LUMI)),
            detail: LocaleText("lumi_loading"),
            icon_shape: AssetRead("assets/lumi/sidebar.shape").data,
            now: HostSeconds(),
            scale: MetricsScale(),
            has_progress: State_lumi_screen.lumi_ui.chat_count > 0n,
            completed: State_lumi_screen.lumi_rows_measured,
            total: State_lumi_screen.lumi_ui.chat_count
        }}
    />;
    AppRequestSmoothFrames(2n);
}
