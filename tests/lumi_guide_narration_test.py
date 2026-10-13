#!/usr/bin/env python3
"""Lumi says every guide line in every language, as the line reads now.

Every key the guides name with GuideOverlayStepFor is a narrated line in
design/lumi-guide/narration.json and the other way round, and each line has
a clip generated from its current text in every locale. After changing a
guide line, run scripts/generate-lumi-guide-narration.py to speak it again.
The app reads each clip's length from its Ogg headers to pace the typing;
tests/ogg_length_behavior.zi checks that reader with the given ziran.

Usage: lumi_guide_narration_test.py [ZIRAN]
"""
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
ziran = sys.argv[1] if len(sys.argv) > 1 else str(root / "build/ziran-toolchain/bin/ziran")
config = json.loads((root / "design/lumi-guide/narration.json").read_text(encoding="utf-8"))
narrated = set(config["keys"])
named = set()
for source in (root / "src").rglob("*.zi"):
    text = source.read_text(encoding="utf-8")
    if "GuideOverlayStepFor(" not in text:
        continue
    named |= set(re.findall(r'"([a-z0-9]+(?:_[a-z0-9]+)*_guide_[a-z0-9_]+)"', text))
failures = []
for key in sorted(named - narrated):
    failures.append(f"guide line {key} has no voice; add it to design/lumi-guide/narration.json")
for key in sorted(narrated - named):
    failures.append(f"narration.json lists {key}, which no guide shows")
if len(named) < 12:
    failures.append(f"only {len(named)} guide lines found in the sources")
check = subprocess.run([sys.executable, str(root / "scripts/generate-lumi-guide-narration.py"),
                        "--check"], capture_output=True, text=True)
if check.returncode != 0:
    failures.append(check.stdout.strip() or check.stderr.strip())
work = root / "build/lumi-guide-test"
work.mkdir(parents=True, exist_ok=True)
bundle = work / "ogg_length.zib"
built = subprocess.run([ziran, "bundle", "--root", str(root / "tests"),
    "--module-path", str(root / "src"),
    "--module-path", str(root / "build/packages/ziran/std"),
    "--entry", "ogg_length_behavior:Answer", "-o", str(bundle),
    str(root / "tests/ogg_length_behavior.zi")], capture_output=True, text=True)
answer = built
if built.returncode == 0:
    answer = subprocess.run([ziran, "run", str(bundle)], capture_output=True,
                            text=True)
if answer.returncode != 0 or answer.stdout.strip() != "42":
    failures.append("the Ogg length reader failed: " +
                    (answer.stdout + answer.stderr).strip())
if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)
print(f"Lumi says all {len(narrated)} guide lines in every language")
