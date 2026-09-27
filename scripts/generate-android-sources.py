#!/usr/bin/env python3
"""Generate the complete checked Zi graph and its CMake source manifest."""
import argparse
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--compiler", type=Path, required=True)
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--kryon", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--define", action="append", default=[])
args = parser.parse_args()
root = args.root.resolve()
kryon = args.kryon.resolve()
sources = sorted((root / "src").rglob("*.zi"))
if list((root / "src").rglob("*.c")) or list((root / "src").rglob("*.kry")):
    raise SystemExit("Android application implementation must be current Zi")
if args.output.exists():
    shutil.rmtree(args.output)
args.output.mkdir(parents=True)
command = ["sh", str(root / "scripts/run-ziran.sh"), str(args.compiler),
           "--no-main", "--root", str(root)]
for name in args.define:
    command.extend(["--define", name])
for directory in (
    root / "src", kryon / "src/ui", kryon / "src/backend", kryon / "src/kss",
    root / "build/packages/game2d/src", root / "build/packages/ziran/std", root / "build/packages/daochi-client",
):
    command.extend(["--module-path", str(directory)])
command.extend(["-o", str(args.output)])
command.extend(str(path.relative_to(root)) for path in sources)
completed = subprocess.run(command, cwd=root)
if completed.returncode != 0:
    # The compiler already printed precise diagnostics; avoid repeating the
    # entire application source list inside a Python exception traceback.
    raise SystemExit(completed.returncode)
outputs = sorted(args.output.rglob("*.c"))
if not outputs:
    raise SystemExit("Zi compiler emitted no Android native sources")
headers = sorted(args.output.rglob("*.h"))
include_dirs = sorted({args.output, args.output / "src", *(p.parent for p in headers)})
lines = ["# Generated from the complete Zi import graph.", "set(APP_ZIRAN_GENERATED_SOURCES"]
lines.extend(f'    "{path}"' for path in outputs)
lines.extend([")", "set(APP_ZIRAN_GENERATED_HEADERS"])
lines.extend(f'    "{path}"' for path in headers)
lines.extend([")", "set(APP_ZIRAN_INCLUDE_DIRS"])
lines.extend(f'    "{path}"' for path in include_dirs)
lines.append(")\n")
content = "\n".join(lines)
args.manifest.parent.mkdir(parents=True, exist_ok=True)
if not args.manifest.exists() or args.manifest.read_text() != content:
    args.manifest.write_text(content)
print(f"Generated {len(outputs)} Android C outputs from maintained Zi sources")
