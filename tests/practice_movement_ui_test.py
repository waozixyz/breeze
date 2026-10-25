"""Exercise package movement controls and saved settings on a private display."""
import ast
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/practice-movement-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'GDK_DISPLAY', 'SESSION_MANAGER')
assert all(not os.environ.get(key) for key in DESKTOP_KEYS), 'Inherited desktop environment'
BINARY = Path(sys.argv[1]).resolve()
BUNDLE = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / 'build/inbe-full.zx'


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_KEYS}
    env.update(YUE_DESKTOP_RECOVERY='0', APP_NO_TRAY='1', SDL_VIDEODRIVER='x11',
               SDL_AUDIODRIVER='dummy', LIBGL_ALWAYS_SOFTWARE='1', LP_NUM_THREADS='2', APP_SHOT_WINDOW='1')
    display_log = stack.enter_context((OUTPUT / 'display.log').open('w'))
    display = subprocess.Popen(['Xvfb', '-noreset', ':953', '-displayfd', '1', '-screen', '0',
                                '1280x900x24', '-nolisten', 'tcp'], env=env,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and int(number) >= 300 and display.poll() is None
    env['DISPLAY'] = ':' + number

    @contextlib.contextmanager
    def application(scene):
        with tempfile.TemporaryDirectory(prefix='profile-', dir=OUTPUT) as directory:
            profile = Path(directory)
            cache = profile / 'packages'
            cache.mkdir()
            for name in ('sunsalutation', 'astral_projection', 'workout'):
                shutil.copyfile(ROOT / 'build/practice-content' / (name + '.zx'),
                                cache / ('practice-' + name + '.zx'))
            driver = UiDriver(profile / 'driver')
            local_env = env | driver.environment() | {'INBE_SCREENSHOT_DATA_ROOT': str(profile), 'APP_DATA_ROOT': str(profile)}
            log_path = OUTPUT / (scene + '.log')
            with log_path.open('w') as log:
                arguments = [str(BINARY), '--bundle', str(BUNDLE), '--screenshot',
                             str(OUTPUT / 'unused.png'), '--screenshot-scene', scene,
                             '--screenshot-width', '411', '--screenshot-height', '900',
                             '--screenshot-ui-scale', '10', '--screenshot-theme', '0']
                bootstrap = subprocess.Popen(arguments, cwd=ROOT, env=local_env,
                                             stdout=log, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 20
                    while not (profile / 'inbe.db').exists():
                        assert bootstrap.poll() is None
                        assert time.monotonic() < deadline
                        time.sleep(.05)
                    time.sleep(.5)
                finally:
                    stop(bootstrap)
                with sqlite3.connect(profile / 'inbe.db') as db:
                    user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
                    for key, value in {'language': 'en', 'language_system': '0', 'language_setup_done': '1',
                                       'apps_setup_done': '1', 'tutorial_seen': '1', 'habits_guide_seen': '1',
                                       'lumi_guides_seen': '127', 'launcher_guide_seen': '1',
                                       'package_updates_allowed': '0', 'voice_narration_enabled': '0',
                                       'guide_narration_enabled': '0'}.items():
                        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                                   "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
                driver.reset()
                app = subprocess.Popen(arguments, cwd=ROOT, env=local_env, stdout=log, stderr=subprocess.STDOUT)
                driver.attach(app, log_path)
                try:
                    deadline = time.monotonic() + 20
                    window = ''
                    while time.monotonic() < deadline:
                        assert app.poll() is None, log_path.read_text()[-4000:]
                        found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                               env=local_env, capture_output=True, text=True, timeout=2)
                        if found.returncode == 0 and (profile / 'inbe.db').exists():
                            window = found.stdout.splitlines()[0]
                            break
                        time.sleep(.05)
                    assert window, log_path.read_text()[-4000:]
                    yield driver, profile, window, local_env
                    assert app.poll() is None, log_path.read_text()[-4000:]
                    assert 'frame rejected' not in log_path.read_text()
                finally:
                    stop(app)

    def state(window, environment):
        output = subprocess.check_output(['xprop', '-id', window, '_HARMONY_APP_STATE'],
                                         env=environment, text=True, timeout=5)
        return json.loads(ast.literal_eval(output.split(' = ', 1)[1]))

    def saved(profile, key, expected=None):
        deadline = time.monotonic() + 5
        while True:
            with sqlite3.connect(profile / 'inbe.db', timeout=3) as db:
                row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            value = row[0] if row else None
            if expected is None or value == expected or time.monotonic() >= deadline:
                return value
            time.sleep(.05)

    with application('practice_config_sun_salutation') as (driver, profile, window, local_env):
        slider = driver.wait(label='Rounds', role='slider')
        x = slider['x'] + slider['width'] * .98
        y = slider['y'] + slider['height'] * .7
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)
        driver.release_pointer()
        assert saved(profile, 'sun_salutation_repetitions', '12') == '12'
        driver.press(label='Woman with bun', role='dropdown')
        driver.press(label='Man with short hair', role='option')
        assert saved(profile, 'sun_salutation_character', '1') == '1'

    with application('astral_projection_session') as (driver, profile, window, local_env):
        driver.wait(label='Resume', role='button')
        assert state(window, local_env)['paused']
        driver.press(label='Resume', role='button')
        driver.wait(label='Pause', role='button')
        assert not state(window, local_env)['paused']
        driver.press(label='Pause', role='button')
        driver.wait(label='Resume', role='button')
        assert state(window, local_env)['paused']

    with application('workout_home') as (driver, profile, window, local_env):
        driver.press(label='Start Practice', role='button')
        driver.wait(label='Pause', role='button')
        assert state(window, local_env)['practice_running']
        driver.press(label='Pause', role='button')
        driver.wait(label='Resume', role='button')
        assert state(window, local_env)['paused']
        driver.press(label='Resume', role='button')
        driver.wait(label='Pause', role='button')
        assert not state(window, local_env)['paused']

print('Sun Salutation saved settings, Astral pause/resume and Workout start/pause/resume passed')
