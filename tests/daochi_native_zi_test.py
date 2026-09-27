#!/usr/bin/env python3
"""Exercise Inbe's Ziran Daochi adapter through a disposable HTTP server."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading


ROOT = Path(__file__).resolve().parent.parent
COMPILER = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin/zi2c"
USER_ID = "a" * 64
NONCE = "c" * 64


class Handler(BaseHTTPRequestHandler):
    friends_requests = 0
    registrations = 0
    syncs = 0

    def log_message(self, *_args):
        pass

    def respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == f"/api/v1/sync/challenge?user_id={USER_ID}":
            self.respond(200, json.dumps({"nonce": NONCE}).encode())
            return
        if self.path == "/api/v1/friends":
            assert self.headers.get("Authorization") == "Bearer token-from-server"
            assert self.headers.get("X-Daochi-User") == USER_ID
            assert self.headers.get("X-Daochi-Client") == "client-1"
            type(self).friends_requests += 1
            if type(self).friends_requests == 1:
                self.respond(401, b"{}")
            else:
                self.respond(200, b'{"friends":[]}')
            return
        self.respond(404, b"{}")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path == "/api/v1/account/devices":
            data = json.loads(body)
            assert self.headers.get("Authorization") == "Bearer token-from-server"
            assert data["app_id"] == "inbe"
            assert data["device_key_id"] == "b" * 64
            assert data["public_key"] == "b" * 64
            assert data["nonce"] == "01" * 32
            assert data["expires_at"] == 1700000301
            assert data["signature"] == "bb" * 2420
            type(self).registrations += 1
            self.respond(200, b"{}")
            return
        if self.path == "/api/v1/sync":
            envelope = json.loads(self.headers["X-Daochi-Tx"])
            assert self.headers.get("Authorization") == "Bearer token-from-server"
            assert envelope["protocol_version"] == 6
            assert envelope["app_id"] == "inbe"
            assert envelope["device_key_id"] == "b" * 64
            assert envelope["tx_id"] == "02" * 32
            assert envelope["nonce"] == "03" * 32
            assert envelope["expires_at"] == 1700000301
            assert envelope["body_sha256"] == hashlib.sha256(body).hexdigest()
            assert envelope["signature"] == "bb" * 2420
            assert envelope["device_signature"] == "d" * 128
            assert body == b'{"protocol_version":6}'
            type(self).syncs += 1
            self.respond(200, b'{"server_version":7}')
            return
        try:
            data = json.loads(body)
            signature = bytes.fromhex(self.headers.get("X-Daochi-Signature", ""))
        except ValueError:
            data = {}
            signature = b""
        valid = (self.path == "/api/v1/sync/login" and
                 self.headers.get("X-Daochi-User") == USER_ID and
                 self.headers.get("Content-Type") == "application/json" and
                 data.get("user_id_hash") == USER_ID and
                 data.get("public_key") == "pub" and
                 len(signature) == 2420 and
                 signature[:64] == hashlib.sha256(body).hexdigest().encode() and
                 signature[64:128] == NONCE.encode() and
                 signature[128:] == b"\xbb" * (2420 - 128))
        if not valid:
            self.respond(400, b"{}")
        elif data.get("client_id") == "bad-client":
            self.respond(401, b"{}")
        elif data.get("client_id") == "client-1":
            self.respond(200, json.dumps({
                "auth_token": "token-from-server",
                "expires_in_seconds": 1800,
                "server_time": 1700000000,
            }).encode())
        else:
            self.respond(400, b"{}")


with tempfile.TemporaryDirectory(prefix="inbe-daochi-native-") as temporary:
    generated = Path(temporary) / "generated"
    executable = Path(temporary) / "client"
    subprocess.run([
        str(COMPILER), "--no-main", "--root", str(ROOT / "src"),
        "--module-path", str(ROOT / "build/packages/ziran/std"),
        "--module-path", str(ROOT / "build/packages/daochi-client"),
        "-o", str(generated), str(ROOT / "src/storage/daochi_native.zi"),
    ], check=True)
    sources = [
        "storage/daochi_native.c", "daochi_account.c", "client.c", "auth.c", "url.c", "wire.c",
        "sync.c", "transaction.c", "sync_account_sign.c", "sync_crypto.c",
        "sync_crypto_random.c",
        "net_http_curl_linux.c", "json_scan.c", "text.c", "text_buffer.c",
        "byte_text_linux.c", "c_string.c",
    ]
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-O0", "-Wall", "-Wextra",
        "-Werror", "-Wno-unused-function", "-Wno-unused-variable",
        f"-I{ROOT / 'build/packages/ziran/include'}", f"-I{generated}",
        f"-I{generated / 'storage'}",
        str(ROOT / "tests/daochi_native_zi_test.c"),
        *(str(generated / source) for source in sources),
        "-l:libcurl.so.4", "-o", str(executable),
    ], check=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        environment = os.environ.copy()
        environment.pop("DISPLAY", None)
        environment.pop("WAYLAND_DISPLAY", None)
        subprocess.run([
            str(executable), f"127.0.0.1:{server.server_port}"
        ], check=True, env=environment)
        assert Handler.friends_requests == 2
        assert Handler.registrations == 1
        assert Handler.syncs == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
