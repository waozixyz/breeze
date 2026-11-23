"""Run only on Alpha with the actual Breeze test-driver build on private Xvfb."""
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

from PIL import Image, ImageChops, ImageStat

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
WORKOUT_ACTIVITY = 6  # EXERCISE_WORKOUT
CAROUSEL_PREVIOUS = 7091
CAROUSEL_NEXT = 7092
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
        'music_volume': '0', 'sound_volume': '80', 'voice_narration_enabled': '1',
        'guide_narration_enabled': '0',
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


def enter_customize(driver):
    select_short_preset(driver)
    driver.press(label='Customize', role='button')
    title = driver.wait(label='Customize', role='title_bar')
    woman, man = [driver.wait(label=label, role='image') for label in ('Woman', 'Man')]
    left, right = driver.center(woman), driver.center(man)
    assert left[1] == right[1] and abs((left[0] + right[0]) / 2 - driver.center(title)[0]) <= 2
    assert not any(node['kind'] == 'navigation_bar' and node['visible'] for node in driver.tree())
    for label in ('New routine', 'Routine name', 'Routine unavailable', 'Manage workouts', 'Custom workout'):
        assert not driver.find(label=label, visible=True)
    for label in ('Woman', 'Man'):
        card = driver.wait(label=label, role='button')
        assert 44 <= card['width'] <= 155 and 44 <= card['height'] <= 190, card


def select_short_preset(driver):
    deadline = time.monotonic() + 20
    titles = {'7-Minute Workout', '4-Minute Workout', 'Custom workout'}
    while True:
        title = next((node['label'] for node in driver.tree() if node['visible'] and
                      node['kind'] == 'text' and node['label'] in titles), None)
        if title is not None:
            break
        assert time.monotonic() < deadline, 'Workout carousel did not become visible'
        time.sleep(.05)
    if title == 'Custom workout':
        driver.press(key=CAROUSEL_PREVIOUS, role='button')
    elif title == '7-Minute Workout':
        driver.press(key=CAROUSEL_NEXT, role='button')
    driver.wait(label='4-Minute Workout', role='text')


def open_routine_library(driver):
    if not driver.find(label='Manage workouts', role='button', visible=True):
        select_short_preset(driver)
        driver.press(key=CAROUSEL_NEXT, role='button')
    driver.wait(label='Custom workout', role='text')
    driver.wait(label='3 / 3', role='text')
    assert not driver.find(label='Customize', role='button', visible=True)
    driver.press(label='Manage workouts', role='button')
    driver.wait(label='New routine', role='button')
    for title in ('4-Minute Workout', '7-Minute Workout', 'Presets'):
        assert not driver.find(label=title, role='button', visible=True)
    driver.wait(label='Routine unavailable', role='button')
    # A preset can unlock a toast over the library's top row.
    driver.wait_gone(contains='Achievement unlocked', role='text')


def assert_character(driver, chosen):
    for label in ('Woman', 'Man'):
        assert driver.wait(label=label, role='button')['selected'] == (label == chosen)


def choose_character(driver, label):
    preview = driver.wait(label=label, role='image')
    x, y = driver.center(preview)
    driver.pointer(x, y)
    driver.pointer(x, y, down=True)
    driver.pointer(x, y, down=False)
    driver.release_pointer()
    assert_character(driver, label)


def reveal_builder(driver, label, role='button'):
    driver.wait(label=label, role=role, visible=False)
    for _ in range(20):
        driver.wait_idle(frames=2, timeout=1)
        nodes = {node['index']: node for node in driver.tree()}
        node = next(node for node in nodes.values()
                    if node['label'] == label and role in (node['role'], node['kind']))
        if node['visible'] and node['visible_height'] >= node['height'] - 1:
            return
        viewport = nodes[node['parent']]
        while viewport['kind'] != 'scroll':
            viewport = nodes[viewport['parent']]
        direction = 2 if node['y'] < viewport['visible_y'] else -2
        driver.pointer(*driver.center(viewport), wheel=direction)
        driver.release_pointer()
    raise AssertionError(f'Workout manager control remained clipped: {label}')


def press_builder(driver, label, role='button'):
    reveal_builder(driver, label, role)
    driver.press(label=label, role=role)


