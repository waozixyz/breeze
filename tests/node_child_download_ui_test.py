"""Download one declared game, reject corruption, and reopen its offline cache."""
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import bundle_assets
sys.path.insert(0, str(ROOT.parent / 'shovey/tests'))
from inbe_apps import open_arcade

BINARY, CATALOG = (Path(value).resolve() for value in sys.argv[1:3])
BUNDLE = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else ROOT / 'build/inbe-full.zx'
OUTPUT = ROOT / 'build/node-child-download-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
           'GDK_DISPLAY', 'SESSION_MANAGER')
assert all(not os.environ.get(key) for key in DESKTOP), 'Inherited desktop environment'
catalog = json.loads(bundle_assets(CATALOG.read_bytes())['assets/apps/catalog.json'])
assert catalog['id'] == 'inbe.arcade'
assert all(entry['bundle'] not in bundle_assets(CATALOG.read_bytes()) for entry in catalog['children'])
classic = next(entry for entry in catalog['children'] if entry['expected_id'] == 'shovey')
payloads = CATALOG.with_suffix('.games')
game = (payloads / (classic['sha256'] + '.zx')).read_bytes()
assert hashlib.sha256(game).hexdigest() == classic['sha256']
requests = []


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        requests.append(self.path)
        wanted = '/api/v2/packages/inbe.arcade/' + classic['sha256'] + '.zx'
        if self.path != wanted:
            self.send_error(404)
            return
        # The first response has the correct length and a deliberately bad hash.
        body = game if len(requests) > 1 else game[:-1] + bytes([game[-1] ^ 1])
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            for start in range(0, len(body), 65536):
                self.wfile.write(body[start:start + 65536])
                self.wfile.flush()
                time.sleep(.02)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_):
        pass


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='child-download-', dir=OUTPUT)))
    audio = profile / 'alsa.conf'
    audio.write_text('pcm.!default { type null }\n')
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    stack.callback(server_thread.join)
    stack.callback(server.server_close)
    stack.callback(server.shutdown)
    driver = UiDriver(profile / 'driver')
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP}
    for key in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
        env.pop(key, None)
    env.update(driver.environment())
    env.update(APP_DATA_ROOT=str(profile), APP_NO_TRAY='1', YUE_DESKTOP_RECOVERY='0',
               INBE_NODE_APP_FILE=str(CATALOG),
               INBE_LOCAL_PACKAGE_ORIGIN='http://127.0.0.1:' + str(server.server_port),
               NO_PROXY='127.0.0.1', SDL_VIDEODRIVER='x11', LIBGL_ALWAYS_SOFTWARE='1',
               LP_NUM_THREADS='2', ALSA_CONFIG_PATH=str(audio))
    display_log = stack.enter_context((OUTPUT / 'display.log').open('w'))
    display = subprocess.Popen(['Xvfb', ':975', '-noreset', '-displayfd', '1',
                                '-screen', '0', '411x900x24', '-nolisten', 'tcp'], env=env,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and int(number) >= 400 and display.poll() is None
    env['DISPLAY'] = ':' + number

    @contextlib.contextmanager
    def application(name):
        driver.reset()
        log_path = OUTPUT / (name + '.log')
        with log_path.open('w') as log:
            process = subprocess.Popen([str(BINARY), '--bundle', str(BUNDLE)], cwd=ROOT,
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            driver.attach(process, log_path)
            try:
                driver.tree()
                found = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(process.pid)],
                                                env=env, text=True, timeout=5)
                window = found.splitlines()[0]
                subprocess.run(['xdotool', 'windowsize', window, '411', '900'], env=env, check=True, timeout=5)
                yield process
                assert process.poll() is None, log_path.read_text()[-3000:]
            finally:
                stop(process)

    with application('initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = dict(language='en', language_system=0, language_setup_done=1,
                        apps_setup_done=1, tutorial_seen=1, habits_guide_seen=1,
                        launcher_guide_seen=1, lumi_guides_seen=127, enabled_apps=63,
                        package_updates_allowed=0, sync_enabled=0, navigation_placement=2,
                        apps_last_update_check=1900000000, node_apps_checked_at=int(time.time()),
                        node_apps_offers='arcade|Arcade\n', node_app_slot_0='arcade', app_used_arcade=1)
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, str(value)))

    percentages = []
    captured = False

    def wait_for_download(label):
        global captured
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            labels = driver.labels()
            percentages.extend(int(match.group(1)) for text in labels
                               if (match := re.fullmatch(r'Downloading (\d+)%', text)))
            if not captured and percentages and 0 < percentages[-1] < 100:
                windows = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid',
                                                   str(driver.process.pid)], env=env, text=True, timeout=5)
                subprocess.run(['import', '-display', env['DISPLAY'], '-window', windows.splitlines()[0],
                                str(OUTPUT / 'progress.png')], env=env, check=True, timeout=10)
                captured = True
            if any(label in text for text in labels):
                return
            time.sleep(.05)
        raise AssertionError('Download did not reach ' + label + ': ' + driver.text())

    with application('download'):
        driver.wait(label='Apps', role='button')
        open_arcade(driver)
        driver.wait_idle(frames=4)
        assert not requests, 'Opening the catalog downloaded a game'
        driver.press(label='Play', role='button')
        driver.wait(role='modal')
        assert not requests, 'Opening the dialog downloaded before consent'
        driver.press(label='Download', role='button')
        wait_for_download('Download failed')
        assert not driver.find(contains='Level 1 / ', visible=True), 'Corrupt bytes opened'
        driver.press(label='Try again', role='button')
        wait_for_download('Level 1 / ')
        assert len(requests) == 2 and all(classic['sha256'] in request for request in requests), requests
        assert any(0 < value < 100 for value in percentages), percentages

    count = len(requests)
    with application('offline-restart'):
        open_arcade(driver)
        driver.wait_idle(frames=4)
        driver.press(label='Play', role='button')
        wait_for_download('Level 1 / ')
        assert len(requests) == count, 'Restart downloaded the cached game again'

    (OUTPUT / 'result.json').write_text(json.dumps(dict(
        passed=True, requests=requests, percentages=percentages,
        corrupt_payload_rejected=True, automatic_open=True, offline_restart=True), indent=2) + '\n')

print('Separate game download: visible progress, corruption rejection, retry, automatic open and offline restart passed')
