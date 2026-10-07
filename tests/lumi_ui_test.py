"""Exercise Lumi's real cell chat against a disposable, account-scoped profile."""
import ast
import contextlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def tap(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    command("xdotool", "mousedown", "1")
    time.sleep(0.06)
    command("xdotool", "mouseup", "1")
    time.sleep(0.2)


def capture(window, label):
    raw = OUTPUT / f"{label}.xwd"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(OUTPUT / f"{label}.png"))
    raw.unlink()


@contextlib.contextmanager
def application(profile, label, standalone=False, recommended=False):
    bundle = ROOT / ("build/cells/lumi.zib" if standalone else
                     "build/inbe.zib" if recommended else "build/inbe-full.zib")
    with (OUTPUT / f"{label}.log").open("w") as log:
        app = subprocess.Popen([sys.argv[1], "--bundle", str(bundle)], cwd=ROOT,
                               env=ENV | {"APP_DATA_ROOT": str(profile)},
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                assert app.poll() is None, f"Lumi exited: {label}"
                found = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(app.pid)],
                                       env=ENV, text=True, capture_output=True, timeout=2)
                if found.returncode == 0 and found.stdout.strip():
                    window = found.stdout.splitlines()[0]
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Lumi window did not appear")
            command("xdotool", "windowsize", window, "900", "720")
            command("xdotool", "windowfocus", window)
            time.sleep(1)
            yield window
            assert app.poll() is None, "Lumi crashed"
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=3)


def query(profile, sql):
    with sqlite3.connect(profile / "inbe.db") as db:
        return db.execute(sql).fetchall()


def wait_for(predicate, description):
    deadline = time.monotonic() + 8
    while not predicate():
        assert time.monotonic() < deadline, description
        time.sleep(0.1)


def state(window):
    prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
    return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))


def chat(profile):
    rows = query(profile, "SELECT value FROM settings WHERE key='lumi_chat'")
    return json.loads(rows[0][0]) if rows else []


def send(window, profile, text, *, button=False):
    before = chat(profile)
    tap(window, 490, 676)
    command("xdotool", "keydown", "--clearmodifiers", "ctrl+a")
    time.sleep(0.15)
    command("xdotool", "keyup", "ctrl+a")
    for index, line in enumerate(text.split("\n")):
        if index:
            command("xdotool", "keydown", "--clearmodifiers", "shift+Return")
            time.sleep(0.15)
            command("xdotool", "keyup", "shift+Return")
            time.sleep(0.15)
            assert chat(profile) == before, "Shift+Enter sent the draft"
        command("xdotool", "type", "--clearmodifiers", "--delay", "18", line)
        time.sleep(0.15)
    time.sleep(0.3)
    if button:
        tap(window, 850, 676)
    else:
        command("xdotool", "keydown", "--clearmodifiers", "Return")
        time.sleep(0.15)
        command("xdotool", "keyup", "Return")
    try:
        wait_for(lambda: chat(profile) != before and
                 len(chat(profile)) == min(64, len(before) + 2) and
                 chat(profile)[-2]["text"] == text.strip(), "Chat exchange was not saved")
    except AssertionError:
        capture(window, "failure")
        raise


