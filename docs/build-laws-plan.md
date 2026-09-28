# Build laws in Ziran

Every Inbe law is stated, implemented, and checked in Ziran. Bend, its Node.js
checker, and the generated `.zi` tables are gone. This file records what the
laws cover, how they are enforced, and what is still to do.

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
- **Ziran `forall` laws** (in `~/Projects/ziran`).
  `#law NAME forall x: 0..4, k: SomeEnum => condition;` checks every
  combination of integer ranges and enum members with the compile-time
  evaluator. A failure reports the counterexample; a domain over 1,000,000
  cases or a condition the evaluator cannot decide is `unknown`, which fails
  the gate unless explicitly waived.

The laws do not prove server availability, delivery, alias/friend restoration,
filesystem or SQLite behavior, or arbitrary `.zi` code. Integration tests for
those effects remain, and the sync recovery native build still stops at the
unfinished Ziran source gate.

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
- `make sync-recovery-test`: generated Ziran C and the coordinator; blocked by
  the unfinished app source gate.
- `make version-test`: release synchronization and mismatch rejection.

Compiler regression tests, the text/button scanners, migration tests, and the
sync integration suite are separate checks with their own scope; none is a
proof of application behavior.

## Toolchain pin

`ziran.lock` pins Ziran commit `ff497c9` (`forall` and enum-aware `custom` laws)
on `master`. Law identity and waiver validation landed later in `e63fcf5`; bump
the pin with `ziran lock` when the rest of the lock is ready to move.
`ziran lock` currently also re-resolves Kryon, whose working tree needs raylib,
so the pin was changed by hand to the toolchain commit only. Local builds use
the `../ziran` and `../kryon` working trees through `ziran.local.toml`.

## Remaining Ziran work

1. **Determinism matrix.** Law tables byte-identical across runs and between
   source and saved IR (covered for `forall` and enum laws in Ziran's
   `tests/laws.sh`, not yet across the whole matrix).
2. **Mutation gate as a Ziran library.** Inbe's `tests/law_mutation_test.sh` is
   a local script; Ziran should provide the reusable form.
3. **Beyond finite tables.** Bounded quantification over sequences, and a stated
   relation between the checked pure model and the lowered native code, so a
   proof of a model is never claimed to prove a separately implemented C path.
   Needed for collection merges and the SQL-level recovery rules below.

Done in Ziran: `forall` over integer ranges and enums, counterexamples, the case
budget, enum members and typed locals in pure procedures, and law identity and
waiver validation (unique names; a waiver must name an existing law; only
unknown laws can be waived).

## Next migrations, in order

1. **Recovery rules that live in SQL.** Restoring an account resets the sync
   state and deletes the outbox, relying on a backfill to re-queue local data;
   a law that restoring cannot lose queued local changes needs the sequence
   model above, and is covered today only by storage integration tests.
2. **Collection merges**, once Ziran supports bounded sequence quantification.
3. **Widget behavior** in ordinary Kryon Ziran modules with tests of the
   portable values and host boundaries. Ziran stays unaware of UI widgets.

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
