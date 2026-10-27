# Inner Breeze app packages

Inner Breeze has a root package and six apps, including Lumi and Leaderboard.
The interface calls these Apps and presents them in one sidebar settings list.
All six apps ship with the app and can be added to the sidebar offline.
Leaderboard is installed for every profile but is not pinned by default.
Selections are stored per app and synced with the account. Lumi always ships with
Inner Breeze. Her selection controls her sidebar shortcut, while her harness and
tools remain available.
The root contains shared fonts, translations, themes and icons. Practices keeps
small previews, controls and shared cues. Heavy content is downloaded per
practice and works offline afterwards. Each feature can add private resources under
`assets/lumi/`, `assets/habits/`, `assets/practices/`, `assets/lists/`, `assets/diary/`
or `assets/leaderboard/`. The practices' media (pictures, course data and
recordings) is not kept in this repository: it is the
[practices](https://github.com/waozixyz/practices) package, pinned
in `ziran.lock`, linked at `build/packages/practices` and packaged under
`assets/practices/` (`scripts/practice_media.py`). Change it there, then run
`ziran update practices` and commit the lock. The narration, character
and Tai Chi generators write into a practices checkout mapped in
`ziran.local.toml` and refuse the locked package.
The app picker, Lists and Diary editor/calendar compose the
standard Kryon widgets inside their ZX bundles. Raylib, Android and canvas bind the
same typed render effects to their normal widgets. File dialogs, persistence,
account sync and native input stay in the wrapper. Habits draws all of its
screens in its package: the habit list and each habit's week and calendar
(`apps/habits/habit_list_view.zi`), a day's screen and the entry dialog
(`habit_day_view.zi`), the editor with its practice picker
(`habit_edit_view.zi`), the statistics (`habit_stats_view.zi`), the count
dialog and the editor's save/discard/delete confirmations (`habits_view.zi`
and `editor_dialogs.zi`). Practices draws its home in its package
(`apps/practice/practice_home_view.zi`): the host gives the chosen
practice's banner, title, tabs and what its card offers (Start, or Install,
Unlock or Cancel with the download's status and price, from
`src/practices/practice_offer.zi`), and does what the page asks: start,
open the manual or settings, press the offer, or choose another practice by
swipe, arrow key, arrow button or tab. The manuals of Wim Hof, Meditation,
Patterns, Astral Projection and Sun Salutation are the package's too
(`apps/practice/manual_view.zi`): the host gives the page, the guide's
colours and the settings the pages show, runs the Wim Hof breathing preview
and saves a speed changed on its page (`src/practices/practice_manual_host.zi`),
and each practice closes its manual or starts from what the page asks.
The Customize pages of Meditation, Breathing Patterns, Wim Hof, Astral
Projection, Sun Salutation and Tai Chi come from the package as well (`apps/practice/settings_view.zi`): the host gives the settings, the
music tracks with the chosen track's download, and the languages narration
is recorded in, and saves the one change the page asks for
(`src/practices/practice_settings_host.zi`). A finished practice's results
are drawn there too (`apps/practice/results_view.zi`): the host gives the
session's numbers and reads out each Wim Hof round, and keeps the mood
picked, discards the session or closes the results as asked. The running
Meditation, Patterns and Wim Hof layouts are in `meditation_view.zi`,
`patterns_view.zi` and `whm_view.zi`; Sun Salutation, Tai Chi, Astral Projection
and the 7-Minute Workout use `movement_view.zi`. Tai Chi's course chooser is
in `course_view.zi`. These pages return actions to the host, which retains
session clocks, saved settings, audio, lifecycle and routing. Detailed
movement figures stay on the render thread with their native mesh caches:
`figure_view.zi` submits one bounded figure request, accepted only by the
painter installed for the active page. The package owns each figure's bounds,
labels and surrounding controls; changing native pose/rendering capabilities
still needs a wrapper release. Practices 1.5.0 requires host interface 31.
The list's frame (`HabitsListFrame`) carries the page's bounds, the theme
and the state the host keeps: the open habit, scrolling, the name column's
width, a dragged row. The package reads each habit with
`ReadHabitsListRowHost` and each of its days with `ReadHabitsListDayHost`
(planned, done, counted, a span running), lays out and draws the table,
and returns what the person asked for: open a habit, tap a day, move a
habit or make it inactive, open its history, statistics or editor, the
shop or a new habit (host interface 30). The host applies each through the
same habit rules as before. A day's screen reads the day's entries
(`ReadHabitsDayEntryHost`), its linked sessions ordered by practice
(`ReadHabitsDaySessionHost`) and a breathing session's rounds
(`ReadHabitsDayRoundHost`); the package keeps the round being typed, with
the number pad or the keyboard, and asks the host to add, change or delete
an entry, end a span, delete a session or a round, save a round's seconds
or step the count. The entry dialog reads each answer with
`ReadHabitsAnswerHost` and gives back a changed one with
`WriteHabitsAnswerHost`, which keeps only values its question's type
allows; Done, Skip, Delete and Cancel go through the host's entry rules.
The editor reads the habit being edited (`ReadHabitsEditHost`), each of its
questions and each practice or app it may link, keeps what is typed and gives the
draft back; the host validates and saves it with the same habit rules as
before. The eight writing icons added in host interface 38 keep stable numbers
77–84; Habits packages offering these choices require that host so the editor
preserves them when saving. A link is one bit of the habit's `sync_activity`
(`src/habits/habit_links.zi`): a practice checks the day of a saved session,
and Diary checks a day with a real entry (`DiaryStoreSave` reports it, and
linking a habit brings its earlier entry days along). Another app links by
adding its bit and label there and reporting its days through
`habits_mark_link_day`. A new profile starts with Meditation alone; with
Habits installed, any other practice's first saved session, when no habit
links it, offers one on its results (host interface 37). The statistics read the figures the host counted over the habit's
last year (`ReadHabitsStatsHost`): streaks, weekdays, linked time, moods,
Wim Hof rounds and span times, then each answer chart, its points, each
hold and each change. Their answer charts are plot's band chart, which the
host draws for the package (`BandChartHostSupports` and `BandChartHostCall`
from `plot/band_chart_host`).
The habit shop is Habits' own page as well (`apps/habits/shop_view.zi`): the
package draws the coins, the rewards and the form and asks the wrapper to
save, delete or buy a reward; the wrapper checks each request against what
is stored, so a reward is bought only at its stored price with enough coins.

