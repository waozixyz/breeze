"""Verify spoken-time budgets and pack certification without provider calls."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_media import media_path
import practice_content
spec = importlib.util.spec_from_file_location('speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
config = json.loads((ROOT / 'design/astral-projection/bruce-narration.json').read_text())
keys = speech.narration_keys(config)
assert len(keys) == 88 and len(set(keys)) == 88
assert set(config['maximum_clip_seconds_by_key']) == set(keys)
folder = media_path('assets/practices/astral_projection')
source = json.loads((folder / 'drafts/bruce-practices.json').read_text())
for row in source['practices']:
    session = json.loads((folder / 'sessions' / (row['id'] + '.json')).read_text())
    times = [cue['second'] for cue in session['cues']] + [session['duration']]
    for index, (cue, draft) in enumerate(zip(session['cues'], row['cues'])):
        budget = speech.maximum_clip_seconds(config, cue['key'])
        assert budget > 0 and budget + draft['quiet_after_seconds'] <= times[index + 1] - times[index]
assert speech.maximum_clip_seconds({}, 'cue') == 40
for bad in (-1, 0, 121, float('nan'), True, '60'):
    try:
        speech.maximum_clip_seconds({'maximum_clip_seconds': bad}, 'cue')
    except ValueError:
        pass
    else:
        raise AssertionError(f'Invalid speech bound accepted: {bad}')

output = ROOT / 'build/astral-narration-test'
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='fixture-', dir=output) as directory:
    directory = Path(directory)
    target = directory / 'spoken.ogg'
    work_paths = []

    def encode(_config, _pcm, work):
        work_paths.append(work)
        assert work.is_relative_to(ROOT / 'backup/narration/tmp')
        clip = work / 'spoken.ogg'
        clip.write_bytes(b'local speech fixture')
        return clip

    with patch.object(speech, 'speak', return_value=(b'pcm', 'local-test')) as speak, \
            patch.object(speech, 'encode', side_effect=encode), \
            patch.object(speech, 'seconds', return_value=45.0), \
            patch.object(speech, 'transcribe', return_value='A complete spoken cue.'), \
            patch.object(speech, 'clip_path', return_value=target), \
            patch.object(speech, 'packaged_path', return_value='fixture/spoken.ogg'):
        accepted = speech.generate(config, 'unused-local-key', 'en', keys[0], 'A complete spoken cue.')
        assert accepted['seconds'] == 45 and accepted['match'] == 1 and target.exists()
        assert speak.call_count == 1
        assert all(not path.exists() for path in work_paths), 'Temporary audio retained after generation'
        target.unlink()
        legacy = dict(config)
        legacy.pop('maximum_clip_seconds')
        legacy.pop('maximum_clip_seconds_by_key')
        try:
            speech.generate(legacy, 'unused-local-key', 'en', keys[0], 'A complete spoken cue.')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Legacy 40-second limit accepted 45 seconds')
        assert not target.exists()

# Advertise no language pack until every new cue has a valid recording and
# matching transcription receipt. No existing 20-cue receipt certifies it.
configuration = json.loads((ROOT / 'apps/practice/content.json').read_text())
if not (ROOT / configuration['narration']['astral_projection_bruce']['receipt']).exists():
    assert not practice_content.narration_current(configuration, 'astral_projection', 'en')
print('88 cue budgets preserve quiet time; 45-second generation, default limit, local staging and incomplete-pack rejection passed')

# Exercise staging independently of provider/transcription verification:
# a certified receipt still needs every packed byte, and legacy files survive.
from hashlib import sha256
from types import SimpleNamespace
with tempfile.TemporaryDirectory(prefix='pack-', dir=output) as directory:
    directory = Path(directory)
    assets = directory / 'assets'
    recordings = assets / 'practices/astral_projection/voice/en'
    recordings.mkdir(parents=True)
    payload = b'local package fixture'
    receipt = directory / 'receipt.json'
    receipt.write_text(json.dumps({'clips': {'en/' + key: {'sha256': sha256(payload).hexdigest()} for key in keys}}))
    configured = json.loads(json.dumps(configuration))
    configured['narration']['astral_projection_bruce']['receipt'] = str(receipt)
    for key in keys + config['preserved_keys']:
        (recordings / (key + '.ogg')).write_bytes(payload)
    (recordings / 'unused.ogg').write_bytes(payload)
    fake = SimpleNamespace(narration_keys=lambda cfg: keys,
                           wanted=lambda cfg, codes, selected: [('en', key, 'fixture') for key in selected],
                           current=lambda *args: True)
    loader = SimpleNamespace(exec_module=lambda module: None)
    with patch('importlib.util.spec_from_file_location', return_value=SimpleNamespace(loader=loader)), \
            patch('importlib.util.module_from_spec', return_value=fake):
        missing = recordings / (keys[-1] + '.ogg')
        missing.unlink()
        assert not practice_content.narration_current(configured, 'astral_projection', 'en', assets)
        missing.write_bytes(b'wrong byte content')
        assert not practice_content.narration_current(configured, 'astral_projection', 'en', assets)
        missing.write_bytes(payload)
        assert practice_content.narration_current(configured, 'astral_projection', 'en', assets)
    assert not (recordings / 'unused.ogg').exists()
    assert all((recordings / (key + '.ogg')).exists() for key in config['preserved_keys'])
print('Pack staging rejects missing/mismatched cues and retains all 20 legacy recording paths')
