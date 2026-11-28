import { ResolvedModal } from "kryon/tsx/modal";
import { Scroll } from "kryon/tsx/scroll";
// Authored UI composition; native application state remains in settings_view.zi.
import * as NativeDropdown from "kryon/dropdown";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSegmentedControl from "kryon/segmented_control";
import * as NativeShape from "kryon/shape";
import * as NativeSlider from "kryon/slider";
import * as NativeToggle from "kryon/toggle";
import * as State_settings_view from "settings_view";
import { PracticeFigure } from "figure_view";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { DarkenColor, LightenColor } from "kryon/drawing_props";
import { Rectangle } from "kryon/geometry";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { ToggleSize } from "kryon/toggle_measure";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { Dropdown } from "kryon/tsx/dropdown";
import { SegmentedControl } from "kryon/tsx/segmented_control";
import { Shape } from "kryon/tsx/shape";
import { DiscreteSlider } from "kryon/tsx/slider";
import { Text } from "kryon/tsx/text";
import { TitleBar } from "kryon/tsx/title_bar";
import { Toggle } from "kryon/tsx/toggle";
import {
    PATTERNS_PRESET_COUNT,
    PATTERNS_PRESET_CUSTOM,
    patterns_preset_ratio
} from "patterns_rules";
import {
    PRACTICE_SETTINGS_BACK,
    PRACTICE_SETTINGS_BELL,
    PRACTICE_SETTINGS_CUE_VOLUME,
    PRACTICE_SETTINGS_CUSTOM,
    PRACTICE_SETTINGS_DURATION,
    PRACTICE_SETTINGS_EXTEND,
    PRACTICE_SETTINGS_LANGUAGE,
    PRACTICE_SETTINGS_LANGUAGE_ACTION,
    PRACTICE_SETTINGS_MUSIC,
    PRACTICE_SETTINGS_MUSIC_DOWNLOAD,
    PRACTICE_SETTINGS_MUSIC_TEST,
    PRACTICE_SETTINGS_MUSIC_VOLUME,
    PRACTICE_SETTINGS_NARRATION,
    PRACTICE_SETTINGS_OVERTIME,
    PRACTICE_SETTINGS_PATTERN,
    PRACTICE_SETTINGS_PATTERN_LESS,
    PRACTICE_SETTINGS_PATTERN_MINUTES,
    PRACTICE_SETTINGS_PATTERN_MORE,
    PRACTICE_SETTINGS_SUN_CHARACTER,
    PRACTICE_SETTINGS_SUN_END,
    PRACTICE_SETTINGS_SUN_REPETITIONS,
    PRACTICE_SETTINGS_SUN_START,
    PRACTICE_SETTINGS_TAI_CHARACTER,
    PRACTICE_SETTINGS_VOICE,
    PRACTICE_SETTINGS_WHM_ANIMATION,
    PRACTICE_SETTINGS_WHM_CONTROLS,
    PRACTICE_SETTINGS_WHM_DOUBLE_TAP,
    PRACTICE_SETTINGS_WHM_EDITOR_CLOSE,
    PRACTICE_SETTINGS_WHM_PROGRESSIVE,
    PRACTICE_SETTINGS_WHM_REMINDER,
    PRACTICE_SETTINGS_WHM_RESET,
    PRACTICE_SETTINGS_WHM_SPEED,
    PRACTICE_SETTINGS_WHM_START_EDITOR,
    PRACTICE_SETTINGS_WHM_START_SPEED
} from "practice_types";
import {
    Ask,
    AttributionHeight,
    Bounds,
    BreathPreview,
    ContentHeight,
    CountText,
    CustomMinutesLabel,
    EmptyString,
    FormatValue,
    FormatValueSuffix,
    Locale,
    MEDITATION_PRESETS,
    MinutesChoiceLabel,
    NARRATION_DOWNLOAD_ICON,
    NARRATION_REMOVE_ICON,
    NewOptions,
    NewOptions1NativeDropdownOption,
    NewOptionsSETTINGS_LANGUAGE_MAXNativeDropdownOption,
    NewSeconds,
    Page,
    ParagraphHeight,
    PatternSeconds,
    PatternSecondsLabel,
    PatternsPresetLabel,
    ReadPracticeCharacterHost,
    ReadPracticeMusicTrackHost,
    ReadPracticeNarrationHost,
    SETTINGS_LANGUAGE_MAX,
    SETTINGS_MUSIC_TRACK_MAX,
    SETTINGS_TEXT_12,
    Scale,
    ScrollKey,
    SunDuration,
    TaiAudioHeight,
    WhmBreathHeight,
    WhmOptionsHeight,
    WhmRounds,
    Width
} from "settings_view";
import { ExerciseType } from "exercise_types";

export function Label(text: string, x: s32, y: s32): void {
    <Text
        session={State_settings_view.settings.session}
        props={{ bounds: Bounds(x, y, 0n, 0n), text: text, wrap: Wrap.TextWrapNone }}
    />;
}

export function Choice(bounds: Rectangle, label: string, chosen: boolean): boolean {
    return Button({
        session: State_settings_view.settings.session,
        props: {
            bounds: bounds,
            label: label,
            tone: chosen ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
            emphasis: chosen
                ? ButtonEmphasis.ButtonEmphasisFilled
                : ButtonEmphasis.ButtonEmphasisSoft
        }
    });
}