## Shared app interface

Inner Breeze is a harness for awareness and personal growth. Diary is the
first bundled app using Kryon's shared `app_context` interface: its editor,
calendar, undo/redo and document rules live in `apps/diary/`. The wrapper
provides account-scoped documents, sync, input, locales and optional photo
and spelling services. Older compatible Diary packages keep their existing
host interface.

The same `diary.zx` can run in Werkzeug with `werk --bundle diary.zx` or
in Kryon's desktop player with `kryon run diary.zx`, without `inbe.zx`.
The desktop providers keep private local documents and support photo picking;
online spelling is available only where the harness supplies it. Documents
outside Inner Breeze do not automatically join its account sync. Other
bundled apps still use their existing interface while they migrate.

Downloaded apps can also use the shared contract. Werkzeug's Calculator is
the first reverse check; offer its local bundle through the existing
`INBE_NODE_APP_FILE` mechanism. Capability and identity validation still run.

`tests/portable_apps_ui_test.py` checks the same Diary bundle in Werkzeug and
the standalone player, including editing, photo bytes and rendering, saving
on close and restart, on a private display with disposable profiles.

## Lumi

New profiles follow the device language, or English when Inner Breeze has no
translation for it, and ask once whether to download voice guidance, then open
Apps with Lumi, Habits and Practice pinned. Existing app choices and todo data are retained. Settings lists
Lumi in the same compact list as every other app. Removing her shortcut
keeps her package, conversation and app abilities; she cannot be uninstalled.
Her firefly image belongs to `assets/lumi/mascot.png` in her package and appears
beside her replies. The conversation has compact connection controls; navigation uses a
monochrome outlined firefly, matching the other navigation glyphs. The sidebar
uses `assets/lumi/sidebar.shape` with the standard button size and foreground;
navigation bars use the matching transparent `assets/lumi/sidebar.png`.
The chat avatar is mirrored toward the conversation. Enter sends a message;
Shift+Enter inserts a new line and the composer grows with the draft.

`apps/lumi/lumi_view.zi` composes the chat and command suggestions with hosted
Kryon widgets. `apps/lumi/engine.zi` interprets supported commands offline;
its typed `LumiAction` output is validated by the host before an action runs.
Offline commands need no AI model or model download. Lumi starts offline.
After agreement to the in-app terms, online AI can answer other requests
through Inner Breeze's service or the person's own compatible provider.
`src/apps/lumi_connection.zi` owns connection choice and agreement;
`src/apps/lumi_online.zi` owns requests. Switching offline stops AI requests.
The agreement explains the conversation and app context sent to each route.
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
The `LumiTools` context reports the installed and enabled apps to the engine;
help, suggestions and actions all follow those capabilities. Todo tools require
Lists, habit tools require Habits, and practice starts require Practices.
The wrapper validates IDs and live state again before using the existing
user-scoped storage, sync outbox and practice registry. A practice starts after
the chat app finishes its call, within the same application frame.

The conversation is saved as account-scoped records, with older messages loaded
on demand. It survives restart, follows the active account, and can sync as
encrypted records when an account is connected. Online AI agreement is separate
from account sync. The wrapper provides input, persistence and bounded
app effects; no database pointers or arbitrary code cross the app boundary.

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

A counting habit can have a daily target of 0 to track something the person
wants to avoid. A recorded count of 0 completes that day; occurrences miss the
goal, and unrecorded or cleared days stay incomplete. Closing the count dialog
with 0 records that zero. Stored counts and linked sessions remain visible.

