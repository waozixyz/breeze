#!/usr/bin/env python3
"""Summarize existing narration without changing package links or media."""
import argparse
import importlib.util
import json
from pathlib import Path

import ming_narration

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


def inventory(media):
    def resolve(name):
        prefix = 'assets/practices/'
        return media / name[len(prefix):] if name.startswith(prefix) else ROOT / name

    content = json.loads((ROOT / 'apps/practice/content.json').read_text())
    rows = []
    for name, settings in content['narration'].items():
        config = json.loads((ROOT / settings['config']).read_text())
        keys = speech.narration_keys(config)
        speech.LOCALES = resolve(settings['text_directory'])
        speech.VOICE = resolve(settings['output_directory'])
        path = ROOT / settings['receipt']
        receipt = json.loads(path.read_text()) if path.is_file() else {'clips': {}}
        languages = {}
        for code in speech.locale_codes():
            selected = speech.wanted(config, [code], keys)
            languages[code] = dict(
                expected=len(keys), present=sum(speech.clip_path(code, key).is_file() for key in keys),
                current=sum(speech.current(receipt, config, code, key, text) for _, key, text in selected),
                ming=sum(receipt.get('clips', {}).get(code + '/' + key, {}).get('synthesis', {}).get('provider') == 'Ming'
                         for key in keys))
        limits = [speech.maximum_clip_seconds(config, key) for key in keys]
        rows.append(dict(practice=name, cues=len(keys), incumbent_voice=config['voice'],
                         incumbent_model=config['model'], speech_seconds=dict(min=min(limits), max=max(limits)),
                         languages=languages))
    female = sum(row['cues'] for row in rows if not row['practice'].endswith('_male'))
    return dict(schema=1, female_cues_per_locale=female,
                ming_languages=list(ming_narration.LANGUAGES), ming_female_total=female * len(ming_narration.LANGUAGES),
                unsupported_languages=[code for code in speech.locale_codes() if code not in ming_narration.LANGUAGES],
                practices=rows, timer_practices_without_narration=['whm', 'meditation', 'patterns'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inventory(args.media_root)
    data = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
        print(f"Inventory: {result['female_cues_per_locale']} female cues/locale; {result['ming_female_total']} Ming clips across seven locales.")
    else:
        print(data, end='')


if __name__ == '__main__':
    main()
