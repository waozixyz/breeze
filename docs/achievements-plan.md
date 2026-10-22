# Inner Breeze achievements implementation plan

Date: 18 October 2026. Status: implementation in progress; final application
integration and device verification remain pending.

The 160 catalogs, app earning adapters, shared Self view and alert control are
implemented. Facts and permanent awards use validated account-owned settings
records in their own encrypted collection, rather than a second database.
Presentation receipts remain local. Native SQLite checks cover earning,
source deletion and purge, sync merging, archive restore and profile replacement.
Successful focused checks do not establish that the final application is released.

Achievements live in the shared **Self** profile app. Each installed Inner
Breeze app supplies its own achievements, and Practices supplies an additional
set for each installed practice. Self shows both earned and unearned
achievements; unearned achievements have gray artwork and visible requirements
and progress. A single **Achievement alerts** switch lets the person enable or
disable alerts without changing whether achievements are earned.

The initial catalog below defines **160 achievements**: Self 10, Practices 60
(10 general and 10 for each of five practices), Diary 20, Habits 20, Lists 15,
Lumi 10, Photos 10, Radio 10, and Leaderboard 5. This is the full catalog, not
the number every installation must display. Only the installed apps and practice
content contribute to the visible catalog and its earned/available counts.

## 1. Product behavior

### Where achievements appear

- Add **Achievements** inside Self, alongside the existing profile content.
  Opening it shows app headings, each app's earned/available count, and its
  achievements. Practices has nested headings for its general achievements
  and each installed practice.
- Every row shows a distinct, meaningful icon, name, plain-language earning condition,
  and progress such as `7 / 25 sessions`. Earned rows also show the earned
  date. A row can open its full description when space is limited.
- Unearned icons are gray. Keep the text readable, and show explicit
  **Not earned** or **Earned** status so color is never the only distinction.
  Gray rows remain focusable and readable; they are not disabled controls.
- Use the existing profile typography, theme, standard widgets, and responsive
  layout. Keep one scrolling collection with clear app headings. Do not add
  search, filters, new navigation destinations outside Self, or separate
  achievement screens in every app for this work.
- Show progress for each individual achievement, including first-step awards.
  Use counts for simple thresholds and explanatory progress for compound rules.
  For example, a return achievement says `Return after a 14-day gap`; do not
  display a countdown encouraging someone to stop practicing.

### Which apps and practices are visible

- Use the same successful installation state as Apps. Package bytes bundled
  with the host, sidebar pins, available downloads, and installation requests
  are not by themselves proof that the person installed an optional app.
- Keep an installed app's achievements visible offline and when its sidebar
  shortcut is removed. Lumi and Leaderboard follow their existing installation
  rules; removing a shortcut does not uninstall them.
- An app appears only after installation commits successfully. An update in
  progress or a failed update keeps its last working installed catalog.
- Uninstalling an app immediately hides its heading, achievements and visible
  totals. Preserve its private progress and earned records so reinstalling
  restores them silently. Do not add an archive screen.
- Apply the same rule to downloaded practice content: show practice-specific
  sets only while their content is installed and available through Practices.
  Merely selecting a practice or having preview artwork does not install it.
  General Practices achievements remain visible while Practices is installed.
- A compound achievement that needs another app is visible only when all its
  declared prerequisites are installed. In this catalog that affects Lumi's
  practice and diary awards, and Leaderboard's two-practice award. A saved
  leaderboard can still be read without internet; an unavailable friend row
  does not fabricate a qualifying check-in.
- Installation state is local to the current device. Synced preferences may
  request an app, but do not make its achievements visible before its package
  is usable on that device. Earned history belongs to the profile across devices.

### What earning means

- Earn on a successfully saved, qualifying action. Opening a composer,
  clicking Start, receiving an AI reply, a failed save, and cancelling an action
  do not prove completion.
- Count each source action once. Reopening a completed task and completing it
  again does not create another task milestone. A habit's linked practice and
  manual completion resolve to one habit/day result.
- All day, week and month thresholds below are cumulative, not streaks. A
  missed day never erases an earned achievement. Weeks start on Monday.
- Capture a valid local activity date when the action happens, with UTC time
  and timezone offset where available. A later timezone change does not move
  old activity into new days. Reject invalid dates; do not invent local dates
  from UTC when the historical timezone is unknown.
- Awards are permanent within a profile. Editing or deleting source activity
  can reduce progress toward an unearned achievement, but does not revoke an
  earned award. Remove deleted source details from the calculation and retain
  only the minimal award record. Deleting the profile or all its data removes
  its achievements and receipts too.
- Existing history counts wherever it actually proves the condition. Preserve
  an unknown earned date as `Earned from earlier activity` instead of claiming
  the migration date was the activity date. Historical backfill is silent.
- Achievements do not grant Dew, money, paid content, rankings or extra access.
  There are no purchase, account-linking, public-sharing, breath-hold duration,
  faster-breathing, longer-single-session or mood-improvement requirements.

## 2. Achievement alerts

The requested control is one standard toggle in **Self → Achievements**:

**Achievement alerts**

`Show an alert when you earn an achievement. Achievements still unlock when alerts are off.`

- Proposed default: **on**, consistent with opt-out milestone feedback. It
  enables quiet in-app alerts; it does not request system notification
  permission or enable system notifications automatically.
- Store the boolean per profile through the existing settings path, using
  `notification_achievements`. Save it offline, retain it across restarts,
  and sync it using the account's existing settings conflict rules. Keep a
  guest profile's preference local until an explicit account migration.
- **Off:** continue recording progress and saving awards; suppress in-app and
  system achievement alerts, dismiss any pending achievement alert, and consume
  the corresponding presentation receipts. Other notification preferences keep
  their existing behavior.
- **On again:** alert for new qualifying unlocks from that point forward. Never
  replay unlocks suppressed while off, imported history, awards restored on
  reinstall, or awards learned from another device.
