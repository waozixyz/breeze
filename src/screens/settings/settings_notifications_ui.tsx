import { SettingsNotificationsNewDetail } from "settings_notifications";
import { SettingsNotificationsNewOptions } from "settings_notifications";
import { SettingsNotificationsNewTimeBytes } from "settings_notifications";
// Authored UI composition; native application state remains in settings_notifications.zi.
import * as NativeButton from "kryon/button";
import * as NativeDropdown from "kryon/dropdown";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeSpinbox from "kryon/spinbox";
import * as NativeText from "kryon/text";
import * as NativeToggle from "kryon/toggle";
import {
    PushConfigure,
    PushConfigureWith,
    PushDisable,
    PushRefresh,
    PushRegistered
} from "android_push";
import { practice_label } from "app_notifications";
import { save_settings } from "app_settings";
import { APP_PUSH_DISTRIBUTOR_MAX, APP_REMINDER_PRACTICE_COUNT, InnerBreeze } from "app_types";
import { AndroidPlatform } from "environment";
import { ButtonEmphasis, ButtonTone, ContentAlignment } from "kryon/control_props";
import { ImageFit } from "kryon/image_props";
import { TextAlign } from "kryon/text_align";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { Spinbox } from "kryon/tsx/spinbox";
import { Text } from "kryon/tsx/text";
import { Toggle } from "kryon/tsx/toggle";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppTextWidth, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import {
    SETTINGS_PUSH_ROW,
    settings_notifications_button_row_height,
    settings_notifications_close_picker,
    settings_notifications_entry_height,
    settings_notifications_entry_wide,
    settings_notifications_push_body,
    settings_notifications_remove_reminder
} from "settings_notifications";
import {
    settings_button_width,
    settings_section_end,
    toggle_switch_height,
    toggle_switch_width
} from "settings_ui";
import {
    settings_row_dividerView as settings_row_divider,
    settings_section_beginView as settings_section_begin
} from "settings_ui_ui";
import { AppTextFromCString, FormatArg, FormatTemplate, FrameTextHold } from "text_buffers";

export function settings_notifications_button_row(
    app: NativeRef<InnerBreeze>,
    id: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    label: string
): boolean {
    let button: NativeButton.Props = {};
    button.id = id;
    button.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y) + AppScale(10n)),
        width: float32(width),
        height: float32(AppScale(36n))
    };
    button.label = label;
    button.tone = ButtonTone.ButtonToneNeutral;
    button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    nativeDeref(y) = nativeDeref(y) + settings_notifications_button_row_height();
    return Button({ session: app.ui.session, props: button });
}

