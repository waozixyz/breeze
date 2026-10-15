"""Every spoken cue in the shipped course has narration, without Node tooling."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import course_narration_keys

config = json.loads((ROOT / 'design/tai-chi/narration.json').read_text())
actual = json.loads((ROOT / config['keys_file']).read_text())
course = (ROOT / 'assets/practices/taichi/course.bin').read_bytes()
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
import re
labels = (ROOT / 'src/practices/sun_salutation/sun_salutation_labels.zi').read_text()
spoken = set(re.findall(r'"(sun_salutation_voice_[a-z_]+)"', labels))
content = json.loads((ROOT / 'apps/practice/content.json').read_text())
for name in ('sunsalutation', 'sunsalutation_male'):
    speech = json.loads((ROOT / content['narration'][name]['config']).read_text())
    lines = json.loads((ROOT / speech['keys_file']).read_text())
    assert set(lines) == spoken, f'{name}: narration lines differ from the spoken keys'
print(f'All {len(spoken)} Sun Salutation breath lines are recorded in both voices')
