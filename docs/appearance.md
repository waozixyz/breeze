# Custom appearance

Open **Settings → Appearance → Advanced appearance (CSS)**. Choose **All apps**
or Lists, Habits, Practices, Diary, or Lumi. Each scope has its own custom sheet.
The shared style pack and Inbe defaults remain readable in the Source menu.

Valid edits render after a short typing pause. An invalid draft stays editable;
the last complete preview remains installed. The status shows the source file,
line, and column of an error. **Save** persists the selected sheet for the current
account. **Discard** restores its saved sheet. **Undo edit** restores a previous
draft. **Format CSS** formats the draft without saving it. **Reset to defaults**
clears and saves only the selected customization. Resetting one app still keeps
the All apps customization; reset All apps as well to return to shipped styling.

```css
Button {
  border-radius: 24px;
}

Button.profile-header:hover {
  border-width: 2px;
}

:root {
  --canvas: #14202b;
}
```

Sheets are written in Kryon CSS, the subset of CSS every Kryon platform
draws (see the `css` package's README). Use the component names, classes,
custom properties and properties shown in the shipped sheets; anything outside
the subset is an error naming its line. Styles resolve in this order: shared pack and app defaults, All apps,
then the selected app. The inspector displays resolved properties and matching
source rules for a component and interaction state. Sheets may contain up to
8,191 UTF-8 bytes; the complete cascade allows 512 rules. Custom sheets cannot
import files. Saved preferences never modify shipped assets or other accounts. Sheets
saved while Breeze used KSS convert to CSS the first time Breeze starts; one
that has no CSS form opens as a draft with the error.

**Ask Lumi** opens the conversation with the selected scope in a draft. Describe
the look you want and send it. Online Lumi and Harmony use the same app-owned
tools: `read_style`, `inspect_style`, `preview_style`, `save_style`, `reset_style`,
`undo_style`, `discard_style`, and `format_style`. A mutation requires the current
revision from a read or preceding operation, so an outdated edit cannot overwrite
newer changes. Lumi requires an available online chat service; manual editing
works offline.

Verification: `make style-apply-zi-test appearance-ui-test` checks parsing,
atomic validation, scope isolation, persistence, reset, and real editor input on
a private display. Harmony's `tests/app_mcp_test.py` checks the registered tool
path through its companion and hosted app. Daochi's chat tests cover the complete
tool count and larger style-result continuations while retaining input limits.
