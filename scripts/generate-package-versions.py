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
for api in ("host_api", "oldest_host_api", "module_api"):
    if type(ledger.get(api)) is not int or not 0 < ledger[api] <= 65535:
        raise SystemExit(f"invalid {api}")
# The interfaces are compiled host behavior, so they live apart from the
# package versions and changing them triggers an app release.
interfaces = "\n".join([
    "// Generated from apps/versions.json. This host runs packages built for host",
    "// interfaces from the oldest to the current one; module interfaces must match.",
    f"PackageHostAPI :: {ledger['host_api']}",
    f"PackageHostAPIOldest :: {ledger['oldest_host_api']}",
    f"PackageModuleAPI :: {ledger['module_api']}", ""])
interface_path = root / "src/apps/host_api.zi"
if not interface_path.exists() or interface_path.read_text() != interfaces:
    interface_path.write_text(interfaces)
lines = ["// Generated from apps/versions.json; module releases are independent.",
         "PackageBundledVersion :: (index: s32) -> string {",
         f"    if index < 0 || index >= {len(names)} {{", "        return \"\"", "    }",
         f"    versions: [{len(names)}]string = .[" + ", ".join(json.dumps(apps[n]["version"]) for n in names) + "]",
         "    return versions[index]", "}", "",
         "PackageBundledSequence :: (index: s32) -> s32 {",
         f"    if index < 0 || index >= {len(names)} {{", "        return 0", "    }",
         f"    sequences: [{len(names)}]s32 = .[" + ", ".join(str(apps[n]["sequence"] if apps[n]["bundled"] else 0) for n in names) + "]",
         "    return sequences[index]", "}", "",
         "// The oldest host interface a package of each app may be built for. An",
         "// app whose screens moved into its package needs a package that draws",
         "// them; an older one gives way to the bundled copy.",
         "PackageHostAPIOldestFor :: (index: s32) -> s32 {",
         f"    if index < 0 || index >= {len(names)} {{", f"        return {ledger['oldest_host_api']}", "    }",
         f"    oldest: [{len(names)}]s32 = .[" + ", ".join(str(apps[n].get("oldest_host_api", ledger["oldest_host_api"])) for n in names) + "]",
         "    return oldest[index]", "}", ""]
path = root / "src/apps/versions.zi"
content = "\n".join(lines)
if not path.exists() or path.read_text() != content:
    path.write_text(content)
