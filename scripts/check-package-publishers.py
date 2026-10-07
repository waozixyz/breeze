#!/usr/bin/env python3
"""Keep release wrappers from shipping an unconfigured optional app catalog."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
publishers = json.loads((root / "apps/publishers.json").read_text())
required = {value["id"] for value in json.loads((root / "apps/versions.json").read_text())["apps"].values()}
if not isinstance(publishers, list) or not 0 < len(publishers) <= 32:
    raise SystemExit("Release requires registered public publisher pins in apps/publishers.json; see docs/cells.md")
covered = set()
seen = set()
for publisher in publishers:
    if not isinstance(publisher, dict):
        raise SystemExit("Publisher entries must be JSON objects")
    key_id = publisher.get("key_id", "")
    public = publisher.get("public_key", "")
    apps = publisher.get("app_ids", [])
    if not isinstance(key_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", key_id) or key_id in (".", "..") or key_id in seen:
        raise SystemExit("Invalid or duplicate publisher key ID")
    if not isinstance(public, str) or not re.fullmatch(r"[0-9a-f]{64}", public) or public == "0" * 64:
        raise SystemExit("Publisher public key must be 32 bytes in lowercase hexadecimal")
    if not isinstance(apps, list) or not apps or any(not isinstance(app, str) or app not in required for app in apps):
        raise SystemExit("Publisher must be scoped to known Inbe app IDs")
    covered.update(apps)
    seen.add(key_id)
if covered != required:
    raise SystemExit("Release requires publisher coverage for the root and all five cells")
print("Publisher pins cover the root and all five cells")
