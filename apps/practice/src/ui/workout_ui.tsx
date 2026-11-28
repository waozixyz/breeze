import { ResolvedModal } from "kryon/tsx/modal";
import * as Layout from "kryon/layout";
import * as NativeDropdown from "kryon/dropdown";
import * as NativeModal from "kryon/modal";
import * as NativeText from "kryon/text";
import { Rectangle } from "kryon/geometry";
import { StyleTokenColor } from "kryon/drawing_props";
import { TextAlign } from "kryon/text_align";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { InnerBreeze } from "app_types";
import { ExerciseType } from "exercise_types";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, MetricsScale } from "metrics";
import { PracticeContentReady } from "practice_downloads";
import { PracticeFigurePrepare } from "practice_figure_draw";
import { PracticeSubscreenLayout } from "practice_subscreen_layout";
import { WorkoutBuilderDraw } from "workout_builder";
import { WORKOUT_ROUTINE_CUSTOM } from "workout_sequence";
import {
    WorkoutChooseCharacter,
    WorkoutConfigBack,
    WorkoutManagerBack,
    WorkoutManagerPlay,
    WorkoutPreviewFigure,
    WorkoutTitle
} from "workout";

export function WorkoutConfigView(
    app: NativeRef<InnerBreeze>,
    layout: PracticeSubscreenLayout
): void {
    let options: [NativeDropdown.Option] = [{}];
    const bar = TitleBar({
        session: app.ui.session,
        props: {
            title: LocaleText("practice_configure_button"),
            height: layout.title_h,
            has_leading_action: true,
            leading_label: LocaleText("back_button")
        },
        options: nativeSlice(options, 0n, 0n)
    });
    if (bar.clicked_leading) {
        WorkoutConfigBack(app);
        return;
    }
    let width = app.ui.view_width - Layout.PageSidePaddingFor(app.ui.view_width) * 2n;
    if (width > AppScale(308n)) {
        width = AppScale(308n);
    }
    let height = (width * 2n) / 3n;
    if (height > AppScale(188n)) {
        height = AppScale(188n);
    }
    if (height > layout.scroll_h) {
        height = layout.scroll_h;
    }
    if (width <= 0n || height < AppScale(44n)) {
        return;
    }
    WorkoutCharacterCards(app, {
        x: float32((app.ui.view_width - width) / 2n),
        y: float32(layout.scroll_y + (layout.scroll_h - height) / 2n),
        width: float32(width),
        height: float32(height)
    });
}

export function WorkoutManagerView(app: NativeRef<InnerBreeze>): void {
    let height = app.ui.view_height - AppScale(32n);
    if (height > AppScale(660n)) {
        height = AppScale(660n);
    }
    // The editor lays out its scroll scope in the resolved modal content rectangle.
    const frame = ResolvedModal({
        session: app.ui.session,
        props: {
            id: 28900n,
            title: WorkoutTitle(WORKOUT_ROUTINE_CUSTOM),
            width: AppScale(500n),
            height: height,
            scale: MetricsScale(),
            has_left_action: true,
            left_label: LocaleText("back_button"),
            strong_title: true
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            const action = WorkoutBuilderDraw(
                app,
                frame.layout.content,
                PracticeContentReady(s32(ExerciseType.EXERCISE_WORKOUT))
            );
            WorkoutManagerPlay(app, action);
        }
    });
    if (frame.left_clicked || frame.dismissed) {
        WorkoutManagerBack(app);
        return;
    }
}

export function WorkoutCharacterCards(app: NativeRef<InnerBreeze>, area: Rectangle): void {
    const labelHeight = float32(AppScale(32n));
    const gap = float32(AppScale(6n));
    const column = (area.width - gap) / 2.0;
    const key = Layout.KeyHash("workout/customize/character");
    PracticeFigurePrepare(app.workout_character === 1n);
    for (let character: s32 = s32(0n); character <= 1n; character += 1n) {
        const label = LocaleText(
            character === 1n ? "workout_character_man" : "workout_character_woman"
        );
        const x = area.x + float32(character) * (column + gap);
        const selected = app.workout_character === character;
        const bounds: Rectangle = { x: x, y: area.y, width: column, height: area.height };
        <Box
            session={app.ui.session}
            props={{
                key: key + u64(8n + character),
                bounds: bounds,
                fill: StyleTokenColor("surface"),
                radius: float32(AppScale(12n)),
                border: StyleTokenColor(selected ? "accent" : "surface")
            }}
        />;
        const clicked = Button({
            session: app.ui.session,
            props: {
                key: key + u64(character),
                id: 28910n + character,
                bounds: bounds,
                label: label,
                invisible: true,
                selected: selected
            }
        });
        if (clicked && !selected) {
            WorkoutChooseCharacter(app, character);
        }
        const figureHeight = area.height - labelHeight - gap * 2.0;
        const figureWidth = column - gap * 2.0;
        if (figureHeight > 0.0 && figureWidth > 0.0) {
            WorkoutPreviewFigure(
                app,
                {
                    x: x + (column - figureWidth) / 2.0,
                    y: area.y + gap,
                    width: figureWidth,
                    height: figureHeight
                },
                character,
                key + u64(4n + character),
                label
            );
        }
        let strong: [NativeText.Range] = [{ start: 0n, end: s32(label.count) }];
        <Text
            session={app.ui.session}
            props={{
                bounds: {
                    x: x,
                    y: area.y + area.height - labelHeight,
                    width: column,
                    height: labelHeight
                },
                text: label,
                size: AppFontSize(),
                strong: nativeSlice(strong, 0n, selected ? 1n : 0n),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter
            }}
        />;
    }
}
