"""Run only on Alpha with the actual Breeze test-driver build on private Xvfb."""
import contextlib
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
WORKOUT_ACTIVITY = 6  # EXERCISE_WORKOUT
DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'GDK_DISPLAY', 'SESSION_MANAGER', 'WAYLAND_SOCKET', 'DBUS_STARTER_ADDRESS',
                'DBUS_STARTER_BUS_TYPE')


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def fixture_settings(profile):
    settings = {
        'language': 'en', 'language_system': '0', 'language_setup_done': '1',
        'apps_setup_done': '1', 'tutorial_seen': '1', 'habits_guide_seen': '1',
        'lumi_guides_seen': '127', 'launcher_guide_seen': '1', 'package_updates_allowed': '0',
        'workout_routine': '1', 'workout_custom_v1_0': 'workout/2\nExisting routine\n',
    }
    with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
        user = database.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        database.executemany(
            'INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
            'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value',
            ((user, key, value) for key, value in settings.items()),
        )


def saved(profile):
    with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
        return dict(database.execute("SELECT key,value FROM settings WHERE key LIKE 'workout_%'"))


def enter_builder(driver):
    driver.press(label='Customize', role='button')
    driver.press(label='Custom workouts', role='button')
    driver.wait(label='Routine unavailable', role='button')
    # A preset can unlock a toast over the library's top row.
    driver.wait_gone(contains='Achievement unlocked', role='text')


def assert_character(driver, chosen):
    for label in ('Woman', 'Man'):
        assert driver.wait(label=label, role='button')['selected'] == (label == chosen)


def adjust_seconds(driver, seconds):
    driver.press(label='Active seconds', role='text_field')
    driver.key('a', control=True)
    driver.type(str(seconds))
    driver.key('enter')


def add(driver, exercise, seconds):
    driver.press(label='Add exercise', role='button')
    driver.press(label=exercise, role='button')
    adjust_seconds(driver, seconds)


def create_routine(driver, profile):
    enter_builder(driver)
    driver.press(label='New routine', role='button')
    driver.press(label='Routine name', role='text_field')
    driver.type('Mat and wall')
    add(driver, 'Squats', 75)
    driver.press(label='Standard form', role='button')
    driver.wait(label='Shallow', role='button')
    add(driver, 'Push-ups', 5)
    driver.press(label='Duplicate', role='button')
    driver.wait(label='3. Push-ups · 5 sec', role='button')
    driver.press(label='Remove exercise', role='button')
    driver.wait_gone(label='3. Push-ups · 5 sec', role='button')
    add(driver, 'Wall sit', 5)
    driver.press(label='Up', role='button')
    driver.wait(label='2. Wall sit · 5 sec', role='button')
    driver.wait(label='3. Push-ups · 5 sec', role='button')
    driver.wait(label='117 s total · 85 s active · 32 s transitions', role='text')
    driver.press(label='Save', role='button')
    driver.wait(label='Routine saved.', role='text')
    data = saved(profile)
    assert data['workout_custom_v1_0'] == 'workout/2\nExisting routine\n'
    assert data['workout_custom_v1_1'] == 'workout/1\nMat and wall\nsquats 75 3\nwall_sit 5 0\npush_ups 5 0\n'
    assert data['workout_routine'] == '1'


def capture_pose(window, figure, output, name, env):
    x, y, width, height = (round(figure[key]) for key in ('x', 'y', 'width', 'height'))
    path = output / f'{name}.png'
    subprocess.run(['import', '-window', window, '-crop', f'{width}x{height}+{x}+{y}', str(path)],
                   env=env, check=True, timeout=5)
    with Image.open(path) as image:
        assert image.size == (width, height)
        return image.convert('RGB')


def app_window(app, env):
    return subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                   env=env, text=True, timeout=5).splitlines()[0]


def pause_at_start(driver, exercise):
    driver.wait(label=exercise, role='image')
    driver.press(label='Pause', role='button', settle=False)
    driver.wait(label='Resume', role='button')
    driver.press(label=exercise, role='button', settle=False)


