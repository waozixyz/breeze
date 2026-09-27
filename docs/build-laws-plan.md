# Build contracts and Bend proofs

## Implemented

Inbe's release metadata uses the numeric changelog release and the permanent
`APP_VERSION_*` macros. `update_version.sh` synchronizes the release fields;
`check-version.py` rejects inconsistencies. The version check now runs in the
native, web, and Windows artifact graphs and in both Gradle and CMake, including
incremental builds. Version semantics remain a structural build check, not a
formal theorem.

The retry implementation is **Bend 2 code evaluated into checked Ziran**:

1. `laws/sync_retry/main.bend` defines the actual pure retry policy.
2. `LAWS.bend` states 11 universally quantified contracts; `PROOF.bend` proves
   them for the complete finite input types.
3. Inbe's `scripts/bend-laws.mjs` uses directly pinned Bend 2.0.16, commit
   `15ae0c86f3193b8f645b4bedbc438655b648d0da`. It verifies the checker and Base
   hashes before loading, checks termination and types, and rejects holes,
   unproved declarations, `@unsafe`, foreign implementations, remote imports,
   and imports outside the proof package.
4. The checked function is evaluated directly in Bend's kernel for all 45
   combinations of result and retry state. `scripts/generate-sync-retry.mjs`
   writes `src/app/sync_retry.zi`, which the Ziran compiler checks and lowers.
   There is no separate handwritten retry implementation or Bend runtime on
   the phone.
   `src/storage/sync_result.zi` declares the wire result codes; generation
   rejects changes to their names or numeric values.
5. Account-data and social retries both call that module. It clamps persisted
   integers before selecting a proved decision, avoiding increment overflow.
   Unknown results stop automatic retries.

The proofs establish success resetting the retry state; temporary challenge
and request failures following 5/15/30/60 seconds with a saturated fourth
attempt; actionable failures stopping automatic retry; and the mapping of
saved retry states and delays. Each error classification has its own law.
They do not prove server availability, delivery, alias/friend restoration,
or arbitrary `.zi` behavior. The integration tests for those effects remain,
but their native build currently stops at the unfinished Ziran source gate.

The private-data directory and database names come from the proved finite
Bend policy in `laws/storage_layout`. Its generated header is consumed by
`data_root()` and storage import/export code. The proof establishes current
names on each target and that the export entry is importable; it does not
establish filesystem or SQLite behavior. See `docs/STORAGE_LAYOUT.md`.

## Build behavior and verification

Install Node.js **22.18 or newer** on the build host and initialize the
`vendor/bend`, `vendor/ziran`, and `vendor/kryon` submodules. The checker runs
offline once those dependencies are present.
CI and package builders provide Node explicitly. The container setup script
uses pinned, checksummed official Node archives; ordinary compilation never
downloads a proof tool. Flatpak removes its Node build tool from the app.

- `make build-laws`: release consistency and proofs.
- `make proof-test`: deterministic generation, contract-breaking mutations,
  enum mapping drift, and rejection with old generated Ziran source present.
- `make sync-retry-zi-test`: source and saved IR behavior across C, C++, Go,
  and portable bundles.
- `make sync-recovery-test`: the generated Ziran C and coordinator, including
  all known result codes, extreme persisted integers, and social retry state;
  currently blocked by the unfinished app source gate.
- `make version-test`: release synchronization and rejecting mismatches.
- `make proof-test`: checker/evaluator acceptance and rejection, including
  broken laws and changed wire codes.

Make's generated-source and app artifact prerequisites run the checks on
every invocation. Failed checking prevents compilation even if old source
exists. Successful generation preserves its timestamp when the proved policy
is unchanged. Gradle `preBuild` always checks; direct CMake builds regenerate
the Ziran module. Plan 9 compiles that module with the other app sources.

The Ziran compiler's image surface restriction remains separate from these
application proofs. Compiler regression tests do not prove application
behavior.
The text/button scanners, migration tests, and sync integration suite remain
separate checks with their own scope.

## Trust and use with smaller models

A model can change the implementation and provide proofs while the contracts
stay fixed. Its output is accepted only when the checker verifies those
contracts. This reduces dependence on model quality for **specified behavior**;
it does not establish that a smaller model is equally good at designing the
contracts or diagnosing missing requirements.

The trusted boundary is the pinned checker/Base, the finite-table generator,
the enum/integer adapter, build graph, and target compiler. Regression tests
exercise the integration boundary. An agent able to rewrite the laws or gates
can weaken the guarantee. Protected branches, required checks, and independent
review ownership should protect those files on the hosting service; repository
files alone cannot make themselves immutable. Hosting settings have not been
changed by this implementation.

`AGENTS.md` now states ownership, contract-change boundaries, and the remaining
product/review obligations instead of treating prose as a proof system.

## Next migrations, in order

1. Move practice lifecycle decisions into a pure finite policy: desktop focus
   cannot pause a session, user pause remains explicit, and mobile background
   transitions preserve the required timer behavior. Compile its proved table
   through the same Bend checker; retain platform integration tests.
2. Specify sync recovery transitions: restoring an account cannot discard
   queued local changes, partial social refresh cannot erase known friends,
   and an account switch cannot apply responses belonging to the old account.
   Model effects explicitly; proofs of scheduling do not prove network delivery.
3. For unbounded algorithms such as collection merges, define a checked direct
   compilation path and its semantics before expanding beyond finite tables.
   Do not claim a proof of a model also proves a separately implemented C path.
4. Specify widget behavior in ordinary Kryon Ziran modules and test the
   portable values and host boundaries. Ziran remains unaware of UI widgets.
   The current Inbe source gate still reports unsupported host operations.

[Bend's upstream guide](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md)
describes its law/proof convention. Inbe uses the actual checker rather than
naming ordinary assertions or tests mathematical proofs.
