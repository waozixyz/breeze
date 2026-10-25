"""Small signed Practices catalog and immutable resource packs.

The catalog is an asset of the signed Practices harness. Its exact hashes bind
each practice and language to a resource-only ZX. Lumi's guide narration is
listed separately under "guide", one pack per language, so hosts that predate
it keep reading the practice list unchanged. All blobs use the existing
inbe.practices publisher and Daochi artifact endpoint, with no new registry IDs.
"""
import json
from hashlib import sha256
from pathlib import Path
import struct
import subprocess

from practice_media import media_path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = 'assets/practices/catalog.json'
NAMES = ('whm', 'meditation', 'sunsalutation', 'patterns', 'taichi', 'astral_projection', 'workout')
GUIDE = 'guide'
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
    """Read the bounded ZX v26 resource table; never execute a bundle."""
    if data[:8] != b'ZX\0\0\x1a\0\0\0' or len(data) > MAXIMUM:
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
    if data[:8] != b'ZX\0\0\x1a\0\0\0':
        return []
    assets = bundle_assets(data)
    if CATALOG not in assets:
        return []
    catalog = json.loads(assets[CATALOG])
    packs = catalog.get('packs')
    if catalog.get('schema') != 1 or not isinstance(packs, list) or len(packs) > 96:
        raise ValueError('invalid practice catalog')
    seen = set()
    for pack in packs:
        practice = pack.get('practice')
        language = pack.get('language')
        voice = pack.get('voice', '')
        digest = pack.get('sha256')
        size = pack.get('size')
        if (practice not in NAMES or not isinstance(language, str) or
                voice not in ('', 'male') or (voice and not language) or
                (language and (len(language) != 2 or not language.isascii() or not language.islower())) or
                not isinstance(digest, str) or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest) or
                type(size) is not int or not 8 <= size <= MAXIMUM or
                (practice, language, voice) in seen or
                not isinstance(pack.get('product', ''), str)):
            raise ValueError('invalid or duplicate practice pack')
        seen.add((practice, language, voice))
    if {(name, '', '') for name in NAMES[:5]} - seen:
        raise ValueError('practice catalog lacks base content')
    guide = catalog.get('guide', [])
    if not isinstance(guide, list) or len(guide) > 32:
        raise ValueError('invalid guide narration catalog')
    languages = set()
    for pack in guide:
        language = pack.get('language')
        digest = pack.get('sha256')
        size = pack.get('size')
        if (not isinstance(language, str) or len(language) != 2 or not language.isascii() or
                not language.islower() or language in languages or
                not isinstance(digest, str) or len(digest) != 64 or
                any(c not in '0123456789abcdef' for c in digest) or
                type(size) is not int or not 8 <= size <= MAXIMUM):
            raise ValueError('invalid or duplicate guide narration pack')
        languages.add(language)
    return packs + [dict(practice=GUIDE, language=pack['language'], sha256=pack['sha256'],
                         size=pack['size']) for pack in guide]