def exit_routine(driver):
    driver.press(label='Close', role='button', settle=False)
    driver.press(label='Exit', role='button')
    if driver.wait(label='4-Minute Workout')['kind'] == 'button':
        driver.press(label='Back', role='button')
    driver.wait(label='4-Minute Workout', role='text')


def assert_different_models(first, second):
    difference = ImageChops.difference(first, second).convert('L')
    visible_pixels = difference.histogram()[24:]
    assert sum(visible_pixels) > 1_000, 'The two character renders look identical'


def preset_poses(driver, profile, window, output, character, env):
    poses = []
    for title, exercise, count in (('7-Minute Workout', 'Jumping jacks', 10),
                                   ('4-Minute Workout', 'Step jacks', 15)):
        driver.press(label='Customize', role='button')
        assert_character(driver, character)
        driver.press(label=title, role='button')
        driver.press(label='Back', role='button')
        driver.wait(label=title, role='text')
        driver.press(label='Start Practice', role='button')
        pause_at_start(driver, exercise)
        driver.wait(label=str(count), role='text')
        figure = driver.wait(label=exercise, role='image')
        poses.append(capture_pose(window, figure, output, f'{title[0]}min-{character.lower()}', env))
        driver.press(label='Close', role='button', settle=False)
        driver.press(label='Exit', role='button')
        driver.wait(label=title, role='text')
    assert saved(profile)['workout_routine'] == '1'
    return poses


def capture_custom_character(driver, window, output, character, env):
    driver.press(label='Start routine', role='button')
    driver.wait(label='Mat and wall', role='text')
    pause_at_start(driver, 'Squats')
    figure = driver.wait(label='Squats', role='image')
    return capture_pose(window, figure, output, f'custom-{character.lower()}', env)


def play_routine(driver, profile, output, window, env):
    enter_builder(driver)
    driver.press(label='Mat and wall', role='button')
    driver.wait(label='117 s total · 85 s active · 32 s transitions', role='text')
    driver.press(label='3. Push-ups · 5 sec', role='button')
    adjust_seconds(driver, 6)
    driver.wait(label='118 s total · 86 s active · 32 s transitions', role='text')
    driver.press(label='Save', role='button')
    driver.wait(label='Routine saved.', role='text')
    assert saved(profile)['workout_custom_v1_1'].endswith('push_ups 6 0\n')
    pose = capture_custom_character(driver, window, output, 'Man', env)
    driver.press(label='Wall sit', role='button', settle=False)
    driver.wait(label='Transition to the next exercise', role='text')
    driver.wait(label='11', role='text')
    assert driver.wait(label='Wall sit', role='button')['selected']
    driver.press(label='Push-ups', role='button', settle=False)
    figure = driver.wait(label='Push-ups', role='image')
    driver.wait(label='16', role='text')
    wall = capture_pose(window, figure, output, 'wall', env)
    driver.press(label='Resume', role='button', settle=False)
    # This bridge first stands up and walks away from the wall, then moves
    # down to the mat. Let the real session advance to its active interval.
    driver.wait(label='8', role='text', timeout=20)
    standing = capture_pose(window, figure, output, 'standing', env)
    driver.wait(label='4', role='text')
    lowering = capture_pose(window, figure, output, 'lowering', env)
    driver.wait(label='Exercise 3 of 3', role='text', timeout=30)
    driver.wait(label='6', role='text')
    driver.wait(label='Push-ups', role='image')
    floor = capture_pose(window, figure, output, 'floor', env)
    for before, after in zip((wall, standing, lowering), (standing, lowering, floor)):
        assert ImageChops.difference(before, after).getbbox(), 'The rendered workout pose did not change'
    exit_routine(driver)
    assert saved(profile)['workout_routine'] == '1'
    with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
        # Seeking skipped more than a minute. History credits only played time.
        count = database.execute('SELECT COUNT(*) FROM sessions WHERE deleted_at=0 AND activity=?',
                                 (WORKOUT_ACTIVITY,)).fetchone()[0]
        assert count == 0, f'Scrubbing created {count} workout history rows'
    return pose


