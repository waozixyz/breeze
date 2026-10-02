-- Inbe 1.8.9 schema_create SQL, extracted from src/storage/db.c.
-- Upstream commit: 5cdfa63d6ad9989cc1d51af5edb1d067cf453176
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta( key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users( id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, kind TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings( user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at INTEGER NOT NULL, PRIMARY KEY(user_id,key));
CREATE TABLE IF NOT EXISTS social_snapshots( user_id TEXT NOT NULL, kind TEXT NOT NULL, json TEXT NOT NULL, updated_at INTEGER NOT NULL, PRIMARY KEY(user_id,kind));
CREATE TABLE IF NOT EXISTS sessions( id TEXT PRIMARY KEY, user_id TEXT NOT NULL, started_at INTEGER NOT NULL, local_date INTEGER NOT NULL, topic INTEGER NOT NULL DEFAULT 0, activity INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL, imported_at INTEGER NOT NULL, rounds_hash INTEGER NOT NULL, deleted_at INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0, UNIQUE(user_id,started_at,rounds_hash));
CREATE TABLE IF NOT EXISTS session_rounds( session_id TEXT NOT NULL, round_index INTEGER NOT NULL, seconds INTEGER NOT NULL, PRIMARY KEY(session_id,round_index));
CREATE TABLE IF NOT EXISTS meditation_logs( id TEXT PRIMARY KEY, user_id TEXT NOT NULL, session_id TEXT NOT NULL, duration_seconds INTEGER NOT NULL, completed_at INTEGER NOT NULL, updated_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS habits( id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', color_r INTEGER NOT NULL, color_g INTEGER NOT NULL, color_b INTEGER NOT NULL, sync_mode INTEGER NOT NULL, sync_activity INTEGER NOT NULL, counter_enabled INTEGER NOT NULL DEFAULT 0, sort_order INTEGER NOT NULL, deleted_at INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS habit_days( habit_id TEXT NOT NULL, local_date INTEGER NOT NULL, completed INTEGER NOT NULL, count INTEGER NOT NULL DEFAULT 0, session_count INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL, PRIMARY KEY(habit_id,local_date));
CREATE TABLE IF NOT EXISTS imports( id TEXT PRIMARY KEY, imported_at INTEGER NOT NULL, format TEXT NOT NULL, source_name TEXT NOT NULL, session_count INTEGER NOT NULL, habit_count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sync_outbox( seq INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, local_date INTEGER NOT NULL DEFAULT 0, queued_at INTEGER NOT NULL, UNIQUE(entity_type,entity_id,local_date));
CREATE TABLE IF NOT EXISTS sync_ops( op_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, seq INTEGER NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, local_date INTEGER NOT NULL DEFAULT 0, op_type TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, sent_at INTEGER NOT NULL DEFAULT 0, acked_at INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version','1');

