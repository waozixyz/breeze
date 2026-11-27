#!/usr/bin/env python3
"""Generate the complete checked Zi graph and its CMake source manifest."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

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
sources = sorted(path for path in (root / "src").rglob("*")
                 if path.suffix in {".zi", ".ts", ".tsx"}
                 and path.name != "telegram_stars_view_ui.tsx")
sources.append(root / "apps/practice/hold_reminder.zi")
# Kryon's Android link wraps fopen; its wrapper serves relative names from the
# APK's assets and is a host root of its own, as Kryon's generator adds it.
sources.append(kryon / "src/backend/android_fopen.zi")
if list((root / "src").rglob("*.c")) or list((root / "src").rglob("*.kry")):
    raise SystemExit("Android application implementation must be current Zi")
subprocess.run([sys.executable, str(root / "scripts/stage-practice-figure.py")], cwd=root, check=True)
# The compiler writes every file anew. Outputs with the same bytes as before
# get their earlier times back, so the native build recompiles only changes.
previous = args.output.with_name(args.output.name + ".previous")
if previous.exists():
    shutil.rmtree(previous)
if args.output.exists():
    args.output.rename(previous)
args.output.mkdir(parents=True)
command = ["sh", str(root / "scripts/run-ziran.sh"), str(args.compiler),
           "build", "--target=c", "--no-main", "--project", "--offline",
           "--root", str(root), "--module-path",
           str(root / "build/practice-figure")]
for name in args.define:
    command.extend(["--define", name])
# Ziran selects platform code by its target, not by C preprocessor defines:
# name Android and the ABI's CPU so the standard library takes its Bionic
# branches instead of the host's glibc ones, as Kryon's generator does.
cpu_defines = {
    "__aarch64__": "arm64",
    "__x86_64__": "x64",
    "__arm__": "none",
    "__i386__": "none",
}
target_cpus = {cpu_defines[name] for name in args.define if name in cpu_defines}
if len(target_cpus) != 1:
    parser.error("select exactly one Android CPU define (__aarch64__, __arm__, __x86_64__ or __i386__)")
command.extend(["--target-os", "android", "--target-cpu", target_cpus.pop()])
command.extend(["-o", str(args.output)])
command.extend(str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
               for path in sources)
completed = subprocess.run(command, cwd=root)
if completed.returncode != 0:
    # The compiler already printed precise diagnostics; avoid repeating the
    # entire application source list inside a Python exception traceback.
    raise SystemExit(completed.returncode)
for output in args.output.rglob("*"):
    earlier = previous / output.relative_to(args.output)
    if output.is_file() and earlier.is_file() and output.read_bytes() == earlier.read_bytes():
        times = earlier.stat()
        os.utime(output, ns=(times.st_atime_ns, times.st_mtime_ns))
if previous.exists():
    shutil.rmtree(previous)
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
