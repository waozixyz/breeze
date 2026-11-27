import { LocaleDropdownNewOptions } from "locale_dropdown";
// Authored UI composition; native application state remains in locale_dropdown.zi.
import * as NativeDropdown from "kryon/dropdown";
import { RegisterLanguagePickerFonts } from "fonts";
import { Session } from "kryon/session";
import { Dropdown } from "kryon/tsx/dropdown";
import { LocaleLanguageAt, LocaleLanguageCount, LocaleText } from "locale";

export function LocaleDropdownView(
    session: Session,
    props: NativeDropdown.Props
): NativeDropdown.Result {
    RegisterLanguagePickerFonts();
    let options = LocaleDropdownNewOptions();
    let count = LocaleLanguageCount();
    if (count > 64n) {
        count = 64n;
    }
    if (count <= 0n) {
        nativeAt(options, 0n).label = LocaleText("language_system_label");
        count = 1n;
    } else {
        let index: s32 = s32(0n);
        while (index < count) {
            nativeAt(options, index).label = LocaleLanguageAt(index).label;
            index = index + 1n;
        }
    }
    let resolved = props;
    if (resolved.selected_index < 0n || resolved.selected_index >= count) {
        resolved.selected_index = 0n;
    }
    return Dropdown({
        session: session,
        props: resolved,
        options: nativeSlice(options, 0n, count)
    });
}
