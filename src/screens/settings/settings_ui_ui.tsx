import { SettingsUiNewNumberBuffer } from "settings_ui";
// Authored UI composition; native application state remains in settings_ui.zi.
import * as NativeFieldset from "kryon/fieldset";
import * as NativeProgress from "kryon/progress";
import * as NativeSeparator from "kryon/separator";
import * as NativeSlider from "kryon/slider";
import * as NativeText from "kryon/text";
import * as NativeToggle from "kryon/toggle";
import { save_settings } from "app_settings";
import { InnerBreeze } from "app_types";
import { Rectangle } from "kryon/geometry";
import { SemanticKind } from "kryon/semantic";
import { SessionValid } from "kryon/session";
import { TextAlign } from "kryon/text_align";
import { Wrap } from "kryon/text_props";
import { Fieldset } from "kryon/tsx/fieldset";
import { Progress } from "kryon/tsx/progress";
import { Separator } from "kryon/tsx/separator";
import { Text } from "kryon/tsx/text";
import { Toggle } from "kryon/tsx/toggle";
import { AppFontSize, AppParagraphHeight, AppScale, AppSmallFontSize } from "metrics";
import { NativePresent } from "native_flags";
import { SettingsSection } from "settings_types";
import {
    audio_meter_height,
    settings_choice_control_width,
    settings_choice_row_height,
    settings_choice_row_stacked,
    settings_section_inner_width,
    settings_section_inset,
    settings_section_padding,
    settings_section_title_height,
    toggle_row_height,
    toggle_switch_height,
    toggle_switch_width
} from "settings_ui";
import { AppTextFromCString, FormatNumberTemplate, FrameTextHold } from "text_buffers";

export function settings_section_beginView(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    title: string,
    body_height: s32
): SettingsSection {
    let section: SettingsSection = {};
    section.inner_x = x + settings_section_inset(width);
    section.inner_width = settings_section_inner_width(width);
    if (title !== "") {
        let heading: NativeText.Props = {};
        heading.text = title;
        heading.size = AppSmallFontSize();
        heading.wrap = Wrap.TextWrapNone;
        heading.semantic_kind = SemanticKind.SemanticHeading;
        heading.heading_level = 2n;
        heading.bounds = {
            x: float32(x + AppScale(4n)),
            y: float32(nativeDeref(y)),
            width: float32(width - AppScale(4n)),
            height: float32(AppScale(22n))
        };
        <Text session={app.ui.session} props={heading} />;
        nativeDeref(y) = nativeDeref(y) + settings_section_title_height();
    }
    let frame: NativeFieldset.Props = {};
    frame.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y)),
        width: float32(width),
        height: float32(body_height + settings_section_padding() * 2n)
    };
    <Fieldset session={app.ui.session} props={frame} />;
    nativeDeref(y) = nativeDeref(y) + settings_section_padding();
    return section;
}

export function settings_row_dividerView(
    app: NativeRef<InnerBreeze>,
    section: SettingsSection,
    y: s32
): void {
    let line: NativeSeparator.Props = {};
    line.bounds = {
        x: float32(section.inner_x),
        y: float32(y),
        width: float32(section.inner_width),
        height: 1.0
    };
    <Separator session={app.ui.session} props={line} />;
}

export function settings_choice_rowView(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    label: string
): Rectangle {
    let control_height = AppScale(36n);
    let text: NativeText.Props = {};
    text.text = label;
    text.size = AppFontSize();
    text.wrap = Wrap.TextWrapNone;
    let control: Rectangle = {};
    if (settings_choice_row_stacked(label, width)) {
        let label_height = AppParagraphHeight(label, width, AppFontSize(), 0n);
        if (label_height < AppScale(22n)) {
            label_height = AppScale(22n);
        }
        text.wrap = Wrap.TextWrapAuto;
        text.bounds = {
            x: float32(x),
            y: float32(nativeDeref(y) + AppScale(10n)),
            width: float32(width),
            height: float32(label_height)
        };
        control = {
            x: float32(x),
            y: float32(nativeDeref(y) + AppScale(16n) + label_height),
            width: float32(width),
            height: float32(control_height)
        };
    } else {
        let row_height = settings_choice_row_height(label, width);
        let control_width = settings_choice_control_width(width);
        text.bounds = {
            x: float32(x),
            y: float32(nativeDeref(y)),
            width: float32(width - control_width - AppScale(16n)),
            height: float32(row_height)
        };
        text.vertical_align = TextAlign.TextAlignCenter;
        control = {
            x: float32(x + width - control_width),
            y: float32(nativeDeref(y) + (row_height - control_height) / 2n),
            width: float32(control_width),
            height: float32(control_height)
        };
    }
    <Text session={app.ui.session} props={text} />;
    nativeDeref(y) = nativeDeref(y) + settings_choice_row_height(label, width);
    return control;
}

