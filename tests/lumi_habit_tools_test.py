"""Lumi's habit tools for creating, renaming, pausing, resuming, reading
and deleting a habit, and a reminder without changing its days, on an owned
private Xvfb window. Deleting only asks; nothing is deleted by the tool.
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
OUTPUT = ROOT / 'build/lumi-habit-tools-test'
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
        app = subprocess.Popen([sys.argv[1], '--bundle', str(ROOT / 'build/inbe-full.zx')],
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
    request = 'habit-tools-' + str(sequence)
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


def habit_in(context, name, key='habits'):
    for item in context[key]:
        if item['title'] == name:
            return item
    return None


with tempfile.TemporaryDirectory(prefix='inbe-lumi-habit-tools-') as directory:
    profile = Path(directory)
    with application(profile, 'initialize'):
        pass
    with sqlite3.connect(profile / 'inbe.db') as db:
        user = db.execute('SELECT id FROM users LIMIT 1').fetchone()[0]
        settings = dict(enabled_apps='31', language='en', language_setup_done='1',
                        apps_setup_done='1', tutorial_seen='1', habits_guide_seen='1',
                        lumi_introduced='1', package_updates_allowed='0')
        for key, value in settings.items():
            db.execute('INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) '
                       'ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value', (user, key, value))
    with application(profile, 'tools') as window:
        published = {item['name'] for item in state(window)['mcp']['tools']}
        assert {'create_habit', 'rename_habit', 'set_habit_active', 'read_habit',
                'delete_habit'} <= published, published

        created = tool(window, 'create_habit', dict(name='Stretching'))
        assert created['ok'] and created['title'] == 'Stretching' and not created['paused'], created
        identifier = created['id']
        assert tool(window, 'create_habit', dict(name='Stretching'))['error'] == 'a habit has this name'
        assert tool(window, 'create_habit', dict(name=''))['ok'] is False
        assert tool(window, 'create_habit', dict(name='x' * 40))['ok'] is False
        read = tool(window, 'read_habit', dict(id=identifier))
        assert read['schedule'] == 'every day' and read['notification_hour'] == -1, read
        assert read['tracking'] == dict(mode='check', target=1) and read['questions'] == [], read

        # A reminder alone keeps the planned days.
        result = tool(window, 'set_habit_schedule', dict(id=identifier, repeat='weekly',
                                                          weekdays=['mon', 'wed']))
        assert result['ok'], result
        result = tool(window, 'set_habit_schedule', dict(id=identifier, notification=True,
                                                          notification_hour=7))
        assert result['ok'] and result['notification_hour'] == 7, result
        assert result['schedule'] == tool(window, 'read_habit', dict(id=identifier))['schedule']
        assert 'mon' in result['schedule'].lower() and 'wed' in result['schedule'].lower(), result
        result = tool(window, 'set_habit_schedule', dict(id=identifier, every=2))
        assert result['ok'] is False and 'need repeat' in result['error'], result

        renamed = tool(window, 'rename_habit', dict(id=identifier, name='Morning stretch'))
        assert renamed['ok'] and renamed['title'] == 'Morning stretch', renamed
        assert tool(window, 'rename_habit', dict(id=identifier, name='Yoga'))['ok'] is False

        paused = tool(window, 'set_habit_active', dict(id=identifier, active=False))
        assert paused['ok'] and paused['paused'], paused
        context = tool(window, 'read_context', {})
        assert habit_in(context, 'Morning stretch') is None
        assert habit_in(context, 'Morning stretch', 'paused_habits')['id'] == identifier, context
        assert tool(window, 'read_habit', dict(id=identifier))['paused'] is True
        resumed = tool(window, 'set_habit_active', dict(id=identifier, active=True))
        assert resumed['ok'] and not resumed['paused'], resumed
        assert habit_in(tool(window, 'read_context', {}), 'Morning stretch')['id'] == identifier

        # Deleting only asks in Lumi's chat; the habit stays until a yes.
        asked = tool(window, 'delete_habit', dict(id=identifier))
        assert asked['ok'] and asked['deleted'] is False, asked
        assert habit_in(tool(window, 'read_context', {}), 'Morning stretch') is not None
        assert tool(window, 'delete_habit', dict(id='no-such-habit'))['ok'] is False

    with application(profile, 'restart') as window:
        read = tool(window, 'read_habit', dict(id=identifier))
        assert read['title'] == 'Morning stretch' and read['notification_hour'] == 7, read
print('Lumi habit tools: create, rename, pause, resume, read, reminder alone and delete question passed')
