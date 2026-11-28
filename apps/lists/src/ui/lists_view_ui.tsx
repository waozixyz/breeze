import { ResolvedModal } from "kryon/tsx/modal";
// Authored application UI. Native state and effects live in lists_view.zi.
import * as NativeBackIcon from "mingcute/mingcute_regular_arrow_left";
import * as NativeContextMenu from "kryon/context_menu";
import * as NativeLayout from "kryon/layout";
import * as NativeModal from "kryon/modal";
import * as NativeScroll from "kryon/scroll";
import * as NativeSettingsIcon from "mingcute/mingcute_regular_settings_3";
import * as NativeText from "kryon/text";
import * as State from "lists_view";
import {
    AddAccessControl,
    AvatarFill,
    BeginCustomTask,
    BeginInput,
    Bounds,
    ClearAccessControls,
    CloseCustomTask,
    CloseSettings,
    CompleteSwipe,
    Copied,
    DeleteSwipe,
    EditSwipe,
    FriendIcon,
    InvitationAvailable,
    InviteFieldHeight,
    LISTS_ROW_MENU_CHECK,
    LISTS_ROW_MENU_EDIT,
    ListChipsResult,
    ListInvitationSender,
    ListPersonLabel,
    ListsEditText,
    ListsLocaleHost,
    MEMBER_ROW,
    Mutation,
    NewAlias,
    NewChipRow,
    NewChipWidth,
    NewChipX,
    NewFinishedOrder,
    NewId,
    NewNames,
    NewOpenOrder,
    NewInviteRoleOptions,
    NewPriorityOptions,
    NewAccessOptions,
    NewInviteSuggestions,
    NewPreviousBytes,
    NewTarget,
    NewTargets,
    OpenSettings,
    ReadListsRowHost,
    ReadListsSharingRowHost,
    RememberDeleted,
    Remote,
    ResetInvite,
    SaveCustomTask,
    Scale,
    SharedListSummary,
    SharingAccessControlAt,
    SharingAccessControlCount,
    SharingMemberShown,
    TRASH_ICON
} from "lists_view";
import { Box } from "kryon/tsx/box";
import { Button } from "kryon/tsx/button";
import { ButtonEmphasis, ButtonTone, ContentAlignment, IconPlacement } from "kryon/control_props";
import { ContainsFoldASCII } from "std/text";
import { ContextMenu } from "kryon/tsx/context_menu";
import { ControlledTextField } from "kryon/tsx/text_field";
import { CopyCString } from "std/c_string";
import { Dropdown } from "kryon/tsx/dropdown";
import { End } from "kryon/tree";
import { Scroll } from "kryon/tsx/scroll";
import { EntityIconImage } from "entity/picture_image";
import { EntityPublicIconChosen } from "entity/model";
import { FlagIntersection } from "native_flags";
import { IconType } from "kryon/icon";
import { Image } from "kryon/tsx/image";
import {
    LISTS_ACCEPT,
    LISTS_COMMIT,
    LISTS_DECLINE,
    LISTS_DELETE_ITEM,
    LISTS_DELETE_LIST,
    LISTS_INVITE,
    LISTS_REMOVE_ACCESS,
    LISTS_RESTORE_ITEM,
    LISTS_RETRY,
    LISTS_SELECT,
    LISTS_SET_ACCESS,
    LISTS_SET_DONE
} from "lists_types";
import { LISTS_TEXT_LIMIT, ListsUiPerson, ListsUiRow } from "lists_ui_types";
import { ListsTitlePriorityFits, ListsTitleWithoutPriority } from "task_title";
import { Rectangle } from "kryon/geometry";
import { SamplePointer } from "kryon/pointer_input";
import { Swipe } from "kryon/swipe";
import { SwipeDirection } from "kryon/swipe_props";
import { SwipeRow } from "kryon/tsx/swipe_row";
import { Text } from "kryon/tsx/text";
import { TextAlign } from "kryon/text_align";
import { TextArea } from "kryon/tsx/text_area";
import { TextUntilNul } from "std/text_buffer";
import { TextWidth } from "kryon/text_measure";

// A chosen picture or a circle with the initial from the person’s name.
function Avatar(key: u64, name: string, place: s32, x: s32, y: s32, size: s32, icon: s32): void {
    if (EntityPublicIconChosen(icon)) {
        let picture = EntityIconImage(icon, Bounds(x, y, size, size), name);
        picture.key = key;
        <Image session={State.frame.session} props={picture} />;
        return;
    }
    <Box
        session={State.frame.session}
        props={{
            key: key,
            bounds: Bounds(x, y, size, size),
            fill: AvatarFill(place),
            radius: float32(size) / 2.0
        }}
    />;
    let letter_end: s64 = 1n;
    while (
        letter_end < name.count &&
        FlagIntersection(nativeAt(name, letter_end), u8(192n)) === u8(128n)
    ) {
        letter_end += 1n;
    }
    let letter = name.count > 0n ? nativeSlice(name, 0n, letter_end) : "?";
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y, size, size),
            text: letter,
            align: TextAlign.TextAlignCenter,
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
}

function Field(bounds: Rectangle, placeholder: string, read_only: boolean = false): boolean {
    let input = State.frame.input;
    if (State.field_focus_request) {
        input.focus = true;
        State.field_focus_request = false;
    }
    let edited = ControlledTextField({
        session: State.frame.session,
        props: {
            key: u64(6501n),
            bounds: bounds,
            value: State.frame.value,
            placeholder: placeholder,
            cursor: State.frame.cursor,
            anchor: State.frame.anchor,
            scroll_x: State.frame.scroll_x,
            focused: State.frame.focused,
            focus_id: 6501n,
            max_bytes: LISTS_TEXT_LIMIT,
            max_codepoints: LISTS_TEXT_LIMIT,
            input: input,
            disabled: State.frame.sharing_busy || State.frame.sharing_pending || read_only
        }
    });
    if (edited.edit.changed) {
        let start = edited.edit.start;
        let end = edited.edit.end;
        if (start >= 0n && end >= start && end <= State.frame.value.count) {
            let replacement = ListsEditText(State.frame.value, start, end, edited.edit.replacement);
            if (replacement.count <= LISTS_TEXT_LIMIT) {
                State.frame.value = replacement;
            }
        }
    }
    State.frame.cursor = edited.cursor;
    State.frame.anchor = edited.anchor;
    State.frame.scroll_x = edited.scroll_x;
    State.frame.focused = edited.focused;
    if (edited.focused) {
        State.frame.comment_focused = false;
        State.frame.comment_input.blur = true;
    }
    State.frame.clipboard_write = edited.clipboard_write;
    State.frame.clipboard_text = edited.clipboard_text;
    State.field_escaped = edited.escaped;
    return edited.committed;
}

function DescriptionField(
    bounds: Rectangle,
    placeholder: string,
    read_only: boolean = false
): boolean {
    let input = State.frame.comment_input;
    let edited = TextArea({
        session: State.frame.session,
        props: {
            key: u64(6552n),
            bounds: bounds,
            value: State.frame.comment_value,
            placeholder: placeholder,
            cursor: State.frame.comment_cursor,
            anchor: State.frame.comment_anchor,
            scroll_y: State.frame.comment_scroll_y,
            focused: State.frame.comment_focused,
            focus_id: 6552n,
            max_bytes: LISTS_TEXT_LIMIT,
            max_codepoints: LISTS_TEXT_LIMIT,
            wrap: true,
            input: input,
            disabled: State.frame.sharing_busy || State.frame.sharing_pending || read_only
        }
    });
    if (edited.edit.changed) {
        let start = edited.edit.start;
        let end = edited.edit.end;
        if (start >= 0n && end >= start && end <= State.frame.comment_value.count) {
            let replacement = ListsEditText(
                State.frame.comment_value,
                start,
                end,
                edited.edit.replacement
            );
            if (replacement.count <= LISTS_TEXT_LIMIT) {
                State.frame.comment_value = replacement;
            }
        }
    }
    State.frame.comment_cursor = edited.cursor;
    State.frame.comment_anchor = edited.anchor;
    State.frame.comment_scroll_y = edited.scroll_y;
    State.frame.comment_focused = edited.focused;
    if (edited.focused) {
        State.frame.focused = false;
        State.frame.input.blur = true;
    }
    if (edited.clipboard_write) {
        State.frame.clipboard_write = true;
        State.frame.clipboard_text = edited.clipboard_text;
    }
    return edited.escaped;
}

