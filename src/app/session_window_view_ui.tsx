import { SessionWindowViewNewStatusText } from "session_window_view";
// Authored UI composition; native application state remains in session_window_view.zi.
import * as NativeButton from "kryon/button";
import * as NativeLayout from "kryon/layout";
import { InnerBreeze } from "app_types";
import { color_with_alpha } from "color";
import { CssClass } from "css/Css";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { StyleTokenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { PaintRoundedFill } from "kryon/paint_queue";
import { SessionValid } from "kryon/session";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { TreeCurrentParent, TreePrevious, TreeSetDragCapture, TreeSubmitted } from "kryon/tree";
import { TreeHoveredAt, TreeTakeDragAt } from "kryon/tree_input";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { WidgetKind } from "kryon/widget_kind";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppTextWidth } from "metrics";
import { NativePresent } from "native_flags";
import { practice_get, practice_label } from "practice_registry";
import { app_is_session_screen } from "session_screen";
import { app_session_window_restore } from "session_window";
import {
    SESSION_WINDOW_BREATHE_HEIGHT,
    SESSION_WINDOW_BREATHE_ID,
    SESSION_WINDOW_BREATHE_SPACE,
    SESSION_WINDOW_BUTTON_ROW,
    SESSION_WINDOW_CARD_ID,
    SESSION_WINDOW_CLOSE_ID,
    SESSION_WINDOW_GRIP,
    SESSION_WINDOW_HEIGHT,
    SESSION_WINDOW_MAXIMIZE_ID,
    SESSION_WINDOW_PADDING,
    SESSION_WINDOW_RESIZE_ID,
    SESSION_WINDOW_TEXT_HEIGHT,
    SESSION_WINDOW_WIDTH,
    app_session_window_close,
    session_window_breathe_tap,
    session_window_can_breathe,
    session_window_clamp,
    session_window_exit_prompt,
    session_window_fit_size,
    session_window_practice
} from "session_window_view";
import { FrameTextHold } from "text_buffers";
import { ScreenStart } from "types";

export function session_window_resize(app: NativeRef<InnerBreeze>, bounds: Rectangle): void {
    let session = app.ui.session;
    let window = nativeRef(app.session_window);
    let grip_size = float32(AppScale(SESSION_WINDOW_GRIP));
    let grip: NativeButton.Props = {};
    grip.id = SESSION_WINDOW_RESIZE_ID;
    grip.bounds = {
        x: bounds.x + bounds.width - grip_size,
        y: bounds.y + bounds.height - grip_size,
        width: grip_size,
        height: grip_size
    };
    grip.label = LocaleText("session_resize_button");
    grip.icon_only = true;
    grip.icon_shape = "S1.6rr:M19 13L13 19M19 7L7 19";
    grip.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    grip.class_name = CssClass("launcher-muted");
    let key = u64(grip.id);
    let previous = TreePrevious(
        session,
        TreeCurrentParent(session),
        key,
        s32(WidgetKind.WidgetKindButton)
    );
    let drag = TreeTakeDragAt(session, previous);
    if (drag.started) {
        window.resize_origin = { x: drag.x, y: drag.y };
        window.resize_start = window.size;
    }
    if (drag.active || drag.ended) {
        window.size = {
            x: window.resize_start.x + drag.x - window.resize_origin.x,
            y: window.resize_start.y + drag.y - window.resize_origin.y
        };
        session_window_fit_size(app);
        session_window_clamp(app);
    }
    <Button session={session} props={grip} />;
    let node = TreeSubmitted(
        session,
        TreeCurrentParent(session),
        key,
        s32(WidgetKind.WidgetKindButton)
    );
    TreeSetDragCapture(session, node, true);
}

