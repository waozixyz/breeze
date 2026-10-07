# Inner Breeze cell packages

Inner Breeze has a root package and five cells, including Lumi.
All five cells ship with the app and can be added to the sidebar offline.
Selections are stored per app and synced with the account. Lumi always ships with
Inner Breeze. Her selection controls her sidebar shortcut, while her harness and
tools remain available.
The root contains shared fonts, translations, themes and icons; Practices owns
its images and sounds. Each feature can add private package resources under
`assets/lumi/`, `assets/habits/`, `assets/practices/`, `assets/lists/` or `assets/diary/`.
The cell picker, Lists and Diary editor/calendar compose the
standard Kryon widgets inside their ZIBs. Raylib, Android and canvas bind the
same typed render effects to their normal widgets. File dialogs, persistence,
account sync and native input stay in the wrapper. Habits and Practices
still use compiled screen compositions; migrating those screens is required
before every visual change can ship without rebuilding the wrapper.

## Lumi

Lumi is the default home for new profiles and for the first launch after her
introduction. Existing app choices and todo data are retained. Settings lists
Lumi in the same compact list as every other cell. Removing her shortcut
keeps her package, conversation and app abilities; she cannot be uninstalled.
Her firefly image belongs to `assets/lumi/mascot.png` in her package and appears
beside her replies. The conversation has no title bar; navigation uses a
monochrome outlined firefly, matching the other navigation glyphs. The sidebar
uses `assets/lumi/sidebar.shape` with the standard button size and foreground;
navigation bars use the matching transparent `assets/lumi/sidebar.png`.

`apps/lumi/lumi_view.zi` composes the chat and command suggestions with hosted
Kryon widgets. `apps/lumi/engine.zi` is the first small offline interpreter;
its typed `LumiAction` output is the boundary for a future on-device model.
There is no cloud inference, model download or trained model in this version.
Translated commands and the stable `/todo TITLE`, `/done TITLE`, `/reopen TITLE`,
`/habit NAME`, `/lists`, `/habits`, `/practices` and `/diary` forms work offline.
`start whm` starts the Wim Hof Method immediately; meditation, Sun Salutation
and breathing patterns use the same practice-start path as other app controls.
Autocomplete appears as one row of compact chips above the composer. It
completes command prefixes and existing todo or habit names without executing them.
Commands ignore case and tolerate one insertion, deletion, substitution or
adjacent transposition per command word. Anchored, bounded regex patterns
recognize practice phrases and punctuation after normalization. User item names
remain exact or uniquely matched prefixes, with Unicode case folding.
Sending “complete habit” lists the available habits and asks which one; the next
name reply completes that habit. Conversation choice state resets with accounts.
Sending executes only a supported action. Completion chooses an exact match,
or a unique prefix, and asks for clarification when multiple items match.
Habit completion reaches today's counter target while preserving higher or
linked session counts. Repeating a completion never uncompletes a habit.
The `LumiTools` context reports the installed and enabled cells to the engine;
help, suggestions and actions all follow those capabilities. Todo tools require
Lists, habit tools require Habits, and practice starts require Practices.
The wrapper validates IDs and live state again before using the existing
user-scoped storage, sync outbox and practice registry. A practice starts after
the chat cell finishes its call, within the same application frame.

The conversation keeps the latest 32 exchanges in the active user's local
settings. It survives restart, resets on account changes, and is not part of
account preference sync. The wrapper provides input, persistence and bounded
app effects; no database pointers or arbitrary code cross the cell boundary.

Lumi can open Settings or Appearance, change the app theme with `/theme forest`
(or another published theme name), and choose light, dark or system mode.
These actions use the same validation, persistence and refresh path as Settings.
The app publishes its MCP tool schemas in `assets/mcp/tools.json`, including
`get_settings`, `set_theme`, `set_theme_mode`, `set_setting`, `open_view` and
`practice`. Harmony discovers and calls them through `app_mcp`; Lumi is scoped
to Inner Breeze. All its cells share the single Lumi chat. Harmony's per-app
Enable chat / Disable chat control preserves the agent and saved conversation.

## Build and installation

`make cells` produces:

- `build/inbe.zib`, containing `cells/lumi.zib`, `cells/habits.zib` and `cells/practices.zib`.
- Independent `build/cells/{lumi,habits,practices,lists,diary}.zib` files.
- `build/inbe-full.zib`, a local development and test bundle containing all five.

Native, Android and browser builds embed the base root. Lists and Diary are
absent from that root and the native embedded payload. Recommended apps work
offline. Downloaded packages are stored in the private `packages/` directory
beside `inbe.db`. The host checks signed release identity, API compatibility,
hash, size, allowed capabilities and the typed identity handshake before
publishing an immutable payload and atomically replacing its current pointer.
Root packages must contain exactly the three signed recommended dependencies.
Malformed packages cannot apply writes through a mismatched host protocol.

