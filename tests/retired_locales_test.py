"""Only the ten currently supported languages enter app-owned resources."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import whisper_narration
import ming_narration
import practice_content

SUPPORTED = {'en', 'es', 'cs', 'de', 'fr', 'ru', 'ja', 'ko', 'zh', 'pt'}
RETIRED = {'id', 'it'}
index = [row.split('|', 1)[0] for row in (ROOT / 'locales/index.txt').read_text().splitlines() if '|' in row]
assert len(index) == 10 and set(index) == SUPPORTED
assert {path.stem for path in (ROOT / 'locales').glob('*.txt')} == SUPPORTED | {'index'}
assert set(whisper_narration.LANGUAGES) == SUPPORTED
assert set(ming_narration.LANGUAGES) == SUPPORTED - {'ru', 'cs', 'pt'}
for catalog in (ROOT / 'apps').glob('*/achievements.json'):
    actual = {path.stem for path in (catalog.parent / 'achievement-locales').glob('*.json')}
    assert actual == SUPPORTED, (catalog, actual)
for code in RETIRED:
    for folder in ('locales/changelog', 'design/tai-chi/text', 'design/sun-salutation/narration/text'):
        assert not any((ROOT / folder).glob(code + '.*'))
for folder in ('droid/app/src/main/res/values-in', 'droid/app/src/main/res/values-it',
               'fastlane/metadata/android/id', 'fastlane/metadata/android/it-IT'):
    assert not any(path.is_file() for path in (ROOT / folder).rglob('*')), folder
content = json.loads((ROOT / 'apps/practice/content.json').read_text())
for code in RETIRED:
    assert not practice_content.narration_current(content, 'sunsalutation', code)
    for folder in ('voice', 'voice-male'):
        assert practice_content.resource_language(f'assets/practices/taichi/{folder}/{code}/cue.ogg') == code
    assert practice_content.resource_language(f'assets/practices/astral_projection/text/{code}.txt') == code
for settings in content['narration'].values():
    path = ROOT / settings['receipt']
    if path.exists():
        clips = json.loads(path.read_text()).get('clips', {})
        assert all(name.split('/', 1)[0] in SUPPORTED for name in clips), path
assert (ROOT / 'droid/app/src/main/res/values-pt/strings.xml').is_file()
assert (ROOT / 'fastlane/metadata/android/pt-BR/full_description.txt').is_file()
print('Ten UI/ASR locales, seven Ming locales, app translations and narration inventories agree; retired assets excluded')
