"""The downloadable session, text and narration inventory must stay together."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
folder = ROOT / 'assets/practices/astral_projection'
course = json.loads((folder / 'session.json').read_text())
config = json.loads((ROOT / 'design/astral-projection/narration.json').read_text())
keys = [cue['key'] for cue in course['cues']]
assert keys == speech.narration_keys(config)
assert course['schema'] == 1 and course['duration'] == 2400
assert course['cues'][0]['second'] == 0
times = [cue['second'] for cue in course['cues']] + [course['duration']]
assert all(a < b for a, b in zip(times, times[1:]))
assert times[-1] - times[-2] >= 60, 'Allow time for the gentle return'
english = speech.entries(folder / 'text/en.txt')
for code in speech.locale_codes():
    values = speech.entries(folder / 'text' / (code + '.txt'))
    assert set(values) == set(keys), code
    assert all(values[key].strip() for key in keys), code
    if code != 'en':
        assert all(values[key] != english[key] for key in keys), code

# Already verified recordings must fit their cue, including the final return.
receipt_path = ROOT / 'design/astral-projection/narration-receipt.json'
if receipt_path.is_file():
    receipt = json.loads(receipt_path.read_text())
    for name, clip in receipt.get('clips', {}).items():
        code, key = name.split('/')
        index = keys.index(key)
        assert clip['seconds'] + 1 < times[index + 1] - times[index], name
print(f'All {len(keys)} guidance cues of the 40-minute session have complete translations in all 12 locales')
