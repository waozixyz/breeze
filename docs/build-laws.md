# Build laws in Ziran

Every Inbe law is stated, implemented, and checked in Ziran. Bend, its Node.js
checker, and the generated `.zi` tables are gone. This reference describes the
checked behavior, enforcement and limits.

## Implemented

- **Release metadata.** `update_version.sh` synchronizes the release fields from
  the numeric `CHANGELOG.md` entry; `check-version.py` rejects inconsistencies.
  It runs in the native, web, and Windows artifact graphs and in Gradle and
  CMake, including incremental builds. It is a structural build check, not a
  formal theorem.
- **Sync retry** (`src/app/sync_retry.zi`, laws in `sync_retry_laws.zi`).
  Ordinary hand-written Ziran, with 21 `#law` obligations checked by
  `ziran check`. Result codes and retry states are checked exhaustively,
  including out-of-range persisted integers. They establish: the wire result
  codes; success resetting the retry state; temporary challenge and request
  failures following 5/15/30/60 seconds with a saturated fourth attempt; each
  actionable error class and every unknown code stopping automatic retry; the
  saved-delay mapping; which results need user action; and the attempt never
  leaving its saved range. Expected values are written independently of the
  implementation.
- **Storage layout** (`src/storage/storage_layout.zi`, laws in
  `storage_layout_laws.zi`). The current and older directory names (distinct on
  every target), database names, export and historical import entries, web
  homes, and temporary names are fixed by 11 laws. See `docs/STORAGE_LAYOUT.md`.
  `tests/storage_layout.h` holds independently written expected names for the C
  storage path test.
- **Practice lifecycle** (`src/app/practice_lifecycle.zi`, laws in
  `practice_lifecycle_laws.zi`). A pure decision that Android's
  `android_sync_lifecycle` applies. Twelve laws, proved for every flag
  combination: desktop focus loss cannot pause or move a session into the
  background-timer path; a user pause is never resumed by the lifecycle; the
  timer keeps running in the background only with permission and a visible
  indicator; the lifecycle never pauses and resumes at once.
- **Sync recovery** (`src/app/sync_recovery_policy.zi`, laws in
  `sync_recovery_policy_laws.zi`). Pure decisions used by
  `sync_async.zi` and `social_async.zi`. Thirteen laws: a response for a
  switched account or server is never applied; a failed required social stage
  ends the refresh without clearing anything, so known friends and requests
  stay; a failed optional statistic clears only itself; stages run once, in
  order, and the average statistic exists only for `whm`.
- **Habit merge** (`src/storage/habit_merge_model.zi`, laws in
  `habit_merge_laws.zi`). Seven laws over every three-day sequence: the merge
  keeps both sides, invents nothing, and is commutative, idempotent, and
  associative, with a missing day as identity. `tests/habit_merge_sql_test.py`
  runs the real merge SQL (both `storage_merge_habit_into` and the remote-map
  path) on all 729 sequence pairs and requires the same behavior, so the proof
  of the model is tied to the SQL that actually runs.
- **Account restore** (`src/storage/sync_restore_model.zi`, laws in
  `sync_restore_laws.zi`). Four laws: restoring queues every local entity and
  invents none. `tests/sync_restore_sql_test.py` runs the real clear-and-requeue
  SQL on every subset of already-queued entities, including a soft-deleted
  habit, and requires that every local entity is queued afterward.
- **Dialog rules** (`src/app/modal_rules.zi`, laws in `modal_rules_laws.zi`).
  Seven laws over every dialog type and screen numbers -2 to 20: each
  screen-specific dialog appears only where it belongs, all others appear
  anywhere, and the habit-tab flag cannot leak a dialog onto another screen.
- **Ziran `forall` laws** (in the pinned Ziran package).
  `#law NAME forall x: 0..4, k: SomeEnum => condition;` checks every
  combination of integer ranges and enum members with the compile-time
  evaluator. A failure reports the counterexample; a domain over 1,000,000
  cases or a condition the evaluator cannot decide is `unknown`, which fails
  the gate unless explicitly waived.

The laws do not prove server availability, delivery, alias/friend restoration,
filesystem or SQLite behavior, or arbitrary `.zi` code. Integration tests check
those effects separately.

## Build behavior and verification

`make build-laws` runs the version check and `ziran check` on each module in
`LAW_MODULES`. Failed checking prevents compilation; no old generated output can
satisfy it because none exists. Gradle and CMake run the same checks. Node is no
longer required to build, and the Flatpak no longer carries a Node build tool.

- `make proof-test` runs `tests/law_mutation_test.sh`: the unmutated tree
  passes, and eight deliberate breakages (a changed result code, delay,
  saturation bound, stop rule, reset value, and storage names) are each rejected
  by the specific law that should catch them. This is what shows the laws are
  not vacuous.
- `make sync-retry-zi-test`: behavior across the portable bundle and the C, C++,
  and Go targets, from source and saved IR.
- `make sync-recovery-test`: generated Ziran C and the coordinator.
- `make version-test`: release synchronization and mismatch rejection.

Compiler regression tests, the text/button scanners, migration tests, and the
sync integration suite are separate checks with their own scope; none is a
proof of application behavior.

## Toolchain

`ziran.lock` selects the exact Ziran package. Release builds use
`PACKAGE_FLAGS=--locked`; local canonical checkout overrides belong only in the
ignored `ziran.local.toml`. Update dependencies through the package command,
then run `make package-check` and the relevant law and behavior checks.

## Model and implementation

A law about a model proves the model. Where the real behavior is SQL or effectful
code, a test runs that code against the same statements (`habit-merge-sql-test`,
`sync-restore-sql-test`), and the mutation test shows each such test rejects a
broken implementation. What is not covered is stated next to each law; no law
claims to prove a separately implemented path it does not check.

## Limits

The proofs cover their declared finite domains. Wider or unbounded merges are
not established by the bounded model or by a passing SQL test. Rendering,
layout and interaction transitions use runtime tests, not formal UI proofs.
The mutation harness remains local to this application.

## Trust and use with smaller models

A model may change the implementation while the laws stay fixed; its output is
accepted only when `ziran check` proves them. This reduces dependence on model
quality for **specified behavior**. It does not make a small model as good at
designing contracts or noticing a missing requirement.

The trusted base is the Ziran checker and evaluator, the build graph, and the
target compiler. An agent that can rewrite `*_laws.zi`, the mutation test, or
the gates can weaken the guarantee, so protect them with protected branches,
required checks, and independent review ownership on the host; repository files
cannot make themselves immutable. Those hosting settings have not been changed.
`AGENTS.md` states ownership and the rule not to weaken laws.