def main(binary, bundle):
    assert all(not os.environ.get(key) for key in DESKTOP_KEYS), 'Inherited desktop environment'
    output = ROOT / 'build/workout-custom-ui-test'
    output.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        profile = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='profile-', dir=output)))
        local_files = {}
        for variable in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME',
                         'XDG_STATE_HOME', 'XDG_RUNTIME_DIR'):
            directory = profile / variable.lower()
            directory.mkdir(mode=0o700)
            local_files[variable] = str(directory)
        env = os.environ | local_files | {
            'HARMONY_DESKTOP_RECOVERY': '0', 'YUE_DESKTOP_RECOVERY': '0',
            'APP_DATA_ROOT': str(profile), 'INBE_SCREENSHOT_DATA_ROOT': str(profile),
            'APP_SHOT_WINDOW': '1', 'APP_NO_TRAY': '1', 'SDL_VIDEODRIVER': 'x11',
            'SDL_AUDIODRIVER': 'dummy',
            'LIBGL_ALWAYS_SOFTWARE': '1', 'LP_NUM_THREADS': '2',
        }
        display_log = stack.enter_context((output / 'display.log').open('w'))
        display = subprocess.Popen(['Xvfb', '-noreset', '-displayfd', '1', '-screen', '0',
                                    '1280x1100x24', '-nolisten', 'tcp'], env=env,
                                   stdout=subprocess.PIPE, stderr=display_log)
        stack.callback(stop, display)
        number = display.stdout.readline().decode().strip()
        display.stdout.close()
        assert number.isdecimal() and display.poll() is None
        env['DISPLAY'] = ':' + number
        cache = profile / 'packages'
        cache.mkdir()
        for pack in ('workout.zx', 'workout.en.zx'):
            shutil.copyfile(ROOT / 'build/practice-content' / pack, cache / ('practice-' + pack))
        driver = UiDriver(profile / 'driver')
        env.update(driver.environment())
        arguments = [str(binary), '--bundle', str(bundle)]
        with (output / 'bootstrap.log').open('w') as log:
            bootstrap = subprocess.Popen(arguments, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                while not (profile / 'inbe.db').exists():
                    assert bootstrap.poll() is None and time.monotonic() < deadline
                    time.sleep(.05)
                driver.attach(bootstrap, output / 'bootstrap.log')
                driver.send('status')
            finally:
                stop(bootstrap)
        fixture_settings(profile)
        arguments += ['--screenshot', str(profile / 'unused.png'), '--screenshot-scene', 'workout_home',
                      '--screenshot-width', '910', '--screenshot-height', '1000',
                      '--screenshot-ui-scale', '10', '--screenshot-theme', '0']
        for step in (1, 2):
            log_path = output / f'app-{step}.log'
            with log_path.open('w') as log:
                driver.reset()
                app = subprocess.Popen(arguments, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                driver.attach(app, log_path)
                try:
                    driver.wait(label='Customize', role='button')
                    window = app_window(app, env)
                    if step == 1:
                        woman = preset_poses(driver, profile, window, output, 'Woman', env)
                        create_routine(driver, profile)
                        woman.append(capture_custom_character(driver, window, output, 'Woman', env))
                        exit_routine(driver)
                        driver.press(label='Customize', role='button')
                        driver.press(label='Man', role='button')
                        assert_character(driver, 'Man')
                        assert saved(profile)['workout_character'] == '1'
                        driver.press(label='Back', role='button')
                    else:
                        man = preset_poses(driver, profile, window, output, 'Man', env)
                        man.append(play_routine(driver, profile, output, window, env))
                        for female_pose, male_pose in zip(woman, man):
                            assert_different_models(female_pose, male_pose)
                    assert app.poll() is None
                finally:
                    stop(app)
    print('Custom workout UI: create, edit, reopen, play, pause, seek and render both characters across all routines')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
