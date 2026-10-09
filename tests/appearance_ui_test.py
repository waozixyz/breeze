"""KSS editor and app-owned Lumi tools on an owned private Xvfb window."""
import ast
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/appearance-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
ENV = os.environ | dict(APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy',
                        YUE_DESKTOP_RECOVERY='0')
for key in ('WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
    ENV.pop(key, None)
sequence = 0
receipts = []


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


@contextlib.contextmanager
def application(profile, label, width=900, height=720):
    with (OUTPUT / (label + '.log')).open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zib')],
                               cwd=ROOT, env=ENV | dict(APP_DATA_ROOT=str(profile)),
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            def find():
                assert app.poll() is None, 'Owned application exited: ' + label
                found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                       env=ENV, capture_output=True, text=True, timeout=5)
                return found.stdout.strip().splitlines()[0] if found.returncode == 0 else ''
            window = wait_for(find, 'Owned app window did not appear')
            command('xdotool', 'windowsize', window, str(width), str(height))
            command('xdotool', 'windowfocus', window)
            wait_for(lambda: ' = ' in command('xprop', '-id', window, '_HARMONY_APP_STATE'),
                     'App state did not become ready')
            yield window
            assert app.poll() is None, 'Owned app crashed'
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)


def state(window):
    value = command('xprop', '-id', window, '_HARMONY_APP_STATE')
    return json.loads(ast.literal_eval(value.split(' = ', 1)[1]))


def tool(window, name, arguments):
    global sequence
    sequence += 1
    request = 'appearance-' + str(sequence)
    payload = dict(request_id=request, control='mcp.' + name, arguments=arguments)
    command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
            '-set', '_HARMONY_APP_ACTION', json.dumps(payload))
    report = wait_for(lambda: (value if (value := state(window))['last_request_id'] == request else None),
                      'App tool did not acknowledge: ' + name)
    receipts.append(dict(request=payload, result=report['tool_result']))
    return report['tool_result']


def read(window, scope='all'):
    result = tool(window, 'read_style', dict(scope=scope))
    assert result['ok'], result
    return result


def change(window, name, scope='all', **arguments):
    revision = read(window, scope)['revision']
    return tool(window, name, dict(scope=scope, revision=revision, **arguments))


def capture(window, label):
    path = OUTPUT / (label + '.png')
    command('import', '-window', window, str(path))
    return path