export function Duration(x: s32, width: s32, y: NativeRef<s32>): void {
    let labels: [string, string, string, string, string, string] = [
        Locale("duration_5m"),
        Locale("duration_15m"),
        Locale("duration_30m"),
        Locale("duration_1h"),
        Locale("duration_2h"),
        Locale("meditation_duration_custom")
    ];
    let gap = Scale(8n);
    let button_height = Scale(48n);
    Label(Locale("meditation_duration_setting"), x, nativeDeref(y));
    nativeSet(y, nativeDeref(y) + Scale(30n));
    let columns: s32 = width >= Scale(520n) ? 3n : 2n;
    let button_width = (width - gap * (columns - 1n)) / columns;
    for (let index = s32(0n); index <= MEDITATION_PRESETS; index += s32(1)) {
        if (
            Choice(
                Bounds(
                    x + (index % columns) * (button_width + gap),
                    nativeDeref(y) + (index / columns) * (button_height + gap),
                    button_width,
                    button_height
                ),
                nativeAt(labels, index),
                index === State_settings_view.settings.duration_mode
            )
        ) {
            Ask(PRACTICE_SETTINGS_DURATION, index);
        }
    }
    nativeSet(
        y,
        nativeDeref(y) +
            (((MEDITATION_PRESETS + 1n + columns - 1n) / columns) * (button_height + gap) +
                Scale(8n))
    );
    let custom_y = nativeDeref(y);
    Label(CustomMinutesLabel(), x, custom_y);
    let adjust_labels: [string, string, string, string] = ["-5", "-1", "+1", "+5"];
    let adjust_values: [s32, s32, s32, s32] = [-5n, -1n, 1n, 5n];
    let adjust_width = Scale(50n);
    let adjust_x = x + (width - (adjust_width * 4n + gap * 3n)) / 2n;
    for (let index = s32(0n); index <= 3n; index += s32(1)) {
        if (
            Button({
                session: State_settings_view.settings.session,
                props: {
                    bounds: Bounds(
                        adjust_x + index * (adjust_width + gap),
                        custom_y + Scale(34n),
                        adjust_width,
                        button_height
                    ),
                    label: nativeAt(adjust_labels, index),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }
            })
        ) {
            Ask(PRACTICE_SETTINGS_CUSTOM, nativeAt(adjust_values, index));
        }
    }
    nativeSet(y, nativeDeref(y) + Scale(108n));
    Label(Locale("meditation_extend_controls_label"), x, nativeDeref(y));
    let extend: NativeToggle.Props = {
        value: State_settings_view.settings.extend_controls,
        off_label: Locale("toggle_off"),
        on_label: Locale("toggle_on")
    };
    let size = ToggleSize(State_settings_view.settings.session, extend);
    extend.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y) + Scale(26n)),
        width: size.x,
        height: size.y > float32(Scale(30n)) ? size.y : float32(Scale(30n))
    };
    let toggled = Toggle({ session: State_settings_view.settings.session, props: extend });
    if (toggled.changed) {
        Ask(PRACTICE_SETTINGS_EXTEND, toggled.value ? 1n : 0n);
    }
    nativeSet(y, nativeDeref(y) + Scale(84n));
    Label(Locale("meditation_overtime_label"), x, nativeDeref(y));
    let overtime: NativeToggle.Props = {
        value: State_settings_view.settings.overtime_enabled,
        off_label: Locale("toggle_off"),
        on_label: Locale("toggle_on")
    };
    let overtime_size = ToggleSize(State_settings_view.settings.session, overtime);
    overtime.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y) + Scale(26n)),
        width: overtime_size.x,
        height: overtime_size.y > float32(Scale(30n)) ? overtime_size.y : float32(Scale(30n))
    };
    let overtime_toggled = Toggle({
        session: State_settings_view.settings.session,
        props: overtime
    });
    if (overtime_toggled.changed) {
        Ask(PRACTICE_SETTINGS_OVERTIME, overtime_toggled.value ? 1n : 0n);
    }
    nativeSet(y, nativeDeref(y) + Scale(84n));
    Label(Locale("meditation_interval_bell_label"), x, nativeDeref(y));
    let bell_labels: [string, string, string, string, string, string, string] = [
        Locale("meditation_interval_bell_off"),
        "1",
        "2",
        "5",
        "10",
        "15",
        "30"
    ];
    let bell_values: [s32, s32, s32, s32, s32, s32, s32] = [0n, 1n, 2n, 5n, 10n, 15n, 30n];
    let bell_chosen: s32 = s32(0n);
    for (let index = s32(0n); index <= 6n; index += s32(1)) {
        if (State_settings_view.settings.bell_minutes === nativeAt(bell_values, index)) {
            bell_chosen = index;
        }
    }
    let bell_columns: s32 = width >= Scale(460n) ? 7n : 4n;
    let bell_width = (width - gap * (bell_columns - 1n)) / bell_columns;
    if (bell_width > Scale(72n)) {
        bell_width = Scale(72n);
    }
    for (let index = s32(0n); index <= 6n; index += s32(1)) {
        if (
            Choice(
                Bounds(
                    x + (index % bell_columns) * (bell_width + gap),
                    nativeDeref(y) + Scale(26n) + (index / bell_columns) * (button_height + gap),
                    bell_width,
                    button_height
                ),
                nativeAt(bell_labels, index),
                index === bell_chosen
            )
        ) {
            Ask(PRACTICE_SETTINGS_BELL, nativeAt(bell_values, index));
        }
    }
    let bell_rows = (7n + bell_columns - 1n) / bell_columns;
    nativeSet(
        y,
        nativeDeref(y) +
            (Scale(26n) + bell_rows * button_height + (bell_rows - 1n) * gap + Scale(12n))
    );
}

export function Pattern(x: s32, width: s32, y: NativeRef<s32>): void {
    let button_height = Scale(48n);
    let gap = Scale(8n);
    Label(Locale("patterns_preset_label"), x, nativeDeref(y));
    nativeSet(y, nativeDeref(y) + Scale(30n));
    for (let preset = s32(0n); preset < PATTERNS_PRESET_COUNT; preset += s32(1)) {
        let seconds = NewSeconds();
        for (let phase = s32(0n); phase <= 3n; phase += s32(1)) {
            nativeSet(seconds, phase, patterns_preset_ratio(preset, phase));
            if (preset === PATTERNS_PRESET_CUSTOM) {
                nativeSet(seconds, phase, PatternSeconds(phase));
            }
        }
        if (
            Choice(
                Bounds(x, nativeDeref(y) + preset * (button_height + gap), width, button_height),
                PatternsPresetLabel(preset, nativeSlice(seconds)),
                State_settings_view.settings.pattern === preset
            )
        ) {
            Ask(PRACTICE_SETTINGS_PATTERN, preset);
        }
    }
    nativeSet(y, nativeDeref(y) + (PATTERNS_PRESET_COUNT * (button_height + gap) + Scale(10n)));
    if (State_settings_view.settings.pattern === PATTERNS_PRESET_CUSTOM) {
        Label(Locale("patterns_custom_label"), x, nativeDeref(y));
        nativeSet(y, nativeDeref(y) + Scale(30n));
        let phases: [string, string, string, string] = [
            Locale("patterns_phase_inhale"),
            Locale("patterns_phase_hold_in"),
            Locale("patterns_phase_exhale"),
            Locale("patterns_phase_hold_out")
        ];
        let step_width = Scale(46n);
        for (let phase = s32(0n); phase <= 3n; phase += s32(1)) {
            Label(nativeAt(phases, phase), x, nativeDeref(y));
            if (
                Button({
                    session: State_settings_view.settings.session,
                    props: {
                        bounds: Bounds(
                            x + width - step_width * 2n - gap,
                            nativeDeref(y),
                            step_width,
                            button_height
                        ),
                        label: "-5",
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }
                })
            ) {
                Ask(PRACTICE_SETTINGS_PATTERN_LESS, phase);
            }
            if (
                Button({
                    session: State_settings_view.settings.session,
                    props: {
                        bounds: Bounds(
                            x + width - step_width,
                            nativeDeref(y),
                            step_width,
                            button_height
                        ),
                        label: "+5",
                        tone: ButtonTone.ButtonToneNeutral,
                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                    }
                })
            ) {
                Ask(PRACTICE_SETTINGS_PATTERN_MORE, phase);
            }
            let value_text = PatternSecondsLabel(phase);
            Label(
                value_text,
                x +
                    width -
                    step_width * 2n -
                    gap -
                    Width(value_text, State_settings_view.settings.font) -
                    Scale(8n),
                nativeDeref(y)
            );
            nativeSet(y, nativeDeref(y) + (button_height + gap));
        }
        nativeSet(y, nativeDeref(y) + Scale(6n));
    }
    Label(Locale("patterns_duration_label"), x, nativeDeref(y));
    nativeSet(y, nativeDeref(y) + Scale(30n));
    let minutes: [s32, s32, s32, s32, s32] = [0n, 3n, 5n, 10n, 20n];
    let minutes_width = (width - gap * 4n) / 5n;
    for (let index = s32(0n); index <= 4n; index += s32(1)) {
        if (
            Choice(
                Bounds(
                    x + index * (minutes_width + gap),
                    nativeDeref(y),
                    minutes_width,
                    button_height
                ),
                MinutesChoiceLabel(nativeSlice(minutes), index),
                State_settings_view.settings.pattern_minutes === nativeAt(minutes, index)
            )
        ) {
            Ask(PRACTICE_SETTINGS_PATTERN_MINUTES, nativeAt(minutes, index));
        }
    }
    nativeSet(y, nativeDeref(y) + (button_height + Scale(10n)));
}

