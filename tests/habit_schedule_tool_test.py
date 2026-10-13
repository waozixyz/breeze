"""Lumi's set_habit_schedule tool on an owned private Xvfb window.

Lumi sets every kind of schedule and the notification through the same
app tool external MCP clients use; a changed schedule starts today, keeps
the earlier days' schedule, and survives a restart.
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
OUTPUT = ROOT / 'build/habit-schedule-tool-test'
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
    request = 'schedule-' + str(sequence)
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


def schedule(window, **arguments):
    return tool(window, 'set_habit_schedule', arguments)


with tempfile.TemporaryDirectory(prefix='inbe-habit-schedule-') as directory:
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
        assert 'set_habit_schedule' in published
        yoga = habit(window, 'Yoga')
        assert yoga['schedule'] == 'every day', yoga
        assert yoga['notification_hour'] == -1, yoga
        identifier = yoga['id']

        result = schedule(window, id=identifier, repeat='weekly',
                          weekdays=['mon', 'wed', 'thu'], notification=True,
                          notification_hour=7)
        assert result == dict(ok=True, schedule='every week on mon,wed,thu',
                              notification_hour=7), result
        yoga = habit(window, 'Yoga')
        assert yoga['schedule'] == 'every week on mon,wed,thu' and yoga['notification_hour'] == 7, yoga

        result = schedule(window, id=identifier, repeat='monthly', week_of_month='last',
                          weekdays=['fri'], notification=False)
        assert result['ok'] and result['schedule'] == 'every month on the last fri', result
        assert result['notification_hour'] == -1, result

        result = schedule(window, id=identifier, repeat='monthly', month_days=[1, 15],
                          last_day_of_month=True, every=2, start='2026-01-01')
        assert result['schedule'] == 'every 2 months on day 1,15,last from 2026-01-01', result

        result = schedule(window, id=identifier, repeat='formula', formula='days % 3 = 0 and weekday < 6',
                          start='2026-10-01')
        assert result['schedule'] == 'days where days % 3 = 0 and weekday < 6 from 2026-10-01', result

        for wrong, error in [
                (dict(repeat='formula', formula='days %'), 'formula'),
                (dict(repeat='weekly', weekdays=['someday']), 'weekdays'),
                (dict(repeat='daily', every=0), 'every'),
                (dict(repeat='daily', start='2026-02-30'), 'start'),
                (dict(repeat='hourly'), 'repeat'),
                (dict(repeat='monthly', week_of_month='last'), 'weekdays'),
                (dict(repeat='daily', notification=True), 'notification_hour')]:
            result = schedule(window, id=identifier, **wrong)
            assert result['ok'] is False and error in result['error'], (wrong, result)
        result = schedule(window, id='no-such-habit', repeat='daily')
        assert result['ok'] is False, result
        assert habit(window, 'Yoga')['schedule'] == \
            'days where days % 3 = 0 and weekday < 6 from 2026-10-01'

        result = schedule(window, id=identifier, repeat='yearly', start='2026-12-06')
        assert result['schedule'] == 'every year from 2026-12-06', result
        result = schedule(window, id=identifier, repeat='none')
        assert result['schedule'] == 'no set days', result
        result = schedule(window, id=identifier, repeat='daily', every=2,
                          notification=True, notification_hour=21)
        assert result == dict(ok=True, schedule='every 2 days from ' + time.strftime('%Y-%m-%d'),
                              notification_hour=21), result

    with sqlite3.connect(profile / 'inbe.db') as db:
        stored, hour = db.execute("SELECT schedule,reminder_hour FROM habits WHERE id=?",
                                  (identifier,)).fetchone()
    # Yoga counts its practices, so its earlier days keep the schedule they
    # had; every change today replaced the one before it.
    lines = stored.split('\n')
    assert len(lines) == 2, stored
    assert lines[0].startswith('from=0;repeat=weekly;every=1;start=0;weekdays=127;'), stored
    assert lines[1].startswith('from=' + time.strftime('%Y%m%d') + ';repeat=daily;every=2;'), stored
    assert hour == 21

    with application(profile, 'restart') as window:
        yoga = habit(window, 'Yoga')
        assert yoga['schedule'] == 'every 2 days from ' + time.strftime('%Y-%m-%d'), yoga
        assert yoga['notification_hour'] == 21, yoga
print('habit schedule tool tests passed')