// The role menu opens after the settings scroll ends, so its options can extend outside the viewport.
function InviteField(x: s32, y: s32, width: s32, disabled: boolean): boolean {
    let button_width = Scale(96n);
    let role_width = Scale(140n);
    let narrow = width < Scale(480n);
    let field_width = narrow ? width : width - button_width - role_width - Scale(16n);
    let row_y = narrow ? y + Scale(52n) : y;
    State.invite_role_bounds = Bounds(
        narrow ? x : x + field_width + Scale(8n),
        row_y,
        role_width,
        Scale(44n)
    );
    let previous_bytes = NewPreviousBytes();
    CopyCString(State.invite_text, nativeSlice(previous_bytes));
    let previous = TextUntilNul(nativeSlice(previous_bytes));
    let edited = ControlledTextField({
        session: State.frame.session,
        props: {
            key: u64(6540n),
            bounds: Bounds(x, y, field_width, Scale(44n)),
            value: previous,
            placeholder: ListsLocaleHost("elist_invite_by_name"),
            cursor: State.invite_cursor,
            anchor: State.invite_anchor,
            scroll_x: State.invite_scroll,
            focused: State.invite_focused,
            focus_id: 6540n,
            scale: State.frame.scale,
            max_bytes: 127n,
            max_codepoints: 127n,
            input: State.frame.input,
            disabled: disabled
        }
    });
    if (edited.edit.changed) {
        let value = previous;
        if (
            edited.edit.start >= 0n &&
            edited.edit.end >= edited.edit.start &&
            edited.edit.end <= value.count
        ) {
            State.invite_text = ListsEditText(
                value,
                edited.edit.start,
                edited.edit.end,
                edited.edit.replacement
            );
            nativeSet(State.invite_target, 0n, u8(0n));
            State.invite_suggestions = true;
        }
    }
    State.invite_cursor = edited.cursor;
    State.invite_anchor = edited.anchor;
    State.invite_scroll = edited.scroll_x;
    State.invite_focused = edited.focused;
    if (State.invite_focused) {
        State.frame.focused = true;
    }
    if (edited.clipboard_write) {
        State.frame.clipboard_write = true;
        State.frame.clipboard_text = Copied(edited.clipboard_text);
    }
    if (edited.escaped) {
        State.invite_suggestions = false;
    }
    if (
        Button({
            session: State.frame.session,
            props: {
                key: u64(6541n),
                bounds: Bounds(x + width - button_width, row_y, button_width, Scale(44n)),
                label: ListsLocaleHost("elist_invite"),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                disabled: disabled || nativeAt(State.invite_target, 0n) === u8(0n)
            }
        })
    ) {
        let access: [string, string, string] = ["owner", "editor", "viewer"];
        Remote(
            LISTS_INVITE,
            TextUntilNul(nativeSlice(State.invite_target)),
            "",
            "",
            nativeAt(access, State.invite_role)
        );
        ResetInvite();
        return true;
    }
    return false;
}

// The access a new invitation gives, as a menu like each member’s.
function InviteRole(disabled: boolean): void {
    if (
        State.invite_role_bounds.width <= 0.0 ||
        State.invite_role_bounds.y < State.sharing_viewport.y ||
        State.invite_role_bounds.y + State.invite_role_bounds.height >
            State.sharing_viewport.y + State.sharing_viewport.height
    ) {
        return;
    }
    let labels: [string, string, string] = [
        ListsLocaleHost("elist_owner"),
        ListsLocaleHost("elist_can_edit"),
        ListsLocaleHost("elist_read_only")
    ];
    let options = NewInviteRoleOptions();
    for (let index: s32 = s32(0n); index <= 2n; index += 1n) {
        nativeSet(options, index, { key: u64(index + 1n), label: nativeAt(labels, index) });
    }
    let chosen = Dropdown({
        session: State.frame.session,
        props: {
            key: u64(6543n),
            bounds: State.invite_role_bounds,
            selected_index: State.invite_role,
            disabled: disabled,
            scale: State.frame.scale
        },
        options: nativeSlice(options, 0n, 3n)
    });
    if (chosen.open) {
        State.settings_menu_open = true;
    }
    if (chosen.changed) {
        State.invite_role = chosen.selected_index;
    }
}

// Suggestions only select the recipient. Sending requires the Invite button.
function InviteSuggestions(x: s32, y: s32, list_id: string, owner: string): void {
    if (!State.invite_suggestions || State.invite_text.count === 0n) {
        return;
    }
    let options = NewInviteSuggestions();
    let names = NewNames();
    let targets = NewTargets();
    let count: s32 = s32(0n);
    for (let index: s32 = s32(0n); index < State.frame.friend_count; index += 1n) {
        let friend = ReadListsSharingRowHost(index, false);
        let id = NewId();
        let alias = NewAlias();
        CopyCString(friend.id, nativeSlice(id));
        CopyCString(friend.alias, nativeSlice(alias));
        if (
            !ContainsFoldASCII(TextUntilNul(nativeSlice(alias)), State.invite_text) ||
            !InvitationAvailable(TextUntilNul(nativeSlice(id)), list_id, owner)
        ) {
            continue;
        }
        nativeSet(names, count, alias);
        nativeSet(targets, count, id);
        nativeSet(options, count, {
            id: count + 1n,
            label: TextUntilNul(nativeSlice(nativeAt(names, count)))
        });
        count += 1n;
        if (count === 8n) {
            break;
        }
    }
    if (count === 0n) {
        nativeSet(options, 0n, {
            id: 1n,
            label: ListsLocaleHost("elist_no_matches"),
            disabled: true
        });
        count = 1n;
    }
    let result = ContextMenu({
        session: State.frame.session,
        props: {
            key: u64(6542n),
            open: true,
            x: float32(x),
            y: float32(y),
            escape: State.frame.input.escape,
            scale: State.frame.scale
        },
        items: nativeSlice(options, 0n, count)
    });
    if (
        result.activated_id > 0n &&
        result.activated_id <= count &&
        !nativeAt(options, result.activated_id - 1n).disabled
    ) {
        let selected = result.activated_id - 1n;
        State.invite_text = Copied(TextUntilNul(nativeSlice(nativeAt(names, selected))));
        State.invite_target = nativeAt(targets, selected);
        State.invite_cursor = s32(State.invite_text.count);
        State.invite_anchor = State.invite_cursor;
        State.invite_suggestions = false;
    } else if (result.closed) {
        State.invite_suggestions = false;
    }
}