- Finish persisting the setting before reporting the switch as saved. Show
  the ordinary save error and restore the previous value if saving fails.
  Recheck the live setting just before dispatch, so switching off also cancels
  an alert queued while a practice was running. Receiving a synced Off setting
  has the same effect.
- A foreground alert is one quiet, nonmodal message. Never interrupt a running
  practice, take input focus, vibrate, or play a sound. Wait until its results
  or the next idle screen; group several unlocks from one action into one
  message, such as `3 achievements earned`.
- If the app is in the background, use only its existing supported notification
  route and existing permission. System permission denied means no system
  alert; it does not change the toggle or earning. Never issue both an in-app
  and a system alert for the same award on the same device.
- A practice alert deferred until the next idle screen is eligible only in the
  current foreground run. On restart, sync, or profile change, old pending
  receipts are consumed without an alert. Switch-off takes effect immediately
  on the current device; an offline second device uses its last synced value
  until it reconnects.
- Alert text includes the achievement name or grouped count, never diary text,
  habit names, task titles, photo names or Lumi messages. Respect the existing
  platform quiet-mode and accessibility behavior.
- Keep presentation receipts local to each device. Mark a receipt consumed
  before dispatch for best-effort, at-most-once presentation; a crash may miss
  an alert but must not replay an uncertain alert. Awards remain visible in Self.

## 3. Existing code and ownership

The current checkout already provides these integration points:

- [`../src/app/self_host.zi`](../src/app/self_host.zi) loads the independent
  Self bundle, supplies `self.json`, maps profile data and allows scoped store
  and locale calls. It currently adds account, progress, data, friends and
  Telegram extensions; it has no achievement catalog or award contract.
- Self is a dependency in [`../ziran.toml`](../ziran.toml). Its canonical
  repository is `waozixyz/self`; `src/model.zi` owns the profile document and
  `src/self.zi` owns its UI. Make shared Self UI changes there first, commit
  there, then update Inbe's dependency with the package tool. Do not edit a
  cached package or build copy.
- [`../src/screens/profile_screen.zi`](../src/screens/profile_screen.zi) still
  hosts Inner Breeze progress content. It should not become a second
  implementation of the shared Self achievement collection.
- [`../src/cells/catalog.zi`](../src/cells/catalog.zi),
  [`../src/cells/node_apps.zi`](../src/cells/node_apps.zi), and the Apps
  installation path distinguish bundled selections, node apps, and downloads.
  Reuse those installation decisions through one shared installed-app snapshot.
- [`../apps/versions.json`](../apps/versions.json) declares the bundled apps
  and optional Photos and Radio node apps in this checkout. Their source
  presence is not evidence that every user's device has them installed.
- [`../src/practices/practice_registry.zi`](../src/practices/practice_registry.zi)
  and [`../apps/practice/content.json`](../apps/practice/content.json) identify
  WHM, Meditation, Sun Salutation, Breathing Patterns and Tai Chi.
- [`../src/storage/storage_profile_stats.zi`](../src/storage/storage_profile_stats.zi)
  supplies current profile statistics. Reuse validated source history, but do
  not turn its limited recent-day scans into lifetime achievement totals.
- Session history lives in `sessions`, `session_rounds` and `meditation_logs`.
  Their values have different meanings: WHM rounds contain retention values,
  while Sun Salutation saves repetitions through the same round surface.
  Summing every `seconds` column cannot produce trustworthy practice minutes.
- Diary, habits, Lists and media already have account-scoped stores and sync.
  Some events needed below, such as a task's first completion date, a Radio
  listening interval, or a rendered Leaderboard check-in, are not recoverable
  from their current snapshots. They need durable facts going forward.
- Existing notification settings are loaded and saved in
  [`../src/app/app_settings.zi`](../src/app/app_settings.zi). Reuse that pattern
  for the alerts preference rather than creating another preferences store.

App-specific definitions, text, thresholds and fact rules belong in
`apps/<app>/`, with Practices using its existing `apps/practice/` source
directory. Shared Self presentation belongs in the Self repository. Inbe's
host supplies generic storage, scoped access, event persistence, notification
dispatch and installed-package information. Apps do not read another app's
database tables or internals. Existing compiled practice completion paths may
emit validated save facts through the bridge; this does not require an
unrelated rewrite of every practice screen.

## 4. Definitions, facts and storage

### Package supplied definitions

Each achievement-capable app ships a versioned `achievements.json` manifest
inside its signed package, plus its localized strings. Practice definitions
also declare their content-pack ID. The root integration supplies the Self
overview definitions to the shared profile display.

Each definition contains:

- A stable `app_id` and `achievement_id`, independent of translations and
  package slot numbers. The catalog's IDs below are the proposed stable IDs.
- `definition_version`, a rule version, order, title and description locale
  keys, and a badge reference in that package's approved assets.
- The metric, target and one bounded rule form: threshold, distinct days,
  distinct periods, distinct source IDs, first successful action, or return
  after a gap. Compound rules declare their required metrics explicitly.
- Required installed app/content IDs, optional source capability requirements,
  the source fact kinds it can consume, and a backfill policy.

Validate manifests when installing the package. Reject duplicate IDs, invalid
targets, unbounded rules, undeclared assets and cross-app writes. Retain a
last-known-good catalog if an update fails. A future downloaded app provides
its own catalog through this contract; an unknown app's achievements must not
be invented by the host. An older installed package with no catalog contributes
no achievement rows until its compatible achievement package is installed.

Keep achievement identity stable across package updates. Titles and translation
fixes may change; a materially different earning rule gets a new achievement
ID. Do not turn an earned 10-session award into a 100-session requirement by
editing the existing ID. Removed definitions are hidden from the current
catalog while their minimal earned history is retained for compatible return.

### Source facts

Facts carry only the data required by the rule: profile, publisher app,
source ID and revision, event kind, activity date, trusted numeric measures,
and the minimal flags or subtype IDs needed for qualification. Keep names,
diary prose, photo bytes, chat content and habit answers in their owning stores.

