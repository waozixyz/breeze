"""Verify reply emphasis and suggestion feedback in an owned private-Xvfb app."""
import ast
from pathlib import Path
import sqlite3
import tempfile
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
# Reuse the existing owned-window harness without running its full scenario.
source = ast.parse((ROOT / 'tests/lumi_ui_test.py').read_text())
source.body = [node for node in source.body
               if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef))]
exec(compile(source, str(ROOT / 'tests/lumi_ui_test.py'), 'exec'))
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
OUTPUT = ROOT / 'build/lumi-online-test'
OUTPUT.mkdir(parents=True, exist_ok=True)


def stroke_width(image, node, screen):
    """How wide the vertical strokes of a text's last line are, in pixels:
    the mean length of the ink runs along its rows. Bold text has wider
    strokes than regular text of the same size."""
    scale = image.width / screen['width']
    left = round((node['x'] - screen['x']) * scale)
    top = round((node['y'] - screen['y']) * scale)
    crop = image.crop((left, top, left + round(node['width'] * scale),
                       top + round(node['height'] * scale))).convert('L')
    histogram = crop.histogram()
    background = max(range(256), key=lambda value: histogram[value])
    pixels = crop.load()
    ink_rows = [y for y in range(crop.height)
                if any(abs(pixels[x, y] - background) > 60 for x in range(crop.width))]
    assert ink_rows, f"No text is drawn for {node['label']!r}"
    # The last line is the last run of rows with ink.
    bottom = ink_rows[-1]
    first = bottom
    while first - 1 in ink_rows:
        first -= 1
    runs = []
    for y in range(first, bottom + 1):
        run = 0
        for x in range(crop.width):
            if abs(pixels[x, y] - background) > 60:
                run += 1
            elif run:
                runs.append(run)
                run = 0
        if run:
            runs.append(run)
    return sum(runs) / len(runs)


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
                        lumi_introduced='1', package_updates_allowed='0', tutorial_seen='1',
                        habits_guide_seen='1', lumi_guides_seen='127', lumi_archive_migrated='0', lumi_chat=json.dumps(history),
                        # Switched offline, Lumi opens on its chat rather than its terms.
                        lumi_online='0')
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user,key,value))
    with application(profile, 'emphasis') as window:
        assert all(any(row['text'] == seeded['text'] for row in chat(profile))
                   for seeded in history), 'Seeded emphasis replies were not loaded'
        # Lumi shows the replies without their emphasis marks, except in code.
        bold_reply = driver.wait(contains='Try a small step today.', role='text')
        plain_reply = driver.wait(contains='Literal code stays literal', role='text')
        assert bold_reply['label'] == ('You can write in your Diary, track habits, and start a '
                                       'breathing practice.\n\nTry a small step today.'), bold_reply['label']
        assert plain_reply['label'].endswith('Literal code stays literal: `**example**`.'), plain_reply['label']
        assert 'Unicode works too: té · 水を飲む.' in plain_reply['label'], plain_reply['label']
        # The one pixel check: the emphasised line is really drawn bold,
        # with wider strokes than the plain line in the same font.
        driver.wait_idle(frames=3)
        screen = driver.wait(role='screen')
        capture_path = OUTPUT / 'bold-replies.png'
        command('import', '-window', window, str(capture_path))
        with Image.open(capture_path) as image:
            image = image.convert('RGB')
            bold = stroke_width(image, bold_reply, screen)
            plain = stroke_width(image, plain_reply, screen)
        assert bold > plain * 1.25, f'Emphasis is not drawn bold: strokes {bold:.2f} vs {plain:.2f} px'
        # A failure keeps the capture to look at; a pass leaves none behind.
        capture_path.unlink()
        suggestion = 'Suggestion: add a weekly habit reminder'
        start_draft(suggestion)
        driver.key('enter')
        wait_for(lambda: any(row.get('kind', 0) == 3 for row in chat(profile)),
                 'Feedback approval card was not saved')
        pending_sql = ("SELECT value FROM settings WHERE key LIKE 'cell.feedback.pending.%' "
                       "AND json_extract(value,'$.id') IS NOT NULL")
        assert query(profile, pending_sql) == [], 'Feedback queued before Yes approval'

        def card_answer(label):
            """The approval card's answer button, whatever its label's spacing."""
            return [node for node in driver.find(role='button', visible=True, enabled=True)
                    if node['label'].strip() == label]

        wait_for(lambda: card_answer('Yes'), 'The feedback card offers no Yes')
        driver.press(key=card_answer('Yes')[0]['key'])
        wait_for(lambda: len(query(profile, pending_sql)) == 1,
                 'Approved feedback was not saved in the outbox')
        reports = [json.loads(row[0]) for row in query(profile, pending_sql)]
        assert len(reports) == 1 and reports[0]['message'] == suggestion
        assert reports[0]['title'] == suggestion
        # Answered, the card offers neither answer again.
        wait_for(lambda: not card_answer('Yes') and not card_answer('No'),
                 'The answered feedback card still offers Yes or No')
        # The confirmation card stays the whole exchange: Yes adds no message.
        time.sleep(1.0)
        assert chat(profile)[-1].get('kind', 0) == 3, 'A message followed the feedback card: %r' % chat(profile)[-2:]
    with application(profile, 'emphasis-restart'):
        reports = [json.loads(row[0]) for row in query(profile, pending_sql)]
        assert len(reports) == 1 and reports[0]['message'] == suggestion
    print('Lumi emphasis and suggestion feedback: real UI, bold strokes '
          f'{bold:.2f} px against {plain:.2f} px, durable outbox and restart passed')
