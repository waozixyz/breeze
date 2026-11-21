"""Exercise the real astral selector and sessions on an isolated display/profile."""
import ast
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver
from window_icon_property import verify_window_icon
from practice_audio_ui import prepare_music_fixture, exercise_audio_modal

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/astral-projection-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'GDK_DISPLAY', 'SESSION_MANAGER')
assert all(not os.environ.get(key) for key in DESKTOP_KEYS), 'Inherited desktop environment'
BINARY = Path(sys.argv[1]).resolve()
BUNDLE = ROOT / 'build/inbe-full.zx'
if '--bundle' in sys.argv[2:]:
    BUNDLE = Path(sys.argv[sys.argv.index('--bundle') + 1]).resolve()
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_media import media_path
spec = importlib.util.spec_from_file_location('speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
folder = media_path('assets/practices/astral_projection')
if '--media' in sys.argv[2:]:
    folder = Path(sys.argv[sys.argv.index('--media') + 1]).resolve()
rows = json.loads((folder / 'catalogue.json').read_text())['practices']
text = speech.entries(folder / 'text/en.txt')


def tail(path, count=4000):
    with path.open('rb') as stream:
        stream.seek(0, 2)
        stream.seek(max(0, stream.tell() - count))
        return stream.read(count).decode(errors='replace')


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
    display = subprocess.Popen(['Xvfb', '-noreset', ':957', '-displayfd', '1', '-screen', '0',
                                '1280x900x24', '-nolisten', 'tcp'], env=env,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and int(number) >= 300 and display.poll() is None
    env['DISPLAY'] = ':' + number
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='profile-', dir=OUTPUT)))
    prepare_music_fixture(profile)
    cache = profile / 'packages'
    cache.mkdir()
    # The base pack must come from the app, including on a fresh profile.
    voice = ROOT / 'build/practice-content/astral_projection.en.zx'
    if voice.exists():
        shutil.copyfile(voice, cache / ('practice-' + voice.name))
    alsa = profile / 'alsa.conf'
    alsa.write_text('pcm.!default {\n    type null\n}\n')
    env.update(ALSA_CONFIG_PATH=str(alsa), INBE_SCREENSHOT_DATA_ROOT=str(profile), APP_DATA_ROOT=str(profile))
    driver = UiDriver(profile / 'driver')
    env.update(driver.environment())

    @contextlib.contextmanager
    def application(scene='astral_projection_home', width=1280, height=900, theme=0, dark=0):
        log_path = OUTPUT / (scene + '-' + str(width) + '-theme-' + str(theme) + '.log')
        with log_path.open('w') as log:
            driver.reset()
            bundle_args = [] if '--embedded' in sys.argv[2:] else ['--bundle', str(BUNDLE)]
            app = subprocess.Popen([str(BINARY), *bundle_args, '--screenshot',
                                    str(OUTPUT / 'unused.png'), '--screenshot-scene', scene,
                                    '--screenshot-width', str(width), '--screenshot-height', str(height),
                                    '--screenshot-ui-scale', '10', '--screenshot-theme', str(theme),
                                    '--screenshot-dark', str(dark)],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 30
                window = ''
                while time.monotonic() < deadline:
                    assert app.poll() is None, tail(log_path)
                    found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and (profile / 'inbe.db').exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.05)
                assert window, tail(log_path)
                driver.tree()  # The first committed frame follows window/icon setup.
                verify_window_icon(env['DISPLAY'], window, ROOT / 'assets/app/icon.webp')
                yield window
                assert app.poll() is None, tail(log_path)
                assert 'frame rejected' not in tail(log_path)
            finally:
                stop(app)

    def state(window):
        output = subprocess.check_output(['xprop', '-id', window, '_HARMONY_APP_STATE'],
                                         env=env, text=True, timeout=5)
        return json.loads(ast.literal_eval(output.split(' = ', 1)[1]))

    def setting(key):
        with sqlite3.connect(profile / 'inbe.db', timeout=3) as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row[0] if row else None

    def reveal(title, description):
        for _ in range(30):
            tree = driver.tree()
            by_index = {node['index']: node for node in tree}
            heading = next(node for node in tree if node['label'] == title and node['kind'] == 'button')
            paragraph = next(node for node in tree if node['label'] == description and node['kind'] == 'text')
            viewport = by_index[heading['parent']]
            while viewport['kind'] != 'scroll':
                viewport = by_index[viewport['parent']]
            top = viewport['visible_y']
            bottom = top + viewport['visible_height']
            if (heading['visible_height'] >= heading['height'] - 1 and
                    paragraph['visible_height'] >= paragraph['height'] - 1 and
                    paragraph['y'] + paragraph['height'] + 44 <= bottom):
                driver.release_pointer()
                return
            direction = 2 if heading['y'] < top else -2
            driver.pointer(*driver.center(viewport), wheel=direction)
            driver.wait_idle(frames=3, timeout=2)
        raise AssertionError('Could not scroll to ' + title)

    # Initialize only this private database, then choose English and suppress
    # unrelated first-run guides. Existing real profiles are never opened.
    with application():
        driver.tree()
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        for key, value in {'language': 'en', 'language_system': '0', 'language_setup_done': '1',
                           'apps_setup_done': '1', 'tutorial_seen': '1', 'habits_guide_seen': '1',
                           'lumi_guides_seen': '127', 'launcher_guide_seen': '1',
                           'package_updates_allowed': '0', 'voice_narration_enabled': '1',
                           'guide_narration_enabled': '0', 'notification_achievements': '0'}.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))

    # A remembered retired language migrates to an explicit English preference,
    # including narration overrides, while retaining other saved owner choices.
    prior_system_language = env.get('LANGUAGE')
    env['LANGUAGE'] = 'de_DE.UTF-8'
    for retired in ('id', 'it', 'pt'):
        expected_language = 'pt' if retired == 'pt' else 'en'
        retained_exercise = rows[-1]['id']
        with sqlite3.connect(profile / 'inbe.db') as db:
            changes = {'language': retired, 'locale_retirement_fixture': 'preserved',
                       'astral_projection_exercise': retained_exercise,
                       'sun_salutation_narration_language': retired,
                       'astral_projection_narration_language': retired,
                       'tai_chi_narration_language': retired}
            for key, value in changes.items():
                db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                           'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))
        for _ in range(2):
            with application(width=390, height=844):
                driver.tree()
                assert setting('language') == expected_language, retired
                for key in ('sun_salutation_narration_language', 'astral_projection_narration_language',
                            'tai_chi_narration_language'):
                    assert setting(key) == expected_language, (retired, key)
                assert setting('astral_projection_exercise') == retained_exercise
                assert setting('locale_retirement_fixture') == 'preserved'
        print(f'{retired}: {expected_language} UI and narration preferences persisted across re-entry')
    with sqlite3.connect(profile / 'inbe.db') as db:
        db.execute("UPDATE settings SET value='en' WHERE key='language' OR key IN "
                   "('sun_salutation_narration_language','astral_projection_narration_language',"
                   "'tai_chi_narration_language')")
    if prior_system_language is None:
        env.pop('LANGUAGE', None)
    else:
        env['LANGUAGE'] = prior_system_language

    def choose_saved(identifier):
        with sqlite3.connect(profile / 'inbe.db') as db:
            db.execute("UPDATE settings SET value=? WHERE key='astral_projection_exercise'", (identifier,))

    def recorded(identifier, seconds):
        with sqlite3.connect(profile / 'inbe.db') as db:
            rows = db.execute("SELECT details FROM sessions WHERE activity=5 AND deleted_at=0").fetchall()
        return [json.loads(row[0]) for row in rows
                if json.loads(row[0]).get('item') == identifier and
                json.loads(row[0]).get('duration_seconds') == seconds]

    # Home buttons sit above a scroll gesture that must not move them.
    # selects its own practice, and remembers Astral when returning to its tab.
    def press_home(label):
        driver.pointer(100, 200, wheel=-100)
        driver.wait_idle(frames=20)
        driver.press(label=label, role='button')

    def timeline(duration):
        labels = [node['label'] for node in driver.tree() if node['visible']]
        clocks = [match.groups() for label in labels
                  if (match := re.fullmatch(r'(\d+):(\d{2}) / (\d+):(\d{2})', label))]
        assert len(clocks) == 1, labels
        minutes, seconds, total_minutes, total_seconds = map(int, clocks[0])
        assert total_minutes * 60 + total_seconds == duration, clocks
        return minutes * 60 + seconds

    def check_seeking(window, row, session):
        duration = row['duration']
        slider = driver.wait(label='Playback position', role='slider')
        assert slider['visible_width'] >= 180, slider
        assert slider['visible_height'] == slider['height'], slider
        left, top = slider['visible_x'], slider['visible_y']
        length = slider['visible_width']
        center_y = top + slider['visible_height'] / 2
        middle = (left + length / 2, center_y)
        early = (left + length / 4, center_y)
        driver.drag(middle, middle, steps=1)
        assert abs(timeline(duration) - duration // 2) < 10
        assert not state(window)['paused']
        driver.press(label='Pause', role='button')
        driver.wait(label='Resume', role='button')
        driver.drag(middle, early)
        paused_at = timeline(duration)
        assert duration // 5 < paused_at < duration * 3 // 10, paused_at
        current_cue = next(cue for cue in reversed(session['cues']) if cue['second'] <= paused_at)
        driver.wait(label=text[current_cue['key']], role='text')
        assert driver.wait(label='Playback position', role='slider')['focused']
        # Exercise SDL's keyboard input while the real private window owns focus.
        subprocess.run(['xdotool', 'windowfocus', window, 'key', 'Right'], env=env,
                       check=True, timeout=5)
        goal = paused_at + 5
        driver.wait(label=f'{goal // 60}:{goal % 60:02} / {duration // 60}:{duration % 60:02}', role='text')
        time.sleep(1.05)
        assert timeline(duration) == paused_at + 5 and state(window)['paused']
        driver.drag(early, (left + length - 1, center_y))
        assert timeline(duration) == duration
        assert state(window)['practice_running'] and state(window)['paused']
        assert not recorded(row['id'], duration), 'Seeking to the end recorded a completed session'
        driver.press(label='Resume', role='button')
        driver.wait(label='Pause', role='button')
        driver.wait_idle(frames=3)
        assert state(window)['practice_running']
        assert not recorded(row['id'], duration)
        driver.drag((left + length - 1, center_y), (left + 1, center_y))
        assert timeline(duration) < 10
        driver.wait(label=text[session['cues'][0]['key']], role='text')
        print(f'{slider["visible_width"]}px timeline: click, drag, keyboard, pause and history passed')

    for width, height in ((1280, 900), (390, 844)):
        for row in rows:
            title = text[row['title_key']]
            session = json.loads((folder / 'sessions' / (row['id'] + '.json')).read_text())
            with application(width=width, height=height) as window:
                press_home('Choose Lesson')
                assert not state(window)['practice_running'], 'Session started before selection'
                modal = driver.wait(label='Astral Projection', role='modal')
                assert modal['width'] <= width and modal['height'] <= height, modal
                choices = {node['label'] for node in driver.tree() if node['kind'] == 'button'}
                assert {text[item['title_key']] for item in rows} <= choices, choices
                if row == rows[0]:
                    driver.press(label='Close', role='button')
                    driver.wait_gone(role='modal')
                    assert not state(window)['practice_running']
                    press_home('Choose Lesson')
                    driver.wait(label='Astral Projection', role='modal')
                reveal(title, text[row['description_key']])
                driver.press(label=title, role='button')
                assert setting('astral_projection_exercise') == row['id']
                driver.wait(label=title, role='image')
                assert not state(window)['practice_running']
                press_home('How to')
                driver.wait(label=text[row['guide_key']], role='text')
                driver.press(label='Back', role='button')
                reveal(title, text[row['description_key']])
                subprocess.run(['import', '-window', window, str(OUTPUT / (row['id'] + '-' + str(width) + '.png'))],
                               env=env, check=True, capture_output=True, timeout=10)
                press_home('Start Practice')
                driver.wait(label='Pause', role='button')
                assert state(window)['practice_running']
                driver.wait(label=text[session['cues'][0]['key']], role='text')
                assert timeline(row['duration']) < 10
                if row == rows[0]:
                    exercise_audio_modal(driver, lambda: state(window), setting,
                                         'practice_music_track_5')
                    check_seeking(window, row, session)
                driver.press(label='Pause', role='button')
                driver.wait(label='Resume', role='button')
                assert state(window)['paused']
                driver.press(label='Close', role='button')
                driver.press(label='Cancel', role='button')
                driver.wait(label='Resume', role='button')
                assert state(window)['paused'], 'Exit cancellation lost explicit pause'
                driver.press(label='Resume', role='button')
                driver.wait(label='Pause', role='button')
                assert not state(window)['paused']
                driver.press(label='Close', role='button')
                driver.press(label='Exit', role='button')
                driver.wait(label='Choose Lesson', role='button')
                assert not state(window)['practice_running']
                driver.press(label='Choose Lesson', role='button')
                assert setting('astral_projection_exercise') == row['id']
                driver.wait(label=title, role='image')
                assert not state(window)['practice_running']
                driver.press(label='Start Practice', role='button')
                driver.wait(label=text[session['cues'][0]['key']], role='text')
                driver.press(label='Close', role='button')
                driver.press(label='Exit', role='button')
                driver.press(label='Choose Lesson', role='button')
                following = rows[(rows.index(row) + 1) % len(rows)]
                following_session = json.loads((folder / 'sessions' / (following['id'] + '.json')).read_text())
                following_title = text[following['title_key']]
                reveal(following_title, text[following['description_key']])
                driver.press(label=following_title, role='button')
                driver.press(label='Start Practice', role='button')
                driver.wait(label=text[following_session['cues'][0]['key']], role='text')
                assert setting('astral_projection_exercise') == following['id']
                assert timeline(following['duration']) < 10
                # End the switched session before this shared test profile restarts.
                driver.press(label='Close', role='button')
                driver.press(label='Exit', role='button')
                driver.wait(label='Choose Lesson', role='button')
                assert not state(window)['practice_running']
                print(f'{width}x{height}: {row["id"]} guided, paused, restarted and switched to {following["id"]}')

    # Drive the final second through the real native lifecycle and recording
    # code. The fixture uses the selected real course and advances its clock;
    # it does not substitute a shorter course or completion implementation.
    for row in rows:
        choose_saved(row['id'])
        with application('astral_projection_ending', 390, 844) as window:
            driver.wait(label='Resume', role='button')
            assert not recorded(row['id'], row['duration'])
            driver.press(label='Resume', role='button')
            driver.wait(label='Done', role='button')
            assert not state(window)['practice_running'] and state(window)['screen'] == 5
            matches = recorded(row['id'], row['duration'])
            assert len(matches) == 1 and matches[0]['title'] == text[row['title_key']], matches
            driver.press(label='Done', role='button')
            driver.press(label='Choose Lesson', role='button')
            driver.wait(label=text[row['title_key']], role='image')
            assert not state(window)['practice_running']
        with application('astral_projection_home', 390, 844) as window:
            assert len(recorded(row['id'], row['duration'])) == 1
            press_home('How to')
            driver.wait(label=text[row['guide_key']], role='text')
            driver.press(label='Back', role='button')
            driver.wait(label=text[row['title_key']], role='button')
        print(f'{row["id"]}: finite completion and named history persisted')

    choose_saved(rows[0]['id'])
    with application('astral_projection_session', 390, 844) as window:
        driver.wait(label='Resume', role='button')
        driver.press(label='Close', role='button')
        driver.press(label='Save', role='button')
        driver.wait(label='Choose Lesson', role='button')
        assert len(recorded(rows[0]['id'], 60)) == 1

    with application('astral_projection_missing', 390, 844) as window:
        driver.wait(label='This practice could not be loaded. Download the practice again and try once more.', role='text')
        assert not state(window)['practice_running'], 'Missing selected session fell back to the legacy practice'
        reveal(text[rows[1]['title_key']], text[rows[1]['description_key']])
        driver.press(label=text[rows[1]['title_key']], role='button')
        assert setting('astral_projection_exercise') == rows[1]['id']
        assert not state(window)['practice_running']

    with application('astral_projection_legacy_home', 390, 844) as window:
        press_home('Choose Lesson')
        driver.wait(label='This practice could not be loaded. Download the practice again and try once more.', role='text')
        assert not state(window)['practice_running'], 'The lesson entry launched an unrelated legacy session'
        assert not driver.find(label='Start Practice', role='button')
        driver.press(label='Close', role='button')
        driver.wait(label='Choose Lesson', role='button')
        assert setting('astral_projection_exercise') == rows[1]['id']
        driver.press(label='How to', role='button')
        assert not state(window)['practice_running']
        driver.press(label='Start Practice', role='button')
        driver.wait(label='Pause', role='button')
        legacy = json.loads((folder / 'session.json').read_text())
        driver.wait(label=text[legacy['cues'][0]['key']], role='text')
        driver.press(label='Close', role='button')
        driver.press(label='Exit', role='button')
        driver.wait(label='Choose Lesson', role='button')
        assert setting('astral_projection_exercise') == rows[1]['id']

    with application('astral_projection_legacy', 390, 844) as window:
        driver.wait(label='Resume', role='button')
        legacy = json.loads((folder / 'session.json').read_text())
        cue = next(cue for cue in reversed(legacy['cues']) if cue['second'] <= 60)
        driver.wait(label=text[cue['key']], role='text')
        driver.wait(label='1:00', role='text')
        assert state(window)['practice_running'], 'Older package no longer starts its original session'
        driver.press(label='Close', role='button')
        driver.press(label='Save', role='button')
        driver.wait(label='Choose Lesson', role='button')
        assert len(recorded('', 60)) == 1, 'Original package no longer saves an elapsed session'

    # A translated portrait uses the actual packaged metadata and cue text.
    # German has long descriptions, so exercise each selection and its guide.
    localized = speech.entries(folder / 'text/de.txt')
    labels = speech.entries(ROOT / 'locales/de.txt')
    with sqlite3.connect(profile / 'inbe.db') as db:
        db.execute("UPDATE settings SET value='de' WHERE key='language'")
    for row in rows:
        choose_saved(row['id'])
        with application(width=390, height=844) as window:
            driver.press(label=labels['astral_choose_lesson'], role='button')
            assert not state(window)['practice_running']
            title = localized[row['title_key']]
            reveal(title, localized[row['description_key']])
            driver.wait(label=localized[row['description_key']], role='text')
            driver.press(label=title, role='button')
            driver.press(label=labels['practice_manual_button'], role='button')
            driver.wait(label=localized[row['guide_key']], role='text')
            driver.press(label=labels['back_button'], role='button')
            reveal(title, localized[row['description_key']])
            subprocess.run(['import', '-window', window, str(OUTPUT / (row['id'] + '-de-390.png'))],
                           env=env, check=True, capture_output=True, timeout=10)
            driver.press(label=labels['practice_start_button'], role='button')
            session = json.loads((folder / 'sessions' / (row['id'] + '.json')).read_text())
            driver.wait(label=localized[session['cues'][0]['key']], role='text')
            driver.press(label=labels['pause_button'], role='button')
            driver.wait(label=labels['patterns_resume_button'], role='button')
            assert state(window)['paused']
            driver.press(label=labels['close_button'], role='button')
            driver.press(label=labels['exit_button'], role='button')
            driver.wait(label=labels['astral_choose_lesson'], role='button')
            assert not state(window)['practice_running']
        print(f"390x844 de: {row['id']} translated selection, guide and initial cue passed")

print('All six astral exercises passed desktop and portrait native UI selection/session coverage')
