"""Observe and control a synthetic account session on an owned Xvfb window."""
import ast
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

assert os.environ.get('INBE_ACTIVITY_PRIVATE_DISPLAY') == '1'
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/account-activity-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
ENV = os.environ | dict(APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy',
                        SDL_VIDEODRIVER='x11', YUE_DESKTOP_RECOVERY='0')
for key in ('WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
    ENV.pop(key, None)


def command(*args):
    return subprocess.check_output(args, env=ENV, text=True, timeout=10).strip()


def wait_for(predicate, message):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


def state(window):
    value = command('xprop', '-id', window, '_HARMONY_APP_STATE')
    return json.loads(ast.literal_eval(value.split(' = ', 1)[1]))


sequence = 0


def action(window, control):
    global sequence
    sequence += 1
    request = 'activity-' + str(sequence)
    payload = dict(request_id=request, control=control, arguments={})
    command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
            '-set', '_HARMONY_APP_ACTION', json.dumps(payload))
    return wait_for(lambda: (value if (value := state(window))['last_request_id'] == request else None),
                    'App did not acknowledge activity control')


def capture(window, label):
    path = OUTPUT / (label + '.png')
    command('import', '-window', window, str(path))
    from PIL import Image
    enlarged = OUTPUT / 'ocr.png'
    with Image.open(path) as source:
        source.resize((source.width * 3, source.height * 3)).save(enlarged)
    return command('tesseract', str(enlarged), 'stdout', '--psm', '11').lower()


with tempfile.TemporaryDirectory(prefix='inbe-account-activity.') as temporary:
    profile = Path(temporary) / 'runner'
    subprocess.run([sys.argv[2]], env=ENV | dict(APP_DATA_ROOT=temporary),
                   check=True, capture_output=True, timeout=20)
    database = sqlite3.connect(profile / 'inbe.db', timeout=5)
    user = database.execute('SELECT id FROM users LIMIT 1').fetchone()[0]

    def setting(key, value):
        database.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,?) '
                         'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
                         (user, key, str(value), int(time.time())))

    owner = database.execute("SELECT value FROM settings WHERE key='sync_public_id'").fetchone()[0]
    database.execute("UPDATE meta SET value=? WHERE key='sync_data_owner_public_id'", (owner,))
    for key, value in dict(sync_enabled=1, sync_server_url='', language='en', language_setup_done=1,
                           enabled_apps=31, tutorial_seen=1, launcher_guide_seen=1,
                           practice_guide_seen=1, habits_guide_seen=1).items():
        setting(key, value)
    remote = dict(version=1, session_id='a' * 32, device_id='b' * 64, control_id='',
                  time=int(time.time()), revision=1, active=1, paused=0, screen=2,
                  phase=0, round=0, count=0, elapsed=120, remaining=480,
                  duration=600, cycles=0, total=0)

    def publish(**changes):
        remote.update(changes)
        setting('cell.lumi.activity.current', json.dumps(remote, separators=(',', ':')))
        database.commit()

    publish()
    with (OUTPUT / 'app.log').open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zib')],
                               cwd=ROOT, env=ENV | dict(APP_DATA_ROOT=str(profile)),
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            def find_window():
                assert app.poll() is None, 'Owned test app exited'
                result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                        env=ENV, capture_output=True, text=True, timeout=5)
                return result.stdout.strip().splitlines()[0] if result.returncode == 0 else ''

            window = wait_for(find_window, 'Owned test app window did not appear')
            command('xdotool', 'windowsize', window, '900', '720')
            command('xdotool', 'windowfocus', window)
            wait_for(lambda: ' = ' in command('xprop', '-id', window, '_HARMONY_APP_STATE'),
                     'App state did not appear')
            wait_for(lambda: state(window).get('account_activity_fresh'), 'Remote session did not load')
            assert action(window, 'open.practices')['last_request_ok']
            time.sleep(.4)
            text = capture(window, 'running')
            assert 'meditation' in text and 'running on another device' in text, text
            report = state(window)
            assert not report['practice_running'], 'Observer started a duplicate practice'
            assert report['account_activity']['session_id'] == remote['session_id']
            assert not next(item for item in report['controls'] if item['control'] == 'practice.meditation.start')['enabled']
            assert action(window, 'practice.pause')['last_request_ok']
            row = database.execute("SELECT value FROM settings WHERE key='cell.lumi.activity.control'").fetchone()
            control = json.loads(row[0])
            assert control['session_id'] == remote['session_id'] and control['paused'] == 1
            publish(paused=1, revision=2, control_id=control['id'], time=int(time.time()))
            wait_for(lambda: state(window)['account_activity']['paused'] == 1, 'Pause acknowledgement did not load')
            assert 'paused on another device' in capture(window, 'paused')
            publish(time=int(time.time()) - 25)
            wait_for(lambda: not state(window)['account_activity_fresh'], 'Stale session remained fresh')
            report = state(window)
            assert not next(item for item in report['controls'] if item['control'] == 'practice.resume')['enabled']
            assert 'last known session' in capture(window, 'stale')
            command('xdotool', 'windowsize', window, '411', '813')
            time.sleep(.4)
            assert 'last known session' in capture(window, 'phone-stale')
            publish(active=0, revision=3, time=int(time.time()))
            wait_for(lambda: state(window)['account_activity'] is None, 'Completed session remained active')
            assert database.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
            database.close()

print('Account activity UI, host controls, acknowledgement, stale state and completion passed')
