# Inner Breeze and feature bundles

`make subapps` builds `lists.zib`, `habits.zib` and `practice.zib` from the
independent entries in `apps/`. Each entry includes only its feature protocol,
feature decisions and required portable rules. None imports `application.zi`,
the native screens, SQLite, audio or the other two app entries.

The root `build/inbe.zib` owns unified configuration, onboarding decisions and
route policy. Its `subapps/` asset directory holds the exact three independently
built feature files. The unified executable loads the root from its embedded
`inbe.zib` asset and opens each nested feature from that package. Android,
Windows and web build paths embed the same root and nested payloads
and link a Ziran bundle runtime compiled for their target. They are required
payloads, not metadata aliases. The host opens four persistent VM instances,
checks the capability allowlist and protocol identity, and invokes them through
typed value messages. Root route requests dispatch to the appropriate feature
VM through a checked capability, so a root route cannot silently substitute
native feature behavior. Missing, corrupt or mismatched identities fail startup
before opening storage. Every incoming record, nested record, array and scalar
is validated before decoding or calling persistence. A wrong host schema fails
the VM call without applying that invalid value.

Lists owns list selection/reset decisions, per-item visibility, edit and
completion decisions, and list/item mutation selection. The existing Lists
screen calls its loaded bundle for these actions.
Visibility results are cached in ephemeral host state across unchanged frames;
data reloads, edits and filter changes invalidate them, and the Lists module
supplies the deadline for timed completion visibility. Scrolling and rendering
reuse the results without re-entering the VM for every item each frame.
Habits owns page transitions,
linked-day action selection, name trimming/validation and form-save decisions.
Practice owns the live breathing, meditation, sun-salutation and patterns timing
steps; foreground and mobile/web elapsed-time paths call the same loaded bundle.

After language selection, fresh profiles choose Lists, Habits and Practice.
Only selected feature instances remain loaded and their navigation entries
are shown. Choosing none keeps Settings available. Settings can reopen the
chooser; switching selections preserves stored data. Existing profiles without
the new settings retain all three apps. Choices and incomplete onboarding
survive restart in the existing settings table.

An explicit mini launch asks the root for a temporary Practice-only selection,
even when the full profile selected Lists only or no apps. It loads the Practice
VM before opening the practice menu. Mini sessions keep their existing temporary
storage behavior, so the saved app selection and session history are untouched.
Expanding the mini window restores the full profile's module selection and keeps
Practice loaded while its active session continues. Later saves retain the
profile's original selection.

The desktop host also accepts `--feature practices|habits|lists` after normal
initialization. Repeat feature requests use `_HARMONY_APP_FEATURE` on the
process's own SDL X11 window: CARDINAL 1 selects Lists, 2 Habits, 4 Practices;
0 restores the normal parent route. `app_open_feature(void *, int32_t)` uses
the same IDs. The host consumes valid property requests and enables a requested
feature through the root before routing, preserving the same database and
identity. Harmony can reuse one supervised runtime through this interface;
this repository does not install or deploy Harmony's launcher changes.

`SubappsOpenPackage` accepts validated root bytes, and features are canonical
assets inside that root. This provides a replacement package boundary for future
updates. No automatic updater, network delivery or hot replacement is enabled
by this change.

The shared host retains the existing Kryon native screen compositions and
renderer, input/hover/focus transitions, navigation shell, theme, locale and
settings. It also retains the single database, migrations, sync v6 identity,
outbox, list and habit relationships, habit-day storage, practice setup,
audio/notifications and session completion/results persistence. Messages copy
returned strings into host-owned buffers before the VM returns. Application,
UI session and database pointers never cross the portable feature boundary.
Returned text views remain valid until the next call to the same feature;
the screen copies persistent results into its existing state buffers.
There is no second database or per-feature sync account.

These bundles are loadable feature sub-apps inside Inner Breeze. The root and features need its
capabilities and are not standalone Kryon UI applications in the generic ZIB
player. This change does not convert the retained screens to portable UI trees,
add hot replacement or deploy/install an app. Desktop focus loss remains
independent of mobile lifecycle and explicit user pause.

`make subapps-test` executes the actual three bundles with shared persistence,
upgrades a 1.8.9 database fixture, checks shared identity and relationships after
restart, covers rejected-name retries and practice completion/pause, and rejects
missing/corrupt/wrong-identity/wrong-record/wrong-scalar payloads. Temporary-file
creation is denied during that test. `make subapps-navigation-test` uses only
private Xvfb windows and disposable screenshot profiles. It exercises populated
Lists at the existing supported capacity, UI edits and navigation, records
memory/CPU observations and verifies practice ticking without focus and stopping
on explicit pause. Target build/runtime outcomes and deployment evidence are
recorded separately in the project's ignored task receipts.
`make subapps-artifact-test` checks that the native executable embeds its root
exactly once, containing each independent feature payload exactly once, and
that its single generated Lists codec matches the current protocol schema.

`make subapps-onboarding-test` checks real language-to-chooser navigation,
Lists-only and zero-app selections, restart between onboarding steps, saved
choices, existing-profile defaults and data/identity preservation on private
Xvfb with disposable profiles. It covers mini launch and expansion from disabled
Practice profiles, saving/restarting, and explicit feature requests in one
process. The compiled package test also compares every
nested asset by name and byte content through the real bundle-reader API.