def tap(driver, node):
    x, y = driver.center(node)
    driver.pointer(x, y)
    driver.pointer(x, y, down=True)
    driver.pointer(x, y, down=False)
    driver.release_pointer()
    driver.wait_idle(frames=2, timeout=2)


def step(driver, label, presses):
    """Press a block's length stepper: each press is five seconds."""
    sign = '+' if presses > 0 else '-'
    for _ in range(abs(presses)):
        reveal_builder(driver, label, 'spinbox')
        nodes = driver.tree()
        box = next(node for node in nodes if node['label'] == label and node['visible'] and
                   'spinbox' in (node['role'], node['kind']))
        tap(driver, next(node for node in nodes if node['parent'] == box['index'] and node['label'] == sign))


def add(driver, exercise, presses):
    press_builder(driver, 'Add block')
    press_builder(driver, exercise)
    reveal_builder(driver, 'Length', 'spinbox')
    step(driver, 'Length', presses)


def blocks(driver, labels):
    """The visible blocks among labels, top to bottom."""
    nodes = [node for node in driver.tree() if node['label'] in labels and node['visible'] and
             'button' in (node['role'], node['kind'])]
    return [node['label'] for node in sorted(nodes, key=lambda node: node['y'])]


def create_routine(driver, profile):
    open_routine_library(driver)
    driver.press(label='New routine', role='button')
    driver.press(label='Routine name', role='text_field')
    driver.type('Mat and wall')
    add(driver, 'Squats', 9)
    press_builder(driver, 'Shallow')
    add(driver, 'Push-ups', -5)
    press_builder(driver, 'Duplicate')
    assert blocks(driver, {'Push-ups'}) == ['Push-ups', 'Push-ups']
    press_builder(driver, 'Remove')
    driver.wait_gone(label='Length', role='spinbox')
    assert blocks(driver, {'Push-ups'}) == ['Push-ups']
    add(driver, 'Wall sit', -5)
    press_builder(driver, 'Up')
    order = blocks(driver, {'Squats', 'Push-ups', 'Wall sit'})
    assert order == ['Squats', 'Wall sit', 'Push-ups'], order
    reveal_builder(driver, '1:57 total · 1:25 active · 3 exercises', 'text')
    press_builder(driver, 'Save')
    driver.wait(label='Routine saved.', role='text')
    data = saved(profile)
    assert data['workout_custom_v1_0'] == 'workout/2\nExisting routine\n'
    assert data['workout_custom_v1_1'] == ('workout/2\nMat and wall\ne 0 squats 75 3 0\ne 0 wall_sit 5 0 0\n'
                                           'e 0 push_ups 5 0 0\n'), data['workout_custom_v1_1']
    assert data['workout_routine'] == '2'


def capture_pose(driver, window, figure, output, name, env):
    frame = driver.tree()[0]
    # Widget coordinates are in the frame's logical space, including the rail offset.
    x = round(figure['x'] - frame['x'])
    y = round(figure['y'] - frame['y'])
    width, height = (round(figure[key]) for key in ('width', 'height'))
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
    driver.wait(contains='Starting in', role='text')


def exit_routine(driver):
    driver.press(label='Close', role='button', settle=False)
    driver.press(label='Exit', role='button')
    select_short_preset(driver)


def assert_different_models(first, second):
    for image in (first, second):
        assert max(ImageStat.Stat(image).stddev) > 4, 'A character render is blank'
    difference = ImageChops.difference(first, second).convert('L')
    visible_pixels = difference.histogram()[24:]
    assert sum(visible_pixels) > 1_000, 'The two character renders look identical'


def select_preset(driver, title, window, env):
    driver.wait(label='Start Practice', role='button')
    if not driver.find(label=title, role='text', visible=True):
        direction = 'Right' if title == '4-Minute Workout' else 'Left'
        subprocess.run(['xdotool', 'windowfocus', window, 'key', direction],
                       env=env, check=True, timeout=5)
    driver.wait(label=title, role='text')


def disk_audio(path):
    if not path.exists():
        return False
    with path.open('rb') as stream:
        return any(chunk.strip(b'\0') for chunk in iter(lambda: stream.read(1_048_576), b''))