The host derives the publisher scope from the running package's validated
identity. An app cannot claim another app ID, write arbitrary awards, or
submit arbitrary SQL. An app's ordinary successful save returns its canonical
receipt; that receipt is the basis of the fact, not an unchecked UI message.
These are private personal milestones, not a tamper-proof competitive score.

Use source IDs for set membership, not increment-only counters. For example:

- Practice session: unique canonical session ID and practice ID.
- Meditation: one session ID even if both a session row and a meditation log
  describe it. Standalone legacy logs count once when their source identity
  and duration are valid.
- Diary: one valid nonempty document per local date, with a photo-present flag.
- Habits: one resolved completed habit/date, using that day's schedule and
  target; separate committed answer/span flags for their specific awards.
- Lists: distinct item IDs, with a persisted first successful completion date
  and actor. Re-completing an item does not add another first completion.
- Lumi: successful command/action receipts with their confirmed effects,
  not counts of sent messages or model claims of success.
- Photos: distinct original-content hashes, valid capture days and deliberate
  successful photo opens; reimporting the same file adds nothing.
- Radio: persisted playback-session/interval IDs with active playback seconds.
  Connection time, buffering, muted playback, stopped time and retries add
  nothing. Checkpoint while listening, so a crash loses at most one checkpoint.
  Deduplicate replayed intervals; merge concurrent-device overlapping intervals
  once rather than treating two streams as twice the listening time.
- Leaderboard: one successful own-row check-in per local day, plus the
  installed practice ID viewed. Opening an empty or failed board adds nothing.

For every current fact that is edited or deleted, update its contribution and
recompute the affected unearned progress. Keep only a minimal deduplication
tombstone when needed, without source content. Awards already earned remain.
All-data deletion clears these tombstones as well.

### Proposed account scoped records

The following names describe new records to add, not existing tables:

- `achievement_facts`: canonical source contribution, source version, date and
  bounded numeric/flag payload. Profile, app, fact kind and source ID form a
  unique identity. A source revision replaces its contribution; it does not
  create extra activity.
- `achievement_progress`: rebuildable aggregate cache by profile, app and
  achievement. Store the source/catalog revision used for its computation.
- `achievement_awards`: unique `(profile_id, app_id, achievement_id)`, rule
  version, known earned time/date or explicit unknown, and backfill origin.
- `achievement_alert_receipts`: device-local consumed/suppressed status by
  profile and award identity. Do not sync notification presentation state.

Keep the alerts preference in existing settings rather than one of these
tables. Add schema upgrades without rewriting source history or dropping old
upgrade paths. Include award records and non-reconstructible facts in account
export/import and all-data deletion. Rebuild progress from the restored sources
and facts; do not trust imported cached totals.

Use the existing encrypted, account-authenticated sync envelope and protocol
v6 for a separate achievement record namespace, proposed
`private.inbe.v1.achievements`. Do not put achievement records into Lumi's
restricted collection. Confirm node support before enabling the new namespace;
earning and Self remain available locally when sync is unavailable.

Synced awards merge by stable identity as a union; preserve the earliest known
valid earned time and keep unknown time distinct. Merge facts by canonical
source ID and revision, following their owning source's conflict semantics.
Never add two devices' aggregate progress counters together. Source facts and
their later source deletions may arrive in either order; use revisions and
tombstones to avoid resurrecting deleted progress.

### Evaluation and display contract

1. Commit a successful source mutation and its fact, or a durable outbox job
   for that fact, in the same storage transaction. The outbox closes the crash
   window for sources whose existing store cannot share the transaction.
2. Recompute only affected metrics and rules. Insert each newly earned award
   under a unique constraint, then commit the new progress and award records.
3. Queue an alert only for a genuinely new award caused by a live local action.
   Imports, backfills, replays, sync, startup rebuilds and catalog discovery
   initialize consumed receipts silently. A live local action may still qualify
   after a local outbox retry in the current foreground run.
4. Project the installed catalog, progress, awards and saved preference to Self.
   Self renders this data and writes only the alerts preference. It cannot
   create or edit awards.

Provide bounded, paginated projections over Self's existing generic store
bridge, with explicitly allowed document names for the catalog, pages and
settings. Do not place the 160 definitions into `self.json`: Self's current
identity decoder has an 8192-byte input limit. Add optional capability
negotiation so old Self packages keep working and old hosts do not claim to
support achievements. Any host interface change must use the existing app
version/compatibility machinery and requires a host update before packages
can rely on it.

## 5. Qualification rules used by the catalog

These rules make each requirement below implementable and consistent:

- **Active day:** a date containing at least one qualifying saved practice,
  habit completion, nonempty diary day, first task completion, confirmed useful
  Lumi action, successful photo import/open, one minute of active Radio
  playback, or a successful own-row Leaderboard check-in. Self overview uses
  the union of these dates. Source updates, settings changes and merely
  installing or opening an app are not activity.
- **Practice session:** a distinct saved session meeting its practice's
  qualification. WHM requires at least one completed normal round, with no
  retention-duration target. Meditation and Patterns require at least 60
  seconds of actual practice, excluding paused time; keeping a saved partial
  session of at least that length counts. Sun Salutation requires one complete
  sequence; Tai Chi requires one course item played to completion. Do not infer
  a full routine from a bare Start event or an ambiguous old session row.
- **Practice day:** a distinct local date with at least one qualifying session
  of that practice. General Practices days combine practice IDs by date.
- **Diary day:** one saved date containing non-whitespace authored text or a
  valid photo embed/attachment. Empty autosaves, formatting markers alone and
  broken image references do not count. Count edits to the same date once.
  A photo diary day needs at least one valid photo, not a particular app's
  photo integration. Months are distinct `YYYY-MM`; weeks are Monday-based
  civil week keys, with year-boundary tests.
- **Habit completion:** one habit/date that meets the owning app's existing
  completion rules and the historical schedule/target for that date. Count
  one result for counter, linked-practice, question and span representations
  of that same day. Reaching twice the target does not earn two completions.
  General habit-days are distinct dates across habits. A skipped question may
  count as an ordinary completed day under Habits' existing rules, but never
  earns the answered-question award; an unfinished span does not earn the
  ended-span award.