function MemberRow(
    row: ListsUiPerson,
    place: s32,
    x: s32,
    y: s32,
    width: s32,
    manages: boolean,
    original_owner: boolean,
    disabled: boolean
): void {
    let target = NewTarget();
    CopyCString(row.target, nativeSlice(target));
    let name = row.target_alias;
    if (name.count === 0n) {
        name = nativeSlice(row.target, 0n, row.target.count > 8n ? 8n : row.target.count);
    }
    if (row.target === State.frame.public_id) {
        name = ListsLocaleHost("elist_you");
    }
    let shown = name;
    if (row.status === "pending") {
        shown = ListPersonLabel(Copied(name), ListsLocaleHost("elist_invited"));
    }
    let avatar = Scale(36n);
    let icon = row.target === State.frame.public_id ? State.frame.profile_icon : row.profile_icon;
    Avatar(
        u64(7900n + place),
        shown,
        place,
        x,
        y + (Scale(MEMBER_ROW) - avatar) / 2n,
        avatar,
        icon
    );
    let role_width = Scale(140n);
    let name_x = x + avatar + Scale(12n);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(
                name_x,
                y,
                x + width - role_width - Scale(8n) - name_x,
                Scale(MEMBER_ROW)
            ),
            text: shown,
            vertical_align: TextAlign.TextAlignCenter,
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let role: s32 =
        original_owner || row.access === "owner" ? 0n : row.access === "viewer" ? 2n : 1n;
    let labels: [string, string, string] = [
        ListsLocaleHost("elist_owner"),
        ListsLocaleHost("elist_can_edit"),
        ListsLocaleHost("elist_read_only")
    ];
    let bounds = Bounds(
        x + width - role_width,
        y + (Scale(MEMBER_ROW) - Scale(40n)) / 2n,
        role_width,
        Scale(40n)
    );
    if (
        manages &&
        !original_owner &&
        bounds.y >= State.sharing_viewport.y &&
        bounds.y + bounds.height <= State.sharing_viewport.y + State.sharing_viewport.height
    ) {
        // Submit the dropdowns after the scroll to avoid clipping their menus.
        AddAccessControl(target, bounds, role, disabled);
    } else {
        <Text
            session={State.frame.session}
            props={{
                bounds: bounds,
                text: nativeAt(labels, role),
                align: TextAlign.TextAlignEnd,
                vertical_align: TextAlign.TextAlignCenter,
                disabled: true
            }}
        />;
    }
}

function SharingAccessControls(): boolean {
    let labels: [string, string, string] = [
        ListsLocaleHost("elist_owner"),
        ListsLocaleHost("elist_can_edit"),
        ListsLocaleHost("elist_read_only")
    ];
    let options = NewAccessOptions();
    for (let index: s32 = s32(0n); index <= 2n; index += 1n) {
        nativeSet(options, index, { key: u64(index + 1n), label: nativeAt(labels, index) });
    }
    nativeSet(options, 3n, {
        key: u64(4n),
        label: ListsLocaleHost("elist_remove_access"),
        separator_before: true
    });
    for (let index: s32 = s32(0n); index < SharingAccessControlCount(); index += 1n) {
        let control = SharingAccessControlAt(index);
        let target = TextUntilNul(nativeSlice(control.target));
        let changed = Dropdown({
            session: State.frame.session,
            props: {
                key: NativeLayout.KeyHash(target),
                bounds: control.bounds,
                selected_index: control.role,
                disabled: control.disabled,
                scale: State.frame.scale
            },
            options: nativeSlice(options, 0n, 4n)
        });
        if (changed.open) {
            State.settings_menu_open = true;
        }
        if (changed.changed) {
            if (changed.selected_index === 3n) {
                Remote(LISTS_REMOVE_ACCESS, target);
            } else {
                let access: [string, string, string] = ["owner", "editor", "viewer"];
                Remote(LISTS_SET_ACCESS, target, "", "", nativeAt(access, changed.selected_index));
            }
            return true;
        }
    }
    return false;
}

// Invitations to other people’s lists update while the dialog is open.
export function InvitationsDialog(): void {
    let width = State.frame.width - Scale(32n);
    if (width > Scale(520n)) {
        width = Scale(520n);
    }
    let detail = ListsLocaleHost(
        State.frame.connected ? "elist_invitations_detail" : "elist_connect"
    );
    let count: s32 = s32(0n);
    for (let index: s32 = s32(0n); index < State.frame.invitation_count; index += 1n) {
        let row = ReadListsSharingRowHost(index, true);
        if (row.target === State.frame.public_id && row.status === "pending") {
            count += 1n;
        }
    }
    let row_height = Scale(160n);
    let shown = count > 4n ? 4n : count;
    let height = Scale(120n) + shown * row_height;
    if (height > State.frame.height - State.frame.bottom - Scale(32n)) {
        height = State.frame.height - State.frame.bottom - Scale(32n);
    }
    // The modal frame supplies dismiss results and the resolved content bounds.
    let dialog = ResolvedModal({
        session: State.frame.session,
        props: {
            key: u64(6520n),
            title: ListsLocaleHost("elist_invitations"),
            width: width,
            height: height,
            scale: State.frame.scale,
            has_right_action: true,
            right_label: ListsLocaleHost("close_button")
        },
        children: (dialog: NativeModal.ModalFrameResult): void => {
            let x = s32(dialog.layout.content.x);
            let y = s32(dialog.layout.content.y);
            let content_width = s32(dialog.layout.content.width);
            let bottom = s32(dialog.layout.content.y + dialog.layout.content.height);
            let disabled = State.frame.sharing_busy || State.frame.sharing_pending;
            <Text
                session={State.frame.session}
                props={{
                    bounds: Bounds(x, y, content_width, Scale(32n)),
                    text: detail,
                    wrap: NativeText.Wrap.TextWrapAuto
                }}
            />;
            y += Scale(40n);
            if (!State.frame.connected) {
                return;
            }
            if (count === 0n) {
                <Text
                    session={State.frame.session}
                    props={{
                        bounds: Bounds(x, y, content_width, Scale(44n)),
                        text: ListsLocaleHost("elist_no_invitations"),
                        wrap: NativeText.Wrap.TextWrapAuto
                    }}
                />;
                return;
            }
            let invitations = Scroll({
                session: State.frame.session,
                props: {
                    key: 6512n,
                    bounds: Bounds(x, y, content_width, bottom - y),
                    content_height: count * row_height,
                    scroll_offset: State.sharing_scroll
                },
                children: (scroll: NativeScroll.ScrollResult): void => {
                    InvitationRows(scroll, x, content_width, row_height, disabled);
                }
            });
            State.sharing_scroll = invitations.scroll_offset;
        }
    });
    if (dialog.dismissed || dialog.right_clicked) {
        State.frame.panel = 0n;
        State.frame.focused = false;
        State.sharing_scroll = 0n;
        return;
    }
}

function InvitationRows(
    scroll: NativeScroll.ScrollResult,
    x: s32,
    content_width: s32,
    row_height: s32,
    disabled: boolean
): void {
    State.sharing_scroll = scroll.scroll_offset;
    let row_y = s32(scroll.content.y);
    let changed: boolean = false;
    for (let index: s32 = s32(0n); index < State.frame.invitation_count; index += 1n) {
        let row = ReadListsSharingRowHost(index, true);
        if (row.target !== State.frame.public_id || row.status !== "pending") {
            continue;
        }
        if (
            row_y + row_height > s32(scroll.viewport.y) &&
            row_y < s32(scroll.viewport.y + scroll.viewport.height)
        ) {
            changed = InvitationRow(row, index, x, row_y, content_width - Scale(14n), disabled);
            if (changed) {
                break;
            }
        }
        row_y += row_height;
    }
}

