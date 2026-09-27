#!/usr/bin/env python3
"""Compile and verify the Ziran device key against Monocypher Ed25519."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
COMPILER = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin/zi2c"

with tempfile.TemporaryDirectory(prefix="inbe-device-key-") as temporary:
    generated = Path(temporary) / "generated"
    executable = Path(temporary) / "test"
    subprocess.run([
        str(COMPILER), "--no-main", "--root", str(ROOT / "src"),
        "--module-path", str(ROOT / "vendor/ziran/std"),
        "--module-path", str(ROOT / "vendor/daochi-client"),
        "--module-path", str(ROOT / "vendor/kryon/src/ui"),
        "-o", str(generated), str(ROOT / "src/storage/device_key_store.zi"),
    ], check=True)
    names = {"device_key_store.c", "device_key.c", "sync_crypto.c",
             "sync_crypto_random.c", "byte_text_linux.c"}
    sources = sorted(str(path) for path in generated.rglob("*.c")
                     if path.name in names)
    monocypher = ROOT / "vendor/monocypher/src"
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-O0", "-Wall", "-Wextra",
        "-Werror", "-Wno-unused-function", "-Wno-unused-variable",
        "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
        f"-I{ROOT / 'vendor/ziran/include'}", f"-I{generated}",
        f"-I{generated / 'storage'}", f"-I{monocypher}",
        f"-I{monocypher / 'optional'}",
        str(ROOT / "tests/device_key_zi_test.c"), *sources,
        str(monocypher / "monocypher.c"),
        str(monocypher / "optional/monocypher-ed25519.c"),
        "-o", str(executable),
    ], check=True)
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    subprocess.run([str(executable)], check=True, env=environment)
