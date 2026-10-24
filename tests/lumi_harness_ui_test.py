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
reopens the terms, and one tap on its Back returns to the chat.

The app is driven through Kryon's test driver: buttons are found in its
widget tree and pressed, and messages typed, through its own input path.
"""
import ast
import contextlib
import http.server
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

from ui_driver import UiDriver

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
driver = UiDriver(OUTPUT / 'driver')
# Lumi's title bar buttons, from apps/lumi/lumi_view.zi.
CONNECTION_KEY = 300401
WRENCH_KEY = 300390


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


def terms_open():
    return bool(driver.find(label='Agree and go online', role='button', visible=True))


def send(profile, text):
    before = len(chat(profile))
    driver.press(role='text_area')
    driver.type(text)
    driver.wait(role='text_area', value=text)
    driver.key('enter')
    rows = wait_for(lambda: (rows if len(rows := chat(profile)) >= before + 2 and not rows[-1]['user'] else None),
                    'Lumi did not answer: ' + text)
    return rows[-1]['text']


def connection(state):
    """Lumi's title bar connection button, once its label says state."""
    return driver.wait(key=CONNECTION_KEY, label=state)


@contextlib.contextmanager
def application(profile, size, label):
    width, height, _ = size
    log_path = OUTPUT / (label + '.log')
    with log_path.open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zx')], cwd=ROOT,
                               env=ENV | driver.environment() | dict(APP_DATA_ROOT=str(profile)),
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, log_path)
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
            # The app lays out at the window's shape, whatever its scale.
            wait_for(lambda: abs((screen := driver.wait(role='screen'))['width'] * height -
                                 screen['height'] * width) <= width * height // 100,
                     'The app did not take the window size')
            driver.wait_idle(frames=3)
            yield window
            assert app.poll() is None, 'Owned app crashed'
        except BaseException:
            if app.poll() is None:
                with contextlib.suppress(Exception):
                    (OUTPUT / ('failure-' + label + '.json')).write_text(json.dumps(driver.tree(), indent=1))
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


def run(name, size, port):
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
            wait_for(terms_open, 'Opening Lumi did not show the terms')
            assert not Provider.requests, 'Showing the terms sent something'
            driver.press(label='Not now', role='button')
            driver.wait_gone(label='Agree and go online', role='button')
            connection('Offline')
            # Once a run: leaving Lumi and coming back doesn't ask again.
            action(window, 'mcp.open_view', dict(view='settings'))
            driver.wait(label='Device', role='button')
            action(window, 'mcp.open_view', dict(view='lumi'))
            driver.wait(role='text_area')
            driver.wait_idle(frames=3)
            assert not terms_open(), 'The terms showed twice in one run'
            answer = send(profile, 'tell me a joke')
            assert 'offline' in answer.lower() or 'title bar' in answer, answer
            answer = send(profile, 'add a habit stretching every day at 8')
            assert 'Stretching' in answer, answer
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' in habits, habits
            send(profile, 'new habit jumping rope')
            answer = send(profile, 'jumping rope should ask how many I did, higher is better')
            assert 'How many I did?' in answer, answer
            answer = send(profile, 'delete the habit stretching')
            assert 'Stretching' in answer and 'yes' in answer.lower(), answer
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' in habits, 'Deleted before the person answered'
            answer = send(profile, 'yes')
            habits = {item['title'] for item in action(window, 'mcp.read_context')['tool_result']['habits']}
            assert 'Stretching' not in habits, habits
            assert not Provider.requests, 'Lumi reached the provider while offline'

            driver.press(key=CONNECTION_KEY)
            wait_for(terms_open, 'The terms did not open')
            assert not Provider.requests, 'Opening the terms sent something'
            driver.press(label='Agree and go online', role='button')
            driver.wait_gone(label='Agree and go online', role='button')
            assert connection('Online')['selected'], 'The connection button does not show online'
            assert setting(profile, 'lumi_provider_agreement') == f'1 http://127.0.0.1:{port}/v1'
            assert '"agreed":true' in setting(profile, 'cell.lumi.agreement')

            answer = send(profile, 'tell me a joke')
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
            driver.wait(label=REPLY, role='text')

            driver.press(key=CONNECTION_KEY)
            assert not connection('Offline')['selected'], 'The connection button still shows online'
            answer = send(profile, 'another joke please')
            assert len(Provider.requests) == 1, 'Lumi reached the provider while switched off'

            # The wrench opens Lumi's settings page; one tap on Back returns
            # to the chat.
            driver.press(key=WRENCH_KEY)
            driver.wait(label='Read the terms', role='button')
            assert driver.find(label='Model', visible=True), "Lumi's settings show no provider"
            assert not driver.find(label='Device', visible=True), "The wrench opened the app's Settings"
            assert KEY not in json.dumps(driver.tree()), 'The settings page shows the provider key'
            driver.press(label='Back', role='button')
            driver.wait_gone(label='Model')
            driver.wait(label='another joke please', role='text')
            driver.press(key=WRENCH_KEY)
            driver.wait(label='Read the terms', role='button')
            assert setting(profile, 'lumi_provider_key') == KEY
            driver.press(label='Read the terms', role='button')
            driver.wait(label='Withdraw agreement', role='button')


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Provider)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    for name, size in SIZES.items():
        run(name, size, server.server_address[1])
finally:
    server.shutdown()
print('Lumi harness UI: terms on opening once a run, offline until agreed, connection button, '
      "own provider request, and the wrench to Lumi's settings and Back passed")
