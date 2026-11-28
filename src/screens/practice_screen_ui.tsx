import { app_content_top_reserved } from "app_chrome";
import { app_content_bottom_reserved } from "app_nav_state";
// Authored UI composition; native application state remains in practice_screen.zi.
import * as NativeButton from "kryon/button";
import * as NativeLayout from "kryon/layout";
import * as NativeTitleBar from "kryon/title_bar";
import * as State_practice_screen from "practice_screen";
import { app_route_transition_request } from "app_frame_transition";
import { TraceLog } from "app_trace";
import { AppThemeMode, InnerBreeze } from "app_types";
import { CurrentApp } from "current_app";
import { ExerciseType } from "exercise_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle, RectangleIntersection } from "kryon/geometry";
import { IconType } from "kryon/icon";
import { ImageFit } from "kryon/image_props";
import { Session } from "kryon/session";
import { CurrentTheme } from "kryon/theme";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import { manual_screen_draw } from "manual_dispatch";
import { AppScale, AppTitleBarHeight } from "metrics";
import { ModalType } from "modal_rules";
import { NativePresent } from "native_flags";
import {
    PATTERNS_PHASE_EXHALE,
    PATTERNS_PHASE_HOLD_IN,
    PATTERNS_PHASE_INHALE
} from "patterns_rules";
import { PRACTICE_BANNER_HZ, PracticeBannerBoxAt } from "practice_banner_motion";
import { practice_get } from "practice_registry";
import {
    empty_title_options,
    practice_banner_color,
    practice_home_box_frame,
    practice_home_inside,
    practice_home_painting_height,
    practice_screen_leave_config,
    practice_screen_subscreen_integrated
} from "practice_screen";

import { PracticeHomeFrame } from "practice_ui_types";
import { PRACTICE_TAB_CONFIG, PRACTICE_TAB_MANUAL } from "route_types";
import { AppSetThemeMode } from "settings_actions";

export function practice_screen_handle_config_titleView(
    app: NativeRef<InnerBreeze>,
    title: string,
    modal_type: s32,
    has_leave_config: s32
): s32 {
    let title_h: s32 = s32(0n);
    if (!NativePresent(app)) {
        return 0n;
    }
    title_h =
        practice_screen_subscreen_integrated(app, modal_type) !== 0n
            ? app_content_top_reserved(app)
            : AppTitleBarHeight();
    let bar: NativeTitleBar.Props = {};
    bar.title = title;
    bar.height = title_h;
    bar.has_leading_action = true;
    bar.leading_label = LocaleText("back_button");
    let title_result = TitleBar({
        session: CurrentApp().ui.session,
        props: bar,
        options: empty_title_options()
    });
    if (!title_result.clicked_leading) {
        return 0n;
    }
    has_leave_config;
    practice_screen_leave_config(app, modal_type);
    return 1n;
}

export function practice_draw_card_banner(asset_path: string, dest: Rectangle): void {
    if (
        asset_path.count === 0n ||
        nativeAt(asset_path, 0n) === u8(0) ||
        dest.width <= 0n ||
        dest.height <= 0n
    ) {
        return;
    }
    let first_banner = State_practice_screen.practice_banner_probe_count === 0n;
    State_practice_screen.practice_banner_probe_count =
        State_practice_screen.practice_banner_probe_count + 1n;
    if (first_banner) {
        TraceLog(3n, "APP PROBE: before banner Image");
    }
    <Image
        session={CurrentApp().ui.session}
        props={{ asset_path: asset_path, bounds: dest, fit: ImageFit.ImageFitCover }}
    />;
    if (first_banner) {
        TraceLog(3n, "APP PROBE: after banner Image");
    }
}

export function practice_home_theme_button(
    app: NativeRef<InnerBreeze>,
    frame: PracticeHomeFrame
): boolean {
    if (frame.card.width <= 0.0 || frame.top <= 0n) {
        return false;
    }
    let width = float32(AppScale(44n));
    let height = float32(frame.top);
    let size = width < height ? width : height;
    let night = app.dark_mode !== 0n;
    let clicked = false;
    {
        let button: NativeButton.Props = {
            key: NativeLayout.KeyHash("practice/theme-mode"),
            bounds: {
                x: frame.card.x + frame.card.width - width - float32(AppScale(8n)),
                y: (height - size) * 0.5,
                width: width,
                height: size
            },
            label: LocaleText(night ? "theme_light" : "theme_dark"),
            icon_type: s32(night ? s32(IconType.IconSun) : s32(IconType.IconMoon)),
            icon_only: true,
            circle: true,
            disabled: !frame.choosing,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisGhost
        };
        clicked = Button({ session: app.ui.session, props: button });
    }
    if (!clicked) {
        return false;
    }
    if (!CurrentTheme().motion.reduced_motion) {
        app_route_transition_request(app);
    }
    return AppSetThemeMode(
        app,
        night ? s32(AppThemeMode.APP_THEME_LIGHT) : s32(AppThemeMode.APP_THEME_DARK)
    );
}

export function practice_home_box_line(
    session: Session,
    bounds: Rectangle,
    line: Rectangle,
    color: Color
): void {
    let shown = RectangleIntersection(bounds, line);
    if (shown.width > 0.0 && shown.height > 0.0) {
        <Box session={session} props={{ bounds: shown, fill: color }} />;
    }
}

