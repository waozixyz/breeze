#!/usr/bin/env python3
"""Exercise the appcast worker through a private loopback HTTP server."""

import ctypes
import ctypes.util
import http.server
import os
from pathlib import Path
import platform
import socketserver
import subprocess
import sys
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parent.parent
BODY = b'{"version":"2.0.7","notes_url":"https://example.org/release"}'
ARTIFACT = b"Ziran update artifact\n" * 4096
SCRIPT = b'#!/bin/sh\nprintf "updated" > "$UPDATE_MARKER"\n'



class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/manifest")
            self.end_headers()
            return
        if self.path == "/large":
            body = b"x" * 32768
        elif self.path == "/artifact":
            body = ARTIFACT
        elif self.path == "/script":
            body = SCRIPT
        elif self.path == "/manifest":
            body = BODY
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def check(fetch, base, route, expected):
    url = ctypes.create_string_buffer((base + route).encode())
    started = fetch.app_update_fetch_start(
        ctypes.cast(url, ctypes.POINTER(ctypes.c_uint8)))
    assert started == 1, route
    output = (ctypes.c_uint8 * 32768)()
    deadline = time.monotonic() + 10
    while True:
        length = fetch.app_update_fetch_poll(output, len(output))
        if length >= 0:
            break
        assert time.monotonic() < deadline, route
        time.sleep(0.01)
    assert bytes(output[:length]) == expected, (route, length)


def check_artifact(fetch, base, expected_size, succeeds):
    url = ctypes.create_string_buffer((base + "/artifact").encode())
    started = fetch.app_update_download_start(
        ctypes.cast(url, ctypes.POINTER(ctypes.c_uint8)), expected_size)
    assert started == 1
    path = (ctypes.c_uint8 * 4096)()
    deadline = time.monotonic() + 10
    while True:
        result = fetch.app_update_download_poll(path, len(path))
        if result >= 0:
            break
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert result == int(succeeds)
    if succeeds:
        name = bytes(path).split(b"\0", 1)[0]
        assert name and os.path.exists(name)
        handle = fetch.app_update_verified_file_open()
        assert handle
        data = bytearray()
        chunk = (ctypes.c_uint8 * 65536)()
        while True:
            length = fetch.app_update_file_read(handle, chunk, len(chunk))
            assert length >= 0
            if length == 0:
                break
            data.extend(chunk[:length])
        assert fetch.app_update_file_close(handle) == 1
        assert data == ARTIFACT
        assert fetch.app_update_download_progress() == 1000
        fetch.app_update_discard_download()
        assert not os.path.exists(name)


