"""Verify the native artifact contains the exact independently built bundles."""

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
binary = Path(sys.argv[1]).resolve()
data = binary.read_bytes()
result = {
    "binary": str(binary),
    "sha256": hashlib.sha256(data).hexdigest(),
    "bundles": {},
    "deployment": False,
}
root_payload = (ROOT / "build/inbe.zib").read_bytes()
assert data.count(root_payload) == 1, "root payload missing or duplicated"
assert b"inbe.zib\0" in data, "root asset name missing"
result["root_bundle"] = {
    "sha256": hashlib.sha256(root_payload).hexdigest(),
    "bytes": len(root_payload),
    "embedded_identically": True,
}
for name in ("lists", "habits", "practice"):
    path = ROOT / "build/subapps" / f"{name}.zib"
    payload = path.read_bytes()
    assert data.count(payload) == 1, f"{name} payload missing or duplicated"
    assert root_payload.count(payload) == 1, f"{name} is not the root's exact nested payload"
    assert f"subapps/{name}.zib".encode() in root_payload, name
    result["bundles"][name] = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "embedded_identically": True,
    }

# A renamed generated path must not leave a second, stale codec/header pair.
generated = ROOT / "build/kryon/generated"
codecs = list(generated.rglob("value_codec.c"))
assert len(codecs) == 1, codecs
source = (ROOT / "src/subapps/lists_types.zi").read_text()
record = re.search(r"ListsMessage\s*::\s*struct\s*\{([^{}]*)\}", source)[1]
expected = len(re.findall(r"^\s*\w+\s*:", record, re.M))
encoder = re.search(
    r"\b(?:[A-Za-z0-9_]+_)?EncodeListsMessage\([^)]*\)\s*\{(.*?)\n\}",
    codecs[0].read_text(),
    re.S,
)
assert encoder, "Lists encoder missing"
actual = int(re.search(r"value.field_count = (\d+);", encoder[1])[1])
assert actual == expected, (actual, expected)
result["codec"] = {
    "path": str(codecs[0].relative_to(ROOT)),
    "sha256": hashlib.sha256(codecs[0].read_bytes()).hexdigest(),
    "lists_fields": actual,
}
output = ROOT / "build/subapps-artifact-test.json"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
print("Embedded bundles and generated Lists codec match the final sources")
