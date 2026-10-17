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
from PIL import Image, ImageOps, ImageStat

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
            command('xdotool', 'windowmove', window, '0', '0')
            time.sleep(2)
            return process, window
        time.sleep(.1)
    stop(process)
    raise AssertionError('App did not map its own window')


def light_text(image, name):
    """A dark screen's light text as black on white at twice the size, which
    OCR reads on tinted bars too; None for a light screen."""
    with Image.open(image) as picture:
        gray = ImageOps.grayscale(picture)
    if ImageStat.Stat(gray).mean[0] >= 110:
        return None
    path = output / (name + '-light-text.png')
    gray.point(lambda value: 0 if value > 150 else 255).resize((gray.width * 2, gray.height * 2)).save(path)
    return path


def capture(window, name):
    image = output / (name + '.png')
    command('import', '-window', window, str(image))
    text = command('tesseract', str(image), 'stdout', '--psm', '11')
    with Image.open(image) as picture:
        enlarged = output / (name + '-ocr.png')
        picture.resize((picture.width * 2, picture.height * 2)).save(enlarged)
        # Isolate the header action from detailed banner artwork on narrow
        # screens. Keep the full original capture as the visual evidence.
        header = picture.crop((max(0, picture.width - 160), 16, picture.width - 16, 60))
        header = ImageOps.invert(ImageOps.grayscale(header)).resize((576, 176))
        header_path = output / (name + '-header.png')
        header.save(header_path)
    text += '\n' + command('tesseract', str(enlarged), 'stdout', '--psm', '11')
    text += '\n' + command('tesseract', str(header_path), 'stdout', '--psm', '7')
    # On a wide window the night artwork around a centred dialog defeats
    # OCR's page segmentation; read the dialog's column on its own too.
    with Image.open(image) as picture:
        if picture.width > 800:
            left = (picture.width - 760) // 2
            column = output / (name + '-column.png')
            picture.crop((left, 60, left + 760, picture.height - 60)).save(column)
            text += '\n' + command('tesseract', str(column), 'stdout', '--psm', '11')
    stale = output / (name + '-light-text.png')
    if stale.exists():
        stale.unlink()
    light = light_text(image, name)
    if light:
        text += '\n' + command('tesseract', str(light), 'stdout', '--psm', '11')
    # OCR's page segmentation skips the dark text on the mint action fill.
    # Read that actual rendered button separately, retaining the full image.
    with Image.open(image) as picture:
        rgb = picture.convert('RGB')
        rows = []
        for y in range(picture.height // 2, picture.height):
            mint = sum(1 for x in range(picture.width)
                       if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30 and 130 < c[2] < 220)(rgb.getpixel((x, y))))
            if mint > min(200, picture.width // 3):
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
            if len(columns) > 12 and rows[-1] - rows[0] > 8:
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
    matches = [row for row in words_of(image) if row['text'] == target]
    if matches:
        word = matches[-1]
        x = int(word['left']) + int(word['width']) // 2
        y = int(word['top']) + int(word['height']) // 2
    elif target == 'Manage':
        with Image.open(image) as picture:
            x = picture.width - 85
        y = 38
    else:
        # Mint-filled action text is read from its enlarged crop by capture().
        with Image.open(image) as picture:
            rgb = picture.convert('RGB')
            rows = [y for y in range(picture.height // 2, picture.height)
                    if sum(1 for x in range(picture.width)
                           if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30
                               and 130 < c[2] < 220)(rgb.getpixel((x, y)))) > min(200, picture.width // 3)]
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


def click_mint(window, name, first=True):
    """Press a filled mint action that OCR cannot read, by its rendered fill."""
    image, _ = capture(window, name)
    with Image.open(image) as picture:
        rgb = picture.convert('RGB')
        rows = [y for y in range(130, picture.height - 40)
                if sum(1 for x in range(picture.width)
                       if (lambda c: 100 < c[0] < 200 and c[1] > c[0] + 30
                           and 130 < c[2] < 220)(rgb.getpixel((x, y)))) > picture.width // 4]
        assert rows, 'No filled action in ' + name
        y = rows[0] + 15 if first else rows[-1] - 15
        x = picture.width // 2
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    command('xdotool', 'mousedown', '1')
    time.sleep(.15)
    command('xdotool', 'mouseup', '1')
    time.sleep(1)


def read_manager(window, name, width, height, steps=8):
    """Read the whole Manage practices list, scrolling a few rows at a time."""
    _, text = capture(window, name + '-0')
    for step in range(1, steps + 1):
        command('xdotool', 'mousemove', '--window', window, str(width // 2), str(height // 2))
        command('xdotool', 'click', '--repeat', '3', '--delay', '80', '5')
        time.sleep(.4)
        text += '\n' + capture(window, name + '-' + str(step))[1]
    return text


def close_manager(window):
    command('xdotool', 'mousemove', '--window', window, '350', '86')
    command('xdotool', 'mousedown', '1')
    time.sleep(.15)
    command('xdotool', 'mouseup', '1')
    time.sleep(.5)


def words_of(image):
    """Rendered words with their boxes, also from a wide window's dialog column."""
    tsv = command('tesseract', str(image), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
    words = [row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t') if row['text'].strip()]
    column = Path(str(image)[:-4] + '-column.png')
    if column.exists():
        with Image.open(image) as picture:
            left = (picture.width - 760) // 2
        tsv = command('tesseract', str(column), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
        for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
            if row['text'].strip():
                row['left'] = str(int(row['left']) + left)
                row['top'] = str(int(row['top']) + 60)
                words.append(row)
    light = Path(str(image)[:-4] + '-light-text.png')
    if light.exists():
        tsv = command('tesseract', str(light), 'stdout', '--psm', '11', '-c', 'tessedit_create_tsv=1')
        for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
            if row['text'].strip():
                for field in ('left', 'top', 'width', 'height'):
                    row[field] = str(int(row[field]) // 2)
                words.append(row)
    return words


def press(window, x, y):
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    command('xdotool', 'mousedown', '1')
    time.sleep(.15)
    command('xdotool', 'mouseup', '1')
    time.sleep(.6)


def drag_row(window, name, practice_word, section_word):
    """Drag a practice by the six-dot handle before its name onto a section's header.

    Installed's header reads "Installed"; Not installed's is the only
    lowercase "installed"."""
    image, text = capture(window, name)
    words = words_of(image)
    practice = [row for row in words if row['text'] == practice_word]
    section = [row for row in words if row['text'] == section_word]
    if section_word == 'installed':
        # OCR sometimes splits it into "i nstalled".
        section = [row for row in words if 'nstalled' in row['text'] and not row['text'].startswith('I')]
    assert practice and section, text
    x = int(practice[-1]['left']) - 20
    y = int(practice[-1]['top']) + int(practice[-1]['height']) // 2
    to_x = int(section[0]['left']) + int(section[0]['width']) // 2
    to_y = int(section[0]['top']) + int(section[0]['height']) // 2
    command('xdotool', 'mousemove', '--window', window, str(x), str(y))
    command('xdotool', 'mousedown', '1')
    time.sleep(.2)
    for step in range(1, 13):
        command('xdotool', 'mousemove', '--window', window,
                str(x + (to_x - x) * step // 12), str(y + (to_y - y) * step // 12))
        time.sleep(.08)
    time.sleep(.4)
    command('xdotool', 'mouseup', '1')
    time.sleep(1)


with tempfile.TemporaryDirectory(prefix='inbe-downloads-ui-') as temporary:
    profile = Path(temporary)
    # Lumi's guide narration downloads by itself in the app's language; its
    # copy is already here, so the test reaches no server.
    (profile / 'packages').mkdir()
    shutil.copyfile(ROOT / 'build/practice-content/guide.en.zib', profile / 'packages/practice-guide.en.zib')
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
    cache = profile / 'packages'
    sizes = {name: (ROOT / 'build/practice-content' / (name + '.zib')).stat().st_size
             for name in ('whm', 'meditation', 'sunsalutation')}
    process, window = launch(profile, 'installed')
    try:
        # Wim Hof ships installed; it is the only practice on the home.
        _, text = capture(window, 'installed')
        assert 'Manage practices' in text and 'Start' in text and '/ 5' not in text, text
        click_word(window, 'manager-open', 'Manage')
        time.sleep(1)
        _, text = capture(window, 'manager')
        whm_kb = (sizes['whm'] + 1023) // 1024
        meditation_kb = (sizes['meditation'] + 1023) // 1024
        sun_mb = (sizes['sunsalutation'] + 512 * 1024) // (1024 * 1024)
        # Two sections: Wim Hof is installed; Meditation and Breathing
        # Patterns ship with the app, so they show their size before they are
        # added; Sun Salutation downloads. No row has a Remove or trash button.
        assert 'Installed' in text and 'Not installed' in text, text
        assert str(whm_kb) + ' KB' in text and 'Comes with the app' in text, text
        assert str(meditation_kb) + ' KB' in text and str(sun_mb) + ' MB' in text, text
        assert 'Not downloaded' in text and 'Remove' not in text, text
        assert 'Included in this version' not in text, text
        assert not (cache / 'practice-meditation.zib').exists()
        # Dragged by its handle into Installed, Meditation is added from the
        # app's own copy at once, without a copy of its own.
        drag_row(window, 'manager-drag-meditation', 'Meditation', 'Installed')
        _, text = capture(window, 'manager-added')
        assert 'Downloading' not in text and str(meditation_kb) + ' KB' in text, text
        assert not (cache / 'practice-meditation.zib').exists()
        assert (cache / 'practice-meditation.added').exists()
        # Dropped on Wim Hof, Meditation takes its place in the order.
        drag_row(window, 'manager-reorder', 'Meditation', 'Wim')
        _, text = capture(window, 'manager-reordered')
        assert 0 <= text.find('Meditation') < text.find('Wim'), text
        # Tapping a row opens its one next step: Meditation comes off
        # Practice. Wim Hof is dragged out, last.
        click_word(window, 'manager-meditation', 'Meditation')
        _, text = capture(window, 'manager-meditation-open')
        assert 'Remove' in text and 'Practice' in text, text
        click_word(window, 'manager-remove', 'Remove')
        assert (cache / 'practice-meditation.removed').exists()
        drag_row(window, 'manager-drag-whm', 'Wim', 'installed')
        _, text = capture(window, 'removed')
        # Removed, the shipped practices offer themselves again without a
        # download, still in the app.
        assert 'Drag a practice here' in text and 'Comes with the app' in text, text
        assert 'Remove' not in text and 'Included in this version' not in text, text
        assert not (cache / 'practice-meditation.zib').exists()
        assert not (cache / 'practice-meditation.added').exists()
        close_manager(window)
        _, text = capture(window, 'empty')
        assert 'No practices installed' in text and 'Start' not in text, text
    finally:
        stop(process)
    assert (cache / 'practice-whm.removed').exists()
    # The order is saved: Meditation, Wim Hof, then the default order.
    with sqlite3.connect(profile / 'inbe.db') as database:
        order = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                 (user, 'practice_order')).fetchone()
        assert order and order[0] == '110324', order
    process, window = launch(profile, 'still-removed')
    try:
        _, text = capture(window, 'still-removed')
        assert 'No practices installed' in text, text
        click_mint(window, 'empty-manage')
        _, text = capture(window, 'manager-removed')
        assert 'Drag a practice here' in text and 'Remove' not in text, text
        # Wim Hof's open row adds it back from the app's own copy, without a
        # download.
        click_word(window, 'manager-whm', 'Wim')
        _, text = capture(window, 'manager-whm-open')
        assert 'adds back' in text, text
        click_mint(window, 'manager-restore')
        _, text = capture(window, 'manager-restored')
        assert 'Comes with the app' in text and 'Drag a practice here' not in text, text
        close_manager(window)
        _, text = capture(window, 'restored')
        assert 'Start' in text and 'No practices installed' not in text, text
    finally:
        stop(process)
    assert not (cache / 'practice-whm.removed').exists()
    with sqlite3.connect(profile / 'inbe.db') as database:
        value = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                 (user, 'tai_chi_progress')).fetchone()[0]
        assert value.startswith('1'), 'Content removal changed saved practice progress'
        selected = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                    (user, 'exercise_type')).fetchone()[0]
        assert selected == '0', 'Managing downloads switched the practice underneath'
    # A downloaded practice joins the home, with its banner from its own pack.
    # Downloading clears the earlier Remove, as adding it does.
    shutil.copyfile(ROOT / 'build/practice-content/meditation.zib', cache / 'practice-meditation.zib')
    assert (cache / 'practice-meditation.removed').exists()
    (cache / 'practice-meditation.removed').unlink()
    process, window = launch(profile, 'two-installed')
    try:
        _, text = capture(window, 'two-installed')
        # Meditation was dragged ahead of Wim Hof, so the selected Wim Hof is
        # second on Practice.
        assert '2 / 2' in text or '2/2' in text, text
    finally:
        stop(process)
    process, window = launch(profile, 'narrow', 320, 640)
    try:
        _, text = capture(window, 'narrow')
        assert 'Manage practices' in text and 'Start' in text, text
        click_word(window, 'narrow-open', 'Manage')
        _, text = capture(window, 'narrow-manager')
        assert 'Meditation' in text, text
        command('xdotool', 'mousemove', '--window', window, '160', '350')
        command('xdotool', 'click', '--repeat', '10', '--delay', '80', '5')
        time.sleep(.5)
        _, text = capture(window, 'narrow-manager-bottom')
        assert 'Tai Chi' in text, text
    finally:
        stop(process)
    with sqlite3.connect(profile / 'inbe.db') as database:
        for key, value in {'exercise_type': 4, 'voice_narration_enabled': 1}.items():
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?',
                             (str(value), user, key))
    shutil.copyfile(ROOT / 'build/practice-content/taichi.zib', cache / 'practice-taichi.zib')
    shutil.copyfile(ROOT / 'build/practice-content/taichi.en.zib', cache / 'practice-taichi.en.zib')
    shutil.copyfile(ROOT / 'build/practice-content/taichi.en.male.zib', cache / 'practice-taichi.en.male.zib')
    # A Tai Chi pack on the device without an account that bought it stays
    # locked: off the home, offered at its price with its size.
    process, window = launch(profile, 'taichi-unowned', 1280, 900)
    try:
        _, text = capture(window, 'taichi-unowned')
        assert 'Tai Chi' not in text and 'Start' in text, text
        click_word(window, 'taichi-unowned-open', 'Manage')
        time.sleep(1)
        command('xdotool', 'mousemove', '--window', window, '640', '450')
        command('xdotool', 'click', '--repeat', '16', '--delay', '80', '5')
        time.sleep(.5)
        _, text = capture(window, 'taichi-unowned-manager')
        assert 'Tai Chi' in text and 'Dew' in text and 'MB' in text, text
        # Narration is chosen in each practice's Customize, never here.
        assert 'Voice narration' not in text and 'Female voice' not in text, text
    finally:
        stop(process)
    # The account's purchase, remembered on this device; sync stays off, so
    # nothing reaches a node.
    account = 'a' * 64
    with sqlite3.connect(profile / 'inbe.db') as database:
        # Unowned, Tai Chi gave way to Wim Hof; the owner selects it again.
        for key, value in {'sync_public_id': account, 'sync_public_key': 'fixture-public',
                           'sync_private_key': 'fixture-private', 'sync_enabled': 0,
                           'exercise_type': 4}.items():
            database.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,?) '
                             'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value',
                             (user, key, str(value), int(time.time())))
        database.execute('INSERT OR REPLACE INTO social_snapshots(user_id,kind,json,updated_at) VALUES(?,?,?,?)',
                         (user, 'practice.unlocks', '{"account_id":"' + account + '","taichi":true}',
                          int(time.time())))
    for name, width, height in [('taichi-ready', 390, 844), ('taichi-narrow', 320, 640),
                                ('desktop-manager', 1280, 900)]:
        process, window = launch(profile, name, width, height)
        try:
            _, text = capture(window, name)
            assert 'Start' in text and 'Manage practices' in text and 'Available offline' not in text, text
            # The account's purchase is known from the first frame: Tai Chi stays selected.
            assert 'Tai Chi' in text, text
            click_word(window, name + '-open', 'Manage')
            time.sleep(1)
            text = read_manager(window, name + '-manager', width, height)
            assert 'Tai Chi' in text and 'On this device' in text, text
            # Bought: no Dew price or unlock button is left.
            assert 'Dew' not in text and 'Unlock' not in text, text
            assert 'Voice narration' not in text and "Lumi's guide" not in text, text
            if name == 'desktop-manager':
                close_manager(window)
                click_word(window, name + '-customize', 'Customize')
                time.sleep(1)
                _, text = capture(window, name + '-customize-open')
                # Jade woman speaks with the female voice, in the language
                # chosen in a list that downloads or removes each language.
                assert 'Female voice' in text and 'Male voice' in text and 'English' in text, text
                assert 'Plays in' not in text and 'Downloading' not in text, text
                click_word(window, name + '-languages', 'English')
                time.sleep(.5)
                _, text = capture(window, name + '-languages-open')
                assert 'Deutsch' in text and 'Italiano' in text, text
        finally:
            stop(process)
    # Sun Salutation speaks in its own free packs; a man speaks with the male voice.
    with sqlite3.connect(profile / 'inbe.db') as database:
        for key, value in {'exercise_type': 2, 'sun_salutation_character': 2}.items():
            database.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,?) '
                             'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value',
                             (user, key, str(value), int(time.time())))
    for name in ('sunsalutation', 'sunsalutation.en.male'):
        shutil.copyfile(ROOT / 'build/practice-content' / (name + '.zib'),
                        cache / ('practice-' + name + '.zib'))
    process, window = launch(profile, 'sun-customize', 1280, 900)
    try:
        click_word(window, 'sun-customize-open', 'Customize')
        time.sleep(1)
        command('xdotool', 'mousemove', '--window', window, '640', '450')
        command('xdotool', 'click', '--repeat', '20', '--delay', '80', '5')
        time.sleep(.5)
        _, text = capture(window, 'sun-customize-narration')
        assert 'Voice narration' in text and 'Female voice' in text and 'Male voice' in text, text
        assert 'English' in text and 'Plays in' not in text, text
    finally:
        stop(process)
    # Dragged out of Installed, a downloaded practice stays on this device;
    # its open row deletes the copy and its narration after asking once.
    with sqlite3.connect(profile / 'inbe.db') as database:
        for key, value in {'exercise_type': 2, 'voice_narration_enabled': 0}.items():
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?',
                             (str(value), user, key))
    process, window = launch(profile, 'sun-delete', 1280, 900)
    try:
        click_word(window, 'sun-delete-open', 'Manage')
        time.sleep(1)
        _, text = capture(window, 'sun-delete-manager')
        assert 'Sun Salutation' in text and 'On this device' in text and str(sun_mb) + 'MB' in text.replace(' ', ''), text
        drag_row(window, 'sun-delete-drag', 'Sun', 'installed')
        assert (cache / 'practice-sunsalutation.zib').exists()
        assert (cache / 'practice-sunsalutation.removed').exists()
        click_word(window, 'sun-delete-row', 'Sun')
        _, text = capture(window, 'sun-delete-row-open')
        assert 'still on this device' in text and 'Delete files' in text, text
        click_word(window, 'sun-delete-files', 'files')
        image, text = capture(window, 'sun-delete-asked')
        assert 'Delete Sun Salutation?' in text and 'Your progress stays.' in text, text
        assert (cache / 'practice-sunsalutation.zib').exists()
        # Delete fills the right half under the question, beside Cancel; the
        # question starts where both buttons do.
        words = words_of(image)
        cancel = [row for row in words if row['text'] == 'Cancel']
        question = [row for row in words if row['text'] == 'Delete']
        assert cancel and question, text
        cancel_x = int(cancel[-1]['left']) + int(cancel[-1]['width']) // 2
        start_x = int(question[0]['left'])
        press(window, cancel_x + 2 * (cancel_x - start_x) + 8,
              int(cancel[-1]['top']) + int(cancel[-1]['height']) // 2)
        _, text = capture(window, 'sun-deleted')
        assert str(sun_mb) + 'MB' in text.replace(' ', '') and 'Not downloaded' in text, text
        assert not (cache / 'practice-sunsalutation.zib').exists()
        assert not (cache / 'practice-sunsalutation.en.male.zib').exists()
        assert not (cache / 'practice-sunsalutation.removed').exists()
    finally:
        stop(process)
print('Private Practices modal: Installed and Not installed sections, real sizes, drag to add and '
      'remove, reorder that Practice follows, rows that open their next step, removal that stays, '
      'restore without download, '
      'installed-only home, saved progress, owned Tai Chi without a price, narration languages, '
      'narrow layout, Sun Salutation narration and delete passed')
