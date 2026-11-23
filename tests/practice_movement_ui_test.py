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

from PIL import Image, ImageChops

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/practice-movement-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'GDK_DISPLAY', 'SESSION_MANAGER', 'WAYLAND_SOCKET', 'DBUS_STARTER_ADDRESS',
                'DBUS_STARTER_BUS_TYPE')
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
    env.update(HARMONY_DESKTOP_RECOVERY='0', YUE_DESKTOP_RECOVERY='0', APP_NO_TRAY='1', SDL_VIDEODRIVER='x11',
               SDL_AUDIODRIVER='dummy', LIBGL_ALWAYS_SOFTWARE='1', LP_NUM_THREADS='2', APP_SHOT_WINDOW='1')
    display_log = stack.enter_context((OUTPUT / 'display.log').open('w'))
    display = subprocess.Popen(['Xvfb', '-noreset', ':953', '-displayfd', '1', '-screen', '0',
                                '1280x1100x24', '-nolisten', 'tcp'], env=env,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and int(number) >= 300 and display.poll() is None
    env['DISPLAY'] = ':' + number

    @contextlib.contextmanager
    def application(scene, width=411, height=900, scale=10, language='en'):
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
                             '--screenshot-width', str(width), '--screenshot-height', str(height),
                             '--screenshot-ui-scale', str(scale), '--screenshot-theme', '0']
                bootstrap = subprocess.Popen(arguments[:3], cwd=ROOT, env=local_env,
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
                    for key, value in {'language': language, 'language_system': '0', 'language_setup_done': '1',
                                       'apps_setup_done': '1', 'tutorial_seen': '1', 'habits_guide_seen': '1',
                                       'lumi_guides_seen': '127', 'launcher_guide_seen': '1',
                                       'package_updates_allowed': '0', 'voice_narration_enabled': '0',
                                       'guide_narration_enabled': '0', 'workout_routine': '0'}.items():
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

    def bounds(node):
        return tuple(node[part] for part in ('x', 'y', 'width', 'height'))

    def breath_image(window, local_env, profile, label):
        # Only the cue to the left of the label is sampled on the private Xvfb.
        path = profile / 'breath.png'
        subprocess.run(['import', '-window', window, str(path)], env=local_env, check=True, timeout=5)
        x, y, _, height = bounds(label)
        with Image.open(path) as image:
            return image.convert('RGB').crop((round(x - 36), round(y), round(x - 3), round(y + height)))

    def color_distance(first, second):
        return sum((index % 256) * count
                   for index, count in enumerate(ImageChops.difference(first, second).histogram()))

    for width, height in ((411, 900), (1280, 900)):
        with application('sun_salutation_session', width, height) as (driver, profile, window, local_env):
            driver.wait(label='Settle in', role='text')
            stage = bounds(driver.wait(label='Sun Salutation', role='image'))

            def capture_breath(label, next_label):
                samples = []
                deadline = time.monotonic() + 12
                while not driver.find(label=next_label, role='text', visible=True):
                    samples.append(breath_image(window, local_env, profile, label))
                    assert time.monotonic() < deadline, f'Breath did not change to {next_label}'
                    time.sleep(.12)
                assert samples
                return samples

            # Window startup may use most of the first inhale. Start sampling
            # at the next breath boundary to observe both complete directions.
            exhale = driver.wait(label='Breathe out', role='text')
            exhaling = capture_breath(exhale, 'Breathe in')
            inhale = driver.wait(label='Breathe in', role='text')
            inhaling = capture_breath(inhale, 'Breathe out')
            driver.wait(label='Mountain pose', role='text')
            driver.press(label='Pause', role='button', settle=False)
            driver.wait(label='PLAY', role='button')
            paused = breath_image(window, local_env, profile, inhale)
            time.sleep(.25)
            assert ImageChops.difference(paused, breath_image(window, local_env, profile, inhale)).getbbox() is None

            images = []
            for pose, breath in (('Upward salute', 'Breathe in'), ('Standing forward fold', 'Breathe out'),
                                 ('Low lunge', 'Breathe in')):
                driver.press(label='Next', role='button', settle=False)
                driver.wait(label=pose, role='text')
                label = driver.wait(label=breath, role='text')
                assert bounds(driver.wait(label='Sun Salutation', role='image')) == stage, pose
                images.append(breath_image(window, local_env, profile, label))
            driver.wait(contains='leg back', role='text')
            empty, full, lunge = images
            assert color_distance(lunge, empty) == 0
            driver.press(label='Back', role='button', settle=False)
            driver.wait(label='Standing forward fold', role='text')
            assert color_distance(breath_image(window, local_env, profile, exhale), full) == 0

            full_distance = color_distance(empty, full)
            assert full_distance > 5000, 'The circle does not visibly fill at a breath boundary'

            def nearest(samples, target, name):
                fill, sample = min(((color_distance(empty, sample) / full_distance, sample)
                                    for sample in samples), key=lambda value: abs(value[0] - target))
                assert abs(fill - target) < .16, (name, width, fill)
                sample.save(OUTPUT / f'sun-breath-{width}-{name}.png')

            assert color_distance(empty, inhaling[-1]) > color_distance(empty, inhaling[0])
            assert color_distance(empty, exhaling[0]) > color_distance(empty, exhaling[-1])
            nearest(inhaling, .5, 'inhale-half')
            nearest(inhaling, 1, 'inhale-full')
            nearest(exhaling, .5, 'exhale-half')
            nearest(exhaling, 0, 'exhale-empty')

    with application('astral_projection_session') as (driver, profile, window, local_env):
        driver.wait(label='Resume', role='button')
        assert state(window, local_env)['paused']
        driver.press(label='Resume', role='button')
        driver.wait(label='Pause', role='button')
        assert not state(window, local_env)['paused']
        driver.press(label='Pause', role='button')
        driver.wait(label='Resume', role='button')
        assert state(window, local_env)['paused']

    with application('workout_home', 800, 1050, 12, 'de') as (driver, profile, window, local_env):
        driver.wait(label='7-Minuten-Workout')
        driver.press(label='Praxis starten', role='button')
        pause = driver.wait(label='Pause', role='button')
        figure = driver.wait(label='Hampelmann', role='image')
        heading = driver.wait(label='Hampelmann', role='text')
        center = figure['x'] + figure['width'] / 2
        assert abs(heading['x'] + heading['width'] / 2 - center) <= 2, heading
        assert abs(pause['x'] + pause['width'] / 2 - center) <= 2, pause
        assert state(window, local_env)['practice_running']
        driver.press(label='Pause', role='button')
        driver.wait(label='Fortsetzen', role='button')
        assert state(window, local_env)['paused']
        driver.press(label='Fortsetzen', role='button')
        driver.wait(label='Pause', role='button')
        assert not state(window, local_env)['paused']

    with application('workout_home') as (driver, profile, window, local_env):
        driver.wait(label='7-Minute Workout')
        subprocess.run(['xdotool', 'windowfocus', window, 'key', 'Right'],
                       env=local_env, check=True, timeout=5)
        driver.wait(label='4-Minute Workout', role='text')
        assert saved(profile, 'workout_routine', '1') == '1'
        driver.press(label='Start Practice', role='button')
        driver.wait(label='4-Minute Workout', role='text')
        driver.wait(label='Step jacks', role='image')
        assert state(window, local_env)['practice_running']
        steps = ('Step jacks', 'Mini squats', 'Heel raises', 'Easy march', 'Side reaches', 'Back taps')
        for step in steps:
            control = driver.wait(label=step, role='button')
            assert control['width'] >= 44 and control['height'] >= 44, control
        for exercise in ('Jumping jacks', 'Push-ups', 'Side plank'):
            assert not driver.find(label=exercise, role='button', visible=True)
        assert driver.wait(label='Step jacks', role='button')['selected']
        driver.wait(label='Exercise 1 of 6', role='text', timeout=30)
        driver.press(label='Back taps', role='button')
        driver.wait(label='Back taps', role='image')
        driver.wait(label='Rest before the next exercise', role='text')
        assert driver.wait(label='Back taps', role='button')['selected']
        driver.press(label='Pause', role='button')
        driver.wait(label='Resume', role='button')
        driver.press(label='Mini squats', role='button')
        driver.wait(label='Mini squats', role='image')
        assert state(window, local_env)['paused']
        assert driver.wait(label='Mini squats', role='button')['selected']
        driver.wait(label='15', role='text')
        driver.wait(label='Rest before the next exercise', role='text')
        for _ in range(30):
            driver.key('tab')
            if driver.wait(label='Step jacks', role='button')['focused']:
                break
        assert driver.wait(label='Step jacks', role='button')['focused']
        driver.key('enter')
        driver.wait(label='Step jacks', role='image')
        assert driver.wait(label='Step jacks', role='button')['selected']
        assert state(window, local_env)['paused']
        driver.press(label='Resume', role='button')
        driver.wait(label='Pause', role='button')
        assert not state(window, local_env)['paused']
        driver.press(label='Close', role='button')
        driver.press(label='Exit', role='button')
        subprocess.run(['xdotool', 'windowfocus', window, 'key', 'Left'],
                       env=local_env, check=True, timeout=5)
        driver.wait(label='7-Minute Workout', role='text')
        assert saved(profile, 'workout_routine', '0') == '0'
        driver.press(label='Start Practice', role='button')
        driver.wait(label='Exercise 1 of 12', role='text', timeout=25)
        first = driver.wait(label='Jumping jacks', role='button')
        last = driver.wait(label='Side plank', role='button')
        assert last['y'] >= first['y'] + 44, (first, last)
        for step in ('Step-ups', 'Squats', 'Triceps dips', 'Plank', 'High knees', 'Push-up and rotation'):
            control = driver.wait(label=step, role='button')
            assert control['width'] >= 44 and control['height'] >= 44, control
        driver.press(key=last['key'], role='button')
        driver.wait(label='Side plank', role='image')
        assert driver.wait(label='Side plank', role='button')['selected']

print('Sun Salutation guidance, Astral controls, and both Workout routines with pointer and keyboard step navigation passed')
