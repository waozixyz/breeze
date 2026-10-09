#!/usr/bin/env python3
"""Exercise the review choices using isolated encrypted screenshot fixtures."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from PIL import Image

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

readers = {}

def count(db, sql):
    # Observe the live fixture through one read-only connection. Reopening a
    # writer between frames can trigger WAL cleanup while the app is writing.
    if db not in readers:
        readers[db] = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=3)
    return readers[db].execute(sql).fetchone()[0]

for choice, width, height, dark in [('merge', 900, 720, 0), ('replace', 411, 813, 0),
                                  ('keep', 900, 720, 0), ('merge', 900, 720, 1)]:
    case = choice + ('-dark' if dark else '')
    initial = output / (case + '-initial.png')
    logfile = output / (case + '.log')
    env = os.environ.copy()
    env.update(APP_SHOT_WINDOW='1', APP_NO_TRAY='1', SDL_VIDEODRIVER='x11', YUE_DESKTOP_RECOVERY='0', LIBGL_ALWAYS_SOFTWARE='1')
    with logfile.open('w') as log:
        app = subprocess.Popen([str(binary), '--screenshot', str(initial),
            '--screenshot-scene', 'sync_review', '--screenshot-width', str(width),
            '--screenshot-height', str(height), '--screenshot-theme', '0',
            '--screenshot-dark', str(dark)],
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
            assert count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'") == 1
            assert count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'") == 0
            # The frame uses a 32-unit viewport margin and a 720-unit max height.
            panel_top = (height - min(height - 32, 720)) // 2
            content_top = panel_top + 56
            command('import', '-window', window, str(initial))
            footer_start = panel_top + min(height - 32, 720) - 18 - 132
            panel_width = min(width - 32, 680)
            body = Image.open(initial).convert('RGB').crop((
                (width - panel_width) // 2 + 18, content_top,
                (width + panel_width) // 2 - 18, footer_start - 8))
            # tobytes() works on every Pillow release; CI's Pillow predates
            # get_flattened_data().
            raw = body.tobytes()
            palette = [tuple(raw[index:index + 3]) for index in range(0, len(raw), 3)]
            expected_colors = ([(134, 220, 165), (255, 163, 163), (255, 212, 119)] if dark
                               else [(23, 102, 58), (179, 38, 30), (128, 80, 0)])
            for color in expected_colors:
                matching = sum(all(abs(a - b) <= 20 for a, b in zip(pixel, color))
                               for pixel in palette)
                assert matching > 5, ('missing change color', choice, color)
            # The long hierarchy scrolls inside the modal, without dismissing it.
            if choice == 'merge':
                start = content_top + 140
                command('xdotool', 'mousemove', '--window', window, str(width // 2), str(start + 130),
                    'mousedown', '1', 'sleep', '0.1',
                    'mousemove', '--window', window, str(width // 2), str(start),
                    'sleep', '0.15', 'mouseup', '1')
                time.sleep(0.4)
                assert count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") == '1'
                scrolled = output / (case + '-scrolled.png')
                command('import', '-window', window, str(scrolled))
                after = Image.open(scrolled).convert('RGB')
                assert after.crop((0, content_top, width, footer_start - 8)).tobytes() != (
                    Image.open(initial).convert('RGB').crop((0, content_top, width, footer_start - 8)).tobytes()
                ), 'review text did not scroll'
                assert after.crop((0, footer_start, width, height)).tobytes() == (
                    Image.open(initial).convert('RGB').crop((0, footer_start, width, height)).tobytes()
                ), 'action buttons moved with the scrolling text'
            footer = panel_top + min(height - 32, 720) - 18 - 132 + 19
            action_index = {'merge': 0, 'keep': 1, 'replace': 2}[choice]
            pending_before = count(db, 'SELECT COUNT(*) FROM sync_outbox')
            click(window, width // 2, footer + action_index * 44)
            time.sleep(0.5)
            local = count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'")
            remote = count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'")
            assert local == (0 if choice == 'replace' else 1), (choice, 'local', local)
            assert (remote > 0) == (choice != 'keep'), (choice, 'remote', remote)
            if choice == 'keep':
                assert count(db, 'SELECT COUNT(*) FROM sync_outbox') == pending_before
            assert count(db, "SELECT json_extract(json,'$.friends[0].alias') FROM social_snapshots WHERE kind='friends.list'") == (
                'Alice' if choice == 'keep' else 'Alicia')
            assert count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") != '1'
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
            if db in readers:
                readers.pop(db).close()
            shutil.rmtree(db.parent)
    assert 'APP: frame rejected with status' not in logfile.read_text()
# A persisted review whose merge has no visible changes must resolve before
# rendering a dialog, including when screenshot setup explicitly opened one.
env = os.environ.copy()
env.update(APP_SHOT_WINDOW='1', APP_NO_TRAY='1', SDL_VIDEODRIVER='x11',
           YUE_DESKTOP_RECOVERY='0', LIBGL_ALWAYS_SOFTWARE='1')
with (output / 'no-changes.log').open('w') as log:
    app = subprocess.Popen([str(binary), '--screenshot', str(output / 'no-changes-initial.png'),
        '--screenshot-scene', 'sync_review_no_changes', '--screenshot-width', '900',
        '--screenshot-height', '720', '--screenshot-dark', '0'],
        cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        db = Path('/tmp') / ('inbe-screenshot-' + str(app.pid)) / 'inbe.db'
        deadline = time.monotonic() + 30
        resolved = False
        while time.monotonic() < deadline:
            assert app.poll() is None, 'no-changes fixture exited'
            if db.is_file():
                try:
                    resolved = count(db, "SELECT COALESCE((SELECT CAST(value AS INTEGER) FROM meta WHERE key='sync_last_server_version'),0)") == 24
                except sqlite3.Error:
                    pass
            if resolved:
                break
            time.sleep(0.1)
        assert resolved, 'no-changes review did not resolve automatically'
        assert count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") != '1'
        assert count(db, 'SELECT COUNT(*) FROM sync_outbox') > 0
        assert count(db, 'SELECT COUNT(*) FROM habits') > 0
        window = command('xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)).splitlines()[0]
        command('import', '-window', window, str(output / 'no-changes.png'))
    finally:
        app.terminate()
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=5)
        if db in readers:
            readers.pop(db).close()
        shutil.rmtree(db.parent)
print('PASS: desktop merge/keep, narrow replacement, direct footer actions, colored changes, modal scrolling, encrypted data outcomes, pending-upload preservation, no-changes review automatically resolved')