with tempfile.TemporaryDirectory(prefix="inbe-lumi-ui-") as directory:
    profile = Path(directory)
    with application(profile, "standalone", standalone=True) as window:
        capture(window, "standalone")
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in {
            "enabled_apps": "31", "app_used_lists": "1", "app_used_lumi": "1",
            "app_used_habits": "1", "app_used_practices": "1", "app_used_diary": "1",
            "main_tab": "4", "language": "en", "language_setup_done": "1",
            "apps_setup_done": "1", "lumi_introduced": "1", "cells_auto_update": "0",
            "tutorial_seen": "1", "habits_guide_seen": "1",
        }.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,sync_mode,"
                   "sync_activity,counter_enabled,counter_target,weekdays,sort_order,deleted_at,updated_at) "
                   "VALUES('lumi-counting-habit',?,'Read daily',100,150,100,0,0,1,3,0,20,0,1)", (user,))
        db.execute("INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,sync_mode,"
                   "sync_activity,counter_enabled,sort_order,deleted_at,updated_at) "
                   "VALUES('lumi-ambiguous-habit',?,'Read poetry',100,150,100,0,0,0,21,0,1)", (user,))
    with application(profile, "chat") as window:
        capture(window, "welcome")
        assert query(profile, "SELECT value FROM settings WHERE key='main_tab'")[0][0] == "4"
        send(window, profile, "/todo Read five pages", button=True)
        assert query(profile, "SELECT done FROM elist_items WHERE title='Read five pages'") == [(0,)]
        send(window, profile, "/done Read five")
        assert query(profile, "SELECT done FROM elist_items WHERE title='Read five pages'") == [(1,)]
        send(window, profile, "/reopen Read five")
        assert query(profile, "SELECT done FROM elist_items WHERE title='Read five pages'") == [(0,)]
        send(window, profile, "/todo Read five poems")
        send(window, profile, "/done Read five")
        assert "Several items match" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT SUM(done) FROM elist_items WHERE title LIKE 'Read five%'") == [(0,)]
        tap(window, 490, 676)
        command("xdotool", "type", "--clearmodifiers", "--delay", "18", "/done Read five p")
        time.sleep(0.4)
        capture(window, "autocomplete")
        assert query(profile, "SELECT SUM(done) FROM elist_items WHERE title LIKE 'Read five%'") == [(0,)]
        tap(window, 390, 628)
        assert query(profile, "SELECT SUM(done) FROM elist_items WHERE title LIKE 'Read five%'") == [(0,)]
        before = len(chat(profile))
        tap(window, 850, 676)
        wait_for(lambda: len(chat(profile)) == before + 2, "Selected completion was not sent")
        assert query(profile, "SELECT done FROM elist_items WHERE title='Read five pages'") == [(1,)]
        capture(window, "conversation")
        send(window, profile, "How can you help?")
        assert "Add todo" in chat(profile)[-1]["text"]
        assert "Complete habit" in chat(profile)[-1]["text"]
        send(window, profile, "complete habit Read")
        assert "Several items match" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        tap(window, 490, 676)
        command("xdotool", "type", "--clearmodifiers", "--delay", "18", "/habit Read d")
        time.sleep(0.4)
        capture(window, "habit-autocomplete")
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        tap(window, 390, 628)
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        before = len(chat(profile))
        tap(window, 850, 676)
        wait_for(lambda: len(chat(profile)) == before + 2, "Selected habit was not completed")
        assert query(profile, "SELECT completed,count FROM habit_days WHERE habit_id='lumi-counting-habit'") == [(1, 3)]
        send(window, profile, "COMPLETE HABIT")
        assert "Which habit" in chat(profile)[-1]["text"]
        assert "Read daily" in chat(profile)[-1]["text"] and "Read poetry" in chat(profile)[-1]["text"]
        capture(window, "choose-habit")
        send(window, profile, "READ DAILY")
        assert "habit is complete for today" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT completed,count FROM habit_days WHERE habit_id='lumi-counting-habit'") == [(1, 3)]
        send(window, profile, "Something you do not understand")
        assert chat(profile)[-1]["text"] == "What would you like me to do?"
        send(window, profile, "write this to my diary:")
        assert chat(profile)[-1]["text"] == "What would you like to write?"
        send(window, profile, "A calm morning\nThen a walk")
        assert chat(profile)[-1]["text"] == "Saved to today’s Diary."
        entry = next((profile / "diary").glob("????-??-??.json"))
        diary_text = json.loads(entry.read_text())["text"]
        assert re.fullmatch(r"\*\*\d{2}:\d{2}\*\*\nA calm morning\nThen a walk", diary_text)
        send(window, profile, "write this to my diary: Another thought\nA second line")
        diary_text = json.loads(entry.read_text())["text"]
        assert re.fullmatch(r"\*\*\d{2}:\d{2}\*\*\nA calm morning\nThen a walk"
                            r"\n\n\*\*\d{2}:\d{2}\*\*\nAnother thought\nA second line", diary_text)
        capture(window, "diary-chat")
        send(window, profile, "theme forest")
        assert state(window)['settings']['theme'] == 'forest'
        send(window, profile, "/dark")
        assert state(window)['settings']['theme_mode'] == 2
        assert query(profile, "SELECT value FROM settings WHERE key='theme'") == [('2',)]
        command("xdotool", "windowsize", window, "390", "720")
        time.sleep(0.6)
        capture(window, "narrow-chat")
        transcript = chat(profile)
    with application(profile, "restart") as window:
        capture(window, "restart")
        assert chat(profile) == transcript
        assert json.loads(entry.read_text())["text"] == diary_text
        assert state(window)['settings']['theme'] == 'forest'
        assert state(window)['settings']['theme_mode'] == 2
    with sqlite3.connect(profile / "inbe.db") as db:
        for key, value in {"enabled_apps": "22", "app_used_lists": "0", "app_used_diary": "0"}.items():
            db.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    before_todos = query(profile, "SELECT id,title,done FROM elist_items ORDER BY id")
    with application(profile, "recommended-only", recommended=True) as window:
        send(window, profile, "How can you help?")
        help_text = chat(profile)[-1]["text"]
        assert "Start WHM" in help_text and "Complete habit" in help_text
        assert "todo" not in help_text and "Lists" not in help_text and "Diary" not in help_text
        capture(window, "installed-cells-help")
        tap(window, 490, 676)
        command("xdotool", "type", "--clearmodifiers", "--delay", "18", "add")
        time.sleep(0.4)
        capture(window, "lists-unavailable-suggestions")
        send(window, profile, "/todo This must not be added")
        assert "unavailable" in chat(profile)[-1]["text"]
        send(window, profile, "/done Read five poems")
        assert "unavailable" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT id,title,done FROM elist_items ORDER BY id") == before_todos
        assert query(profile, "SELECT value FROM settings WHERE key='enabled_apps'") == [("22",)]
        send(window, profile, "start whm")
        wait_for(lambda: state(window)["practice_running"] and state(window)["practice"] == 0,
                 "Lumi did not start WHM immediately")
        breath = state(window)["breath"]
        wait_for(lambda: state(window)["breath"] > breath, "WHM did not advance")
        assert state(window)["screen"] == 1 and not state(window)["paused"]
        capture(window, "whm-started")
    for label, command_text, practice_id in [
        ("meditation-typo", "start meditaiton", 1),
        ("meditation-uppercase", "START MEDITATION", 1),
        ("sun-salutation", "start sun salutation", 2),
        ("breathing-patterns", "start breathing patterns", 3),
    ]:
        with sqlite3.connect(profile / "inbe.db") as db:
            db.execute("UPDATE settings SET value='4' WHERE key='main_tab'")
        with application(profile, label, recommended=True) as window:
            send(window, profile, command_text)
            wait_for(lambda: state(window)["practice_running"] and state(window)["practice"] == practice_id,
                     f"{command_text} did not start its practice")
            assert not state(window)["paused"]
            capture(window, label)
    with sqlite3.connect(profile / "inbe.db") as db:
        for key, value in {"enabled_apps": "16", "app_used_habits": "0", "app_used_practices": "0",
                           "main_tab": "4"}.items():
            db.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    before_habits = query(profile, "SELECT habit_id,local_date,completed,count FROM habit_days ORDER BY habit_id,local_date")
    with application(profile, "lumi-only", standalone=True) as window:
        send(window, profile, "How can you help?")
        assert "todo" not in chat(profile)[-1]["text"]
        assert "Start WHM" not in chat(profile)[-1]["text"]
        send(window, profile, "start whm")
        assert "unavailable" in chat(profile)[-1]["text"]
        assert not state(window)["practice_running"]
        send(window, profile, "complete habit Read poetry")
        assert "unavailable" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT habit_id,local_date,completed,count FROM habit_days ORDER BY habit_id,local_date") == before_habits
        capture(window, "lumi-only")
    (OUTPUT / "result.json").write_text(json.dumps({
        "passed": True, "exchanges": len(transcript) // 2,
        "checked": ["standalone cell", "default Lumi home", "add todo", "unique completion",
                    "reopen", "ambiguous completion", "suggestions do not execute", "restart persistence",
                    "habit ambiguity", "habit counter target", "no uncompletion on repeated command",
                    "Lists absent", "WHM starts and advances immediately", "Practices and Habits absent", "habit question and name reply",
                    "meditation transposition", "case-insensitive commands", "all four practice starts",
                    "brief unknown reply", "Diary follow-up", "timestamp before entry", "Shift+Enter",
                    "multiline Diary append", "Diary restart persistence"],
    }, indent=2) + "\n")
print("Lumi UI: chat, installed-cell tools, habit targets, WHM start, autocomplete and persistence passed")
