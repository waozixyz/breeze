// Authored application UI. Native state and effects live in inbe_view.zi.
import * as NativeLayout from "kryon/layout";
import * as NativeScroll from "kryon/scroll";
import * as State from "inbe_view";
import { Available, Bit, FinishPicker, PickerLocaleHost, Scale, Status } from "inbe_view";
import { Button } from "kryon/tsx/button";
import { ButtonEmphasis, ButtonTone } from "kryon/control_props";
import { Checkbox } from "kryon/tsx/checkbox";
import { Scroll } from "kryon/tsx/scroll";
import { FlagComplement, FlagIntersection, FlagUnion } from "native_flags";
import { InbeMessage } from "inbe_types";
import { Text } from "kryon/tsx/text";
import { Toggle } from "kryon/tsx/toggle";

export function InbePickerViewComposition(): InbeMessage {
    let column = NativeLayout.CenteredColumnFor(State.frame.width, Scale(420n), Scale(16n));
    let top = Scale(20n);
    let compact = State.frame.height < Scale(480n);
    let scroll_top = compact ? Scale(104n) : Scale(156n);
    let content_height = Scale(548n);
    for (let packageId: s32 = 1n; packageId <= s32(5n); packageId += s32(1)) {
        if (Status(packageId) >= 3n) {
            content_height += Scale(16n);
        }
    }
    <Text
        session={State.frame.session}
        props={{
            bounds: {
                x: float32(column.x),
                y: float32(top),
                width: float32(column.width),
                height: float32(compact ? Scale(28n) : Scale(40n))
            },
            text: PickerLocaleHost("cells_picker_title"),
            size: Scale(24n)
        }}
    />;
    <Text
        session={State.frame.session}
        props={{
            bounds: {
                x: float32(column.x),
                y: float32(top + (compact ? Scale(32n) : Scale(48n))),
                width: float32(column.width),
                height: float32(compact ? Scale(44n) : Scale(84n))
            },
            text: PickerLocaleHost("cells_picker_body"),
            size: State.frame.font
        }}
    />;
    let left = column.x;
    let scroll = (
        <Scroll
            session={State.frame.session}
            props={{
                key: 27000n,
                bounds: {
                    x: float32(left),
                    y: float32(scroll_top),
                    width: float32(column.width),
                    height: float32(State.frame.height - scroll_top - Scale(80n))
                },
                content_height: content_height,
                scroll_offset: State.frame.scroll
            }}
            children={(view: NativeScroll.ScrollResult): void => {
                PickerRows(view, left);
            }}
        />
    );
    State.frame.scroll = scroll.scroll_offset;
    if (!scroll.opened) {
        return FinishPicker();
    }
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 274n,
                    bounds: {
                        x: float32(column.x),
                        y: float32(State.frame.height - Scale(64n)),
                        width: float32(column.width),
                        height: float32(Scale(44n))
                    },
                    label: PickerLocaleHost("next_button"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        State.frame.confirm = true;
    }
    return FinishPicker();
}

function PickerRows(scroll: NativeScroll.ScrollResult, left: s32): void {
    State.frame.scroll = scroll.scroll_offset;
    let content_width = s32(scroll.content.width);
    let row_top = s32(scroll.content.y);
    let labels: [string, string, string, string, string] = [
        "Lumi",
        PickerLocaleHost("tab_habits"),
        PickerLocaleHost("tab_practices"),
        PickerLocaleHost("tab_elist"),
        PickerLocaleHost("tab_diary")
    ];
    let packageIds: [s32, s32, s32, s32, s32] = [5n, 2n, 3n, 1n, 4n];
    let index: s32 = 0n;
    while (index < 5n) {
        if (index === 0n || index === 3n) {
            <Text
                session={State.frame.session}
                props={{
                    bounds: {
                        x: float32(left),
                        y: float32(row_top),
                        width: float32(content_width),
                        height: float32(Scale(36n))
                    },
                    text: PickerLocaleHost(index === 0n ? "cells_recommended" : "cells_optional"),
                    size: State.frame.font
                }}
            />;
            row_top += Scale(40n);
        }
        let packageId = packageIds[index];
        let bit = Bit(packageId);
        let checkbox = (
            <Checkbox
                session={State.frame.session}
                props={{
                    id: packageId === 5n ? 278n : 270n + packageId - 1n,
                    bounds: {
                        x: float32(left),
                        y: float32(row_top),
                        width: float32(content_width),
                        height: float32(Scale(44n))
                    },
                    label: labels[index],
                    checked: FlagIntersection(State.state.enabled_apps, bit) !== 0n
                }}
            />
        );
        if (checkbox.changed) {
            if (checkbox.checked) {
                State.state.enabled_apps = FlagUnion(State.state.enabled_apps, bit);
            } else {
                State.state.enabled_apps = FlagIntersection(
                    State.state.enabled_apps,
                    FlagComplement(bit)
                );
            }
        }
        row_top += Scale(44n);
        {
            let status = Status(packageId);
            let key =
                FlagIntersection(State.frame.installed, bit) !== 0n || Available(packageId)
                    ? "cells_installed"
                    : "cells_download";
            if (status === 1n) {
                key = "update_downloading";
            } else if (status === 3n) {
                key = "cells_download_failed";
            } else if (status === 4n) {
                key = "cells_signing_setup";
            }
            <Text
                session={State.frame.session}
                props={{
                    bounds: {
                        x: float32(left + Scale(32n)),
                        y: float32(row_top),
                        width: float32(content_width - Scale(32n)),
                        height: float32(status >= 3n ? Scale(44n) : Scale(28n))
                    },
                    text: PickerLocaleHost(key),
                    size: Scale(14n)
                }}
            />;
            row_top += status >= 3n ? Scale(44n) : Scale(28n);
        }
        index += 1n;
    }
    <Text
        session={State.frame.session}
        props={{
            bounds: {
                x: float32(left),
                y: float32(row_top + Scale(12n)),
                width: float32(content_width - Scale(80n)),
                height: float32(Scale(44n))
            },
            text: PickerLocaleHost("cells_auto_update"),
            size: State.frame.font
        }}
    />;
    let automatic = (
        <Toggle
            session={State.frame.session}
            props={{
                id: 276n,
                bounds: {
                    x: float32(left + content_width - Scale(64n)),
                    y: float32(row_top + Scale(12n)),
                    width: float32(Scale(64n)),
                    height: float32(Scale(44n))
                },
                label: PickerLocaleHost("cells_auto_update"),
                value: State.frame.automatic
            }}
        />
    );
    if (automatic.changed) {
        State.frame.automatic = automatic.value;
    }
    row_top += Scale(64n);
    if (
        (
            <Button
                session={State.frame.session}
                props={{
                    id: 277n,
                    bounds: {
                        x: float32(left),
                        y: float32(row_top),
                        width: float32(content_width),
                        height: float32(Scale(44n))
                    },
                    label: PickerLocaleHost("cells_check_updates"),
                    tone: ButtonTone.ButtonToneNeutral,
                    emphasis: ButtonEmphasis.ButtonEmphasisSoft
                }}
            />
        )
    ) {
        State.frame.check_updates = true;
    }
}