Custom coins replace difficulty rewards with a signed amount for every
occurrence, regardless of whether the target is reached. For example, -2 coins
with 3 occurrences deducts 6; 0 gives no reward or penalty. A recorded zero
never creates an occurrence. Edits and sync recalculate each day's amount
without charging twice. Rate changes apply from their local day onward, keeping
earlier days' rates, and deleted habits retain their earned coins or penalties.

Each habit has a difficulty, medium, hard or very hard. A done day earns 1, 2
or 3 coins, counted the way the habit list counts a day as done (marked,
counted to its target, or covered by linked practice sessions). A changed
difficulty applies from the day it changed, so earlier days keep what they
earned, and each habit earns from its `coins_from` day: the day it was created,
or for a habit from before coins, the day the upgrade first opened. Sync keeps
the earliest such day of every device. The coins and the shop's icon end the
line of today's count. The shop lists the rewards the person sets, each with a price
of 1 to 9999 coins, and Buy asks before it spends the coins. Rewards
(`habit_rewards`) and coin records (`habit_coins`: a reward's price as bought,
or the coins a deleted habit's days had earned, kept under `kept:<habit id>`)
sync as `private.inbe.v1.habit-rewards` and `private.inbe.v1.habit-coins` with
deletions. The balance is what the days earned plus the kept coins less what
was bought (`src/storage/storage_habit_wallet.zi`). An older app keeps a
habit's difficulty and skips the shop.

Inner Breeze has no donations; Dew is how people pay. Donation cards that older
versions saved stay in the synced history but are no longer shown, and Lumi
packages before 1.5.0 still import the retired donation calls, which return
nothing. Old text-only chat history remains readable. Cards persist in the same
account-scoped local conversation and render with standard Kryon Text, Box and
Button widgets.

The app publishes its MCP tool schemas in `assets/mcp/tools.json`, including
`get_settings`, `set_theme`, `set_theme_mode`, `set_setting`, `open_view` and
`practice`. Harmony discovers and calls them through `app_mcp`; Lumi is scoped
to Inner Breeze. All its apps share the single Lumi chat. Harmony's per-app
Enable chat / Disable chat control preserves the agent and saved conversation.

## Build and installation

`make apps` produces:

- `build/inbe.zx`, containing every app under `cells/`.
- Independent `build/apps/{lumi,habits,practices,lists,diary,leaderboard}.zx` files.
- `build/inbe-full.zx`, a local development and test bundle containing all six.

Native and browser builds embed the base root. Android stores `inbe.zx`
once in APK assets and opens its bytes through the NDK asset manager. Each
CPU library contains only the native host and small bootstrap assets, so a
universal APK shares the artwork across all four architectures. Direct Gradle
builds run `make apps` and stage the current package before merging assets.
All six app packages are included in that root and can be opened offline;
Lumi, Habits and Practice are pinned by default. Downloaded updates and other
apps are stored in the private `packages/` directory
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
committed PNGs. `packaging/size-budgets.json` bounds the app package,
Linux binary and release APKs. Android releases include a smaller
APK for each CPU architecture as well as the universal APK.
The native library exports only the NativeActivity and JNI loading entries;
registered JNI methods stay internal. This follows the Android NDK
[symbol visibility guidance](https://developer.android.com/ndk/guides/symbol-visibility)
and allows unused dependency functions to be removed when linking.
The smaller Practices inventory requires the `SunSalutationStoredFrame` host
capability. Older wrappers reject it before replacing their working package;
upgrading the wrapper enables the new inventory without changing saved data.

The app selection screen follows language selection. Settings → Apps & sidebar
lists installed and available apps alongside the sidebar shortcuts. Drag a
shortcut's handle to reorder it, or use its trash icon to remove that shortcut.
A app's trash icon removes it from the active selection while preserving its
saved data and bundled package; the plus button adds it back immediately.
Settings is fixed last and is absent
from the editable list. Existing
profiles retain their selection and saved sidebar order.
Each app appears once, with active shortcuts in sidebar order and hidden apps
after them. The list shows icons, names and controls without status paragraphs.

## Practice content and narration

`build/practice-content/*.zx` contains the separate practice data and language
packs. Practice → Manage practices has four tabs and opens on the first,
Installed, which lists every practice on this device. Meditation (breathing
practices included), Yoga and Martial arts list each kind of practice whether
it is installed or not. A practice's kind is `kind` in its
`PracticeDefinition`; one without a kind is listed only under Installed. Each
tab lists its practices in the order Practice shows them. Each row shows the
practice's size (or how its
download is going) and one button: Install, Buy for a paid practice, Cancel
while it downloads, or Uninstall once it is on Practice. Its six-dot handle
drags it onto another practice to take that one's place in the order Practice
and every practice list follow (saved as `practice_order`), also within a
tab. Start opens the manager scrolled to its practice, in a tab that lists it,
when the practice needs content. Downloads
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
`/api/v2/packages/{app_id}/{sha256}.zx`. IDs are `inbe`, `inbe.habits`,
`inbe.practices`, `inbe.lists`, `inbe.diary` and `inbe.lumi`.

Automatic updates default on and check daily for the root and selected apps,
once after a start when the last check is an hour old, and ten minutes after
a sync reports a newer root package (`package_sequence` in sync replies).
A downloaded package proves itself by running ten seconds after a start; one
that three starts in a row never proved is set aside for the bundled package
and is not downloaded again until a different release arrives.
The app picker includes an automatic-update switch and a manual check button.
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
newer independently cached apps remain selected after restart.

On Linux and Android, payload jobs own their paths, release descriptors and
bytes. Reading, hashing and writing large files runs off the frame thread.
Built-in app programs are parsed in the background, then one isolated identity
handshake runs per frame with effects disabled. A verified feature candidate is
retained for activation, so installing it does not parse it again or reopen
unrelated app VMs. Cancellation retires jobs until their workers and parsers
finish; it never joins an unfinished worker in a frame. Web and Windows retain
the synchronous fallback, as does validation of additional node-app trees.

Running additional apps review only changes to their own package generation.
An unrelated update does not reread their signed release files. A replacement
that cannot save yet stays pending and retries at a safe boundary without
repeating that metadata read or signature check; the working app stays alive.

Additional app icons also load through one owned worker on Linux and Android.
Drawing requests an icon and uses the catalog outline until its copied shape
is ready. Cache reads, payload hashing, program verification and cache writes
run on that worker without invoking an app or the host's shared asset index.
The small persistent icon cache is keyed by the signed payload digest. A
completed job is published only while its slot, account, package revision and
temporary-session state still match; obsolete jobs finish without blocking
navigation or starting more workers alongside them.

Nested app images capture their verified asset view while the guest is drawing.
Back can remove its tree node before painting finishes; the retired runtime
keeps those bytes alive until the frame is collected. Image lookup never follows
the removed node. Repeated images share a frame mapping keyed by package digest
and packed path, so tiles reuse it and different releases retain separate bytes.

Practice downloads, cold loads and cache reviews use the same owned content
worker. Recently used verified packs stay in memory within a soft 64 MiB
budget; the selected practice and its voices are never evicted for that limit.
Only selected content is exposed through the asset provider. Removing content
also retires its pending load, so a late result cannot mount it again.

`apps/versions.json` records separate numeric versions and increasing sequences
for every package. Every app release versions all bundled packages: bundles
share host code and Kryon, so any release changes them, and the node refuses
a changed package under an old version. `./update_version.sh` does this once
per release, recorded as each package's `release`: a package whose changelog
already has a newer entry takes it, the others get a "Maintenance release for
Inner Breeze X.Y.Z." entry, and the root package's entry lists the versions it
brings. To write a package's own notes, add a numeric entry to its
`apps/<source>/CHANGELOG.md` before running `./update_version.sh`, or run
`./update_version.sh --app NAME` for a release of that package alone.
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
A host loads only programs in its own Ziran program format, so a toolchain whose
format changed is a new interface too: `oldest_host_api` and every package's
`host_api` rise above the last released host. Host 12 is the first with
format 58; released apps up to 2.1.34 (host 11) cannot load packages built
since, and are not offered them.
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

The `App packages` GitHub Actions workflow builds and verifies package releases
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
so each included app has a configured publisher for its updates.
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
interface (`apps/node_types` from the Apps package, host interface 12, and 13 for the
media library, which Diary also reads from 14): frame and
route messages, hosted Kryon widgets, `AppLocaleHost`, private records,
friends and records shared with friends. It may draw only its own
`assets/<name>/` resources and supplies its icon as
`assets/<name>/sidebar.shape`. A new app that needs nothing more needs no
host code and no APK.

Whether such an app is installed syncs as `app_used_<name>` (`0` or `1`, with
its time) in `private.inbe.v1.app-installs`, its private records as
`app.<name>.<record>` in `private.inbe.v1.app.<name>`, and its pin by name in
`app_order`. Released versions skip these collections; a record this version
cannot read changes nothing and never stops the sync. Removing the app keeps
its records and its downloaded package.

Host interface 31 keeps records whose names start with `local.` on the
device, for both legacy app records and identity-scoped app trees. They are
never queued for account sync. A package using this storage boundary must
require host interface 31 or newer; older hosts may sync those names.

Records shared with friends use the shared-list service (`/api/v1/lists`)
under ids `<name>-...`, which are never shaped like Lists' UUIDs: Lists shows
neither these records nor their invitations. Invitations, answers, saves
with revisions and removal follow the shared-list rules, so a friend accepts
or declines and a stale save is refused. Their content is not end-to-end
encrypted, like shared lists.

Chess (`inbe.chess`) is owned by Arcade, including its source, assets,
translations, tests and independent release ledger. Inbe consumes its signed
node package and preserves existing installations, records and friend games.
It no longer builds or versions Chess. The game offers the computer at three levels
(search depth 1, 3 and 5 with bounded positions, a few positions per frame
so the app keeps drawing) and games with friends, one shared record per game
with its moves in coordinates. From the Arcade repository,
`python3 scripts/package-release.py --store ... --key ... --key-id ...`
stages its release through Inbe's existing signed publisher; with
`--ssh-target`, `--remote-store` and `--verify-origin` it publishes it. The
App packages workflow never publishes these apps. For a local preview or a
test, `INBE_NODE_APP_FILE=/absolute/path/chess.zx` offers that package as if
the node did; it passes the same interface, identity and resource checks.
On Android debug builds, a single `<name>.zx` in the app's external files
folder is offered only when the launch intent includes `--ez local_node_app true`.
Ordinary launches ignore these files and keep using signed node packages.

## Photos and the account's media library

Photos (`apps/photos/`, `inbe.photos`, host interface 13) is the second app
the node offers: a newest-first grid of the library's photos under the day
each was taken, a viewer with previous, next and Move to Trash, and Trash,
where a photo can be restored. Install it from the normal app catalog.

Diary and Photos use the same host import and account storage, even when
Photos is not installed. New opaque still images larger than 256 KiB are
stored as upright JPEG copies at quality 88 and at most 2048 pixels on the
longest edge, only when this saves more than 10%. Source files stay untouched;
capture dates remain in the shared record. Small, transparent and animated
images retain their bytes, as do photos already in the library.

The library belongs to the account, not to Photos, so its photos stay when
Photos is removed. Each photo is a record of the account's entity data
(Daochi `docs/entity-data.md`), which every app of the account shares: Diary
embeds the same photo, and other apps such as the standalone Photos read and
write the same record. Everything there is private. The host keeps it
(`src/apps/media_store.zi`, `entity_photos.zi`): each photo is stored once
by the SHA-256 of its bytes under `media/<account>/<sha256>`, with an
upright JPEG preview of at most 512 pixels (`<sha256>.preview`) made on
import by Kryon's `ImagePreview` (`image_preview.zi`: the host decodes,
portable Ziran scales by area averages, turns by the Exif orientation and
writes a baseline JPEG). The capture day and time come from the file's Exif
original date (`media_metadata.zi`), otherwise from the day it was added.
The record is `entity.photos.<sha256>` on the device and record `<sha256>`
of `private.entity.v1.photos` in the account's signed v6 sync, sealed in
Daochi's record profile (`storage/entity_record_crypto.zi`: XChaCha20-Poly1305
with the account's photos record key, key ID `entity-v1`, the same bytes as
libsodium's):

