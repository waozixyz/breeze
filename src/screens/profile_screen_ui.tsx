import { Scroll } from "kryon/tsx/scroll";
import { ProfileScreenNewOptions } from "profile_screen";
import { app_content_bottom_reserved } from "app_nav_state";
// Authored UI composition; native application state remains in profile_screen.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as NativeTitleBar from "kryon/title_bar";
import { app_block_current_click } from "app_modal_state";
import { app_auto_sync } from "app_sync";
import {
    CONTENT_MAX_W,
    InnerBreeze,
    PROFILE_TAB_COUNT,
    PROFILE_TAB_DATA,
    PROFILE_TAB_OVERVIEW,
    PROFILE_TAB_TELEGRAM,
    PROFILE_VIEW_DATA,
    PROFILE_VIEW_DEW,
    PROFILE_VIEW_HABITS,
    PROFILE_VIEW_MAIN,
    PROFILE_VIEW_SYNC_ACCOUNT
} from "app_types";
import { CurrentApp } from "current_app";
import { storage_database_damaged } from "database_backup";
import { EntityHostFrame, EntityHostRoute, EntityHostTitle } from "entity_host";
import { habits_move } from "habit_model";
import { HABIT_NAME_SIZE } from "habit_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Color, DarkenColor, LightenColor, StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { IconType, ImageForIcon } from "kryon/icon";
import { PaintRoundedFill } from "kryon/paint_queue";
import { Wrap } from "kryon/text_props";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Shape } from "kryon/tsx/shape";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { LocaleText } from "locale";
import {
    AppFontSize,
    AppScale,
    AppSmallFontSize,
    AppTextWidth,
    AppTitleBarHeight,
    GetPageSidePadding
} from "metrics";
import { NativeContext, NativePresent } from "native_flags";

import { ProfileDewDraw } from "profile_dew_ui";
import {
    profile_content_height,
    profile_draw_data,
    profile_draw_overview,
    profile_screen_back,
    profile_screen_handle_platform_import,
    profile_tab_title
} from "profile_screen";
import { settings_sync_account_draw_config } from "settings_sync_account_impl";
import { settings_telegram_draw } from "settings_telegram_ui";
import { AppTextFromCString, FrameTextRead, FrameTextSave } from "text_buffers";
import { PackageFree, PackageText } from "package_files";

export function profile_draw_hub_stat_card(
    x: s32,
    y: s32,
    w: s32,
    h: s32,
    icon_type: IconType,
    label: string,
    value: string,
    icon_color: Color
): void {
    let icon_box = AppScale(34n);
    let icon_size = AppScale(18n);
    let center_x = x + w / 2n;
    let icon_x = center_x - icon_box / 2n;
    let value_font = AppScale(22n);
    let label_font = AppSmallFontSize();
    let value_w = AppTextWidth(value, value_font);
    let label_w = AppTextWidth(label, label_font);
    <Box
        session={CurrentApp().ui.session}
        props={{
            bounds: { x: float32(x), y: float32(y), width: float32(w), height: float32(h) },
            fill: DarkenColor(StyleTokenColor("canvas"), 7n),
            radius: float32(AppScale(12n))
        }}
    />;
    <Box
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(icon_x),
                y: float32(y + AppScale(26n) - icon_box / 2n),
                width: float32(icon_box),
                height: float32(icon_box)
            },
            fill: LightenColor(icon_color, 12n),
            radius: float32(icon_box) / 2.0
        }}
    />;
    <Image
        session={CurrentApp().ui.session}
        props={ImageForIcon(
            s32(icon_type),
            {
                x: float32(icon_x + (icon_box - icon_size) / 2n),
                y: float32(y + AppScale(26n) - icon_size / 2n),
                width: float32(icon_size),
                height: float32(icon_size)
            },
            ""
        )}
    />;
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(center_x - label_w / 2n),
                y: float32(y + AppScale(54n)),
                width: 0n,
                height: 0n
            },
            text: label,
            wrap: Wrap.TextWrapNone
        }}
    />;
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(center_x - value_w / 2n),
                y: float32(y + AppScale(78n)),
                width: 0n,
                height: 0n
            },
            text: value,
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function profile_draw_stat_row(
    x: s32,
    w: s32,
    y: NativeRef<s32>,
    label: string,
    value: string
): void {
    let font = AppFontSize();
    let value_w: s32 = s32(0n);
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: { x: float32(x), y: float32(nativeDeref(y)), width: 0n, height: 0n },
            text: label,
            wrap: Wrap.TextWrapNone
        }}
    />;
    value_w = AppTextWidth(value, font);
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: {
                x: float32(x + w - value_w),
                y: float32(nativeDeref(y) - AppScale(2n)),
                width: 0n,
                height: 0n
            },
            text: value,
            wrap: Wrap.TextWrapNone
        }}
    />;
    nativeDeref(y) = nativeDeref(y) + AppScale(28n);
}

