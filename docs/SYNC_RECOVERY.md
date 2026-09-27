# Sync recovery

Sync enablement records the user’s intent, not whether the last request succeeded.
The 1.9.19 connection setting is migrated without enabling disconnected accounts.
Restoring a key explicitly requests synchronization with the configured server.
Restoring the same key preserves upload cursors, migration completion, and local data.

Connect and Retry schedule the existing background worker. Temporary challenge and
request failures retry after 5, 15, 30, then at most 60 seconds. The last result and
attempt count survive restart; authentication, configuration, signing, and payload
failures require action. Logout and server changes disable synchronization and
clear retry state. Queued records remain until the server response is applied.

Data and Sync show actionable status and queued changes. Repair flags and server
cursors stay internal. Secure-data migration runs through the normal background
sync path, without an automatic blocking prompt, and completion is only recorded
after successful response application.

Friendships are retrieved from the server under the restored account identity.
Successful synchronization schedules social refresh. Temporary social failures
retry; failed leaderboard requests do not discard a fetched friend list or replace
cached leaderboard data with empty results. Restoring a different account cannot
recover friendships belonging to the original identity.

Native clients share a SQLite connection between the UI and sync workers. Settings
text uses a buffer per thread so a UI read cannot replace the recovery key during
decryption. Transactions hold the connection mutex through commit or rollback,
and habit ID reconciliation reuses a schema-created mapping table instead of
dropping and recreating a temporary table while another thread is reading.

Validation: `make sync-retry-zi-test` checks the proved retry policy across
Ziran backends. `make sync-recovery-test` covers the native coordinator once
the app source migration gate passes. The sync account/review and locale tests
cover their respective boundaries. Run
`DAOCHI_BIN=/path/to/daochi make sync-server-test` for the server flow. That test creates two
accounts with separate aliases, accepts a friendship, restores the first account's
exported key on fresh clients with and without pre-seeded default habits, and checks
that the alias, friend, custom habit, completed habit day, session, and check-in return.
It also drops an upload response to verify safe retry. Native screenshot scenes `sync_disconnected` and
`sync_retry` use disposable data and loopback configuration.