export function CustomTaskDialog(): void {
    let width = State.frame.width - Scale(32n);
    if (width > Scale(440n)) {
        width = Scale(440n);
    }
    let height = Scale(404n);
    let available = State.frame.height - State.frame.bottom - Scale(32n);
    if (available < height) {
        height = available;
    }
    // The modal frame supplies dismiss results and the resolved content bounds.
    let dialog = ResolvedModal({
        session: State.frame.session,
        props: {
            key: u64(6550n),
            title: ListsLocaleHost("elist_custom_task"),
            width: width,
            height: height,
            scale: State.frame.scale
        },
        children: (dialog: NativeModal.ModalFrameResult): void => {
            let current: ListsUiRow = {};
            let blocked = State.frame.sharing_busy || State.frame.sharing_pending;
            if (
                State.state.selected_list >= 0n &&
                State.state.selected_list < State.state.list_count
            ) {
                current = ReadListsRowHost(State.state.selected_list, false);
                blocked = blocked || current.read_only || current.incomplete;
            } else {
                blocked = true;
            }
            let x = s32(dialog.layout.content.x);
            let y = s32(dialog.layout.content.y);
            let content_width = s32(dialog.layout.content.width);
            let fields = Scroll({
                session: State.frame.session,
                props: {
                    key: 6555n,
                    bounds: Bounds(x, y, content_width, s32(dialog.layout.content.height)),
                    content_height: Scale(350n),
                    scroll_offset: State.custom_task_scroll,
                    scale: State.frame.scale
                },
                children: (scroll: NativeScroll.ScrollResult): void => {
                    CustomTaskFields(scroll, content_width, blocked);
                }
            });
            if (!fields.opened) {
                State.custom_task_scroll = fields.scroll_offset;
            }
        }
    });
    if (dialog.dismissed) {
        CloseCustomTask();
        return;
    }
}

function CustomTaskFields(
    scroll: NativeScroll.ScrollResult,
    content_width: s32,
    blocked: boolean
): void {
    State.custom_task_scroll = scroll.scroll_offset;
    let x = s32(scroll.content.x);
    let y = s32(scroll.content.y);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y, content_width, Scale(20n)),
            text: ListsLocaleHost("elist_task_label")
        }}
    />;
    let task_committed = Field(
        Bounds(x, y + Scale(24n), content_width, Scale(44n)),
        ListsLocaleHost("elist_item_name_placeholder"),
        blocked
    );
    let task_escaped = State.field_escaped;
    y += Scale(76n);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y, content_width, Scale(20n)),
            text: ListsLocaleHost("habit_description_label")
        }}
    />;
    let description_escaped = DescriptionField(
        Bounds(x, y + Scale(24n), content_width, Scale(112n)),
        ListsLocaleHost("habit_description_label"),
        blocked
    );
    y += Scale(144n);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y, content_width - Scale(132n), Scale(44n)),
            text: ListsLocaleHost("elist_priority_label"),
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    let options = NewPriorityOptions();
    nativeAt(options, 0n).label = ListsLocaleHost("profile_none_label");
    let alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for (let index: s32 = s32(1n); index <= 26n; index += 1n) {
        nativeAt(options, index).label = nativeSlice(alphabet, index - 1n, index);
    }
    let chosen = Dropdown({
        session: State.frame.session,
        props: {
            key: u64(6551n),
            bounds: Bounds(x + content_width - Scale(124n), y, Scale(124n), Scale(44n)),
            selected_index: State.frame.task_priority,
            disabled: blocked,
            scale: State.frame.scale
        },
        options: nativeSlice(options, 0n, 27n)
    });
    if (chosen.changed) {
        State.frame.task_priority = chosen.selected_index;
    }
    y += Scale(54n);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y, content_width, Scale(24n)),
            text: "+project @context due:YYYY-MM-DD",
            disabled: true
        }}
    />;
    y += Scale(32n);
    let button_width = (content_width - Scale(8n)) / 2n;
    let save = Button({
        session: State.frame.session,
        props: {
            key: u64(6553n),
            bounds: Bounds(x, y, button_width, Scale(44n)),
            label: ListsLocaleHost("save_button"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
            disabled:
                ListsTitleWithoutPriority(State.frame.value).count === 0n ||
                blocked ||
                !ListsTitlePriorityFits(
                    State.frame.value,
                    State.frame.task_priority,
                    LISTS_TEXT_LIMIT
                )
        }
    });
    let cancel = Button({
        session: State.frame.session,
        props: {
            key: u64(6554n),
            bounds: Bounds(x + button_width + Scale(8n), y, button_width, Scale(44n)),
            label: ListsLocaleHost("cancel_button")
        }
    });
    if (task_escaped || description_escaped || cancel) {
        CloseCustomTask();
    } else if (save || task_committed) {
        SaveCustomTask();
    }
}

// Returns whether Accept or Decline was chosen.
function InvitationRow(
    row: ListsUiPerson,
    index: s32,
    x: s32,
    y: s32,
    width: s32,
    disabled: boolean
): boolean {
    let alias = row.alias;
    if (alias.count === 0n) {
        alias = row.owner;
    }
    <Box
        session={State.frame.session}
        props={{
            key: u64(7800n + index),
            bounds: Bounds(x, y + Scale(4n), width, Scale(144n)),
            border: { r: 128n, g: 128n, b: 128n, a: 64n },
            radius: float32(Scale(12n))
        }}
    />;
    x += Scale(16n);
    width -= Scale(32n);
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y + Scale(14n), width, Scale(44n)),
            text: row.title,
            size: Scale(18n),
            wrap: NativeText.Wrap.TextWrapAuto
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x, y + Scale(60n), width, Scale(24n)),
            text: ListInvitationSender(alias),
            size: Scale(13n),
            wrap: NativeText.Wrap.TextWrapEllipsis
        }}
    />;
    let button_width = (width - Scale(12n)) / 2n;
    let accept = Button({
        session: State.frame.session,
        props: {
            key: u64(7600n + index * 2n),
            bounds: Bounds(x, y + Scale(92n), button_width, Scale(44n)),
            label: ListsLocaleHost("profile_friend_accept_button"),
            tone: ButtonTone.ButtonToneAccent,
            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
            disabled: disabled || State.state.list_count >= 32n
        }
    });
    let decline = Button({
        session: State.frame.session,
        props: {
            key: u64(7601n + index * 2n),
            bounds: Bounds(x + button_width + Scale(12n), y + Scale(92n), button_width, Scale(44n)),
            label: ListsLocaleHost("profile_friend_decline_button"),
            disabled: disabled,
            tone: ButtonTone.ButtonToneNeutral,
            emphasis: ButtonEmphasis.ButtonEmphasisGhost
        }
    });
    if (accept || decline) {
        Remote(accept ? LISTS_ACCEPT : LISTS_DECLINE, "", row.id, row.list_id);
        return true;
    }
    return false;
}

