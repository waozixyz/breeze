"""A nested game in Breeze reads the account's single canonical campaign."""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'shovey/tests'))
from inbe_apps import open_arcade

assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 400
assert os.environ['YUE_DESKTOP_RECOVERY'] == '0'
root = Path(__file__).resolve().parents[1]
binary, bundle = map(lambda value: Path(value).resolve(), sys.argv[1:3])
output = root / 'build/shared-progress-ui-test'
output.mkdir(parents=True, exist_ok=True)
driver = UiDriver(output / 'driver')
key = 'entity.game-progress.fd65a3d7ac3d5ceb2d4d96cc5224a740'

with tempfile.TemporaryDirectory(prefix='breeze-account-progress-') as directory:
    profile = Path(directory)

    @contextlib.contextmanager
    def application(name):
        log_path = output / (name + '.log')
        with log_path.open('w') as log:
            child = subprocess.Popen([str(binary)], cwd=root,
                                     env=os.environ | driver.environment() | {'APP_DATA_ROOT': str(profile), 'INBE_NODE_APP_FILE': str(bundle)},
                                     stdout=log, stderr=subprocess.STDOUT)
            driver.attach(child, log_path)
            try:
                driver.tree()
                yield child
            finally:
                if child.poll() is None:
                    child.terminate()
                child.wait(timeout=10)

    with application('initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = dict(language='en', language_system=0, language_setup_done=1, apps_setup_done=1,
                        tutorial_seen=1, habits_guide_seen=1, launcher_guide_seen=1, lumi_guides_seen=127,
                        app_used_practices=1, package_updates_allowed=0, sync_enabled=0,
                        apps_last_update_check=1900000000, node_apps_checked_at=int(time.time()),
                        navigation_placement=2, node_apps_offers='arcade|Arcade\n', node_app_slot_0='arcade', app_used_arcade=1)
        settings[key] = json.dumps(dict(game='shovey.classic', unlocked=40, completed='1' * 39))
        for name, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, name, str(value)))
    for attempt in ('first', 'restart'):
        with application(attempt):
            driver.wait(label='Apps', role='button')
            open_arcade(driver)
            driver.press(label='Play', role='button')
            deadline = time.monotonic() + 40
            while not driver.find(contains='Level 40 / ', role='text'):
                if driver.find(label='Download new levels when they come out?', role='text'):
                    driver.press(label='Not now', role='button')
                assert time.monotonic() < deadline, driver.text()
                time.sleep(.05)
            driver.wait_idle(frames=5)
            with sqlite3.connect((profile / 'inbe.db').as_uri() + '?mode=ro', uri=True) as db:
                record = json.loads(db.execute('SELECT value FROM settings WHERE user_id=? AND key=?', (user, key)).fetchone()[0])
                assert record['unlocked'] == 40 and record['completed'] == '1' * 39, record
                assert 'state' not in record, record
                assert db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'entity.game-progress.%'").fetchone()[0] == 1
                assert db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'local.%.campaign' AND value<>''").fetchone()[0] == 1

    # Account hydration can finish after the child has opened its first board.
    # Start with no campaign, then deliver exactly the same account record.
    with sqlite3.connect(profile / 'inbe.db') as db:
        db.execute("DELETE FROM settings WHERE key=? OR key LIKE 'local.%.campaign'", (key,))
    for attempt in ('late-progress', 'late-restart'):
        with application(attempt):
            driver.wait(label='Apps', role='button')
            open_arcade(driver)
            driver.press(label='Play', role='button')
            if attempt == 'late-progress':
                driver.wait(contains='Level 1 / ', role='text', timeout=40)
                with sqlite3.connect(profile / 'inbe.db') as db:
                    db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1)',
                               (user, key, json.dumps(dict(game='shovey.classic', unlocked=40, completed='1' * 39))))
            driver.wait(contains='Level 40 / ', role='text', timeout=40)
print('Breeze nested Shovey restores level 40 before and after late account hydration and cold restart; '
      'only unlocks sync and the campaign stays on-device')
