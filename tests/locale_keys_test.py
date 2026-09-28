#!/usr/bin/env python3
"""Locale files and the code that uses them agree on the set of keys.

Every locale file has exactly the English keys, each with a value and a `---`
separator; the four practice labels exist; every LocaleText / FormatLocaleText
call with a literal key names an English key; and every English key is used
somewhere (or is one of the keys chosen at run time, listed below).
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
failures = []

PRACTICE_LABELS = ["exercise_wim_hof", "exercise_patterns",
                   "exercise_meditation", "exercise_sun_salutation"]

# Keys picked by name at run time, so no literal use appears in the sources.
DYNAMIC_KEYS = """
exercise_wim_hof exercise_patterns exercise_meditation exercise_sun_salutation
meditation_music_download_button meditation_music_redownload_button
sync_alias_title sync_alias_change_title sync_alias_message
sync_alias_change_message sync_alias_register_button sync_alias_save_button
skip_button close_button sync_review_using_remote sync_review_keeping_local
habit_stats_no_rounds_month habit_stats_no_rounds_week habit_stats_day_singular
habit_stats_day_plural session_count_singular session_count_plural
practice_home_minutes practice_home_repetitions practice_home_wim_hof_metadata
habit_session_total_count habit_day_total_count_suffix deleted_sessions
sync_pull_ok sync_pull_conflict sync_push_ok sync_push_failed sync_sign_failed
sync_invalid_account sync_server_unreachable sync_server_error sync_connected
sync_auth_failed sync_failed sync_server_unavailable sync_status_connected
sync_status_disconnected tray_show_inner_breeze tray_hide_inner_breeze
tray_start_practice tray_quit_inner_breeze tray_break_settings
tray_mark_complete tray_wim_hof_paused tray_wim_hof_breath tray_wim_hof_hold
tray_wim_hof_breathe_in tray_wim_hof_next_round tray_wim_hof_starting_seconds
tray_meditation_paused tray_meditation_left tray_sun_salutation
tray_sun_salutation_paused tray_patterns_left tray_patterns_left_paused
tray_patterns_elapsed tray_patterns_elapsed_paused tray_next_break
theme_sky theme_ocean theme_forest theme_sunset theme_lavender theme_cherry
theme_dawn theme_sage theme_sepia theme_mono theme_mint theme_cobalt
tutorial_step_intro tutorial_step_method tutorial_step_breathe
tutorial_step_exhale_hold tutorial_step_inhale_hold
""".split() + ["sun_salutation_step_%d" % i for i in range(1, 13)]


def load_keys(path):
    """The keys of a locale file, recording format problems as failures."""
    keys = []
    pending = None
    needs_separator = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = line.rstrip("\r")
        if line == "---":
            needs_separator = False
        header = re.match(r"^\[([^\]]+)\]", line)
        if header:
            key = header.group(1)
            if needs_separator:
                failures.append(f"{path.name} missing --- before [{key}]")
            needs_separator = True
            if pending is not None:
                failures.append(f"{path.name} key [{pending}] has no value")
            if key not in keys:
                keys.append(key)
            pending = key
        elif pending is not None and line.strip() not in ("", "---"):
            pending = None
    if pending is not None:
        failures.append(f"{path.name} key [{pending}] has no value")
    return keys


def check_practice_labels(keys, name):
    for label in PRACTICE_LABELS:
        if label not in keys:
            failures.append(f"{name} missing practice label [{label}]")


english = load_keys(root / "locales/en.txt")
english_set = set(english)
check_practice_labels(english, "en.txt")

sources = []
for directory in (root / "src", root / "build/packages/kryon/src"):
    if directory.is_dir():
        sources += sorted(p for p in directory.rglob("*") if p.suffix in (".zi", ".c", ".h"))

call = re.compile(r'\b(?:LocaleText|GetLocaleText|FormatLocaleText)\(\s*"([^"]*)"')
used = set(DYNAMIC_KEYS)
for source in sources:
    text = source.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.split("\n"), 1):
        for match in call.finditer(line):
            if match.group(1) not in english_set:
                failures.append(f"{source.relative_to(root)}:{number} locale call missing English key [{match.group(1)}]")
    # Key literals also appear in data tables, not only in direct calls.
    for literal in re.findall(r'"([^"\n]{1,127})"', text):
        if literal in english_set:
            used.add(literal)

# English strings nothing uses yet. Listing them keeps new dead strings from
# slipping in; delete a key from the locale files and from this list together.
allowed_unused = set()
allowlist = root / "tests/locale_unused_keys.txt"
if allowlist.exists():
    allowed_unused = {line.strip() for line in allowlist.read_text().split("\n") if line.strip()}
for key in english:
    if key not in used and key not in allowed_unused:
        failures.append(f"en.txt unused key [{key}]")
for key in sorted(allowed_unused):
    if key not in english_set:
        failures.append(f"tests/locale_unused_keys.txt lists [{key}], which is not in en.txt")
    elif key in used:
        failures.append(f"tests/locale_unused_keys.txt lists [{key}], which is now used")

for path in sorted((root / "locales").glob("*.txt")):
    if path.name in ("en.txt", "index.txt"):
        continue
    keys = load_keys(path)
    check_practice_labels(keys, path.name)
    have = set(keys)
    for key in english:
        if key not in have:
            failures.append(f"{path.name} missing [{key}]")
    for key in keys:
        if key not in english_set:
            failures.append(f"{path.name} extra key [{key}] not in en.txt")

if failures:
    print("\n".join(failures), file=sys.stderr)
    print(f"{len(failures)} locale key test failure(s)", file=sys.stderr)
    sys.exit(1)
print("locale key tests passed")