The cell selection screen follows language selection. Settings → Cells & sidebar
lists installed and available cells alongside the sidebar shortcuts. Drag a
shortcut's handle to reorder it, or use its trash icon to remove that shortcut.
A cell's trash icon removes it from the active selection while preserving its
saved data and bundled package; the plus button adds it back immediately.
Settings is fixed last and is absent
from the editable list. Existing
profiles retain their selection and saved sidebar order.
Each cell appears once, with active shortcuts in sidebar order and hidden cells
after them. The list shows icons, names and controls without status paragraphs.

## Updates and versions

Downloads use the Daochi release v2 endpoints on `https://api.waozi.xyz`:
`/api/v2/packages/{app_id}/latest` and
`/api/v2/packages/{app_id}/{sha256}.zib`. IDs are `inbe`, `inbe.habits`,
`inbe.practices`, `inbe.lists`, `inbe.diary` and `inbe.lumi`.

Automatic updates default on and check daily for the root and selected apps.
The cell picker includes an automatic-update switch and a manual check button.
Turning the switch off cancels active and queued automatic work; manual
installation and checking remain available. No automatic network checks run
until a publisher is configured. Disabling updates is a device preference.
Account restoration can still install a newly selected app.

Only signatures from `apps/publishers.json` are accepted. The verifier rejects
older release sequences, altered metadata, incompatible APIs, oversized
payloads, corrupt hashes and unexpected root dependencies. A missing or corrupt
cache can be repaired with the same signed sequence and hash. Failed updates
preserve the existing package. Local sequence floors include the bundled
baseline. Feature updates activate between frames when editing and practice
state can be preserved. Root updates activate on restart; About identifies a pending root update.
Recommended feature versions follow the active signed root dependencies, and
newer independently cached cells remain selected after restart.

`apps/versions.json` records separate numeric versions and increasing sequences
for every package. Add a numeric entry to the relevant module's
`apps/<source>/CHANGELOG.md`, then run `./update_version.sh --cell NAME`.
Use `practices` as the module name; its source directory is `apps/practice/`.
Changes to either nested recommended payload also require advancing the root
package version. Advance the wrapper for compiled host or remaining compiled UI changes: add
a numeric main changelog entry and run `./update_version.sh`.
About retains the wrapper version and displays each package version separately.
Module-only changes do not trigger the APK release workflow.
Packaged resource and translation changes also trigger only the package workflow.
`make package-version-test` checks every module's numeric changelog, ledger,
sequence and bundled status before publishing.

## Publishing configuration

The `Cell packages` GitHub Actions workflow builds and verifies package releases
on master. It signs and publishes automatically when all deployment values are
configured. Incomplete configuration produces downloadable build artifacts
without claiming publication. When only the signing configuration is present,
the archived artifacts include signed releases ready to import on the node.

1. Register the six app IDs and an active Ed25519 publisher key in Daochi.
2. Add the public key to `apps/publishers.json`, scoped to the six app IDs:
   `[{"key_id":"<registered ID>","public_key":"<64 lowercase hex digits>","app_ids":["inbe","inbe.habits","inbe.practices","inbe.lists","inbe.diary","inbe.lumi"]}]`.
