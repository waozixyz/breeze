"""Serve current Photos through Breeze's real package installer locally."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

@contextmanager
def photos_client_fixture(module, key, signing_message):
    payload = Path(module).resolve().read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    release = dict(app_id='inbe.photos', sequence=2, version='1.0.0',
                   runtime='kryon-app-v1', host_api=43, module_api=2, data_schema=0,
                   key_id='photos-fixture', dependencies=[],
                   artifacts=[dict(variant='module', sha256=digest, size=len(payload))])
    release['signature'] = key.sign(signing_message(release)).hex()
    metadata = json.dumps(release).encode()
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            requests.append(path)
            if path == '/api/v2/packages/inbe.photos/latest':
                body = metadata
            elif path == '/api/v2/packages/inbe.photos/' + digest + '.zx':
                count = requests.count(path)
                body = bytes([payload[0] ^ 1]) + payload[1:] if count == 1 else payload
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {'PHOTOS_CLIENT_ORIGIN': f'http://127.0.0.1:{server.server_port}',
               'PHOTOS_CLIENT_SHA256': digest}
        path = '/api/v2/packages/inbe.photos/' + digest + '.zx'
        assert requests.count(path) == 2, requests
        assert requests.count('/api/v2/packages/inbe.photos/latest') == 2, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
