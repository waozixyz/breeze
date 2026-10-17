# Inner Breeze cell packages

Inner Breeze has a root package and six cells, including Lumi and Leaderboard.
The interface calls these Apps and presents them in one sidebar settings list.
All six cells ship with the app and can be added to the sidebar offline.
Leaderboard is installed for every profile but is not pinned by default.
Selections are stored per app and synced with the account. Lumi always ships with
Inner Breeze. Her selection controls her sidebar shortcut, while her harness and
tools remain available.
The root contains shared fonts, translations, themes and icons. Practices keeps
small previews, controls and shared cues. Heavy content is downloaded per
practice and works offline afterwards. Each feature can add private resources under
`assets/lumi/`, `assets/habits/`, `assets/practices/`, `assets/lists/`, `assets/diary/`
or `assets/leaderboard/`.
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
The chat avatar is mirrored toward the conversation. Enter sends a message;
Shift+Enter inserts a new line and the composer grows with the draft.

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
“Write this to my diary: TEXT” and `/journal TEXT` append an entry to today's
Diary with the current local time above the message. A request without text asks
for it and saves the next reply, preserving line breaks and existing entries.
Use `/cancel` to cancel that question. Unknown requests receive a brief question;
command examples appear only when the user asks for help.
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
Bug reports and suggestions still require the feedback card's Yes. The first
acknowledgement means the report is queued on this device; delivery requires an
Inner Breeze account and internet access. Lumi confirms receipt by the private
developer inbox only after Daochi returns the matching report ID. A failed or
invalid acknowledgement leaves the approved report queued for retry and adds a
failure notice once, including across restarts. Inbox receipt does not mean a
developer has reviewed the report or started a fix.
Lumi can display typed chart cards alongside text replies. Ask
`/progress sessions 7`, `/progress meditation 30`, `/progress retention 7`, or
`/progress habits 7` (1–31 days including today). Charts use the active account's
saved history, omit deleted records, fill empty days with zero, and persist as
snapshots. Meditation and best daily WHM retention are measured in seconds;
habits count scheduled habits whose manual or linked activity count reaches the
target. Select a bar to see its date and value. Online requests use the same
`show_progress_chart` tool; model-provided data never becomes a chart.

Online Lumi sets a habit's schedule and notification with `set_habit_schedule`,
the same choices as the habit editor: daily, weekly on any weekdays, monthly on
days of the month, the last day or a weekday of a week of the month, yearly, a
formula over the day's numbers, or no set days, every N days, weeks, months or
years from a start date. A changed schedule plans the days from today on;
earlier days keep the schedule they had, and nothing recorded is removed. Days
off the schedule have no circle but still open, and what was recorded on them
shows faded. The context lists each habit's schedule and notification hour.