export function SliderRow(
    id: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    row_height: s32,
    label: string,
    minimum: s32,
    maximum: s32,
    value: s32,
    suffix: string
): NativeSlider.SliderDiscreteStep {
    <Text
        session={State_settings_view.settings.session}
        props={{
            text: label,
            size: State_settings_view.settings.small_font,
            wrap: Wrap.TextWrapNone,
            bounds: Bounds(x, nativeDeref(y), width - Scale(64n), Scale(20n))
        }}
    />;
    <Text
        session={State_settings_view.settings.session}
        props={{
            text: FormatValueSuffix(value, suffix),
            size: State_settings_view.settings.small_font,
            wrap: Wrap.TextWrapNone,
            align: TextAlign.TextAlignEnd,
            bounds: Bounds(x + width - Scale(64n), nativeDeref(y), Scale(64n), Scale(20n))
        }}
    />;
    let step = DiscreteSlider({
        session: State_settings_view.settings.session,
        props: {
            id: id,
            bounds: Bounds(x, nativeDeref(y) + Scale(20n), width, Scale(36n)),
            semantic_label: label,
            value: value,
            min: minimum,
            max: maximum
        }
    });
    nativeSet(y, nativeDeref(y) + row_height);
    return step;
}

export function Card(x: s32, y: s32, width: s32, height: s32): void {
    let shorter = height < width ? height : width;
    <Box
        session={State_settings_view.settings.session}
        props={{
            bounds: Bounds(x, y, width, height),
            fill: State_settings_view.settings.surface_color,
            border: State_settings_view.settings.border_color,
            radius: 0.08 * float32(shorter) * 0.5
        }}
    />;
}

export function ToggleRow(
    id: s32,
    label: string,
    value: boolean,
    x: s32,
    width: s32,
    y: s32,
    row_height: s32
): NativeToggle.ToggleValueResult {
    Label(label, x, y);
    let toggle: NativeToggle.Props = {
        id: id,
        value: value,
        off_label: Locale("toggle_off"),
        on_label: Locale("toggle_on")
    };
    let size = ToggleSize(State_settings_view.settings.session, toggle);
    let toggle_height = size.y > float32(Scale(30n)) ? s32(size.y) : Scale(30n);
    toggle.bounds = Bounds(
        x + width - s32(size.x),
        y + (row_height - toggle_height) / 2n,
        s32(size.x),
        toggle_height
    );
    return Toggle({ session: State_settings_view.settings.session, props: toggle });
}

export function WhmBreath(x: s32, width: s32, y: NativeRef<s32>): void {
    let height = WhmBreathHeight();
    Card(x, nativeDeref(y), width, height);
    let padding = Scale(22n);
    let inner_x = x + padding;
    let inner_width = width - padding * 2n;
    let inner_y = nativeDeref(y) + padding;
    Label(Locale("breath_animation_label"), inner_x, inner_y);
    let animations: [NativeDropdown.Option, NativeDropdown.Option] = [
        { label: Locale("breath_animation_linear") },
        { label: Locale("breath_animation_in_out") }
    ];
    let animation = Dropdown({
        session: State_settings_view.settings.session,
        props: {
            id: 104n,
            bounds: Bounds(inner_x, inner_y + Scale(26n), inner_width, Scale(48n)),
            selected_index: State_settings_view.settings.whm_animation
        },
        options: nativeSlice(animations)
    });
    if (animation.changed) {
        Ask(PRACTICE_SETTINGS_WHM_ANIMATION, animation.selected_index);
    }
    inner_y = inner_y + Scale(82n);
    let preview_height = Scale(144n);
    let halo = State_settings_view.settings.link_color;
    halo.a = u8(255.0 * 0.16);
    let clear = State_settings_view.settings.canvas_color;
    clear.a = 0n;
    NativeShape.Circle(State_settings_view.settings.session, {
        center: {
            x: float32(inner_x + inner_width / 2n),
            y: float32(inner_y + preview_height / 2n)
        },
        radius: float32(Scale(72n)),
        fill: halo,
        edge: clear,
        has_edge: true
    });
    BreathPreview(
        inner_x + inner_width / 2n,
        inner_y + preview_height / 2n,
        inner_width,
        preview_height,
        State_settings_view.settings.whm_preview
    );
    inner_y = inner_y + (preview_height + Scale(20n));
    let speed = SliderRow(
        1n,
        inner_x,
        inner_width,
        nativeRef(inner_y),
        Scale(78n),
        Locale("speed_label"),
        State_settings_view.settings.whm_speed_min,
        State_settings_view.settings.whm_speed_max,
        State_settings_view.settings.whm_speed,
        EmptyString()
    );
    if (speed.changed) {
        Ask(PRACTICE_SETTINGS_WHM_SPEED, speed.value);
    }
    let progressive = ToggleRow(
        1101n,
        Locale("progressive_speed_label"),
        State_settings_view.settings.whm_progressive,
        inner_x,
        inner_width,
        inner_y,
        Scale(58n)
    );
    if (progressive.changed) {
        Ask(PRACTICE_SETTINGS_WHM_PROGRESSIVE, progressive.value ? 1n : 0n);
    }
    inner_y = inner_y + Scale(58n);
    if (State_settings_view.settings.whm_progressive) {
        if (
            FittedButton(Locale("modify_start_speed_button"), inner_x, inner_y, inner_width, false)
        ) {
            Ask(PRACTICE_SETTINGS_WHM_START_EDITOR, 0n);
        }
    }
    nativeSet(y, nativeDeref(y) + (height + Scale(16n)));
}