// The list chips wrap, with a new-list chip at the end. The viewport shows up to three rows.
function ListChips(x: s32, y: s32, width: s32, blocked: boolean): ListChipsResult {
    let result: ListChipsResult = {};
    const result_ref = nativeRef(result);
    let chip_height = Scale(40n);
    let gap = Scale(8n);
    let padding = Scale(18n);
    let chip_x = NewChipX();
    let chip_row = NewChipRow();
    let chip_width = NewChipWidth();
    let row: s32 = s32(0n);
    let row_x: s32 = s32(0n);
    for (let index: s32 = s32(0n); index <= State.state.list_count; index += 1n) {
        nativeSet(chip_width, index, chip_height);
        if (index < State.state.list_count) {
            let label = ReadListsRowHost(index, false).title;
            nativeSet(
                chip_width,
                index,
                TextWidth(State.frame.session, { text: label }) + padding * 2n
            );
            if (index === State.state.selected_list) {
                nativeSet(chip_width, index, nativeAt(chip_width, index) + Scale(26n));
            }
        }
        if (nativeAt(chip_width, index) > width) {
            nativeSet(chip_width, index, width);
        }
        if (row_x > 0n && row_x + nativeAt(chip_width, index) > width) {
            row += 1n;
            row_x = 0n;
        }
        nativeSet(chip_x, index, row_x);
        nativeSet(chip_row, index, row);
        row_x += nativeAt(chip_width, index) + gap;
    }
    let rows = row + 1n;
    let shown_rows = rows > 3n ? 3n : rows;
    result.height = shown_rows * chip_height + (shown_rows - 1n) * gap;
    let scroll = Scroll({
        session: State.frame.session,
        props: {
            key: u64(6500n),
            bounds: Bounds(x, y, width, result.height),
            content_height: rows * chip_height + (rows - 1n) * gap,
            scroll_offset: State.frame.tab_scroll
        },
        children: (scroll: NativeScroll.ScrollResult): void => {
            State.frame.tab_scroll = scroll.scroll_offset;

            for (let index: s32 = s32(0n); index <= State.state.list_count; index += 1n) {
                let bounds = Bounds(
                    x + nativeAt(chip_x, index),
                    s32(scroll.content.y) + nativeAt(chip_row, index) * (chip_height + gap),
                    nativeAt(chip_width, index),
                    chip_height
                );
                if (index === State.state.list_count) {
                    if (
                        Button({
                            session: State.frame.session,
                            props: {
                                key: u64(6505n),
                                bounds: bounds,
                                label: ListsLocaleHost("elist_new_list"),
                                icon_type: s32(IconType.IconPlus),
                                icon_only: true,
                                pill: true,
                                emphasis: ButtonEmphasis.ButtonEmphasisOutline,
                                disabled: blocked || State.state.list_count >= 32n
                            }
                        })
                    ) {
                        BeginInput(-2n, "");
                        State.frame.panel = 0n;
                        nativeDeref(result_ref).acted = true;
                    }
                    continue;
                }
                let chosen = index === State.state.selected_list;
                let title = ReadListsRowHost(index, false).title;
                if (
                    Button({
                        session: State.frame.session,
                        props: {
                            key: u64(6800n + index),
                            bounds: bounds,
                            label: title,
                            pill: true,
                            selected: chosen,
                            icon_shape: chosen ? NativeSettingsIcon.Shape : "",
                            icon_placement: IconPlacement.IconPlacementTrailing,
                            tone: chosen
                                ? ButtonTone.ButtonToneAccent
                                : ButtonTone.ButtonToneNeutral,
                            emphasis: chosen
                                ? ButtonEmphasis.ButtonEmphasisFilled
                                : ButtonEmphasis.ButtonEmphasisOutline
                        }
                    })
                ) {
                    if (chosen) {
                        OpenSettings(Copied(title));
                    } else {
                        State.state.action = LISTS_SELECT;
                        State.state.index = index;
                        State.undo_until = 0.0;
                        State.delete_confirm = false;
                        State.frame.panel = 0n;
                    }
                    nativeDeref(result_ref).acted = true;
                }
            }
        }
    });
    if (!scroll.opened) {
        State.frame.tab_scroll = scroll.scroll_offset;
        return result;
    }
    return result;
}

// List settings replaces the page with its name, access and the owner’s delete controls.
export function ListSettingsPage(): void {
    let x = Scale(16n);
    let width = State.frame.width - x * 2n;
    if (width > Scale(640n)) {
        x = (State.frame.width - Scale(640n)) / 2n;
        width = Scale(640n);
    }
    let y = Scale(12n);
    let blocked = State.frame.sharing_busy || State.frame.sharing_pending;
    let row = ReadListsRowHost(State.state.selected_list, false);
    let list_id = Copied(row.id);
    let title = Copied(row.title);
    let owner_id = Copied(row.owner_id);
    let owner_alias = Copied(row.owner_alias);
    let shared = row.shared;
    let owns = !row.shared || row.owner;
    let read_only = row.read_only;
    let incomplete = row.incomplete;
    ClearAccessControls();
    State.invite_role_bounds = {};
    let menu_was_open = State.settings_menu_open;
    State.settings_menu_open = false;
    if (State.frame.input.escape && !menu_was_open && !State.invite_suggestions) {
        CloseSettings();
        return;
    }
    if (
        Button({
            session: State.frame.session,
            props: {
                key: u64(6550n),
                bounds: Bounds(x, y, Scale(44n), Scale(44n)),
                label: ListsLocaleHost("back_button"),
                icon_shape: NativeBackIcon.Shape,
                icon_only: true,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }
        })
    ) {
        CloseSettings();
        return;
    }
    <Text
        session={State.frame.session}
        props={{
            bounds: Bounds(x + Scale(56n), y, width - Scale(56n), Scale(44n)),
            text: ListsLocaleHost("elist_settings"),
            size: Scale(20n),
            vertical_align: TextAlign.TextAlignCenter
        }}
    />;
    y += Scale(60n);
    if (State.state.editing_item !== -3n) {
        BeginInput(-3n, title);
        State.frame.focused = false;
    }
    let members: s32 = s32(1n);
    for (let index: s32 = s32(0n); index < State.frame.invitation_count; index += 1n) {
        if (SharingMemberShown(ReadListsSharingRowHost(index, true), list_id)) {
            members += 1n;
        }
    }
    let inner = width - Scale(14n);
    let can_invite = State.frame.connected && !read_only;
    let content = Scale(28n + 44n + 28n + 32n + 20n);
    content += State.frame.connected ? members * Scale(MEMBER_ROW) : Scale(64n);
    if (can_invite) {
        content += InviteFieldHeight(inner) + Scale(24n);
    }
    if (owns) {
        content += State.delete_confirm ? Scale(170n) : Scale(52n);
    }
    let scroll_action = false;
    const scroll_action_ref = nativeRef(scroll_action);
    let suggestions_y = s32(0);
    const suggestions_y_ref = nativeRef(suggestions_y);
    let scroll = Scroll({
        session: State.frame.session,
        props: {
            key: u64(6560n),
            bounds: Bounds(x, y, width, State.frame.height - State.frame.bottom - y - Scale(12n)),
            content_height: content,
            scroll_offset: State.settings_scroll
        },
        children: (scroll: NativeScroll.ScrollResult): void => {
            State.settings_scroll = scroll.scroll_offset;
            State.sharing_viewport = scroll.viewport;

            let cy = s32(scroll.content.y);
            <Text
                session={State.frame.session}
                props={{
                    bounds: Bounds(x, cy, inner, Scale(24n)),
                    text: ListsLocaleHost("elist_list_name_placeholder"),
                    disabled: true
                }}
            />;
            cy += Scale(28n);
            if (State.invite_focused) {
                State.frame.focused = false;
            }
            let committed = Field(
                Bounds(x, cy, inner - Scale(96n), Scale(44n)),
                ListsLocaleHost("elist_list_name_placeholder"),
                read_only || blocked
            );
            let renamed =
                State.frame.value.count > 0n &&
                State.frame.value !== title &&
                !read_only &&
                !blocked;
            if (
                Button({
                    session: State.frame.session,
                    props: {
                        key: u64(6551n),
                        bounds: Bounds(x + inner - Scale(88n), cy, Scale(88n), Scale(44n)),
                        label: ListsLocaleHost("save_button"),
                        tone: ButtonTone.ButtonToneAccent,
                        emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                        disabled: !renamed
                    }
                }) ||
                (committed && renamed)
            ) {
                Mutation(LISTS_COMMIT, -1n);
                State.frame.focused = false;
                nativeDeref(scroll_action_ref) = true;
                return;
            }
            cy += Scale(72n);
            <Text
                session={State.frame.session}
                props={{
                    bounds: Bounds(x, cy, inner, Scale(24n)),
                    text: ListsLocaleHost("elist_people_with_access"),
                    disabled: true
                }}
            />;
            cy += Scale(32n);
            if (!State.frame.connected) {
                <Text
                    session={State.frame.session}
                    props={{
                        bounds: Bounds(x, cy, inner, Scale(64n)),
                        text: ListsLocaleHost("elist_connect"),
                        wrap: NativeText.Wrap.TextWrapAuto
                    }}
                />;
                cy += Scale(64n);
            } else {
                let owner_name = owner_alias.count > 0n ? owner_alias : owner_id;
                if (!shared || owner_id === State.frame.public_id) {
                    owner_name = ListsLocaleHost("elist_you");
                }
                MemberRow(
                    {
                        target: owner_id,
                        target_alias: owner_name,
                        access: "owner",
                        profile_icon: FriendIcon(owner_id)
                    },
                    0n,
                    x,
                    cy,
                    inner,
                    false,
                    true,
                    blocked
                );
                cy += Scale(MEMBER_ROW);
                let place: s32 = s32(1n);
                for (let index: s32 = s32(0n); index < State.frame.invitation_count; index += 1n) {
                    let person = ReadListsSharingRowHost(index, true);
                    if (!SharingMemberShown(person, list_id)) {
                        continue;
                    }
                    MemberRow(person, place, x, cy, inner, owns, false, blocked);
                    place += 1n;
                    cy += Scale(MEMBER_ROW);
                }
            }
            cy += Scale(20n);
            nativeDeref(suggestions_y_ref) = cy + Scale(48n);
            if (can_invite) {
                if (InviteField(x, cy, inner, blocked || incomplete)) {
                    nativeDeref(scroll_action_ref) = true;
                    return;
                }
                cy += InviteFieldHeight(inner) + Scale(24n);
            }
            if (owns && !State.delete_confirm) {
                if (
                    Button({
                        session: State.frame.session,
                        props: {
                            key: u64(6515n),
                            bounds: Bounds(x, cy, inner, Scale(44n)),
                            label: ListsLocaleHost("elist_delete_list"),
                            icon_shape: TRASH_ICON,
                            tone: ButtonTone.ButtonToneDanger,
                            emphasis: ButtonEmphasis.ButtonEmphasisSoft,
                            disabled: blocked
                        }
                    })
                ) {
                    State.delete_confirm = true;
                }
            } else if (owns) {
                <Box
                    session={State.frame.session}
                    props={{
                        key: u64(6518n),
                        bounds: Bounds(x, cy, inner, Scale(160n)),
                        border: { r: 198n, g: 52n, b: 52n, a: 160n },
                        radius: float32(Scale(12n))
                    }}
                />;
                <Text
                    session={State.frame.session}
                    props={{
                        bounds: Bounds(
                            x + Scale(16n),
                            cy + Scale(12n),
                            inner - Scale(32n),
                            Scale(30n)
                        ),
                        text: ListsLocaleHost("elist_delete_question"),
                        size: Scale(18n)
                    }}
                />;
                <Text
                    session={State.frame.session}
                    props={{
                        bounds: Bounds(
                            x + Scale(16n),
                            cy + Scale(44n),
                            inner - Scale(32n),
                            Scale(48n)
                        ),
                        text: ListsLocaleHost("elist_delete_detail"),
                        wrap: NativeText.Wrap.TextWrapAuto,
                        disabled: true
                    }}
                />;
                let button_width = (inner - Scale(44n)) / 2n;
                if (
                    Button({
                        session: State.frame.session,
                        props: {
                            key: u64(6514n),
                            bounds: Bounds(
                                x + Scale(16n),
                                cy + Scale(100n),
                                button_width,
                                Scale(44n)
                            ),
                            label: ListsLocaleHost("cancel_button")
                        }
                    })
                ) {
                    State.delete_confirm = false;
                }
                if (
                    Button({
                        session: State.frame.session,
                        props: {
                            key: u64(6516n),
                            bounds: Bounds(
                                x + Scale(28n) + button_width,
                                cy + Scale(100n),
                                button_width,
                                Scale(44n)
                            ),
                            label: ListsLocaleHost("elist_delete_list"),
                            tone: ButtonTone.ButtonToneDanger,
                            emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                            disabled: blocked
                        }
                    })
                ) {
                    CloseSettings();
                    Mutation(LISTS_DELETE_LIST, -1n);
                    nativeDeref(scroll_action_ref) = true;
                    return;
                }
            }
        }
    });
    if (!scroll.opened) {
        State.settings_scroll = scroll.scroll_offset;
        State.sharing_viewport = scroll.viewport;
        return;
    }
    if (scroll_action) {
        return;
    }
    if (SharingAccessControls()) {
        return;
    }
    if (can_invite) {
        InviteRole(blocked || incomplete);
        if (!blocked) {
            InviteSuggestions(x, suggestions_y, list_id, owner_id);
        }
    }
}

