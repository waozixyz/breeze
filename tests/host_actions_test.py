"""Actual app routes and practice actions on a private Xvfb and profile."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DISPLAY_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')
assert all(not os.environ.get(key) for key in DISPLAY_KEYS)

with tempfile.TemporaryDirectory(prefix='inbe-host-actions-') as temporary:
    root = Path(temporary)
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(HOME=str(root), APP_DATA_ROOT=str(root / 'profile'),
               XDG_CONFIG_HOME=str(root / 'config'), XDG_DATA_HOME=str(root / 'data'),
               YUE_DESKTOP_RECOVERY='0', APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy', SDL_VIDEODRIVER='x11',
               LIBGL_ALWAYS_SOFTWARE='1', INBE_DEBUG_ROUTE='1')
    with (root / 'app.log').open('w+b') as log:
        display = subprocess.Popen(['Xvfb', '-displayfd', '1', '-screen', '0',
                                    '1024x768x24', '-nolisten', 'tcp'],
                                   env=env, stdout=subprocess.PIPE, stderr=log)
        app = None
        try:
            number = display.stdout.readline().decode().strip()
            assert number.isdecimal()
            display.stdout.close()
            env['DISPLAY'] = ':' + number
            binary = Path(sys.argv[1]).resolve()
            app = subprocess.Popen([str(binary), '--bundle', str(ROOT / 'build/inbe-full.zib'),
                                    '--feature', 'habits'],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)

            def command(*args):
                return subprocess.run(args, env=env, text=True, capture_output=True,
                                      check=True, timeout=5).stdout.strip()

            def wait(read, predicate, label):
                deadline = time.monotonic() + 20
                last = None
                while time.monotonic() < deadline:
                    assert app.poll() is None, (root / 'app.log').read_text()[-2000:]
                    try:
                        last = read()
                        if predicate(last):
                            return last
                    except (subprocess.CalledProcessError, ValueError, SyntaxError, IndexError):
                        pass
                    time.sleep(.08)
                raise AssertionError((label, last, (root / 'app.log').read_text()[-2000:]))

            window = wait(lambda: command('xdotool', 'search', '--onlyvisible', '--pid',
                                           str(app.pid)).splitlines()[0], bool, 'owned window')

            def state():
                prop = command('xprop', '-id', window, '_HARMONY_APP_STATE')
                return json.loads(ast.literal_eval(prop.split(' = ', 1)[1]))

            def feature(value, screen):
                command('xprop', '-id', window, '-f', '_HARMONY_APP_FEATURE', '32c',
                        '-set', '_HARMONY_APP_FEATURE', str(value))
                wait(state, lambda s: s['feature'] == value and s['screen'] == screen, 'feature route')
                time.sleep(.3)
                assert state()['screen'] == screen, 'The router restored the previous screen'

            def action(control, request, ok=True, arguments=None):
                payload = dict(control=control, request_id=request)
                if arguments is not None:
                    payload['arguments'] = arguments
                command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
                        '-set', '_HARMONY_APP_ACTION', json.dumps(payload))
                return wait(state, lambda s: s['last_request_id'] == request and
                            s['last_request_ok'] is ok, 'app acknowledgement')

            wait(state, lambda s: s['feature'] == 2 and s['screen'] == 11, 'cold habits')
            tools = {tool['name']: tool for tool in state()['mcp']['tools']}
            assert {'get_settings', 'set_theme', 'set_theme_mode', 'set_setting', 'open_view', 'practice'} <= tools.keys()
            assert tools['set_theme']['inputSchema']['required'] == ['theme']
            assert action('mcp.set_theme', 'forest', arguments={'theme': 'forest'})['settings']['theme'] == 'forest'
            assert action('mcp.set_theme_mode', 'dark', arguments={'mode': 'dark'})['settings']['theme_mode'] == 2
            assert action('mcp.set_theme', 'unknown-theme', False, {'theme': 'unknown'})['settings']['theme'] == 'forest'
            assert action('mcp.set_theme', 'forest', False, {'theme': 'ocean'})['settings']['theme'] == 'forest'
            assert action('mcp.set_setting', 'compact', arguments={'name': 'sidebar_compact', 'value': 1})['settings']['sidebar_compact'] == 1
            assert action('mcp.set_setting', 'invalid-scale', False, {'name': 'scale', 'value': 99})['settings']['scale'] == 10
            assert action('mcp.open_view', 'appearance', arguments={'view': 'appearance'})['screen'] == 6
            feature(8, 22)
            assert state()['feature'] == 8
            assert any(control['control'] == 'open.diary' and control['enabled']
                       for control in state()['controls'])
            feature(4, 0)
            feature(1, 16)
            feature(2, 11)
            feature(16, 23)
            assert action('open.lumi', 'open-lumi')['screen'] == 23
            started = action('practice.whm.start', 'start-whm')
            assert started['practice_running'] and started['practice'] == 0 and not started['paused']
            progressed = wait(state, lambda s: s['breath'] > started['breath'], 'practice advances')
            replayed = action('practice.whm.start', 'start-whm')
            assert replayed['breath'] >= progressed['breath'], 'Replay reset the practice'
            action('practice.pause', 'start-whm', False)
            assert not state()['paused'], 'Conflicting request ID changed the practice'
            assert action('practice.pause', 'pause-whm')['paused']
            assert not action('practice.resume', 'resume-whm')['paused']
            print('Cold Habits, same-process Practices/Lists/Habits, WHM start and progression, replay/conflict handling, pause/resume: passed')
        finally:
            for process in (app, display):
                if process is None:
                    continue
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