export function WhmOptions(x: s32, width: s32, y: NativeRef<s32>): void {
    let height = WhmOptionsHeight();
    Card(x, nativeDeref(y), width, height);
    let padding = Scale(22n);
    let inner_x = x + padding;
    let inner_width = width - padding * 2n;
    let inner_y = nativeDeref(y) + padding;
    let double_tap = ToggleRow(
        1201n,
        Locale("double_tap_to_breathe_label"),
        State_settings_view.settings.whm_double_tap,
        inner_x,
        inner_width,
        inner_y,
        Scale(60n)
    );
    if (double_tap.changed) {
        Ask(PRACTICE_SETTINGS_WHM_DOUBLE_TAP, double_tap.value ? 1n : 0n);
    }
    inner_y = inner_y + Scale(88n);
    let controls = ToggleRow(
        1202n,
        Locale("advanced_session_controls_label"),
        State_settings_view.settings.whm_controls,
        inner_x,
        inner_width,
        inner_y,
        Scale(60n)
    );
    if (controls.changed) {
        Ask(PRACTICE_SETTINGS_WHM_CONTROLS, controls.value ? 1n : 0n);
    }
    inner_y = inner_y + Scale(88n);
    Label(Locale("whm_hold_reminder_label"), inner_x, inner_y);
    let seconds: [s32, s32, s32] = [0n, 30n, 60n];
    let reminders: [NativeDropdown.Option, NativeDropdown.Option, NativeDropdown.Option] = [
        { label: Locale("whm_hold_reminder_off") },
        { label: Locale("whm_hold_reminder_30s") },
        { label: Locale("whm_hold_reminder_60s") }
    ];
    let chosen: s32 =
        State_settings_view.settings.whm_reminder === 30n
            ? 1n
            : State_settings_view.settings.whm_reminder === 60n
              ? 2n
              : 0n;
    let reminder = Dropdown({
        session: State_settings_view.settings.session,
        props: {
            id: 1203n,
            bounds: Bounds(inner_x, inner_y + Scale(26n), inner_width, Scale(48n)),
            selected_index: chosen
        },
        options: nativeSlice(reminders)
    });
    if (reminder.changed && reminder.selected_index >= 0n && reminder.selected_index < 3n) {
        Ask(PRACTICE_SETTINGS_WHM_REMINDER, nativeAt(seconds, reminder.selected_index));
    }
    nativeSet(y, nativeDeref(y) + (height + Scale(16n)));
}

export function Whm(x: s32, width: s32, y: NativeRef<s32>): void {
    nativeSet(y, nativeDeref(y) + Scale(16n));
    WhmBreath(x, width, y);
    WhmRounds(x, width, y);
    WhmOptions(x, width, y);
    nativeSet(y, nativeDeref(y) + Scale(24n));
    Music(x, width, y);
    nativeSet(y, nativeDeref(y) + Scale(12n));
    let label = Locale("reset_to_defaults_label");
    let reset_width = Width(label, State_settings_view.settings.font) + Scale(24n);
    if (reset_width > width) {
        reset_width = width;
    }
    if (
        Button({
            session: State_settings_view.settings.session,
            props: {
                bounds: Bounds(x + width - reset_width, nativeDeref(y), reset_width, Scale(48n)),
                label: label,
                tone: ButtonTone.ButtonToneNeutral,
                emphasis: ButtonEmphasis.ButtonEmphasisSoft
            }
        })
    ) {
        Ask(PRACTICE_SETTINGS_WHM_RESET, 0n);
    }
    nativeSet(y, nativeDeref(y) + (Scale(48n) + Scale(24n)));
}

export function WhmStartSpeedEditor(): void {
    let frame = ResolvedModal({
        session: State_settings_view.settings.session,
        props: {
            key: NativeLayout.KeyHash("whm/start_speed"),
            title: Locale("progressive_start_speed_editor_title"),
            width: Scale(340n),
            height: Scale(360n),
            scale: State_settings_view.settings.scale,
            has_right_action: true,
            right_label: Locale("close_button")
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let content = frame.layout.content;
            let x = s32(content.x);
            let y = s32(content.y);
            let width = s32(content.width);
            BreathPreview(
                x + width / 2n,
                y + Scale(90n),
                width,
                Scale(180n),
                State_settings_view.settings.whm_editor_preview
            );
            let slider_y = y + Scale(206n);
            let start = SliderRow(
                12n,
                x,
                width,
                nativeRef(slider_y),
                Scale(56n),
                Locale("progressive_start_speed_label"),
                State_settings_view.settings.whm_speed_min,
                State_settings_view.settings.whm_speed,
                State_settings_view.settings.whm_start_speed,
                EmptyString()
            );
            if (start.changed) {
                Ask(PRACTICE_SETTINGS_WHM_START_SPEED, start.value);
            }
        }
    });
    if (frame.dismissed || frame.right_clicked) {
        Ask(PRACTICE_SETTINGS_WHM_EDITOR_CLOSE, 0n);
        return;
    }
}

export function MusicProgress(x: s32, y: s32, width: s32): void {
    if (width <= 0n) {
        return;
    }
    let bar_height = Scale(10n);
    let fill: s32 = s32(0n);
    if (State_settings_view.settings.music_total > 0n) {
        fill = s32(
            (State_settings_view.settings.music_bytes * s64(width)) /
                State_settings_view.settings.music_total
        );
    }
    if (fill < 0n) {
        fill = 0n;
    }
    if (fill > width) {
        fill = width;
    }
    let background = State_settings_view.settings.canvas_color;
    <Box
        session={State_settings_view.settings.session}
        props={{ bounds: Bounds(x, y, width, bar_height), fill: DarkenColor(background, 28n) }}
    />;
    let dark = DarkenColor(background, 55n);
    let light = LightenColor(background, 35n);
    let left = float32(x);
    let top = float32(y);
    let right = float32(x + width - 1n);
    let bottom = float32(y + bar_height - 1n);
    <Shape
        session={State_settings_view.settings.session}
        props={{ start: { x: left, y: top }, end: { x: right, y: top }, color: light }}
    />;
    <Shape
        session={State_settings_view.settings.session}
        props={{ start: { x: left, y: top }, end: { x: left, y: bottom }, color: light }}
    />;
    <Shape
        session={State_settings_view.settings.session}
        props={{ start: { x: left, y: bottom }, end: { x: right, y: bottom }, color: dark }}
    />;
    <Shape
        session={State_settings_view.settings.session}
        props={{ start: { x: right, y: top }, end: { x: right, y: bottom }, color: dark }}
    />;
    if (fill > 0n) {
        let inner = fill - Scale(4n);
        if (inner < Scale(2n)) {
            inner = Scale(2n);
        }
        <Box
            session={State_settings_view.settings.session}
            props={{
                bounds: Bounds(x + Scale(2n), y + Scale(2n), inner, bar_height - Scale(4n)),
                fill: State_settings_view.settings.accent_color
            }}
        />;
    }
}

