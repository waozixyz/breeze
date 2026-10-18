#!/usr/bin/env python3
"""Run the real account-restore SQL and check it against the restore laws.

src/storage/sync_restore_laws.zi proves that restoring an account cannot leave
a local change out of the upload queue, for a model of the restore. This test
runs the actual statements from sync_outbox.zi (clear the outbox, then queue
all local data) on every subset of already-queued entities, and requires that
every local entity, including soft-deleted ones, is queued afterward and that
nothing else is.
"""
import itertools
import os
import pathlib
import re
import sqlite3
import sys

ROOT = pathlib.Path(os.environ.get("SYNC_RESTORE_ROOT") or
                    pathlib.Path(__file__).resolve().parent.parent)
OUTBOX = (ROOT / "src/storage/sync_outbox.zi").read_text()
SCHEMA = (ROOT / "src/storage/schema_sql.zi").read_text()

TABLES = ["users", "habits", "habit_days", "habit_entries", "habit_changes", "sessions", "elist_lists",
          "elist_items", "settings", "sync_outbox"]


def table_sql(name):
    match = re.search(r"CREATE TABLE IF NOT EXISTS " + name + r"\(.*?\);",
                      SCHEMA, re.S)
    assert match, name
    return match.group(0)


def restore_statements():
    reset = re.search(r"storage_reset_sync_state :: \(\) \{(.*?)\n\}", OUTBOX, re.S)
    assert reset, "storage_reset_sync_state"
    clear = re.findall(r'exec_sql\("(DELETE FROM sync_outbox)"\)', reset.group(1))
    assert clear == ["DELETE FROM sync_outbox"], clear
    enqueue = re.search(r"storage_enqueue_all_sync_state :: \(\) \{(.*?)\n\}",
                        OUTBOX, re.S)
    assert enqueue, "storage_enqueue_all_sync_state"
    inserts = re.findall(r'exec_sql\("(INSERT INTO sync_outbox[^"]*)"\)',
                         enqueue.group(1))
    assert len(inserts) == 14, inserts
    return clear + inserts


def insert_row(database, table, values):
    columns = database.execute(f"PRAGMA table_info({table})").fetchall()
    row = dict(values)
    for _, name, kind, notnull, default, _ in columns:
        if name not in row and notnull and default is None:
            row[name] = "x" if "TEXT" in kind.upper() else 0
    names = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    database.execute(f"INSERT INTO {table}({names}) VALUES ({marks})",
                     list(row.values()))


ENTITIES = [
    ("habit", "h1", 0), ("habit", "h2", 0), ("habit_day", "h1", 20260101),
    ("app_preference", "app_used_lists", 0), ("app_preference", "app_used_diary", 0),
    ("app_order", "app_order", 0),
    ("session", "s1", 0), ("elist_list", "l1", 0), ("elist_item", "i1", 0),
    ("habit_entry", "e1", 0), ("habit_change", "c1", 0),
    ("cell_record", "cell.lumi.message.history", 0),
    ("cell_record", "cell.diary.entry.today", 0),
    ("cell_record", "cell.feedback.report", 0),
]

# Apps the node offers and the account's media library: queued all or none,
# alternating over the cases above, so the exhaustive check stays small.
NESTED = "nested." + "ab" * 32 + ".position"
EXTRA = [
    ("app_record", NESTED, 0),
    ("app_install", "app_used_chess", 0),
    ("app_record", "cell.chess.computer", 0),
    ("media_record", "cell.media." + "ab" * 32, 0),
    ("media_record", "cell.media.preview." + "ab" * 32, 0),
]


def open_database():
    database = sqlite3.connect(":memory:")
    for table in TABLES:
        database.execute(table_sql(table))
    insert_row(database, "users", {"id": "u1"})
    insert_row(database, "habits", {"id": "h1", "user_id": "u1", "deleted_at": 0})
    insert_row(database, "habits", {"id": "h2", "user_id": "u1", "deleted_at": 5})
    insert_row(database, "habit_days",
               {"habit_id": "h1", "local_date": 20260101})
    insert_row(database, "sessions", {"id": "s1", "user_id": "u1"})
    insert_row(database, "elist_lists", {"id": "l1", "user_id": "u1"})
    insert_row(database, "elist_items", {"id": "i1", "user_id": "u1"})
    insert_row(database, "habit_entries",
               {"id": "e1", "user_id": "u1", "habit_id": "h1", "local_date": 20260101})
    insert_row(database, "habit_changes",
               {"id": "c1", "user_id": "u1", "habit_id": "h1", "changed_at": 1, "kind": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_lists", "value": "0", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_diary", "value": "1", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "cells_auto_update", "value": "0", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "app_order", "value": "lumi,diary", "updated_at": 2})
    # A default nobody chose is never queued.
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_leaderboard", "value": "0", "updated_at": 1})
    for key in ("cell.lumi.message.history", "cell.diary.entry.today", "cell.feedback.report"):
        insert_row(database, "settings", {"user_id": "u1", "key": key, "value": "{}", "updated_at": 2})
    # Apps the node offers and the account's media library, each in its
    # own collection; the library is never taken for an app's records.
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_chess", "value": "1", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "cell.chess.computer", "value": "x", "updated_at": 2})
    for key in ("cell.media." + "ab" * 32, "cell.media.preview." + "ab" * 32):
        insert_row(database, "settings", {"user_id": "u1", "key": key, "value": "{}", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": NESTED, "value": "saved", "updated_at": 2})
    for key in ("nested." + "ag" * 32 + ".position", "nested." + "ab" * 32 + ".",
                "nested." + "ab" * 32 + ".Big", "app_used_achievement"):
        insert_row(database, "settings", {"user_id": "u1", "key": key, "value": "1", "updated_at": 2})
    insert_row(database, "users", {"id": "u2"})
    insert_row(database, "settings", {"user_id": "u2", "key": "nested." + "cd" * 32 + ".position", "value": "foreign", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u2", "key": "cell.lumi.message.foreign", "value": "{}", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "telegram.sent.local", "value": "1", "updated_at": 2})
    return database


def outbox(database):
    return set(database.execute(
        "SELECT entity_type,entity_id,local_date FROM sync_outbox"))


def main():
    statements = restore_statements()
    # Dedicated achievement records never become generic installed-app data.
    database = open_database()
    insert_row(database, "settings", {"user_id": "u1", "key": "cell.achievement.photo", "value": "{}", "updated_at": 2})
    for statement in statements:
        if "SELECT 'app_record'" in statement or "SELECT 'app_install'" in statement:
            database.execute(statement)
    assert not any(identifier in ("cell.achievement.photo", "app_used_achievement")
                   for _, identifier, _ in outbox(database))
    database.close()
    local = set(ENTITIES) | set(EXTRA)
    cases = 0
    for flags in itertools.product((0, 1), repeat=len(ENTITIES)):
        queued = {entity for entity, flag in zip(ENTITIES, flags) if flag}
        if cases % 2 == 1:
            queued |= set(EXTRA)
        database = open_database()
        for kind, identifier, date in queued:
            database.execute(
                "INSERT INTO sync_outbox(entity_type,entity_id,local_date,"
                "queued_at) VALUES (?,?,?,1)", (kind, identifier, date))
        for statement in statements:
            database.execute(statement)
        after = outbox(database)
        assert local <= after, ("local change left unqueued", queued, local - after)
        assert after <= local, ("invented entry", queued, after - local)
        cases += 1
    print(f"account restore SQL agrees with the restore laws on {cases} cases")


if __name__ == "__main__":
    sys.exit(main())
