#!/usr/bin/env python3
"""Synced records may only gain fields together with STORAGE_SYNC_RECORD_FIELDS.

A device keeps only the fields its app version reads from a record. When a
newer version reads more, raising STORAGE_SYNC_RECORD_FIELDS makes every
device download its records again once, so it gets the new fields. This
check records the fields read for the current value and fails when they
change without it.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests/sync_record_fields.txt"


def read_fields():
    fields = set()
    for path in sorted((ROOT / "src/storage").glob("*.zi")):
        fields.update(re.findall(r"json_extract\(value,\s*'\$\.([A-Za-z_][A-Za-z0-9_.]*)'\)", path.read_text()))
    return fields


def current_version():
    core = (ROOT / "src/storage/storage_core.zi").read_text()
    return int(re.search(r"^STORAGE_SYNC_RECORD_FIELDS :: (\d+)$", core, re.M)[1])


def main():
    fields = read_fields()
    version = current_version()
    if "--record" in sys.argv:
        RECORDED.write_text(f"version {version}\n" + "".join(f"{name}\n" for name in sorted(fields)))
        return 0
    lines = RECORDED.read_text().split()
    recorded_version = int(lines[1])
    recorded = set(lines[2:])
    if recorded_version == version and recorded == fields:
        print(f"Synced record fields: {len(fields)} fields for record version {version}")
        return 0
    added = sorted(fields - recorded)
    removed = sorted(recorded - fields)
    if recorded_version == version:
        print("Synced record fields changed without raising STORAGE_SYNC_RECORD_FIELDS "
              f"(src/storage/storage_core.zi): added {added}, removed {removed}. Raise it so "
              "devices download their records again, then run "
              "python3 tests/sync_record_fields_test.py --record", file=sys.stderr)
    else:
        print("STORAGE_SYNC_RECORD_FIELDS changed; record its fields with "
              "python3 tests/sync_record_fields_test.py --record", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
