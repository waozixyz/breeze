"""Lumi's title bar, online terms and own AI provider in the real app, on a
private display, at phone size (1080x1920, UI scale 2.5) and desktop size
(900x720), against a local stand-in for an OpenAI-compatible provider.

Opening Lumi shows its online terms until they are answered, once a run.
After "Not now" Lumi stays offline: an unknown request gets the offline
answer and a habit request still works on the device, while the provider
receives nothing. The title bar's connection button opens the terms; after
agreeing, the provider gets the request with the key only in its
Authorization header. Switched off, nothing is sent again. The title bar's
wrench opens Lumi's own settings page, which shows the provider and
reopens the terms, and one tap on its Back returns to the chat. Screenshots of each step are kept in build/lumi-harness-ui-test.
"""
import ast
import contextlib
import csv
import http.server
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/lumi-harness-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300, 'needs a private display'
ENV = os.environ | dict(APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy', YUE_DESKTOP_RECOVERY='0',
                        INBE_NETWORK_TRACE='1')
for name in ('WAYLAND_DISPLAY',):
    ENV.pop(name, None)
KEY = 'sk-test-harness-provider-4242'
REPLY = 'Here is a joke from the test provider.'
SIZES = {'phone': (1080, 1920, 25), 'desktop': (900, 720, 10)}


class Provider(http.server.BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8')
        Provider.requests.append(dict(path=self.path, authorization=self.headers.get('Authorization', ''),
                                      body=json.loads(body)))
        answer = json.dumps(dict(id='test', object='chat.completion', choices=[dict(
            index=0, finish_reason='stop', message=dict(role='assistant', content=REPLY))]))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(answer)))
        self.end_headers()
        self.wfile.write(answer.encode())

    def log_message(self, *arguments):
        pass


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True, check=True, timeout=10).stdout.strip()


def wait_for(predicate, description, seconds=12):
    deadline = time.monotonic() + seconds
    while True:
        result = predicate()
        if result:
            return result
        assert time.monotonic() < deadline, description
        time.sleep(0.1)


def capture(window, label):
    raw = OUTPUT / (label + '.xwd')
    command('xwd', '-silent', '-id', window, '-out', str(raw))
    command('convert', str(raw), str(OUTPUT / (label + '.png')))
    raw.unlink()
    return OUTPUT / (label + '.png')


def tap(window, x, y):
    command('xdotool', 'windowfocus', window)
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    time.sleep(0.15)
    command('xdotool', 'mousedown', '1')
    time.sleep(0.15)
    command('xdotool', 'mouseup', '1')
    time.sleep(0.4)