export function FittedButton(label: string, x: s32, y: s32, width: s32, accent: boolean): boolean {
    let button_width = Width(label, State_settings_view.settings.font) + Scale(24n);
    if (button_width > width) {
        button_width = width;
    }
    return Button({
        session: State_settings_view.settings.session,
        props: {
            bounds: Bounds(x, y, button_width, Scale(48n)),
            label: label,
            tone: accent ? ButtonTone.ButtonToneAccent : ButtonTone.ButtonToneNeutral,
            emphasis: accent
                ? ButtonEmphasis.ButtonEmphasisFilled
                : ButtonEmphasis.ButtonEmphasisSoft
        }
    });
}

export function Music(x: s32, width: s32, y: NativeRef<s32>): void {
    Label(
        Locale(
            State_settings_view.settings.practice === s32(ExerciseType.EXERCISE_SUN_SALUTATION)
                ? "sun_salutation_music_track_label"
                : "practice_background_music_label"
        ),
        x,
        nativeDeref(y)
    );
    let count = State_settings_view.settings.music_count;
    if (count > SETTINGS_MUSIC_TRACK_MAX) {
        count = SETTINGS_MUSIC_TRACK_MAX;
    }
    let options = NewOptions();
    nativeSet(options, 0n, { label: Locale("audio_music_none_option") });
    for (let index = s32(0n); index < count; index += s32(1)) {
        nativeSet(options, index + 1n, { label: ReadPracticeMusicTrackHost(index).label });
    }
    let selection = State_settings_view.settings.music_selection;
    if (selection < 0n || selection > count) {
        selection = 0n;
    }
    let picked = Dropdown({
        session: State_settings_view.settings.session,
        props: {
            id: 451n + State_settings_view.settings.practice,
            bounds: Bounds(x, nativeDeref(y) + Scale(26n), width, Scale(48n)),
            selected_index: selection
        },
        options: nativeSlice(options, 0n, count + 1n)
    });
    if (picked.changed) {
        Ask(PRACTICE_SETTINGS_MUSIC, picked.selected_index);
    }
    nativeSet(y, nativeDeref(y) + Scale(90n));
    if (selection === 0n) {
        return;
    }
    if (State_settings_view.settings.music_installed) {
        if (
            FittedButton(
                Locale(
                    State_settings_view.settings.music_playing
                        ? "meditation_music_stop_test_button"
                        : "meditation_music_test_button"
                ),
                x,
                nativeDeref(y),
                width,
                false
            )
        ) {
            Ask(PRACTICE_SETTINGS_MUSIC_TEST, 0n);
        }
        nativeSet(y, nativeDeref(y) + Scale(60n));
    }
    if (
        State_settings_view.settings.music_built_in &&
        (!State_settings_view.settings.music_installed ||
            State_settings_view.settings.music_redownload)
    ) {
        if (
            FittedButton(
                Locale(
                    State_settings_view.settings.music_installed
                        ? "meditation_music_redownload_button"
                        : "meditation_music_download_button"
                ),
                x,
                nativeDeref(y),
                width,
                true
            )
        ) {
            Ask(PRACTICE_SETTINGS_MUSIC_DOWNLOAD, 0n);
        }
        nativeSet(y, nativeDeref(y) + Scale(60n));
    }
    if (State_settings_view.settings.music_show_status) {
        Label(State_settings_view.settings.music_status, x, nativeDeref(y));
        if (State_settings_view.settings.music_downloading) {
            nativeSet(y, nativeDeref(y) + Scale(28n));
            MusicProgress(x, nativeDeref(y), width);
            nativeSet(y, nativeDeref(y) + Scale(22n));
        } else {
            nativeSet(y, nativeDeref(y) + Scale(34n));
        }
    }
    let height = AttributionHeight(width);
    <Text
        session={State_settings_view.settings.session}
        props={{
            bounds: Bounds(x, nativeDeref(y), width, height),
            text: Locale("meditation_music_attribution"),
            size: SETTINGS_TEXT_12,
            wrap: Wrap.TextWrapAuto
        }}
    />;
    nativeSet(y, nativeDeref(y) + (height + Scale(10n)));
}

export function NarrationLanguages(x: s32, width: s32, y: NativeRef<s32>): void {
    let count = State_settings_view.settings.narration_count;
    if (count > SETTINGS_LANGUAGE_MAX) {
        count = SETTINGS_LANGUAGE_MAX;
    }
    if (count <= 0n) {
        return;
    }
    let options = NewOptionsSETTINGS_LANGUAGE_MAXNativeDropdownOption();
    for (let index = s32(0n); index < count; index += s32(1)) {
        let language = ReadPracticeNarrationHost(index);
        let state = language.state;
        nativeSet(options, index, {
            key: u64(language.rank + 1n),
            label: language.label,
            action_shape:
                state === 2n
                    ? NARRATION_REMOVE_ICON
                    : state === 1n
                      ? EmptyString()
                      : NARRATION_DOWNLOAD_ICON,
            action_label: Locale(
                state === 2n ? "practice_download_remove" : "practice_narration_download"
            )
        });
    }
    let picked = Dropdown({
        session: State_settings_view.settings.session,
        props: {
            key:
                NativeLayout.KeyHash("inbe/practice/customize/narration-language") +
                u64(State_settings_view.settings.practice),
            bounds: Bounds(x, nativeDeref(y), width, Scale(44n)),
            selected_index: State_settings_view.settings.narration_selected,
            placeholder: Locale("language_label")
        },
        options: nativeSlice(options, 0n, count)
    });
    if (picked.action_index >= 0n && picked.action_index < count) {
        Ask(PRACTICE_SETTINGS_LANGUAGE_ACTION, picked.action_index);
    }
    if (picked.changed && picked.selected_index >= 0n && picked.selected_index < count) {
        Ask(PRACTICE_SETTINGS_LANGUAGE, picked.selected_index);
    }
    nativeSet(y, nativeDeref(y) + Scale(44n + 16n));
    if (State_settings_view.settings.narration_status.count > 0n) {
        let height = ParagraphHeight(
            State_settings_view.settings.narration_status,
            width,
            State_settings_view.settings.font,
            Scale(3n)
        );
        <Text
            session={State_settings_view.settings.session}
            props={{
                bounds: Bounds(x, nativeDeref(y), width, height),
                text: State_settings_view.settings.narration_status,
                size: State_settings_view.settings.font,
                wrap: Wrap.TextWrapAuto
            }}
        />;
        nativeSet(y, nativeDeref(y) + (height + Scale(12n)));
    }
}

