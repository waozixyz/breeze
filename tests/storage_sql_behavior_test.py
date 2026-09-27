#!/usr/bin/env python3
"""Exercise checked Ziran sync and export SQL against a real SQLite database."""

import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]


def load_sql(module):
    lines = (ROOT / "src/storage" / module).read_text().splitlines()
    queries = {}
    index = 0
    while index < len(lines):
        if lines[index].endswith(" :: #string SQL"):
            name = lines[index].split()[0]
            body = []
            index += 1
            while index < len(lines) and lines[index] != "SQL":
                body.append(lines[index])
                index += 1
            assert index < len(lines), f"unterminated SQL: {name}"
            queries[name] = "\n".join(body)
        index += 1
    return queries


sql = load_sql("sync_sql.zi") | load_sql("export_sql.zi") | load_sql("habit_sync_sql.zi")
db = sqlite3.connect(":memory:")
db.executescript(
    """
    CREATE TABLE sessions(
        id TEXT PRIMARY KEY, user_id TEXT, started_at INTEGER,
        local_date INTEGER, topic INTEGER, activity INTEGER, source TEXT,
        imported_at INTEGER, rounds_hash INTEGER, mood_before INTEGER,
        mood_after INTEGER, energy INTEGER, stress INTEGER, note TEXT,
        tags TEXT, deleted_at INTEGER, updated_at INTEGER);
    CREATE TABLE session_rounds(
        session_id TEXT, round_index INTEGER, seconds INTEGER);
    CREATE TABLE meditation_logs(
        id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT,
        duration_seconds INTEGER, completed_at INTEGER, updated_at INTEGER);
    CREATE TABLE social_snapshots(
        user_id TEXT, kind TEXT, json TEXT, updated_at INTEGER,
        PRIMARY KEY(user_id, kind));
    CREATE TABLE sync_outbox(
        entity_type TEXT, entity_id TEXT, local_date INTEGER);
    CREATE TABLE habits(
        id TEXT PRIMARY KEY, user_id TEXT, name TEXT, color_r INTEGER,
        color_g INTEGER, color_b INTEGER, sync_mode INTEGER,
        sync_activity INTEGER, counter_enabled INTEGER,
        counter_target INTEGER, sort_order INTEGER, deleted_at INTEGER,
        updated_at INTEGER, weekdays INTEGER, reminder_hour INTEGER);
    CREATE TABLE habit_days(
        habit_id TEXT, local_date INTEGER, completed INTEGER,
        count INTEGER, session_count INTEGER, updated_at INTEGER,
        PRIMARY KEY(habit_id, local_date));
    CREATE TABLE sync_remote_habit_map(
        old_id TEXT PRIMARY KEY, new_id TEXT);
    """
)
db.execute(
    "INSERT INTO sessions(id,user_id,activity,updated_at,deleted_at) "
    "VALUES('local','user',3,2000000000,0)"
)
db.execute("INSERT INTO session_rounds VALUES('local',0,999)")
db.execute("INSERT INTO sync_outbox VALUES('session','local',0)")
db.execute(
    "INSERT INTO sessions(id,user_id,activity,updated_at,deleted_at) "
    "VALUES('deleted','user',2,1,1)"
)
response = json.dumps(
    {
        "changes": {
            "sessions": [
                {
                    "id": "remote", "started_at": "2026-09-26T12:00:00Z",
                    "updated_at": "2026-09-26T12:00:00Z",
                    "local_date": 20260926, "activity": 1,
                    "rounds": [{"round_index": 0, "hold_seconds": 80}],
                },
                {
                    "id": "local", "started_at": "2026-09-26T12:00:00Z",
                    "updated_at": "2026-09-26T12:00:00Z",
                    "local_date": 20260926, "activity": 1,
                    "rounds": [{"round_index": 0, "hold_seconds": 80}],
                },
            ],
            "meditation_logs": [
                {
                    "id": "log1", "session_id": "remote",
                    "duration_seconds": 300,
                    "completed_at": "2026-09-26T12:05:00Z",
                }
            ],
            "social_cache": [
                {"kind": "friends", "json": "{}",
                 "updated_at": "2026-09-26T12:00:00Z"}
            ],
        },
        "data": {"sessions": [], "meditation_logs": [], "social": []},
    }
)
for name in (
    "SyncSessionRoundDeleteSQL", "SyncSessionRoundsSQL", "SyncSessionsSQL",
    "SyncMeditationLogsSQL", "SyncSocialSQL", "SyncSocialCacheSQL",
):
    arguments = (response, "user") if "?2" in sql[name] else (response,)
    db.execute(sql[name], arguments)

assert db.execute(
    "SELECT activity,local_date FROM sessions WHERE id='remote'"
).fetchone() == (1, 20260926)
assert db.execute(
    "SELECT seconds FROM session_rounds WHERE session_id='remote'"
).fetchone() == (80,)
assert db.execute(
    "SELECT activity FROM sessions WHERE id='local'"
).fetchone() == (3,), "newer local edit was overwritten"
assert db.execute(
    "SELECT seconds FROM session_rounds WHERE session_id='local'"
).fetchone() == (999,), "newer local rounds were overwritten"
assert db.execute(
    "SELECT duration_seconds FROM meditation_logs WHERE id='log1'"
).fetchone() == (300,)
assert db.execute(
    "SELECT kind FROM social_snapshots"
).fetchone() == ("friends",)
assert [row[1] for row in db.execute(sql["ExportSessionsSQL"])] == [3, 1]
assert [(row[1], row[2]) for row in db.execute(sql["ExportHealthConnectSQL"])] == [
    (3, 999), (1, 300)
]

db.execute(
    "INSERT INTO habits(id,user_id,name,deleted_at,updated_at) "
    "VALUES('old-habit','user','Walking',0,2000000000)"
)
db.execute("INSERT INTO habit_days VALUES('old-habit',20260925,1,3,0,2000000000)")
db.execute("INSERT INTO sync_outbox VALUES('habit','old-habit',0)")
habit_response = json.dumps(
    {
        "changes": {
            "habits": [
                {"id": "new-habit", "name": "Walking", "updated_at": "2026-09-26T12:00:00Z"}
            ],
            "habit_days": [
                {"habit_id": "new-habit", "local_date": 20260926,
                 "completed": 1, "count": 2,
                 "updated_at": "2026-09-26T12:00:00Z"}
            ],
        },
        "data": {"habits": [], "habit_days": []},
    }
)
db.execute(sql["SyncHabitsSQL"], (habit_response, "user"))
db.execute(sql["SyncHabitDaysSQL"], (habit_response,))
db.execute(sql["SyncRemoteHabitMapSQL"], (habit_response,))
assert db.execute("SELECT old_id,new_id FROM sync_remote_habit_map").fetchone() == (
    "old-habit", "new-habit"
)
db.execute(sql["MergeRemoteHabitDaysSQL"])
db.execute(sql["InsertRemoteHabitDaysSQL"])
db.executescript(sql["FinishRemoteHabitIDsSQL"])
assert db.execute("SELECT id FROM habits WHERE id='old-habit'").fetchone() is None
assert db.execute(
    "SELECT count FROM habit_days WHERE habit_id='new-habit' AND local_date=20260925"
).fetchone() == (3,)
assert db.execute(
    "SELECT count FROM habit_days WHERE habit_id='new-habit' AND local_date=20260926"
).fetchone() == (2,)
assert db.execute(
    "SELECT entity_id FROM sync_outbox WHERE entity_type='habit'"
).fetchone() == ("new-habit",)

print("Ziran sync SQL preserved local edits, reconciled habits, and omitted deleted exports")
