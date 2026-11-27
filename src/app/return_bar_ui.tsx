// Authored UI composition; native application state remains in return_bar.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeCompressionIcon from "mingcute/mingcute_regular_tool";
import { app_block_current_click } from "app_modal_state";
import { InnerBreeze } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { ImageFit } from "kryon/image_props";
import { Button } from "kryon/tsx/button";
import { LocaleText } from "locale";
import { MediaCompressionRequest } from "media_compression_request";
import { AppScale } from "metrics";
import { NodeAppName } from "node_apps";
import {
    app_node_app_back,
    app_return_bar_height,
    app_return_bar_route,
    app_return_to_apps
} from "return_bar";
import { AppNavRoute } from "route_types";
import { ScreenNodeApp } from "types";

export function app_draw_return_barView(app: NativeRef<InnerBreeze>): void {
    let route = app_return_bar_route(app);
    if (route === s32(AppNavRoute.APP_NAV_ROUTE_NONE) || app.file_dialog_active !== 0n) {
        return;
    }
    let height = float32(app_return_bar_height(app));
    let control = float32(AppScale(44n));
    let inset = float32(AppScale(8n));
    let y = -height + (height - control) / 2.0;
    let label = LocaleText(
        app.breathing.screen === ScreenNodeApp ? "back_button" : "return_to_apps"
    );
    if (
        Button({
            session: app.ui.session,
            props: {
                key: NativeLayout.KeyHash("inbe/return-to-apps"),
                bounds: { x: inset, y: y, width: control, height: control },
                label: label,
                image: {
                    asset_path: "assets/app/back-home.avif",
                    alt_text: label,
                    fit: ImageFit.ImageFitContain,
                    smooth: true
                },
                icon_only: true,
                circle: true,
                disabled: app.modal.active !== 0n,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }
        }) &&
        !app_node_app_back(app)
    ) {
        app_return_to_apps(app);
    }
    let photos =
        app.breathing.screen === ScreenNodeApp && NodeAppName(app.node_app_slot) === "photos";
    if (photos) {
        if (
            Button({
                session: app.ui.session,
                props: {
                    key: NativeLayout.KeyHash("media/compression/settings"),
                    bounds: {
                        x: float32(app.ui.view_width) - inset - control,
                        y: y,
                        width: control,
                        height: control
                    },
                    label: LocaleText("media_compression_title"),
                    icon_shape: NativeCompressionIcon.Shape,
                    icon_only: true,
                    disabled: app.modal.active !== 0n,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost
                }
            })
        ) {
            app_block_current_click(app);
            MediaCompressionRequest();
        }
    }
}
