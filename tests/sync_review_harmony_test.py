#!/usr/bin/env python3
"""Exercise the real review dialog through Harmony's private app host/transport."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
MCP_INPUT = os.environ.get('INBE_REVIEW_MCP_INPUT') == '1'
OUTPUT = Path(os.environ.get('INBE_REVIEW_TEST_OUTPUT',
              ROOT / ('build/sync-review-harmony-mcp-test' if MCP_INPUT
                      else 'build/sync-review-harmony-test'))).resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(os.environ['HARMONY_REVIEW_TEST_BUILD']).resolve()
HARMONY = Path(os.environ['HARMONY_TEST_ROOT']).resolve()
BINARY = Path(sys.argv.pop(1)).resolve()
assert BINARY.is_file(), BINARY
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
    assert not os.environ.get(key), 'Inherited desktop environment: ' + key

# Freeze only compiled artifacts. No source checkout or live state is copied.
for name in ('client/native_desktop', 'client/libapp-start.so',
             'desktop/desktop', 'bridge/bridge', 'fixture/embedded_app_fixture'):
    target = OUTPUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / name, target)
shutil.copy2(BINARY, OUTPUT / 'inbe')
os.environ['APP_CONTROL_BUILD'] = str(OUTPUT)
sys.path.insert(0, str(HARMONY / 'tests'))
sys.path.insert(0, str(HARMONY))
from app_control_test import AppControlTest


class ReviewHostTest(AppControlTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        wrapper = cls.projects / 'waozixyz/inbe/build/bin/linux/inbe-linux-x86_64'
        wrapper.write_text('#!/bin/sh\nexport APP_SHOT_WINDOW=1\nexec ' +
            shlex.quote(str(OUTPUT / 'inbe')) + ' --screenshot ' +
            shlex.quote(str(OUTPUT / 'fixture.png')) +
            ' --screenshot-scene sync_review --screenshot-width 900' +
            ' --screenshot-height 720 --screenshot-dark 0\n')
        wrapper.chmod(0o700)

    def xdo(self, *args):
        result = subprocess.run(['xdotool', *map(str, args)], env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def count(self, db, sql):
        # Keep a read-only observer for the child lifetime. The test must not
        # create databases or trigger WAL cleanup between the app's writes.
        if db not in self.readers:
            connection = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=3)
            self.readers[db] = connection
            self.addCleanup(connection.close)
        return self.readers[db].execute(sql).fetchone()[0]

    def click_at(self, window, x, y):
        if MCP_INPUT:
            self.require('click', 'inbe', x=int(x), y=int(y))
        else:
            self.xdo('windowfocus', '--sync', window)
            self.xdo('mousemove', '--window', window, int(x), int(y),
                     'sleep', '.1', 'mousedown', '1', 'sleep', '.25', 'mouseup', '1')
        time.sleep(.25)

    def scroll_at(self, window, x, y):
        if MCP_INPUT:
            self.require('scroll', 'inbe', x=int(x), y=int(y), delta=-3)
        else:
            self.xdo('mousemove', '--window', window, int(x), int(y),
                     'click', '--repeat', '3', '5')

    def test_review_choices_inside_harmony(self):
        self.readers = {}
        host = int(self.xdo('search', '--onlyvisible', '--pid', self.client.pid).splitlines()[0])
        foreign_pid = self.foreign.pid
        results = []
        for choice, width, height in [('merge', 960, 900), ('replace', 411, 877), ('keep', 960, 900)]:
            self.xdo('windowsize', '--sync', host, width, height)
            time.sleep(.3)
            self.require('open', 'inbe')
            state = self.ready('inbe')
            window = int(state['window'])
            pid = int(self.xdo('getwindowpid', window))
            self.assertNotEqual(pid, foreign_pid)
            self.assertEqual(Path(f'/proc/{pid}/exe').resolve(), OUTPUT / 'inbe')
            def stop_owned(pid=pid):
                try:
                    if Path(f'/proc/{pid}/exe').resolve() == OUTPUT / 'inbe':
                        os.kill(pid, signal.SIGTERM)
                        deadline = time.monotonic() + 3
                        while time.monotonic() < deadline:
                            if not Path(f'/proc/{pid}/exe').exists():
                                return
                            time.sleep(.05)
                        if Path(f'/proc/{pid}/exe').resolve() == OUTPUT / 'inbe':
                            os.kill(pid, signal.SIGKILL)
                except FileNotFoundError:
                    pass
            self.addCleanup(stop_owned)
            db = Path('/tmp') / f'inbe-screenshot-{pid}' / 'inbe.db'
            def fixture_ready():
                if not db.is_file():
                    return False
                try:
                    return self.count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'") == 1
                except sqlite3.Error:
                    return False
            self.wait_until(fixture_ready, 'Review fixture did not become ready')
            time.sleep(.5)
            state = self.state('inbe')
            self.xdo('windowfocus', '--sync', window)
            content_width = int(state['content_width'])
            content_height = int(state['content_height'])
            self.assertEqual(content_width, width)
            self.assertEqual(content_height, height - 64)
            panel_height = min(content_height - 32, 720)
            panel_top = (content_height - panel_height) // 2
            content_top = panel_top + 56
            pending = self.count(db, 'SELECT COUNT(*) FROM sync_outbox')
            # Empty modal header space must not lend input to the page below.
            # Clicking the backdrop intentionally dismisses this dialog.
            header_x, header_y = content_width // 2, panel_top + 30
            self.click_at(window, header_x, header_y)
            self.scroll_at(window, header_x, header_y)
            self.xdo('mousemove', '--window', window, header_x, header_y,
                     'mousedown', '1', 'mousemove', '--window', window,
                     header_x + 40, header_y,
                     'sleep', '.15', 'mouseup', '1')
            time.sleep(.3)
            self.assertEqual(self.count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'"), '1')
            self.assertEqual(self.count(db, 'SELECT COUNT(*) FROM sync_outbox'), pending)
            if choice == 'keep':
                self.click_at(window, content_width // 2, content_top + 44 + 19)
            elif choice == 'replace':
                self.click_at(window, content_width // 2, content_top + 88 + 19)
            capture = self.require('screenshot', 'inbe')
            shutil.copy2(capture['path'], OUTPUT / f'{choice}-embedded.png')
            if choice == 'merge':
                self.scroll_at(window, content_width // 2, content_top + 260)
                self.assertEqual(self.count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'"), '1')
            footer = panel_top + panel_height - 18 - 40 + 19
            self.click_at(window, content_width // 2, footer)
            capture = self.require('screenshot', 'inbe')
            shutil.copy2(capture['path'], OUTPUT / f'{choice}-after-apply.png')
            paths = []
            for fd in Path(f'/proc/{pid}/fd').iterdir():
                try:
                    target = str(fd.resolve())
                    if 'inbe-screenshot-' in target:
                        paths.append(target)
                except FileNotFoundError:
                    pass
            (OUTPUT / f'{choice}-storage-observation.json').write_text(json.dumps({
                'database': str(db), 'open_fixture_files': paths,
                'pending': self.count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'"),
                'local': self.count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'"),
                'remote': self.count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'")}, indent=2) + '\n')
            self.wait_until(lambda: self.count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'") != '1',
                            f'{choice}: Apply did not resolve the review')
            self.assertEqual(self.count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'"),
                             0 if choice == 'replace' else 1)
            self.assertEqual(self.count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'") > 0,
                             choice != 'keep')
            if choice != 'replace':
                self.assertEqual(self.count(db, 'SELECT COUNT(*) FROM sync_outbox'), pending)
            self.assertIsNone(self.foreign.poll(), 'Foreign fixture must remain untouched')
            results.append({'choice': choice, 'width': content_width, 'height': content_height,
                            'ready': True, 'data_outcome_verified': True})
            # Only this test's owned child is terminated; the host stays alive.
            stop_owned()
            self.wait_until(lambda: not self.state('inbe')['running'], 'Owned fixture did not exit')
            self.readers.pop(db).close()
            self.assertEqual(self.count(db, "SELECT value FROM meta WHERE key='sync_pending_review_pending'"), '')
            self.assertEqual(self.count(db, "SELECT COUNT(*) FROM habits WHERE id='local-review-walk'"),
                             0 if choice == 'replace' else 1)
            self.assertEqual(self.count(db, "SELECT COUNT(*) FROM habits WHERE id<>'local-review-walk'") > 0,
                             choice != 'keep')
            self.readers.pop(db).close()
            shutil.rmtree(db.parent)
        (OUTPUT / 'review-results.json').write_text(json.dumps({
            'inbe_sha256': hashlib.sha256((OUTPUT / 'inbe').read_bytes()).hexdigest(),
            'host_sha256': hashlib.sha256((OUTPUT / 'client/native_desktop').read_bytes()).hexdigest(),
            'choices': results, 'private_display': True,
            'input_source': 'MCP app_control' if MCP_INPUT else 'held pointer events on the exact owned child window',
            'deployed': False}, indent=2) + '\n')
        print('PASS: real Inner Breeze review inside Harmony, desktop/narrow choices, modal input isolation and data outcomes')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([ReviewHostTest('test_review_choices_inside_harmony')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
