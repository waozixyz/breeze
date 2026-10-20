"""Private-display regression of Practice's tabs and its download controls."""
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


# Practice's tabs, one for each kind of practice; breathing practices are
# under Meditation.
TABS = ['Meditation', 'Yoga', 'Martial arts', 'Workout']
RUSSIAN = ['Медитация', 'Йога', 'Боевые искусства', 'Тренировка']


def tab_nodes(labels=TABS):
    return [node for node in driver.tree() if node['role'] == 'tab' and node['label'] in labels]


def home_tabs(labels=TABS):
    """Practice's tabs in order, as label and whether it is selected."""
    return [(node['label'], node['selected']) for node in tab_nodes(labels)]


def selected_tab(labels=TABS):
    selected = [label for label, chosen in home_tabs(labels) if chosen]
    assert len(selected) == 1, home_tabs(labels)
    return selected[0]


def visible_tab(label, labels=TABS):
    tabs = [node for node in tab_nodes(labels) if node['label'] == label
            and node['visible'] and node['visible_width'] >= 24]
    return tabs[0] if tabs else None


def select_tab(label, labels=TABS):
    """Show one tab's practices."""
    tabs = [node for node in tab_nodes(labels) if node['label'] == label]
    assert tabs, f'No {label} tab: ' + screen_text()
    driver.press(key=tabs[0]['key'])
    driver.wait_idle(frames=3)
    assert selected_tab(labels) == label, home_tabs(labels)


def swipe_to_tab(label, labels=TABS):
    """Swipe the tabs toward their end until a tab shows; the swipe selects
    no tab."""
    before = selected_tab(labels)
    for _ in range(6):
        if visible_tab(label, labels):
            break
        bar = next(node for node in driver.tree() if node['kind'] == 'tab_bar' and
                   any(tab['parent'] == node['index'] for tab in tab_nodes(labels)))
        y = bar['visible_y'] + bar['visible_height'] / 2
        driver.drag((bar['visible_x'] + bar['visible_width'] - 8, y), (bar['visible_x'] + 8, y), steps=12)
        driver.wait_idle(frames=4)
    assert visible_tab(label, labels), (label, home_tabs(labels))
    chosen = [name for name, selected in home_tabs(labels) if selected]
    assert chosen in ([], [before]), ('A swipe selected a tab', home_tabs(labels))


def buttons(prefix):
    """The visible buttons whose label is `prefix` or starts with it and a
    size, such as "Install · 22 MB"."""
    return [node for node in driver.tree() if node['kind'] == 'button' and node['visible'] and
            (node['label'] == prefix or node['label'].startswith(prefix + ' · '))]


def press_button(prefix):
    found = buttons(prefix)
    assert found, f'No {prefix} button: ' + screen_text()
    driver.press(key=found[0]['key'])
    driver.wait_idle(frames=2)


