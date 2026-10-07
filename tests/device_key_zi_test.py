#!/usr/bin/env python3
"""Compile and verify the Ziran device key against Monocypher Ed25519."""

from pathlib import Path
import argparse
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("compiler", nargs="?", type=Path, default=ROOT / "build/ziran-toolchain/bin/zi2c")
parser.add_argument("--wasm", action="store_true")
parser.add_argument("--emcc", default=os.environ.get("EMCC", "/home/wao/emsdk/upstream/emscripten/emcc"))
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix="inbe-device-key-") as temporary:
    generated = Path(temporary) / "generated"
    executable = Path(temporary) / ("test.js" if args.wasm else "test")
    subprocess.run([
        str(args.compiler), "--no-main", "--root", str(ROOT / "src"),
        *(["--define", "PLATFORM_WEB", "--define", "__EMSCRIPTEN__"] if args.wasm else []),
        "--module-path", str(ROOT / "build/packages/ziran/std"),
        "--module-path", f"oqs={ROOT / 'build/packages/oqs/src'}",
        "--module-path", str(ROOT / "build/packages/daochi-client"),
        "--module-path", str(ROOT / "build/packages/kryon/src/ui"),
        "-o", str(generated), str(ROOT / "src/storage/device_key_store.zi"),
        str(ROOT / "src/app/update_transport.zi"),
    ], check=True)
    names = {"device_key_store.c", "device_key.c", "sync_crypto.c",
             "sync_crypto_random.c", "byte_text_linux.c", "Oqs.c", "update_transport.c"}
    sources = sorted(str(path) for path in generated.rglob("*.c")
                     if path.name in names)
    monocypher = ROOT / "build/packages/monocypher/src"
    subprocess.run([
        args.emcc if args.wasm else os.environ.get("CC", "cc"), "-std=c11", "-O0", "-Wall", "-Wextra",
        "-Werror", "-Wno-unused-function", "-Wno-unused-variable",
        "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
        f"-I{ROOT / 'build/packages/ziran/include'}", f"-I{generated}",
        f"-I{generated / 'storage'}", f"-I{monocypher}",
        f"-I{monocypher / 'optional'}",
        str(ROOT / "tests/device_key_zi_test.c"), *sources,
        str(monocypher / "monocypher.c"),
        str(monocypher / "optional/monocypher-ed25519.c"),
        *(["-sENVIRONMENT=node", "-sWASM_ASYNC_COMPILATION=0", "-sEXIT_RUNTIME=1",
           "-Wl,--fatal-warnings"] if args.wasm else []),
        "-o", str(executable),
    ], check=True)
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    environment.pop("XAUTHORITY", None)
    environment.pop("DBUS_SESSION_BUS_ADDRESS", None)
    subprocess.run([*(["node"] if args.wasm else []), str(executable)], check=True, env=environment)
