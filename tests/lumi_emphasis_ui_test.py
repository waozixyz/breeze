"""Verify reply emphasis and suggestion feedback in an owned private-Xvfb app."""
import ast
from pathlib import Path
import sqlite3
import tempfile
import json

ROOT = Path(__file__).resolve().parents[1]
# Reuse the existing owned-window harness without running its full scenario.
source = ast.parse((ROOT / 'tests/lumi_ui_test.py').read_text())
source.body = [node for node in source.body
               if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef))]
exec(compile(source, str(ROOT / 'tests/lumi_ui_test.py'), 'exec'))
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
OUTPUT = ROOT / 'build/lumi-online-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='inbe-emphasis-') as directory:
    profile = Path(directory)
    with application(profile, 'emphasis-init', standalone=True):
        pass
    history = [
        dict(user=1, text='What can I do with Lumi?'),
        dict(user=0, text='You can **write in your Diary**, track __habits__, and start a breathing practice.\n\n**Try a small step today.**'),
        dict(user=0, text='**Bold emphasis wraps naturally** when a longer reply reaches the edge of the message.\n\nUnicode works too: **té · 水を飲む**.\nLiteral code stays literal: `**example**`.'),
    ]
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        settings = dict(enabled_apps='31', app_used_lists='1', app_used_lumi='1',
                        app_used_habits='1', app_used_practices='1', app_used_diary='1',
                        main_tab='4', language='en', language_setup_done='1', apps_setup_done='1',
                        lumi_introduced='1', cells_auto_update='0', tutorial_seen='1',
                        habits_guide_seen='1', lumi_archive_migrated='0', lumi_chat=json.dumps(history))
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user,key,value))
    with application(profile, 'emphasis') as window:
        assert all(any(row['text'] == seeded['text'] for row in chat(profile))
                   for seeded in history), 'Seeded emphasis replies were not loaded'
        capture(window, 'bold-replies')
        suggestion = 'Suggestion: add a weekly habit reminder'
        tap(window, 490, 676)
        command('xdotool', 'type', '--clearmodifiers', '--delay', '18', suggestion)
        command('xdotool', 'keydown', '--clearmodifiers', 'Return')
        time.sleep(0.15)
        command('xdotool', 'keyup', 'Return')
        wait_for(lambda: any(row.get('kind', 0) == 3 for row in chat(profile)),
                 'Feedback approval card was not saved')
        pending_sql = ("SELECT value FROM settings WHERE key LIKE 'cell.feedback.pending.%' "
                       "AND json_extract(value,'$.id') IS NOT NULL")
        assert query(profile, pending_sql) == [], 'Feedback queued before Yes approval'
        capture(window, 'suggestion-approval')
        tap_rendered_button(window, 'Yes')
        wait_for(lambda: len(query(profile, pending_sql)) == 1,
                 'Approved feedback was not saved in the outbox')
        reports = [json.loads(row[0]) for row in query(profile, pending_sql)]
        assert len(reports) == 1 and reports[0]['message'] == suggestion
        assert reports[0]['title'] == suggestion
        saved = 'Saved on this device, waiting to send to the developer inbox. Delivery needs an Inner Breeze account and internet access.'
        wait_for(lambda: chat(profile)[-1]['text'].strip() == saved,
                 'Lumi did not explain that delivery is still pending')
        capture(window, 'suggestion-feedback')
    with application(profile, 'emphasis-restart'):
        reports = [json.loads(row[0]) for row in query(profile, pending_sql)]
        assert len(reports) == 1 and reports[0]['message'] == suggestion
    print('Lumi emphasis and suggestion feedback: real UI, durable outbox and restart passed')
