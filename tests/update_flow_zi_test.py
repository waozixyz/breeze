#!/usr/bin/env python3
"""Link the Ziran update state machine and exercise it over loopback HTTP."""

import ctypes.util
import hashlib
import http.server
import json
import os
from pathlib import Path
import platform
import re
import socketserver
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = b"Ziran update artifact\n" * 4096
EXECUTABLE = b'#!/bin/sh\nprintf "updated" > "$INBE_UPDATE_MARKER"\n'



def release_version():
    source = (ROOT / "src/core/version.zi").read_text()
    match = re.search(r'VersionString :: "(\d+)\.(\d+)\.(\d+)"', source)
    assert match, "numeric VersionString is required"
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/manifest", "/manifest-apply"):
            artifact = EXECUTABLE if self.path == "/manifest-apply" else ARTIFACT
            arch = platform.machine().lower()
            channel = ("appimage-arm64" if arch in ("aarch64", "arm64")
                       else "appimage-amd64" if arch in
                       ("x86_64", "amd64", "i386", "i686")
                       else "appimage")
            body = json.dumps({
                "version": release_version(),
                "notes_url": "https://example.org/release",
                "channels": {channel: {
                    "url": "https://example.org/artifact",
                    "sha256": hashlib.sha256(artifact).hexdigest(),
                    "size": len(artifact),
                }},
            }).encode()
        elif self.path == "/artifact":
            body = ARTIFACT
        elif self.path == "/executable":
            body = EXECUTABLE
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def build_probe(work, compiler, env):
    output = work / "generated"
    arch = platform.machine().lower()
    architecture = ("__aarch64__" if arch in ("aarch64", "arm64")
                    else "__x86_64__" if arch in ("x86_64", "amd64")
                    else "__i386__" if arch in ("i386", "i686") else None)
    definitions = ["--define", "NATIVE_WINDOW_HAVE_SDL"]
    if architecture:
        definitions += ["--define", architecture]
    subprocess.run([
        str(compiler), "--no-main", *definitions,
        "--root", "tests", "--module-path", "src",
        "--module-path", "build/packages/kryon/src/ui",
        "--module-path", "build/packages/kss/src",
        "--module-path", "kryon=build/packages/kryon/src/ui",
        "--module-path", "build/packages/ziran/std",
        "--module-path", "build/packages/daochi-client",
        "-o", str(output), "tests/update_flow_probe.zi",
    ], cwd=ROOT, check=True, env=env)
    sdl = subprocess.check_output(
        ["pkg-config", "--cflags", "--libs", "sdl2"],
        text=True, env=env).split()
    curl_name = ctypes.util.find_library("curl")
    assert curl_name, "libcurl is required"
    executable = work / "probe"
    sources = [
        output / "update_flow_probe.c", output / "update_check.c",
        output / "update_policy.c",
        output / "json_scan.c", output / "update.c",
        output / "text_buffer.c", output / "sync_crypto.c",
        output / "current_app.c", output / "update_transport.c",
        output / "c_string.c", output / "byte_text_linux.c",
    ]
    subprocess.run([
        "cc", "-std=c11", "-D_GNU_SOURCE", "-DNATIVE_WINDOW_HAVE_SDL",
        "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
        "-I", str(ROOT / "build/packages/ziran/include"), "-I", str(output),
        "-I", str(ROOT / "build/packages/curl/include"),
        *map(str, sources), *sdl, f"-l:{curl_name}", "-o", str(executable),
    ], cwd=ROOT, check=True, env=env)
    return executable


def main():
    compiler = (Path(sys.argv[1]) if len(sys.argv) > 1 else
                ROOT / "build/ziran-toolchain/bin/zi2c")
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["PKG_CONFIG_PATH"] = (
        "/home/wao/.local/sdl2/lib/pkgconfig"
        + (":" + env["PKG_CONFIG_PATH"] if env.get("PKG_CONFIG_PATH") else ""))
    with tempfile.TemporaryDirectory(prefix="inbe-update-flow-") as directory:
        work = Path(directory)
        env["TMPDIR"] = str(work)
        executable = build_probe(work, compiler, env)
        with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            appimage = str(work / "test.AppImage")
            original = b"previous installed AppImage"
            Path(appimage).write_bytes(original)
            for supplied_hash, expected in (("-", 3), ("0" * 64, 4)):
                env["UPDATE_APPCAST_OVERRIDE"] = base + "/manifest"
                env["APPIMAGE"] = appimage
                env["INBE_TEST_UPDATE_URL"] = base + "/artifact"
                env["INBE_TEST_UPDATE_HASH"] = supplied_hash
                env["INBE_TEST_UPDATE_EXPECTED"] = str(expected)
                subprocess.run([str(executable)], check=True, env=env, timeout=20)
                assert Path(appimage).read_bytes() == original
            marker = work / "restarted"
            env["INBE_UPDATE_MARKER"] = str(marker)
            env["UPDATE_APPCAST_OVERRIDE"] = base + "/manifest-apply"
            env["INBE_TEST_UPDATE_URL"] = base + "/executable"
            env["INBE_TEST_UPDATE_HASH"] = "-"
            env["INBE_TEST_UPDATE_EXPECTED"] = "3"
            env["INBE_TEST_UPDATE_APPLY"] = "1"
            subprocess.run([str(executable)], check=True, env=env, timeout=20)
            assert marker.read_text() == "updated"
            assert Path(appimage).read_bytes() == EXECUTABLE
            server.shutdown()
            thread.join()
    print("Inbe linked Ziran update flow test passed")


if __name__ == "__main__":
    main()