def next_card():
    """Press the arrow after the "1 / 4" between a tab's practices."""
    nodes = driver.tree()
    pager = [node for node in nodes if node['visible'] and re.fullmatch(r'\d+ / \d+', node['label'] or '')]
    assert pager, 'No pager: ' + screen_text()
    middle = UiDriver.center(pager[0])[0]
    arrows = [node for node in nodes if node['kind'] == 'button' and node['visible'] and not node['label']
              and abs(UiDriver.center(node)[1] - UiDriver.center(pager[0])[1]) < 40
              and UiDriver.center(node)[0] > middle]
    assert arrows, 'No next arrow: ' + screen_text()
    driver.press(key=arrows[0]['key'])
    driver.wait_idle(frames=2)


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
    sizes = {name: (ROOT / 'build/practice-content' / (name + '.zib')).stat().st_size
             for name in ('whm', 'meditation', 'sunsalutation')}
    cache = profile / 'packages'
    sizes = {name: (ROOT / 'build/practice-content' / (name + '.zib')).stat().st_size
             for name in ('whm', 'sunsalutation')}
    sun_mb = (sizes['sunsalutation'] + 512 * 1024) // (1024 * 1024)
    # A practice that comes with the app stays ready even when an older
    # version took it off Practice.
    (cache / 'practice-whm.removed').write_text('1')
    process, window = launch(profile, 'tabs')
    try:
        # Practice opens on Wim Hof under Meditation; Manage practices is gone.
        driver.wait(label='Start Practice', role='button')
        assert home_tabs() == [(label, label == 'Meditation') for label in TABS], home_tabs()
        assert not visible_label('Manage practices'), screen_text()
        assert visible_label('Wim Hof'), screen_text()
        # Meditation pages through its four practices, all ready to start.
        driver.wait(label='1 / 4')
        for name in ('Steady Box Breath', 'Meditation', 'Astral Projection'):
            next_card()
            driver.wait(contains=name)
            assert buttons('Start Practice') and not buttons('Install'), (name, screen_text())
        # Yoga offers Sun Salutation to install, with its size, and no Start.
        select_tab('Yoga')
        driver.wait(contains='Sun Salutation')
        install = buttons('Install')
        assert install and str(sun_mb) + 'MB' in install[0]['label'].replace(' ', ''), screen_text()
        assert not buttons('Start Practice') and not buttons('Uninstall'), screen_text()
        # The 7-Minute Workout comes with the app.
        select_tab('Workout')
        driver.wait(contains='7-Minute Workout')
        assert buttons('Start Practice') and not buttons('Install'), screen_text()
        # A tab shows the practice it showed last.
        select_tab('Meditation')
        driver.wait(contains='Astral Projection')
        # Tai Chi is offered at its price where it can be bought.
        select_tab('Martial arts')
        driver.wait(contains='Tai Chi')
        assert buttons('Unlock') and not buttons('Start Practice'), screen_text()
    finally:
        stop(process)
    with sqlite3.connect(profile / 'inbe.db') as database:
        value = database.execute('SELECT value FROM settings WHERE user_id=? AND key=?',
                                 (user, 'tai_chi_progress')).fetchone()[0]
        assert value.startswith('1'), 'Browsing practices changed saved practice progress'
    # On a narrow phone the last tab lies past the edge in English and in
    # Russian: a swipe across the tabs brings it into view without choosing
    # a tab, and a tap chooses it.
    for language, width in [('en', 320), ('en', 360), ('ru', 320), ('ru', 360)]:
        with sqlite3.connect(profile / 'inbe.db') as database:
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?', (language, user, 'language'))
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?', ('0', user, 'exercise_type'))
        labels = TABS if language == 'en' else RUSSIAN
        process, window = launch(profile, 'swipe-' + language + '-' + str(width), width, 640)
        try:
            driver.wait(label=labels[0])
            assert selected_tab(labels) == labels[0], home_tabs(labels)
            swipe_to_tab(labels[-1], labels)
            select_tab(labels[-1], labels)
            driver.wait(contains='7-Minute Workout' if language == 'en' else '7-минутная тренировка')
        finally:
            stop(process)
    with sqlite3.connect(profile / 'inbe.db') as database:
        database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?', ('en', user, 'language'))
        for key, value in {'exercise_type': 4, 'voice_narration_enabled': 1}.items():
            database.execute('UPDATE settings SET value=? WHERE user_id=? AND key=?',
                             (str(value), user, key))
    shutil.copyfile(ROOT / 'build/practice-content/taichi.zib', cache / 'practice-taichi.zib')
    shutil.copyfile(ROOT / 'build/practice-content/taichi.en.zib', cache / 'practice-taichi.en.zib')
    shutil.copyfile(ROOT / 'build/practice-content/taichi.en.male.zib', cache / 'practice-taichi.en.male.zib')
    # A Tai Chi pack on the device without an account that bought it stays
    # locked: its card offers Unlock at its price.
    process, window = launch(profile, 'taichi-unowned', 1280, 900)
    try:
        driver.wait(contains='Tai Chi')
        assert selected_tab() == 'Martial arts', home_tabs()
        assert buttons('Unlock') and not buttons('Start Practice'), screen_text()
        assert 'Dew' in buttons('Unlock')[0]['label'], screen_text()
        assert not buttons('Uninstall'), screen_text()
    finally:
        stop(process)
    # The account's purchase, remembered on this device; sync stays off, so
    # nothing reaches a node.
    account = 'a' * 64
    with sqlite3.connect(profile / 'inbe.db') as database:
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
                                ('taichi-desktop', 1280, 900)]:
        process, window = launch(profile, name, width, height)
        try:
            # Bought and on this device, Tai Chi starts. No price is left, and
            # its card offers no Uninstall.
            driver.wait(label='Start Practice', role='button')
            driver.wait(contains='Tai Chi')
            assert not buttons('Uninstall'), screen_text()
            text = screen_text()
            assert 'Dew' not in text and 'Unlock' not in text, text
            if name == 'taichi-desktop':
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
print('Practice tabs: Meditation, Yoga, Martial arts and Workout listing every practice, '
      'shipped practices always ready, Install with real sizes, Unlock at its price, '
      'owned Tai Chi without a price, narration languages, swiping to the last tab in '
      'English and Russian, and no Uninstall on a downloaded card passed')
