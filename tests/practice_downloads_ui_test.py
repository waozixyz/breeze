"""Private-display regression of the real Practices download controls."""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from PIL import Image, ImageOps

assert int(os.environ.get('DISPLAY', ':0').split(':')[-1].split('.')[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = ROOT / 'build/practice-downloads-ui-test'
output.mkdir(parents=True, exist_ok=True)


def command(*arguments):
    return subprocess.check_output(arguments, text=True, timeout=10).strip()


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name, width=390, height=844):
    log = (output / (name + '.log')).open('w')
    process = subprocess.Popen([str(binary), '--bundle', str(ROOT / 'build/inbe-full.zib')],
        cwd=ROOT, env=os.environ | {'APP_DATA_ROOT': str(profile), 'APP_NO_TRAY': '1',
        'SDL_AUDIODRIVER': 'dummy', 'YUE_DESKTOP_RECOVERY': '0'}, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(200):
        assert process.poll() is None, 'App exited: ' + name
        found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(process.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / 'inbe.db').exists():
            window = found.stdout.splitlines()[0]
            command('xdotool', 'windowsize', window, str(width), str(height))
            time.sleep(2)
            return process, window
        time.sleep(.1)
    stop(process)
    raise AssertionError('App did not map its own window')


def capture(window, name):
    image = output / (name + '.png')
    command('import', '-window', window, str(image))
    text = command('tesseract', str(image), 'stdout', '--psm', '11')
    # OCR's page segmentation skips the dark text on the mint action fill.
    # Read that actual rendered button separately, retaining the full image.
    with Image.open(image) as picture:
        rgb = picture.convert('RGB')
        rows = []
        for y in range(picture.height // 2, picture.height):
            mint = sum(1 for x in range(picture.width)
                       if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30 and 130 < c[2] < 220)(rgb.getpixel((x, y))))
            if mint > picture.width // 3:
                rows.append(y)
        if rows:
            for index in range(len(rows) - 1, 0, -1):
                if rows[index] - rows[index - 1] > 12:
                    rows = rows[index:]
                    break
            middle = (rows[0] + rows[-1]) // 2
            columns = [x for x in range(picture.width)
                       if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30
                           and 130 < c[2] < 220)(rgb.getpixel((x, middle)))]
            button = picture.crop((columns[0] + 3, rows[0] + 3, columns[-1] - 2, rows[-1] - 2))
            button = ImageOps.grayscale(button).point(lambda value: 255 if value > 120 else 0)
            button = button.resize((button.width * 3, button.height * 3))
            button_path = output / (name + '-action.png')
            button.save(button_path)
            text += '\n' + command('tesseract', str(button_path), 'stdout', '--psm', '7')
    (output / (name + '.txt')).write_text(text)
    return image, text


def click_word(window, name, target):
    image, text = capture(window, name)
    assert target in text, text
    tsv = command('tesseract', str(image), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
    words = list(csv.DictReader(io.StringIO(tsv), delimiter='\t'))
    matches = [row for row in words if row['text'] == target]
    if matches:
        word = matches[-1]
        x = int(word['left']) + int(word['width']) // 2
        y = int(word['top']) + int(word['height']) // 2
    else:
        # Mint-filled action text is read from its enlarged crop by capture().
        with Image.open(image) as picture:
            rgb = picture.convert('RGB')
            rows = [y for y in range(picture.height // 2, picture.height)
                    if sum(1 for x in range(picture.width)
                           if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30
                               and 130 < c[2] < 220)(rgb.getpixel((x, y)))) > picture.width // 3]
            assert rows, 'Action button not found: ' + target
            for index in range(len(rows) - 1, 0, -1):
                if rows[index] - rows[index - 1] > 12:
                    rows = rows[index:]
                    break
            x = picture.width * 3 // 4
            y = (rows[0] + rows[-1]) // 2
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    command('xdotool', 'mousedown', '1')
    time.sleep(.15)
    command('xdotool', 'mouseup', '1')
    time.sleep(.6)


with tempfile.TemporaryDirectory(prefix='inbe-downloads-ui-') as temporary:
    profile = Path(temporary)
    process, _ = launch(profile, 'initialize')
    stop(process)
    with sqlite3.connect(profile / 'inbe.db') as database:
        user = database.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = {'language': 'en', 'language_system': 0, 'language_setup_done': 1,
            'apps_setup_done': 1, 'main_tab': 1, 'exercise_type': 0, 'tutorial_seen': 1,
            'lumi_guides_seen': 127, 'launcher_guide_seen': 1, 'package_updates_allowed': 0,
            'voice_narration_enabled': 0, 'apps_last_update_check': 1900000000,
            'tai_chi_progress': '1' + '0' * 47}
        for key, value in settings.items():
            database.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, str(value)))
    process, window = launch(profile, 'download')
    try:
        _, text = capture(window, 'download')
        assert 'Download practice' in text, text
        click_word(window, 'manual-open', 'How')
        for page in range(3):
            click_word(window, 'manual-page-' + str(page), 'Next')
        click_word(window, 'manual-finish', 'Start')
        _, text = capture(window, 'manual-needs-download')
        assert 'How to' in text and any(action in text.lower() for action in
            ('download practice', 'cancel', 'retry download')), text
        assert any(status in text.lower() for status in ('downloading', 'download failed')), text
    finally:
        stop(process)
    catalog = json.loads((ROOT / 'build/package-assets/practices/assets/practices/catalog.json').read_text())
    pack = next(pack for pack in catalog['packs'] if pack['practice'] == 'whm' and not pack['language'])
    cache = profile / 'packages'
    cache.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'build/practice-content/whm.zib', cache / 'practice-whm.zib')
    process, window = launch(profile, 'ready')
    try:
        image, text = capture(window, 'ready')
        assert 'Available offline' in text and 'Start' in text and 'Remove' in text, text
        tsv = command('tesseract', str(image), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
        word = next(row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t') if row['text'] == 'Remove')
        x = int(word['left']) + int(word['width']) // 2
        y = int(word['top']) + int(word['height']) // 2
        command('xdotool', 'mousemove', '--window', window, str(x), str(y))
        command('xdotool', 'mousedown', '1')
        time.sleep(.15)
        command('xdotool', 'mouseup', '1')
        time.sleep(1)
        _, text = capture(window, 'removed')
        assert 'Download practice' in text, text
    finally:
        stop(process)
    assert not (cache / 'practice-whm.zib').exists()
    with sqlite3.connect(profile / 'inbe.db') as database:
        value = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                 (user, 'tai_chi_progress')).fetchone()[0]
        assert value.startswith('1'), 'Content removal changed saved practice progress'
    process, window = launch(profile, 'narrow', 320, 640)
    try:
        _, text = capture(window, 'narrow')
        assert 'Download practice' in text, text
    finally:
        stop(process)
    with sqlite3.connect(profile / 'inbe.db') as database:
        for key, value in {'exercise_type': 4, 'voice_narration_enabled': 1}.items():
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?',
                             (str(value), user, key))
    shutil.copyfile(ROOT / 'build/practice-content/taichi.zib', cache / 'practice-taichi.zib')
    shutil.copyfile(ROOT / 'build/practice-content/taichi.en.zib', cache / 'practice-taichi.en.zib')
    for name, width, height in [('taichi-ready', 390, 844), ('taichi-narrow', 320, 640)]:
        process, window = launch(profile, name, width, height)
        try:
            _, text = capture(window, name)
            assert 'Available offline' in text and 'Narration ready offline' in text and 'Start' in text, text
        finally:
            stop(process)
print('Private Practices UI: manual download guard, offline-ready, removal with saved progress and narrow layout passed')