3. Configure repository secrets `INBE_PACKAGE_SIGNING_KEY` (PEM Ed25519 key)
   and `INBE_NODE_SSH_KEY` (deployment SSH key), plus
   `INBE_NODE_KNOWN_HOSTS`, `INBE_NODE_SSH_TARGET` and
   `INBE_NODE_PACKAGE_STORE` (the node's absolute package directory).
   Node connection values are secrets so GitHub masks them in job output.
4. Configure repository variable `INBE_PACKAGE_KEY_ID`.
5. Ensure the node runs Daochi's release v2 package HTTP implementation and
   has Python with `cryptography` available for the remote importer.

`python3 scripts/package-release.py --store build/package-releases --key
/path/to/private.pem --key-id REGISTERED_ID` stages a signed release locally.
Add `--ssh-target USER@HOST --remote-store /absolute/node/package-store` to
publish, and `--verify-origin https://api.waozi.xyz` to check the public node's
served metadata and every package hash and size. The workflow requires this
public verification before reporting a successful publication.
The publisher checks that the signing key matches the shipped public
pin and rejects changed packages whose version and sequence have not advanced.
Upload staging uses a private remote directory and strict SSH host checking.
Private signing material is never included in package archives.

To prepare the initial publisher registrations, the node operator can run
`python3 scripts/package-manifests.py --origin https://api.waozi.xyz
--publisher-key /private/publisher.pem --approval-key /private/registry.pem
--key-id REGISTERED_ID --output build/package-registrations`. The output
contains only public keys, manifests and signatures. Submit each app JSON to
`POST /api/v1/apps/register-signed` on the node. Its configured registry public
key must match `registry-public-key.hex`. The package publisher cannot approve
itself: registration requires the separate node operator key. Existing account
collections, capabilities, token policies and other publisher keys are retained;
suspended, revoked and node-restricted registrations are not replaced. Repeating
the preparation keeps unchanged manifest versions and advances changed ones.

The wrapper release workflow requires public pins covering all six app IDs,
so each included cell has a configured publisher for its updates.
The public pin `inbe-2026-10` covers the root and all five apps. The private
signing key is kept in an ignored local backup and is excluded from every
package artifact. Optional production installation requires registering this
public key on the node and publishing the signed packages. Automatic server
publication additionally requires the GitHub signing and node deployment
configuration above; a checked build does not establish that configuration.

## Account app choices

Sync v6 uses `private.inbe.v1.app-preferences`. Each of the five `app_used_*`
keys is a separate timestamped record, including explicit zero values for
removals. Independent changes merge without overwriting unrelated selections.
Pending local choices win equal timestamps; newer remote choices win.
Invalid keys, values and timestamps cannot alter preferences. Versions, package
paths, release sequence floors and the automatic-update preference stay local.
All apps share the existing account, SQLite database and outbox. Diary entries
currently remain device-local, as they were in Harmony.

## Diary and standalone use

Diary owns date arithmetic, entry editing, JSON documents and calendar marks in
its own VM. Its bounded host capabilities provide only its private files and
clock. Entries use Harmony's existing version-1 per-day document format;
text edits preserve attached photo metadata. Failed or malformed reads never
overwrite the original document. Native storage uses an exclusive directory
lock and atomic writes.

For explicit migration, set `INBE_DIARY_IMPORT=/absolute/harmony/diary` when
opening Diary. The importer copies safe regular filenames and skips existing
Inbe files and symlinks. It leaves Harmony originals untouched. There is no
automatic migration from an unrelated live profile. Harmony's Diary catalog
entry now opens the Inbe child inside the existing supervised parent window
and passes its own Diary folder for a safe import. Old saved native-renderer
metadata does not restore a second Diary engine. Inbe's Diary package includes
photo attachment, previews, navigation and removal; removal retains original
photo bytes. Native and Android use their ordinary file pickers.

The desktop wrapper accepts `--bundle /path/to/inbe.zib`, or an individual
Lumi, Habits, Practices, Lists or Diary ZIB. A feature bundle opens its own app using
the same host and account. Explicit local files still pass capability and
identity checks; publisher verification applies to network installation.
`--feature lumi|habits|practices|lists|diary` opens a selected feature.
`_HARMONY_APP_FEATURE` requests on the process's own SDL X11 window use
1 for Lists, 2 for Habits, 4 for Practices, 8 for Diary and 0 for the parent.
The host control interface also supports `open.diary`.

Mini mode remains a temporary Practices session. It preserves the full
profile's selection and its existing history behavior. Desktop focus loss
continues to be distinct from mobile lifecycle and explicit pause.

These bundles currently need Inbe's capabilities and are not complete
standalone UI applications in the generic Kryon player. The cell picker, Lists
and Diary compose standard widgets through the same raylib and canvas host.
Their layouts and all packaged graphics, fonts, styles and translations can
update without a wrapper release. Habits and Practices still contain compiled
screen compositions; moving those compositions into their bundles is required
to finish the entirely portable architecture. Changes to their compiled UI or
to native host capabilities still require a wrapper release.

## Verification

Harmony Projects shows this wrapper release, every cell version and its Moto
screenshots. Harmony's `make inbe-release-verify` checks the latest published
APK on the development Moto and writes private evidence under
`backup/releases/`. A newer version starts pending until its exact APK passes
launch and resume checks. Debug candidates stay labeled as candidates.

Translation catalogs follow the current package asset provider. An early
lookup before the root mounts retries when resources become available, and
changing packages rebuilds the catalogs before reusing any borrowed text.
`make locale-zi-test` checks every key in all 12 languages and exercises delayed
resource availability, provider replacement and fallback restoration.

`make cells-test` exercises the root and all five actual feature bundles,
typed capability rejection, shared SQLite/identity, a 1.8.9 upgrade fixture,
practice timing, all selection masks and Diary Unicode/calendar/document edits.
`make package-release-test` checks Ed25519 metadata, payloads, signed nested
content, rollback rejection, cache repair, manual checking with auto-update off
and cancellation that preserves manual requests. Account preference tests
exercise real sync SQL and account isolation. The Wasm download test verifies
bounded browser streaming, filesystem writes, cancellation and failures.
`make cells-diary-test` verifies the standalone Diary window, delayed saves,
clock insertion, calendar and restart. GUI onboarding and navigation tests run only on private Xvfb displays with
application-owned windows and disposable profiles.
`make package-workflow-test` executes the publisher configuration branches and
checks the workflow's signing and upload commands, including private file
permissions and keeping credentials out of its output.