- **Completed task:** a distinct item whose own successful not-done → done
  transition is committed for this profile. Attribute shared-list actions to
  their actual actor; another person's completion cannot earn this profile an
  achievement. List-clearing awards require completing the final open item
  in a list containing at least three distinct active items, all now done.
  Removing the last open item or deleting a list does not qualify.
- **Useful Lumi action:** a confirmed change to an installed app's data,
  a qualifying practice caused by Lumi, or a verified requested progress
  chart. No-op commands, failed actions, cosmetic settings changes, plain
  conversation and repeated reads of the same chart/day do not add actions.
  A practice-start action counts only when its correlated session qualifies.
  The first-offline-action award requires the action's recorded mode to be
  offline; all other Lumi awards work with either connection mode.
- **Photo:** a successfully imported, nontrashed original with a unique hash.
  A photo-open fact requires deliberately opening a successfully decoded
  photo, not merely scrolling past a thumbnail. Days-of-photos thresholds
  use valid capture dates, not guessed dates for files with no date metadata.
- **Radio day:** at least 60 nonoverlapping seconds of active audible playback
  on a date. Minute totals are cumulative across listening sessions. The
  two-station award requires 60 active seconds for each of two distinct stable
  station IDs, not station names or reconnects.
- **Leaderboard check-in:** the person's own row successfully rendered in
  the visible board after an explicit open/selection, from valid cached or
  fresh data. Count one check-in date regardless of refreshes. No award
  depends on a rank, friend count, another person's performance or hold time.
- **Return after a 14-day gap:** a new qualifying action whose date is at
  least 15 civil days after the most recent prior qualifying date. There must
  be prior activity; first use never qualifies. The 14 days between them have
  no qualifying activity in that scope.

Progress for distinct-day and count thresholds is `current / target`, capped
at the target for display. For same-habit awards show the largest qualifying
day count for one habit. For a return award show earned/not earned plus its
condition. Tier achievements are individual awards with individual IDs; one
action may cross multiple tiers and produces one grouped alert.

## 6. Complete initial catalog of 160 achievements

Every numbered line defines one achievement, its stable proposed ID and its
earning condition. Session, day, completion and return terms use section 5.

### Self overview — 10 achievements

These are the profile's cross-app milestones, supplied by the root integration.

1. **A beginning** — `self.active.1`: record 1 active day.
2. **Three days for yourself** — `self.active.3`: record 3 active days.
3. **A week of moments** — `self.active.7`: record 7 active days.
4. **Fourteen moments** — `self.active.14`: record 14 active days.
5. **Thirty days for yourself** — `self.active.30`: record 30 active days.
6. **Sixty days of care** — `self.active.60`: record 60 active days.
7. **One hundred days** — `self.active.100`: record 100 active days.
8. **A growing history** — `self.active.180`: record 180 active days.
9. **A year of moments** — `self.active.365`: record 365 active days.
10. **Welcome back** — `self.return.14`: record an active day after a 14-day activity gap.

### Practices general — 10 achievements

Owned by `inbe.practices`; visible while Practices is installed.

11. **First practice** — `practices.sessions.1`: record 1 qualifying practice session.
12. **Five practices** — `practices.sessions.5`: record 5 qualifying practice sessions.
13. **Ten practices** — `practices.sessions.10`: record 10 qualifying practice sessions.
14. **Twenty-five practices** — `practices.sessions.25`: record 25 qualifying practice sessions.
15. **Fifty practices** — `practices.sessions.50`: record 50 qualifying practice sessions.
16. **One hundred practices** — `practices.sessions.100`: record 100 qualifying practice sessions.
17. **A lasting practice** — `practices.sessions.250`: record 250 qualifying practice sessions.
18. **Seven practice days** — `practices.days.7`: practice on 7 distinct days.
19. **Thirty practice days** — `practices.days.30`: practice on 30 distinct days.
20. **One hundred practice days** — `practices.days.100`: practice on 100 distinct days.

### WHM — 10 achievements

Owned by Practices; requires the installed `whm` content pack. All session
awards use normal completed rounds without comparing retention values.

21. **First WHM practice** — `whm.sessions.1`: record 1 qualifying WHM session.
22. **Five WHM practices** — `whm.sessions.5`: record 5 qualifying WHM sessions.
23. **Ten WHM practices** — `whm.sessions.10`: record 10 qualifying WHM sessions.
24. **Twenty-five WHM practices** — `whm.sessions.25`: record 25 qualifying WHM sessions.
25. **Fifty WHM practices** — `whm.sessions.50`: record 50 qualifying WHM sessions.
26. **One hundred WHM practices** — `whm.sessions.100`: record 100 qualifying WHM sessions.
27. **Three WHM days** — `whm.days.3`: practice WHM on 3 distinct days.
28. **Seven WHM days** — `whm.days.7`: practice WHM on 7 distinct days.
29. **Thirty WHM days** — `whm.days.30`: practice WHM on 30 distinct days.
30. **One hundred WHM days** — `whm.days.100`: practice WHM on 100 distinct days.

### Meditation — 10 achievements

Owned by Practices; requires the installed `meditation` content pack. Time
thresholds are cumulative, never a requirement to sit for one long session.

31. **First meditation** — `meditation.sessions.1`: record 1 qualifying meditation session.
32. **Five quiet moments** — `meditation.sessions.5`: record 5 qualifying meditation sessions.
33. **Ten quiet moments** — `meditation.sessions.10`: record 10 qualifying meditation sessions.
34. **Twenty-five quiet moments** — `meditation.sessions.25`: record 25 qualifying meditation sessions.
35. **Fifty quiet moments** — `meditation.sessions.50`: record 50 qualifying meditation sessions.
36. **Three meditation days** — `meditation.days.3`: meditate on 3 distinct days.
37. **Seven meditation days** — `meditation.days.7`: meditate on 7 distinct days.
38. **Thirty meditation days** — `meditation.days.30`: meditate on 30 distinct days.
39. **An hour of quiet** — `meditation.minutes.60`: accumulate 60 actual meditation minutes.
40. **Ten hours of quiet** — `meditation.minutes.600`: accumulate 600 actual meditation minutes.

