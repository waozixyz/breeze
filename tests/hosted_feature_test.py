"""Direct cell opens omit app navigation, on an owned private Xvfb display."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
OUTPUT = ROOT / 'build/hosted-feature-test'
OUTPUT.mkdir(parents=True, exist_ok=True)


def run(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def wait_for(predicate, message):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


with tempfile.TemporaryDirectory(prefix='inbe-hosted-feature-') as directory:
    env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory,
               APP_NO_TRAY='1', APP_SHOT_WINDOW='1', YUE_DESKTOP_RECOVERY='0')
    env.pop('DBUS_SESSION_BUS_ADDRESS', None)
    env.pop('WAYLAND_DISPLAY', None)
    with (OUTPUT / 'app.log').open('w') as log:
        app = subprocess.Popen([
            sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zib'),
            '--feature', 'practices', '--screenshot', str(OUTPUT / 'initial.png'),
            '--screenshot-scene', 'start_practice', '--screenshot-width', '900',
            '--screenshot-height', '720',
        ], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            def window():
                assert app.poll() is None, 'Owned test application exited'
                result = subprocess.run(['xdotool', 'search', '--onlyvisible',
                                         '--pid', str(app.pid), '--name', 'Inner Breeze'],
                                        capture_output=True, text=True, timeout=5)
                return result.stdout.strip().splitlines()[0] if result.returncode == 0 else ''
            target = wait_for(window, 'Owned app window did not appear')

            def state():
                value = run('xprop', '-id', target, '_HARMONY_APP_STATE')
                match = re.search(r'=\s*(".*")', value)
                return json.loads(json.loads(match[1])) if match else {}

            wait_for(lambda: state().get('host_feature') == 4, 'Practice child did not isolate navigation')
            time.sleep(.3)
            run('import', '-window', target, str(OUTPUT / 'practices.png'))
            for feature, name in ((2, 'habits'), (0, 'parent'), (4, 'practices-again')):
                run('xprop', '-id', target, '-f', '_HARMONY_APP_FEATURE', '32c',
                    '-set', '_HARMONY_APP_FEATURE', str(feature))
                wait_for(lambda: state().get('host_feature') == feature, 'Feature request was not applied')
                time.sleep(.3)
                run('import', '-window', target, str(OUTPUT / (name + '.png')))
            (OUTPUT / 'state.json').write_text(json.dumps(state(), indent=2) + '\n')
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
print('Practice/Habits child navigation and parent restoration passed')