def words(window):
    path = capture(window, 'current')
    enlarged = OUTPUT / 'ocr.png'
    command('convert', str(path), '-resize', '300%', str(enlarged))
    tsv = command('tesseract', str(enlarged), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
    rows = [row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t')
            if row.get('text', '').strip()]
    for row in rows:
        for key in ('left', 'top', 'width', 'height'):
            row[key] = str(int(row[key]) // 3)
    return rows


def tap(window, x, y):
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    command('xdotool', 'mousedown', '1')
    time.sleep(.12)
    command('xdotool', 'mouseup', '1')
    time.sleep(.3)


def locate(window, phrase, scroll=False):
    expected = phrase.lower().split()
    for attempt in range(14 if scroll else 1):
        rows = words(window)
        for i in range(len(rows) - len(expected) + 1):
            if [re.sub(r'[^a-z0-9:]', '', row['text'].lower())
                for row in rows[i:i + len(expected)]] == expected:
                first = rows[i]
                if phrase == 'save':
                    line = [row for row in rows if all(row[key] == first[key]
                            for key in ('block_num', 'par_num', 'line_num'))]
                    if len(line) != 1:
                        continue
                return int(first['left']) + int(first['width']) // 2, int(first['top']) + int(first['height']) // 2
        if scroll:
            width = int(re.search(r'WIDTH=(\d+)', command('xdotool', 'getwindowgeometry', '--shell', window))[1])
            command('xdotool', 'mousemove', '--window', window, str(width - 60), '500', 'click', '--repeat', '3', '5')
            time.sleep(.2)
    raise AssertionError('Rendered control not found: ' + phrase + '\n' + ' '.join(row['text'] for row in rows))


with tempfile.TemporaryDirectory(prefix='inbe-appearance-') as directory:
    profile = Path(directory)
    with application(profile, 'initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        settings = dict(enabled_apps='31', language='en', language_setup_done='1',
                        apps_setup_done='1', tutorial_seen='1', habits_guide_seen='1',
                        lumi_introduced='1', cells_auto_update='0')
        for name in ('lists', 'habits', 'practices', 'diary', 'lumi'):
            settings['app_used_' + name] = '1'
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))
    with application(profile, 'editor', height=1100) as window:
        published = {item['name'] for item in state(window)['mcp']['tools']}
        assert {'read_style', 'inspect_style', 'preview_style', 'save_style', 'reset_style',
                'discard_style', 'undo_style', 'format_style'} <= published
        assert read(window)['rule_limit'] == 512
        original = read(window)['revision']
        assert change(window, 'preview_style', source='Button { radius: 24; }')['ok']
        assert not tool(window, 'reset_style', dict(scope='all', revision=original))['ok']
        inspected = tool(window, 'inspect_style', dict(scope='all', widget='Button', state='normal'))
        assert inspected['ok'] and 'radius: 24' in inspected['inspection'], inspected
        assert not change(window, 'preview_style', source='Button { radius: unknown; }')['ok']
        assert read(window)['preview_source'] == 'Button { radius: 24; }'
        assert not change(window, 'save_style')['ok']
        assert change(window, 'undo_style')['ok']
        assert change(window, 'save_style')['ok']
        assert change(window, 'preview_style', scope='habits', source='Button { radius: 7; }')['ok']
        assert change(window, 'save_style', scope='habits')['ok']
        inspected = tool(window, 'inspect_style', dict(scope='habits', widget='Button', state='normal'))
        assert 'radius: 7' in inspected['inspection'], inspected
        inspected = tool(window, 'inspect_style', dict(scope='lists', widget='Button', state='normal'))
        assert 'radius: 24' in inspected['inspection'], inspected
        assert change(window, 'reset_style', scope='habits')['ok']
        assert change(window, 'reset_style')['ok']
        tool(window, 'open_view', dict(view='appearance'))
        tap(window, *locate(window, 'advanced appearance', scroll=True))
        wait_for(lambda: state(window)['appearance']['open'], 'Advanced editor did not open')
        capture(window, 'desktop-editor')
        tap(window, *locate(window, 'radius:', scroll=True))
        command('xdotool', 'key', '--clearmodifiers', 'ctrl+a')
        command('xdotool', 'type', '--clearmodifiers', '--delay', '10', 'Button { radius: 19; }')
        wait_for(lambda: state(window)['appearance']['source'] == 'Button { radius: 19; }',
                 'Manual typing did not update KSS draft')
        time.sleep(.5)
        inspected = tool(window, 'inspect_style', dict(scope='all', widget='Button', state='normal'))
        assert inspected['ok'] and 'radius: 19' in inspected['inspection'], inspected
        tap(window, *locate(window, 'save', scroll=True))
        wait_for(lambda: read(window)['saved_source'] == 'Button { radius: 19; }', 'UI save did not persist')
        capture(window, 'saved-preview')
    with application(profile, 'restart') as window:
        assert read(window)['saved_source'] == 'Button { radius: 19; }'
        assert change(window, 'reset_style')['ok']
        assert read(window)['saved_source'] == ''
        tool(window, 'open_view', dict(view='appearance'))
        tap(window, *locate(window, 'advanced appearance', scroll=True))
        tap(window, *locate(window, 'ask lumi', scroll=True))
        capture(window, 'lumi-handoff')
        assert state(window)['feature'] == 16
    with application(profile, 'phone', width=390, height=844) as window:
        assert read(window)['saved_source'] == ''
        tool(window, 'open_view', dict(view='appearance'))
        tap(window, *locate(window, 'advanced appearance', scroll=True))
        locate(window, 'radius:', scroll=True)
        capture(window, 'phone-editor')
    with sqlite3.connect(profile / 'inbe.db') as db:
        assert db.execute("SELECT value FROM settings WHERE key='appearance.kss.all'").fetchone()[0] == ''

(OUTPUT / 'results.json').write_text(json.dumps(receipts, indent=2) + '\n')
print('Appearance: real editor, live validation, scopes, save/restart, reset and Lumi handoff passed')
