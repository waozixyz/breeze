"""A recording changed during staging cannot enter a verified language pack."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import practice_content
from practice_content import narration_current
from practice_media import media_path

spec = importlib.util.spec_from_file_location('speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
configuration = json.loads((ROOT / 'apps/practice/content.json').read_text())
config = json.loads((ROOT / 'design/tai-chi/narration.json').read_text())
direction = 'Keep the shoulders low, soften both knees, then place the left heel down and shift your weight slowly.'
assert speech.match(direction, direction.replace('left', 'right')) > config['minimum_match']
assert speech.verified_match(config, 'en', direction, direction.replace('left', 'right')) == 0
ordered = direction + ' Keep that heel grounded and move the right hand gently toward the center.'
swapped = ordered.replace('left', 'SIDE').replace('right', 'left').replace('SIDE', 'right')
assert speech.match(ordered, swapped) > config['minimum_match']
assert speech.verified_match(config, 'en', ordered, swapped) == 0
assert speech.verified_match(config, 'en', 'Hold for 16 seconds', 'Hold for 17 seconds') == 0
assert speech.verified_match(config, 'ja', '右脚に腰を落とす', '右足に腰を落とす') == 1
assert speech.verified_match(config, 'ja', '右足に腰を落とす', '右足に腰を落とす') == 1
assert speech.verified_match(config, 'ja', '片脚で、すっと静かに立つ', '片足でスッと静かに立つ') == 1
keys = speech.narration_keys(config)
with tempfile.TemporaryDirectory(prefix='narration-snapshot-', dir=ROOT / 'build') as temporary:
    assets = Path(temporary)
    voice = assets / 'practices/taichi/voice/en'
    voice.mkdir(parents=True)
    for key in keys:
        shutil.copyfile(media_path('assets/practices/taichi/voice/en') / (key + '.ogg'),
                        voice / (key + '.ogg'))
    (voice / 'unused-label.ogg').write_bytes(b'unspoken label')
    (voice / 'unfinished.ogg.part').write_bytes(b'partial recording')
    assert narration_current(configuration, 'taichi', 'en', assets)
    assert not (voice / 'unused-label.ogg').exists()
    assert not (voice / 'unfinished.ogg.part').exists()
    (voice / (keys[0] + '.ogg')).write_bytes(b'changed after staging')
    assert not narration_current(configuration, 'taichi', 'en', assets)
    # An incomplete or invalid alternative must leave the existing voice intact.
    media = assets / 'media'
    index = media / 'jungle-narration.json'
    target = assets / 'practice-sunsalutation-voice-en/assets/practices/sunsalutation/voice/en'
    target.mkdir(parents=True)
    prior = target / 'old.ogg'
    prior.write_bytes(b'previous verified recording')
    audio = (voice / (keys[1] + '.ogg')).read_bytes()
    rows = [('en', 'first_cue', 'First instruction.'), ('en', 'second_cue', 'Second instruction.')]
    receipt = dict(format='practices-jungle-narration-1',
                   speaker_tensor_sha256=practice_content.JUNGLE_TENSOR, clips={})
    for code, key, text in rows:
        name = f'sunsalutation/voice-jungle/{code}/{key}.ogg'
        recording = media / name
        recording.parent.mkdir(parents=True, exist_ok=True)
        recording.write_bytes(audio)
        request = dict(practice_content.JUNGLE_REQUEST, language=code, text=text, seed=20261108)
        identity = json.dumps(request, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        receipt['clips'][name] = dict(request=request, request_sha256=sha256(identity.encode()).hexdigest(),
                                      sha256=sha256(audio).hexdigest(), text_sha256=sha256(text.encode()).hexdigest(),
                                      seconds=1.0, frames_48000=48000, practices={'sunsalutation': {'cue': key}})
    last_name = f'sunsalutation/voice-jungle/en/{rows[-1][1]}.ogg'
    plan = ('sunsalutation', {}, speech, {}, [key for _, key, _ in rows])
    lookup = lambda path: media / path.removeprefix('assets/practices/')
    with (patch.object(practice_content, 'media_path', side_effect=lookup),
          patch.object(practice_content, 'narration_inventory', return_value=plan),
          patch.object(speech, 'wanted', return_value=rows)):
        last_receipt = receipt['clips'].pop(last_name)
        index.write_text(json.dumps(receipt))
        assert practice_content.stage_jungle_narration(configuration, assets, {'en'}) == set()
        assert prior.is_file() and not (target / 'first_cue.ogg').exists()
        receipt['clips'][last_name] = last_receipt
        index.write_text(json.dumps(receipt))
        (media / last_name).write_bytes(b'corrupted clip')
        assert practice_content.stage_jungle_narration(configuration, assets, {'en'}) == set()
        assert prior.is_file() and not (target / 'first_cue.ogg').exists()
        (media / last_name).write_bytes(audio)
        assert practice_content.stage_jungle_narration(configuration, assets, {'en'}) == {('sunsalutation', 'en')}
        assert sorted(p.name for p in target.iterdir()) == ['first_cue.ogg', 'second_cue.ogg']
        assert (target / 'second_cue.ogg').read_bytes() == audio

    # The original and selected Astral lessons share one voice pack but each
    # source has its own cue identity and timing limits.
    receipt['clips'].clear()
    current = 'astral_projection_bruce'
    original = 'astral_projection'
    plans = {current: (current, {}, speech, {}, ['selected_cue']),
             original: (original, {}, speech, {}, ['original_cue'])}
    target = assets / 'practice-astral_projection-voice-en/assets/practices/astral_projection/voice/en'
    target.mkdir(parents=True)
    old = target / 'old.ogg'
    old.write_bytes(b'previous verified recording')
    for inventory, _, _, _, cues in plans.values():
        key = cues[0]
        name = f'{original}/voice-jungle/en/{key}.ogg'
        recording = media / name
        recording.parent.mkdir(parents=True, exist_ok=True)
        recording.write_bytes(audio)
        request = dict(practice_content.JUNGLE_REQUEST, language='en', text=key, seed=20261108)
        identity = json.dumps(request, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        receipt['clips'][name] = dict(request=request, request_sha256=sha256(identity.encode()).hexdigest(),
                                      sha256=sha256(audio).hexdigest(), text_sha256=sha256(key.encode()).hexdigest(),
                                      seconds=1.0, frames_48000=48000, practices={inventory: {'cue': key}})
    last_name = f'{original}/voice-jungle/en/original_cue.ogg'

    def astral_inventory(_configuration, practice, *, legacy_astral=False):
        assert practice == original
        return plans[original if legacy_astral else current]

    def astral_wanted(_config, languages, keys):
        return [(language, key, key) for language in languages for key in keys]

    with (patch.object(practice_content, 'media_path', side_effect=lookup),
          patch.object(practice_content, 'narration_inventory', side_effect=astral_inventory),
          patch.object(speech, 'wanted', side_effect=astral_wanted)):
        last_receipt = receipt['clips'].pop(last_name)
        index.write_text(json.dumps(receipt))
        assert practice_content.stage_jungle_narration(configuration, assets, {'en'}) == set()
        assert old.is_file() and not (target / 'selected_cue.ogg').exists()
        receipt['clips'][last_name] = last_receipt
        index.write_text(json.dumps(receipt))
        assert practice_content.stage_jungle_narration(configuration, assets, {'en'}) == {(original, 'en')}
        assert sorted(p.name for p in target.iterdir()) == ['original_cue.ogg', 'selected_cue.ogg']

print('Narration packs reject changed audio and stage complete verified alternatives without mixing voices')