def assert_starting_in(driver, number):
    driver.wait(label=number, role='text')
    nodes = [node for node in driver.tree() if node['kind'] == 'text' and node['visible']]
    numerals = [node for node in nodes if node['label'] == number]
    labels = [node for node in nodes if node['label'] == 'Starting in']
    assert len(numerals) == len(labels) == 1
    assert labels[0]['y'] + labels[0]['height'] <= numerals[0]['y'] + 1
    assert not any(node['label'].startswith('Starting in ') for node in nodes)


def delayed_preset_start(driver, scene_ready, audio_path, window, env):
    select_preset(driver, '7-Minute Workout', window, env)
    driver.press(label='Start Practice', role='button')
    driver.wait(label='Loading workout…', role='text')
    time.sleep(3)
    driver.wait(label='Loading workout…', role='text')
    assert not driver.find(contains='Starting in', role='text', visible=True)
    assert not disk_audio(audio_path), 'Narration started before the scene was ready'
    driver.press(label='Pause', role='button')
    driver.wait(label='Resume', role='button')
    scene_ready.touch()
    driver.wait(label='Jumping jacks', role='image')
    assert_starting_in(driver, '10')
    time.sleep(2)
    assert not disk_audio(audio_path), 'Narration started while the session was paused'
    assert_starting_in(driver, '10')
    driver.press(label='Resume', role='button', settle=False)
    assert_starting_in(driver, '9')
    deadline = time.monotonic() + 3
    while not disk_audio(audio_path):
        assert time.monotonic() < deadline, 'The English workout introduction never played after readiness'
        time.sleep(.05)
    driver.wait(label='Exercise 1 of 12', role='text', timeout=20)
    driver.press(label='Close', role='button', settle=False)
    driver.press(label='Exit', role='button')
    select_preset(driver, '7-Minute Workout', window, env)


def preset_poses(driver, profile, window, output, character, env):
    poses = []
    for title, exercise in (('7-Minute Workout', 'Jumping jacks'), ('4-Minute Workout', 'Step jacks')):
        select_preset(driver, title, window, env)
        driver.press(label='Start Practice', role='button')
        pause_at_start(driver, exercise)
        figure = driver.wait(label=exercise, role='image')
        poses.append(capture_pose(driver, window, figure, output, f'{title[0]}min-{character.lower()}', env))
        if title == '7-Minute Workout':
            driver.press(label='Resume', role='button', settle=False)
            driver.wait(label='Exercise 1 of 12', role='text', timeout=20)
            driver.press(label='Lunges', role='button', settle=False)
            driver.wait(label='Exercise 10 of 12', role='text', timeout=20)
            figure = driver.wait(label='Lunges', role='image')
            time.sleep(.8)
            driver.press(label='Pause', role='button', settle=False)
            driver.wait(label='Resume', role='button')
            capture_pose(driver, window, figure, output, f'lunge-{character.lower()}', env)
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
    return capture_pose(driver, window, figure, output, f'custom-{character.lower()}', env)


