"""Lumi's set_habit_tracking and set_habit_questions tools on an owned
private Xvfb window.

Lumi makes a habit count or measure spans from start to end, and sets the
questions it asks with their good answers; a question keeps its id while
its words stay, and everything survives a restart.
"""
import ast
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/habit-tracking-tool-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
ENV = os.environ | dict(APP_NO_TRAY='1', SDL_AUDIODRIVER='dummy',
                        YUE_DESKTOP_RECOVERY='0')
for key in ('WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER'):
    ENV.pop(key, None)
sequence = 0


def command(*args):
    return subprocess.check_output(args, env=ENV, text=True, timeout=10).strip()


def wait_for(predicate, message):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


@contextlib.contextmanager
def application(profile, label):
    with (OUTPUT / (label + '.log')).open('w') as log:
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zib')],
                               cwd=ROOT, env=ENV | dict(APP_DATA_ROOT=str(profile)),
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            def find():
                assert app.poll() is None, 'Owned application exited: ' + label
                found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(app.pid)],
                                       env=ENV, capture_output=True, text=True, timeout=5)
                return found.stdout.strip().splitlines()[0] if found.returncode == 0 else ''
            window = wait_for(find, 'Owned app window did not appear')
            wait_for(lambda: ' = ' in command('xprop', '-id', window, '_HARMONY_APP_STATE'),
                     'App state did not become ready')
            yield window
            assert app.poll() is None, 'Owned app crashed'
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)


def state(window):
    value = command('xprop', '-id', window, '_HARMONY_APP_STATE')
    return json.loads(ast.literal_eval(value.split(' = ', 1)[1]))


def tool(window, name, arguments):
    global sequence
    sequence += 1
    request = 'tracking-' + str(sequence)
    payload = dict(request_id=request, control='mcp.' + name, arguments=arguments)
    command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
            '-set', '_HARMONY_APP_ACTION', json.dumps(payload))
    report = wait_for(lambda: (value if (value := state(window))['last_request_id'] == request else None),
                      'App tool did not acknowledge: ' + name)
    return report['tool_result']


def habit(window, name):
    for item in tool(window, 'read_context', {})['habits']:
        if item['title'] == name:
            return item
    raise AssertionError('Lumi does not see the habit ' + name)


def tracking(window, **arguments):
    return tool(window, 'set_habit_tracking', arguments)


def questions(window, identifier, items):
    return tool(window, 'set_habit_questions', dict(id=identifier, questions=items))


MEAL = [
    dict(text='When did I start eating?', answer='time', good='at_most', high='08:00'),
    dict(text='Plates', answer='number', good='between', low=1, high=2),
    dict(text='Ate fruit?', answer='yes_no', good='yes'),
    dict(text='What did I eat first?', answer='text'),
]


def stored_ids(profile, identifier):
    with sqlite3.connect(profile / 'inbe.db') as db:
        text = db.execute('SELECT questions FROM habits WHERE id=?', (identifier,)).fetchone()[0]
    return {item['text']: item['id'] for item in json.loads(text)}


with tempfile.TemporaryDirectory(prefix='inbe-habit-tracking-') as directory:
    profile = Path(directory)
    with application(profile, 'initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        settings = dict(enabled_apps='31', language='en', language_setup_done='1',
                        apps_setup_done='1', tutorial_seen='1', habits_guide_seen='1',
                        lumi_introduced='1', cells_auto_update='0')
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))
    with application(profile, 'lumi') as window:
        published = {item['name'] for item in state(window)['mcp']['tools']}
        assert {'set_habit_tracking', 'set_habit_questions'} <= published, published
        yoga = habit(window, 'Yoga')
        assert yoga['tracking']['mode'] in ('check', 'count') and yoga['questions'] == [], yoga
        identifier = yoga['id']

        result = tracking(window, id=identifier, mode='span')
        assert result['ok'] and result['tracking'] == dict(mode='span', target=1), result
        result = tracking(window, id=identifier, mode='count', target=3)
        assert result['tracking'] == dict(mode='count', target=3), result
        result = tracking(window, id=identifier, mode='span')
        assert result['tracking'] == dict(mode='span', target=3), result

        result = questions(window, identifier, MEAL)
        assert result['ok'], result
        assert result['questions'] == [
            dict(text='When did I start eating?', answer='time', good='at_most', high='08:00'),
            dict(text='Plates', answer='number', good='between', low=1, high=2),
            dict(text='Ate fruit?', answer='yes_no', good='yes'),
            dict(text='What did I eat first?', answer='text')], result
        before = stored_ids(profile, identifier)
        assert len(set(before.values())) == 4, before

        # Changing a goal keeps the question; new words make a new one.
        result = questions(window, identifier, [
            dict(text='Plates', answer='number', good='at_most', high=3),
            dict(text='When did I start eating?', answer='time', good='at_least',
                 low='12:00'),
            dict(text='Bedtime', answer='time', good='between', low='22:00', high='00:30')])
        assert result['ok'], result
        after = stored_ids(profile, identifier)
        assert after['Plates'] == before['Plates'], (before, after)
        assert after['When did I start eating?'] == before['When did I start eating?']
        assert after['Bedtime'] not in before.values(), (before, after)
        assert habit(window, 'Yoga')['questions'][2] == dict(
            text='Bedtime', answer='time', good='between', low='22:00', high='00:30')

        for items, error in [
                ([dict(text='Plates', answer='number', good='yes')], 'yes and no'),
                ([dict(text='Plates', answer='number', good='at_least')], 'whole numbers'),
                ([dict(text='Wake', answer='time', good='at_most', high='7')], 'H:MM'),
                ([dict(text='Mood', answer='text', good='at_least', low=1)], 'text answers'),
                ([dict(text='When', answer='date')], 'answer must be'),
                ([dict(text='', answer='text')], 'words'),
                ([dict(text='Q%d' % index, answer='text') for index in range(9)], 'at most 8'),
                ([dict(text='Plates', answer='number', good='between', low=5, high=2)], 'low')]:
            result = questions(window, identifier, items)
            assert result['ok'] is False and error in result['error'], (items, result)
        for wrong, error in [
                (dict(mode='timer'), 'mode'),
                (dict(mode='count', target=0), 'target')]:
            result = tracking(window, id=identifier, **wrong)
            assert result['ok'] is False and error in result['error'], (wrong, result)
        assert tracking(window, id='no-such-habit', mode='check')['ok'] is False
        assert questions(window, 'no-such-habit', [])['ok'] is False

    with application(profile, 'restart') as window:
        yoga = habit(window, 'Yoga')
        assert yoga['tracking'] == dict(mode='span', target=3), yoga
        assert [item['text'] for item in yoga['questions']] == [
            'Plates', 'When did I start eating?', 'Bedtime'], yoga
        result = questions(window, yoga['id'], [])
        assert result['ok'] and result['questions'] == [], result
print('habit tracking tool tests passed')