```json
{"hash","size","type":"image/jpeg","taken_at","width","height",
 "blobs":[{"address","size"}],"preview":{"hash","size","type","blobs"},
 "added_at","name","trashed":false,"day","taken","capture":true}
```

`blobs` names the photo's sealed chunks once a node has them all, and the
preview names its own. Fields this version does not know are kept when it
writes a record back, and an entity record of another kind, or one that does
not open, changes nothing and never stops a sync. A record that arrives
replaces this device's copy, keeping fields only this device has, unless a
change here has not gone out yet; that change then goes out over it.

Released versions kept the library in `private.inbe.v1.media`, which they
read through 2027-10-24, and each photo's bytes as one old sealed copy at
`/api/v1/blobs/inbe/` (`diary_records.zi`):

| Key | Value |
|---|---|
| `cell.media.<sha256>` | `{"hash","size","type","name","day","taken","added","trashed"[,"blob","key"][,"photo"]}` |
| `cell.media.preview.<sha256>` | `{"hash","size","type"[,"blob","key"][,"photo"]}` |

Those photos and Diary photos older versions attached as Diary files move to
the entity data (`media_diary_photos.zi`). A library photo moves once its
bytes are on the device, its old copy downloading for it, and its entity
record takes its name, day, Trash and the time it was added. Each Diary file
a day's entry still includes, by a `photos` row or a `diary:` embed, moves by
its hash through the photo button's path (`MediaAddBytes`), named as the
entry names it and, without an Exif date, under the entry's day (`taken` is
then the day alone); its library file is a hard link to the Diary file where
the platform allows. Entries are not rewritten, and Diary draws a moved photo
by its hash. A Diary file no entry includes stays as it is. Once the sync
node confirmed a moved photo's record and chunks and the media pass
downloaded them back whole (`verified_contents`), its old records name it,
`"photo": "<sha256>"`, keeping every other field; then its Diary file
leaves the device, its hex chunks from before copies shrink to one byte
each, and the media pass deletes its old copies from every node
(`old_copies_deleted`). Any failure keeps the old copy for a later pass, and
a delegate (Telegram) device moves nothing. A check is due at start, for
another account, after each good sync and when a photo's file arrives or
comes back whole; it reads the day entries only when what has not moved or
the entries changed, and moves four photos per frame while the person is
idle and no practice shows.