export function settings_notifications_draw_entry(
    app: NativeRef<InnerBreeze>,
    index: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): boolean {
    let reminder = nativeRef(nativeAt(app.reminders, index));
    let control_height = AppScale(36n);
    let gap = AppScale(12n);
    let remove_width = settings_button_width(LocaleText("remove_button"), AppScale(88n));
    let toggle_width = toggle_switch_width();
    let toggle_height = toggle_switch_height();
    let time_bytes = SettingsNotificationsNewTimeBytes();
    let hour = reminder.hour;
    if (hour < 0n) {
        hour = 0n;
    }
    if (hour > 23n) {
        hour = 23n;
    }
    nativeSet(time_bytes, 0n, u8(48n + hour / 10n));
    nativeSet(time_bytes, 1n, u8(48n + (hour % 10n)));
    nativeSet(time_bytes, 2n, u8(58n));
    nativeSet(time_bytes, 3n, u8(48n));
    nativeSet(time_bytes, 4n, u8(48n));
    nativeSet(time_bytes, 5n, u8(0n));
    let time_text = FrameTextHold(
        nativeRef(app.ui.frame_text),
        AppTextFromCString(nativeRef(nativeAt(time_bytes, 0n)), 6n)
    );
    let stepper_width =
        control_height * 2n + AppTextWidth(time_text, AppFontSize()) + AppScale(24n);
    let first_center = nativeDeref(y) + AppScale(28n);
    let toggle_x = x;
    let toggle_center = first_center;
    let menu_x = x + toggle_width + gap;
    let menu_width = width - toggle_width - stepper_width - remove_width - gap * 3n;
    let stepper_x = x + width - remove_width - gap - stepper_width;
    let stepper_center = first_center;
    if (!settings_notifications_entry_wide(width)) {
        menu_x = x;
        menu_width = width - remove_width - gap;
        toggle_center = first_center + AppScale(46n);
        stepper_x = x + width - stepper_width;
        stepper_center = toggle_center;
    }
    let enabled: NativeToggle.Props = {};
    enabled.id = s32(4010n) + index;
    enabled.bounds = {
        x: float32(toggle_x),
        y: float32(toggle_center - toggle_height / 2n),
        width: float32(toggle_width),
        height: float32(toggle_height)
    };
    enabled.label = practice_label(reminder.practice);
    enabled.value = reminder.enabled !== 0n;
    let toggle_result = Toggle({ session: app.ui.session, props: enabled });
    if (toggle_result.changed) {
        reminder.enabled = toggle_result.value ? 1n : 0n;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    let options = SettingsNotificationsNewOptions();
    for (let practice = s32(0); practice <= APP_REMINDER_PRACTICE_COUNT - 1n; practice += s32(1)) {
        nativeAt(options, practice).label = practice_label(s32(practice));
    }
    let menu: NativeDropdown.Props = {};
    menu.id = s32(400n) + index * 4n;
    menu.bounds = {
        x: float32(menu_x),
        y: float32(first_center - control_height / 2n),
        width: float32(menu_width),
        height: float32(control_height)
    };
    menu.selected_index = reminder.practice;
    let reminder_menu = Dropdown({
        session: app.ui.session,
        props: menu,
        options: nativeSlice(options)
    });
    if (reminder_menu.changed) {
        reminder.practice = reminder_menu.selected_index;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    let time: NativeSpinbox.Props = {};
    time.id = s32(401n) + index * 2n;
    time.bounds = {
        x: float32(stepper_x),
        y: float32(stepper_center - control_height / 2n),
        width: float32(stepper_width),
        height: float32(control_height)
    };
    time.label = practice_label(reminder.practice);
    time.min = 0n;
    time.max = 23n;
    time.value = reminder.hour;
    time.value_text = time_text;
    time.wrap = true;
    let time_result = Spinbox({ session: app.ui.session, props: time });
    if (time_result.changed) {
        reminder.hour = time_result.value;
        app.settings_dirty = 1n;
        save_settings(app);
    }
    let remove: NativeButton.Props = {};
    remove.id = s32(440n) + index;
    remove.bounds = {
        x: float32(x + width - remove_width),
        y: float32(first_center - control_height / 2n),
        width: float32(remove_width),
        height: float32(control_height)
    };
    remove.label = LocaleText("remove_button");
    remove.tone = ButtonTone.ButtonToneNeutral;
    remove.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    nativeDeref(y) = nativeDeref(y) + settings_notifications_entry_height(width);
    if (Button({ session: app.ui.session, props: remove })) {
        settings_notifications_remove_reminder(app, index);
        return true;
    }
    return false;
}

export function settings_notifications_push_row(
    app: NativeRef<InnerBreeze>,
    id: s32,
    label: string,
    detail: string,
    icon: string,
    x: s32,
    y: s32,
    width: s32
): boolean {
    let props: NativeButton.Props = {};
    props.id = id;
    props.key = u64(id);
    props.bounds = {
        x: float32(x),
        y: float32(y),
        width: float32(width),
        height: float32(AppScale(SETTINGS_PUSH_ROW))
    };
    props.label = label;
    props.detail = detail;
    props.content_alignment = ContentAlignment.ContentAlignmentStart;
    props.tone = ButtonTone.ButtonToneNeutral;
    props.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    if (icon.count > 0n) {
        props.image = {
            asset_path: icon,
            alt_text: label,
            fit: ImageFit.ImageFitContain,
            smooth: true
        };
    }
    return Button({ session: app.ui.session, props: props });
}

export function settings_notifications_handle_overlaysView(app: NativeRef<InnerBreeze>): void {
    if (!NativePresent(app) || AndroidPlatform() === 0n || app.push_picker_open === 0n) {
        return;
    }
    let count = app.push_distributor_count;
    if (count < 0n) {
        count = 0n;
    }
    if (count > APP_PUSH_DISTRIBUTOR_MAX) {
        count = APP_PUSH_DISTRIBUTOR_MAX;
    }
    let row = AppScale(SETTINGS_PUSH_ROW);
    let gap = AppScale(8n);
    let frame = NativeModal.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("notifications/push-picker"),
        id: 720n,
        title: LocaleText("notifications_push_picker_title"),
        strong_title: true,
        width: AppScale(440n),
        height: (count + 1n) * (row + gap) + AppScale(74n),
        scale: MetricsScale()
    });
    if (frame.dismissed) {
        settings_notifications_close_picker(app);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content = frame.layout.content;
    let x = s32(content.x);
    let width = s32(content.width);
    let y = s32(content.y);
    let index: s32 = s32(0n);
    while (index < count) {
        let label = AppTextFromCString(
            nativeRef(nativeAt(nativeAt(app.push_distributor_labels, index), 0n)),
            64n
        );
        let package = AppTextFromCString(
            nativeRef(nativeAt(nativeAt(app.push_distributors, index), 0n)),
            96n
        );
        let icon = AppTextFromCString(
            nativeRef(nativeAt(nativeAt(app.push_distributor_icons, index), 0n)),
            256n
        );
        let detail = SettingsNotificationsNewDetail();
        let named = false;
        for (const byte of package) {
            if (byte === u8(46n)) {
                named = true;
            }
        }
        if (named) {
            let args: [FormatArg] = [{ text: package, is_text: true }];
            FormatTemplate(
                LocaleText("notifications_push_uses_app"),
                nativeSlice(args),
                nativeSlice(detail)
            );
        }
        if (
            settings_notifications_push_row(
                app,
                7210n + index,
                label,
                FrameTextHold(
                    nativeRef(app.ui.frame_text),
                    AppTextFromCString(nativeRef(nativeAt(detail, 0n)), 160n)
                ),
                icon,
                x,
                y,
                width
            )
        ) {
            PushConfigureWith(app, index);
            settings_notifications_close_picker(app);
        }
        y = y + (row + gap);
        index = index + 1n;
    }
    if (
        settings_notifications_push_row(
            app,
            7219n,
            LocaleText("notifications_push_none"),
            LocaleText("notifications_push_none_detail"),
            "",
            x,
            y,
            width
        )
    ) {
        PushDisable();
        settings_notifications_close_picker(app);
    }
    End(app.ui.session);
}

export function settings_notifications_draw_push(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    if (AndroidPlatform() === 0n) {
        return;
    }
    let section = settings_section_begin(
        app,
        x,
        width,
        y,
        LocaleText("notifications_push_section"),
        settings_notifications_push_body()
    );
    let status: NativeText.Props = {};
    status.text = LocaleText("notifications_push_status_off");
    if (PushRegistered() !== 0n) {
        status.text = LocaleText("notifications_push_status_on");
    }
    status.size = AppFontSize();
    status.vertical_align = TextAlign.TextAlignCenter;
    status.bounds = {
        x: float32(section.inner_x),
        y: float32(nativeDeref(y)),
        width: float32(section.inner_width),
        height: float32(AppScale(44n))
    };
    <Text session={app.ui.session} props={status} />;
    nativeDeref(y) = nativeDeref(y) + AppScale(44n);
    settings_row_divider(app, section, nativeDeref(y));
    if (
        settings_notifications_button_row(
            app,
            730n,
            section.inner_x,
            section.inner_width,
            y,
            LocaleText("notifications_push_setup")
        )
    ) {
        PushRefresh(app);
        if (app.push_distributor_count > 0n) {
            app.push_picker_open = 1n;
        } else {
            PushConfigure();
        }
    }
    settings_section_end(y);
}