def play_routine(driver, profile, output, window, env):
    open_routine_library(driver)
    driver.press(label='Mat and wall', role='button')
    driver.wait(label='1:57 total · 1:25 active · 3 exercises', role='text')
    press_builder(driver, 'Push-ups')
    step(driver, 'Length', 1)
    reveal_builder(driver, '2:02 total · 1:30 active · 3 exercises', 'text')
    press_builder(driver, 'Save')
    driver.wait(label='Routine saved.', role='text')
    assert saved(profile)['workout_custom_v1_1'].endswith('e 0 push_ups 10 0 0\n')
    pose = capture_custom_character(driver, window, output, 'Man', env)
    driver.press(label='Resume', role='button', settle=False)
    driver.wait(label='Exercise 1 of 3', role='text', timeout=25)
    driver.press(label='Pause', role='button', settle=False)
    driver.wait(label='Resume', role='button')
    driver.press(label='Wall sit', role='button', settle=False)
    driver.wait(label='Transition to the next exercise', role='text')
    driver.wait(label='11', role='text')
    assert driver.wait(label='Wall sit', role='button')['selected']
    driver.press(label='Push-ups', role='button', settle=False)
    figure = driver.wait(label='Push-ups', role='image')
    driver.wait(label='16', role='text')
    wall = capture_pose(driver, window, figure, output, 'wall', env)
    driver.press(label='Resume', role='button', settle=False)
    # This bridge first stands up and walks away from the wall, then moves
    # down to the mat. Let the real session advance to its active interval.
    driver.wait(label='8', role='text', timeout=20)
    leaving_wall = capture_pose(driver, window, figure, output, 'leaving-wall', env)
    driver.wait(label='7', role='text')
    standing = capture_pose(driver, window, figure, output, 'standing', env)
    driver.wait(label='4', role='text')
    lowering = capture_pose(driver, window, figure, output, 'lowering', env)
    driver.wait(label='Exercise 3 of 3', role='text', timeout=30)
    driver.wait(label='6', role='text')
    driver.wait(label='Push-ups', role='image')
    floor = capture_pose(driver, window, figure, output, 'floor', env)
    for before, after in zip((wall, leaving_wall, standing, lowering), (leaving_wall, standing, lowering, floor)):
        assert ImageChops.difference(before, after).getbbox(), 'The rendered workout pose did not change'
    exit_routine(driver)
    assert saved(profile)['workout_routine'] == '1'
    with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
        # Seeking skipped more than a minute. History credits only played time.
        count = database.execute('SELECT COUNT(*) FROM sessions WHERE deleted_at=0 AND activity=?',
                                 (WORKOUT_ACTIVITY,)).fetchone()[0]
        assert count == 0, f'Scrubbing created {count} workout history rows'
    return pose


def work_of(values, index):
    """A Workout checkpoint's covered work for one step: four fields, then each step's preparation and work."""
    steps = (len(values) - 4) // 2
    return values[4 + steps + index]


def checkpoint(profile, matches):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
            row = database.execute('SELECT json FROM practice_draft WHERE id=1').fetchone()
        if row:
            try:
                draft = json.loads(row[0])
            except json.JSONDecodeError:
                draft = {}
            if 'resume' in draft and matches(draft['resume']['values']):
                return draft
        time.sleep(.05)
    raise AssertionError(f'Expected recovery checkpoint did not appear: {row!r}')


def recovery_prompt(driver, title, stage=None):
    driver.wait(label='Interrupted practice')
    driver.wait(label=title, role='text')
    if stage:
        driver.wait(label=stage, role='text')
    assert not driver.find(label='Save', role='button', visible=True)
    assert driver.wait(label='Cancel', role='button')['height'] >= 44
    driver.wait(contains='elapsed', role='text')
    assert driver.wait(label='Continue', role='button')['height'] >= 44


