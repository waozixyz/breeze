"""Exercise Tai Chi's two choosers using only a private display and profile."""
import contextlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import wave

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/tai-chi-ui-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
DESKTOP_KEYS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')
assert all(not os.environ.get(key) for key in DESKTOP_KEYS), 'Inherited desktop environment'
BINARY = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'build/bin/linux/inbe-linux-x86_64')
BUNDLE = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'build/inbe-full.zib')


def stop(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=5)


def contains(outer, inner):
    """Whether a widget's bounds hold a point."""
    x, y = inner
    return (outer['x'] <= x <= outer['x'] + outer['width'] and
            outer['y'] <= y <= outer['y'] + outer['height'])


with tempfile.TemporaryDirectory(prefix='profile-', dir=OUTPUT) as profile, contextlib.ExitStack() as stack:
    cache = Path(profile) / 'packages'
    cache.mkdir()
    for name in ('taichi', 'taichi.en'):
        shutil.copyfile(ROOT / 'build/practice-content' / (name + '.zib'),
                        cache / ('practice-' + name + '.zib'))
    driver = UiDriver(OUTPUT / 'driver')
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_KEYS}
    env.update(driver.environment())
    env.update(INBE_SCREENSHOT_DATA_ROOT=profile, YUE_DESKTOP_RECOVERY='0',
               APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy', SDL_VIDEODRIVER='x11',
               LIBGL_ALWAYS_SOFTWARE='1', APP_SHOT_WINDOW='1')
    display_log = stack.enter_context((OUTPUT / 'display.log').open('w'))
    display = subprocess.Popen(['Xvfb', ':951', '-displayfd', '1', '-screen', '0', '1280x900x24',
                                '-nolisten', 'tcp'], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and int(number) >= 300
    env['DISPLAY'] = ':' + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True, text=True, timeout=10).stdout.strip()

    def settings():
        with sqlite3.connect(Path(profile) / 'inbe.db', timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    def saved(check):
        """The saved settings once check accepts them, or after five seconds."""
        deadline = time.monotonic() + 5
        while True:
            values = settings()
            if check(values) or time.monotonic() >= deadline:
                return values
            time.sleep(.05)

    def press_at(node, across, down):
        """Press a widget at a fraction of its width and height."""
        x = node['x'] + node['width'] * across
        y = node['y'] + node['height'] * down
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)
        driver.release_pointer()

    def press_card(title):
        """Press the preview card around a title's picture.

        Preview cards are buttons without a label; their title belongs to
        the picture and text drawn inside them."""
        driver.wait(label=title, role='image')
        nodes = driver.tree()
        picture = next(node for node in nodes if node['label'] == title and node['kind'] == 'image'
                       and node['visible'])
        centre = UiDriver.center(picture)
        cards = [node for node in nodes if node['kind'] == 'button' and node['visible']
                 and node['interactive'] and contains(node, centre)]
        assert cards, f'No card holds {title}'
        card = min(cards, key=lambda node: node['width'] * node['height'])
        assert len([node for node in nodes if node['key'] == card['key']]) == 1, card
        driver.press(key=card['key'])

    def dropdown_below(label):
        """The dropdown right below a section's label."""
        heading = driver.wait(label=label)
        dropdowns = [node for node in driver.find(role='dropdown', visible=True)
                     if node['y'] >= heading['y']]
        assert dropdowns, f'No dropdown below {label}'
        return min(dropdowns, key=lambda node: node['y'])

    @contextlib.contextmanager
    def application(scene, width=1280, height=900):
        log_path = OUTPUT / (scene + '.log')
        with log_path.open('w') as log:
            app = subprocess.Popen([str(BINARY), '--bundle', str(BUNDLE),
                                    '--screenshot', str(OUTPUT / 'unused.png'),
                                    '--screenshot-scene', scene, '--screenshot-width', str(width),
                                    '--screenshot-height', str(height), '--screenshot-ui-scale', '10',
                                    '--screenshot-theme', '0'], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 20
                window = ''
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and (Path(profile) / 'inbe.db').exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                assert window, log_path.read_text()
                command('xdotool', 'windowmove', window, '0', '0')
                driver.wait_idle(frames=3)
                yield window
                assert app.poll() is None, log_path.read_text()
                assert 'frame rejected' not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    with application('tai_chi_customize'):
        for label in ('Jade woman', 'Indigo man'):
            driver.wait(label=label, role='text')
        for label in ('Background music', 'Voice narration'):
            driver.wait(label=label)
        for label in ('Music volume', 'Cue volume'):
            driver.wait(label=label, role='slider')
        # The narration voice lives here, under the switch, with the list of
        # languages it speaks.
        switch = driver.wait(role='toggle')
        voices = [driver.wait(label=label, role='button') for label in ('Female voice', 'Male voice')]
        languages = driver.wait(label='English', role='dropdown')
        hint = driver.wait(contains='Tai Chi instructions')
        for node in (*voices, languages, hint):
            assert node['y'] > switch['y'] and abs(node['x'] - switch['x']) < switch['width'], \
                (node['label'], 'is not under the narration switch')
        assert not driver.find(contains='Plays in', visible=True), driver.text()
        press_at(driver.wait(label='Music volume', role='slider'), .26, .7)
        press_at(driver.wait(label='Cue volume', role='slider'), .5, .7)
        driver.press(role='toggle')
        audio = saved(lambda values: values['voice_narration_enabled'] == '0')
        assert audio['voice_narration_enabled'] == '0', audio
        saved_music = int(audio['music_volume'])
        saved_cue = int(audio['sound_volume'])
        assert 15 <= saved_music <= 35 and 40 <= saved_cue <= 60, audio
        # Both character cards are real, large targets; selecting the second
        # writes the existing setting rather than creating another profile.
        press_card('Indigo man')
        value = saved(lambda values: values.get('tai_chi_character') == '1').get('tai_chi_character')
        assert value == '1', value
        driver.press(label='Close')
        driver.wait_gone(label='Background music')
        driver.wait(label='Tai Chi')
        driver.wait(label='Start Practice', role='button')
        # The full app's sidebar shows beside the practice. Diary is no
        # longer pinned on a new install; Apps opens it with the rest.
        nodes = driver.tree()
        bars = {node['index'] for node in nodes if node['kind'] == 'navigation_bar'}
        navigation = [node['label'] for node in nodes if node['visible'] and node['parent'] in bars]
        assert 'Habits' in navigation and 'Apps' in navigation, navigation
        assert not driver.find(contains='Indigo man', visible=True), driver.text()
        driver.press(label='Start Practice', role='button')
        # The Course dialog: its progress line and lessons. Kryon's dialog
        # title ("Course") is not in the widget tree.
        driver.wait(contains='practised')
        driver.wait(label='Lesson 1', role='button')
        assert not driver.find(label='Background music', visible=True), driver.text()
        # A press outside the dialog, where the old test clicked, dismisses it.
        nodes = driver.tree()
        backdrop = next(node for node in nodes if node['kind'] == 'modal')
        outside = (backdrop['x'] + 100, backdrop['y'] + 30)
        dialog = next(node for node in nodes if node['parent'] == backdrop['index']
                      and node['kind'] != 'button')
        assert not contains(dialog, outside), dialog
        driver.pointer(*outside)
        driver.pointer(*outside, down=True)
        driver.pointer(*outside, down=False)
        driver.release_pointer()
        driver.wait_gone(contains='practised')
        driver.wait(label='Start Practice', role='button')
        driver.press(label='Customize', role='button')
        for label in ('Jade woman', 'Indigo man'):
            driver.wait(label=label, role='text')

    # Use an existing custom-track slot with a disposable WAV. Previewing it
    # exercises the real music player without a download or desktop audio.
    track = Path(profile) / 'test-music.wav'
    with wave.open(str(track), 'wb') as music:
        music.setnchannels(1)
        music.setsampwidth(2)
        music.setframerate(22050)
        music.writeframes(b'\0\0' * (22050 * 30))
    with sqlite3.connect(Path(profile) / 'inbe.db') as db:
        user = db.execute("SELECT user_id FROM settings LIMIT 1").fetchone()[0]
        for key, value in {'audio_custom_music_count': '1',
                           'audio_custom_music_0_title': 'Test music',
                           'audio_custom_music_0_path': str(track)}.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, value))

    with application('tai_chi_customize'):
        driver.wait(label='Background music')
        # An initially selected On would make this press a no-op. The saved
        # Off must be loaded, and the other saved volumes must survive it.
        driver.press(role='toggle')
        audio = saved(lambda values: values['voice_narration_enabled'] == '1')
        assert audio['voice_narration_enabled'] == '1', audio
        assert int(audio['music_volume']) == saved_music, audio
        assert int(audio['sound_volume']) == saved_cue, audio
        driver.press(key=dropdown_below('Background music')['key'])
        driver.press(label='Test music', role='option')
        assert dropdown_below('Background music')['label'] == 'Test music', driver.text()
        audio = saved(lambda values: values['practice_music_track_tai_chi'] == '3')
        assert audio['practice_music_track_tai_chi'] == '3', audio
        assert int(audio['practice_music_mask']) & (1 << 4), audio
        # The button beside the chosen track previews it until stopped.
        driver.press(label='Test music', role='button')
        driver.wait(contains='Stop', role='button')
        driver.press(label='Close')
        driver.press(label='Customize', role='button')
        assert dropdown_below('Background music')['label'] == 'Test music', driver.text()
        assert not driver.find(contains='Stop', visible=True), driver.text()
        # None is the music off option, independent of narration and cues.
        driver.press(key=dropdown_below('Background music')['key'])
        driver.press(label='None', role='option')
        audio = saved(lambda values: values['practice_music_track_tai_chi'] == '-1')
        assert audio['practice_music_track_tai_chi'] == '-1', audio
        assert not int(audio['practice_music_mask']) & (1 << 4), audio

    with application('tai_chi_customize', 390, 844):
        driver.wait(label='Background music')
        driver.wait(label='Voice narration')
        parent = driver.find(label='Background music')[0]['parent']
        scroll = next(node for node in driver.tree() if node['index'] == parent)
        x, y = UiDriver.center(scroll)
        for _ in range(6):
            driver.pointer(x, y, wheel=-1)
        driver.release_pointer()
        for label in ('Jade woman', 'Indigo man'):
            driver.wait(label=label, role='text')

    with application('tai_chi_choose'):
        driver.wait(contains='practised')
        driver.wait(label='Lesson 1', role='button')
        # Navigate to a different lesson and start its first preview card.
        driver.press(label='Lesson 4', role='button')
        driver.wait(label='Lesson 4', role='heading')
        heading = driver.find(label='Lesson 4', role='heading')[0]
        cards = [node for node in driver.tree() if node['kind'] == 'image' and node['visible']
                 and node['y'] > heading['y']]
        assert cards, driver.text()
        press_card(min(cards, key=lambda node: (node['y'], node['x']))['label'])
        deadline = time.monotonic() + 20
        while not (driver.find(label='Pause', role='button', visible=True) or
                   driver.find(label='Single Whip', visible=True)):
            assert time.monotonic() < deadline, driver.text()
            time.sleep(.05)
        value = saved(lambda values: int(values.get('tai_chi_item', '-1')) > 17).get('tai_chi_item')
        assert value and int(value) > 17, value

print('Tai Chi chooser interaction test passed')