### Breathing Patterns — 10 achievements

Owned by Practices; requires the installed `patterns` content pack. Preset
awards require a qualifying session with the recorded preset, not selecting it.

41. **First breathing pattern** — `patterns.sessions.1`: record 1 qualifying Patterns session.
42. **Five breathing practices** — `patterns.sessions.5`: record 5 qualifying Patterns sessions.
43. **Ten breathing practices** — `patterns.sessions.10`: record 10 qualifying Patterns sessions.
44. **Twenty-five breathing practices** — `patterns.sessions.25`: record 25 qualifying Patterns sessions.
45. **Fifty breathing practices** — `patterns.sessions.50`: record 50 qualifying Patterns sessions.
46. **One hundred breathing practices** — `patterns.sessions.100`: record 100 qualifying Patterns sessions.
47. **Seven breathing days** — `patterns.days.7`: practice Patterns on 7 distinct days.
48. **Thirty breathing days** — `patterns.days.30`: practice Patterns on 30 distinct days.
49. **A box-breathing moment** — `patterns.preset.box`: record 1 qualifying box-breathing session.
50. **A coherent-breathing moment** — `patterns.preset.coherent`: record 1 qualifying coherent-breathing session.

### Sun Salutation — 10 achievements

Owned by Practices; requires the installed `sunsalutation` content pack.
Qualification requires a completed sequence, without a pace or flexibility goal.

51. **First salutation** — `sunsalutation.sessions.1`: record 1 qualifying Sun Salutation session.
52. **Five salutation practices** — `sunsalutation.sessions.5`: record 5 qualifying Sun Salutation sessions.
53. **Ten salutation practices** — `sunsalutation.sessions.10`: record 10 qualifying Sun Salutation sessions.
54. **Twenty-five salutation practices** — `sunsalutation.sessions.25`: record 25 qualifying Sun Salutation sessions.
55. **Fifty salutation practices** — `sunsalutation.sessions.50`: record 50 qualifying Sun Salutation sessions.
56. **One hundred salutation practices** — `sunsalutation.sessions.100`: record 100 qualifying Sun Salutation sessions.
57. **Three salutation days** — `sunsalutation.days.3`: practice Sun Salutation on 3 distinct days.
58. **Seven salutation days** — `sunsalutation.days.7`: practice Sun Salutation on 7 distinct days.
59. **Thirty salutation days** — `sunsalutation.days.30`: practice Sun Salutation on 30 distinct days.
60. **One hundred salutation days** — `sunsalutation.days.100`: practice Sun Salutation on 100 distinct days.

### Tai Chi — 10 achievements

Owned by Practices; requires the installed `taichi` content pack. Completing
one course item qualifies a session; no form needs to be performed faster.

61. **First Tai Chi practice** — `taichi.sessions.1`: record 1 qualifying Tai Chi session.
62. **Five Tai Chi practices** — `taichi.sessions.5`: record 5 qualifying Tai Chi sessions.
63. **Ten Tai Chi practices** — `taichi.sessions.10`: record 10 qualifying Tai Chi sessions.
64. **Twenty-five Tai Chi practices** — `taichi.sessions.25`: record 25 qualifying Tai Chi sessions.
65. **Fifty Tai Chi practices** — `taichi.sessions.50`: record 50 qualifying Tai Chi sessions.
66. **One hundred Tai Chi practices** — `taichi.sessions.100`: record 100 qualifying Tai Chi sessions.
67. **Three Tai Chi days** — `taichi.days.3`: practice Tai Chi on 3 distinct days.
68. **Seven Tai Chi days** — `taichi.days.7`: practice Tai Chi on 7 distinct days.
69. **Thirty Tai Chi days** — `taichi.days.30`: practice Tai Chi on 30 distinct days.
70. **One hundred Tai Chi days** — `taichi.days.100`: practice Tai Chi on 100 distinct days.

### Diary — 20 achievements

Owned by `inbe.diary`. Week and month counts need one qualifying diary day
in each distinct period; the periods do not have to be consecutive.

71. **First page** — `diary.days.1`: save 1 qualifying diary day.
72. **Three pages** — `diary.days.3`: save 3 qualifying diary days.
73. **Seven pages** — `diary.days.7`: save 7 qualifying diary days.
74. **Fourteen pages** — `diary.days.14`: save 14 qualifying diary days.
75. **Thirty pages** — `diary.days.30`: save 30 qualifying diary days.
76. **Sixty pages** — `diary.days.60`: save 60 qualifying diary days.
77. **One hundred pages** — `diary.days.100`: save 100 qualifying diary days.
78. **An unfolding story** — `diary.days.180`: save 180 qualifying diary days.
79. **A year of pages** — `diary.days.365`: save 365 qualifying diary days.
80. **Two weeks remembered** — `diary.weeks.2`: write in 2 distinct weeks.
81. **Four weeks remembered** — `diary.weeks.4`: write in 4 distinct weeks.
82. **Twelve weeks remembered** — `diary.weeks.12`: write in 12 distinct weeks.
83. **Twenty-six weeks remembered** — `diary.weeks.26`: write in 26 distinct weeks.
84. **Three months remembered** — `diary.months.3`: write in 3 distinct months.
85. **Six months remembered** — `diary.months.6`: write in 6 distinct months.
86. **Twelve months remembered** — `diary.months.12`: write in 12 distinct months.
87. **A picture in your story** — `diary.photo_days.1`: save a valid photo on 1 diary day.
88. **Five illustrated days** — `diary.photo_days.5`: save valid photos on 5 distinct diary days.
89. **Twenty illustrated days** — `diary.photo_days.20`: save valid photos on 20 distinct diary days.
90. **A new page again** — `diary.return.14`: save a diary day after a 14-day diary gap.

