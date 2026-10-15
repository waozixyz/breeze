"""Exercise Tai Chi's two choosers using only a private display and profile."""
import contextlib
import csv
import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import wave

from PIL import Image

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


with tempfile.TemporaryDirectory(prefix='profile-', dir=OUTPUT) as profile, contextlib.ExitStack() as stack:
    cache = Path(profile) / 'packages'
    cache.mkdir()
    for name in ('taichi', 'taichi.en'):
        shutil.copyfile(ROOT / 'build/practice-content' / (name + '.zib'),
                        cache / ('practice-' + name + '.zib'))
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_KEYS}
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

    def capture(window, name):
        path = OUTPUT / (name + '.png')
        command('import', '-window', window, str(path))
        with Image.open(path) as picture:
            larger = path.with_name(path.stem + '-ocr.png')
            picture.resize((picture.width * 2, picture.height * 2)).save(larger)
        return command('tesseract', str(larger), 'stdout', '--psm', '11') + '\n' + command('tesseract', str(larger), 'stdout', '--psm', '3')

    def click(window, x, y):
        command('xdotool', 'mousemove', '--window', window, str(x), str(y))
        time.sleep(.15)
        command('xdotool', 'mousedown', '1')
        time.sleep(.12)
        command('xdotool', 'mouseup', '1')
        time.sleep(.5)

    def click_text(window, name, label):
        capture(window, name)
        data = command('tesseract', str(OUTPUT / (name + '-ocr.png')),
                       'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
        lines = {}
        for row in csv.DictReader(io.StringIO(data), delimiter='\t'):
            if row['text'].strip():
                key = tuple(row[field] for field in ('block_num', 'par_num', 'line_num'))
                lines.setdefault(key, []).append(row)
        for words in lines.values():
            if ' '.join(word['text'] for word in words) == label:
                left = min(int(word['left']) for word in words)
                right = max(int(word['left']) + int(word['width']) for word in words)
                top = min(int(word['top']) for word in words)
                bottom = max(int(word['top']) + int(word['height']) for word in words)
                click(window, (left + right) // 4, (top + bottom) // 4)
                return
        raise AssertionError(f'{label!r} missing from menu: {lines}')

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
                command('xdotool', 'windowfocus', window)
                time.sleep(1)
                yield window
                assert app.poll() is None, log_path.read_text()
                assert 'frame rejected' not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    with application('tai_chi_customize') as window:
        text = capture(window, 'characters')
        assert 'monk' in text.lower() and 'woman' in text.lower(), text
        assert 'Background music' in text and 'Music volume' in text and 'Cue volume' in text, text
        assert 'Voice narration' in text and 'written' in text, text
        click(window, 760, 294)
        click(window, 865, 368)
        click(window, 755, 446)
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            audio = dict(db.execute("SELECT key,value FROM settings"))
        assert audio['voice_narration_enabled'] == '0', audio
        saved_music = int(audio['music_volume'])
        saved_cue = int(audio['sound_volume'])
        assert 15 <= saved_music <= 35 and 40 <= saved_cue <= 60, audio
        # Both character cards are real, large targets; selecting the second
        # writes the existing setting rather than creating another profile.
        click(window, 520, 300)
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            value = db.execute("SELECT value FROM settings WHERE key='tai_chi_character'").fetchone()
        assert value and value[0] == '1', value
        click(window, 1086, 104)
        time.sleep(.5)
        text = capture(window, 'customize-closed')
        assert 'Tai Chi' in text and 'Start' in text, text
        # Read the full-app sidebar separately from the detailed banner.
        sidebar = OUTPUT / 'navbar.png'
        with Image.open(OUTPUT / 'customize-closed.png') as picture:
            picture.crop((0, 0, 88, 900)).resize((352, 3600)).save(sidebar)
        navigation = command('tesseract', str(sidebar), 'stdout', '--psm', '11')
        assert 'Habits' in navigation and 'Diary' in navigation, navigation
        assert 'monk' not in text.lower(), text
        click(window, 500, 855)
        text = capture(window, 'start-opens-course')
        assert 'Course' in text and 'Lesson 1' in text, text
        click(window, 100, 30)
        text = capture(window, 'outside-dismisses-course')
        assert 'Start' in text and 'Course' not in text, text
        click(window, 850, 855)
        text = capture(window, 'customize-reopens')
        assert 'monk' in text.lower() and 'woman' in text.lower(), text

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

    with application('tai_chi_customize') as window:
        capture(window, 'audio-reloaded')
        # An initially selected On would make this click a no-op. The saved
        # Off must be loaded, and the other saved volumes must survive it.
        click(window, 975, 446)
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            audio = dict(db.execute("SELECT key,value FROM settings"))
        assert audio['voice_narration_enabled'] == '1', audio
        assert int(audio['music_volume']) == saved_music, audio
        assert int(audio['sound_volume']) == saved_cue, audio
        click(window, 865, 188)
        click_text(window, 'music-menu', 'Test music')
        text = capture(window, 'music-selected')
        assert 'Test music' in text, text
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            audio = dict(db.execute("SELECT key,value FROM settings"))
        assert audio['practice_music_track_tai_chi'] == '3', audio
        assert int(audio['practice_music_mask']) & (1 << 4), audio
        click(window, 690, 262)
        text = capture(window, 'music-preview')
        assert 'Stop' in text, text
        click(window, 1086, 104)
        click(window, 850, 855)
        text = capture(window, 'music-preview-closed')
        assert 'Test music' in text and 'Stop' not in text, text
        # None is the music off option, independent of narration and cues.
        click(window, 865, 188)
        click_text(window, 'music-off-menu', 'None')
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            audio = dict(db.execute("SELECT key,value FROM settings"))
        assert audio['practice_music_track_tai_chi'] == '-1', audio
        assert not int(audio['practice_music_mask']) & (1 << 4), audio

    with application('tai_chi_customize', 390, 844) as window:
        text = capture(window, 'narrow-audio')
        assert 'Background music' in text and 'Voice narration' in text, text
        command('xdotool', 'mousemove', '--window', window, '300', '650')
        command('xdotool', 'click', '--repeat', '6', '--delay', '100', '5')
        time.sleep(.5)
        text = capture(window, 'narrow-characters')
        assert 'monk' in text.lower() and 'woman' in text.lower(), text

    with application('tai_chi_choose') as window:
        text = capture(window, 'course')
        assert 'Course' in text and 'Lesson 1' in text, text
        # Navigate to a different lesson and start its first preview card.
        click(window, 210, 604)
        text = capture(window, 'lesson')
        assert 'Lesson 4' in text, text
        click(window, 540, 420)
        text = capture(window, 'playing')
        assert 'Pause' in text or 'Single Whip' in text, text
        with sqlite3.connect(Path(profile) / 'inbe.db') as db:
            value = db.execute("SELECT value FROM settings WHERE key='tai_chi_item'").fetchone()
        assert value and int(value[0]) > 17, value

print('Tai Chi chooser interaction test passed')
