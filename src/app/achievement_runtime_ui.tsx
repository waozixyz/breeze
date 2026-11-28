import { AchievementToast, AchievementToastClose } from "entity/achievement_toast";
import { Toast } from "entity/achievement_toast_ui";
import { InnerBreeze } from "app_types";
import { HostSeconds } from "host_clock";
import { DarkenColor, StyleTokenColor } from "kryon/drawing_props";
import { AppTitleBarHeight, MetricsScale } from "metrics";
import { AppNotificationToastSeconds } from "notification_presentation";

export function AchievementRuntimeToast(
    app: NativeRef<InnerBreeze>,
    toast: NativeRef<AchievementToast>
): void {
    const result = Toast(app.ui.session, toast, {
        key: u64(0x61636869657665n),
        viewport: {
            x: float32(0),
            y: float32(0),
            width: float32(app.ui.view_width),
            height: float32(app.ui.view_height)
        },
        top: float32(AppTitleBarHeight()),
        scale: MetricsScale(),
        now: HostSeconds(),
        seconds: AppNotificationToastSeconds,
        plain: true,
        fill: StyleTokenColor("surface"),
        border: DarkenColor(StyleTokenColor("canvas"), 18n),
        accent: StyleTokenColor("accent")
    });
    if (result.close) {
        AchievementToastClose(toast);
    }
}