### Habits — 20 achievements

Owned by `inbe.habits`. These follow Habits' historical schedule and completion
semantics; missing an unscheduled day never breaks a requirement.

91. **An intention takes shape** — `habits.created.1`: save 1 valid habit.
92. **First habit day** — `habits.days.1`: complete a habit on 1 distinct day.
93. **Three habit days** — `habits.days.3`: complete habits on 3 distinct days.
94. **Seven habit days** — `habits.days.7`: complete habits on 7 distinct days.
95. **Fourteen habit days** — `habits.days.14`: complete habits on 14 distinct days.
96. **Thirty habit days** — `habits.days.30`: complete habits on 30 distinct days.
97. **Sixty habit days** — `habits.days.60`: complete habits on 60 distinct days.
98. **One hundred habit days** — `habits.days.100`: complete habits on 100 distinct days.
99. **A habit history** — `habits.days.180`: complete habits on 180 distinct days.
100. **A year of habit days** — `habits.days.365`: complete habits on 365 distinct days.
101. **Ten completions** — `habits.completions.10`: record 10 distinct habit/date completions.
102. **Fifty completions** — `habits.completions.50`: record 50 distinct habit/date completions.
103. **One hundred completions** — `habits.completions.100`: record 100 distinct habit/date completions.
104. **Five hundred completions** — `habits.completions.500`: record 500 distinct habit/date completions.
105. **One habit, seven times** — `habits.single_scheduled_days.7`: complete the same habit on 7 of its scheduled dates.
106. **One habit, thirty times** — `habits.single_scheduled_days.30`: complete the same habit on 30 of its scheduled dates.
107. **One habit, one hundred times** — `habits.single_scheduled_days.100`: complete the same habit on 100 of its scheduled dates.
108. **A target met** — `habits.counter_target.1`: reach a counting habit's own target on 1 date.
109. **An answer recorded** — `habits.question_answer.1`: save 1 genuine answer to a habit question.
110. **A span recorded** — `habits.ended_span.1`: save 1 valid span with both start and end.

### Lists — 15 achievements

Owned by `inbe.lists`. Completed items count once by item ID, including shared
items only when this profile is the confirmed completing actor.

111. **A place for intentions** — `lists.created.1`: save 1 valid list.
112. **First task finished** — `lists.items.1`: complete 1 distinct task.
113. **Five tasks finished** — `lists.items.5`: complete 5 distinct tasks.
114. **Ten tasks finished** — `lists.items.10`: complete 10 distinct tasks.
115. **Twenty-five tasks finished** — `lists.items.25`: complete 25 distinct tasks.
116. **Fifty tasks finished** — `lists.items.50`: complete 50 distinct tasks.
117. **One hundred tasks finished** — `lists.items.100`: complete 100 distinct tasks.
118. **Two hundred fifty tasks finished** — `lists.items.250`: complete 250 distinct tasks.
119. **Three days of follow-through** — `lists.days.3`: finish tasks on 3 distinct days.
120. **Seven days of follow-through** — `lists.days.7`: finish tasks on 7 distinct days.
121. **Thirty days of follow-through** — `lists.days.30`: finish tasks on 30 distinct days.
122. **One hundred days of follow-through** — `lists.days.100`: finish tasks on 100 distinct days.
123. **A list brought to rest** — `lists.cleared.1`: finish the last open task in 1 list containing at least 3 distinct active tasks.
124. **Five lists brought to rest** — `lists.cleared.5`: do that for 5 distinct lists.
125. **Details carried through** — `lists.commented_completion.1`: finish 1 task with a saved nonempty comment.

### Lumi — 10 achievements

Owned by `inbe.lumi`. All effects must be confirmed by their owning app; no
achievement requires online AI, message volume or a paid provider.

126. **A little help, offline** — `lumi.offline_action.1`: complete 1 useful Lumi action in offline mode.
127. **Five useful moments** — `lumi.actions.5`: complete 5 distinct useful Lumi actions.
128. **Twenty-five useful moments** — `lumi.actions.25`: complete 25 distinct useful Lumi actions.
129. **One hundred useful moments** — `lumi.actions.100`: complete 100 distinct useful Lumi actions.
130. **Help on three days** — `lumi.days.3`: complete useful Lumi actions on 3 distinct days.
131. **Help on seven days** — `lumi.days.7`: complete useful Lumi actions on 7 distinct days.
132. **Help on thirty days** — `lumi.days.30`: complete useful Lumi actions on 30 distinct days.
133. **Your progress, made visible** — `lumi.progress_chart.1`: request 1 successfully built chart from verified saved activity.
134. **A practice with Lumi** — `lumi.practice.1`: finish 1 qualifying practice started through Lumi; requires Practices and at least 1 installed practice pack.
135. **A page with Lumi** — `lumi.diary.1`: successfully save 1 nonempty diary addition through Lumi; requires Diary.

### Photos — 10 achievements

Owned by `inbe.photos`; visible only while Photos is installed. No cloud
upload, public sharing, album feature or new editing tool is required.

136. **First memory kept** — `photos.originals.1`: import 1 distinct original photo.
137. **Ten memories kept** — `photos.originals.10`: import 10 distinct original photos.
138. **Fifty memories kept** — `photos.originals.50`: import 50 distinct original photos.
139. **One hundred memories kept** — `photos.originals.100`: import 100 distinct original photos.
140. **Three days remembered** — `photos.capture_days.3`: keep photos from 3 distinct valid capture dates.
141. **Seven days remembered** — `photos.capture_days.7`: keep photos from 7 distinct valid capture dates.
142. **Thirty days remembered** — `photos.capture_days.30`: keep photos from 30 distinct valid capture dates.
143. **A closer look** — `photos.opened.1`: deliberately open 1 successfully decoded photo.
144. **Ten closer looks** — `photos.opened.10`: deliberately open 10 distinct successfully decoded photos.
145. **Returning to your memories** — `photos.view_days.7`: deliberately open photos on 7 distinct days.