export function profile_draw_divider(x: s32, w: s32, y: s32): void {
    <Shape
        session={CurrentApp().ui.session}
        props={{
            start: { x: float32(x), y: float32(y) },
            end: { x: float32(x + w), y: float32(y) },
            color: DarkenColor(StyleTokenColor("canvas"), 28n)
        }}
    />;
}

export function profile_draw_fitted_text(
    text: string,
    x: s32,
    y: s32,
    max_w: s32,
    font: s32
): void {
    if (text.count === 0n || max_w <= 0n) {
        return;
    }
    <Text
        session={CurrentApp().ui.session}
        props={{
            bounds: { x: float32(x), y: float32(y), width: float32(max_w), height: 0.0 },
            size: font,
            text: text,
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function profile_draw_habits(
    app: NativeRef<InnerBreeze>,
    x: s32,
    w: s32,
    y: NativeRef<s32>
): void {
    let font = AppFontSize();
    let btn_h = AppScale(32n);
    let btn_w = AppScale(74n);
    let gap = AppScale(8n);
    let stack_rows = w < AppScale(260n);
    nativeDeref(y) = nativeDeref(y) + AppScale(16n);
    {
        let i: s32 = s32(0n);
        while (i < app.habits.count) {
            let row_y = nativeDeref(y);
            let controls_w = btn_w * 2n + gap;
            let name_w = stack_rows ? w : w - controls_w - gap;
            profile_draw_fitted_text(
                AppTextFromCString(
                    nativeRef(nativeAt(nativeAt(app.habits.items, i).name, 0n)),
                    HABIT_NAME_SIZE
                ),
                x,
                row_y + AppScale(7n),
                name_w,
                font
            );
            if (stack_rows) {
                row_y = row_y + AppScale(36n);
            }
            if (
                Button({
                    session: CurrentApp().ui.session,
                    props: {
                        bounds: {
                            x: float32(stack_rows ? x : x + w - btn_w * 2n - gap),
                            y: float32(row_y),
                            width: float32(btn_w),
                            height: float32(btn_h)
                        },
                        label: LocaleText("move_up_button"),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                        disabled: i === 0n
                    }
                })
            ) {
                if (habits_move(nativeRef(app.habits), i, i - 1n) !== 0n) {
                    app_auto_sync(app);
                }
                return;
            }
            if (
                Button({
                    session: CurrentApp().ui.session,
                    props: {
                        bounds: {
                            x: float32(stack_rows ? x + btn_w + gap : x + w - btn_w),
                            y: float32(row_y),
                            width: float32(btn_w),
                            height: float32(btn_h)
                        },
                        label: LocaleText("move_down_button"),
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                        disabled: i === app.habits.count - 1n
                    }
                })
            ) {
                if (habits_move(nativeRef(app.habits), i, i + 1n) !== 0n) {
                    app_auto_sync(app);
                }
                return;
            }
            nativeDeref(y) = nativeDeref(y) + (stack_rows ? AppScale(78n) : AppScale(46n));
            profile_draw_divider(x, w, nativeDeref(y) - AppScale(6n));
            i = i + 1n;
        }
    }
    if (app.habits.count <= 0n) {
        <Text
            session={CurrentApp().ui.session}
            props={{
                bounds: {
                    x: float32(x),
                    y: float32(nativeDeref(y)),
                    width: 0n,
                    height: 0n
                },
                text: LocaleText("habit_empty_title"),
                wrap: Wrap.TextWrapNone
            }}
        />;
    }
}

export function profile_screen_draw(app: NativeRef<InnerBreeze>): s32 {
    if (!NativePresent(app)) {
        return 0n;
    }
    let header_h = AppTitleBarHeight();
    let content_y = header_h + AppScale(8n);
    let view_width: s32 = app.ui.view_width;
    let content_h = app.ui.view_height - content_y - app_content_bottom_reserved(app);
    let content_x: s32 = s32(0n);
    let content_w: s32 = s32(0n);
    let page_content_h: s32 = s32(0n);
    let max_w = AppScale(CONTENT_MAX_W);
    let y: s32 = s32(0n);
    profile_screen_handle_platform_import(app);
    if (app.profile_tab < 0n || app.profile_tab >= PROFILE_TAB_COUNT) {
        app.profile_tab = PROFILE_TAB_OVERVIEW;
    }
    if (content_h < 0n) {
        content_h = 0n;
    }
    if (max_w > view_width - GetPageSidePadding() * 2n) {
        max_w = view_width - GetPageSidePadding() * 2n;
    }
    if (max_w < AppScale(320n)) {
        max_w = AppScale(320n);
    }
    let column = NativeLayout.CenteredColumnFor(view_width, max_w, GetPageSidePadding());
    content_x = column.x;
    content_w = column.width;
    let title_key = "tab_profile";
    if (app.profile_view === PROFILE_VIEW_DATA) {
        title_key = "profile_data";
    } else if (app.profile_view === PROFILE_VIEW_DEW) {
        title_key = "profile_dew_title";
    } else if (app.profile_view === PROFILE_VIEW_HABITS) {
        title_key = "profile_my_habits_title";
    }
    let title_range = FrameTextSave(
        nativeRef(app.ui.frame_text),
        app.profile_view === PROFILE_VIEW_MAIN && app.profile_tab !== PROFILE_TAB_OVERVIEW
            ? profile_tab_title(app.profile_tab)
            : LocaleText(title_key)
    );
    let shared =
        EntityHostRoute(app) &&
        EntityHostFrame(app, {
            x: 0.0,
            y: float32(content_y),
            width: float32(view_width),
            height: float32(content_h)
        });
    if (shared) {
        const fallback = PackageText(FrameTextRead(nativeRef(app.ui.frame_text), title_range), "");
        title_range = FrameTextSave(nativeRef(app.ui.frame_text), EntityHostTitle(fallback));
        PackageFree(fallback);
    }
    if (!shared) {
        let recovery =
            storage_database_damaged() !== 0n &&
            app.profile_view === PROFILE_VIEW_MAIN &&
            app.profile_tab === PROFILE_TAB_OVERVIEW;
        if (app.profile_view === PROFILE_VIEW_MAIN && app.profile_tab === PROFILE_TAB_OVERVIEW) {
            title_range = FrameTextSave(
                nativeRef(app.ui.frame_text),
                LocaleText(recovery ? "profile_data" : "profile_progress_title")
            );
        }
        page_content_h = profile_content_height(content_w, NativeContext(app));
        let scroll_1_bounds: Rectangle = {
            x: float32(0n),
            y: float32(content_y),
            width: float32(view_width),
            height: float32(content_h)
        };
        let scroll_1_key: u64 = NativeLayout.KeyHash("inbe/screens/profile_screen/scroll/1");
        let scroll_1_props: NativeScroll.Props = {};
        scroll_1_props.key = scroll_1_key;
        scroll_1_props.bounds = scroll_1_bounds;
        scroll_1_props.content_height = page_content_h;
        scroll_1_props.scroll_offset = app.profile_scroll;
        let scroll_1_result = Scroll({
            session: CurrentApp().ui.session,
            props: scroll_1_props,
            children: (scroll_1_result: NativeScroll.ScrollResult): void => {
                nativeDeref(app).profile_scroll = scroll_1_result.scroll_offset;
                let page: Rectangle = scroll_1_result.content;
                let y = s32(page.y) + AppScale(12n);
                if (recovery) {
                    profile_draw_data(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_view === PROFILE_VIEW_DEW) {
                    ProfileDewDraw(app, content_x, nativeRef(y), content_w);
                } else if (app.profile_view === PROFILE_VIEW_SYNC_ACCOUNT) {
                    settings_sync_account_draw_config(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_view === PROFILE_VIEW_DATA) {
                    profile_draw_data(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_view === PROFILE_VIEW_HABITS) {
                    profile_draw_habits(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_tab === PROFILE_TAB_OVERVIEW) {
                    profile_draw_overview(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_tab === PROFILE_TAB_DATA) {
                    profile_draw_data(app, content_x, content_w, nativeRef(y));
                } else if (app.profile_tab === PROFILE_TAB_TELEGRAM) {
                    settings_telegram_draw(app, content_x, content_w, nativeRef(y));
                } else {
                    settings_sync_account_draw_config(app, content_x, content_w, nativeRef(y));
                }
            }
        });
        if (!scroll_1_result.opened) {
            app.profile_scroll = scroll_1_result.scroll_offset;
        }
    }
    PaintRoundedFill(
        app.ui.session,
        -1n,
        { x: 0.0, y: 0.0, width: float32(view_width), height: float32(content_y) },
        0.0,
        4n,
        StyleTokenColor("canvas")
    );
    let clicked_leading = false;
    {
        let bar: NativeTitleBar.Props = {};
        bar.title = FrameTextRead(nativeRef(app.ui.frame_text), title_range);
        bar.height = header_h;
        bar.bounds = { x: 0.0, y: 0.0, width: float32(view_width), height: float32(header_h) };
        bar.has_leading_action = app.modal.active === 0n;
        bar.leading_label = LocaleText("back_button");
        let options = ProfileScreenNewOptions();
        let title_result = TitleBar({
            session: app.ui.session,
            props: bar,
            options: nativeSlice(options, 0n, 0n)
        });
        clicked_leading = title_result.clicked_leading;
    }
    if (clicked_leading) {
        app_block_current_click(app);
        profile_screen_back(app);
        return 1n;
    }
    return 0n;
}