export function practice_home_box_outline(
    session: Session,
    bounds: Rectangle,
    night: boolean
): void {
    let box = practice_home_box_frame(bounds, night);
    let art_h = practice_home_painting_height(bounds);
    let thickness = art_h * 0.006;
    if (thickness < 1.0) {
        thickness = 1.0;
    }
    let color = practice_banner_color(night ? 0xffbe66n : 0xfff0b4n, 235n);
    let half = thickness * 0.5;
    practice_home_box_line(
        session,
        bounds,
        { x: box.x, y: box.y - half, width: box.width, height: thickness },
        color
    );
    practice_home_box_line(
        session,
        bounds,
        { x: box.x, y: box.y + box.height - half, width: box.width, height: thickness },
        color
    );
    practice_home_box_line(
        session,
        bounds,
        { x: box.x - half, y: box.y, width: thickness, height: box.height },
        color
    );
    practice_home_box_line(
        session,
        bounds,
        { x: box.x + box.width - half, y: box.y, width: thickness, height: box.height },
        color
    );
    let radius = art_h * (night ? 0.016 : 0.027);
    let glow = radius * 1.8;
    for (let corner = s32(0); corner <= 3n; corner += s32(1)) {
        let x = corner === 1n || corner === 2n ? box.x + box.width : box.x;
        let y = corner >= 2n ? box.y + box.height : box.y;
        let halo: Rectangle = { x: x - glow, y: y - glow, width: glow * 2.0, height: glow * 2.0 };
        if (practice_home_inside(bounds, halo)) {
            <Box
                session={session}
                props={{
                    bounds: halo,
                    radius: glow,
                    fill: practice_banner_color(night ? 0xffc46cn : 0xfff3bcn, 70n)
                }}
            />;
            <Box
                session={session}
                props={{
                    bounds: {
                        x: x - radius,
                        y: y - radius,
                        width: radius * 2.0,
                        height: radius * 2.0
                    },
                    radius: radius,
                    fill: practice_banner_color(night ? 0xffdc94n : 0xfffbe2n)
                }}
            />;
        }
    }
}

export function practice_home_box_breath(
    session: Session,
    bounds: Rectangle,
    night: boolean,
    tick: s64
): void {
    if (tick <= 0n) {
        return;
    }
    let box = practice_home_box_frame(bounds, night);
    let x = box.x;
    let y = box.y;
    let size = practice_home_painting_height(bounds) * 0.023;
    let color = practice_banner_color(night ? 0xffdf92n : 0xfff9dcn);
    let timing = PracticeBannerBoxAt(((tick - 1n) * 1000n) / PRACTICE_BANNER_HZ);
    if (timing.phase === PATTERNS_PHASE_INHALE) {
        x = x + box.width * timing.progress;
    } else if (timing.phase === PATTERNS_PHASE_HOLD_IN) {
        x = x + box.width;
        y = y + box.height * timing.progress;
    } else if (timing.phase === PATTERNS_PHASE_EXHALE) {
        x = x + box.width * (1.0 - timing.progress);
        y = y + box.height;
    } else {
        y = y + box.height * (1.0 - timing.progress);
    }
    let marker: Rectangle = { x: x - size * 0.5, y: y - size * 0.5, width: size, height: size };
    if (practice_home_inside(bounds, marker)) {
        <Box
            session={session}
            props={{
                bounds: marker,
                fill: color,
                radius: size * 0.5,
                border: practice_banner_color(night ? 0x966d47n : 0xc28957n)
            }}
        />;
    }
}

export function practice_screen_draw_modal(app: NativeRef<InnerBreeze>): void {
    if (!NativePresent(app) || app.modal.active === 0n) {
        return;
    }
    if (
        app.modal.type !== ModalType.ModalPracticeManual &&
        app.modal.type !== ModalType.ModalPracticeConfig &&
        app.modal.type !== ModalType.ModalEditProgressiveStartSpeed
    ) {
        return;
    }
    if (
        app.modal.type === ModalType.ModalPracticeManual &&
        app.exercise_type === s32(ExerciseType.EXERCISE_ASTRAL_PROJECTION)
    ) {
        app.practice_tab = PRACTICE_TAB_MANUAL;
        manual_screen_draw(app);
        return;
    }
    <Box
        session={app.ui.session}
        props={{
            bounds: {
                x: 0.0,
                y: 0.0,
                width: float32(app.ui.view_width),
                height: float32(app.ui.view_height - app_content_bottom_reserved(app))
            },
            fill: StyleTokenColor("canvas")
        }}
    />;
    if (app.modal.type === ModalType.ModalEditProgressiveStartSpeed) {
        let practice = practice_get(app.exercise_type);
        if (NativePresent(practice.draw_config)) {
            practice.draw_config(app);
        }
        return;
    }
    if (app.modal.type === ModalType.ModalPracticeManual) {
        app.practice_tab = PRACTICE_TAB_MANUAL;
        manual_screen_draw(app);
    } else {
        let practice = practice_get(app.exercise_type);
        app.practice_tab = PRACTICE_TAB_CONFIG;
        if (NativePresent(practice.draw_config)) {
            practice.draw_config(app);
        }
    }
}