### Radio — 10 achievements

Owned by `inbe.radio`; visible only while Radio is installed. Listening time
is cumulative, audible playback time, not continuous-session length.

146. **A minute of atmosphere** — `radio.minutes.1`: listen for 1 active minute in total.
147. **Ten minutes of atmosphere** — `radio.minutes.10`: listen for 10 active minutes in total.
148. **Half an hour of atmosphere** — `radio.minutes.30`: listen for 30 active minutes in total.
149. **An hour of atmosphere** — `radio.minutes.60`: listen for 60 active minutes in total.
150. **Two hours of atmosphere** — `radio.minutes.120`: listen for 120 active minutes in total.
151. **Five hours of atmosphere** — `radio.minutes.300`: listen for 300 active minutes in total.
152. **Three listening days** — `radio.days.3`: listen on 3 qualifying Radio days.
153. **Seven listening days** — `radio.days.7`: listen on 7 qualifying Radio days.
154. **Thirty listening days** — `radio.days.30`: listen on 30 qualifying Radio days.
155. **Two atmospheres** — `radio.stations.2`: listen for at least 1 active minute to each of 2 distinct stations.

### Leaderboard — 5 achievements

Owned by `inbe.leaderboard`. These recognize checking personal progress,
without creating a competition to increase retention or beat another person.

156. **A look at your progress** — `leaderboard.check_days.1`: complete 1 own-row check-in.
157. **Three progress check-ins** — `leaderboard.check_days.3`: check your own row on 3 distinct days.
158. **Seven progress check-ins** — `leaderboard.check_days.7`: check your own row on 7 distinct days.
159. **Thirty progress check-ins** — `leaderboard.check_days.30`: check your own row on 30 distinct days.
160. **Two perspectives** — `leaderboard.practices.2`: check your own row for 2 distinct installed practices; requires at least 2 installed practice packs.

## 7. Backfill and migration

1. Add the achievement schema, preference default and migration checkpoint.
   Read old databases without changing the meaning of their source records.
2. Load each installed app's validated manifest. Scan its existing history in
   bounded, resumable batches through that app's scoped data provider.
3. Backfill confirmed practice counts/dates, meditation time, nonempty diary
   dates and valid photos, resolved habit history, currently completed owned
   tasks, valid list counts and photo-library hashes/capture dates where the
   source proves the requirement. Deduplicate meditation's two representations.
4. Do not infer a task's completion date from `updated_at`, a Patterns preset
   from duration, a full Tai Chi item from seconds alone, or a completed Sun
   Salutation sequence from a timer. Check actual source guarantees and import
   provenance before qualifying historical records. An ambiguous record remains
   ordinary history but cannot prove a specific achievement fact.
5. Only start counting facts absent from historical storage when that new
   instrumentation is installed: verified command effects, photo opens, Radio
   playback, Leaderboard check-ins, and first task completion dates. Do not read
   personal chat text to infer that a command succeeded.
6. If an old task is already done, it can prove a unique completed-item total
   when ownership/actor are known. Seed its deduplication record with unknown
   completion date, so a later reopen/re-complete does not count as a new item
   or falsely create its first completion date. Unknown shared actors do not
   prove personal completion.
7. Write awards with backfill origin and consumed alert receipts in the same
   batch. Record an earned date only when source ordering proves it. Restarting
   the scan must not add progress, alerts or duplicate awards.
8. Complete reconciliation before exposing a partially computed earned count
   as final. Show ordinary loading feedback during first migration, retaining
   a previously valid projection during later rebuilds.

## 8. Implementation sequence

### Stage 1 — Agree and encode the contract

- Turn this catalog into app-owned definition data without changing the IDs
  or thresholds accidentally. Add a catalog validator with count, unique-ID,
  valid prerequisite, bounded-rule and locale-completeness checks.
- Define the exact installed-app/content snapshot and document the difference
  between installed, bundled, pinned, updating and requested-on-another-device.
- Define source receipts, local dates, deletion semantics, projection pages,
  preference scope, award identity and alert eligibility before wiring UI.

Exit: the complete 160-definition catalog validates, and representative fixtures
describe earning, muted alerts, uninstalled apps and historical ambiguity.

### Stage 2 — Durable progress and earning

- Add data-preserving schema upgrades, scoped fact storage, dirty metric
  evaluation, unique award inserts, durable outbox handling and local receipts.
- Instrument committed practice, diary, habit and Lists mutations. Put
  app-specific qualification in their app packages. Add practice subtype and
  completion metadata only where the source currently cannot prove it.
- Add resumable backfill, export/import coverage and profile isolation.

Exit: real source actions and restored history produce correct deterministic
awards offline, including retries and restarts, without showing alerts yet.

### Stage 3 — Self collection and alerts switch

- Implement the shared collection, grouped app headings, nested practice
  headings, gray unearned badges, accessible progress and earned dates in the
  canonical Self repository. Add the standard alerts toggle and save behavior.
- Connect Inbe's scoped projection and preference provider, with pagination
  and capability negotiation. Update Self through Inbe's package dependency.
- Use existing icons or vector badge primitives for the first implementation.
  A separate request for illustrated badges can supply bitmap assets later;
  no generated image production is required for the achievement behavior.

Exit: Self renders correct installed-only results at phone and desktop sizes;
the toggle survives restart and account changes without losing achievements.

### Stage 4 — Complete every app and sync

- Add verified Lumi receipts, Photos view facts, Radio playback checkpoints
  and Leaderboard check-ins, finishing all 160 definitions' source adapters.
- Add encrypted sync records and source-aware merge/recovery. Reconcile
  synced awards silently, preserving different installation states by device.
- Enable quiet grouped alerts with the immediate Off behavior and local
  receipt rules in section 2.

Exit: every achievement has a working earning path, a working installed-state
gate, and a documented evidence/backfill policy. The feature is not complete
if the UI lists awards that have no implemented trigger.