export function draw_toggle_row(
    app: NativeRef<InnerBreeze>,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    label: string,
    value: NativeRef<s32>
): boolean {
    if (
        !NativePresent(app) ||
        !NativePresent(y) ||
        !NativePresent(value) ||
        !SessionValid(app.ui.session)
    ) {
        return false;
    }
    let row_height = toggle_row_height(label, width);
    let toggle_width = toggle_switch_width();
    let toggle_height = toggle_switch_height();
    let gap = AppScale(18n);
    let label_width = width - toggle_width - gap;
    if (label_width < AppScale(120n)) {
        label_width = width;
    }
    let label_height = AppParagraphHeight(label, label_width, 0n, 0n);
    let toggle_x = x;
    let toggle_y = nativeDeref(y) + (row_height - toggle_height) / 2n;
    let label_y: s32 = s32(0);
    if (label_width < width) {
        label_y = nativeDeref(y) + (row_height - label_height) / 2n;
        toggle_x = x + width - toggle_width;
    } else {
        label_y = nativeDeref(y) + AppScale(8n);
        toggle_y = label_y + label_height + AppScale(8n);
    }
    let text: NativeText.Props = {};
    text.text = label;
    text.size = AppFontSize();
    text.wrap = Wrap.TextWrapAuto;
    text.bounds = {
        x: float32(x),
        y: float32(label_y),
        width: float32(label_width),
        height: float32(label_height)
    };
    <Text session={app.ui.session} props={text} />;
    let props: NativeToggle.Props = {};
    props.id = s32(62000n) + nativeDeref(y);
    props.bounds = {
        x: float32(toggle_x),
        y: float32(toggle_y),
        width: float32(toggle_width),
        height: float32(toggle_height)
    };
    props.value = nativeDeref(value) !== 0n;
    props.label = label;
    let result = Toggle({ session: app.ui.session, props: props });
    nativeDeref(y) = nativeDeref(y) + row_height;
    if (result.changed) {
        nativeDeref(value) = result.value ? 1n : 0n;
    }
    return result.changed;
}

export function commit_slider_rowView(
    app: NativeRef<InnerBreeze>,
    id: s32,
    x: s32,
    width: s32,
    y: NativeRef<s32>,
    row_height: s32,
    label: string,
    minimum: s32,
    maximum: s32,
    value: NativeRef<s32>,
    suffix: string,
    save_now: s32
): s32 {
    if (
        !NativePresent(app) ||
        !NativePresent(y) ||
        !NativePresent(value) ||
        !SessionValid(app.ui.session)
    ) {
        return 0n;
    }
    let template: string = "%d";
    if (suffix === "s") {
        template = "%ds";
    }
    if (suffix === "x") {
        template = "%dx";
    }
    let number_buffer = SettingsUiNewNumberBuffer();
    FormatNumberTemplate(template, nativeDeref(value), nativeSlice(number_buffer));
    let number = FrameTextHold(
        nativeRef(app.ui.frame_text),
        AppTextFromCString(nativeRef(nativeAt(number_buffer, 0n)), 32n)
    );
    let label_props: NativeText.Props = {};
    label_props.text = label;
    label_props.size = AppSmallFontSize();
    label_props.wrap = Wrap.TextWrapNone;
    label_props.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y)),
        width: float32(width - AppScale(64n)),
        height: float32(AppScale(20n))
    };
    <Text session={app.ui.session} props={label_props} />;
    let number_props: NativeText.Props = {};
    number_props.text = number;
    number_props.size = AppSmallFontSize();
    number_props.wrap = Wrap.TextWrapNone;
    number_props.align = TextAlign.TextAlignEnd;
    number_props.bounds = {
        x: float32(x + width - AppScale(64n)),
        y: float32(nativeDeref(y)),
        width: float32(AppScale(64n)),
        height: float32(AppScale(20n))
    };
    <Text session={app.ui.session} props={number_props} />;
    let slider: NativeSlider.DiscreteSliderProps = {};
    slider.id = id;
    slider.bounds = {
        x: float32(x),
        y: float32(nativeDeref(y) + AppScale(20n)),
        width: float32(width),
        height: float32(AppScale(36n))
    };
    slider.semantic_label = label;
    slider.value = nativeDeref(value);
    slider.min = minimum;
    slider.max = maximum;
    let result = NativeSlider.DiscreteSlider(app.ui.session, slider);
    nativeDeref(y) = nativeDeref(y) + row_height;
    if (!result.changed) {
        return 0n;
    }
    nativeDeref(value) = result.value;
    app.settings_dirty = 1n;
    if (save_now !== 0n) {
        save_settings(app);
    }
    return 1n;
}

export function draw_audio_meterView(
    app: NativeRef<InnerBreeze>,
    level: float32,
    x: s32,
    y: s32,
    width: s32,
    label: string
): s32 {
    if (!NativePresent(app) || width <= 0n || !SessionValid(app.ui.session)) {
        return audio_meter_height();
    }
    if (level < 0.0) {
        level = 0.0;
    }
    if (level > 1.0) {
        level = 1.0;
    }
    let text: NativeText.Props = {};
    text.text = label;
    text.size = AppSmallFontSize();
    text.wrap = Wrap.TextWrapNone;
    text.bounds = {
        x: float32(x),
        y: float32(y),
        width: float32(width),
        height: float32(AppScale(18n))
    };
    <Text session={app.ui.session} props={text} />;
    let progress: NativeProgress.Props = {};
    progress.bounds = {
        x: float32(x),
        y: float32(y + AppScale(18n)),
        width: float32(width),
        height: float32(AppScale(10n))
    };
    progress.min = 0n;
    progress.max = 1000n;
    progress.value = s32(level * 1000.0);
    <Progress session={app.ui.session} props={progress} />;
    return audio_meter_height();
}
