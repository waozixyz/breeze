"""KSS editor and app-owned Lumi tools on an owned private Xvfb window.

The app runs with Kryon's test driver: the editor's controls are found in
its widget tree, pressed and typed into through its own input path.
"""
import ast
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/appearance-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
driver = UiDriver(OUTPUT / 'driver')
ENV = os.environ | dict(APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy',
                        YUE_DESKTOP_RECOVERY='0') | driver.environment()
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
    log_path = OUTPUT / (label + '.log')
    with log_path.open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zx')],
                               cwd=ROOT, env=ENV | dict(APP_DATA_ROOT=str(profile)),
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, log_path)
        try:
            def find():
                assert app.poll() is None, 'Owned application exited: ' + label
                found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                       env=ENV, capture_output=True, text=True, timeout=5)
                return found.stdout.strip().splitlines()[0] if found.returncode == 0 else ''
            window = wait_for(find, 'Owned app window did not appear')
            command('xdotool', 'windowsize', window, str(width), str(height))
            wait_for(lambda: ' = ' in command('xprop', '-id', window, '_HARMONY_APP_STATE'),
                     'App state did not become ready')
            wait_for(lambda: driver.tree()[0]['width'] == width, 'App did not take its window size')
            driver.wait_idle(frames=3)
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


def previewed_radius(window, radius):
    """The Button inspection once the editor's draft previews `radius`."""
    inspected = tool(window, 'inspect_style', dict(scope='all', widget='Button', state='normal'))
    if f'radius: {radius}' in inspected.get('inspection', ''):
        return inspected
    return None


def reveal(**selector):
    """Scroll the Settings panel down until a widget shows, as a wheel would."""
    for attempt in range(14):
        found = driver.find(visible=True, **selector)
        if found:
            return found[0]
        panel = [node for node in driver.tree() if node['kind'] == 'scroll' and node['visible']]
        assert panel, 'Settings has no scrolling panel'
        x, y = UiDriver.center(panel[-1])
        driver.pointer(x, y, wheel=-3)
        driver.release_pointer()
    raise AssertionError(f'Control not found: {selector}\n{driver.text()}')


def press(**selector):
    reveal(**selector)
    driver.press(**selector)


with tempfile.TemporaryDirectory(prefix='inbe-appearance-') as directory:
    profile = Path(directory)
    with application(profile, 'initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        settings = dict(enabled_apps='31', language='en', language_setup_done='1',
                        apps_setup_done='1', tutorial_seen='1', habits_guide_seen='1', lumi_guides_seen='127',
                        lumi_introduced='1', package_updates_allowed='0')
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
        press(label='Advanced appearance (KSS)', role='button')
        wait_for(lambda: state(window)['appearance']['open'], 'Advanced editor did not open')
        press(label='Custom KSS', role='text_area')
        wait_for(lambda: driver.find(label='Custom KSS', role='text_area')[0]['focused'],
                 'The KSS editor did not take focus')
        driver.key('a', control=True)
        driver.type('Button { radius: 19; }')
        wait_for(lambda: state(window)['appearance']['source'] == 'Button { radius: 19; }',
                 'Manual typing did not update KSS draft')
        driver.wait(label='Custom KSS', role='text_area', value='Button { radius: 19; }')
        # The typed draft previews live once the editor pauses.
        inspected = wait_for(lambda: previewed_radius(window, 19), 'Typed KSS did not preview')
        assert inspected['ok'] and 'radius: 19' in inspected['inspection'], inspected
        press(label='Save', role='button')
        wait_for(lambda: read(window)['saved_source'] == 'Button { radius: 19; }', 'UI save did not persist')
    with application(profile, 'restart') as window:
        assert read(window)['saved_source'] == 'Button { radius: 19; }'
        assert change(window, 'reset_style')['ok']
        assert read(window)['saved_source'] == ''
        tool(window, 'open_view', dict(view='appearance'))
        press(label='Advanced appearance (KSS)', role='button')
        press(label='Ask Lumi', role='button')
        wait_for(lambda: state(window)['feature'] == 16, 'Ask Lumi did not hand off to Lumi')
    with application(profile, 'phone', width=390, height=844) as window:
        assert read(window)['saved_source'] == ''
        tool(window, 'open_view', dict(view='appearance'))
        press(label='Advanced appearance (KSS)', role='button')
        reveal(label='Custom KSS', role='text_area')
    with sqlite3.connect(profile / 'inbe.db') as db:
        assert db.execute("SELECT value FROM settings WHERE key='appearance.kss.all'").fetchone()[0] == ''

(OUTPUT / 'results.json').write_text(json.dumps(receipts, indent=2) + '\n')
print('Appearance: real editor, live validation, scopes, save/restart, reset and Lumi handoff passed')