### Stage 5 — Verification and release preparation

- Translate all achievement names, conditions, progress units, states and
  alerts in every shipped locale. Keep localized strings owned by the packages
  that supply the feature; never copy English placeholders to other locales.
- Check old-host/new-package and new-host/old-package behavior, including an
  older Self package and packages without achievement definitions.
- Run the targeted tests below and the repository's required compatibility,
  proof, locale and visual gates. Reuse stable build output directories.
- For an eventual approved release, add its numeric changelog entry and use
  `update_version.sh`, followed by the existing release-ready and exact-artifact
  phone checks. App and Self version changes must use their owning workflows.
  Publishing or releasing remains a separate owner-authorized action.

Exit: all 160 earning rules and alert states pass, translations are complete,
and the exact artifacts are ready for the existing release process.

## 9. Acceptance and verification

### Core earning and persistence

- Zero progress, one below target, exact target and above target for each rule
  type; every catalog ID has at least one fixture proving its earning path.
- Repeated saves, duplicate source events, source revisions, app restarts,
  outbox retries and a crash between source save and evaluation never inflate
  progress or insert another award.
- Account A, account B and a guest profile never read one another's progress,
  alert preference, award dates or pending alerts. All-data deletion includes
  awards, facts, cached projections, outbox jobs and local receipts.
- Late source deletion, partial sync, stale revisions and source correction
  update locked progress without revoking earned awards or resurrecting data.
- A legacy database migrates without data loss; backfill is resumable and
  silent. Mixed meditation history counts each session once. WHM retention
  and Sun Salutation repetitions are never treated as meditation minutes.
- Civil dates cover midnight, timezone travel, leap days and week/year
  boundaries. Cumulative day rules do not become accidental streak rules.

### Installed apps and package compatibility

- A fresh profile shows only its truly installed app and content sets; keeping
  an optional package in the APK does not expose its uninstalled achievements.
- Unpinning, offline use and a failed update retain installed achievements.
  Uninstall hides them and fixes totals immediately. Reinstall restores earned
  rows with no alerts. A failed first install adds no rows.
- Photos and Radio remain optional. Prerequisite-dependent Lumi and
  Leaderboard rows follow installed state, including different device layouts
  on the same account. Catalog loading handles more than the initial 160 rows
  without exceeding the Self identity-document limit.
- Malformed catalogs, duplicate IDs, cross-app award attempts and unsupported
  capabilities are rejected without replacing the working package or data.

### Alerts switch and delivery

- On + live local unlock: one quiet alert after the action commits; one message
  for several simultaneous awards. An active practice defers it until idle.
- Off + unlock: the earned row appears, progress is saved, and no alert is
  shown through any supported surface. Pending practice alerts are suppressed.
- Off → On: historical or muted awards never replay; the next live local
  unlock can alert. Repeated toggles never alter earned records.
- Preference survives restart and offline use, syncs with existing setting
  rules, and never changes another notification setting. Save failure restores
  the prior toggle value and uses the existing error behavior.
- Sync, import, migration, startup recovery and reinstall never produce a
  notification burst. Profile switching discards the old profile's pending
  presentations. Receipt recovery never replays an uncertain dispatch.
- Permission denied, background operation, platform quiet mode and an offline
  second device behave as specified in section 2. Foreground/background
  transitions never show both alert forms for one award.

### Source specific checks

- A Start/cancel loop grants no practice awards. Partial saved sessions follow
  the explicit qualification of their practice. Preset selection alone grants
  no Patterns award. No WHM rule examines a best hold or demands improvement.
- Empty diary autosaves and broken photo links grant no days. Multiple edits
  to one day count once. A diary photo does not require Photos installation.
- Counter increments, question answers, spans and linked sessions resolve to
  one habit/date completion. Historical schedules remain authoritative.
- Reopening/re-completing a task counts its item once. Deleting the last open
  task cannot earn a cleared-list award. Shared actions credit their actor.
- Lumi failures and plain chat add no action progress. Photos deduplicates
  original hashes. Buffering, mute and reconnects add no Radio listening time.
  Refreshing a Leaderboard does not add another check-in date.

### UI and existing checks

- Verify earned/unearned contrast, visible labels, keyboard focus, touch
  targets, wrapping of translated conditions, large text, and the toggle's
  accessible name and checked state. Test the existing light/dark themes and
  the supported zoom range without truncating the earning condition.
- Run relevant existing targets including `profile-host-test`,
  `launcher-policy-test`, `schema-zi-test`, `database-upgrade-zi-test`,
  `package-compat-test`, `package-check`, `proof-test`, `sync-recovery-test`,
  `version-test`, `locale-translated-test`, `clean-text-api-check` and
  `button-api-check`, plus the new focused achievement/alert tests.
- Run required visual and phone checks against the actual release artifacts.
  Every screenshot or UI automation check must use a private Xvfb/Xephyr
  display and disposable profiles. Scrub inherited `DISPLAY`,
  `WAYLAND_DISPLAY`, `XAUTHORITY` and `DBUS_SESSION_BUS_ADDRESS` before starting
  that private display; never verify against the owner's live windows.

## 10. Completion boundary

The requested feature is complete when Self owns the achievement UI, all 160
catalog entries can be earned through implemented app actions, only installed
apps/practices are shown, unearned badges are gray and understandable, profile
history survives restart/reinstall/sync, and the alerts toggle reliably controls
all achievement alerts while leaving earning active.

This planning change does not implement or deploy the feature. The catalog and
default-on in-app alert behavior are proposed decisions for implementation;
source-specific historical credit remains conditional on evidence as described
above.


Owner decision, 2026-10-21: every achievement has its own meaningful pictogram,
without shield artwork, numbered tiers or a badge container. The catalogs name
icons from the locked MingCute package; package preparation copies their shapes
and license into each app. Catalog tests reject repeated icon artwork across all
160 built-in achievements. Earned IDs, dates and progress are unchanged.