A habit keeps what happens on its days as entries. It can ask questions, set
under "Ask when done" in its editor: each has its words, an answer type (text,
a whole number, a time or yes or no) and what counts as good: above or below
the average of the values recorded before it (later or earlier for times; new
number questions start above, new time questions earlier), at least, at most or
between two values, a time after, before or between two times, or a yes or a
no. A habit can instead measure spans ("Measure start to end", which turns
counter mode off): a tap starts a span, and a tap on its half-filled day opens
it, where the end is picked, set to Now, or cleared to keep it running; a tap
never ends a span. A span habit's first and second time questions ask its start
and end, so they are not asked twice. Spans are good by their length, whenever
they start: shorter or longer than the average, at least, at most or between
lengths in hours and minutes, or any. The entry dialog's Skip marks the day done
without answers. Without questions or spans a tap marks the day as
before. With them the Habits package answers a day tap with
`HABITS_DAY_QUESTIONS` or `HABITS_DAY_SPAN`: an open day takes a new entry in
the entry dialog (its time, or a span's start and end, then the questions), and
a day with entries opens the day's screen, which also shows its practice
sessions, to add, change or delete entries or end a running span. A day with an
entry (for spans an ended one) is done. Counting habits open the day's entries
from their count dialog. Questions and the span setting are stored on the habit
(`habits.questions` as JSON, `habits.span` and the span's goal in
`span_goal`, `span_low` and `span_high` as minutes); entries are rows of
`habit_entries` with a start, an end (0 while a span runs) and their answers as
JSON, each answer keeping the question's id and words, so an entry reads the
same after a question changes or goes. Entries sync as their own encrypted
records (`private.inbe.v1.habit-entries`) with deletions; an older app keeps a
habit's questions and span and skips entries. Every change of a habit's
settings is kept in `habit_changes` (what changed, the question it concerns,
the values before and after) and syncs as `private.inbe.v1.habit-changes`; each
entry is judged by the goal its question had when it was recorded. The habit's
statistics add up the last 30 days: spans' average and longest length, a bar per span, and when they
started and ended on average; for each question the average and total of
numbers, the average and earliest to latest of times (cut at the day's longest
unanswered stretch, so bedtimes around midnight average correctly), how often
the answer was yes, how many answers were on target, and the latest written
answers. Charts (Plot's band chart) shade each day's good range, so a changed
goal or a moving average steps, and hovering or tapping a value shows its day,
value and goal; a Changes card lists the habit's latest changes. Online Lumi
sets a habit's tracking with `set_habit_tracking` (check, count with a target,
or span with its good length) and its questions and good answers with
`set_habit_questions`; her context lists both for each habit.

Inner Breeze has no donations; Dew is how people pay. Donation cards that older
versions saved stay in the synced history but are no longer shown, and Lumi
packages before 1.5.0 still import the retired donation calls, which return
nothing. Old text-only chat history remains readable. Cards persist in the same
account-scoped local conversation and render with standard Kryon Text, Box and
Button widgets.

The app publishes its MCP tool schemas in `assets/mcp/tools.json`, including
`get_settings`, `set_theme`, `set_theme_mode`, `set_setting`, `open_view` and
`practice`. Harmony discovers and calls them through `app_mcp`; Lumi is scoped
to Inner Breeze. All its cells share the single Lumi chat. Harmony's per-app
Enable chat / Disable chat control preserves the agent and saved conversation.

## Build and installation

`make cells` produces:

- `build/inbe.zib`, containing every cell under `cells/`.
- Independent `build/cells/{lumi,habits,practices,lists,diary,leaderboard}.zib` files.
- `build/inbe-full.zib`, a local development and test bundle containing all six.

Native and browser builds embed the base root. Android stores `inbe.zib`
once in APK assets and opens its bytes through the NDK asset manager. Each
CPU library contains only the native host and small bootstrap assets, so a
universal APK shares the artwork across all four architectures. Direct Gradle
builds run `make cells` and stage the current package before merging assets.
Lists and Diary are
absent from that root and the native embedded payload. Recommended apps work
offline. Downloaded packages are stored in the private `packages/` directory
beside `inbe.db`. The host checks signed release identity, API compatibility,
hash, size, allowed capabilities and the typed identity handshake before
publishing an immutable payload and atomically replacing its current pointer.
Root packages must contain exactly the three signed recommended dependencies.
Malformed packages cannot apply writes through a mismatched host protocol.

Runtime resources are selected in `scripts/prepare-package-assets.py`; source
icons, store banners, prompts and test images are excluded. Sun Salutation
keeps its full four-character, 30 fps timeline while storing identical PNGs
once. Character regeneration losslessly compresses the PNGs and regenerates
`sun_salutation_inventory.zi`; builds check that this table is current. The
compression step requires Python `zopfli`, while ordinary builds use the
committed PNGs. `packaging/size-budgets.json` bounds the app package, native
libraries, Linux binary and release APKs. Android releases include a smaller
APK for each CPU architecture as well as the universal APK.
The native library exports only the NativeActivity and JNI loading entries;
registered JNI methods stay internal. This follows the Android NDK
[symbol visibility guidance](https://developer.android.com/ndk/guides/symbol-visibility)
and allows unused dependency functions to be removed when linking.
The smaller Practices inventory requires the `SunSalutationStoredFrame` host
capability. Older wrappers reject it before replacing their working package;
upgrading the wrapper enables the new inventory without changing saved data.

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

## Practice content and narration

`build/practice-content/*.zib` contains the separate practice data and language
packs. Practice → Manage practices opens one scrolling list of practices in the
order Practice shows them. Each row shows the practice's size (or how its
download is going) and one button: Install, Buy for a paid practice, Cancel
while it downloads, or Uninstall once it is on Practice. Its six-dot handle
drags it onto another practice to take that one's place in the order Practice
and every practice list follow (saved as `practice_order`). Start opens the
manager scrolled to its practice when the practice needs content. Downloads
continue inside the modal without changing the selected practice, and
unselected downloads are verified and saved without mounting their artwork.
Uninstall asks once and then deletes a downloaded copy and its narration while
preserving progress. Practices that ship with the app just leave Practice and
install again from the app's own copy without a download. Only the selected
practice and narration language are mounted in memory. Changing language reuses artwork and loads or
downloads the matching voice; switching back reuses its verified cache. Missing
narration is shown explicitly and never falls back to another spoken language.
Each practice/language has one verified cache slot, so an update replaces its
previous copy. Delete also clears cached languages retired from the catalog.
Manuals, tray shortcuts and app links use the same checked start path. Temporary
mini sessions can reuse public cached content; new downloads stay transient and
do not alter the full profile's saved content or practice records.

`apps/practice/content.json` owns the inventory and narration paths. The small
`assets/practices/catalog.json` is built into the signed Practices harness and
authenticates each resource pack's exact hash and size. Packs use the existing
`inbe.practices` artifact endpoint and publisher, are restricted to their own
practice/language prefix, and are never instantiated as programs. Publishing
places verified content before the harness advertises its hashes. New content
requires a new Practices release; the wrapper is unchanged for data that fits
the existing practice renderer and schema.

Tai Chi narration uses the existing speech/transcription pipeline:

```sh
python3 scripts/generate-lumi-guide-narration.py --practice taichi
python3 scripts/generate-lumi-guide-narration.py --practice taichi --check
```

Generation uses `OPENROUTER_API_KEY` from the operator's private environment,
checks recordings against translated text and saves a resumable receipt. Model,
voice, compression and equivalent spoken spellings are configured in
`design/tai-chi/narration.json`. Only changed or missing recordings are generated
again. `--locale CODE` limits generation or checks to one language. Incomplete or
stale languages are excluded from the catalog. Cues follow cue volume and
narration settings, pause with the practice, and stop on exit. Step-by-step
movement leaves time for the downloaded recording.
The course exporter also writes `design/tai-chi/narration-lines.json` from the
actual step cues and movement names. Menu labels are excluded. The coverage
check catches course changes that need a new narration inventory; packs check
the staged recording hashes against the verified receipt before publication.
The same configuration owns per-language verifier models, bounded token limits
and vocabulary hints. Verification keeps raw transcripts, accepts configured
equivalent spellings, and separately checks direction and numeric tokens.

The node needs the signed archive receiver and its catalog helper. Install them
independently of publishing content:

```sh
python3 scripts/install-package-receiver.py --ssh-target USER@NODE --store /absolute/node/package-store
```

The store must already exist. The installer restricts the launcher to that store
and refuses to replace an unrelated launcher or unmanaged receiver directory.
It does not publish packages, change SSH keys or restart the node.

## Updates and versions

Downloads use the Daochi release v2 endpoints on `https://api.waozi.xyz`:
`/api/v2/packages/{app_id}/latest` and
`/api/v2/packages/{app_id}/{sha256}.zib`. IDs are `inbe`, `inbe.habits`,
`inbe.practices`, `inbe.lists`, `inbe.diary` and `inbe.lumi`.

Automatic updates default on and check daily for the root and selected apps,
once after a start when the last check is an hour old, and ten minutes after
a sync reports a newer root package (`package_sequence` in sync replies).
A downloaded package proves itself by running ten seconds after a start; one
that three starts in a row never proved is set aside for the bundled package
and is not downloaded again until a different release arrives.
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

Hosts and packages agree on interfaces, not exact versions. Every package
declares the oldest host interface it needs (`host_api` in its ledger entry),
and the host runs packages from `oldest_host_api` to its own `host_api`.
Records between them match fields by name, so a field one side lacks keeps its
zero value and an unknown field is ignored. Update checks send the host's
interfaces and a stable device bucket; the node answers with the newest
release that fits, so apps that keep an older host still receive the packages
built for it. `package-release.py --rollout PERCENT --rollout-hours HOURS`
stages changed releases to that share of devices first; the node releases them
to everyone when the time runs out. `make package-compat-test` runs the
packages the node serves in the current build, and runs each new package that
declares an older interface in the last released app.

## Publishing configuration

The `Cell packages` GitHub Actions workflow builds and verifies package releases
on master. It signs and publishes automatically when all deployment values are
configured. Incomplete configuration produces downloadable build artifacts
without claiming publication. When only the signing configuration is present,
the archived artifacts include signed releases ready to import on the node.

1. Register the seven app IDs and an active Ed25519 publisher key in Daochi.
2. Add the public key to `apps/publishers.json`, scoped to the seven app IDs:
   `[{"key_id":"<registered ID>","public_key":"<64 lowercase hex digits>","app_ids":["inbe","inbe.habits","inbe.practices","inbe.lists","inbe.diary","inbe.lumi","inbe.leaderboard"]}]`.
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
the preparation retains the registry protocol version and existing scopes while
updating the app's client version.

The wrapper release workflow requires public pins covering all seven app IDs,
so each included cell has a configured publisher for its updates.
The public pin `inbe-2026-10` covers the root and all six apps. The private
signing key is kept in an ignored local backup and is excluded from every
package artifact. Optional production installation requires registering this
public key on the node and publishing the signed packages. Automatic server
publication additionally requires the GitHub signing and node deployment
configuration above; a checked build does not establish that configuration.

## Apps the node offers

Besides the bundled apps, More apps lists every app Waozi's node offers: each
registry entry `inbe.<name>` (`GET /api/v1/apps`, active, not a bundled ID)
whose latest signed release (`/api/v2/packages/inbe.<name>/latest`) this host
can run. The list is read while Apps is open, at most every six hours, and
kept for offline use. Its title is the root package's translated
`app_name_<name>` when there is one, otherwise the registry's display name,
so an app added to the node appears without an app update. The publisher pin
`inbe-2026-10` trusts its key for these apps through `"app_prefixes":
["inbe."]`.

Installing one assigns one of eight device-local slots (package indexes
after the bundled seven, setting `node_app_slot_<n>`) and downloads it through
the package manager with the same signature, hash, size, interface, trial
and cache rules as the bundled apps. Such an app is never part of the root
package or its dependencies. It runs in its own VM through one generic
interface (`src/cells/node_app_types.zi`, host interface 12): frame and
route messages, hosted Kryon widgets, `AppLocaleHost`, private records,
friends and records shared with friends. It may draw only its own
`assets/<name>/` resources and supplies its icon as
`assets/<name>/sidebar.shape`. A new app that needs nothing more needs no
host code and no APK.

Whether such an app is installed syncs as `app_used_<name>` (`0` or `1`, with
its time) in `private.inbe.v1.app-installs`, its private records as
`cell.<name>.<record>` in `private.inbe.v1.app.<name>`, and its pin by name in
`app_order`. Released versions skip these collections; a record this version
cannot read changes nothing and never stops the sync. Removing the app keeps
its records and its downloaded package.

Records shared with friends use the shared-list service (`/api/v1/lists`)
under ids `<name>-...`, which are never shaped like Lists' UUIDs: Lists shows
neither these records nor their invitations. Invitations, answers, saves
with revisions and removal follow the shared-list rules, so a friend accepts
or declines and a stale save is refused. Their content is not end-to-end
encrypted, like shared lists.

Chess (`apps/chess/`) is the first such app: the computer at three levels
(search depth 1, 3 and 5 with bounded positions, a few positions per frame
so the app keeps drawing) and games with friends, one shared record per game
with its moves in coordinates. `python3 scripts/package-release.py --node-app
chess --store ... --key ... --key-id ...` stages its release; with
`--ssh-target`, `--remote-store` and `--verify-origin` it publishes it. The
App packages workflow never publishes these apps. For a local preview or a
test, `INBE_NODE_APP_FILE=/absolute/path/chess.zib` offers that package as if
the node did; it passes the same interface, identity and resource checks.

## Account app choices

A new profile comes with Lumi, Habits and Practice installed and pinned, in
that order; Lists, Diary and Leaderboard are added from More apps. Existing
profiles keep their apps.

Sync v6 uses `private.inbe.v1.app-preferences`. Each of the six `app_used_*`
keys is a separate timestamped record, including explicit zero values for
removals. Independent changes merge without overwriting unrelated selections.
Pending local choices win equal timestamps; newer remote choices win.
Invalid keys, values and timestamps cannot alter preferences. Released
versions reject an unknown key in this collection and stop syncing, so a new
app's choice needs its own collection. A choice nobody made, such as a new
profile's apps, is stored at time 1 (`AppDefaultTime`) and never uploaded, so
a new device takes the account's apps instead of replacing them.

The pinned apps and their order are one record, `app_order`, in
`private.inbe.v1.app-order`: package names separated by commas, such as
`lumi,habits,practices`, at most 255 bytes. It is sent only when the owner
pins, moves or unpins an app. The newest order wins and a pending local order
wins a tie; versions that don't know the collection skip it, and a record this
version can't read changes nothing without stopping the sync. An arriving
order sets `app_order_received`, and the pins take it once. An app removed on
another device is unpinned here too. Versions, package paths, release
sequence floors and the automatic-update preference stay local.
All apps share the existing account, SQLite database and outbox. Diary entries
and photos use the owner-only encrypted cell collection on that same sync
account. Per-account files provide a local cache; they are not the only copy.

## Diary and standalone use

Diary owns date arithmetic, entry editing, JSON documents and calendar marks in
its own VM. Its bounded host capabilities provide only its private files and
clock. Entries use Harmony's existing version-1 per-day document format;
text edits preserve attached photo metadata. Failed or malformed reads never
overwrite the original document. Native storage uses an exclusive directory
lock and atomic writes.

For explicit migration, set `INBE_DIARY_IMPORT=/absolute/harmony/diary` when
opening Diary. The importer copies safe regular filenames and skips existing
Inbe files and symlinks. It preserves Harmony entries and photos and binds each legacy folder to the
first importing account with an owner marker. There is no automatic migration
from an unrelated live profile. Harmony's Diary catalog entry opens the Inbe
child inside the existing supervised parent window and passes its own data
root as `HARMONY_DATA_ROOT` for a safe import. Old saved native-renderer
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

A new app version is published only with a passing phone check of its
exact sources. `make phone-check APK=...` installs that APK on the development
Moto, runs the Wim Hof session for a minute while it reads SurfaceFlinger's
frame times, checks resuming from the background and records
`releases/phone-checks/VERSION.json`; the Release workflow refuses a new tag
without it or when app sources changed after it.

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