def words(window, label):
    """Words OCR reads in the owned window: light on dark and dark on light,
    enlarged so small desktop text reads too. Positions are the window's."""
    image = capture(window, label)
    found = []
    for variant, options in (('plain', []), ('negated', ['-negate', '-level', '10%,70%'])):
        source = OUTPUT / (label + '-' + variant + '.png')
        command('convert', str(image), '-colorspace', 'Gray', *options, '-resize', '200%', str(source))
        result = command('tesseract', str(source), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
        for row in csv.DictReader(io.StringIO(result), delimiter='\t'):
            if (row.get('text') or '').strip():
                for key in ('left', 'top', 'width', 'height'):
                    row[key] = str(int(row[key]) // 2)
                found.append(row)
        source.unlink()
    return found


def tap_word(window, word, label, lowest=False, highest=False):
    """Taps a rendered word in the owned window, found by OCR."""
    found = [row for row in words(window, label) if row['text'].strip(' .,…').lower() == word.lower()]
    assert found, f'{word!r} is not on screen ({label})'
    if lowest:
        found.sort(key=lambda row: -int(row['top']))
    elif highest:
        found.sort(key=lambda row: int(row['top']))
    row = found[0]
    tap(window, int(row['left']) + int(row['width']) // 2, int(row['top']) + int(row['height']) // 2)


def state(window):
    value = command('xprop', '-id', window, '_HARMONY_APP_STATE')
    return json.loads(ast.literal_eval(value.split(' = ', 1)[1]))


sequence = 0


def action(window, control, arguments=None):
    global sequence
    sequence += 1
    request = 'harness-' + str(sequence)
    payload = dict(request_id=request, control=control, arguments=arguments or {})
    command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s', '-set', '_HARMONY_APP_ACTION',
            json.dumps(payload))
    return wait_for(lambda: (value if (value := state(window))['last_request_id'] == request else None),
                    'App action was not acknowledged: ' + control)


def chat(profile):
    with sqlite3.connect(profile / 'inbe.db') as db:
        rows = db.execute("SELECT value FROM settings WHERE key LIKE 'cell.lumi.message.%' "
                          "ORDER BY CAST(json_extract(value,'$.time') AS INTEGER),key").fetchall()
    return [json.loads(row[0]) for row in rows]


def setting(profile, key):
    with sqlite3.connect(profile / 'inbe.db') as db:
        row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return row[0] if row else None


def tap_title_button(window, size, button):
    """Lumi's title bar ends 12 units from the right with two 40-unit
    buttons 4 apart: the connection button, then the wrench."""
    width, _, scale = size
    scale /= 10
    centre = 12 + 20 if button == 'wrench' else 12 + 40 + 4 + 20
    tap(window, width - round(centre * scale), round(26 * scale))


def tap_back(window, size):
    """Back leads the settings page's title bar, 52 units tall, right of
    the 88-unit navigation rail of a desktop window."""
    width, height, scale = size
    scale /= 10
    rail = 88 if width > height else 0
    tap(window, round((rail + 32) * scale), round(26 * scale))


def terms_open(window, label):
    return any(row['text'] == 'Agree' for row in words(window, label))


def tap_composer(window, size, label):
    """The composer sits at the bottom, above a bottom navigation bar."""
    width, height, scale = size
    scale /= 10
    labels = [row for row in words(window, label) if row['text'] == 'Habits']
    bottom_bar = [row for row in labels if int(row['top']) > height * 0.8]
    y = int(bottom_bar[0]['top']) - round(76 * scale) if bottom_bar else height - round(40 * scale)
    tap(window, round(width * 0.4), y)


def send(window, profile, text, label):
    before = len(chat(profile))
    tap_composer(window, current_size, label + '-composer')
    command('xdotool', 'type', '--clearmodifiers', '--delay', '18', text)
    time.sleep(0.3)
    command('xdotool', 'keydown', '--clearmodifiers', 'Return')
    time.sleep(0.15)
    command('xdotool', 'keyup', 'Return')
    rows = wait_for(lambda: (rows if len(rows := chat(profile)) >= before + 2 and not rows[-1]['user'] else None),
                    'Lumi did not answer: ' + text)
    return rows[-1]['text']


@contextlib.contextmanager
def application(profile, size, label):
    width, height, scale = size
    log_path = OUTPUT / (label + '.log')
    with log_path.open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zib')], cwd=ROOT,
                               env=ENV | dict(APP_DATA_ROOT=str(profile)), stdout=log, stderr=subprocess.STDOUT)
        try:
            def find():
                assert app.poll() is None, 'Owned app exited: ' + label
                found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                       env=ENV, capture_output=True, text=True, timeout=5)
                return found.stdout.strip().splitlines()[0] if found.returncode == 0 and found.stdout.strip() else ''
            window = wait_for(find, 'Owned app window did not appear', 30)
            command('xdotool', 'windowsize', window, str(width), str(height))
            wait_for(lambda: ' = ' in command('xprop', '-id', window, '_HARMONY_APP_STATE'),
                     'App state did not become ready')
            time.sleep(1.0)
            yield window
            assert app.poll() is None, 'Owned app crashed'
        except BaseException:
            if app.poll() is None and 'window' in locals():
                capture(window, 'failure-' + label)
            raise
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
    assert KEY not in log_path.read_text(errors='replace'), 'The provider key reached the log'


def seed(profile, values):
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        for key, value in values.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, str(value)))


current_size = None


