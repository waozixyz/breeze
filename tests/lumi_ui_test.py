"""Exercise Lumi's real cell chat against a disposable, account-scoped profile.

The app runs on a private display and is driven through Kryon's test driver:
widgets are found in its committed tree and pressed, typed into and read
through the app's own input path.
"""
import ast
import contextlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
# Made when the first app starts, in the OUTPUT of the test that runs it.
driver = None
# Lumi's command list and chart bars, from apps/lumi/lumi_view.zi.
COMMAND_LIST_KEY = 360001
CHART_BAR_KEYS = range(310000, 330000)


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def save_tree(label):
    """Keep what the app showed when a step failed, for the CI artifact."""
    with contextlib.suppress(Exception):
        (OUTPUT / f"failure-{label}.json").write_text(json.dumps(driver.tree(), indent=1) + "\n")


@contextlib.contextmanager
def application(profile, label, standalone=False, recommended=False):
    global driver
    if driver is None:
        driver = UiDriver(OUTPUT / "driver")
    bundle = ROOT / ("build/cells/lumi.zib" if standalone else
                     "build/inbe.zib" if recommended else "build/inbe-full.zib")
    log_path = OUTPUT / f"{label}.log"
    with log_path.open("w") as log:
        app = subprocess.Popen([sys.argv[1], "--bundle", str(bundle)], cwd=ROOT,
                               env=ENV | driver.environment() | {
                                   "APP_DATA_ROOT": str(profile),
                                   "KRYON_TEST_OPEN_URI_CAPTURE": str(OUTPUT / (label + "-uri.txt"))},
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, log_path)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                assert app.poll() is None, f"Lumi exited: {label}"
                found = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(app.pid)],
                                       env=ENV, text=True, capture_output=True, timeout=5)
                if found.returncode == 0 and found.stdout.strip():
                    window = found.stdout.splitlines()[0]
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Lumi window did not appear")
            command("xdotool", "windowsize", window, "900", "720")
            wait_for(lambda: " = " in command("xprop", "-id", window, "_HARMONY_APP_STATE"),
                     "Owned app UI did not become ready")
            driver.wait(role="screen")
            driver.wait_idle(frames=3)
            yield window
            assert app.poll() is None, "Lumi crashed"
        except BaseException:
            if app.poll() is None:
                save_tree(label)
            raise
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
    rows = query(profile, "SELECT value FROM settings WHERE key LIKE 'cell.lumi.message.%' "
                 "ORDER BY CAST(json_extract(value,'$.time') AS INTEGER),key")
    return [{key: value for key, value in json.loads(row[0]).items() if key != "time"} for row in rows]


def draft():
    """The text in Lumi's message field."""
    return driver.wait(role="text_area")["value"]


def wait_draft(text):
    """Wait until the draft contains text, as a chosen suggestion leaves it."""
    deadline = time.monotonic() + 8
    while text not in draft():
        assert time.monotonic() < deadline, f"The draft is {draft()!r}, without {text!r}"
        time.sleep(0.05)


def start_draft(text=""):
    """Put the keyboard in an empty draft and type text into it."""
    driver.press(role="text_area")
    driver.key("a", control=True)
    driver.key("backspace")
    driver.wait(role="text_area", value="")
    if text:
        driver.type(text)
        driver.wait(role="text_area", value=text)


def send(window, profile, text, *, button=False):
    before = chat(profile)
    start_draft()
    for index, line in enumerate(text.split("\n")):
        if index:
            driver.key("enter", shift=True)
            assert chat(profile) == before, "Shift+Enter sent the draft"
        driver.type(line)
    assert draft() == text, f"The draft is {draft()!r}, not {text!r}"
    if button:
        driver.press(label="Send", role="button", enabled=True)
    else:
        driver.key("enter")
    confirm_exchange(profile, before, text)


