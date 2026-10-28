"""Download one declared game, reject corruption, and reopen its offline cache."""
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import bundle_assets

def open_arcade(driver):
    driver.press(label='Apps', role='button')
    if not driver.find(label='Arcade', role='button', visible=True):
        driver.press(label='Find an app', role='text_field')
        driver.type('Arcade')
    driver.press(label='Arcade', role='button')
    deadline = time.monotonic() + 60
    while driver.find(label='Find an app', role='text_field', visible=True):
        assert time.monotonic() < deadline, 'Arcade did not open: ' + driver.text()
        cancel = driver.find(label='Cancel', role='button', visible=True)
        if cancel:
            downloads = driver.find(label='Download', role='button', visible=True)
            nearest = min(range(len(downloads)), key=lambda at: abs(downloads[at]['y'] - cancel[0]['y']))
            driver.press(label='Download', role='button', index=nearest)
        elif driver.find(label='Ready to open', role='text', visible=True):
            driver.press(label='Open', role='button')
        time.sleep(.1)

BINARY, CATALOG = (Path(value).resolve() for value in sys.argv[1:3])
BUNDLE = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else ROOT / 'build/inbe-full.zx'
OUTPUT = ROOT / 'build/node-child-download-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
           'GDK_DISPLAY', 'SESSION_MANAGER')
assert all(not os.environ.get(key) for key in DESKTOP), 'Inherited desktop environment'
catalog_assets = bundle_assets(CATALOG.read_bytes())
catalog = json.loads(catalog_assets['assets/apps/catalog.json'])
assert catalog['id'] == 'inbe.arcade'
assert all(entry['bundle'] not in catalog_assets for entry in catalog['children'])
host_controller = bundle_assets(BUNDLE.read_bytes())['assets/apps/apps.zx']
controller_digest = hashlib.sha256(host_controller).hexdigest()
if catalog['harness'] in catalog_assets:
    assert controller_digest == hashlib.sha256(catalog_assets[catalog['harness']]).hexdigest(), 'Catalog uses another controller'
classic = next(entry for entry in catalog['children'] if entry['expected_id'] == 'shovey')
payloads = CATALOG.with_suffix('.games')
game = (payloads / (classic['sha256'] + '.zx')).read_bytes()
assert hashlib.sha256(game).hexdigest() == classic['sha256']
requests = []
updated_game = None
updated_digest = None


def rewrite_assets(source, destination, replacements=None, additions=None):
    """Keep executable sections intact while streaming fixture resource changes."""
    replacements = replacements or {}
    additions = additions or {}
    with source.open('rb') as incoming, destination.open('wb') as outgoing:
        def number():
            return struct.unpack('<I', incoming.read(4))[0]

        def skip_text():
            incoming.seek(number(), 1)

        assert incoming.read(8) == b'ZX\0\0\x1a\0\0\0'
        skip_text(); skip_text()
        for _ in range(number()):
            skip_text(); skip_text()
        for _ in range(number()):
            for _ in range(7):
                skip_text()
            incoming.seek(8, 1); skip_text(); incoming.seek(4, 1)
        for _ in range(number()):
            for _ in range(3):
                skip_text()
        incoming.seek(number(), 1)
        count_at = incoming.tell()
        count = number()
        incoming.seek(0)
        outgoing.write(incoming.read(count_at))
        incoming.seek(4, 1)
        outgoing.write(struct.pack('<I', count + len(additions)))
        for _ in range(count):
            name = incoming.read(number())
            length = number()
            outgoing.write(struct.pack('<I', len(name)) + name)
            replacement = replacements.get(name.decode())
            if replacement is not None:
                outgoing.write(struct.pack('<I', len(replacement)) + replacement)
                incoming.seek(length, 1)
            else:
                outgoing.write(struct.pack('<I', length))
                remaining = length
                while remaining:
                    block = incoming.read(min(remaining, 65536))
                    assert block, 'Truncated fixture bundle'
                    outgoing.write(block)
                    remaining -= len(block)
        assert incoming.read(1) == b''
        for name, content in additions.items():
            encoded = name.encode()
            outgoing.write(struct.pack('<I', len(encoded)) + encoded)
            outgoing.write(struct.pack('<I', len(content)) + content)


