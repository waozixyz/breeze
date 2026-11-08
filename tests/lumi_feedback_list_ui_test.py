"""Real native list -> tool -> preview -> one consent, using a local provider.

No Send button is pressed and no real developer feedback is queued or sent.
"""
import http.server
import json
from pathlib import Path
import sqlite3
import tempfile
import threading

import lumi_harness_ui_test as h
from ui_driver import UiDriver

h.OUTPUT = h.ROOT / 'build/lumi-feedback-list-ui-test'
h.OUTPUT.mkdir(parents=True, exist_ok=True)
h.driver = UiDriver(h.OUTPUT / 'driver')
fixture = json.loads((h.ROOT / 'tests/lumi_feedback_list_fixture.json').read_text())


class Provider(http.server.BaseHTTPRequestHandler):
    requests = []
    largest_response = 0

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        assert body['max_tokens'] == 32768, 'Report output budget too small'
        context = json.loads(body['messages'][0]['content'].split('Current app context:\n', 1)[1])
        target = next(row for row in context['lists'] if row['title'] == 'Apps')
        assert context['feedback_list_required'] and context['feedback_list_id'] == target['id']
        reads = [json.loads(row['content']) for row in body['messages'] if row['role'] == 'tool']
        if not reads:
            calls = [('read-apps', 'read_list', dict(list_id=target['id']))]
        else:
            saved = reads[-1]
            assert [row['title'] for row in saved['items']] == fixture['originals']
            # Exercise double JSON escaping above the former 65KiB response
            # cap, while each point and the complete message stay in contract.
            points = [dict(item_id=row['item_id'], message=message + '\n' +
                           '"' * (4095 - len(message.encode())))
                      for row, message in zip(saved['items'], fixture['expansions'])]
            report = dict(title='Apps feedback', source_list_id=target['id'], points=points)
            calls = [('proposal-1', 'report_feedback', report),
                     ('proposal-retry-2', 'report_feedback', report),
                     ('proposal-stale-3', 'report_feedback',
                      dict(title='Leaderboard scores', message='Fix leaderboard scores'))]
        message = dict(role='assistant', content=None, tool_calls=[
            dict(id=identifier, type='function', function=dict(name=name, arguments=json.dumps(args)))
            for identifier, name, args in calls])
        answer = json.dumps(dict(choices=[dict(message=message)])).encode()
        Provider.largest_response = max(Provider.largest_response, len(answer))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)


def cards(profile):
    return [row for row in h.chat(profile) if row.get('kind') == 3]


