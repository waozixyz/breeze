"""A recording changed during staging cannot enter a verified language pack."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import narration_current

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
        shutil.copyfile(ROOT / 'assets/practices/taichi/voice/en' / (key + '.ogg'),
                        voice / (key + '.ogg'))
    (voice / 'unused-label.ogg').write_bytes(b'unspoken label')
    (voice / 'unfinished.ogg.part').write_bytes(b'partial recording')
    assert narration_current(configuration, 'taichi', 'en', assets)
    assert not (voice / 'unused-label.ogg').exists()
    assert not (voice / 'unfinished.ogg.part').exists()
    (voice / (keys[0] + '.ogg')).write_bytes(b'changed after staging')
    assert not narration_current(configuration, 'taichi', 'en', assets)
print('Narration packs reject changed staged audio and exclude unspoken/partial recordings')
