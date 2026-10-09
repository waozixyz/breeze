# Custom appearance

Open **Settings → Appearance → Advanced appearance (KSS)**. Choose **All apps**
or Lists, Habits, Practices, Diary, or Lumi. Each scope has its own custom sheet.
The shared style pack and Inbe defaults remain readable in the Source menu.

Valid edits render after a short typing pause. An invalid draft stays editable;
the last complete preview remains installed. The status shows the source file,
line, and column of an error. **Save** persists the selected sheet for the current
account. **Discard** restores its saved sheet. **Undo edit** restores a previous
draft. **Format KSS** formats the draft without saving it. **Reset to defaults**
clears and saves only the selected customization. Resetting one app still keeps
the All apps customization; reset All apps as well to return to shipped styling.

```kss
Button {
    radius: 24;
}

Button.profile-header:hover {
    border-width: 2;
}

tokens {
    color {
        canvas: #14202b;
    }
}
```

KSS is Kryon's stylesheet language. Use the component names, classes, tokens,
and properties shown in the shipped sheets; unsupported CSS properties produce
errors. Styles resolve in this order: shared pack and app defaults, All apps,
then the selected app. The inspector displays resolved properties and matching
source rules for a component and interaction state. Sheets may contain up to
8,191 UTF-8 bytes; the complete cascade allows 512 rules. Custom imports cannot
load files. Saved preferences never modify shipped assets or other accounts.

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
