// The cabinet: cover art with the illuminated dial, the station presets
// and the invisible controls laid over the art. State, audio and saved
// preferences live in radio_model.
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import * as NativeImage from "kryon/image";
import * as NativeText from "kryon/text";
import { TextAlign } from "kryon/text_align";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { Scroll } from "kryon/tsx/scroll";
import { Text } from "kryon/tsx/text";
import { ScrollResult } from "kryon/scroll";
import { AppMessage } from "apps/node_types";
import { RADIO_STATION_COUNT, StationName } from "stations";
import * as Model from "radio_model";

export function RadioView(message: AppMessage): AppMessage {
    Model.RadioLoad(message.account);
    const frame = Model.ReadAppUiHost();
    const margin = s32(16.0 * frame.scale);
    let width = frame.width - margin * s32(2);
    const maximum = s32(620.0 * frame.scale);
    if (width > maximum) {
        width = maximum;
    }
    const x = (frame.width - width) / s32(2);
    const y = frame.top + margin;
    const viewport: Rectangle = {x: float32(x), y: float32(y),
        width: float32(width),
        height: float32(frame.height - frame.bottom - y)};
    const view = <Scroll session={frame.session}
        props={{key: u64(26000), bounds: viewport, content_height: width,
            scroll_offset: Model.scroll_offset, scale: frame.scale}}
        children={(scroll: ScrollResult): void => {
            const cabinet: Rectangle = {x: scroll.content.x, y: scroll.content.y,
                width: scroll.content.width, height: scroll.content.width};
            <Image session={frame.session} props={{key: u64(26001), bounds: cabinet,
                asset_path: "assets/radio/player.avif", alt_text: "Radio",
                fit: NativeImage.ImageFit.ImageFitContain, smooth: true}}/>;
            const target = 44.0 * frame.scale;
            const power = Model.RadioTarget(
                Model.RadioRect(cabinet, 581.0, 766.0, 100.0, 100.0), target);
            const volume_control = Model.RadioTarget(
                Model.RadioRect(cabinet, 680.0, 735.0, 160.0, 160.0), target);
            const tuning = Model.RadioTarget(
                Model.RadioRect(cabinet, 942.0, 735.0, 160.0, 160.0), target);
            const pointer = Model.RadioDragUpdate(volume_control, tuning, frame.scale);
            const drag_moved = Model.drag_moved;
            // Presets are ordinary buttons: focus, activation and drags.
            for (let index: s32 = s32(0); index < s32(RADIO_STATION_COUNT); index += s32(1)) {
                const preset = Model.RadioTarget(Model.RadioRect(cabinet,
                    767.0 + float32(index) * 80.0, 636.0, 80.0, 62.0), target);
                const pressed = <Button session={frame.session}
                    props={{id: s32(26010) + index, bounds: preset,
                        label: StationName(index), selected: Model.selected === index,
                        icon_only: true, invisible: true,
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisGhost}}/>;
                if (pressed) {
                    Model.RadioTune(index);
                }
            }
            const needle = Model.RadioNeedle(
                Model.RadioRect(cabinet, 654.0, 433.0, 459.0, 186.0));
            <Box session={frame.session} props={{key: u64(26031), bounds: needle,
                fill: {r: u8(153), g: u8(66), b: u8(39), a: u8(255)}}}/>;
            const state = Model.AudioStateHost();
            // Power is independent of the knobs' drags.
            const power_pressed = <Button session={frame.session}
                props={{id: s32(26002), bounds: power,
                    label: Model.RadioPowerLabel(state),
                    icon_only: true, invisible: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost}}/>;
            if (power_pressed && !drag_moved) {
                Model.RadioPower(state);
            }
            const volume_pressed = <Button session={frame.session}
                props={{id: s32(26003), bounds: volume_control,
                    label: Model.AppLocaleHost("music_volume_label"),
                    detail: Model.RadioVolumeLabel(),
                    icon_only: true, invisible: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost}}/>;
            if (volume_pressed && !drag_moved) {
                Model.RadioVolumeStep();
            }
            const tuning_pressed = <Button session={frame.session}
                props={{id: s32(26005), bounds: tuning,
                    label: Model.AppLocaleHost("radio_tuning"),
                    detail: StationName(Model.selected),
                    icon_only: true, invisible: true,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost}}/>;
            if (tuning_pressed && !drag_moved) {
                Model.RadioTuneNext();
            }
            const display = Model.RadioRect(cabinet, 717.0, 575.0, 335.0, 36.0);
            <Box session={frame.session} props={{key: u64(26032), bounds: display,
                fill: {r: u8(63), g: u8(31), b: u8(18), a: u8(220)}}}/>;
            <Text session={frame.session} props={{key: u64(26020), bounds: display,
                text: Model.RadioDisplayText(state), size: frame.font - s32(5),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapAuto}}/>;
            Model.RadioDragEnd(pointer);
        }}/>;
    Model.scroll_offset = view.scroll_offset;
    if (!view.opened) {
        message.succeeded = true;
        return message;
    }
    message.succeeded = true;
    return message;
}
