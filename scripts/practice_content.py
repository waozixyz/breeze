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


def course_narration_keys(data):
    """Read spoken cue references from the same bounded TCH2 data as the app."""
    if data[:4] != b'TCH2' or len(data) > MAXIMUM:
        raise ValueError('unsupported Tai Chi course')
    at = 4

    def take(size):
        nonlocal at
        if size < 0 or at + size > len(data):
            raise ValueError('truncated Tai Chi course')
        value = data[at:at + size]
        at += size
        return value

    def unsigned():
        return struct.unpack('<I', take(4))[0]

    def signed():
        return struct.unpack('<i', take(4))[0]

    def count(maximum):
        value = unsigned()
        if value > maximum:
            raise ValueError('Tai Chi course section exceeds its bound')
        return value

    strings = [take(struct.unpack('<H', take(2))[0]).decode('utf-8')
               for _ in range(count(10000))]
    sets = []
    # TCH2 stores 49 pose channels, 26 rig fields and 96 bytes per image.
    for _ in range(count(256)):
        keys = []
        for _ in range(count(50000)):
            take(4)
            keys.append(signed())
            take(212)
        sets.append(keys)
    for _ in range(count(16)):
        take(8 + 26 * 4)
        take(count(1024) * 96)
    spoken = set()

    def cue(index):
        if index < 0:
            return
        if index >= len(strings) or not strings[index].startswith('tai_chi_text_'):
            raise ValueError('invalid Tai Chi spoken cue')
        spoken.add(strings[index])

    for _ in range(count(64)):
        take(4)
        for _ in range(count(256)):
            take(12)
            for _ in range(count(1024)):
                take(12)
                flags = take(5)
                first, last = signed(), signed()
                take(12)
                marks = [(signed(), take(8)) for _ in range(count(1024))]
                if flags[4]:
                    if flags[3] == 1 and 0 <= first < len(sets):
                        keys = sets[first]
                    elif flags[3] == 0 and sets and 0 <= first <= last < len(sets[0]):
                        keys = sets[0][first:last + 1]
                    else:
                        raise ValueError('invalid Tai Chi narrated timeline')
                    for index in keys:
                        cue(index)
                else:
                    for index, _ in marks:
                        cue(index)
    if at != len(data):
        raise ValueError('trailing Tai Chi course bytes')
    return sorted(spoken)


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
    speech = json.loads((ROOT / configuration['narration']['taichi']['config']).read_text())
    declared = json.loads((ROOT / speech['keys_file']).read_text())
    if course_narration_keys((ROOT / 'assets/practices/taichi/course.bin').read_bytes()) != declared:
        raise ValueError('export Tai Chi again to update its narration inventory')
    output = ROOT / 'build/practice-content'
    output.mkdir(parents=True, exist_ok=True)
    packs = []
    for practice in NAMES:
        directories = [ROOT / ('build/package-assets/practice-' + practice)]
        directories += sorted((ROOT / 'build/package-assets').glob('practice-' + practice + '-voice-*'))
        for directory in directories:
            language = directory.name.split('-voice-', 1)[1] if '-voice-' in directory.name else ''
            assets = directory / 'assets'
            if language and not narration_current(configuration, practice, language, assets):
                print(f'{practice}/{language}: incomplete narration excluded from the catalog')
                continue
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
    # Default practices ship inside Practices, installed until removed.
    for practice in configuration['default']:
        if practice not in NAMES:
            raise ValueError('unknown default practice')
        shipped = ROOT / 'build/package-assets/practices/assets/practices/default' / (practice + '.zib')
        shipped.parent.mkdir(parents=True, exist_ok=True)
        shipped.write_bytes((output / (practice + '.zib')).read_bytes())
    print(f'Prepared {len(packs)} separate practice content packs')


def narration_current(configuration, practice, language, assets=None):
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
    keys = speech.narration_keys(config)
    receipt = json.loads(receipt_path.read_text())
    for _, key, text in speech.wanted(config, [language], keys):
        if not speech.current(receipt, config, language, key, text):
            return False
        if assets is not None:
            staged = assets / 'practices' / practice / 'voice' / language / (key + '.ogg')
            if not staged.is_file() or sha256(staged.read_bytes()).hexdigest() != receipt['clips'][language + '/' + key]['sha256']:
                return False
    # Package only actual spoken cues, excluding unused labels and partial files.
    if assets is not None:
        voice = assets / 'practices' / practice / 'voice' / language
        wanted = {key + '.ogg' for key in keys} | {'pack.json'}
        for path in voice.iterdir():
            if path.is_file() and path.name not in wanted:
                path.unlink()
    return True


if __name__ == '__main__':
    import sys
    prepare(Path(sys.argv[1]).resolve())
