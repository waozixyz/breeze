# Private data layout

Inbe uses `<app internalDataPath>/inbe` on Android, `$XDG_DATA_HOME/inbe`
(or `~/.local/share/inbe`) on Unix desktops, `%LOCALAPPDATA%/inbe` on
Windows, and `/home/inbe` in the web filesystem. The database is `inbe.db`
inside that directory. Android release and debug packages have separate
private `internalDataPath` directories.

The older `breathing` or `BreathSession` directory and `breathing.db` database
upgrades now have checked Ziran implementations. Their linked tests cover
directory conflicts, failed moves, SQLite WAL content, and failed backup
publication. The containing startup modules still have C-style source, so the
upgrades have not run in a complete app build. The loose plain-text session
file upgrade now has a checked parser and startup scanner with a linked test,
but its containing startup path has not linked as an app. The checked Linux
archive module reads file-session ZIPs and current or historical database ZIPs,
and writes snapshot ZIPs from committed SQLite data. Its public caller still
fails source checking, so import/export has not run in the full app. The import
table recognizes both
`inbe-data/inbe.db` and the older `breathing-data/breathing.db` archive entry.
Exports use `inbe-data/inbe.db` and `inbe-data/metadata.json` with format
`inbe-data-sqlite`.

`src/storage/storage_layout_laws.zi` states the current and older directory
names (distinct on every target), the current and older database names, and
the current and historical archive entries, and `ziran check` proves the
constants in `src/storage/storage_layout.zi` match. That module supplies the
directory and database names, archive suffix, and import/export entry names;
`data_root()` and import/export code consume its names. The laws cover the
finite naming policy only. Native storage tests cover path selection,
database opening, and archive round trips. The full app remains unbuildable
during the Ziran migration, so those native integration tests cannot currently
be linked from the full app build.

## Desktop profiles

`make run` and `make run-termi` use the persistent debug profile at
`$XDG_DATA_HOME/inbe-debug` (or `~/.local/share/inbe-debug` when XDG_DATA_HOME
is unset). `make run-fresh` uses a disposable temporary profile.

`make install` installs the production desktop app under `~/.local` by default.
Launching `inbe` or its desktop entry uses `$XDG_DATA_HOME/inbe` (or
`~/.local/share/inbe`). Sync keys, settings, sessions, habits, and downloaded
meditation audio stay inside their respective profile directories. `PREFIX`
can be set explicitly for a system installation; it does not change the
production data location. Debug and production windows have separate desktop
identities and single-instance locks.

## Private Lumi sync collection

New Lumi records use `private.inbe.v2.lumi` and key generation `inbe-lumi-1`.
Only validated `cell.lumi.*` records belong to that collection. Its key is
HMAC-SHA-256 of the owner's full ML-DSA private key with the distinct context
`inbe-private-lumi-record-key-v2`, using the existing record encryption format.
Diary, feedback, sessions and other private records retain their existing
owner-only collections and legacy key context. A Lumi delegate must receive
only the approved Lumi key; the legacy global key and combined
`private.inbe.v1.cells` collection must never be delegated.

Opening an owner profile queues existing Lumi settings for upload under the
new collection and saves `sync_lumi_collection_v2_done` in the same SQLite
savepoint. Existing settings, history and pending outbox entries are retained.
The marker makes restarts idempotent; a failed marker write rolls back the
queued copies so a restart can retry. A legacy Lumi record received later is
still decrypted with the old key, preserved locally, and queued under the new
key. The old combined collection remains readable by the owner so historical
Diary and feedback records continue to restore. Grant revocation cannot erase
plaintext or keys already received by a delegate; new grants and key generations
must be approved separately.
