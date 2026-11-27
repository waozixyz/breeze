#!/usr/bin/env python3
"""Check the complete Inbe Ziran program against its pinned libraries."""

import fcntl
import os
import shlex
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parent.parent
compiler = Path(sys.argv[1]).resolve()
sources = sorted(path for path in (root / "src").rglob("*")
                 if path.suffix in {".zi", ".ts", ".tsx"})
sources.append(root / "apps/practice/src/native/hold_reminder.zi")
legacy = sorted((root / "src").rglob("*.kry"))

if legacy:
    for path in legacy:
        print(f"legacy source: {path.relative_to(root)}", file=sys.stderr)
    sys.exit(1)

if not sources:
    print("No Inbe native sources found", file=sys.stderr)
    sys.exit(1)

target_defines = os.environ.get("ZI_CHECK_DEFINES", "PLATFORM_DESKTOP").split()
# The browser payment view is imported by its native platform dispatcher only
# on web builds; checking it as a desktop root bypasses that platform boundary.
if "PLATFORM_WEB" not in target_defines:
    sources = [path for path in sources if path.name != "telegram_stars_view_ui.tsx"]
define_args = [part for name in target_defines for part in ("--define", name)]
# Native target constants select backend modules independently of defines.
# Match the artifact target so a web/Android check includes its actual backend.
target_args = []
if "PLATFORM_WEB" in target_defines:
    target_args = ["--target-os", "web", "--target-cpu", "wasm32"]
elif "ANDROID_BUILD" in target_defines:
    cpu_defines = {"__aarch64__": "arm64", "__x86_64__": "x64",
                   "__arm__": "none", "__i386__": "none"}
    target_cpu = next((cpu for name, cpu in cpu_defines.items()
                       if name in target_defines), "arm64")
    target_args = ["--target-os", "android", "--target-cpu", target_cpu]
(root / "build").mkdir(exist_ok=True)
compiler_lock = (root / "build/ziran-compiler.lock").open("a")
fcntl.flock(compiler_lock, fcntl.LOCK_EX)
subprocess.run([sys.executable, str(root / "scripts/stage-practice-figure.py")], cwd=root, check=True)
result = subprocess.run(
    [
        str(compiler),
        "check",
        "--project",
        "--offline",
        *shlex.split(os.environ.get("PACKAGE_FLAGS", "")),
        "--root",
        ".",
        "--module-path",
        str(root / "build/practice-figure"),
        *target_args,
        *define_args,
        *(str(source.relative_to(root)) for source in sources),
    ],
    cwd=root,
    capture_output=True,
    text=True,
    check=False,
)
compiler_lock.close()

if result.returncode == 0:
    print(f"Ziran checked {len(sources)} modules together: passed")
    sys.exit(0)

diagnostics = result.stderr.strip().splitlines()
print(f"Ziran checked {len(sources)} modules together: failed", file=sys.stderr)
if not diagnostics:
    print(f"Compiler exited with status {result.returncode} without a diagnostic",
          file=sys.stderr)
else:
    limit = len(diagnostics) if os.environ.get("ZI_CHECK_VERBOSE") == "1" else 30
    for line in diagnostics[:limit]:
        print(line, file=sys.stderr)
    if len(diagnostics) > limit:
        print(f"... {len(diagnostics) - limit} more diagnostic lines",
              file=sys.stderr)
sys.exit(result.returncode if result.returncode > 0 else 1)
