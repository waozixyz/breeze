# Inner Breeze TODO

What is still pending, as of 2026-10-17. Remove an item when it lands; plans
belong in `docs/`, marketing outside this repository.

## Release 2.1.35

- Unreleased on master: Chess and the node's optional apps in More apps,
  beta apps in Settings › About, the Photos beta with photos copied to every
  photo node, and upright camera photos in Diary on desktops.
- The Diary redesign (Markdown and photos) is in progress in another session
  and is meant for this release.
- Release with `make release-ready`, then `make release` with the Moto
  connected (docs/cells.md, "Verification"); push only with the owner's
  say-so.

## Codebase

- Move the rest of Habits (`src/screens/habits*`) into `apps/habits/`, so
  Habits updates through its package without an APK; Practices after it.
  The count dialog moved in Habits 1.1.0 (`habits_view.zi`). The editor
  needs hosted Kryon Dropdown, Fieldset and SegmentedControl, the table
  hosted paint primitives and drag capture, statistics hosted Plot charts,
  and all of them typed host calls for habits, days and entries.
- Lumi's UI tests (`mk/tests-lumi.mk`) are read before `TARGET` is set, so
  they don't build the app first, and editing an `mk/` area file does not
  rebuild the artifacts whose rules list only `Makefile`.
- `make music-navigation-test` includes `src/platform/audio_runtime.h`,
  which the generator writes as `audio_runtime.h`; it does not build.
- `make release-ready` does not cover CI's browser add-on smoke tests or
  shard 0's Daochi sync test yet.

## Translations

- `locales/pt.txt` lacks accents in 14 strings; for example
  `exercise_sun_salutation` "Saudacao ao sol" should be "Saudação ao sol".
  The others: `profile_leaderboard_title`, `profile_metric_avg_hold`,
  `profile_friend_remove_message`, `profile_no_leaderboard_data`,
  `sun_salutation_repetitions_label`, `sun_salutation_tempo_preview_hint`,
  `sun_salutation_step_2`, `_3`, `_4`, `_9`, `_10`, `_11`, `about_text` and
  `elist_default_item_breathe`.

## Repository weight

- Practice media is 129 MB of the tracked files, most of it Tai Chi narration
  in 12 languages and two voices. Phones already download it as practice
  packs from the node, but the packs are built from these files in Git, so
  moving them out needs another home for pack sources first (owner decision).
