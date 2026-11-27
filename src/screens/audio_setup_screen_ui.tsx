import { AudioSetupScreenNewSizeBuffer } from "audio_setup_screen";
// Authored UI composition; native application state remains in audio_setup_screen.zi.
import * as NativeLayout from "kryon/layout";
import { InnerBreeze } from "app_types";
import { AudioSetupBytes, AudioSetupFinish } from "audio_setup";
import { AudioSetupSizeText } from "audio_setup_screen";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Wrap } from "kryon/text_props";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import {
    AppScale,
    AppSmallFontSize,
    AppTextLineHeight,
    AppTextWidth,
    AppTitleFontSize
} from "metrics";

export function AudioSetupLine(
    app: *InnerBreeze,
    text: string,
    font: s32,
    y: s32
): void {
    let width = AppTextWidth(text, font);
    <Text
        session={app.ui.session}
        props={{
            text: text,
            size: font,
            bounds: {
                x: float32((app.ui.view_width - width) / 2n),
                y: float32(y),
                width: float32(width),
                height: float32(AppTextLineHeight(font))
            },
            wrap: Wrap.TextWrapNone
        }}
    />;
}

export function AudioSetupScreen(app: *InnerBreeze): void {
    let column = NativeLayout.CenteredColumnFor(app.ui.view_width, AppScale(380n), AppScale(16n));
    let gap = AppScale(12n);
    let button_height = AppScale(48n);
    let title = LocaleText("optional_audio_title");
    let title_font = AppTitleFontSize(title, column.width);
    let size_buffer = AudioSetupScreenNewSizeBuffer();
    let size = AudioSetupSizeText(AudioSetupBytes(), size_buffer[:]);
    let content_height =
        AppTextLineHeight(title_font) +
        AppTextLineHeight(AppSmallFontSize()) +
        button_height * 2n +
        gap * 4n;
    let y = (app.ui.view_height - content_height) / 2n;
    if (y < AppScale(16n)) {
        y = AppScale(16n);
    }
    AudioSetupLine(app, title, title_font, y);
    y = y + (AppTextLineHeight(title_font) + gap);
    AudioSetupLine(app, size, AppSmallFontSize(), y);
    y = y + (AppTextLineHeight(AppSmallFontSize()) + gap * 2n);
    if (
        (
            <Button
                session={app.ui.session}
                props={{
                    id: 264n,
                    bounds: {
                        x: float32(column.x),
                        y: float32(y),
                        width: float32(column.width),
                        height: float32(button_height)
                    },
                    label: LocaleText("practice_narration_download"),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled
                }}
            />
        )
    ) {
        AudioSetupFinish(app, true);
        return;
    }
    y = y + (button_height + gap);
    if (
        (
            <Button
                session={app.ui.session}
                props={{
                    id: 265n,
                    bounds: {
                        x: float32(column.x),
                        y: float32(y),
                        width: float32(column.width),
                        height: float32(button_height)
                    },
                    label: LocaleText("optional_audio_skip"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        AudioSetupFinish(app, false);
    }
}
