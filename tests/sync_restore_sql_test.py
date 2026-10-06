#!/usr/bin/env python3
"""Run the real account-restore SQL and check it against the restore laws.

src/storage/sync_restore_laws.zi proves that restoring an account cannot leave
a local change out of the upload queue, for a model of the restore. This test
runs the actual statements from storage_core.zi (clear the outbox, then queue
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
CORE = (ROOT / "src/storage/storage_core.zi").read_text()
SCHEMA = (ROOT / "src/storage/schema_sql.zi").read_text()

TABLES = ["users", "habits", "habit_days", "sessions", "elist_lists",
          "elist_items", "settings", "sync_outbox"]


def table_sql(name):
    match = re.search(r"CREATE TABLE IF NOT EXISTS " + name + r"\(.*?\);",
                      SCHEMA, re.S)
    assert match, name
    return match.group(0)


def restore_statements():
    reset = re.search(r"storage_reset_sync_state :: \(\) \{(.*?)\n\}", CORE, re.S)
    assert reset, "storage_reset_sync_state"
    clear = re.findall(r'exec_sql\("(DELETE FROM sync_outbox)"\)', reset.group(1))
    assert clear == ["DELETE FROM sync_outbox"], clear
    enqueue = re.search(r"storage_enqueue_all_sync_state :: \(\) \{(.*?)\n\}",
                        CORE, re.S)
    assert enqueue, "storage_enqueue_all_sync_state"
    inserts = re.findall(r'exec_sql\("(INSERT INTO sync_outbox[^"]*)"\)',
                         enqueue.group(1))
    assert len(inserts) == 6, inserts
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
    ("session", "s1", 0), ("elist_list", "l1", 0), ("elist_item", "i1", 0),
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
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_lists", "value": "0", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "app_used_diary", "value": "1", "updated_at": 2})
    insert_row(database, "settings", {"user_id": "u1", "key": "apps_auto_update", "value": "0", "updated_at": 2})
    return database


def outbox(database):
    return set(database.execute(
        "SELECT entity_type,entity_id,local_date FROM sync_outbox"))


def main():
    statements = restore_statements()
    local = set(ENTITIES)
    cases = 0
    for flags in itertools.product((0, 1), repeat=len(ENTITIES)):
        queued = {entity for entity, flag in zip(ENTITIES, flags) if flag}
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
