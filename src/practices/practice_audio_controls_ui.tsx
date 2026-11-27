// Authored UI composition; native application state remains in practice_audio_controls.zi.
import * as NativeButton from "kryon/button";
import * as NativeOverlay from "kryon/overlay";
import * as NativeSlider from "kryon/slider";
import { InnerBreeze, SETTINGS_VOLUME_MAX, SETTINGS_VOLUME_MIN } from "app_types";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { End, TreePushScope } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { DismissibleOverlay } from "kryon/tsx/overlay";
import { DiscreteSlider } from "kryon/tsx/slider";
import { LocaleText } from "locale";
import { AppScale } from "metrics";
import { PracticeAudioImage } from "practice_audio_controls";
import { save_settings } from "practice_settings_host";

export function PracticeAudioTriggerView(
    app: *InnerBreeze,
    id: s32,
    x: s32,
    y: s32,
    music: boolean
): boolean {
    let label = LocaleText("cue_volume_label");
    if (music) {
        label = LocaleText("practice_background_music_label");
    }
    let button: NativeButton.Props = {};
    button.id = id;
    button.bounds = {
        x: float32(x),
        y: float32(y),
        width: float32(AppScale(44n)),
        height: float32(AppScale(44n))
    };
    button.label = label;
    button.image = PracticeAudioImage(music, !music && app.sound_volume <= 0n, label);
    button.icon_only = true;
    button.circle = true;
    button.tone = ButtonTone.ButtonToneNeutral;
    button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    return <Button session={app.ui.session} props={button} />;
}

export function PracticeAudioPopupView(
    app: *InnerBreeze,
    id: s32,
    x: s32,
    y: s32,
    music: boolean
): boolean {
    let popup_width = AppScale(52n);
    let popup_height = AppScale(176n);
    let popup_x = x + (AppScale(44n) - popup_width) / 2n;
    let popup_y = y + AppScale(48n);
    if (popup_x < 0n) {
        popup_x = 0n;
    }
    if (popup_x + popup_width > app.ui.view_width) {
        popup_x = app.ui.view_width - popup_width;
    }
    if (popup_x < 0n) {
        popup_x = 0n;
    }
    if (popup_y + popup_height > app.ui.view_height) {
        popup_y = y - popup_height - AppScale(4n);
    }
    if (popup_y < 0n) {
        popup_y = 0n;
    }
    let bounds: Rectangle = {
        x: float32(popup_x),
        y: float32(popup_y),
        width: float32(popup_width),
        height: float32(popup_height)
    };
    let overlay_props: NativeOverlay.Props = {};
    overlay_props.key = u64(id + 100n);
    overlay_props.bounds = bounds;
    overlay_props.view_width = app.ui.view_width;
    overlay_props.view_height = app.ui.view_height;
    let overlay = <DismissibleOverlay session={app.ui.session} props={overlay_props} />;
    if (overlay.closed) {
        return true;
    }
    if (overlay.panel_node < 0n || !TreePushScope(app.ui.session, overlay.panel_node)) {
        return false;
    }
    let panel: NativeButton.Props = {};
    panel.id = id + 200n;
    panel.bounds = bounds;
    panel.disabled = true;
    panel.tone = ButtonTone.ButtonToneNeutral;
    panel.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
    <Button session={app.ui.session} props={panel} />;
    let label = LocaleText("cue_volume_label");
    let value = app.sound_volume;
    if (music) {
        label = LocaleText("music_volume_label");
        value = app.music_volume;
    }
    let slider: NativeSlider.DiscreteSliderProps = {};
    slider.id = id + 1n;
    slider.semantic_label = label;
    slider.bounds = {
        x: float32(popup_x + (popup_width - AppScale(20n)) / 2n),
        y: float32(popup_y + AppScale(14n)),
        width: float32(AppScale(20n)),
        height: float32(popup_height - AppScale(28n))
    };
    slider.value = value;
    slider.min = SETTINGS_VOLUME_MIN;
    slider.max = SETTINGS_VOLUME_MAX;
    slider.vertical = true;
    let result: NativeSlider.SliderDiscreteStep = (
        <DiscreteSlider session={app.ui.session} props={slider} />
    );
    End(app.ui.session);
    if (!result.changed) {
        return false;
    }
    if (music) {
        app.music_volume = result.value;
    } else {
        app.sound_volume = result.value;
    }
    app.settings_dirty = 1n;
    save_settings(app);
    return false;
}