export function session_window_breathe_button(
    app: NativeRef<InnerBreeze>,
    bounds: Rectangle
): boolean {
    let label = LocaleText("breath_button");
    let padding = float32(AppScale(SESSION_WINDOW_PADDING));
    let height = float32(AppScale(SESSION_WINDOW_BREATHE_HEIGHT));
    let width = float32(
        AppTextWidth(label, AppFontSize()) + AppScale(SESSION_WINDOW_BREATHE_SPACE)
    );
    if (width > bounds.width - padding * 2.0) {
        width = bounds.width - padding * 2.0;
    }
    let bottom = bounds.y + bounds.height - float32(AppScale(SESSION_WINDOW_TEXT_HEIGHT)) - padding;
    let button: NativeButton.Props = {};
    button.id = SESSION_WINDOW_BREATHE_ID;
    button.bounds = {
        x: bounds.x + (bounds.width - width) * 0.5,
        y: bottom - height,
        width: width,
        height: height
    };
    button.label = label;
    button.tone = ButtonTone.ButtonToneAccent;
    button.emphasis = ButtonEmphasis.ButtonEmphasisFilled;
    return Button({ session: app.ui.session, props: button });
}

export function app_session_window_draw(app: NativeRef<InnerBreeze>): void {
    if (
        !NativePresent(app) ||
        app.session_window.screen === ScreenStart ||
        app_is_session_screen(app.breathing.screen) ||
        !SessionValid(app.ui.session)
    ) {
        return;
    }
    if (app.session_window.detached) {
        session_window_exit_prompt(app);
        return;
    }
    let window = nativeRef(app.session_window);
    if (!window.placed) {
        window.size = {
            x: float32(AppScale(SESSION_WINDOW_WIDTH)),
            y: float32(AppScale(SESSION_WINDOW_HEIGHT))
        };
        window.position = {
            x: float32(app.ui.view_width) - window.size.x,
            y: float32(AppScale(72n))
        };
        window.placed = true;
    }
    session_window_fit_size(app);
    session_window_clamp(app);
    let width = window.size.x;
    let height = window.size.y;
    let bounds: Rectangle = {
        x: window.position.x,
        y: window.position.y,
        width: width,
        height: height
    };
    let session = app.ui.session;
    let radius = float32(AppScale(18n));
    let shadow: Rectangle = {
        x: bounds.x + float32(AppScale(2n)),
        y: bounds.y + float32(AppScale(6n)),
        width: width,
        height: height
    };
    PaintRoundedFill(session, -1n, shadow, radius, 14n, { r: 0n, g: 0n, b: 0n, a: 64n });
    <Box
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/session-window/card"),
            bounds: bounds,
            fill: StyleTokenColor("surface"),
            border: color_with_alpha(StyleTokenColor("accent"), float32(0.35)),
            radius: radius
        }}
    />;
    app_session_window_picture(
        app,
        window.screen,
        bounds,
        float32(AppScale(SESSION_WINDOW_BUTTON_ROW))
    );
    let name = practice_label(session_window_practice(window.screen));
    let card: NativeButton.Props = {};
    card.id = SESSION_WINDOW_CARD_ID;
    card.bounds = bounds;
    card.invisible = true;
    card.label = name;
    let key = u64(card.id);
    let previous = TreePrevious(
        session,
        TreeCurrentParent(session),
        key,
        s32(WidgetKind.WidgetKindButton)
    );
    let drag = TreeTakeDragAt(session, previous);
    if (drag.started) {
        window.drag_moved = false;
        window.drag_origin = { x: drag.x, y: drag.y };
        window.drag_start = window.position;
    }
    if (drag.active || drag.ended) {
        let dx = drag.x - window.drag_origin.x;
        let dy = drag.y - window.drag_origin.y;
        let threshold = float32(AppScale(6n));
        if (dx * dx + dy * dy >= threshold * threshold) {
            window.drag_moved = true;
        }
        if (window.drag_moved) {
            window.position = { x: window.drag_start.x + dx, y: window.drag_start.y + dy };
            session_window_clamp(app);
        }
    }
    let tapped = drag.ended && !window.drag_moved && TreeHoveredAt(session, previous);
    let activated = Button({ session: session, props: card }) || tapped;
    let node = TreeSubmitted(
        session,
        TreeCurrentParent(session),
        key,
        s32(WidgetKind.WidgetKindButton)
    );
    TreeSetDragCapture(session, node, true);
    session_window_resize(app, bounds);
    let button_size = float32(AppScale(36n));
    let maximize: NativeButton.Props = {};
    maximize.id = SESSION_WINDOW_MAXIMIZE_ID;
    maximize.bounds = {
        x: bounds.x + width - float32(AppScale(78n)),
        y: bounds.y + float32(AppScale(2n)),
        width: button_size,
        height: button_size
    };
    maximize.label = LocaleText("session_maximize_button");
    maximize.icon_only = true;
    maximize.icon_shape = "S1.8rr:M14 5H19V10M10 19H5V14M19 5L13 11M5 19L11 13";
    maximize.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    maximize.class_name = CssClass("launcher-action");
    let close: NativeButton.Props = {};
    close.id = SESSION_WINDOW_CLOSE_ID;
    close.bounds = {
        x: bounds.x + width - float32(AppScale(42n)),
        y: bounds.y + float32(AppScale(2n)),
        width: button_size,
        height: button_size
    };
    close.label = LocaleText("close_button");
    close.icon_only = true;
    close.icon_shape = "S1.8rr:M6 6L18 18M18 6L6 18";
    close.emphasis = ButtonEmphasis.ButtonEmphasisGhost;
    close.class_name = CssClass("launcher-action");
    if (Button({ session: session, props: maximize })) {
        app_session_window_restore(app);
        return;
    }
    if (Button({ session: session, props: close })) {
        app_session_window_close(app);
        return;
    }
    let practice = practice_get(session_window_practice(window.screen));
    let can_breathe = session_window_can_breathe(app, practice);
    let double_tap = can_breathe && app.double_tap_to_breathe !== 0n;
    if (!double_tap) {
        app.breath_tap_last_time = 0.0;
    }
    if (can_breathe && !double_tap && session_window_breathe_button(app, bounds)) {
        practice.breathe(app);
        return;
    }
    if (session_window_exit_prompt(app)) {
        return;
    }
    if (!activated || window.drag_moved) {
        return;
    }
    if (double_tap) {
        session_window_breathe_tap(app, practice);
        return;
    }
    app_session_window_restore(app);
}

