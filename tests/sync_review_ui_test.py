#!/usr/bin/env python3
"""Exercise the review choices using isolated encrypted screenshot fixtures."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

assert os.environ.get('INBE_REVIEW_PRIVATE_DISPLAY') == '1', 'run inside a private Xvfb display'
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / 'build/sync-review-ui-test'
output.mkdir(parents=True, exist_ok=True)

def command(*args):
    return subprocess.check_output(args, text=True).strip()

def click(window, x, y):
    command('xdotool', 'mousemove', '--window', window, str(x), str(y),
            'mousedown', '1', 'sleep', '0.1', 'mouseup', '1')
    time.sleep(0.3)

def count(db, sql):
    with sqlite3.connect(db, timeout=3) as connection:
        return connection.execute(sql).fetchone()[0]

for choice, width, height in [('merge', 900, 720), ('replace', 411, 813), ('keep', 900, 720)]:
    initial = output / (choice + '-initial.png')
    logfile = output / (choice + '.log')
    env = os.environ.copy()
    env.update(APP_SHOT_WINDOW='1', APP_NO_TRAY='1', SDL_VIDEODRIVER='x11', YUE_DESKTOP_RECOVERY='0', LIBGL_ALWAYS_SOFTWARE='1')
    with logfile.open('w') as log:
        app = subprocess.Popen([str(binary), '--screenshot', str(initial),
            '--screenshot-scene', 'sync_review', '--screenshot-width', str(width),
            '--screenshot-height', str(height), '--screenshot-dark', '0'],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            db = Path('/tmp') / ('inbe-screenshot-' + str(app.pid)) / 'inbe.db'
            deadline = time.monotonic() + 30
            window = ''
            while time.monotonic() < deadline:
                if app.poll() is not None:
                    raise AssertionError('fixture exited: ' + logfile.read_text()[-2000:])
                result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                    capture_output=True, text=True)
                if result.returncode == 0 and db.is_file():
                    try:
                        ready = count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'") == 1
                    except sqlite3.Error:
                        ready = False
                    if ready:
                        window = result.stdout.splitlines()[0]
                        break
                time.sleep(0.1)
            assert window, 'fixture did not become ready'
            command('xdotool', 'windowfocus', '--sync', window)
            time.sleep(0.5)
            command('import', '-window', window, str(initial))
            assert count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'") == 1
            assert count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'") == 0
            # The frame uses a 32-unit viewport margin and a 720-unit max height.
            panel_top = (height - min(height - 32, 720)) // 2
            content_top = panel_top + 56
            if choice == 'keep':
                click(window, width // 2, content_top + 44 + 19)
            elif choice == 'replace':
                click(window, width // 2, content_top + 88 + 19)
            command('import', '-window', window, str(output / (choice + '-selected.png')))
            # The long hierarchy scrolls inside the modal, without dismissing it.
            if choice == 'merge':
                start = content_top + 210
                command('xdotool', 'mousemove', '--window', window, str(width // 2), str(start + 130),
                    'mousedown', '1', 'mousemove', '--window', window, str(width // 2), str(start),
                    'sleep', '0.15', 'mouseup', '1')
                time.sleep(0.4)
                assert count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") == '1'
                command('import', '-window', window, str(output / 'merge-scrolled.png'))
            footer = panel_top + min(height - 32, 720) - 18 - 40 + 19
            pending_before = count(db, 'SELECT COUNT(*) FROM sync_outbox')
            click(window, width // 2, footer)
            time.sleep(0.5)
            local = count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'")
            remote = count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'")
            assert local == (0 if choice == 'replace' else 1), (choice, 'local', local)
            assert (remote > 0) == (choice != 'keep'), (choice, 'remote', remote)
            if choice == 'keep':
                assert count(db, 'SELECT COUNT(*) FROM sync_outbox') == pending_before
            assert count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") != '1'
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
    assert 'APP: frame rejected with status' not in logfile.read_text()
print('PASS: desktop merge/keep, narrow replacement, modal scrolling, encrypted data outcomes, pending-upload preservation')
