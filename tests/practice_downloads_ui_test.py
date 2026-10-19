"""Private-display regression of the real Practices download controls."""
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

assert int(os.environ.get('DISPLAY', ':0').split(':')[-1].split('.')[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = ROOT / 'build/practice-downloads-ui-test'
output.mkdir(parents=True, exist_ok=True)
driver = UiDriver(output / 'driver')


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
    log_path = output / (name + '.log')
    log = log_path.open('w')
    process = subprocess.Popen([str(binary), '--bundle', str(ROOT / 'build/inbe-full.zib')],
        cwd=ROOT, env=os.environ | driver.environment() | {'APP_DATA_ROOT': str(profile),
        'APP_NO_TRAY': '1', 'SDL_AUDIODRIVER': 'dummy', 'YUE_DESKTOP_RECOVERY': '0'},
        stdout=log, stderr=subprocess.STDOUT)
    driver.attach(process, log_path)
    # A loaded machine can take a while to start the app.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        assert process.poll() is None, 'App exited: ' + name
        found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(process.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / 'inbe.db').exists():
            window = found.stdout.splitlines()[0]
            command('xdotool', 'windowsize', window, str(width), str(height))
            command('xdotool', 'windowmove', window, '0', '0')
            driver.wait_idle(frames=3)
            return process, window
        time.sleep(.1)
    stop(process)
    raise AssertionError('App did not map its own window')


def screen_text():
    """What the window shows: every visible label."""
    return driver.text()


def manager_nodes():
    """Every widget of the Manage practices dialog, also those scrolled away."""
    nodes = driver.tree()
    modals = [node for node in nodes if node['kind'] == 'modal']
    assert modals, 'Manage practices is not open: ' + screen_text()
    inside = {modals[-1]['index']}
    found = []
    for node in nodes:
        if node['parent'] in inside:
            inside.add(node['index'])
            found.append(node)
    return found


def manager_text():
    return '\n'.join(node['label'] for node in manager_nodes() if node['label'])


def manager_rows():
    """The dialog's practices in order. Each row starts with its drag handle,
    an unlabeled button, then its name, status, price and buttons."""
    nodes = manager_nodes()
    scroll = next(node for node in nodes if node['kind'] == 'scroll')
    rows = []
    for node in nodes:
        if node['parent'] != scroll['index']:
            continue
        if node['kind'] == 'button' and not node['label']:
            rows.append(dict(handle=node, name='', nodes=[]))
            continue
        assert rows, ('A practice row has no handle', node)
        row = rows[-1]
        if node['kind'] == 'text' and not row['name']:
            row['name'] = node['label']
        row['nodes'].append(node)
    return rows


def manager_row(name):
    rows = [row for row in manager_rows() if row['name'].startswith(name)]
    assert rows, f'No {name} row: ' + manager_text()
    return rows[0]


def row_text(row):
    return '\n'.join(node['label'] for node in row['nodes'] if node['label'])


def row_names():
    return [row['name'] for row in manager_rows()]


# Installed comes first and is selected on opening; breathing practices are
# under Meditation.
TABS = ['Installed', 'Meditation', 'Yoga', 'Martial arts']


def manager_tabs():
    """The dialog's tabs in order, as label and whether it is selected."""
    return [(node['label'], node['selected']) for node in manager_nodes() if node['role'] == 'tab']


def selected_tab():
    selected = [label for label, chosen in manager_tabs() if chosen]
    assert len(selected) == 1, manager_tabs()
    return selected[0]


def select_tab(label):
    """Show one tab's practices."""
    tabs = [node for node in manager_nodes() if node['role'] == 'tab' and node['label'] == label]
    assert tabs, f'No {label} tab: ' + manager_text()
    driver.press(key=tabs[0]['key'])
    driver.wait_idle(frames=2)
    assert selected_tab() == label, manager_tabs()


def act(name, label):
    """Press the button of a practice's row."""
    # Install and Uninstall carry the size, such as "Install · 449 KB".
    buttons = [node for node in manager_row(name)['nodes'] if node['kind'] == 'button'
               and (node['label'] == label or node['label'].startswith(label + ' · '))]
    assert buttons, f'{name} has no {label} button: ' + manager_text()
    driver.press(key=buttons[0]['key'])
    driver.wait_idle(frames=2)


def open_manager():
    driver.press(label='Manage practices', role='button')
    driver.wait(label='Close', role='button')
    driver.wait_idle(frames=2)


def close_manager():
    close = [node for node in manager_nodes() if node['label'] == 'Close' and node['kind'] == 'button']
    assert close, manager_text()
    driver.press(key=close[0]['key'])
    deadline = time.monotonic() + 10
    while any(node['kind'] == 'modal' for node in driver.tree()):
        assert time.monotonic() < deadline, 'Manage practices did not close'
        time.sleep(.05)
    driver.wait_idle(frames=2)


def scroll_manager(steps):
    """Turn the wheel over the dialog's list, one step a frame."""
    scroll = next(node for node in manager_nodes() if node['kind'] == 'scroll')
    x, y = UiDriver.center(scroll)
    for _ in range(steps):
        driver.pointer(x, y, wheel=-1)
    driver.release_pointer()
    driver.wait_idle(frames=2)


def wait_file(path, present=True):
    """A marker or pack the press wrote or removed."""
    deadline = time.monotonic() + 5
    while path.exists() != present:
        assert time.monotonic() < deadline, (path, 'present' if present else 'absent')
        time.sleep(.05)


def visible_label(contains):
    return driver.find(contains=contains, visible=True)


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
        # Wim Hof ships installed; it is the only practice on the home, so
        # there is no "1 / 5" between practices.
        driver.wait(label='Manage practices', role='button')
        driver.wait(label='Start Practice', role='button')
        assert not any(re.fullmatch(r'\d+ / \d+', label) for label in driver.labels()), screen_text()
        open_manager()
        # Manage practices opens on Installed: Wim Hof, which ships
        # installed, and Breathing Patterns and Meditation, which come with
        # the app. Sun Salutation, Tai Chi and Astral Projection are not on
        # this device, so only their own tabs list them.
        assert manager_tabs() == [(label, label == 'Installed') for label in TABS], manager_tabs()
        assert row_names() == ['Wim Hof Breathing', 'Breathing Patterns', 'Meditation'], row_names()
        text = manager_text()
        whm_kb = (sizes['whm'] + 1023) // 1024
        meditation_kb = (sizes['meditation'] + 1023) // 1024
        sun_mb = (sizes['sunsalutation'] + 512 * 1024) // (1024 * 1024)
        # Wim Hof is on Practice, so its button uninstalls it; Meditation and
        # Breathing Patterns install. Each row has its size and one button,
        # and no menu.
        assert 'Uninstall' in row_text(manager_row('Wim')), text
        assert 'On Practice' not in text and 'On device' not in text, text
        assert str(whm_kb) + ' KB' in row_text(manager_row('Wim')) and 'Comes with' not in text, text
        assert str(meditation_kb) + ' KB' in row_text(manager_row('Meditation')), text
        for row in manager_rows():
            buttons = [node for node in row['nodes'] if node['kind'] == 'button']
            assert len(buttons) == 1, (row['name'], 'has more than one button', buttons)
        assert 'Remove' not in text and 'Included in this version' not in text, text
        # Each kind's tab lists its practices in order, on this device or
        # not; breathing practices are under Meditation.
        kinds = {'Meditation': ['Wim Hof Breathing', 'Breathing Patterns', 'Meditation', 'Astral Projection'],
                 'Yoga': ['Sun Salutation'], 'Martial arts': ['Tai Chi']}
        for label, names in kinds.items():
            select_tab(label)
            assert row_names() == names, (label, row_names())
            for row in manager_rows():
                buttons = [node for node in row['nodes'] if node['kind'] == 'button']
                assert len(buttons) == 1, (label, row['name'], 'has more than one button', buttons)
            if label == 'Meditation':
                # Every practice has a row, also the last one in the order.
                assert 'Install' in row_text(manager_row('Astral Projection')), manager_text()
            if label == 'Yoga':
                assert str(sun_mb) + 'MB' in row_text(manager_row('Sun')).replace(' ', ''), manager_text()
        select_tab('Installed')
        assert not (cache / 'practice-meditation.zib').exists()
        # Install adds Meditation from the app's own copy at once, without a
        # copy of its own.
        act('Meditation', 'Install')
        text = manager_text()
        assert 'Downloading' not in text and str(meditation_kb) + ' KB' in text, text
        assert 'Uninstall' in row_text(manager_row('Meditation')), text
        wait_file(cache / 'practice-meditation.added')
        assert not (cache / 'practice-meditation.zib').exists()
        # Dropped on Wim Hof by the six-dot handle before its name, Meditation
        # takes its place in the order.
        meditation = manager_row('Meditation')
        wim = next(node for node in manager_row('Wim')['nodes'] if node['label'].startswith('Wim'))
        driver.drag(UiDriver.center(meditation['handle']), UiDriver.center(wim), steps=12)
        driver.wait_idle(frames=3)
        names = [row['name'] for row in manager_rows()]
        assert names.index('Meditation') < names.index('Wim Hof Breathing'), names
        # Within the Meditation tab, Astral Projection dropped on Breathing
        # Patterns takes its place in the same order, also while it is not
        # installed; Installed keeps its own practices in that order.
        select_tab('Meditation')
        assert row_names() == ['Meditation', 'Wim Hof Breathing', 'Breathing Patterns', 'Astral Projection'], \
            row_names()
        astral = manager_row('Astral Projection')
        patterns = next(node for node in manager_row('Breathing')['nodes'] if node['label'].startswith('Breathing'))
        driver.drag(UiDriver.center(astral['handle']), UiDriver.center(patterns), steps=12)
        driver.wait_idle(frames=3)
        assert row_names() == ['Meditation', 'Wim Hof Breathing', 'Astral Projection', 'Breathing Patterns'], \
            row_names()
        select_tab('Installed')
        assert row_names() == ['Meditation', 'Wim Hof Breathing', 'Breathing Patterns'], row_names()
        # Uninstall takes both off Practice; they come with the app, so
        # nothing is deleted, nothing asks and both stay under Installed.
        act('Meditation', 'Uninstall')
        wait_file(cache / 'practice-meditation.removed')
        act('Wim', 'Uninstall')
        assert row_names() == ['Meditation', 'Wim Hof Breathing', 'Breathing Patterns'], row_names()
        text = manager_text()
        assert 'Uninstall' not in text and str(whm_kb) + ' KB' in text, text
        assert 'Remove' not in text and 'Included in this version' not in text, text
        assert not (cache / 'practice-meditation.zib').exists()
        assert not (cache / 'practice-meditation.added').exists()
        close_manager()
        driver.wait(contains='No practices installed')
        assert not visible_label('Start'), screen_text()
    finally:
        stop(process)
    assert (cache / 'practice-whm.removed').exists()
    # The order is saved: Meditation, Wim Hof, Astral Projection, then the
    # default order.
    with sqlite3.connect(profile / 'inbe.db') as database:
        order = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                 (user, 'practice_order')).fetchone()
        assert order and order[0] == '1105324', order
    process, window = launch(profile, 'still-removed')
    try:
        driver.wait(contains='No practices installed')
        # The empty home's own Manage practices action opens the dialog.
        open_manager()
        text = manager_text()
        assert 'Uninstall' not in text and 'Remove' not in text, text
        # Wim Hof's Install adds it back from the app's own copy, without a
        # download.
        act('Wim', 'Install')
        text = manager_text()
        assert 'Uninstall' in row_text(manager_row('Wim')) and str(whm_kb) + ' KB' in text, text
        # The chosen tab lasts while the dialog is open; it opens on
        # Installed again.
        select_tab('Yoga')
        close_manager()
        open_manager()
        assert selected_tab() == 'Installed', manager_tabs()
        close_manager()
        driver.wait(label='Start Practice', role='button')
        assert not visible_label('No practices installed'), screen_text()
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
        # Meditation was dragged ahead of Wim Hof, so the selected Wim Hof is
        # second on Practice.
        driver.wait(label='2 / 2')
    finally:
        stop(process)
    process, window = launch(profile, 'narrow', 320, 640)
    try:
        driver.wait(label='Manage practices', role='button')
        driver.wait(label='Start Practice', role='button')
        open_manager()
        # In a narrow dialog a tab's last row scrolls into view.
        select_tab('Meditation')
        scroll_manager(10)
        driver.wait(label='Astral Projection')
        select_tab('Yoga')
        driver.wait(label='Sun Salutation')
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
        driver.wait(label='Start Practice', role='button')
        assert not visible_label('Tai Chi'), screen_text()
        open_manager()
        # Locked, it is not installed even with its pack here; Martial arts
        # offers it.
        assert 'Tai Chi' not in row_names(), row_names()
        select_tab('Martial arts')
        driver.wait(label='Tai Chi')
        # Its Unlock button says the price. Its row shows no size: the old
        # single list passed a size check only through other rows' buttons.
        text = row_text(manager_row('Tai Chi'))
        assert 'Dew' in text, manager_text()
        # Narration is chosen in each practice's Customize, never here.
        text = manager_text()
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
            driver.wait(label='Start Practice', role='button')
            driver.wait(label='Manage practices', role='button')
            assert not visible_label('Available offline'), screen_text()
            # The account's purchase is known from the first frame: Tai Chi stays selected.
            driver.wait(label='Tai Chi')
            open_manager()
            # Bought and on this device, Tai Chi is under Installed, also
            # when its row is scrolled out of the dialog.
            text = manager_text()
            assert 'Tai Chi' in [row['name'] for row in manager_rows()], text
            # Bought: no Dew price or unlock button is left.
            assert 'Dew' not in text and 'Unlock' not in text, text
            assert 'Voice narration' not in text and "Lumi's guide" not in text, text
            if name == 'desktop-manager':
                close_manager()
                driver.press(label='Customize', role='button')
                # Jade woman speaks with the female voice, in the language
                # chosen in a list that downloads or removes each language.
                driver.wait(label='Female voice', role='button')
                driver.wait(label='Male voice', role='button')
                driver.wait(label='English', role='dropdown')
                text = screen_text()
                assert 'Plays in' not in text and 'Downloading' not in text, text
                driver.press(label='English', role='dropdown')
                driver.wait(label='Deutsch')
                driver.wait(label='Italiano')
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
        driver.press(label='Customize', role='button')
        driver.wait(label='Background music')
        parent = driver.find(label='Background music')[0]['parent']
        scroll = next(node for node in driver.tree() if node['index'] == parent)
        x, y = UiDriver.center(scroll)
        for _ in range(20):
            driver.pointer(x, y, wheel=-1)
        driver.release_pointer()
        driver.wait(label='Voice narration')
        driver.wait(label='Female voice', role='button')
        driver.wait(label='Male voice', role='button')
        driver.wait(label='English', role='dropdown')
        assert not visible_label('Plays in'), screen_text()
    finally:
        stop(process)
    # Uninstalling a downloaded practice asks once, then deletes the copy and
    # its narration.
    with sqlite3.connect(profile / 'inbe.db') as database:
        for key, value in {'exercise_type': 2, 'voice_narration_enabled': 0}.items():
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?',
                             (str(value), user, key))
    process, window = launch(profile, 'sun-delete', 1280, 900)
    try:
        open_manager()
        # Downloaded, Sun Salutation is under Installed; its row in Yoga has
        # the same button and question.
        assert 'Sun Salutation' in row_names(), row_names()
        select_tab('Yoga')
        text = row_text(manager_row('Sun'))
        assert 'Sun Salutation' in text and str(sun_mb) + 'MB' in text.replace(' ', ''), text
        act('Sun', 'Uninstall')
        row = manager_row('Sun')
        question = [node for node in row['nodes'] if node['label'].startswith('Uninstall Sun Salutation?')]
        assert question and 'Your progress stays.' in question[0]['label'], row_text(row)
        question = question[0]
        assert (cache / 'practice-sunsalutation.zib').exists()
        # Uninstall fills the right half under the question, beside Cancel;
        # the question starts where both buttons do.
        buttons = [node for node in row['nodes'] if node['kind'] == 'button']
        cancel = next(node for node in buttons if node['label'] == 'Cancel')
        confirm = buttons[buttons.index(cancel) + 1]
        assert confirm['label'] == 'Uninstall', buttons
        assert question['y'] < cancel['y'] and confirm['y'] == cancel['y'], (question, cancel, confirm)
        assert abs(confirm['width'] - cancel['width']) < 2 and confirm['x'] > cancel['x'] + cancel['width'] - 1, \
            (cancel, confirm)
        assert abs(question['x'] - cancel['x']) < 1, (question, cancel)
        assert abs(question['x'] + question['width'] - confirm['x'] - confirm['width']) < 2, (question, confirm)
        driver.press(key=confirm['key'])
        # The files are gone; the row still shows the download's size.
        wait_file(cache / 'practice-sunsalutation.zib', present=False)
        driver.wait_idle(frames=2)
        text = row_text(manager_row('Sun'))
        assert str(sun_mb) + 'MB' in text.replace(' ', ''), text
        assert not (cache / 'practice-sunsalutation.en.male.zib').exists()
        assert not (cache / 'practice-sunsalutation.removed').exists()
        # Its button installs again: Uninstall left the row.
        assert 'Uninstall' not in text and 'Install' in text, text
        # No longer on this device, it left Installed.
        select_tab('Installed')
        assert 'Sun Salutation' not in row_names(), row_names()
    finally:
        stop(process)
print('Private Practices modal: Installed, Meditation, Yoga and Martial arts tabs, '
      'one Install, Buy, Cancel or Uninstall button per practice, real sizes, '
      'reorder that Practice follows within a tab, removal that stays, '
      'restore without download, installed-only home, saved progress, owned Tai Chi without a price, '
      'narration languages, narrow layout, Sun Salutation narration and delete passed')
