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

- Move the Habits screens (`src/screens/habits*`) into `apps/habits/`, so
  Habits updates through its package without an APK; Practices after it.
- Split `src/storage/storage_core.zi` (3,300 lines) and
  `src/app/application.zi` (1,900 lines) into focused modules.
- Split the 3,300-line `Makefile`. With its test targets in their own file,
  test-only edits would no longer count as app changes for the phone check.
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
