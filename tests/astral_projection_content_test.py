"""The downloadable session, text and narration inventory must stay together."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_media import media_path
spec = importlib.util.spec_from_file_location(
    'speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
folder = media_path('assets/practices/astral_projection')
course = json.loads((folder / 'session.json').read_text())
config = json.loads((ROOT / 'design/astral-projection/narration.json').read_text())
keys = [cue['key'] for cue in course['cues']]
assert set(keys) <= set(speech.narration_keys(config))
assert course['schema'] == 1 and course['duration'] == 2400
assert course['cues'][0]['second'] == 0
times = [cue['second'] for cue in course['cues']] + [course['duration']]
assert all(a < b for a, b in zip(times, times[1:]))
assert times[-1] - times[-2] >= 60, 'Allow time for the final spoken cue'
english = speech.entries(folder / 'text/en.txt')
for code in speech.locale_codes():
    values = speech.entries(folder / 'text' / (code + '.txt'))
    assert set(keys) <= set(values), code
    assert all(values[key].strip() for key in keys), code
    if code != 'en':
        assert all(values[key] != english[key] for key in keys), code

# Already verified recordings must fit their cue, including the final line.
receipt_path = ROOT / 'design/astral-projection/narration-receipt.json'
if receipt_path.is_file():
    receipt = json.loads(receipt_path.read_text())
    for name, clip in receipt.get('clips', {}).items():
        code, key = name.split('/')
        index = keys.index(key)
        assert clip['seconds'] + 1 < times[index + 1] - times[index], name
catalogue_path = folder / 'catalogue.json'
if catalogue_path.exists():
    catalogue = json.loads(catalogue_path.read_text())
    expected = {
        'bruce_foundation_touch': (1200, 10),
        'bruce_full_body_current': (1500, 13),
        'bruce_elevator_trance': (1800, 15),
        'bruce_spin_loosening': (1800, 15),
        'bruce_rope_exit': (2400, 20),
        'bruce_roll_out_exit': (1800, 15),
    }
    assert catalogue['schema'] == 1
    assert [row['id'] for row in catalogue['practices']] == list(expected)
    new_keys = []
    metadata = []
    sessions = []
    for row in catalogue['practices']:
        duration, count = expected[row['id']]
        session = json.loads((folder / 'sessions' / (row['id'] + '.json')).read_text())
        assert session['schema'] == 1
        assert row['duration'] == session['duration'] == duration
        assert len(session['cues']) == count
        cue_times = [cue['second'] for cue in session['cues']] + [duration]
        assert cue_times[0] == 0 and all(a < b for a, b in zip(cue_times, cue_times[1:]))
        sessions.append((session, cue_times))
        new_keys.extend(cue['key'] for cue in session['cues'])
        metadata.extend(row[key] for key in ('title_key', 'description_key', 'guide_key'))
    assert len(new_keys) == len(set(new_keys)) == 88
    assert not set(new_keys) & set(keys)
    assert all(key.startswith('astral_text_') and len(key) < 64 and
               all(c.islower() or c.isdigit() or c == '_' for c in key) for key in new_keys)
    selected_config = json.loads((ROOT / "design/astral-projection/bruce-narration.json").read_text())
    assert speech.narration_keys(selected_config) == new_keys
    assert selected_config["preserved_keys"] == keys
    missing = []
    for code in speech.locale_codes():
        values = speech.entries(folder / 'text' / (code + '.txt'))
        for key in new_keys + metadata:
            assert values.get(key, '').strip(), (code, key)
            if code != 'en':
                assert values[key] != english[key], (code, key)
        for row in catalogue['practices']:
            assert '\n\n' in values[row['guide_key']], (code, row['id'], 'readable guide paragraphs')
        for session, cue_times in sessions:
            for index, cue in enumerate(session['cues']):
                clip = folder / 'voice' / code / (cue['key'] + '.ogg')
                if not clip.exists():
                    missing.append(f"{code}/{cue['key']}")
                    continue
                seconds = speech.seconds(clip)
                assert 0 < seconds + 1 < cue_times[index + 1] - cue_times[index], (code, cue['key'], seconds)
    if '--require-narration' in sys.argv:
        assert not missing, f'{len(missing)} new narration clips missing; first: {missing[:3]}'
    print(f'Six finite sessions, 88 unique cues, 18 metadata entries and all {len(speech.locale_codes())} translations passed; '
          f'{len(missing)} narration clips pending')
else:
    assert '--require-narration' not in sys.argv, 'New six-practice catalogue is missing'
    print(f'Legacy package: 20 cues and {len(speech.locale_codes())} translations passed; new six-practice media not present')