def confirm_exchange(profile, before, text):
    def exchange_saved():
        rows = chat(profile)
        return (rows != before and len(rows) >= 2 and
                rows[-2]["user"] == 1 and rows[-2]["text"] == text.strip() and
                rows[-1]["user"] == 0)

    try:
        wait_for(exchange_saved, "Chat exchange was not saved")
        rows = chat(profile)
        assert rows[:-2] == before, "Chat lost earlier conversation"
    except AssertionError:
        save_tree("exchange")
        (OUTPUT / "failure-exchange.json").write_text(json.dumps({
            "expected": text.strip(), "recent": chat(profile)[-3:]
        }, indent=2) + "\n")
        raise


def command_list():
    """The /names the command list over the draft shows, top to bottom."""
    menu = driver.wait(key=COMMAND_LIST_KEY)
    return [node for node in driver.find(role="text", visible=True)
            if menu["y"] <= node["y"] < menu["y"] + menu["height"] and node["label"].startswith("/")]


def command_list_entry(name):
    """A command's row in the list over the draft, by its /name."""
    rows = []
    deadline = time.monotonic() + 8
    while not rows:
        assert time.monotonic() < deadline, f"{name} is not in the command list"
        rows = [node for node in command_list() if node["label"] == name]
    return rows[0]