def assert_no_outbox(profile):
    with sqlite3.connect(profile / 'inbe.db') as db:
        assert not db.execute("SELECT key FROM settings WHERE key LIKE 'cell.feedback.pending.%'").fetchall()


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Provider)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with tempfile.TemporaryDirectory(prefix='profile-', dir=h.OUTPUT) as directory:
        profile = Path(directory)
        with h.application(profile, (900, 720, 10), 'initialize'):
            pass
        url = f'http://127.0.0.1:{server.server_port}/v1'
        h.seed(profile, dict(enabled_apps=31, app_used_lists=1, app_used_lumi=1,
                            main_tab=4, language='en', language_setup_done=1, apps_setup_done=1,
                            lumi_introduced=1, package_updates_allowed=0, tutorial_seen=1,
                            lumi_guides_seen=127, ui_scale=10, navigation_placement=0,
                            elist_initialized=1, lumi_online=1, lumi_provider='own',
                            lumi_provider_url=url, lumi_provider_model='local-fixture',
                            lumi_provider_agreement=f'1 {url}'))
        with sqlite3.connect(profile / 'inbe.db') as db:
            user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
            db.execute('DELETE FROM elist_items')
            db.execute('DELETE FROM elist_lists')
            for order, title in enumerate(('Scores', 'Apps')):
                db.execute('INSERT INTO elist_lists(id,user_id,title,sort_order,deleted_at,updated_at) VALUES(?,?,?,?,0,1)',
                           (title.lower(), user, title, order))
            for index in range(10):
                db.execute("INSERT INTO elist_items(id,user_id,list_id,title,comment,done,sort_order,deleted_at,updated_at) "
                           "VALUES(?,?,'scores','Leaderboard scores are wrong','',0,?,0,1)",
                           (f'score-{index}', user, index))
            for index, title in enumerate(fixture['originals']):
                db.execute("INSERT INTO elist_items(id,user_id,list_id,title,comment,done,sort_order,deleted_at,updated_at) "
                           "VALUES(?,?,'apps',?,'',0,?,0,1)", (f'issue-{index}', user, title, index))
            stale = dict(time=1, user=0, kind=0, text='Earlier report: leaderboard score is incorrect', payload='')
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,'cell.lumi.message.stale-score',?,1)",
                       (user, json.dumps(stale)))
        with h.application(profile, (900, 720, 10), 'list-report'):
            if h.terms_open():
                h.driver.press(label='Agree and go online', role='button')
            before_rows = h.chat(profile)
            h.driver.press(role='text_area')
            h.driver.type(fixture['request'])
            h.driver.key('enter')
            h.wait_for(lambda: len(cards(profile)) == 1, 'No single source-backed confirmation', 30)
            assert len(Provider.requests) == 2, 'Report did not read the list before proposing'
            assert Provider.largest_response > 65536, 'Large escaped provider response was not exercised'
            rows = h.chat(profile)
            added = rows[len(before_rows):]
            assert added[0]['user'] and added[0]['text'] == fixture['request']
            preview_rows = [row for row in added[1:] if not row['user'] and row['kind'] == 0]
            preview = ''.join(row['text'] for row in preview_rows)
            for original, expansion in zip(fixture['originals'], fixture['expansions']):
                assert original in preview and expansion in preview
            assert 'leaderboard' not in preview.lower(), preview
            assert rows[-1]['kind'] == 3
            with sqlite3.connect(profile / 'inbe.db') as db:
                draft = json.loads(db.execute('SELECT value FROM settings WHERE key=?',
                    ('cell.feedback.draft.' + rows[-1]['payload'],)).fetchone()[0])
            assert preview == draft['title'] + '\n\n' + draft['message'], 'Preview differs from consent-bound report'
            assert len(draft['message'].encode()) > 24000
            h.driver.wait(label='Send', role='button', enabled=True)
            # Read all proposal bubbles in the actual rendered tree while scrolling.
            observed = set()
            for _ in range(250):
                observed.update(h.driver.labels())
                if all(row['text'] in observed for row in preview_rows):
                    break
                h.driver.pointer(450, 280, wheel=3)
                h.driver.wait_idle(frames=3)
            missing = [dict(index=index, size=len(row['text']), prefix=row['text'][:60], suffix=row['text'][-30:])
                       for index, row in enumerate(preview_rows) if row['text'] not in observed]
            if missing:
                (h.OUTPUT / 'missing-chunks.json').write_text(json.dumps(missing, indent=2))
            assert not missing, f'A report chunk was not rendered: {[row["index"] for row in missing]}'
            assert len(cards(profile)) == 1
            assert_no_outbox(profile)
        with h.application(profile, (900, 720, 10), 'reopen'):
            assert len(cards(profile)) == 1, 'Reopen duplicated the consent'
            assert_no_outbox(profile)
            h.driver.wait(label='Cancel', role='button', enabled=True)
            h.driver.press(label='Cancel', role='button', enabled=True)
            h.driver.wait_idle(frames=4)
            assert not h.driver.find(label='Cancel', role='button', enabled=True, visible=True)
            assert len(cards(profile)) == 1
            assert_no_outbox(profile)
            previous_id = cards(profile)[0]['payload']
            h.driver.press(role='text_area')
            h.driver.type(fixture['request'])
            h.driver.key('enter')
            h.wait_for(lambda: len(cards(profile)) == 2, 'New identical message did not get its own proposal', 30)
            assert cards(profile)[-1]['payload'] != previous_id
            assert len(Provider.requests) == 4, 'Repeated wording did not read the actual list again'
            h.driver.press(label='Cancel', role='button', enabled=True)
            h.driver.wait_idle(frames=4)
            assert not h.driver.find(label='Cancel', role='button', enabled=True, visible=True)
            assert_no_outbox(profile)
finally:
    server.shutdown()
    thread.join(timeout=5)
print('Lumi native list feedback: all six original issues and expansions rendered before one consent; '
      'varied tool IDs, stale history, scrolling, reopen and Cancel passed; no feedback sent')
