# Inbe repository rules

## Ownership and releases

- Dependencies are Ziran packages pinned in `ziran.toml`/`ziran.lock` and
  linked under `build/packages/`; there is no `vendor/`. Never edit a package
  checkout. Change Kryon (or any dependency) in its own repository on `master`,
  commit and push there, then run `ziran update NAME` here and commit
  `ziran.lock`. Run `make package-check` after dependency changes. For local
  debugging, map a package to a working repository in the ignored
  `ziran.local.toml`; release builds use `PACKAGE_FLAGS=--locked`.
- Add the numeric release to `CHANGELOG.md`, then run `./update_version.sh`.
  The canonical macros are `APP_VERSION_STRING`, `APP_VERSION_MAJOR`,
  `APP_VERSION_MINOR`, and `APP_VERSION_PATCH`; do not create aliases.
  Only the GitHub Actions release workflow creates or pushes release tags.
- Translate changed strings in every affected locale; no English placeholders.
- `make locale-translated-test` fails on any locale string that still equals
  its English text. Translate it; add it to `tests/locale_same_as_english.txt`
  only when it is a real brand name, loanword, or format string.

## Machine-checked contracts

- `make build-laws` is mandatory for native, web, and Windows artifacts;
  Gradle and CMake enforce the same version and proof checks independently.
  Never bypass a failed gate or hand-edit generated policy tables.
- Retry behavior lives in `laws/sync_retry/main.bend`. Implement changes there
  and prove `LAWS.bend` in `PROOF.bend`; the app consumes the checked table.
  Do not weaken laws to make an implementation pass. Contract changes require
  explicit product intent and separate review from implementation changes.
- Run `make proof-test sync-recovery-test version-test` for these contracts.
  Coverage, trust boundaries, and the next proof migrations are described in
  [docs/build-laws-plan.md](docs/build-laws-plan.md).

## Public UI and sync boundaries

- Use current Kryon calls `Text(session, TextProps)`,
  `Image(session, ImageProps)`, and `Button(session, ButtonProps)` directly.
  Semantic images use the same `Image` surface. No positional Text, legacy
  drawing calls, alternate widgets, or thin local forwarding wrappers.
  Keep meaningful compositions and gestures; use standard Checkbox and Toggle.
  Run `make clean-text-api-check button-api-check` for UI changes.
- If a required widget capability is missing, implement the reusable primitive
  upstream first. Do not work around it in Inbe or generated code.
- Use sync protocol v6 and the clean Kryon API; no new `Ksync` names or wrappers.
  Remove old wire projections and format fallbacks as the storage and sync
  modules are converted to current Ziran. Keep the current protocol and data
  model in Inbe rather than adding compatibility adapters.
- Keep on-disk schema and user-data upgrade paths. Convert their implementation
  to checked Ziran; do not delete a migration merely because it handles an old
  database. An upgrade must preserve existing data, and its replacement needs
  a test using an older database fixture before the prior path is removed.
- A `.zi` filename is not a completed migration. All owned application
  behavior, including storage upgrades, must compile as current Ziran. Prefer
  direct Ziran foreign imports for native libraries; migrate owned C adapters
  as Ziran gains the required ABI support. Never keep application policy in C.

## Product behavior and readability

- Desktop focus loss must not pause practices, freeze animation, suppress
  updates, or enter the mobile background-timer path. Preserve mobile/web
  lifecycle handling and explicit user pause as separate behavior.
- Preserve hover, press, and focus transitions. Session audio controls have
  44-unit targets (24-unit icons plus 10-unit padding), scaled and spaced.
- Lists starts with list tabs, without a separate title bar or dropdown.
- Use descriptive names, explicit control flow, and focused helpers. Never
  compress multiple statements, branches, declarations, or checks onto one line.
  Format changed source, inspect the final diff, and run `git diff --check`.

## Bend

When using Bend:
- run `bend guide` to learn it
- use `LAWS.bend` to keep important rules
- run `bend PROOF.bend` before committing
- parallelize the code whenever possible
