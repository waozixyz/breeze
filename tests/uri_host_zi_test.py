#!/usr/bin/env python3
"""Verify native URI dispatch using the capture path, without opening a display."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin"
WORK = ROOT / "build/uri-host-zi-test"
GEN = WORK / "native"
GEN.mkdir(parents=True, exist_ok=True)
subprocess.run([
    str(BIN / "zi2c"), "--no-main", "--root", str(ROOT),
    "--module-path", str(ROOT / "vendor/ziran/std"), "-o", str(GEN),
    str(ROOT / "src/platform/uri_host.zi"), str(ROOT / "src/platform/uri.zi"),
    str(ROOT / "src/platform/android/activity_jni.zi"),
    str(ROOT / "vendor/ziran/std/c_string.zi"),
], check=True)
files = sorted(GEN.rglob("*.c"))
includes = ["-I" + str(ROOT / "src"), "-I" + str(ROOT / "vendor/ziran/include"), "-I" + str(GEN), "-I" + str(GEN / "src")]
includes += ["-I" + str(path) for path in sorted({p.parent for p in GEN.rglob("*.h")})]
environment = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY"):
    environment.pop(name, None)
for test in ("uri_host_test", "uri_link_test"):
    executable = WORK / test
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-D_DEFAULT_SOURCE",
        "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
        *includes, str(ROOT / "tests" / (test + ".c")), *map(str, files),
        "-o", str(executable),
    ], check=True)
    subprocess.run([str(executable)], env=environment, check=True)
for define in ("_WIN32", "PLATFORM_WEB", "KRYON_BACKEND_LIBDRAW", "__APPLE__"):
    subprocess.run([
        str(BIN / "zi2c"), "--no-main", "--root", str(ROOT / "src"),
        "--module-path", str(ROOT / "vendor/ziran/std"),
        "--define", define, "-o", str(WORK / define),
        str(ROOT / "src/platform/uri_host.zi"),
    ], check=True)
print("URI Zi native dispatch and platform emission passed")
