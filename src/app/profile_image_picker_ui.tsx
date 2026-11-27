// Authored UI composition; native application state remains in profile_image_picker.zi.
import * as NativeButton from "kryon/button";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Session } from "kryon/session";
import { End } from "kryon/tree";
import { Button } from "kryon/tsx/button";
import { Image } from "kryon/tsx/image";
import { LocaleText } from "locale";
import { AppScale, MetricsScale } from "metrics";
import {
    ProfileImagePickerProps,
    ProfileImagePickerResult,
    ProfilePictureImage
} from "profile_image_picker";
import { ProfilePictureAt, ProfilePictureCount } from "profile_picture_policy";

export function ProfileImagePickerView(
    session: Session,
    props: ProfileImagePickerProps
): ProfileImagePickerResult {
    let result: ProfileImagePickerResult = {};
    result.selected_index = -1n;
    result.selected_icon_type = props.selected_icon_type;
    result.scroll_offset = props.scroll_offset;
    let width = props.max_width > 0n ? AppScale(props.max_width) : AppScale(440n);
    if (width > props.view_width - AppScale(24n)) {
        width = props.view_width - AppScale(24n);
    }
    if (width <= 0n || props.view_height <= 0n) {
        return result;
    }
    let gap = AppScale(8n);
    let content_width = width - AppScale(36n);
    let columns = (content_width + gap) / (AppScale(64n) + gap);
    if (columns < 1n) {
        columns = 1n;
    }
    let cell = (content_width - (columns - 1n) * gap) / columns;
    if (cell > AppScale(64n)) {
        cell = AppScale(64n);
    }
    let rows = (ProfilePictureCount + columns - 1n) / columns;
    let content_height = rows * cell + (rows - 1n) * gap;
    let height = AppScale(74n) + content_height + AppScale(18n);
    if (height > props.view_height - AppScale(24n)) {
        height = props.view_height - AppScale(24n);
    }
    let frame_props: NativeModal.Props = {};
    frame_props.key = u64(7800n);
    frame_props.title = props.title;
    frame_props.width = width;
    frame_props.height = height;
    frame_props.scale = MetricsScale();
    frame_props.has_right_action = true;
    frame_props.right_label = LocaleText("close_button");
    frame_props.right_image.asset_path = "icons/ui.webp";
    frame_props.right_image.alt_text = frame_props.right_label;
    frame_props.right_image.source = { x: 448.0, y: 384.0, width: 64.0, height: 64.0 };
    let frame = NativeModal.Draw(session, frame_props);
    if (frame.dismissed || frame.right_clicked) {
        result.closed = true;
        return result;
    }
    let layout = frame.layout;
    let content = layout.content;
    if (!frame.opened) {
        return result;
    }
    if (content.width <= 0.0 || content.height <= 0.0) {
        End(session);
        return result;
    }
    content_width = s32(content.width);
    columns = (content_width + gap) / (AppScale(64n) + gap);
    if (columns < 1n) {
        columns = 1n;
    }
    cell = (content_width - (columns - 1n) * gap) / columns;
    if (cell > AppScale(64n)) {
        cell = AppScale(64n);
    }
    rows = (ProfilePictureCount + columns - 1n) / columns;
    content_height = rows * cell + (rows - 1n) * gap;
    let scroll_key: u64 = u64(7801n);
    let scroll_props: NativeScroll.Props = {};
    scroll_props.key = scroll_key;
    scroll_props.bounds = content;
    scroll_props.content_height = content_height;
    scroll_props.scroll_offset = result.scroll_offset;
    let scrolled = NativeScroll.Draw(session, scroll_props);
    result.scroll_offset = scrolled.scroll_offset;
    if (scrolled.opened) {
        let grid_width = columns * cell + (columns - 1n) * gap;
        let index: s32 = s32(0n);
        while (index < ProfilePictureCount) {
            let row = index / columns;
            let column = index % columns;
            let x =
                s32(scrolled.content.x) +
                (s32(scrolled.content.width) - grid_width) / 2n +
                column * (cell + gap);
            let y = s32(scrolled.content.y) + row * (cell + gap);
            let icon_type = ProfilePictureAt(index);
            let button: NativeButton.Props = {};
            button.id = s32(7800n) + index;
            button.bounds = {
                x: float32(x),
                y: float32(y),
                width: float32(cell),
                height: float32(cell)
            };
            button.label = props.title;
            button.selected = props.selected_icon_type === icon_type;
            button.tone = ButtonTone.ButtonToneNeutral;
            button.emphasis = ButtonEmphasis.ButtonEmphasisSoft;
            button.icon_only = true;
            if (Button({ session: session, props: button })) {
                result.changed = true;
                result.closed = true;
                result.selected_index = index;
                result.selected_icon_type = icon_type;
            }
            let inset = AppScale(6n);
            let picture = ProfilePictureImage(icon_type, props.title);
            picture.key = u64(8800n + index);
            picture.bounds = {
                x: float32(x + inset),
                y: float32(y + inset),
                width: float32(cell - inset * 2n),
                height: float32(cell - inset * 2n)
            };
            <Image session={session} props={picture} />;
            index = index + 1n;
        }
        End(session);
    }
    End(session);
    return result;
}
