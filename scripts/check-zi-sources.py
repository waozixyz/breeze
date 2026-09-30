#!/usr/bin/env python3
"""Check the complete Inbe Ziran program against its pinned libraries."""

import fcntl
import os
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parent.parent
compiler = Path(sys.argv[1]).resolve()
ui = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else root / "build/packages/kryon/src/ui"
standard = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else root / "build/packages/ziran/std"
kss = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else root / "build/packages/kss/src"
client = root / "build/packages/daochi-client"
game2d = root / "build/packages/game2d/src"
sources = sorted((root / "src").rglob("*.zi"))
legacy = sorted((root / "src").rglob("*.kry"))

if legacy:
    for path in legacy:
        print(f"legacy source: {path.relative_to(root)}", file=sys.stderr)
    sys.exit(1)

if not sources:
    print("No Inbe .zi sources found", file=sys.stderr)
    sys.exit(1)

target_defines = os.environ.get("ZI_CHECK_DEFINES", "PLATFORM_DESKTOP").split()
define_args = [part for name in target_defines for part in ("--define", name)]
(root / "build").mkdir(exist_ok=True)
compiler_lock = (root / "build/ziran-compiler.lock").open("a")
fcntl.flock(compiler_lock, fcntl.LOCK_EX)
result = subprocess.run(
    [
        str(compiler),
        "--check-only",
        "--root",
        ".",
        "--module-path",
        "src",
        "--module-path",
        str(ui),
        "--module-path",
        str(kss),
        "--module-path",
        str(root / "build/packages/oqs/src"),
        # KSS imports Kryon as kryon/NAME.
        "--module-path",
        f"kryon={ui}",
        "--module-path",
        str(ui.parent / "backend"),
        "--module-path",
        str(game2d),
        "--module-path",
        str(standard),
        "--module-path",
        str(client),
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