export function Narration(x: s32, width: s32, y: NativeRef<s32>): void {
    <Text
        session={State_settings_view.settings.session}
        props={{
            bounds: Bounds(x, nativeDeref(y), width, Scale(28n)),
            text: Locale("voice_narration_label")
        }}
    />;
    nativeSet(y, nativeDeref(y) + Scale(36n));
    let toggled = Toggle({
        session: State_settings_view.settings.session,
        props: {
            id: 15422n,
            bounds: Bounds(x, nativeDeref(y), width, Scale(44n)),
            value: State_settings_view.settings.narration_enabled,
            off_label: Locale("toggle_off"),
            on_label: Locale("toggle_on")
        }
    });
    if (toggled.changed) {
        Ask(PRACTICE_SETTINGS_NARRATION, toggled.value ? 1n : 0n);
    }
    nativeSet(y, nativeDeref(y) + Scale(56n));
    if (!State_settings_view.settings.narration_enabled) {
        return;
    }
    if (State_settings_view.settings.narration_voices) {
        let voices: [NativeSegmentedControl.SegmentOption, NativeSegmentedControl.SegmentOption] = [
            { label: Locale("practice_voice_female") },
            { label: Locale("practice_voice_male") }
        ];
        let voice = SegmentedControl({
            session: State_settings_view.settings.session,
            props: {
                key:
                    NativeLayout.KeyHash("inbe/practice/customize/voice") +
                    u64(State_settings_view.settings.practice),
                bounds: Bounds(x, nativeDeref(y), width, Scale(42n)),
                height: Scale(42n),
                selected_index: State_settings_view.settings.narration_male ? 1n : 0n,
                has_selection: true
            },
            options: nativeSlice(voices)
        });
        if (voice.changed) {
            Ask(PRACTICE_SETTINGS_VOICE, voice.selected_index);
        }
        nativeSet(y, nativeDeref(y) + Scale(42n + 12n));
    }
    NarrationLanguages(x, width, y);
}

export function MovementVolume(x: s32, width: s32, y: NativeRef<s32>, cue: boolean): void {
    let value = cue
        ? State_settings_view.settings.cue_volume
        : State_settings_view.settings.music_volume;
    let slider = DiscreteSlider({
        session: State_settings_view.settings.session,
        props: {
            id: cue
                ? 15421n
                : State_settings_view.settings.practice ===
                    s32(ExerciseType.EXERCISE_SUN_SALUTATION)
                  ? 614n
                  : 15420n,
            bounds: Bounds(x, nativeDeref(y), width, Scale(56n)),
            label: Locale(cue ? "cue_volume_label" : "music_volume_label"),
            value_text: FormatValue(value),
            value: value,
            min: 0n,
            max: 100n
        }
    });
    if (slider.changed) {
        Ask(cue ? PRACTICE_SETTINGS_CUE_VOLUME : PRACTICE_SETTINGS_MUSIC_VOLUME, slider.value);
    }
    nativeSet(y, nativeDeref(y) + Scale(74n));
}

export function SunSetting(
    id: s32,
    key: string,
    value: s32,
    minimum: s32,
    maximum: s32,
    action: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>
): void {
    let shown = FormatValue(value);
    if (id !== 610n) {
        shown = CountText(Locale("sun_salutation_seconds_per_breath"), value);
    }
    let slider = DiscreteSlider({
        session: State_settings_view.settings.session,
        props: {
            id: id,
            bounds: Bounds(x, nativeDeref(y), width, Scale(56n)),
            label: Locale(key),
            value_text: shown,
            value: value,
            min: minimum,
            max: maximum
        }
    });
    if (slider.changed) {
        Ask(action, slider.value);
    }
    nativeSet(y, nativeDeref(y) + Scale(74n));
}

export function Sun(x: s32, width: s32, y: NativeRef<s32>): void {
    let fill = State_settings_view.settings.canvas_color;
    fill.r = fill.r > 6n ? fill.r - u8(6n) : u8(0n);
    fill.g = fill.g > 6n ? fill.g - u8(6n) : u8(0n);
    fill.b = fill.b > 6n ? fill.b - u8(6n) : u8(0n);
    <Box
        session={State_settings_view.settings.session}
        props={{ bounds: Bounds(x, nativeDeref(y), width, Scale(76n)), fill: fill }}
    />;
    <Text
        session={State_settings_view.settings.session}
        props={{
            bounds: Bounds(x + Scale(14n), nativeDeref(y) + Scale(10n), 0n, 0n),
            text: Locale("sun_salutation_duration_label"),
            size: State_settings_view.settings.small_font
        }}
    />;
    <Text
        session={State_settings_view.settings.session}
        props={{
            bounds: Bounds(x + Scale(14n), nativeDeref(y) + Scale(35n), 0n, 0n),
            text: SunDuration(),
            size: State_settings_view.settings.font + Scale(3n)
        }}
    />;
    nativeSet(y, nativeDeref(y) + Scale(100n));
    Label(Locale("sun_salutation_timing_label"), x, nativeDeref(y));
    nativeSet(y, nativeDeref(y) + Scale(32n));
    SunSetting(
        610n,
        "sun_salutation_repetitions_label",
        State_settings_view.settings.sun_repetitions,
        2n,
        12n,
        PRACTICE_SETTINGS_SUN_REPETITIONS,
        x,
        width,
        y
    );
    SunSetting(
        611n,
        "sun_salutation_start_speed_label",
        State_settings_view.settings.sun_start_seconds,
        State_settings_view.settings.sun_seconds_min,
        State_settings_view.settings.sun_seconds_max,
        PRACTICE_SETTINGS_SUN_START,
        x,
        width,
        y
    );
    SunSetting(
        612n,
        "sun_salutation_end_speed_label",
        State_settings_view.settings.sun_end_seconds,
        State_settings_view.settings.sun_seconds_min,
        State_settings_view.settings.sun_start_seconds,
        PRACTICE_SETTINGS_SUN_END,
        x,
        width,
        y
    );
    let hint = Locale("sun_salutation_tempo_preview_hint");
    let height = ParagraphHeight(hint, width, State_settings_view.settings.small_font, Scale(3n));
    <Text
        session={State_settings_view.settings.session}
        props={{
            text: hint,
            bounds: Bounds(x, nativeDeref(y), width, height),
            size: State_settings_view.settings.small_font
        }}
    />;
    nativeSet(y, nativeDeref(y) + (height + Scale(24n)));
    Label(Locale("sun_salutation_character_label"), x, nativeDeref(y));
    let options: [NativeDropdown.Option, NativeDropdown.Option] = [
        { label: Locale("sun_salutation_character_bun_woman") },
        { label: Locale("sun_salutation_character_short_hair_man") }
    ];
    let picked = Dropdown({
        session: State_settings_view.settings.session,
        props: {
            id: 613n,
            bounds: Bounds(x, nativeDeref(y) + Scale(26n), width, Scale(44n)),
            selected_index: State_settings_view.settings.sun_character
        },
        options: nativeSlice(options)
    });
    if (picked.changed) {
        Ask(PRACTICE_SETTINGS_SUN_CHARACTER, picked.selected_index);
    }
    nativeSet(y, nativeDeref(y) + Scale(86n));
    Label(Locale("settings_tab_audio"), x, nativeDeref(y));
    nativeSet(y, nativeDeref(y) + Scale(32n));
    MovementVolume(x, width, y, false);
    Music(x, width, y);
    nativeSet(y, nativeDeref(y) + Scale(12n));
    Narration(x, width, y);
}

