#!/usr/bin/env python3
"""Compile and run the QR device link protocol checks with Monocypher."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
ziran = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin/ziran"
liboqs = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"

with tempfile.TemporaryDirectory(prefix="inbe-device-link-") as temporary:
    generated = Path(temporary) / "generated"
    subprocess.run([
        str(ziran), "build", "--target=c", "--define", "PLATFORM_DESKTOP", "--root", str(ROOT / "tests"),
        "--module-path", str(ROOT / "src"),
        "--module-path", str(ROOT / "build/packages/ziran/std"),
        "--module-path", str(ROOT / "build/packages/daochi-client"),
        *subprocess.check_output(["sh", str(ROOT / "scripts/package-paths.sh"), str(ROOT / "build/packages")], text=True).split(),
        "--entry", "device_link_behavior:Check",
        "-o", str(generated), str(ROOT / "tests/device_link_behavior.zi"),
    ], check=True)
    (generated / "main.c").write_text(
        '#include "device_link_behavior.h"\n#include <stdio.h>\n'
        'int main(void) { int result = Check(); if (result) fprintf(stderr, "device link check %d failed\\n", result); return result != 0; }\n')
    monocypher = ROOT / "build/packages/monocypher/src"
    executable = Path(temporary) / "test"
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-O1",
        f"-I{ROOT / 'build/packages/ziran/include'}", f"-I{generated}",
        f"-I{ROOT / 'vendor-builds/linux/x86_64/inbe-liboqs/include'}",
        *sorted(str(path) for path in generated.rglob("*.c")),
        str(monocypher / "monocypher.c"), str(liboqs), "-lpthread", "-o", str(executable),
    ], check=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")}
    subprocess.run([str(executable)], check=True, env=environment)
print("Device link codes, confirmation digits and sealed accounts passed")
