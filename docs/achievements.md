# Achievements

The shared Entity profile displays achievements supplied by installed apps and
practice content. Each row has its own icon, earning condition, progress and
permanent earned date. Uninstalled apps do not contribute visible rows or totals;
reinstalling an app restores its saved awards without replaying alerts.

The built-in catalogs contain 160 entries. Their machine-readable definitions
live in `apps/*/achievements.json`, with translations in each app's
`achievement-locales/`. Stable IDs, including the historical `self.*` IDs, are
persisted data and must not be renamed when changing a display name.

## Ownership and storage

`src/app/achievement_host.zi` provides Entity's read-only projection and the
owner-guarded alert preference. `src/app/achievement_runtime.zi` reconciles
committed activity and presents new awards. The app adapters supply facts;
merely opening an app or starting an unsaved practice does not earn an award.

`src/storage/achievement_records.zi` validates account-owned facts and permanent
awards. They sync in `private.inbe.v1.achievements`. Presentation receipts stay
local. Deleting source activity removes its contribution to unearned progress;
it does not revoke permanent awards. Deleting the profile removes its records.

The **Achievement alerts** switch controls presentation, not earning. It uses
`notification_achievements`; silent backfill, imports, sync and reinstall do not
replay historical alerts. Active practices defer alerts until idle.

## Qualification rules

These rules make each requirement below implementable and consistent:

- **Active day:** a date containing at least one qualifying saved practice,
  habit completion, nonempty diary day, first task completion, confirmed useful
  Lumi action, successful photo import/open, one minute of active Radio
  playback, or a successful own-row Leaderboard check-in. Entity overview uses
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

## Catalog

Every numbered line defines one achievement, its stable ID and its
earning condition. Session, day, completion and return terms use the qualification rules above.

### Entity overview — 10 achievements

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

## Verification

`make achievements-test achievement-catalog-test` checks storage, source facts,
ownership, deduplication, translation coverage, unique icon artwork and agreement
between this catalog and the packaged definitions. The complete application also
runs its normal package compatibility, migration, locale, visual and release
checks. A focused test pass does not replace those gates.