def digest_file(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()
identities = dict(binary=str(BINARY), runtime_bundle=str(BUNDLE), catalog=str(CATALOG),
                  binary_sha256=hashlib.sha256(BINARY.read_bytes()).hexdigest(),
                  runtime_bundle_sha256=hashlib.sha256(BUNDLE.read_bytes()).hexdigest(),
                  catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
                  controller_sha256=controller_digest, child_sha256=classic['sha256'])
(OUTPUT / 'result.json').write_text(json.dumps(dict(passed=False, **identities), indent=2) + '\n')


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        requests.append(self.path)
        wanted = '/api/v2/packages/inbe.arcade/' + classic['sha256'] + '.zx'
        upgrade = updated_digest and self.path == '/api/v2/packages/inbe.arcade/' + updated_digest + '.zx'
        if self.path != wanted and not upgrade:
            self.send_error(404)
            return
        # The first response has the correct length and a deliberately bad hash.
        self.send_response(200)
        self.send_header('Content-Length', str(updated_game.stat().st_size if upgrade else len(game)))
        self.end_headers()
        try:
            if upgrade:
                with updated_game.open('rb') as source:
                    shutil.copyfileobj(source, self.wfile, 65536)
            else:
                body = game if len(requests) > 1 else game[:-1] + bytes([game[-1] ^ 1])
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
    active_catalog = profile / 'arcade.zx'
    rewrite_assets(CATALOG, active_catalog,
                   replacements={'assets/apps/catalog.json': json.dumps(catalog).encode()})
    if 'art' in catalog:
        cache = profile / 'packages'
        cache.mkdir()
        art_digest = catalog['art']['sha256']
        shutil.copyfile(payloads / (art_digest + '.zx'), cache / ('child-inbe.arcade-' + art_digest + '.zx'))
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
               INBE_NODE_APP_FILE=str(active_catalog),
               INBE_LOCAL_PACKAGE_ORIGIN='http://127.0.0.1:' + str(server.server_port),
               NO_PROXY='127.0.0.1', http_proxy='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9',
               SDL_VIDEODRIVER='x11', LIBGL_ALWAYS_SOFTWARE='1',
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
                subprocess.run(['xdotool', 'windowmove', window, '0', '0'], env=env, check=True, timeout=5)
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
        # Discovery continues after the first painted frame. The catalog must
        # stay open while its declared games are still absent.
        time.sleep(1)
        assert driver.find(label='Download', role='button', visible=True), driver.text()
        driver.press(label='Download', role='button', index=0)
        driver.wait(role='modal')
        assert not requests, 'Opening the dialog downloaded before consent'
        driver.press(label='Download', role='button', index=len(driver.find(label='Download', role='button', visible=True)) - 1)
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
        driver.press(label=classic['title'], role='button', index=0)
        wait_for_download('Level 1 / ')
        assert len(requests) == count, 'Restart downloaded the cached game again'

    # An updated root catalog retains the installed identity, even when the
    # game has a new exact digest. Only that game's update may be downloaded.
    updated_game = profile / 'updated-game.zx'
    rewrite_assets(payloads / (classic['sha256'] + '.zx'), updated_game,
                   additions={'assets/' + classic['expected_id'] + '/test-update.txt': b'updated game fixture'})
    updated_digest = digest_file(updated_game)
    updated_catalog = json.loads(json.dumps(catalog))
    updated_child = next(entry for entry in updated_catalog['children'] if entry['id'] == classic['id'])
    updated_child.update(sha256=updated_digest, bytes=updated_game.stat().st_size, version='999.0.1')
    rewrite_assets(CATALOG, active_catalog,
                   replacements={'assets/apps/catalog.json': json.dumps(updated_catalog).encode()})
    with sqlite3.connect(profile / 'inbe.db') as db:
        db.execute("UPDATE settings SET value='1' WHERE user_id=? AND key='package_updates_allowed'", (user,))
        save_identity = hashlib.sha256(('local-development\n' + classic['id']).encode()).hexdigest()
        save_key = 'nested.' + save_identity + '.test_progress'
        save_value = '{"level":7,"score":420}'
        db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1)',
                   (user, save_key, save_value))
    with application('catalog-update'):
        open_arcade(driver)
        deadline = time.monotonic() + 60
        while len(requests) == count and time.monotonic() < deadline:
            driver.wait_idle(frames=2)
            time.sleep(.05)
        assert requests[count:] == ['/api/v2/packages/inbe.arcade/' + updated_digest + '.zx'], requests
        driver.wait(label='App options', role='button', timeout=60)
        driver.press(label=classic['title'], role='button', index=0)
        wait_for_download('Level 1 / ')
        assert not driver.find(role='modal', visible=True), 'Installed game required installation again'
    count = len(requests)
    with application('updated-offline-restart'):
        open_arcade(driver)
        driver.press(label=classic['title'], role='button', index=0)
        wait_for_download('Level 1 / ')
        assert len(requests) == count, 'Updated cached game downloaded on restart'
    with sqlite3.connect(profile / 'inbe.db') as db:
        assert db.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                          (user, save_key)).fetchone() == (save_value,), 'Saved game record changed during update'

    (OUTPUT / 'result.json').write_text(json.dumps(dict(
        passed=True, **identities, requests=requests, percentages=percentages,
        corrupt_payload_rejected=True, automatic_open=True, offline_restart=True,
        installed_game_update=True, updated_offline_restart=True), indent=2) + '\n')

print('Arcade local tests passed: download consent, corruption rejection, retry, installed catalog update, saved progress and offline restarts.')