export function TaiAudio(x: s32, width: s32, y: s32): void {
    Music(x, width, nativeRef(y));
    y = y + Scale(12n);
    MovementVolume(x, width, nativeRef(y), false);
    MovementVolume(x, width, nativeRef(y), true);
    Narration(x, width, nativeRef(y));
    let text = Locale("tai_chi_narration_hint");
    <Text
        session={State_settings_view.settings.session}
        props={{
            text: text,
            bounds: Bounds(
                x,
                y,
                width,
                ParagraphHeight(text, width, State_settings_view.settings.font, Scale(3n))
            ),
            size: State_settings_view.settings.font,
            disabled: true
        }}
    />;
}

export function TaiCharacters(bounds: Rectangle): void {
    let gap = Scale(16n);
    let card_w = (s32(bounds.width) - gap) / 2n;
    let card_h = Scale(280n);
    for (
        let character = s32(0n);
        character < State_settings_view.settings.tai_character_count;
        character += s32(1)
    ) {
        let title = ReadPracticeCharacterHost(character).label;
        let key = NativeLayout.KeyHash("inbe/tai_chi/character-card") + u64(character) * u64(4096n);
        let card = Bounds(
            s32(bounds.x) + (character % 2n) * (card_w + gap),
            s32(bounds.y) + (character / 2n) * (card_h + gap),
            card_w,
            card_h
        );
        if (
            Button({
                session: State_settings_view.settings.session,
                props: {
                    key: key,
                    bounds: card,
                    selected: State_settings_view.settings.tai_character === character,
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }
            })
        ) {
            Ask(PRACTICE_SETTINGS_TAI_CHARACTER, character);
        }
        PracticeFigure({
            practice: s32(ExerciseType.EXERCISE_TAI_CHI),
            preview: true,
            index: State_settings_view.settings.tai_preview_item,
            character: character,
            bounds: {
                x: card.x + float32(Scale(14n)),
                y: card.y + float32(Scale(14n)),
                width: card.width - float32(Scale(28n)),
                height: card.height - float32(Scale(94n))
            },
            key: key + u64(1000n),
            alt_text: title
        });
        <Text
            session={State_settings_view.settings.session}
            props={{
                text: title,
                size: State_settings_view.settings.font,
                bounds: {
                    x: card.x + float32(Scale(14n)),
                    y: card.y + card.height - float32(Scale(76n)),
                    width: card.width - float32(Scale(28n)),
                    height: float32(Scale(44n))
                }
            }}
        />;
    }
}

export function TaiCustomize(): void {
    let width = State_settings_view.settings.view_width - Scale(32n);
    if (width > Scale(940n)) {
        width = Scale(940n);
    }
    let height = State_settings_view.settings.view_height - Scale(48n);
    if (height > Scale(740n)) {
        height = Scale(740n);
    }
    let frame = ResolvedModal({
        session: State_settings_view.settings.session,
        props: {
            key: NativeLayout.KeyHash("inbe/tai_chi/modal"),
            title: Locale("practice_configure_button"),
            width: width,
            height: height,
            scale: State_settings_view.settings.scale,
            title_at_start: true,
            strong_title: true,
            has_right_action: true,
            right_label: Locale("close_button")
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let bounds = frame.layout.content;
            let gap = Scale(24n);
            let wide = bounds.width >= float32(Scale(700n));
            let audio_w = s32(bounds.width) - Scale(10n);
            let character_w = audio_w;
            if (wide) {
                character_w = (audio_w - gap) / 2n;
                audio_w = audio_w - (character_w + gap);
            }
            let audio_h = TaiAudioHeight(audio_w);
            let rows = (State_settings_view.settings.tai_character_count + 1n) / 2n;
            if (rows < 1n) {
                rows = 1n;
            }
            let title = Locale("tai_chi_character_label");
            let title_font = State_settings_view.settings.font + Scale(2n);
            let title_h = ParagraphHeight(title, character_w, title_font, Scale(3n));
            let character_h = title_h + Scale(12n) + rows * Scale(280n) + (rows - 1n) * Scale(16n);
            let content_h = audio_h + gap + character_h;
            if (wide) {
                content_h = audio_h > character_h ? audio_h : character_h;
            }
            let scrolled = Scroll({
                session: State_settings_view.settings.session,
                props: {
                    key: NativeLayout.KeyHash("inbe/tai_chi/customize/scroll"),
                    bounds: bounds,
                    content_height: content_h + Scale(16n),
                    scroll_offset: State_settings_view.settings.scroll
                },
                children: (scrolled: NativeScroll.ScrollResult): void => {
                    State_settings_view.settings.scroll = scrolled.scroll_offset;
                    let x = s32(scrolled.content.x);
                    let y = s32(scrolled.content.y);
                    let character_y = wide ? y : y + audio_h + gap;
                    let audio_x = wide ? x + character_w + gap : x;
                    TaiAudio(audio_x, audio_w, y);
                    <Text
                        session={State_settings_view.settings.session}
                        props={{
                            text: title,
                            size: title_font,
                            bounds: Bounds(x, character_y, character_w, title_h)
                        }}
                    />;
                    TaiCharacters(
                        Bounds(
                            x,
                            character_y + title_h + Scale(12n),
                            character_w,
                            character_h - title_h - Scale(12n)
                        )
                    );
                }
            });
            if (!scrolled.opened) {
                State_settings_view.settings.scroll = scrolled.scroll_offset;
            }
        }
    });
    if (frame.dismissed || frame.right_clicked) {
        Ask(PRACTICE_SETTINGS_BACK, 0n);
        return;
    }
}

export function Settings(): void {
    if (State_settings_view.settings.practice === s32(ExerciseType.EXERCISE_TAI_CHI)) {
        TaiCustomize();
        return;
    }
    let options = NewOptions1NativeDropdownOption();
    let bar = TitleBar({
        session: State_settings_view.settings.session,
        props: {
            title: Locale("practice_configure_button"),
            height: State_settings_view.settings.title_height,
            has_leading_action: true,
            leading_label: Locale("back_button")
        },
        options: nativeSlice(options, 0n, 0n)
    });
    if (bar.clicked_leading) {
        Ask(PRACTICE_SETTINGS_BACK, 0n);
        return;
    }
    let padding = NativeLayout.PageSidePaddingFor(State_settings_view.settings.view_width);
    if (State_settings_view.settings.practice === s32(ExerciseType.EXERCISE_ASTRAL_PROJECTION)) {
        padding = Scale(16n);
    }
    let max_width = Scale(State_settings_view.SETTINGS_CONTENT_MAX_WIDTH);
    let available = State_settings_view.settings.view_width - padding * 2n;
    if (max_width > available) {
        max_width = available;
    }
    if (State_settings_view.settings.practice === s32(ExerciseType.EXERCISE_WIM_HOF)) {
        if (max_width < available && State_settings_view.settings.view_width <= Scale(520n)) {
            max_width = available;
        }
        if (max_width < Scale(240n)) {
            max_width = available;
        }
    } else if (max_width < Scale(320n)) {
        max_width = Scale(320n);
    }
    let x = padding;
    let width = State_settings_view.settings.view_width - padding * 2n;
    if (width > max_width) {
        x = x + (width - max_width) / 2n;
        width = max_width;
    }
    let scrolled = Scroll({
        session: State_settings_view.settings.session,
        props: {
            key: ScrollKey(),
            bounds: Bounds(
                0n,
                State_settings_view.settings.scroll_y,
                State_settings_view.settings.view_width,
                State_settings_view.settings.scroll_height
            ),
            content_height: ContentHeight(width),
            scroll_offset: State_settings_view.settings.scroll
        },
        children: (scrolled: NativeScroll.ScrollResult): void => {
            State_settings_view.settings.scroll = scrolled.scroll_offset;
            Page(x, width, s32(scrolled.content.y));
        }
    });
    if (!scrolled.opened) {
        State_settings_view.settings.scroll = scrolled.scroll_offset;
    }
    if (
        State_settings_view.settings.practice === s32(ExerciseType.EXERCISE_WIM_HOF) &&
        State_settings_view.settings.whm_editor
    ) {
        WhmStartSpeedEditor();
    }
}