def prepare(compiler, assets_root=None, output=None):
    assets_root = assets_root or ROOT / 'build/package-assets'
    output = output or ROOT / 'build/practice-content'
    configuration = json.loads((ROOT / 'apps/practice/content.json').read_text())
    if configuration['schema'] != 1 or tuple(configuration['practices']) != NAMES:
        raise ValueError('unsupported practice content configuration')
    speech = json.loads((ROOT / configuration['narration']['taichi']['config']).read_text())
    declared = json.loads((ROOT / speech['keys_file']).read_text())
    if course_narration_keys(media_path('assets/practices/taichi/course.tch').read_bytes()) != declared:
        raise ValueError('export Tai Chi again to update its narration inventory')
    astral = json.loads(media_path('assets/practices/astral_projection/session.json').read_text())
    astral_speech = json.loads((ROOT / configuration['narration']['astral_projection']['config']).read_text())
    if [cue['key'] for cue in astral['cues']] != astral_speech['keys']:
        raise ValueError('Astral Projection guidance and narration inventory differ')
    output.mkdir(parents=True, exist_ok=True)
    packs = []
    guide = []
    for practice in NAMES + (GUIDE,):
        # Lumi's guide has narration only, without a base pack.
        directories = [] if practice == GUIDE else [assets_root / ('practice-' + practice)]
        directories += sorted(assets_root.glob('practice-' + practice + '-voice-*'))
        for directory in directories:
            language = directory.name.split('-voice-', 1)[1] if '-voice-' in directory.name else ''
            # practice-taichi-voice-en-male holds the male recording.
            language, _, voice = language.partition('-')
            assets = directory / 'assets'
            if language and not narration_current(configuration, practice, language, assets, voice):
                print(f'{practice}/{language}{"/" + voice if voice else ""}: incomplete narration excluded from the catalog')
                continue
            assets.mkdir(parents=True, exist_ok=True)
            # Even timer-only practices have a versioned content identity.
            folder = ('voice-male/' if voice else 'voice/') + language if language else ''
            identity = assets / 'practices' / practice / folder / 'pack.json'
            identity.parent.mkdir(parents=True, exist_ok=True)
            fields = dict(schema=1, practice=practice, language=language)
            if voice:
                fields['voice'] = voice
            identity.write_text(json.dumps(fields, separators=(',', ':')) + '\n')
            path = output / (practice + ('.' + language if language else '') + ('.' + voice if voice else '') + '.zx')
            subprocess.run([str(compiler), 'bundle', '--root', str(ROOT),
                '--entry', 'content:Main', '--asset-dir', 'assets=' + str(assets),
                '-o', str(path), str(ROOT / 'apps/practice/content.zi')], check=True)
            data = path.read_bytes()
            if len(data) > min(MAXIMUM, configuration['maximum_pack_bytes']):
                raise ValueError('practice pack exceeds its size budget')
            if practice == GUIDE:
                if voice:
                    raise ValueError("Lumi's guide has one voice")
                guide.append(dict(language=language, sha256=sha256(data).hexdigest(), size=len(data)))
                continue
            pack = dict(practice=practice, language=language,
                        sha256=sha256(data).hexdigest(), size=len(data))
            if voice:
                pack['voice'] = voice
            # Paid practices name their unlock; the node gates their packs.
            if practice in configuration['products']:
                pack['product'] = configuration['products'][practice]
            packs.append(pack)
    target = assets_root / 'practices' / CATALOG
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(schema=1, packs=packs, guide=guide), separators=(',', ':')) + '\n')
    # Default practices ship inside Practices, installed until removed; other
    # small ones ship too, added from the app without a download.
    for folder, names in (('default', configuration['default']), ('shipped', configuration.get('shipped', []))):
        for practice in names:
            if practice not in NAMES or practice in configuration['products']:
                raise ValueError('unknown or paid shipped practice')
            shipped = assets_root / 'practices/assets/practices' / folder / (practice + '.zx')
            shipped.parent.mkdir(parents=True, exist_ok=True)
            shipped.write_bytes((output / (practice + '.zx')).read_bytes())
    if set(configuration['default']) & set(configuration.get('shipped', [])):
        raise ValueError('a practice is either installed by default or only shipped')
    print(f'Prepared {len(packs)} separate practice content packs and {len(guide)} guide narration packs')


def narration_current(configuration, practice, language, assets=None, voice=''):
    """Partial or stale recordings never become an advertised language pack."""
    import importlib.util
    settings = configuration['narration'].get(practice + ('_' + voice if voice else ''))
    folder = 'voice-male' if voice else 'voice'
    if not settings:
        return False
    receipt_path = ROOT / settings['receipt']
    if not receipt_path.is_file():
        return False
    spec = importlib.util.spec_from_file_location('practice_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
    speech = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(speech)
    speech.LOCALES = media_path(settings['text_directory'])
    speech.VOICE = media_path(settings['output_directory'])
    config = json.loads((ROOT / settings['config']).read_text())
    keys = speech.narration_keys(config)
    receipt = json.loads(receipt_path.read_text())
    for _, key, text in speech.wanted(config, [language], keys):
        if not speech.current(receipt, config, language, key, text):
            return False
        if assets is not None:
            staged = assets / 'practices' / practice / folder / language / (key + '.ogg')
            if not staged.is_file() or sha256(staged.read_bytes()).hexdigest() != receipt['clips'][language + '/' + key]['sha256']:
                return False
    # Package only actual spoken cues, excluding unused labels and partial files.
    if assets is not None:
        recordings = assets / 'practices' / practice / folder / language
        wanted = {key + '.ogg' for key in keys} | {'pack.json'}
        for path in recordings.iterdir():
            if path.is_file() and path.name not in wanted:
                path.unlink()
    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler', type=Path)
    parser.add_argument('--assets', type=Path, default=ROOT / 'build/package-assets')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/practice-content')
    args = parser.parse_args()
    for path in (args.assets, args.output):
        if not path.resolve().is_relative_to(ROOT / 'build') or path.resolve() == ROOT / 'build':
            parser.error('package output directories must be below the project build directory')
    prepare(args.compiler.resolve(), args.assets.resolve(), args.output.resolve())
