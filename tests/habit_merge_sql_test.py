#!/usr/bin/env python3
"""Run the real habit-day merge SQL and check it against the merge laws.

src/storage/habit_merge_laws.zi proves the laws for a model of the merge. The
SQL is what actually runs, so this test executes it on every pair of 3-day
sequences with values 0..2 (a missing day counts as 0) and requires exactly
the behavior the laws state: the larger value for every day, nothing lost and
nothing invented, for both merge paths.
"""
import itertools
import pathlib
import re
import sqlite3
import sys

import os

ROOT = pathlib.Path(os.environ.get("HABIT_MERGE_ROOT") or
                    pathlib.Path(__file__).resolve().parent.parent)
SYNC = (ROOT / "src/storage/storage_habit_sync.zi").read_text()
SQLS = (ROOT / "src/storage/habit_sync_sql.zi").read_text()
SCHEMA = (ROOT / "src/storage/schema_sql.zi").read_text()


def zi_string_block(text, name):
    match = re.search(name + r" :: #string SQL\n(.*?)\nSQL\n", text, re.S)
    assert match, name
    return match.group(1)


def merge_statements():
    match = re.search(r"storage_merge_habit_into_sqls: \[4\] string = \.\[(.*?)\];",
                      SYNC, re.S)
    assert match, "storage_merge_habit_into_sqls"
    statements = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
    assert len(statements) == 4, statements
    return statements


def schema_table(name):
    match = re.search(r"CREATE TABLE IF NOT EXISTS " + name + r"\(.*?\);",
                      SCHEMA, re.S)
    assert match, name
    return match.group(0)


DAYS = 3
VALUES = range(3)


def open_database():
    database = sqlite3.connect(":memory:")
    database.execute("CREATE TABLE habits(id TEXT PRIMARY KEY)")
    database.execute(schema_table("habit_days"))
    database.execute(schema_table("sync_remote_habit_map"))
    return database


def load(database, habit, sequence):
    database.execute("INSERT OR IGNORE INTO habits(id) VALUES (?)", (habit,))
    for day, value in enumerate(sequence):
        if value:
            database.execute(
                "INSERT INTO habit_days VALUES (?,?,?,?,?,?)",
                (habit, day, value, value, value, value))


def read(database, habit):
    rows = {day: row for day, *row in database.execute(
        "SELECT local_date,completed,count,session_count,updated_at "
        "FROM habit_days WHERE habit_id=?", (habit,))}
    return [rows.get(day, [0, 0, 0, 0]) for day in range(DAYS)]


def expected(mine, theirs):
    return [[max(a, b)] * 4 for a, b in zip(mine, theirs)]


def check(kind, mine, theirs, database):
    merged = read(database, "keeper")
    want = expected(mine, theirs)
    assert merged == want, (kind, mine, theirs, merged, want)


def merge_into(statements, database):
    for statement in statements:
        database.execute(statement.replace("?1", "'keeper'").replace("?2", "'dupe'"))


def merge_remote(database):
    database.execute("INSERT INTO sync_remote_habit_map VALUES ('dupe','keeper')")
    database.execute(zi_string_block(SQLS, "MergeRemoteHabitDaysSQL"))
    database.execute(zi_string_block(SQLS, "InsertRemoteHabitDaysSQL"))


def main():
    statements = merge_statements()
    cases = 0
    for mine in itertools.product(VALUES, repeat=DAYS):
        for theirs in itertools.product(VALUES, repeat=DAYS):
            database = open_database()
            load(database, "keeper", mine)
            load(database, "dupe", theirs)
            merge_into(statements, database)
            check("merge_into", mine, theirs, database)
            assert read(database, "dupe") == [[0, 0, 0, 0]] * DAYS, "duplicate kept"
            database = open_database()
            load(database, "keeper", mine)
            load(database, "dupe", theirs)
            merge_remote(database)
            check("remote", mine, theirs, database)
            cases += 1
    print(f"habit merge SQL agrees with the merge laws on {cases} cases")


if __name__ == "__main__":
    sys.exit(main())