The legacy apply branch still accepts any `cell.media.*` key with a JSON
value, so released versions' records keep syncing; `media` is a reserved app
name, so these keys are never taken for an app's records.

Apps reach the library only through the media calls, which the host grants
to Photos alone among the apps the node offers (`NodeAppMediaGranted`); a
package of another name that imports them cannot start. Diary's view may
read a day of the library with `MediaQueryHost` and `MediaItemHost`. `MediaQueryHost(day, trashed)` lists one capture
day or all, newest first, and `MediaItemHost(index)` reads an item of that
list. `MediaAssetHost(hash, original)` answers the asset path to draw,
`media/preview/<sha256>.jpg` or `media/<sha256>.<fmt>`, or `""` while neither
is on the device; asking for an original asks for its download and shows the
preview until it arrives. `MediaPickHost()` opens the platform picker after
the frame (the desktop file dialog, or Android's photo picker, kind 6, which
keeps the picked file's own bytes), `MediaStatusHost()` says what the last
pick did, the library's revision and this device's date, and
`MediaUpdateHost(hash, field, value)` changes `trashed` or `name`. The hosted
asset policy draws `media/` paths of the current account's library only.

Photo bytes travel as the entity data's sealed chunks: chunks of at most
8 MiB, each sealed with a key made from the account key, the photo's hash and
the chunk's index (DaochiClient's `entity.zi`), ChaCha20-Poly1305 with a zero
nonce, `PUT /api/v1/blobs/entity/<sha256 of the chunk>`, signed with Inbe's
own app ID and device key. The same picture is therefore the same chunks for
every app of the account, uploaded once per node. The media pass
(`diary_blobs.zi`) moves photos, previews, the old copies photos still need
in order to move, and deletes of moved photos' old copies after each good
sync:

