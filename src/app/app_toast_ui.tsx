// Authored UI composition; native application state remains in app_toast.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeToast from "kryon/toast";
import * as State_app_toast from "app_toast";
import { InnerBreeze } from "app_types";
import { GetDPIScale } from "dpi_state";
import { HostSeconds } from "host_clock";
import { Rectangle } from "kryon/geometry";
import { SessionValid } from "kryon/session";
import { Toast } from "kryon/tsx/toast";
import { NativePresent } from "native_flags";
import { AppNotificationToastSeconds } from "notification_presentation";

export function AppToastDraw(app: NativeRef<InnerBreeze>, viewport: Rectangle): void {
    if (!NativePresent(app) || !SessionValid(app.ui.session)) {
        return;
    }
    if (!State_app_toast.app_toast_active && !State_app_toast.app_toast_pending) {
        return;
    }
    let props: NativeToast.Props = {};
    props.key = NativeLayout.KeyHash("inbe/app/toast");
    props.viewport = viewport;
    props.state.until_seconds = State_app_toast.app_toast_until_seconds;
    if (State_app_toast.app_toast_active) {
        props.state.message = State_app_toast.AppToastMessage();
    }
    if (State_app_toast.app_toast_pending) {
        props.message = State_app_toast.AppToastMessage();
    }
    props.seconds = AppNotificationToastSeconds;
    props.now_seconds = HostSeconds();
    props.scale = GetDPIScale();
    const result: NativeToast.ToastResult = Toast({ session: app.ui.session, props: props });
    State_app_toast.app_toast_active = result.state.message.count > 0n;
    State_app_toast.app_toast_until_seconds = result.state.until_seconds;
    State_app_toast.app_toast_pending = false;
}
