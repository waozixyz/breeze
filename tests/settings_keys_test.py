#!/usr/bin/env python3
"""The settings save, load, and import key lists cannot drift apart.

Every literal key the app saves (save_setting_int, storage_set_setting_text,
SettingsStoreInt/Text) must be loaded (load_bool_setting, load_clamped_setting,
SettingsCacheInt/CopyText/Contains, storage_get_setting_text), and every key a
backup can import (the table in src/storage/import.zi) must be saved, written
through a helper listed below, or be a legacy key that loading still migrates.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
settings = (root / "src/app/app_settings.zi").read_text(encoding="utf-8")
application = (root / "src/app/application.zi").read_text(encoding="utf-8")
importer = (root / "src/storage/import.zi").read_text(encoding="utf-8")
failures = []

# Keys written through helpers whose literals live outside the direct calls.
HELPER_SAVED = set("""
audio_cue_breath_in audio_cue_breath_out audio_cue_bell audio_custom_sound_count
audio_custom_music_count break_micro_enabled break_micro_limit
break_micro_duration break_micro_postpone break_micro_max_prompts
break_micro_show_skip break_micro_show_postpone break_rest_enabled
break_rest_limit break_rest_duration break_rest_postpone break_rest_max_prompts
break_rest_show_skip break_rest_show_postpone break_daily_enabled
break_daily_limit break_daily_postpone break_daily_max_prompts
break_daily_show_skip break_daily_show_postpone practice_music_track_wim_hof
practice_music_track_meditation practice_music_track_sun_salutation
""".split())
# Keys saved with formatted indices; their loaders use the same shape.
DERIVED = set()
# Older backups can still import these; loading migrates their values.
LEGACY_IMPORTED = {"glow_effects"}


def first_literal_after_call(text, name):
    """The first quoted literal within 2 KiB after each `name(`, across lines."""
    found = set()
    for match in re.finditer(re.escape(name) + r"\(", text):
        window = text[match.end():match.end() + 2048]
        literal = re.search(r'"([^"]*)"', window)
        if literal:
            found.add(literal.group(1))
    return found


def literal_first_argument(text, name):
    """Literals passed as the first argument; variable keys are ignored."""
    return set(re.findall(re.escape(name) + r'\(\s*"([^"]*)"', text))


saved = (first_literal_after_call(settings, "save_setting_int") |
         first_literal_after_call(settings, "storage_set_setting_text") |
         literal_first_argument(settings, "SettingsStoreInt") |
         literal_first_argument(settings, "SettingsStoreText"))
loaded = (first_literal_after_call(settings, "load_bool_setting") |
          first_literal_after_call(settings, "load_clamped_setting") |
          first_literal_after_call(settings, "settings_cache_get_int") |
          first_literal_after_call(settings, "settings_cache_get") |
          literal_first_argument(settings, "SettingsCacheInt") |
          literal_first_argument(settings, "SettingsCacheCopyText") |
          literal_first_argument(settings, "SettingsCacheContains") |
          first_literal_after_call(application, "storage_get_setting_text"))

if "setting_key_importable ::" not in importer or "return setting_key_importable(key)" in importer:
    failures.append("the import key policy is missing or recursive")
table = re.search(r"keys: \[(\d+)\]string = \.\[(.*?)\]", importer, re.S)
if table is None:
    failures.append("the import key table was not found")
    imported = set()
else:
    imported = set(re.findall(r'"([^"]*)"', table.group(2)))
    if int(table.group(1)) != len(re.findall(r'"([^"]*)"', table.group(2))):
        failures.append(f"the import key table declares {table.group(1)} entries "
                        f"but lists {len(re.findall(chr(34) + '([^' + chr(34) + ']*)' + chr(34), table.group(2)))}")

for key in sorted(saved - loaded - DERIVED):
    failures.append(f"setting [{key}] is saved but never loaded")
for key in sorted(imported):
    if (key not in saved and key not in HELPER_SAVED and
            not (key in LEGACY_IMPORTED and key in loaded)):
        failures.append(f"importable setting [{key}] is never saved")

print(f"saved={len(saved)} loaded={len(loaded)} imported={len(imported)}")
if failures:
    print("\n".join(failures), file=sys.stderr)
    print(f"{len(failures)} settings key test failure(s)", file=sys.stderr)
    sys.exit(1)
print("settings key tests passed")
