// Authored UI composition; native application state remains in astral_projection_pages.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as State_astral_projection from "astral_projection";
import { InnerBreeze } from "app_types";
import {
    AstralCatalogueLoad,
    AstralLegacyAvailable,
    AstralSelection,
    AstralStartSelected,
    AstralText
} from "astral_projection";
import {
    AstralManualClose,
    AstralParagraphHeight,
    NewDurations,
    NewHeights
} from "astral_projection_pages";
import { AstralPreviewDraw } from "astral_scene_view";
import { ButtonTone } from "kryon/control_props";
import { Rectangle } from "kryon/geometry";
import { Wrap } from "kryon/text_props";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Text } from "kryon/tsx/text";
import { LocaleText } from "locale";
import { AppFontSize, AppScale, AppSmallFontSize, MetricsScale } from "metrics";
import { NativePresent } from "native_flags";
import { PracticeManualDraw } from "practice_manual_host";
import { save_settings } from "practice_settings_host";
import { PRACTICE_MANUAL_CLOSE, PRACTICE_MANUAL_START } from "practice_types";
import { TextFromCString } from "std/byte_text_linux";
import { TextUntilNul } from "std/text_buffer";
import { AppCopyText, FormatNumberTemplate } from "text_buffers";

export function AstralManualDrawView(app: NativeRef<InnerBreeze>): void {
    if (!NativePresent(app)) {
        return;
    }
    if (app.modal.active === 0n && AstralLegacyAvailable()) {
        let action = PracticeManualDraw(app);
        if (action === PRACTICE_MANUAL_CLOSE) {
            AstralManualClose(app, 0n);
        } else if (action === PRACTICE_MANUAL_START) {
            AstralStartSelected(app, true);
        }
        return;
    }
    let available = AstralCatalogueLoad();
    let frame_props: NativeModal.Props = {};
    frame_props.key = NativeLayout.KeyHash("astral/start-modal");
    frame_props.title = LocaleText("exercise_astral_projection");
    frame_props.width = AppScale(760n);
    frame_props.height = app.ui.view_height - AppScale(32n);
    if (frame_props.height > AppScale(840n)) {
        frame_props.height = AppScale(840n);
    }
    frame_props.scale = MetricsScale();
    frame_props.has_right_action = true;
    frame_props.right_label = LocaleText("close_button");
    frame_props.right_image.asset_path = "icons/ui.webp";
    frame_props.right_image.alt_text = frame_props.right_label;
    frame_props.right_image.source = { x: 448.0, y: 384.0, width: 64.0, height: 64.0 };
    let frame = NativeModal.Draw(app.ui.session, frame_props);
    if (frame.dismissed || frame.right_clicked) {
        AstralManualClose(app, 0n);
        return;
    }
    if (!frame.opened) {
        return;
    }
    let content = frame.layout.content;
    let left = s32(content.x);
    let width = s32(content.width);
    let top = s32(content.y);
    let bottom = s32(content.y + content.height) - AppScale(52n);
    if (width <= 0n || bottom <= top) {
        End(app.ui.session);
        return;
    }
    if (!available) {
        <Text
            session={app.ui.session}
            props={{
                text: LocaleText("astral_content_unavailable"),
                bounds: {
                    x: content.x,
                    y: content.y,
                    width: content.width,
                    height: content.height
                },
                size: AppFontSize(),
                wrap: Wrap.TextWrapAuto
            }}
        />;
        End(app.ui.session);
        return;
    }
    if (State_astral_projection.astral_content_error) {
        let message = LocaleText("astral_content_unavailable");
        let height = AstralParagraphHeight(app, message, width);
        <Text
            session={app.ui.session}
            props={{
                text: message,
                bounds: {
                    x: content.x,
                    y: content.y,
                    width: content.width,
                    height: float32(height)
                },
                size: AppFontSize(),
                wrap: Wrap.TextWrapAuto
            }}
        />;
        top = top + (height + AppScale(12n));
    }
    let pad = AppScale(16n);
    let selected = AstralSelection(app);
    let preview_height = AppScale(112n);
    if (bottom - top < AppScale(280n)) {
        preview_height = AppScale(64n);
    }
    if (bottom - top >= preview_height + AppScale(72n)) {
        AstralPreviewDraw(
            app.ui.session,
            selected,
            {
                x: float32(left),
                y: float32(top),
                width: float32(width),
                height: float32(preview_height)
            },
            app.dark_mode !== 0n,
            NativeLayout.KeyHash("astral/preview"),
            AstralText(
                TextFromCString(
                    nativeRef(
                        nativeAt(
                            nativeAt(State_astral_projection.astral_catalogue.practices, selected)
                                .title_key,
                            0n
                        )
                    )
                )
            )
        );
        top = top + preview_height;
    }
    let showing_guide = app.tutorial_step === 1n;
    let heights = NewHeights();
    let durations = NewDurations();
    let total: s32 = s32(0n);
    for (
        let index = s32(0n);
        index < State_astral_projection.astral_catalogue.count;
        index += s32(1)
    ) {
        let row = nativeAt(State_astral_projection.astral_catalogue.practices, index);
        let title = AstralText(TextFromCString(nativeRef(nativeAt(row.title_key, 0n))));
        let description = AstralText(TextFromCString(nativeRef(nativeAt(row.description_key, 0n))));
        nativeSet(
            heights,
            index,
            AstralParagraphHeight(app, title, width - pad * 2n) +
                AstralParagraphHeight(app, description, width - pad * 2n) +
                AppScale(72n)
        );
        total = total + (nativeAt(heights, index) + AppScale(12n));
    }
    let guide = AstralText(
        TextFromCString(
            nativeRef(
                nativeAt(
                    nativeAt(State_astral_projection.astral_catalogue.practices, selected)
                        .guide_key,
                    0n
                )
            )
        )
    );
    let guide_h = AstralParagraphHeight(app, guide, width);
    if (showing_guide) {
        total = guide_h + AppScale(24n);
    }
    if (!showing_guide && State_astral_projection.astral_reveal_selection) {
        app.manual_scroll = 0n;
        for (let index = s32(0n); index < selected; index += s32(1)) {
            app.manual_scroll = app.manual_scroll + (nativeAt(heights, index) + AppScale(12n));
        }
        State_astral_projection.astral_reveal_selection = false;
    }
    let scrolled = NativeScroll.Draw(app.ui.session, {
        key: NativeLayout.KeyHash("astral/selection"),
        bounds: {
            x: float32(left),
            y: float32(top + AppScale(12n)),
            width: float32(width),
            height: float32(bottom - top - AppScale(24n))
        },
        content_height: total,
        scroll_offset: app.manual_scroll
    });
    app.manual_scroll = scrolled.scroll_offset;
    if (scrolled.opened) {
        let y = s32(scrolled.content.y);
        if (!showing_guide) {
            for (
                let index = s32(0n);
                index < State_astral_projection.astral_catalogue.count;
                index += s32(1)
            ) {
                let row = nativeAt(State_astral_projection.astral_catalogue.practices, index);
                let title = AstralText(TextFromCString(nativeRef(nativeAt(row.title_key, 0n))));
                let description = AstralText(
                    TextFromCString(nativeRef(nativeAt(row.description_key, 0n)))
                );
                let card: Rectangle = {
                    x: float32(left),
                    y: float32(y),
                    width: float32(width),
                    height: float32(
                        AstralParagraphHeight(app, title, width - pad * 2n) + AppScale(24n)
                    )
                };
                if (
                    Button({
                        session: app.ui.session,
                        props: {
                            key: NativeLayout.KeyHash("astral/exercise") + u64(index),
                            bounds: card,
                            selected: index === selected,
                            tone:
                                index === selected
                                    ? ButtonTone.ButtonToneAccent
                                    : ButtonTone.ButtonToneNeutral,
                            label: title,
                            fit_content: true
                        }
                    })
                ) {
                    AppCopyText(
                        TextFromCString(nativeRef(nativeAt(row.id, 0n))),
                        nativeSlice(app.astral_projection_exercise)
                    );
                    save_settings(app);
                    State_astral_projection.astral_content_error = false;
                }
                let title_h = AstralParagraphHeight(app, title, width - pad * 2n);
                <Text
                    session={app.ui.session}
                    props={{
                        text: description,
                        bounds: {
                            x: float32(left + pad),
                            y: float32(y + title_h + AppScale(24n)),
                            width: float32(width - pad * 2n),
                            height: float32(
                                AstralParagraphHeight(app, description, width - pad * 2n)
                            )
                        },
                        size: AppFontSize(),
                        wrap: Wrap.TextWrapAuto
                    }}
                />;
                FormatNumberTemplate(
                    LocaleText("practice_home_minutes"),
                    row.duration / 60n,
                    nativeSlice(nativeAt(durations, index))
                );
                <Text
                    session={app.ui.session}
                    props={{
                        text: TextUntilNul(nativeSlice(nativeAt(durations, index))),
                        bounds: {
                            x: float32(left + pad),
                            y: float32(y + nativeAt(heights, index) - AppScale(32n)),
                            width: float32(width - pad * 2n),
                            height: float32(AppScale(28n))
                        },
                        size: AppSmallFontSize()
                    }}
                />;
                y = y + (nativeAt(heights, index) + AppScale(12n));
            }
        } else {
            <Text
                session={app.ui.session}
                props={{
                    text: guide,
                    bounds: {
                        x: float32(left),
                        y: float32(y + AppScale(12n)),
                        width: float32(width),
                        height: float32(guide_h)
                    },
                    size: AppFontSize(),
                    wrap: Wrap.TextWrapAuto
                }}
            />;
        }
        End(app.ui.session);
    }
    let gap = AppScale(12n);
    let button_w = (width - gap) / 2n;
    if (
        Button({
            session: app.ui.session,
            props: {
                key: NativeLayout.KeyHash("astral/guide"),
                bounds: {
                    x: float32(left),
                    y: float32(bottom),
                    width: float32(button_w),
                    height: float32(AppScale(52n))
                },
                label: LocaleText(showing_guide ? "back_button" : "practice_manual_button")
            }
        })
    ) {
        app.tutorial_step = showing_guide ? 0n : 1n;
        app.manual_scroll = 0n;
        State_astral_projection.astral_reveal_selection = showing_guide;
    }
    if (
        Button({
            session: app.ui.session,
            props: {
                key: NativeLayout.KeyHash("astral/start-selected"),
                bounds: {
                    x: float32(left + button_w + gap),
                    y: float32(bottom),
                    width: float32(button_w),
                    height: float32(AppScale(52n))
                },
                label: LocaleText("practice_start_button"),
                fit_content: true
            }
        })
    ) {
        AstralStartSelected(app, false);
    }
    End(app.ui.session);
}