def latest_chart_bars():
    """The bars of the newest progress chart, oldest day first."""
    bars = [node for node in driver.tree()
            if node["kind"] == "button" and node["key"] in CHART_BAR_KEYS and node["visible"]]
    assert bars, "No progress chart is on screen"
    newest = max((node["key"] - CHART_BAR_KEYS.start) // 32 for node in bars)
    return newest, sorted((node for node in bars
                           if (node["key"] - CHART_BAR_KEYS.start) // 32 == newest),
                          key=lambda node: node["key"])


with tempfile.TemporaryDirectory(prefix="inbe-lumi-ui-") as directory:
    profile = Path(directory)
    with application(profile, "standalone", standalone=True) as window:
        tool_names = {tool["name"] for tool in state(window)["mcp"]["tools"]}
        assert "show_progress_chart" in tool_names and "show_donation_links" not in tool_names
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in {
            "enabled_apps": "31", "app_used_lists": "1", "app_used_lumi": "1",
            "app_used_habits": "1", "app_used_practices": "1", "app_used_diary": "1",
            "main_tab": "4", "language": "en", "language_setup_done": "1",
            "apps_setup_done": "1", "lumi_introduced": "1", "package_updates_allowed": "0",
            "tutorial_seen": "1", "habits_guide_seen": "1", "lumi_guides_seen": "127",
            # Switched offline, Lumi opens on its chat rather than its terms.
            "lumi_online": "0",
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
    with application(profile, "rich-cards") as window:
        send(window, profile, "/progress sessions 7")
        chart_row = chat(profile)[-1]
        assert chart_row["kind"] == 1
        chart_data = json.loads(chart_row["payload"])
        assert chart_data["metric"] == 0 and len(chart_data["points"]) == 7
        assert all(point["value"] == 0 for point in chart_data["points"])
        driver.wait(label="No recorded activity in this period.")
        send(window, profile, "/progress habits 30")
        assert len(json.loads(chat(profile)[-1]["payload"])["points"]) == 30
        with sqlite3.connect(profile / "inbe.db") as db:
            today = db.execute("SELECT CAST(strftime('%Y%m%d','now','localtime') AS INTEGER)").fetchone()[0]
            for identity, activity, seconds in [("chart-whm", 0, 95), ("chart-meditation", 1, 120)]:
                db.execute("INSERT INTO sessions(id,user_id,started_at,local_date,activity,source,imported_at,rounds_hash) "
                           "VALUES(?,?,?, ?,?,'test',1,1)", (identity, user, 1 if activity == 0 else 2, today, activity))
                db.execute("INSERT INTO session_rounds VALUES(?,0,?)", (identity, seconds))
        for metric, expected in [("sessions", 2), ("meditation", 120), ("retention", 95)]:
            send(window, profile, f"/progress {metric} 7")
            points = json.loads(chat(profile)[-1]["payload"])["points"]
            assert points[-1] == {"date": today, "value": expected}
            assert sum(point["value"] for point in points[:-1]) == 0
        # Select the latest day in the seven-bar chart: its summary shows
        # that day's value instead of the first day's.
        driver.wait_idle(frames=3)
        row, bars = latest_chart_bars()
        assert len(bars) == 7, bars
        summary_key = 330000 + row * 64 + 32
        first_day = str(points[0]["date"])
        driver.wait(key=summary_key, label=f"{first_day[:4]}-{first_day[4:6]}-{first_day[6:]} · 0")
        driver.press(key=bars[-1]["key"])
        today_text = str(today)
        driver.wait(key=summary_key, label=f"{today_text[:4]}-{today_text[4:6]}-{today_text[6:]} · 95")
        # Donations are gone: /donate is no command and adds no card.
        send(window, profile, "/donate")
        assert all(row.get("kind") != 2 for row in chat(profile))
    # Keep the original conversation fixtures independent of chart records.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("DELETE FROM settings WHERE key LIKE 'cell.lumi.message.%'")
        db.execute("DELETE FROM session_rounds WHERE session_id IN ('chart-whm','chart-meditation')")
        db.execute("DELETE FROM sessions WHERE id IN ('chart-whm','chart-meditation')")
    with application(profile, "chat") as window:
        driver.wait(role="text_area")
        assert query(profile, "SELECT value FROM settings WHERE key='main_tab'")[0][0] == "4"
        # As in Telegram, the empty draft offers a command button whose list
        # narrows while typing. Enter picks the highlighted command, and one
        # that needs text waits in the draft with the keyboard still in it.
        before = len(chat(profile))
        driver.press(label="Commands", role="button")
        driver.wait(role="text_area", value="/")
        driver.type("h")
        command_list_entry("/help")
        driver.key("enter")
        wait_for(lambda: len(chat(profile)) == before + 2, "Enter did not send the highlighted command")
        assert chat(profile)[-2]["text"] == "/help" and "I can help" in chat(profile)[-1]["text"]
        driver.type("/to")
        command_list_entry("/todo")
        driver.key("enter")
        driver.wait(role="text_area", value="/todo ")
        driver.wait_idle(frames=3)
        assert len(chat(profile)) == before + 2, "A command that needs text was sent without it"
        driver.type("Water plants")
        driver.wait(role="text_area", value="/todo Water plants")
        driver.key("enter")
        wait_for(lambda: len(chat(profile)) == before + 4, "The completed command was not sent")
        assert chat(profile)[-2]["text"] == "/todo Water plants"
        assert query(profile, "SELECT done FROM elist_items WHERE title='Water plants'") == [(0,)]
        driver.type("/he")
        # The only match, /help, sits next to the draft: tap it.
        wait_for(lambda: [node["label"] for node in command_list()] == ["/help"],
                 "The command list did not narrow to /help")
        driver.press(key=command_list_entry("/help")["key"])
        wait_for(lambda: len(chat(profile)) == before + 6, "A tapped command was not sent")
        assert chat(profile)[-2]["text"] == "/help" and "I can help" in chat(profile)[-1]["text"]
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
        start_draft("/done Read five p")
        driver.wait(label="Read five pages", role="button")
        assert query(profile, "SELECT SUM(done) FROM elist_items WHERE title LIKE 'Read five%'") == [(0,)]
        driver.press(label="Read five pages", role="button")
        wait_draft("Read five pages")
        assert query(profile, "SELECT SUM(done) FROM elist_items WHERE title LIKE 'Read five%'") == [(0,)]
        before = len(chat(profile))
        driver.press(label="Send", role="button", enabled=True)
        wait_for(lambda: len(chat(profile)) == before + 2, "Selected completion was not sent")
        assert query(profile, "SELECT done FROM elist_items WHERE title='Read five pages'") == [(1,)]
        send(window, profile, "How can you help?")
        assert "Add todo" in chat(profile)[-1]["text"]
        assert "Complete habit" in chat(profile)[-1]["text"]
        send(window, profile, "complete habit Read")
        assert "Several items match" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        start_draft("/habit Read d")
        driver.wait(label="Read daily", role="button")
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        driver.press(label="Read daily", role="button")
        wait_draft("Read daily")
        assert query(profile, "SELECT count FROM habit_days WHERE habit_id='lumi-counting-habit'") == []
        before = len(chat(profile))
        driver.press(label="Send", role="button", enabled=True)
        wait_for(lambda: len(chat(profile)) == before + 2, "Selected habit was not completed")
        assert query(profile, "SELECT completed,count FROM habit_days WHERE habit_id='lumi-counting-habit'") == [(1, 3)]
        send(window, profile, "COMPLETE HABIT")
        assert "Which habit" in chat(profile)[-1]["text"]
        assert "Read daily" in chat(profile)[-1]["text"] and "Read poetry" in chat(profile)[-1]["text"]
        send(window, profile, "READ DAILY")
        assert "habit is complete for today" in chat(profile)[-1]["text"]
        assert query(profile, "SELECT completed,count FROM habit_days WHERE habit_id='lumi-counting-habit'") == [(1, 3)]
        send(window, profile, "Something you do not understand")
        # Offline, what Lumi can't read stays here, with how to ask the AI.
        assert chat(profile)[-1]["text"].startswith("I didn’t understand that on this device."), \
            chat(profile)[-1]["text"]
        send(window, profile, "write this to my diary:")
        assert chat(profile)[-1]["text"] == "What would you like to write?"
        send(window, profile, "A calm morning\nThen a walk")
        assert chat(profile)[-1]["text"] == "Saved to today’s Diary."
        # Entries belong to the active account, rather than the legacy shared
        # directory. Reading that exact directory also catches cross-account writes.
        entry = next((profile / "diary" / user).glob("????-??-??.json"))
        diary_text = json.loads(entry.read_text())["text"]
        assert re.fullmatch(r"\*\*\d{2}:\d{2}\*\*\nA calm morning\nThen a walk", diary_text)
        send(window, profile, "write this to my diary: Another thought\nA second line")
        diary_text = json.loads(entry.read_text())["text"]
        assert re.fullmatch(r"\*\*\d{2}:\d{2}\*\*\nA calm morning\nThen a walk"
                            r"\n\n\*\*\d{2}:\d{2}\*\*\nAnother thought\nA second line", diary_text)
        send(window, profile, "theme forest")
        assert state(window)['settings']['theme'] == 'forest'
        send(window, profile, "/dark")
        assert state(window)['settings']['theme_mode'] == 2
        assert query(profile, "SELECT value FROM settings WHERE key='theme'") == [('2',)]
        # A phone-wide window still fits the chat and its draft.
        command("xdotool", "windowsize", window, "390", "720")
        screen = driver.wait(role="screen", visible=None)
        deadline = time.monotonic() + 5
        while screen["width"] != 390:
            assert time.monotonic() < deadline, f"The chat did not narrow: {screen}"
            time.sleep(0.05)
            screen = driver.wait(role="screen", visible=None)
        driver.wait_idle(frames=3)
        field = driver.wait(role="text_area")
        assert screen["x"] <= field["x"] and field["x"] + field["width"] <= screen["x"] + screen["width"], field
        transcript = chat(profile)
    with application(profile, "restart") as window:
        assert chat(profile) == transcript
        assert json.loads(entry.read_text())["text"] == diary_text
        assert state(window)['settings']['theme'] == 'forest'
        assert state(window)['settings']['theme_mode'] == 2
    with sqlite3.connect(profile / "inbe.db") as db:
        for key, value in {"enabled_apps": "22", "app_used_lists": "0", "app_used_diary": "0",
                           "app_used_leaderboard": "0"}.items():
            db.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    before_todos = query(profile, "SELECT id,title,done FROM elist_items ORDER BY id")
    with application(profile, "recommended-only", recommended=True) as window:
        send(window, profile, "How can you help?")
        help_text = chat(profile)[-1]["text"]
        assert "Start WHM" in help_text and "Complete habit" in help_text
        assert "todo" not in help_text and "Lists" not in help_text and "Diary" not in help_text
        # Without Lists, typing "add" suggests no todo.
        start_draft("add")
        driver.wait_idle(frames=3)
        chips = [node["label"] for node in driver.find(role="button", visible=True)
                 if node["label"].lower().startswith("add")]
        assert not chips, f"Lists is not installed, yet Lumi suggests {chips}"
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
    # Without a practice on this device Lumi asks first: no drops the offer,
    # yes opens Manage practices at it, and nothing starts either way.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("UPDATE settings SET value='4' WHERE key='main_tab'")
    with application(profile, "practice-offer", recommended=True) as window:
        send(window, profile, "start sun salutation")
        offer = chat(profile)[-1]["text"]
        assert offer.startswith("Sun Salutation") and offer.endswith("Download it now?"), offer
        send(window, profile, "no")
        assert chat(profile)[-1]["text"] == "Cancelled."
        # Tai Chi is paid: without the account's unlock Lumi offers to unlock it.
        send(window, profile, "start tai chi")
        assert chat(profile)[-1]["text"] == "Tai Chi is unlocked with Dew. Unlock it now?", chat(profile)[-1]
        send(window, profile, "no")
        assert chat(profile)[-1]["text"] == "Cancelled."
        send(window, profile, "start meditation")
        assert chat(profile)[-1]["text"].endswith("Download it now?")
        send(window, profile, "yes")
        assert chat(profile)[-1]["text"] == "Opening Manage practices."
        # Nothing may start in the moments after the answer.
        time.sleep(0.6)
        assert not state(window)["practice_running"]
    # Practices other than Wim Hof are downloads; install them as Manage
    # practices would before Lumi starts them.
    (profile / "packages").mkdir(exist_ok=True)
    for name in ("meditation", "sunsalutation", "patterns"):
        shutil.copyfile(ROOT / "build/practice-content" / (name + ".zib"),
                        profile / "packages" / ("practice-" + name + ".zib"))
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
    with sqlite3.connect(profile / "inbe.db") as db:
        for key, value in {"enabled_apps": "16", "app_used_habits": "0", "app_used_practices": "0",
                           "app_used_leaderboard": "0", "main_tab": "4"}.items():
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
    (OUTPUT / "result.json").write_text(json.dumps({
        "passed": True, "exchanges": len(transcript) // 2,
        "checked": ["standalone cell", "default Lumi home", "add todo", "unique completion",
                    "reopen", "ambiguous completion", "suggestions do not execute", "restart persistence",
                    "habit ambiguity", "habit counter target", "no uncompletion on repeated command",
                    "Lists absent", "WHM starts and advances immediately", "Practices and Habits absent", "habit question and name reply",
                    "meditation transposition", "case-insensitive commands", "all four practice starts",
                    "brief unknown reply", "Diary follow-up", "timestamp before entry", "Shift+Enter",
                    "multiline Diary append", "Diary restart persistence", "durable history retention",
                    "progress zero and recorded values", "chart day selection", "no donations", "download offer",
                    "large tool catalog", "command button and list", "Enter picks a command",
                    "command waits for its text", "tapped command", "no todo suggestions without Lists",
                    "narrow chat fits"],
    }, indent=2) + "\n")
print("Lumi UI: chat, installed-cell tools, habit targets, WHM start, autocomplete and persistence passed")