export function app_session_window_picture(
    app: NativeRef<InnerBreeze>,
    screen: s32,
    bounds: Rectangle,
    button_row: float32
): void {
    let session = app.ui.session;
    let width = bounds.width;
    let height = bounds.height;
    let padding = float32(AppScale(SESSION_WINDOW_PADDING));
    let text_height = float32(AppScale(SESSION_WINDOW_TEXT_HEIGHT));
    let picture: Rectangle = {
        x: bounds.x + padding,
        y: bounds.y + button_row,
        width: width - padding * 2.0,
        height: height - button_row - text_height - padding
    };
    let practice = practice_get(session_window_practice(screen));
    let status_text = SessionWindowViewNewStatusText();
    nativeSet(status_text, 0n, 0n);
    let status: string = "";
    if (NativePresent(practice) && NativePresent(practice.draw_window)) {
        status = practice.draw_window(app, picture, nativeSlice(status_text));
    }
    let name = practice_label(session_window_practice(screen));
    let text_y = picture.y + picture.height + float32(AppScale(4n));
    <Text
        session={session}
        props={{
            key: NativeLayout.KeyHash("inbe/session-window/name"),
            bounds: {
                x: bounds.x + padding,
                y: text_y,
                width: width - padding * 2.0,
                height: float32(AppScale(20n))
            },
            text: FrameTextHold(nativeRef(app.ui.frame_text), name),
            size: AppScale(15n),
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignCenter
        }}
    />;
    if (status.count > 0n) {
        <Text
            session={session}
            props={{
                key: NativeLayout.KeyHash("inbe/session-window/status"),
                bounds: {
                    x: bounds.x + padding,
                    y: text_y + float32(AppScale(20n)),
                    width: width - padding * 2.0,
                    height: float32(AppScale(18n))
                },
                text: FrameTextHold(nativeRef(app.ui.frame_text), status),
                size: AppScale(13n),
                wrap: Wrap.TextWrapNone,
                align: TextAlign.TextAlignCenter,
                class_name: CssClass("launcher-muted")
            }}
        />;
    }
}