// List members appear under the chips. Tapping the names opens List settings.
function SharedLine(current: ListsUiRow, x: s32, y: s32, width: s32): boolean {
    let shared = SharedListSummary(current);
    if (shared.count === 0n) {
        return false;
    }
    let size = Scale(32n);
    let step = Scale(22n);
    let shown = shared.count;
    for (let place: s32 = s32(0n); place < shown; place += s32(1)) {
        Avatar(
            u64(7950n + place),
            nativeAt(shared.names, place),
            place,
            x + place * step,
            y + Scale(4n),
            size,
            nativeAt(shared.icons, place)
        );
    }
    let text_x = x + (shown - 1n) * step + size + Scale(10n);
    if (
        Button({
            session: State.frame.session,
            props: {
                key: u64(6508n),
                bounds: Bounds(text_x, y, x + width - text_x, Scale(40n)),
                label: shared.label,
                content_alignment: ContentAlignment.ContentAlignmentStart,
                emphasis: ButtonEmphasis.ButtonEmphasisGhost
            }
        })
    ) {
        OpenSettings(shared.title);
        return true;
    }
    return false;
}

// The selected list, from its chips and add-item field through its task rows.
export function ListsPage(): void {
    let x = Scale(16n);
    let width = State.frame.width - x * 2n;
    let y = Scale(12n);
    let blocked = State.frame.sharing_busy || State.frame.sharing_pending;
    let current: ListsUiRow = {};
    if (State.state.selected_list >= 0n && State.state.selected_list < State.state.list_count) {
        current = ReadListsRowHost(State.state.selected_list, false);
    }
    if (State.state.editing_item === -3n) {
        State.state.editing_item = -1n;
        State.state.reset_input = true;
    }
    let chips = ListChips(x, y, width, blocked);
    if (chips.acted) {
        return;
    }
    y += chips.height + Scale(12n);
    if (current.shared) {
        if (SharedLine(current, x, y, width)) {
            return;
        }
        y += Scale(48n);
    }
    if (
        (State.frame.sharing_status !== 0n && State.frame.sharing_status !== 2n) ||
        State.frame.sharing_pending
    ) {
        let key = "elist_saving";
        if (State.frame.sharing_pending && !State.frame.sharing_busy) {
            key = "elist_unconfirmed";
        } else if (State.frame.sharing_status === 3n) {
            key = "elist_share_failed";
        } else if (State.frame.sharing_status === 4n) {
            key = "elist_conflict";
        } else if (State.frame.sharing_status === 5n) {
            key = "elist_unavailable";
        }
        let notice_width =
            State.frame.sharing_pending && !State.frame.sharing_busy ? width - Scale(104n) : width;
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y, notice_width, Scale(64n)),
                text: ListsLocaleHost(key),
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        if (State.frame.sharing_pending && !State.frame.sharing_busy) {
            if (
                Button({
                    session: State.frame.session,
                    props: {
                        key: u64(6513n),
                        bounds: Bounds(x + width - Scale(96n), y, Scale(96n), Scale(44n)),
                        label: ListsLocaleHost("retry_button")
                    }
                })
            ) {
                State.state.action = LISTS_RETRY;
                State.state.remote = true;
                return;
            }
        }
        y += Scale(72n);
    }
    if (current.shared && current.incomplete) {
        blocked = true;
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y, width, Scale(64n)),
                text: ListsLocaleHost("elist_capacity"),
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        y += Scale(72n);
    }
    if (current.read_only && State.state.editing_item !== -2n) {
        blocked = true;
    }
    let editing_list = State.state.editing_item === -2n;
    if (!editing_list) {
        if (State.frame.pending_count_text !== "0" && State.frame.pending_count_text !== "") {
            if (
                Button({
                    session: State.frame.session,
                    props: {
                        key: u64(6509n),
                        bounds: Bounds(x, y, width, Scale(44n)),
                        label: ListPersonLabel(
                            ListsLocaleHost("elist_invitations"),
                            State.frame.pending_count_text
                        ),
                        tone: ButtonTone.ButtonToneAccent
                    }
                })
            ) {
                State.frame.panel = 2n;
                State.frame.focused = false;
                State.sharing_scroll = 0n;
            }
            y += Scale(52n);
        }
    }
    if (State.state.input_error !== 0n) {
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y, width, Scale(48n)),
                text: ListsLocaleHost("results_write_failed"),
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        y += Scale(56n);
    }
    if (editing_list) {
        let committed = Field(
            Bounds(x, y, width, Scale(44n)),
            ListsLocaleHost("elist_new_list_placeholder"),
            blocked
        );
        let button_width = (width - Scale(8n)) / 2n;
        if (
            Button({
                session: State.frame.session,
                props: {
                    key: u64(6506n),
                    label: ListsLocaleHost("elist_create_list"),
                    bounds: Bounds(x, y + Scale(56n), button_width, Scale(44n)),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                    disabled: State.frame.value.count === 0n || blocked
                }
            }) ||
            (committed && !blocked)
        ) {
            Mutation(LISTS_COMMIT, -1n);
        }
        if (
            Button({
                session: State.frame.session,
                props: {
                    key: u64(6514n),
                    label: ListsLocaleHost("cancel_button"),
                    bounds: Bounds(
                        x + button_width + Scale(8n),
                        y + Scale(56n),
                        button_width,
                        Scale(44n)
                    ),
                    disabled: blocked
                }
            })
        ) {
            State.state.editing_item = -1n;
            State.state.reset_input = true;
        }
        return;
    }
    if (State.state.list_count === 0n) {
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y + Scale(32n), width, Scale(30n)),
                text: ListsLocaleHost("elist_empty_title"),
                align: TextAlign.TextAlignCenter
            }}
        />;
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y + Scale(72n), width, Scale(64n)),
                text: ListsLocaleHost("elist_empty_detail"),
                align: TextAlign.TextAlignCenter,
                wrap: NativeText.Wrap.TextWrapAuto
            }}
        />;
        return;
    }
    if (State.frame.panel === 3n) {
        y += Scale(56n);
    } else if (State.state.editing_item >= 0n) {
        if (State.frame.input.escape) {
            State.state.editing_item = -1n;
            State.state.reset_input = true;
            State.frame.focused = false;
        }
        <ControlledTextField
            session={State.frame.session}
            props={{
                key: u64(6502n),
                bounds: Bounds(x, y, width - Scale(96n), Scale(44n)),
                placeholder: ListsLocaleHost("elist_add_item_placeholder"),
                disabled: true
            }}
        />;
        <Button
            session={State.frame.session}
            props={{
                key: u64(6510n),
                label: ListsLocaleHost("elist_add_item"),
                bounds: Bounds(x + width - Scale(88n), y, Scale(88n), Scale(44n)),
                tone: ButtonTone.ButtonToneAccent,
                emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                disabled: true
            }}
        />;
    } else {
        let committed = Field(
            Bounds(x, y, width - Scale(180n), Scale(44n)),
            ListsLocaleHost("elist_add_item_placeholder"),
            blocked
        );
        if (
            Button({
                session: State.frame.session,
                props: {
                    key: u64(6507n),
                    label: ListsLocaleHost("elist_add_item"),
                    bounds: Bounds(x + width - Scale(176n), y, Scale(84n), Scale(44n)),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                    disabled: State.frame.value.count === 0n || blocked
                }
            }) ||
            (committed && !blocked)
        ) {
            Mutation(LISTS_COMMIT, -1n);
            return;
        }
        if (
            Button({
                session: State.frame.session,
                props: {
                    key: u64(6515n),
                    label: ListsLocaleHost("elist_custom_button"),
                    bounds: Bounds(x + width - Scale(84n), y, Scale(84n), Scale(44n))
                }
            })
        ) {
            BeginCustomTask(-1n, "", "");
        }
    }
    y += Scale(56n);
    let open_order = NewOpenOrder();
    let open_count: s32 = s32(0n);
    let finished_order = NewFinishedOrder();
    let finished_count: s32 = s32(0n);
    for (let index: s32 = s32(0n); index < State.state.item_count; index += 1n) {
        let row = ReadListsRowHost(index, true);
        if (row.parent_id !== current.id) {
            continue;
        }
        let leaving =
            State.state.show_completed === 0n &&
            row.id === State.state.completing_id &&
            State.state.now < State.state.completing_until;
        if (row.done === 0n || leaving) {
            nativeSet(open_order, open_count, index);
            open_count += 1n;
        } else {
            nativeSet(finished_order, finished_count, index);
            finished_count += 1n;
        }
    }
    let list_height = State.frame.height - State.frame.bottom - y - Scale(12n);
    let undo_shown =
        State.undo_item.title.count > 0n &&
        State.state.now < State.undo_until &&
        State.undo_item.parent_id === current.id &&
        State.undo_account === State.frame.public_id;
    if (undo_shown) {
        list_height -= Scale(52n);
    }
    if (list_height < Scale(72n)) {
        list_height = Scale(72n);
    }
    if (undo_shown) {
        if (
            Button({
                session: State.frame.session,
                props: {
                    key: u64(6517n),
                    label: ListsLocaleHost("elist_undo"),
                    bounds: Bounds(x, y + list_height + Scale(8n), width, Scale(44n)),
                    tone: ButtonTone.ButtonToneAccent,
                    emphasis: ButtonEmphasis.ButtonEmphasisGhost,
                    disabled: blocked
                }
            })
        ) {
            State.state.action = LISTS_RESTORE_ITEM;
            State.state.id = State.undo_item.id;
            State.state.parent_id = State.undo_item.parent_id;
            State.state.title = State.undo_item.title;
            State.state.comment = State.undo_item.comment;
            State.state.done = State.undo_item.done;
            State.state.sort_order = State.undo_item.sort_order;
            State.state.index = State.undo_item.sort_order;
            if (current.shared) {
                Remote(LISTS_RESTORE_ITEM);
            }
            State.undo_until = 0.0;
            return;
        }
    }
    let pointer = SamplePointer();
    // A drag at the top reveals completed items above the open rows.
    let pull = Swipe(
        {
            bounds: Bounds(x, y, width, list_height),
            directions: u32(SwipeDirection.SwipeDown),
            min_distance: float32(Scale(96n)),
            axis_bias: 1.5
        },
        State.finished_pull,
        {
            pointer: { x: pointer.x, y: pointer.y },
            pressed: pointer.pressed,
            down: pointer.down,
            released: pointer.released,
            input_clear:
                State.frame.scroll === 0n &&
                State.frame.panel === 0n &&
                (finished_count > 0n || State.state.show_completed !== 0n),
            owner_clear: State.frame.scroll === 0n,
            now_seconds: State.state.now,
            scale: State.frame.scale
        }
    );
    State.finished_pull = pull.gesture;
    if (pull.direction === SwipeDirection.SwipeDown) {
        State.state.show_completed = State.state.show_completed !== 0n ? 0n : 1n;
        State.frame.scroll = 0n;
    }
    let pull_offset: s32 = s32(0n);
    if (pull.dragging !== 0n && pull.delta.y > 0.0) {
        pull_offset = s32(pull.delta.y / 2.0);
        if (pull_offset > Scale(64n)) {
            pull_offset = Scale(64n);
        }
    }
    if (pull_offset >= Scale(24n)) {
        let key = State.state.show_completed !== 0n ? "elist_pull_hide" : "elist_pull_show";
        if (pull.progress >= 1.0) {
            key = State.state.show_completed !== 0n ? "elist_release_hide" : "elist_release_show";
        }
        <Text
            session={State.frame.session}
            props={{
                bounds: Bounds(x, y, width, pull_offset),
                text: ListsLocaleHost(key),
                align: TextAlign.TextAlignCenter,
                vertical_align: TextAlign.TextAlignCenter,
                disabled: true
            }}
        />;
    }
    let shown_finished = State.state.show_completed !== 0n ? finished_count : 0n;
    let row_action = false;
    const row_action_ref = nativeRef(row_action);
    let scroll = Scroll({
        session: State.frame.session,
        props: {
            key: u64(6600n),
            bounds: Bounds(x, y + pull_offset, width, list_height - pull_offset),
            content_height: (shown_finished + open_count) * Scale(72n),
            scroll_offset: State.frame.scroll
        },
        children: (scroll: NativeScroll.ScrollResult): void => {
            State.frame.scroll = scroll.scroll_offset;
            let row_y = s32(scroll.content.y);
            let row_right = x + width - Scale(14n);
            for (
                let position: s32 = s32(0n);
                position < shown_finished + open_count;
                position += s32(1)
            ) {
                let index =
                    position < shown_finished
                        ? nativeAt(finished_order, position)
                        : nativeAt(open_order, position - shown_finished);
                let visible_row =
                    row_y + Scale(64n) > s32(scroll.viewport.y) &&
                    row_y < s32(scroll.viewport.y + scroll.viewport.height);
                if (visible_row && index === State.state.editing_item && State.frame.panel !== 3n) {
                    let check_x = row_right - Scale(44n);
                    let committed = Field(
                        Bounds(x, row_y + Scale(10n), check_x - Scale(8n) - x, Scale(44n)),
                        ListsLocaleHost("elist_item_name_placeholder"),
                        blocked
                    );
                    if (State.field_escaped) {
                        State.state.editing_item = -1n;
                        State.state.reset_input = true;
                        State.frame.focused = false;

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                    if (
                        Button({
                            session: State.frame.session,
                            props: {
                                key: u64(6511n),
                                bounds: Bounds(check_x, row_y + Scale(10n), Scale(44n), Scale(44n)),
                                label: ListsLocaleHost("save_button"),
                                icon_type: s32(IconType.IconCheck),
                                icon_only: true,
                                tone: ButtonTone.ButtonToneAccent,
                                emphasis: ButtonEmphasis.ButtonEmphasisFilled,
                                disabled: State.frame.value.count === 0n || blocked
                            }
                        }) ||
                        (committed && !blocked)
                    ) {
                        Mutation(LISTS_COMMIT, -1n);

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                } else if (visible_row) {
                    let row = ReadListsRowHost(index, true);
                    let swiped = SwipeRow({
                        widget: {
                            session: State.frame.session,
                            props: {
                                key: u64(7000n + index * 4n),
                                bounds: Bounds(x, row_y, row_right - x, Scale(64n)),
                                label: row.title,
                                now: State.state.now,
                                scale: State.frame.scale,
                                start: CompleteSwipe(),
                                end: DeleteSwipe(),
                                threshold: 0.5,
                                end_threshold: 0.35,
                                long_threshold: 1.0,
                                start_width: float32(Scale(176n)),
                                long_start: EditSwipe(),
                                disabled: blocked
                            }
                        },
                        state: State.row_swipe
                    });
                    State.row_swipe = swiped.state;
                    if (
                        Button({
                            session: State.frame.session,
                            props: {
                                key: u64(8200n + index),
                                bounds: Bounds(
                                    row_right - Scale(44n),
                                    row_y + Scale(10n),
                                    Scale(44n),
                                    Scale(44n)
                                ),
                                label: ListsLocaleHost("elist_edit_task"),
                                icon_type: s32(IconType.IconEdit),
                                icon_only: true,
                                tone: ButtonTone.ButtonToneNeutral,
                                emphasis: ButtonEmphasis.ButtonEmphasisGhost,
                                disabled: blocked
                            }
                        })
                    ) {
                        BeginCustomTask(index, row.title, row.comment);

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                    let text_x = x + Scale(12n) + s32(swiped.offset);
                    let text_width = row_right - x - Scale(68n);
                    <Text
                        session={State.frame.session}
                        props={{
                            bounds: Bounds(
                                text_x,
                                row_y,
                                text_width,
                                row.comment.count > 0n ? Scale(30n) : Scale(64n)
                            ),
                            text: row.title,
                            vertical_align: TextAlign.TextAlignCenter,
                            strikethrough: row.done !== 0n
                        }}
                    />;
                    if (row.comment.count > 0n) {
                        <Text
                            session={State.frame.session}
                            props={{
                                bounds: Bounds(text_x, row_y + Scale(34n), text_width, Scale(24n)),
                                text: row.comment
                            }}
                        />;
                    }
                    if (swiped.swiped_start) {
                        State.state.done = row.done !== 0n ? 0n : 1n;
                        Mutation(LISTS_SET_DONE, index);

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                    if (swiped.clicked) {
                        State.state.done = row.done !== 0n ? 0n : 1n;
                        Mutation(LISTS_SET_DONE, index);

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                    if (swiped.right_clicked) {
                        State.row_menu_open = true;
                        State.row_menu_index = index;
                        State.row_menu_x = swiped.pointer_x;
                        State.row_menu_y = swiped.pointer_y;
                    }
                    if (swiped.swiped_long_start) {
                        BeginCustomTask(index, row.title, row.comment);
                    }
                    if (swiped.swiped_end) {
                        RememberDeleted(row);
                        Mutation(LISTS_DELETE_ITEM, index);
                        if (State.state.editing_item >= 0n) {
                            State.state.editing_item = -1n;
                            State.state.reset_input = true;
                        }

                        nativeDeref(row_action_ref) = true;
                        return;
                    }
                }
                row_y += Scale(72n);
            }
        }
    });
    if (!scroll.opened) {
        State.frame.scroll = scroll.scroll_offset;
    }
    if (row_action) {
        return;
    }
    RowContextMenu(blocked);
}

// Check uses the row’s normal activation. Edit opens the long-swipe task dialog.
function RowContextMenu(blocked: boolean): void {
    if (
        !State.row_menu_open ||
        State.row_menu_index < 0n ||
        State.row_menu_index >= State.state.item_count
    ) {
        return;
    }
    let row = ReadListsRowHost(State.row_menu_index, true);
    let items: [NativeContextMenu.ContextMenuItem, NativeContextMenu.ContextMenuItem] = [
        { id: LISTS_ROW_MENU_CHECK, label: ListsLocaleHost("elist_check_task"), disabled: blocked },
        { id: LISTS_ROW_MENU_EDIT, label: ListsLocaleHost("elist_edit_task"), disabled: blocked }
    ];
    let menu = ContextMenu({
        session: State.frame.session,
        props: {
            key: u64(8500n),
            open: true,
            x: State.row_menu_x,
            y: State.row_menu_y,
            escape: State.frame.input.escape,
            scale: State.frame.scale
        },
        items: nativeSlice(items)
    });
    if (!menu.open) {
        State.row_menu_open = false;
    }
    if (menu.activated_id === LISTS_ROW_MENU_CHECK && !blocked) {
        State.state.done = row.done !== 0n ? 0n : 1n;
        Mutation(LISTS_SET_DONE, State.row_menu_index);
        State.row_menu_open = false;
    } else if (menu.activated_id === LISTS_ROW_MENU_EDIT && !blocked) {
        BeginCustomTask(State.row_menu_index, row.title, row.comment);
        State.row_menu_open = false;
    }
}
