"""Every spoken cue in the shipped course has narration, without Node tooling."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import course_narration_keys
from practice_media import media_path

config = json.loads((ROOT / 'design/tai-chi/narration.json').read_text())
actual = json.loads((ROOT / config['keys_file']).read_text())
course = media_path('assets/practices/taichi/course.tch').read_bytes()
expected = course_narration_keys(course)
assert len(expected) > 200
assert actual == expected, 'Export Tai Chi after changing spoken cues'
for broken in (b'TCH3' + course[4:], course[:-1], b'TCH2\xff\xff\xff\xff'):
    try:
        course_narration_keys(broken)
    except ValueError:
        continue
    raise AssertionError('Malformed course accepted')
print(f'All {len(expected)} shipped course narration lines are covered; unspoken labels are excluded')

# Sun Salutation speaks one line per breath, each recorded in every voice.
import importlib.util
import re
labels = (ROOT / 'src/practices/sun_salutation/sun_salutation_labels.zi').read_text()
spoken = set(re.findall(r'"(sun_salutation_voice_[a-z0-9_]+)"', labels))
content = json.loads((ROOT / 'apps/practice/content.json').read_text())
rules = (ROOT / 'src/practices/sun_salutation/sun_salutation_rules.zi').read_text()
breath = int(re.search(r'SUN_SALUTATION_DEFAULT_END_SECONDS :: (\d+)', rules)[1])
speech_spec = importlib.util.spec_from_file_location('narration', ROOT / 'scripts/generate-lumi-guide-narration.py')
narration = importlib.util.module_from_spec(speech_spec)
speech_spec.loader.exec_module(narration)
entries, text_hash = narration.entries, narration.text_hash
codes = narration.locale_codes()
assert len(codes) >= 12
for name in ('sunsalutation', 'sunsalutation_male'):
    speech = json.loads((ROOT / content['narration'][name]['config']).read_text())
    lines = json.loads((ROOT / speech['keys_file']).read_text())
    assert set(lines) == spoken, f'{name}: narration lines differ from the spoken keys'
    # Each line is written in every language, recorded from that text, and
    # fits the shortest default breath with the player's 0.2 s margin.
    receipt = json.loads((ROOT / content['narration'][name]['receipt']).read_text())['clips']
    for code in codes:
        texts = entries(ROOT / content['narration'][name]['text_directory'] / f'{code}.txt')
        for key in spoken:
            text = texts.get(key, '').strip()
            assert text, f'{code}/{key}: no {name} narration text'
            clip = receipt.get(f'{code}/{key}')
            assert clip and clip['text_sha256'] == text_hash(speech, text), f'{code}/{key}: {name} recording is missing or older than its text'
            assert media_path(clip['file']).is_file(), f'{code}/{key}: {name} clip file is missing'
            assert clip['seconds'] + 0.2 <= breath, f'{code}/{key}: {name} line is {clip["seconds"]} s, longer than a {breath} s breath'
print(f'All {len(spoken)} Sun Salutation lines are recorded in {len(codes)} languages and both voices, each within a {breath} s breath')