def main():
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["PKG_CONFIG_PATH"] = (
        "/home/wao/.local/sdl2/lib/pkgconfig"
        + (":" + env["PKG_CONFIG_PATH"] if env.get("PKG_CONFIG_PATH") else ""))
    with tempfile.TemporaryDirectory(prefix="inbe-update-fetch-") as work:
        flags = subprocess.check_output(
            ["pkg-config", "--cflags", "--libs", "sdl2"],
            text=True, env=env).split()
        curl_name = ctypes.util.find_library("curl")
        assert curl_name is not None, "libcurl is required for this test"
        library = Path(work) / "update_fetch.so"
        compiler = (Path(sys.argv[1]) if len(sys.argv) > 1 else
                    ROOT / "build/ziran-toolchain/bin/zi2c")
        generated = Path(work) / "transport"
        arch = platform.machine().lower()
        architecture = ("__aarch64__" if arch in ("aarch64", "arm64")
                        else "__x86_64__" if arch in ("x86_64", "amd64")
                        else "__i386__" if arch in ("i386", "i686") else None)
        definitions = ["--define", "NATIVE_WINDOW_HAVE_SDL"]
        if architecture:
            definitions += ["--define", architecture]
        subprocess.run([
            str(compiler), "--no-main", *definitions, "--root", "src",
            "--module-path", "vendor/ziran/std", "-o", str(generated),
            "src/app/update_transport.zi",
        ], cwd=ROOT, check=True, env=env)
        subprocess.run([
            "cc", "-std=c11", "-shared", "-fPIC", "-Werror",
            *map(str, generated.rglob("*.c")),
            "-I", str(ROOT / "vendor/ziran/include"), "-iquote", str(generated),
            "-o", str(library), *flags, f"-l:{curl_name}",
        ], check=True, env=env)
        apply_generated = Path(work) / "apply"
        subprocess.run([
            str(compiler), *definitions, "--entry", "update_apply_probe:main",
            "--root", "tests", "--module-path", "src",
            "--module-path", "vendor/ziran/std", "-o", str(apply_generated),
            "tests/update_apply_probe.zi",
        ], cwd=ROOT, check=True, env=env)
        apply_probe = Path(work) / "apply_probe"
        subprocess.run([
            "cc", "-std=c11", *map(str, apply_generated.rglob("*.c")),
            "-I", str(ROOT / "vendor/ziran/include"), "-iquote", str(apply_generated),
            "-o", str(apply_probe), *flags, f"-l:{curl_name}",
        ], check=True, env=env)
        fetch = ctypes.CDLL(str(library))
        fetch.app_update_fetch_start.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        fetch.app_update_fetch_start.restype = ctypes.c_int
        fetch.app_update_fetch_poll.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint64]
        fetch.app_update_fetch_poll.restype = ctypes.c_int
        fetch.app_update_download_start.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint64]
        fetch.app_update_download_start.restype = ctypes.c_int
        fetch.app_update_download_poll.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint64]
        fetch.app_update_download_poll.restype = ctypes.c_int
        fetch.app_update_download_progress.restype = ctypes.c_int
        fetch.app_update_verified_file_open.restype = ctypes.c_void_p
        fetch.app_update_file_read.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint64]
        fetch.app_update_file_read.restype = ctypes.c_int64
        fetch.app_update_file_close.argtypes = [ctypes.c_void_p]
        fetch.app_update_file_close.restype = ctypes.c_int
        fetch.app_update_channel_key.restype = ctypes.c_char_p
        previous_appimage = os.environ.pop("APPIMAGE", None)
        try:
            assert fetch.app_update_channel_key() is None
            os.environ["APPIMAGE"] = "/tmp/inbe-test.AppImage"
            arch = platform.machine().lower()
            expected = (b"appimage-arm64" if arch in ("aarch64", "arm64")
                        else b"appimage-amd64" if arch in ("x86_64", "amd64", "i386", "i686")
                        else b"appimage")
            assert fetch.app_update_channel_key() == expected
        finally:
            os.environ.pop("APPIMAGE", None)
            if previous_appimage is not None:
                os.environ["APPIMAGE"] = previous_appimage
        with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            check(fetch, base, "/redirect", BODY)
            check(fetch, base, "/missing", b"")
            check(fetch, base, "/large", b"")
            check_artifact(fetch, base, len(ARTIFACT), True)
            check_artifact(fetch, base, len(ARTIFACT) - 1, False)
            installed = Path(work) / "test.AppImage"
            installed.write_bytes(b"#!/bin/sh\nexit 9\n")
            installed.chmod(0o755)
            marker = Path(work) / "restarted.txt"
            apply_env = env.copy()
            apply_env["TMPDIR"] = work
            apply_env["UPDATE_MARKER"] = str(marker)
            apply_env["INBE_TEST_UPDATE_URL"] = base + "/script"
            apply_env["INBE_TEST_UPDATE_SIZE"] = str(len(SCRIPT))
            apply_env["APPIMAGE"] = str(installed)
            subprocess.run([str(apply_probe)], check=True, env=apply_env, timeout=20)
            assert installed.read_bytes() == SCRIPT
            assert marker.read_text() == "updated"
            server.shutdown()
            thread.join()
    print("Inbe update fetch host test passed")


if __name__ == "__main__":
    main()
