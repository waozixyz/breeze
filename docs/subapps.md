# Inner Breeze app packages

Inner Breeze has a root package and four independent portable feature packages.
The app picker recommends Habits and Practices and offers Lists and Diary as
optional downloads. Selections are stored per app and synced with the account.
The current packages update app behavior; screen compositions, graphics,
platform effects and the shared storage host still ship in the wrappers.
The full portable UI migration and Harmony Diary switch-over are unfinished.

## Build and installation

`make subapps` produces:

- `build/inbe.zib`, containing `subapps/habits.zib` and `subapps/practices.zib`.
- Independent `build/subapps/{habits,practices,lists,diary}.zib` files.
- `build/inbe-full.zib`, a local development and test bundle containing all four.

Native, Android and browser builds embed the base root. Lists and Diary are
absent from that root and the native embedded payload. Recommended apps work
offline. Downloaded packages are stored in the private `packages/` directory
beside `inbe.db`. The host checks signed release identity, API compatibility,
hash, size, allowed capabilities and the typed identity handshake before
publishing an immutable payload and atomically replacing its current pointer.
Root packages must contain exactly the two signed recommended dependencies.
Malformed packages cannot apply writes through a mismatched host protocol.

The app selection screen follows language selection and is also available from
Device settings. Choosing no apps leaves Settings available. Disabling an app
preserves its saved data. Existing profiles retain their legacy selection.
A requested optional app becomes available after its download succeeds;
failed downloads leave it selected and allow another manual update check.

## Updates and versions

Downloads use the Daochi release v2 endpoints on `https://api.waozi.xyz`:
`/api/v2/packages/{app_id}/latest` and
`/api/v2/packages/{app_id}/{sha256}.zib`. IDs are `inbe`, `inbe.habits`,
`inbe.practices`, `inbe.lists` and `inbe.diary`.

Automatic updates default on and check daily for the root and selected apps.
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
newer independently cached feature packages remain selected after restart.

`apps/versions.json` records separate numeric versions and increasing sequences
for every package. Add a numeric entry to the relevant module's
`apps/<source>/CHANGELOG.md`, then run `./update_version.sh --module NAME`.
Use `practices` as the module name; its source directory is `apps/practice/`.
Changes to either nested recommended payload also require advancing the root
package version. Advance the wrapper only for compiled host/UI changes: add
a numeric main changelog entry and run `./update_version.sh`.
About retains the wrapper version and displays each package version separately.
Module-only changes do not trigger the APK release workflow.

## Publishing configuration

The `App packages` GitHub Actions workflow builds and verifies package releases
on master. It signs and publishes automatically when all deployment values are
configured. Incomplete configuration produces downloadable build artifacts
without claiming publication.

1. Register the five app IDs and an active Ed25519 publisher key in Daochi.
2. Add the public key to `apps/publishers.json`, scoped to the five app IDs:
   `[{"key_id":"<registered ID>","public_key":"<64 lowercase hex digits>","app_ids":["inbe","inbe.habits","inbe.practices","inbe.lists","inbe.diary"]}]`.
3. Configure repository secrets `INBE_PACKAGE_SIGNING_KEY` (PEM Ed25519 key)
   and `INBE_NODE_SSH_KEY` (deployment SSH key).
4. Configure repository variables `INBE_PACKAGE_KEY_ID`,
   `INBE_NODE_KNOWN_HOSTS`, `INBE_NODE_SSH_TARGET` and
   `INBE_NODE_PACKAGE_STORE` (the node's absolute package directory).
5. Ensure the node runs Daochi's release v2 package HTTP implementation and
   has Python with `cryptography` available for the remote importer.

`python3 scripts/package-release.py --store build/package-releases --key
/path/to/private.pem --key-id REGISTERED_ID` stages a signed release locally.
Add `--ssh-target USER@HOST --remote-store /absolute/node/package-store` to
publish. The publisher checks that the signing key matches the shipped public
pin and rejects changed packages whose version and sequence have not advanced.
Upload staging uses a private remote directory and strict SSH host checking.
Private signing material is never included in package archives.

The wrapper release workflow requires public pins covering all five app IDs,
so a release cannot omit optional apps without a configured publisher.
Production publisher pins are currently empty. The observed Waozi package
endpoint returned 404 before configuration. Optional production installation
and automatic server publication require completing the setup above.

## Account app choices

Sync v6 uses `private.inbe.v1.app-preferences`. Each of the four `app_used_*`
keys is a separate timestamped record, including explicit zero values for
removals. Independent changes merge without overwriting unrelated selections.
Pending local choices win equal timestamps; newer remote choices win.
Invalid keys, values and timestamps cannot alter preferences. Versions, package
paths, release sequence floors and the automatic-update preference stay local.
All apps share the existing account, SQLite database and outbox. Diary entries
currently remain device-local, as they were in Harmony.

## Diary and standalone use

Diary owns date arithmetic, entry editing, JSON documents and calendar marks in
its own VM. Its bounded host capabilities provide only its private files and
clock. Entries use Harmony's existing version-1 per-day document format;
text edits preserve attached photo metadata. Failed or malformed reads never
overwrite the original document. Native storage uses an exclusive directory
lock and atomic writes.

For explicit migration, set `INBE_DIARY_IMPORT=/absolute/harmony/diary` when
opening Diary. The importer copies safe regular filenames and skips existing
Inbe files and symlinks. It leaves Harmony originals untouched. There is no
automatic migration from the owner's live profile. Photo attachment and viewing
UI and switching Harmony's existing Diary route to Inbe remain unfinished.

The desktop wrapper accepts `--bundle /path/to/inbe.zib`, or an individual
Habits, Practices, Lists or Diary ZIB. A feature bundle opens its own app using
the same host and account. Explicit local files still pass capability and
identity checks; publisher verification applies to network installation.
`--feature habits|practices|lists|diary` opens a selected feature.
`_HARMONY_APP_FEATURE` requests on the process's own SDL X11 window use
1 for Lists, 2 for Habits, 4 for Practices, 8 for Diary and 0 for the parent.
The host control interface also supports `open.diary`.

Mini mode remains a temporary Practices session. It preserves the full
profile's selection and its existing history behavior. Desktop focus loss
continues to be distinct from mobile lifecycle and explicit pause.

These bundles currently need Inbe's capabilities and are not complete
standalone UI applications in the generic Kryon player. Moving all screens and
assets into portable UI trees, binding the same UI to raylib and canvas, adding
Diary photo parity and migrating Harmony's launcher are required to finish the
requested architecture. UI changes still require wrapper releases.

## Verification

`make subapps-test` exercises the root and all four actual feature bundles,
typed capability rejection, shared SQLite/identity, a 1.8.9 upgrade fixture,
practice timing, all selection masks and Diary Unicode/calendar/document edits.
`make package-release-test` checks Ed25519 metadata, payloads, signed nested
content, rollback rejection, cache repair, manual checking with auto-update off
and cancellation that preserves manual requests. Account preference tests
exercise real sync SQL and account isolation. The Wasm download test verifies
bounded browser streaming, filesystem writes, cancellation and failures.
`make subapps-diary-test` verifies the standalone Diary window, delayed saves,
clock insertion, calendar and restart. GUI onboarding and navigation tests run only on private Xvfb displays with
application-owned windows and disposable profiles.