def recovery_test(arguments, env, profile, driver, output):
    routine = 'workout/1\nRecovery circuit\nsquats 35 3\npush_ups 12 0\n'
    upgraded = 'workout/2\nRecovery circuit\ne 0 squats 35 3 0\ne 0 push_ups 12 0 0\n'
    legacy = '{"schema":1,"started_at":1794800000,"activity":1,"topic":0,"rounds":[42]}'

    def setting(key, value):
        with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
            user = database.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            database.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                             'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))

    @contextlib.contextmanager
    def running(name, scene='workout_home'):
        log_path = output / f'recovery-{name}.log'
        with log_path.open('w') as log:
            app = subprocess.Popen(arguments + ['--screenshot', str(profile / 'unused.png'),
                                   '--screenshot-scene', scene, '--screenshot-width', '411',
                                   '--screenshot-height', '900', '--screenshot-ui-scale', '10'],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                yield app
            finally:
                stop(app)

    def interrupt(app):
        assert app.poll() is None
        app.kill()
        assert app.wait(timeout=5) == -9

    def history():
        with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
            return database.execute('SELECT COUNT(*) FROM sessions WHERE deleted_at=0 AND activity IN (1,3,6)').fetchone()[0]

    count_before = history()
    setting('workout_custom_v1_1', routine)
    with running('workout-before') as app:
        enter_customize(driver)
        choose_character(driver, 'Man')
        driver.press(label='Back', role='button')
        open_routine_library(driver)
        driver.press(label='Recovery circuit', role='button')
        driver.press(label='Start routine', role='button')
        driver.wait(label='Exercise 1 of 2', role='text')
        checkpoint(profile, lambda v: work_of(v, 0) > 1000)
        driver.press(label='Pause', role='button', settle=False)
        driver.wait(label='Resume', role='button')
        first = checkpoint(profile, lambda v: v[1] == 1 and work_of(v, 0) > 1000)
        interrupt(app)
    setting('workout_character', '0')
    setting('workout_custom_v1_1', routine.replace('Recovery circuit', 'Edited circuit'))
    with running('workout-continued', 'meditation_home') as app:
        recovery_prompt(driver, 'Recovery circuit', 'Squats · Exercise 1 of 2')
        subprocess.run(['import', '-window', app_window(app, env), str(output / 'recovery-workout.png')],
                       env=env, check=True, timeout=5)
        driver.press(label='Continue', role='button', settle=False)
        driver.wait(label='Exercise 1 of 2', role='text')
        elapsed = first['resume']['values'][2]
        later = checkpoint(profile, lambda v: v[2] > elapsed)
        assert later['started_at'] == first['started_at']
        assert later['resume']['values'][1] == 1 and later['resume']['values'][2] - elapsed < 3000
        assert bytes.fromhex(later['resume']['definition']).decode() == upgraded
        interrupt(app)
    with running('workout-repeated') as app:
        recovery_prompt(driver, 'Recovery circuit', 'Squats · Exercise 1 of 2')
        driver.press(label='Continue', role='button', settle=False)
        driver.wait(label='Exercise 1 of 2', role='text')
        repeat = checkpoint(profile, lambda v: v[2] > later['resume']['values'][2])
        assert repeat['started_at'] == first['started_at']
        interrupt(app)
    with running('workout-canceled'):
        recovery_prompt(driver, 'Recovery circuit')
        driver.press(label='Cancel', role='button')
        driver.wait_gone(label='Interrupted practice')
        select_short_preset(driver)
        assert saved(profile)['workout_character'] == '0'
        assert saved(profile)['workout_custom_v1_1'].splitlines()[1] == 'Edited circuit'

    with running('patterns-before', 'cobalt_dark') as app:
        driver.press(label='Start Practice', role='button')
        driver.wait(label='Hold', role='text')
        first = checkpoint(profile, lambda v: v[2] == 1 and v[3] == 0)
        interrupt(app)
    with running('patterns-continued') as app:
        recovery_prompt(driver, 'Box', 'Hold')
        subprocess.run(['import', '-window', app_window(app, env), str(output / 'recovery-box.png')],
                       env=env, check=True, timeout=5)
        driver.press(label='Continue', role='button', settle=False)
        driver.wait(label='Hold', role='text')
        later = checkpoint(profile, lambda v: v[2] == 1 and v[5] > first['resume']['values'][5])
        assert later['started_at'] == first['started_at']
        interrupt(app)
    with running('patterns-canceled'):
        recovery_prompt(driver, 'Box')
        driver.press(label='Cancel', role='button')
        driver.wait_gone(label='Interrupted practice')

    with running('meditation-before', 'meditation_home') as app:
        driver.press(label='Start Practice', role='button')
        first = checkpoint(profile, lambda v: v[0] - v[1] >= 2)
        interrupt(app)
    with running('meditation-continued') as app:
        recovery_prompt(driver, 'Meditation')
        driver.press(label='Continue', role='button', settle=False)
        later = checkpoint(profile, lambda v: v[1] < first['resume']['values'][1])
        assert later['started_at'] == first['started_at'] and later['resume']['values'][0] == first['resume']['values'][0]
        interrupt(app)
    with running('meditation-canceled'):
        recovery_prompt(driver, 'Meditation')
        driver.press(label='Cancel', role='button')
        driver.wait_gone(label='Interrupted practice')

    unsupported = json.dumps(dict(schema=1, started_at=1794800000, activity=0, topic=0,
                                  rounds=[42], resume=dict(version=1, values=[42, 3], definition='')))
    corrupt = legacy[:-2]
    invalid_position = json.dumps(dict(schema=1, started_at=1794800000, activity=1, topic=0,
                                       rounds=[42], resume=dict(version=1, values=[25, 99, 0], definition='')))
    for name, payload in [('legacy', legacy), ('unsupported', unsupported),
                          ('corrupt', corrupt), ('invalid-position', invalid_position)]:
        with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
            assert database.execute('SELECT COUNT(*) FROM practice_draft').fetchone()[0] == 0
            database.execute('INSERT INTO practice_draft(id,json,saved_at) VALUES(1,?,1)', (payload,))
        with running(name, 'meditation_home') as app:
            driver.wait(label='Start Practice', role='button')
            for label in ('Interrupted practice', 'Playback position unavailable', 'Continue'):
                assert not driver.find(label=label, visible=True), name
            with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
                assert database.execute('SELECT json FROM practice_draft').fetchone() == (payload,)
            driver.press(label='Start Practice', role='button')
            checkpoint(profile, lambda values: values[0] > 0)
            interrupt(app)
        with sqlite3.connect(profile / 'inbe.db', timeout=5) as database:
            assert database.execute('SELECT 1 FROM meta WHERE key LIKE ? AND value=?',
                                    ('practice_draft_archive/%', payload)).fetchone()
            database.execute('DELETE FROM practice_draft')
    assert history() == count_before, 'Recovery changed practice history'
    print('Practice recovery UI: exact Workout, Box and Meditation checkpoints, Continue and Cancel, and silent preservation of invalid drafts')


def main(binary, bundle, recovery=False):
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
            'DBUS_SESSION_BUS_ADDRESS': 'unix:path=' + local_files['XDG_RUNTIME_DIR'] + '/no-session-bus',
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
        if recovery:
            recovery_test(arguments, env, profile, driver, output)
            return
        arguments += ['--screenshot', str(profile / 'unused.png'), '--screenshot-scene', 'workout_home',
                      '--screenshot-width', '910', '--screenshot-height', '1000',
                      '--screenshot-ui-scale', '10', '--screenshot-theme', '0']
        for step in (1, 2):
            log_path = output / f'app-{step}.log'
            with log_path.open('w') as log:
                driver.reset()
                scene_ready = profile / 'scene-ready'
                audio_path = profile / 'audio.raw'
                app_env = env
                if step == 1:
                    app_env = env | {'INBE_TEST_WORKOUT_READY_FILE': str(scene_ready),
                                     'SDL_AUDIODRIVER': 'disk', 'SDL_DISKAUDIOFILE': str(audio_path)}
                app = subprocess.Popen(arguments, cwd=ROOT, env=app_env, stdout=log, stderr=subprocess.STDOUT)
                driver.attach(app, log_path)
                try:
                    select_short_preset(driver)
                    window = app_window(app, env)
                    if step == 1:
                        delayed_preset_start(driver, scene_ready, audio_path, window, env)
                        woman = preset_poses(driver, profile, window, output, 'Woman', env)
                        create_routine(driver, profile)
                        woman.append(capture_custom_character(driver, window, output, 'Woman', env))
                        exit_routine(driver)
                        enter_customize(driver)
                        assert_character(driver, 'Woman')
                        previews = [capture_pose(driver, window, driver.wait(label=label, role='image'), output,
                                                 f'preview-{label.lower()}', env)
                                    for label in ('Woman', 'Man')]
                        assert_different_models(*previews)
                        choose_character(driver, 'Man')
                        assert saved(profile)['workout_character'] == '1'
                        driver.press(label='Back', role='button')
                    else:
                        enter_customize(driver)
                        assert_character(driver, 'Man')
                        driver.press(label='Back', role='button')
                        open_routine_library(driver)
                        subprocess.run(['xdotool', 'windowfocus', window, 'key', 'Escape'],
                                       env=env, check=True, timeout=5)
                        driver.wait_gone(label='New routine', role='button')
                        select_short_preset(driver)
                        man = preset_poses(driver, profile, window, output, 'Man', env)
                        man.append(play_routine(driver, profile, output, window, env))
                        for female_pose, male_pose in zip(woman, man):
                            assert_different_models(female_pose, male_pose)
                    assert app.poll() is None
                finally:
                    stop(app)
    print('Workout UI: delayed scene and narration, countdown restart, custom saves, seeks, and both character previews')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), '--recovery' in sys.argv[3:])
