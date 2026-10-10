#!/usr/bin/env python3
"""Generate installed baseline versions from the independent app ledger."""
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
ledger = json.loads((root / "apps/versions.json").read_text())
names = ("inbe", "lists", "habits", "practices", "diary", "lumi", "leaderboard")
apps = ledger["apps"]
for name in names:
    value = apps[name]
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})", value["version"]):
        raise SystemExit(f"invalid {name} version")
    if type(value["sequence"]) is not int or not 0 < value["sequence"] <= 2147483647:
        raise SystemExit(f"invalid {name} sequence")
lines = ["// Generated from apps/versions.json; module releases are independent.",
         "PackageBundledVersion :: (index: s32) -> string {",
         f"    if index < 0 || index >= {len(names)} {{", "        return \"\"", "    }",
         f"    versions: [{len(names)}]string = .[" + ", ".join(json.dumps(apps[n]["version"]) for n in names) + "]",
         "    return versions[index]", "}", "",
         "PackageBundledSequence :: (index: s32) -> s32 {",
         f"    if index < 0 || index >= {len(names)} {{", "        return 0", "    }",
         f"    sequences: [{len(names)}]s32 = .[" + ", ".join(str(apps[n]["sequence"] if apps[n]["bundled"] else 0) for n in names) + "]",
         "    return sequences[index]", "}", ""]
path = root / "src/cells/versions.zi"
content = "\n".join(lines)
if not path.exists() or path.read_text() != content:
    path.write_text(content)
