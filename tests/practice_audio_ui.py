"""Behavioral assertions shared by real practice UI tests on private displays."""
from pathlib import Path
import shutil
import subprocess
import time


def prepare_music_fixture(profile):
    root = Path(__file__).resolve().parents[1]
    folder = profile / 'runtime-assets/audio/Elijah_K'
    folder.mkdir(parents=True, exist_ok=True)
    first = folder / 'deep-meditation.ogg'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i',
                    str(root / 'test-fixtures/audio/autumn-sunset.mp3'), '-t', '2',
                    '-c:a', 'libvorbis', '-q:a', '1', str(first)], check=True, timeout=30)
    shutil.copyfile(first, folder / 'path-of-meditation.ogg')


def wait_for(condition, description):
    deadline = time.monotonic() + 8
    while not condition():
        assert time.monotonic() < deadline, description
        time.sleep(.05)


def exercise_audio_modal(driver, read_state, read_setting, track_key):
    before = read_state()

    def preserved():
        after = read_state()
        assert after['practice_running']
        for key in ('screen', 'practice', 'round', 'breath_phase', 'paused'):
            assert after[key] == before[key], ('Audio changed session state', key, before, after)

    def reveal(label, role='button'):
        for _ in range(16):
            found = driver.find(label=label, role=role, visible=True)
            if found:
                return found[0]
            sliders = driver.find(role='slider', visible=True)
            modal = driver.find(role='dialog', visible=True)
            anchor = modal[0] if modal else sliders[-1] if sliders else None
            assert anchor, ('Audio modal disappeared', driver.text())
            driver.pointer(anchor['x'] + anchor['width'] / 2,
                           anchor['y'] + anchor['height'] / 2, wheel=-3)
        raise AssertionError('Audio choice is not reachable: ' + label)

    driver.press(label='Background music', role='button')
    driver.wait(label='Cue volume', role='slider')
    for label, key, amount in (('Cue volume', 'sound_volume', 17),
                               ('Music volume', 'music_volume', 23)):
        slider = reveal(label, 'slider')
        # Send pointer input only to the owned private-display test app.
        left = slider['x']
        right = left + slider['width']
        y = slider['y'] + slider['height'] - 24
        for _ in range(12):
            x = (left + right) / 2
            driver.pointer(x, y)
            driver.pointer(x, y, down=True)
            driver.pointer(x, y, down=False)
            actual = int(read_setting(key))
            if actual == amount:
                break
            if actual < amount:
                left = x
            else:
                right = x
        driver.release_pointer()
        wait_for(lambda: read_setting(key) == str(amount), 'Volume was not persisted: ' + key)
        live_key = 'cue_volume' if key == 'sound_volume' else key
        wait_for(lambda: read_state()[live_key] == amount, 'Live volume differs from settings')
        preserved()
    for label, track in (('Deep Meditation', 0), ('Path Of Meditation', 1)):
        choice = reveal(label)
        driver.press(key=choice['key'])
        wait_for(lambda: read_setting(track_key) == str(track), 'Track choice was not persisted')
        wait_for(lambda: read_state()['music_playing'] and read_state()['music_track'] == track,
                 'Installed choice did not start the selected track')
        preserved()
    driver.press(key=reveal('None')['key'])
    wait_for(lambda: not read_state()['music_playing'], 'None did not stop background music')
    assert read_setting(track_key) == '-1'
    preserved()
    driver.key('escape')
    driver.wait_gone(label='Cue volume', role='slider')
    preserved()
    driver.press(label='Background music', role='button')
    driver.wait(label='Cue volume', role='slider')
    assert read_setting('sound_volume') == '17'
    assert read_setting('music_volume') == '23'
    driver.press(label='Close', role='button')
    driver.wait_gone(label='Cue volume', role='slider')
    preserved()
    assert not read_state()['music_playing']