- Copies go to every node in the account's node list whose photo upload is
  on (Profile › Data), not only the sync node. `diary_blobs(node, blob)`
  remembers what each node holds; each pass starts with the node where the
  previous one stopped, within its limit of 8 files and 32 MiB. A 413 marks
  only that node full; a node that fails only loses its turn.
- Downloads ask the sync node first, then the other nodes in list order; a
  404 moves on to the next node. Previews download everywhere, originals only
  where they are wanted (`media_wanted`, the last 32 photos opened here) or
  when a photo has no preview. Deletes go first, so a node has room for what
  moves; a node that answers 405 keeps its old copies for a later pass.
- Blob requests never use the sync's session. Each node has its own media
  session, saved on this device under `SyncNodeCursorKey(address,
  "media_auth_*")`, opened with a login and a device registration on that
  node (`media_node_session.zi`; blocking on the desktop's sync worker, frame
  by frame on Android and the web) and opened again once after a 401.
  Removing a node forgets its session and its `diary_blobs` rows. Delegate
  (Telegram) accounts never move copies.

Photos is available in the normal app catalog.
The App packages workflow builds every app the node offers and
publishes each one whose ledger names a newer release than the node serves
(`package-release.py --node-apps`). An app the node does not list yet is
reported and skipped: registering it takes the node operator's key. With each
publication the node's importer writes `history-v2.json`, the app's newest
three releases, which the node offers for going back to an earlier version;
`--write-history` rewrites every app's history. `make
media-store-test media-metadata-test photos-app-test` check the library, the
Exif reader and the app through the real host; `make entity-photos-test`
upgrades a 2.1.43 profile (`tests/fixtures/photos-2.1.43.sql`) against nodes
answered from memory, with interrupted passes, a full node, an unreachable
node, a node that cannot delete and a damaged chunk; `make sync-server-test`
(`DAOCHI_BIN=...`, Daochi 17bfd12 or later) adds a photo on one device and
opens it on another through two real Daochi nodes and moves an old copy
there; and `make photos-ui-test` adds a camera photo through the desktop
picker on a private Xvfb display.

## Account app choices

A new profile comes with every app Inner Breeze ships installed: Lumi, Habits
and Practice pinned, in that order, and Lists, Diary and Leaderboard ready
under them. Existing profiles keep their apps; a profile whose Lists, Diary or
Leaderboard choice is still the untouched default gets that app installed
(`storage_migrate_preinstalled_apps`), while a removal stays removed. Each
release builds these apps from the current source into the app, so it ships
their newest versions; a package the node publishes later reaches devices as
an update, and an older one never replaces the shipped copy.

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
and photos use the owner-only encrypted app collection on that same sync
account. Per-account files provide a local cache; they are not the only copy.

## Diary and standalone use

Diary owns date arithmetic, entry editing, JSON documents and calendar marks in
its own VM. Its bounded host capabilities provide only its private files and
clock. Entries use Harmony's existing version-1 per-day document format.
Failed or malformed reads never overwrite the original document. Native
storage uses an exclusive directory lock and atomic writes.

An entry's text is Markdown and the only source of truth
(`apps/diary/diary_markdown.zi`). A photo is a CommonMark image anywhere in
a line, `![NAME](photos/YYYY/MM/DD/<sha256>.<type>)`, with an optional title
and an optional `<angle>` destination: its place in the account's media
library, under the day Photos groups it (the Exif capture day, or the day it
was added), so Diary and Photos keep one library. The photo button adds the
picked file to the library (`MediaImportFile`, once per hash, with its
preview, synced as Photos' items are) and the package puts the embed on a
line of its own at the caret. `![NAME](diary:FILE)` names a Diary file an
older version attached; other images stay text. Loading a day appends the document's `photos` rows that no embed
names yet as such lines, in memory only, so viewing writes nothing; saving
writes `photos` again from the `diary:` embeds, so older versions keep
showing those photos. Deleting an embed's line takes the photo out of the
entry.

The editor previews the Markdown through Kryon's `TextArea`: away from the
caret's line, markers and each photo's Markdown are hidden, emphasis is bold
or slanted, headings are larger (`TextAreaLine`), links and list and quote
marks take the theme's colors, and a line's photos follow it in order
(`TextAreaBlock`); on a line of photos alone, the first takes the line's
place. On the caret's line the source shows with the photos under it, so
text typed before or after a photo keeps it. Under the entry, the
day's photos scroll sideways: the library's photos of that day, then the
entry's other photos; a tap embeds one at the caret. The Diary view reaches
the library through `MediaQueryHost` and `MediaItemHost`, and draws an
embed through `DiaryPhotoHost(destination)`, which answers the library's
preview (`media/preview/<sha256>.<type>`) or the Diary file
(`diary/photos/<file>.<type>`), or `""` while the photo is not on this device
(host interface 14). A Diary file the library keeps too draws as the
library's photo, and the day's photos list one picture once. Spelling
checks send each image as one U+FFFC mark and put it back at its mark,
refusing a correction that lost or added marks (`diary_spelling_mask.zi`).

For explicit migration, set `INBE_DIARY_IMPORT=/absolute/harmony/diary` when
opening Diary. The importer copies safe regular filenames and skips existing
Inbe files and symlinks. It preserves Harmony entries and photos and binds each legacy folder to the
first importing account with an owner marker. There is no automatic migration
from an unrelated live profile. Harmony's Diary catalog entry opens the Inbe
child inside the existing supervised parent window and passes its own data
root as `HARMONY_DATA_ROOT` for a safe import. Old saved native-renderer
metadata does not restore a second Diary engine. Native and Android use
their ordinary photo pickers; Android's keeps the picked file's own bytes,
as for Photos.

The desktop wrapper accepts `--bundle /path/to/inbe.zx`, or an individual
Lumi, Habits, Practices, Lists or Diary ZX. A feature bundle opens its own app using
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
standalone UI applications in the generic Kryon player. The app picker, Lists
and Diary compose standard widgets through the same raylib and canvas host.
Their layouts and all packaged graphics, fonts, styles and translations can
update without a wrapper release. Habits draws its count dialog the same
way, through `ReadHabitsUiHost`, `WriteHabitsUiHost` and `HabitsLocaleHost`
(host interface 14, so Habits 1.1.0 needs Inner Breeze 2.1.35): the host
supplies the day's count, target, linked sessions and the theme's text
colour, and applies the step, the opened day or the closing the dialog asks
for. Every other Habits screen follows since Habits 1.3.0 (host interface
30), and Practice's home since Practices 1.4.0. Practices 1.5.0 moves the
remaining session layouts, manuals, Customize pages and Tai Chi course
chooser into its bundle (host interface 31). Session effects and the detailed
figure painters remain native; changes to those host capabilities require a
wrapper release.

## Device launcher entries

Each installed app card has a compact **⋮** menu with **Pin** or **Unpin** for
Inbe's navigation and **Uninstall**. The Apps search field shows **×** at its
right only while it contains text; clearing it restores the full app list.

The menu also offers **Install to launcher** on Android 8 and later when the
launcher supports pinned shortcuts, on Windows, and in native Linux and
AppImage builds. Android asks for confirmation on the home screen. Windows
adds a per-user Start menu shortcut; Linux adds a per-user application entry.
Each uses the app's name and mark and opens it without Inbe's surrounding
navigation. Repeating the action updates the same entry.

These entries use the existing Inbe executable, packages, account and data;
Inbe must stay installed. They do not install another APK or a separate copy
of the data. Downloaded apps are addressed by their package name, so changing
their device-local slot does not change a saved shortcut. An app removed from
the account must be added again in Inbe before its shortcut can open it.

Desktop entries invoke `--app NAME`; the older `--feature` option remains
available. Native Linux entries respect `XDG_DATA_HOME` and preserve an
explicit `APP_DATA_ROOT`. The action is hidden on the web, in Snap and in
Flatpak, where installing launchers needs a separate portal integration.
`make launcher-entry-test` checks identifier and desktop escaping rules;
`make launcher-shortcut-ui-test` checks pinning, icons, repeated pinning,
the desktop's actual entry parser, profile selection, bundled app launches and
a node app after its slot changes, on a private display. Android shortcut behavior is covered by
`make android-text-selection-test`. The explicit `android-launcher-device-test`
uses only the development Moto's debug app, saves its existing profile before
preparing test data, and restores it with a byte-for-byte check afterward.

## Verification

A new app version is published only with a passing phone check of its exact
app content. The check installs the APK on the development Moto, runs the
Wim Hof session for a minute while it reads SurfaceFlinger's frame times,
checks resuming from the background and records
`releases/phone-checks/VERSION.json` with `app_tree`, a hash of every app
path (`APP_PATHS` in `scripts/phone-check.py`: sources, build rules, assets,
locales, version files and the design files packages are built from, minus
the `TOOLING` that only checks or publishes). The Release workflow refuses a
new tag without it or when the pushed app content differs. Tests, docs and
tooling may change after the check; any app change needs a new one.

A release names one fixed commit while peers keep working on master:

1. Add the numeric `CHANGELOG.md` entry, run `./update_version.sh`, and commit
   the intended source. Do not freeze the repository, dependency lock or
   another session's work.
2. `RELEASE_READY_REVISION=COMMIT make release-ready` runs the local CI suites
   in the Ubuntu 24.04 container with the candidate's locked packages:
   Secret Scan, package URLs, file sizes, all tests, package
   compatibility, Chrome and muted Firefox smoke tests, and the pinned real
   Daochi sync server. Platform release builds remain separate. The existing
   repository overlay materializes every candidate file and recreates source
   directories, so later edits, new files and commits cannot enter the run.
   Outputs stay in `build/release-ready/`.
3. Build the Moto APK in the same fixed-source overlay and save its content
   identity and SHA-256 build receipt. Use `ANDROID_VERIFY_INSTANCE=1` for
   the separate `xyz.waozi.inbe.verification` debug instance when the owner's
   regular app is running; it has its own process and private data. This
   option is rejected for production packages. Run
   `make release REVISION=COMMIT APK=PATH BUILD_RECEIPT=PATH`.
   The exact APK must pass the minute-long practice and resume check;
   physical-phone images use Harmony's owner-only review. The command checks
   both the local gate stamp and APK provenance against the fixed candidate.
4. The command creates "Release Inner Breeze X.Y.Z" from the tested source
   plus its receipt. If master advanced, a merge keeps the release in its
   history while preserving every newer committed source file, staged edit
   and unfinished file. No existing history is rewritten.
5. Push the approved history and run Release for its exact release commit
   using the workflow's `revision` input when master has moved on. Every
   platform and reusable F-Droid build checks out that same candidate.
   Subsequent master commits cannot cancel its release. Only the workflow
   creates the release tag after all required gates pass.

When an earlier Release run already passed every test, platform and
F-Droid reproducibility job for the source, supply its run ID as `reuse_run`.
The identical source must also pass CI, including browser add-on smoke tests.
The workflow admits reuse only when the release commit adds that version's
valid phone-check receipt and changes no other file. It downloads the original
immutable build artifacts for publication and store delivery. A changed source,
unfinished gate or missing result requires the normal complete build.

Harmony Projects shows this wrapper release, every app version and its Moto
screenshots. Harmony's `make inbe-release-verify` checks the latest published
APK on the development Moto and writes private evidence under
`backup/releases/`. A newer version starts pending until its exact APK passes
launch and resume checks. Debug candidates stay labeled as candidates.

Translation catalogs follow the current package asset provider. An early
lookup before the root mounts retries when resources become available, and
changing packages rebuilds the catalogs before reusing any borrowed text.
`make locale-zi-test` checks every key in all 12 languages and exercises delayed
resource availability, provider replacement and fallback restoration.

`make apps-test` exercises the root and all five actual feature bundles,
typed capability rejection, shared SQLite/identity, a 1.8.9 upgrade fixture,
practice timing, all selection masks and Diary Unicode/calendar/document edits,
older photo lists as embeds and inserted library photos.
`make diary-markdown-test` checks Diary's embeds, library places, inserted
photos, the editor preview and spelling masking natively and in the VM.
`make package-release-test` checks Ed25519 metadata, payloads, signed nested
content, rollback rejection, cache repair, manual checking with auto-update off
and cancellation that preserves manual requests. Account preference tests
exercise real sync SQL and account isolation. The Wasm download test verifies
bounded browser streaming, filesystem writes, cancellation and failures.
`make apps-diary-test` verifies the standalone Diary window, delayed saves,
clock insertion, calendar and restart. GUI onboarding and navigation tests run only on private Xvfb displays with
application-owned windows and disposable profiles.
`make package-workflow-test` executes the publisher configuration branches and
checks the workflow's signing and upload commands, including private file
permissions and keeping credentials out of its output.
