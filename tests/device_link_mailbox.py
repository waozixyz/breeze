"""A local stand-in for Daochi's device link mailbox, for UI tests.

It follows the node's rules: 32-hex link IDs, request and response slots that
are written once, 404 while waiting, and a 16384-byte message limit."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading

ID = re.compile(r"^[0-9a-f]{32}$")


class Mailbox:
    def __init__(self):
        self.links = {}
        self.lock = threading.Lock()
        self.requests = []
        # Every message sent, to check what the relay could see.
        self.messages = []


def handler_for(mailbox):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *arguments):
            pass

        def reply(self, status, value):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self.reply(400, {"error": "invalid json"})
            link = body.get("id", "")
            slot = body.get("slot", "")
            with mailbox.lock:
                mailbox.requests.append((self.path, slot))
                if not ID.match(link):
                    return self.reply(400, {"error": "invalid device link"})
                entry = mailbox.links.setdefault(link, {})
                if self.path == "/api/v1/link/put":
                    data = body.get("data", "")
                    if slot not in ("request", "response") or not data or len(data) > 16384:
                        return self.reply(400, {"error": "invalid device link message"})
                    if slot in entry:
                        return self.reply(409, {"error": "already sent"})
                    entry[slot] = data
                    mailbox.messages.append(data)
                    return self.reply(200, {"ok": True})
                if self.path == "/api/v1/link/get":
                    if slot not in entry:
                        return self.reply(404, {"error": "device link waiting"})
                    return self.reply(200, {"data": entry[slot]})
                if self.path == "/api/v1/link/close":
                    mailbox.links.pop(link, None)
                    return self.reply(200, {"ok": True})
            return self.reply(404, {"error": "not found"})

        # Sync and other node calls are not part of these tests.
        def do_GET(self):
            self.reply(404, {"error": "not found"})

    return Handler


def start():
    mailbox = Mailbox()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(mailbox))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, mailbox