def run(name, size, port):
    global current_size
    current_size = size
    Provider.requests.clear()
    with tempfile.TemporaryDirectory(prefix='inbe-lumi-harness-') as directory:
        profile = Path(directory)
        with application(profile, size, name + '-initialize'):
            pass
        seed(profile, dict(enabled_apps=31, app_used_lists=1, app_used_lumi=1, app_used_habits=1,
                           app_used_practices=1, app_used_diary=1, main_tab=4, language='en',
                           language_setup_done=1, apps_setup_done=1, lumi_introduced=1,
                           package_updates_allowed=0, tutorial_seen=1, habits_guide_seen=1,
                           lumi_guides_seen=127, ui_scale=size[2], navigation_placement=0,
                           lumi_provider='own', lumi_provider_url=f'http://127.0.0.1:{port}/v1',
                           lumi_provider_model='test-model', lumi_provider_key=KEY))
        with application(profile, size, name) as window:
            # Opening Lumi asks right away; "Not now" keeps it offline.
            wait_for(lambda: terms_open(window, name + '-prompt-wait'), 'Opening Lumi did not show the terms')
            capture(window, name + '-prompt-on-open')
            assert not Provider.requests, 'Showing the terms sent something'
            tap_word(window, 'Not', name + '-not-now', lowest=True)
            time.sleep(0.8)
            assert not terms_open(window, name + '-after-not-now'), 'The terms stayed open'
            capture(window, name + '-title-offline')
            # Once a run: leaving Lumi and coming back doesn't ask again.
            action(window, 'mcp.open_view', dict(view='settings'))
            time.sleep(1.5)
            action(window, 'mcp.open_view', dict(view='lumi'))
            time.sleep(0.8)
            assert not terms_open(window, name + '-reopened'), 'The terms showed twice in one run'
            answer = send(window, profile, 'tell me a joke', name + '-1')
            assert 'offline' in answer.lower() or 'title bar' in answer, answer
            answer = send(window, profile, 'add a habit stretching every day at 8', name + '-2')
            assert 'Stretching' in answer, answer
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' in habits, habits
            send(window, profile, 'new habit jumping rope', name + '-2a')
            answer = send(window, profile, 'jumping rope should ask how many I did, higher is better',
                          name + '-2b')
            assert 'How many I did?' in answer, answer
            answer = send(window, profile, 'delete the habit stretching', name + '-2c')
            assert 'Stretching' in answer and 'yes' in answer.lower(), answer
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' in habits, 'Deleted before the person answered'
            answer = send(window, profile, 'yes', name + '-2d')
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' not in habits, habits
            capture(window, name + '-habits-offline')
            assert not Provider.requests, 'Lumi reached the provider while offline'

            tap_title_button(window, size, 'connection')
            wait_for(lambda: terms_open(window, name + '-terms-wait'), 'The terms did not open')
            capture(window, name + '-agreement')
            assert not Provider.requests, 'Opening the terms sent something'
            tap_word(window, 'Agree', name + '-agree', lowest=True)
            time.sleep(0.8)
            capture(window, name + '-title-online')
            assert setting(profile, 'lumi_provider_agreement') == f'1 http://127.0.0.1:{port}/v1'
            assert '"agreed":true' in setting(profile, 'cell.lumi.agreement')

            answer = send(window, profile, 'tell me a joke', name + '-3')
            assert answer == REPLY, answer
            assert len(Provider.requests) == 1, Provider.requests
            request = Provider.requests[0]
            assert request['path'] == '/v1/chat/completions', request['path']
            assert request['authorization'] == 'Bearer ' + KEY
            body = request['body']
            assert body['model'] == 'test-model'
            assert body['messages'][0]['role'] == 'system'
            assert 'Current app context' in body['messages'][0]['content']
            assert body['messages'][-1] == dict(role='user', content='tell me a joke'), body['messages'][-1]
            assert any(tool['function']['name'] == 'create_habit' for tool in body['tools'])
            assert KEY not in json.dumps(body)
            capture(window, name + '-online-answer')

            tap_title_button(window, size, 'connection')
            time.sleep(0.4)
            capture(window, name + '-title-offline-again')
            answer = send(window, profile, 'another joke please', name + '-4')
            assert len(Provider.requests) == 1, 'Lumi reached the provider while switched off'

            # The wrench opens Lumi's settings page; one tap on Back returns
            # to the chat.
            tap_title_button(window, size, 'wrench')
            time.sleep(0.8)
            found = words(window, name + '-settings-lumi-words')
            assert any(row['text'] == 'Read' for row in found), "The wrench did not open Lumi's settings"
            assert any(row['text'] == 'Model' for row in found), "Lumi's settings show no provider"
            assert not any(row['text'] == 'Device' for row in found), "The wrench opened the app's Settings"
            capture(window, name + '-settings-lumi')
            tap_back(window, size)
            time.sleep(0.8)
            found = words(window, name + '-settings-back-words')
            assert not any(row['text'] == 'Model' for row in found), 'One tap on Back did not leave the settings'
            assert any(row['text'] == 'another' for row in found), 'Back did not return to the chat'
            capture(window, name + '-settings-back')
            tap_title_button(window, size, 'wrench')
            time.sleep(0.8)
            assert setting(profile, 'lumi_provider_key') == KEY
            tap_word(window, 'Read', name + '-read-terms')
            time.sleep(0.8)
            capture(window, name + '-agreement-read')
            assert any(row['text'] == 'Withdraw' for row in words(window, name + '-withdraw')), \
                'The agreed terms do not offer Withdraw'


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Provider)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    for name, size in SIZES.items():
        run(name, size, server.server_address[1])
finally:
    server.shutdown()
print('Lumi harness UI: terms on opening once a run, offline until agreed, connection button, '
      f"own provider request, and the wrench to Lumi's settings and Back passed; screenshots in {OUTPUT.relative_to(ROOT)}")
