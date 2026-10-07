#!/usr/bin/env python3
"""Exercise the real SQL for per-app merge, removals and device-only settings."""
import json
from pathlib import Path
import re
import sqlite3

root = Path(__file__).resolve().parent.parent
source = (root / "src/storage/sync_sql.zi").read_text()
sql = re.search(r"SyncAppPreferencesSQL :: #string SQL\n(.*?)\nSQL", source, re.S)[1]
schema = (root / "src/storage/schema_sql.zi").read_text()
database = sqlite3.connect(":memory:")
for table in ("settings", "sync_outbox"):
    database.execute(re.search(r"CREATE TABLE IF NOT EXISTS " + table + r"\(.*?\);", schema, re.S)[0])
keys = ("app_used_lists", "app_used_habits", "app_used_practices", "app_used_diary", "app_used_lumi")
for key in keys:
    database.execute("INSERT INTO settings VALUES('account',?,?,100)", (key, "1"))
database.execute("INSERT INTO settings VALUES('account','cells_auto_update','0',100)")
database.execute("INSERT INTO settings VALUES('account','package_sequence_diary','10',100)")
database.execute("INSERT INTO settings VALUES('other-account','app_used_diary','1',100)")


def merge(key, value, timestamp):
    record = dict(key=key, value=value, updated_at=timestamp)
    database.execute(sql, (json.dumps(dict(changes=dict(app_preferences=[record]))), "account"))


def value(key, user="account"):
    return database.execute("SELECT value FROM settings WHERE user_id=? AND key=?", (user, key)).fetchone()[0]


# An app deselection propagates as a value; its saved data is not deleted.
merge("app_used_diary", "0", "1970-01-01T00:03:20Z")
assert value("app_used_diary") == "0"
assert value("app_used_diary", "other-account") == "1"
merge("app_used_diary", "1", "1970-01-01T00:01:40Z")
assert value("app_used_diary") == "0", "older remote choice resurrected an app"
# Local pending changes win equal timestamps; a newer remote change wins.
database.execute("INSERT INTO sync_outbox(entity_type,entity_id,local_date,queued_at) VALUES('app_preference','app_used_habits',0,100)")
merge("app_used_habits", "0", "1970-01-01T00:01:40Z")
assert value("app_used_habits") == "1"
merge("app_used_habits", "0", "1970-01-01T00:05:00Z")
assert value("app_used_habits") == "0"
assert value("app_used_lists") == "1", "merging one app replaced another app's choice"
merge("cells_auto_update", "1", "1970-01-01T00:10:00Z")
merge("package_sequence_diary", "1", "1970-01-01T00:10:00Z")
merge("app_used_lists", "99", "1970-01-01T00:10:00Z")
merge("app_used_practices", "0", "invalid")
assert value("cells_auto_update") == "0"
assert value("package_sequence_diary") == "10"
assert value("app_used_lists") == "1"
assert value("app_used_practices") == "1"
print("Account app choices: removals, independent merge, conflict handling, account isolation and device settings passed")
