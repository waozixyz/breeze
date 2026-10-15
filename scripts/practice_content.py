"""Small signed Practices catalog and immutable resource packs.

The catalog is an asset of the signed Practices harness. Its exact hashes bind
each practice and language to a resource-only ZIB. All blobs use the existing
inbe.practices publisher and Daochi artifact endpoint, with no new registry IDs.
"""
import json
from hashlib import sha256
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CATALOG = 'assets/practices/catalog.json'
NAMES = ('whm', 'meditation', 'sunsalutation', 'patterns', 'taichi')
MAXIMUM = 64 * 1024 * 1024


def bundle_assets(data):
    """Read the bounded ZIB v26 resource table; never execute a bundle."""
    if data[:8] != b'ZIB\0\x1a\0\0\0' or len(data) > MAXIMUM:
        raise ValueError('unsupported resource bundle')
    at = 8

    def take(size):
        nonlocal at
        if size < 0 or at + size > len(data):
            raise ValueError('truncated resource bundle')
        value = data[at:at + size]
        at += size
        return value

    def number():
        return struct.unpack('<I', take(4))[0]

    def text():
        return take(number())

    text(); text()
    for _ in range(number()):
        text(); text()
    for _ in range(number()):
        for _ in range(7):
            text()
        take(8); text(); take(4)
    for _ in range(number()):
        for _ in range(3):
            text()
    take(number())
    count = number()
    if count > 10000:
        raise ValueError('too many resource assets')
    result = {}
    for _ in range(count):
        path = text().decode('utf-8')
        if path in result:
            raise ValueError('duplicate resource path')
        result[path] = take(number())
    if at != len(data):
        raise ValueError('trailing resource bundle bytes')
    return result


def catalog_from_bundle(data):
    # Older releases have no content catalog and remain installable.
    if data[:8] != b'ZIB\0\x1a\0\0\0':
        return []
    assets = bundle_assets(data)
    if CATALOG not in assets:
        return []
    catalog = json.loads(assets[CATALOG])
    packs = catalog.get('packs')
    if catalog.get('schema') != 1 or not isinstance(packs, list) or len(packs) > 65:
        raise ValueError('invalid practice catalog')
    seen = set()
    for pack in packs:
        practice = pack.get('practice')
        language = pack.get('language')
        digest = pack.get('sha256')
        size = pack.get('size')
        if (practice not in NAMES or not isinstance(language, str) or
                (language and (len(language) != 2 or not language.isascii() or not language.islower())) or
                not isinstance(digest, str) or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest) or
                type(size) is not int or not 8 <= size <= MAXIMUM or
                (practice, language) in seen):
            raise ValueError('invalid or duplicate practice pack')
        seen.add((practice, language))
    if {(name, '') for name in NAMES} - seen:
        raise ValueError('practice catalog lacks base content')
    return packs


def prepare(compiler):
    configuration = json.loads((ROOT / 'apps/practice/content.json').read_text())
    if configuration['schema'] != 1 or tuple(configuration['practices']) != NAMES:
        raise ValueError('unsupported practice content configuration')
    output = ROOT / 'build/practice-content'
    output.mkdir(parents=True, exist_ok=True)
    packs = []
    for practice in NAMES:
        directories = [ROOT / ('build/package-assets/practice-' + practice)]
        directories += sorted((ROOT / 'build/package-assets').glob('practice-' + practice + '-voice-*'))
        for directory in directories:
            language = directory.name.split('-voice-', 1)[1] if '-voice-' in directory.name else ''
            if language and not narration_current(configuration, practice, language):
                print(f'{practice}/{language}: incomplete narration excluded from the catalog')
                continue
            assets = directory / 'assets'
            assets.mkdir(parents=True, exist_ok=True)
            # Even timer-only practices have a versioned content identity.
            identity = assets / 'practices' / practice / ('voice/' + language if language else '') / 'pack.json'
            identity.parent.mkdir(parents=True, exist_ok=True)
            identity.write_text(json.dumps(dict(schema=1, practice=practice, language=language),
                                           separators=(',', ':')) + '\n')
            path = output / (practice + ('.' + language if language else '') + '.zib')
            subprocess.run([str(compiler), 'bundle', '--root', str(ROOT),
                '--entry', 'content:Main', '--asset-dir', 'assets=' + str(assets),
                '-o', str(path), str(ROOT / 'apps/practice/content.zi')], check=True)
            data = path.read_bytes()
            if len(data) > min(MAXIMUM, configuration['maximum_pack_bytes']):
                raise ValueError('practice pack exceeds its size budget')
            packs.append(dict(practice=practice, language=language,
                              sha256=sha256(data).hexdigest(), size=len(data)))
    target = ROOT / 'build/package-assets/practices' / CATALOG
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(schema=1, packs=packs), separators=(',', ':')) + '\n')
    print(f'Prepared {len(packs)} separate practice content packs')


def narration_current(configuration, practice, language):
    """Partial or stale recordings never become an advertised language pack."""
    import importlib.util
    settings = configuration['narration'].get(practice)
    if not settings:
        return False
    receipt_path = ROOT / settings['receipt']
    if not receipt_path.is_file():
        return False
    spec = importlib.util.spec_from_file_location('practice_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
    speech = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(speech)
    speech.LOCALES = ROOT / settings['text_directory']
    speech.VOICE = ROOT / settings['output_directory']
    config = json.loads((ROOT / settings['config']).read_text())
    keys = sorted(speech.entries(ROOT / config['keys_from']))
    receipt = json.loads(receipt_path.read_text())
    return all(speech.current(receipt, config, language, key, text)
               for _, key, text in speech.wanted(config, [language], keys))


if __name__ == '__main__':
    import sys
    prepare(Path(sys.argv[1]).resolve())