export function SessionAudio(): void {
    let width = State_settings_view.settings.view_width - Scale(32n);
    if (width > Scale(560n)) {
        width = Scale(560n);
    }
    let height = State_settings_view.settings.view_height - Scale(32n);
    if (height > Scale(680n)) {
        height = Scale(680n);
    }
    let frame = ResolvedModal({
        session: State_settings_view.settings.session,
        props: {
            key: NativeLayout.KeyHash("inbe/practice/session-audio"),
            title: Locale("practice_background_music_label"),
            width: width,
            height: height,
            scale: State_settings_view.settings.scale,
            title_at_start: true,
            strong_title: true,
            has_right_action: true,
            right_label: Locale("close_button")
        },
        children: (frame: NativeModal.ModalFrameResult): void => {
            let bounds = frame.layout.content;
            let count = State_settings_view.settings.music_count;
            if (count < 0n) {
                count = 0n;
            } else if (count > SETTINGS_MUSIC_TRACK_MAX) {
                count = SETTINGS_MUSIC_TRACK_MAX;
            }
            let content_width = s32(bounds.width);
            let status_height: s32 = s32(0n);
            if (
                State_settings_view.settings.music_show_status &&
                State_settings_view.settings.music_status.count > 0n
            ) {
                status_height =
                    ParagraphHeight(
                        State_settings_view.settings.music_status,
                        content_width,
                        State_settings_view.settings.font,
                        0n
                    ) + Scale(12n);
            }
            let attribution_height = AttributionHeight(content_width);
            let content_height = Scale(74n * 2n + 34n + 52n * (count + 1n) + 16n);
            if (State_settings_view.settings.music_selection > 0n) {
                content_height = content_height + (status_height + attribution_height + Scale(12n));
                if (
                    State_settings_view.settings.music_built_in &&
                    !State_settings_view.settings.music_installed
                ) {
                    content_height = content_height + Scale(56n);
                }
                if (State_settings_view.settings.music_downloading) {
                    content_height = content_height + Scale(28n);
                }
            }
            let scrolled = Scroll({
                session: State_settings_view.settings.session,
                props: {
                    key: NativeLayout.KeyHash("inbe/practice/session-audio/scroll"),
                    bounds: bounds,
                    content_height: content_height,
                    scroll_offset: State_settings_view.settings.scroll
                },
                children: (scrolled: NativeScroll.ScrollResult): void => {
                    State_settings_view.settings.scroll = scrolled.scroll_offset;
                    let x = s32(scrolled.content.x);
                    let y = s32(scrolled.content.y);
                    MovementVolume(x, content_width, nativeRef(y), true);
                    MovementVolume(x, content_width, nativeRef(y), false);
                    Label(Locale("practice_background_music_label"), x, y);
                    y = y + Scale(34n);
                    for (let index = s32(0n); index <= count; index += s32(1)) {
                        let label = Locale("audio_music_none_option");
                        if (index > 0n) {
                            label = ReadPracticeMusicTrackHost(index - 1n).label;
                        }
                        let selected = State_settings_view.settings.music_selection === index;
                        if (
                            Button({
                                session: State_settings_view.settings.session,
                                props: {
                                    key:
                                        NativeLayout.KeyHash("inbe/practice/session-audio/track") +
                                        u64(index),
                                    bounds: Bounds(x, y, content_width, Scale(44n)),
                                    label: label,
                                    selected: selected,
                                    fit_content: true,
                                    tone: selected
                                        ? ButtonTone.ButtonToneAccent
                                        : ButtonTone.ButtonToneNeutral,
                                    emphasis: selected
                                        ? ButtonEmphasis.ButtonEmphasisFilled
                                        : ButtonEmphasis.ButtonEmphasisSoft
                                }
                            })
                        ) {
                            Ask(PRACTICE_SETTINGS_MUSIC, index);
                        }
                        y = y + Scale(52n);
                    }
                    if (State_settings_view.settings.music_selection > 0n) {
                        if (
                            State_settings_view.settings.music_built_in &&
                            !State_settings_view.settings.music_installed
                        ) {
                            if (
                                Button({
                                    session: State_settings_view.settings.session,
                                    props: {
                                        key: NativeLayout.KeyHash(
                                            "inbe/practice/session-audio/download"
                                        ),
                                        bounds: Bounds(x, y, content_width, Scale(44n)),
                                        label: Locale("meditation_music_download_button"),
                                        disabled: State_settings_view.settings.music_downloading,
                                        tone: ButtonTone.ButtonToneAccent,
                                        emphasis: ButtonEmphasis.ButtonEmphasisSoft
                                    }
                                })
                            ) {
                                Ask(PRACTICE_SETTINGS_MUSIC_DOWNLOAD, 0n);
                            }
                            y = y + Scale(56n);
                        }
                        if (status_height > 0n) {
                            <Text
                                session={State_settings_view.settings.session}
                                props={{
                                    bounds: Bounds(x, y, content_width, status_height - Scale(12n)),
                                    text: State_settings_view.settings.music_status,
                                    wrap: Wrap.TextWrapAuto
                                }}
                            />;
                            y = y + status_height;
                        }
                        if (State_settings_view.settings.music_downloading) {
                            MusicProgress(x, y, content_width);
                            y = y + Scale(28n);
                        }
                        <Text
                            session={State_settings_view.settings.session}
                            props={{
                                bounds: Bounds(x, y, content_width, attribution_height),
                                text: Locale("meditation_music_attribution"),
                                size: SETTINGS_TEXT_12,
                                wrap: Wrap.TextWrapAuto
                            }}
                        />;
                    }
                }
            });
            if (!scrolled.opened) {
                State_settings_view.settings.scroll = scrolled.scroll_offset;
            }
        }
    });
    if (frame.dismissed || frame.right_clicked) {
        Ask(PRACTICE_SETTINGS_BACK, 0n);
        return;
    }
}
