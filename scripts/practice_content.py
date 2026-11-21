"""Small signed Practices catalog and immutable resource packs.

The catalog is an asset of the signed Practices harness. Its exact hashes bind
each practice and language to a resource-only ZX. Lumi's guide narration is
listed separately under "guide", one pack per language, so hosts that predate
it keep reading the practice list unchanged. All blobs use the existing
inbe.practices publisher and Mesh artifact endpoint, with no new registry IDs.
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
JUNGLE_LANGUAGES = frozenset(('en', 'de', 'es', 'fr', 'zh', 'ja', 'ko'))
JUNGLE_TENSOR = '5666d1a4f3f75d48d6589b834fa3a27607c250daabc76ec750890e5db3626d5e'
JUNGLE_REQUEST = {
    'model': 'inclusionAI/Ming-3.0-tts-0.5B',
    'model_revision': '7247f4c94a5b2e987404ed28a5cfec41b1a4ca61',
    'runtime_revision': 'a39b80660bdc5a4394d5e1d41af6dbfd9c443a54',
    'reference_sha256': 'ab306a969ba91d4f314a0f54b67abfdedcc22047006e0ebb0f3462929d0604c7',
    'voice': 'jungle-calm-female',
    'task': 'BASIC',
    'profile': 'normal',
    'controls': {'speed': '中速', 'pitch': '中', 'volume': '中'},
    'raw_text': True,
    'text_normalization': False,
    'output_rate': 22050,
}


def supported_languages():
    return {line.split('|', 1)[0] for line in (ROOT / 'locales/index.txt').read_text().splitlines()
            if '|' in line and not line.startswith('#')}


def resource_language(path):
    parts = path.split('/')
    if len(parts) >= 5 and parts[:2] == ['assets', 'practices']:
        if parts[3] in ('voice', 'voice-male'):
            return parts[4]
        if parts[3] == 'text' and Path(parts[4]).stem != 'index':
            return Path(parts[4]).stem
    return ''


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


ZX28 = b'ZX\0\0\x1c\0\0\0'
ZX28_ASSETS = 3


def zx28_assets_section(data):
    """The bounds of a revision-28 executable's asset section (kind 3).

    Ziran's ASSEMBLY/zx-executable-format.md: a 64-byte header, then 32-byte
    directory records in increasing kind order; the file length is exact."""
    if len(data) < 64:
        raise ValueError('truncated ZX 28 container')
    header_size, record_size = struct.unpack_from('<II', data, 8)
    count = struct.unpack_from('<I', data, 32)[0]
    length, directory = struct.unpack_from('<QQ', data, 40)
    if (header_size != 64 or record_size != 32 or directory != 64 or
            length != len(data) or not 3 <= count <= 1024 or
            directory + count * record_size > len(data)):
        raise ValueError('invalid ZX 28 container')
    for index in range(count):
        kind, flags, offset, size = struct.unpack_from('<IIQQ', data, directory + index * record_size)
        if kind == ZX28_ASSETS:
            if not flags & 1 or offset + size > len(data):
                raise ValueError('invalid ZX 28 asset section')
            return offset, offset + size
    raise ValueError('ZX 28 container has no asset section')


def zx28_bundle_assets(data, include_paths):
    start, end = zx28_assets_section(data)
    at = start

    def take(size):
        nonlocal at
        if size < 0 or at + size > end:
            raise ValueError('truncated resource bundle')
        value = data[at:at + size]
        at += size
        return value

    def number():
        return struct.unpack('<I', take(4))[0]

    count = number()
    if count > 10000:
        raise ValueError('too many resource assets')
    result = {}
    previous = None
    for _ in range(count):
        name = take(number())
        if previous is not None and name <= previous:
            raise ValueError('unsorted or duplicate resource path')
        previous = name
        size = number()
        path = name.decode('utf-8')
        if include_paths is None or path in include_paths:
            result[path] = take(size)
        else:
            take(size)
    if at != end:
        raise ValueError('trailing resource section bytes')
    return result


def bundle_assets(data, *, maximum=MAXIMUM, include_paths=None):
    """Read a bundle's resources (ZX 28, or released v26/v27); never run its code."""
    if len(data) > maximum:
        raise ValueError('unsupported resource bundle')
    if data[:8] == ZX28:
        return zx28_bundle_assets(data, include_paths)
    if data[:8] not in (b'ZX\0\0\x1a\0\0\0', b'ZX\0\0\x1b\0\0\0'):
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
    seen = set()
    for _ in range(count):
        path = text().decode('utf-8')
        if path in seen:
            raise ValueError('duplicate resource path')
        seen.add(path)
        size = number()
        if include_paths is None or path in include_paths:
            result[path] = take(size)
        else:
            if at + size > len(data):
                raise ValueError('truncated resource bundle')
            at += size
    if at != len(data):
        raise ValueError('trailing resource bundle bytes')
    return result


def catalog_from_bundle(data):
    # Older releases have no content catalog and remain installable.
    if data[:8] not in (b'ZX\0\0\x1a\0\0\0', ZX28):
        return []
    assets = bundle_assets(data, maximum=len(data), include_paths={CATALOG})
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
    astral_folder = assets_root / 'practice-astral_projection/assets/practices/astral_projection'
    catalogue = astral_folder / 'catalogue.json'
    if not catalogue.is_file():
        raise ValueError('Astral Projection lesson catalogue is missing from the base pack')
    selected = json.loads(catalogue.read_text())
    astral_keys = [cue['key'] for row in selected['practices']
                  for cue in json.loads((astral_folder / 'sessions' / (row['id'] + '.json')).read_text())['cues']]
    settings = configuration['narration']['astral_projection_bruce']
    astral_speech = json.loads((ROOT / settings['config']).read_text())
    declared = json.loads((ROOT / astral_speech['keys_file']).read_text()) if 'keys_file' in astral_speech else astral_speech['keys']
    if astral_keys != declared:
        raise ValueError('Astral Projection sessions and narration inventory differ')
    output.mkdir(parents=True, exist_ok=True)
    packs = []
    guide = []
    languages = supported_languages()
    jungle_packs = stage_jungle_narration(configuration, assets_root, languages)
    for practice in NAMES + (GUIDE,):
        # Lumi's guide has narration only, without a base pack.
        directories = [] if practice == GUIDE else [assets_root / ('practice-' + practice)]
        directories += sorted(assets_root.glob('practice-' + practice + '-voice-*'))
        for directory in directories:
            language = directory.name.split('-voice-', 1)[1] if '-voice-' in directory.name else ''
            # practice-taichi-voice-en-male holds the male recording.
            language, _, voice = language.partition('-')
            if language and language not in languages:
                continue
            assets = directory / 'assets'
            jungle = not voice and (practice, language) in jungle_packs
            if language and not jungle and not narration_current(configuration, practice, language, assets, voice):
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
            if language and practice in configuration.get('default_narration', []):
                if 'product' in pack:
                    raise ValueError('paid narration cannot ship in the default package')
                shipped = assets_root / 'practices/assets/practices/default' / path.name
                shipped.parent.mkdir(parents=True, exist_ok=True)
                shipped.write_bytes(data)
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


def narration_inventory(configuration, practice, voice='', *, legacy_astral=False):
    inventory = practice + ('_' + voice if voice else '')
    if practice == 'astral_projection' and not voice and not legacy_astral and media_path(
            'assets/practices/astral_projection/catalogue.json').exists():
        inventory = 'astral_projection_bruce'
    settings = configuration['narration'].get(inventory)
    if not settings:
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location('practice_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
    speech = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(speech)
    speech.LOCALES = media_path(settings['text_directory'])
    speech.VOICE = media_path(settings['output_directory'])
    config = json.loads((ROOT / settings['config']).read_text())
    return inventory, settings, speech, config, speech.narration_keys(config)


def verified_jungle_clip(row, inventory, code, key, text, maximum, file):
    if not isinstance(row, dict):
        return None
    request = row.get('request')
    if (not isinstance(request, dict) or request.get('language') != code or request.get('text') != text
            or any(request.get(field) != value for field, value in JUNGLE_REQUEST.items())):
        return None
    identity = json.dumps(request, ensure_ascii=False, separators=(',', ':'), sort_keys=True, allow_nan=False)
    if (row.get('request_sha256') != sha256(identity.encode('utf-8')).hexdigest()
            or row.get('text_sha256') != sha256(text.encode('utf-8')).hexdigest()):
        return None
    practices = row.get('practices')
    practice = practices.get(inventory) if isinstance(practices, dict) else None
    if not isinstance(practice, dict) or practice.get('cue') != key:
        return None
    frames = row.get('frames_48000')
    seconds = row.get('seconds')
    if (type(frames) is not int or not 24000 <= frames <= maximum * 48000
            or type(seconds) not in (int, float) or not 0.5 <= seconds <= maximum):
        return None
    if not file.is_file() or not 36 <= file.stat().st_size <= MAXIMUM:
        return None
    audio = file.read_bytes()
    if not audio.startswith(b'OggS') or b'OpusHead' not in audio[:64]:
        return None
    return audio if sha256(audio).hexdigest() == row.get('sha256') else None


def stage_jungle_narration(configuration, assets_root, languages):
    index = media_path('assets/practices/jungle-narration.json')
    if not index.is_file():
        return set()
    receipt = json.loads(index.read_text())
    if (receipt.get('format') != 'practices-jungle-narration-1'
            or receipt.get('speaker_tensor_sha256') != JUNGLE_TENSOR
            or not isinstance(receipt.get('clips'), dict)):
        raise ValueError('invalid Jungle narration provenance')
    staged = set()
    for practice in NAMES + (GUIDE,):
        prefix = practice + '/voice-jungle/'
        if not any(key.startswith(prefix) for key in receipt['clips']):
            continue
        plan = narration_inventory(configuration, practice)
        if plan is None:
            continue
        plans = [plan]
        if plan[0] == 'astral_projection_bruce':
            # Both sets share a language pack. Preserve the original lesson
            # when updating to the six selected lessons and their narration.
            legacy = narration_inventory(configuration, practice, legacy_astral=True)
            if legacy is None or set(plan[4]).intersection(legacy[4]):
                raise ValueError('overlapping or missing original Astral Projection narration inventory')
            plans.append(legacy)
        cue_count = sum(len(keys) for _, _, _, _, keys in plans)
        for language in sorted(set(languages) & JUNGLE_LANGUAGES):
            locale_prefix = prefix + language + '/'
            if not any(key.startswith(locale_prefix) for key in receipt['clips']):
                continue
            recordings = {}
            for inventory, _, speech, config, keys in plans:
                for _, key, text in speech.wanted(config, [language], keys):
                    name = key + '.ogg'
                    path = locale_prefix + name
                    audio = verified_jungle_clip(receipt['clips'].get(path), inventory, language, key, text,
                                                 speech.maximum_clip_seconds(config, key),
                                                 media_path('assets/practices/' + path))
                    if audio is None:
                        break
                    recordings[name] = audio
            if len(recordings) != cue_count:
                print(f'{practice}/{language}: Jungle narration incomplete, keeping the verified existing voice')
                continue
            target = assets_root / f'practice-{practice}-voice-{language}' / 'assets/practices' / practice / 'voice' / language
            target.mkdir(parents=True, exist_ok=True)
            for existing in target.iterdir():
                if existing.is_file() and existing.name not in recordings:
                    existing.unlink()
            for name, audio in recordings.items():
                (target / name).write_bytes(audio)
            staged.add((practice, language))
    return staged


def narration_current(configuration, practice, language, assets=None, voice=''):
    """Partial or stale recordings never become an advertised language pack."""
    if language not in supported_languages():
        return False
    plan = narration_inventory(configuration, practice, voice)
    if plan is None:
        return False
    _, settings, speech, config, keys = plan
    folder = 'voice-male' if voice else 'voice'
    receipt_path = ROOT / settings['receipt']
    if not receipt_path.is_file():
        return False
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
        wanted = {key + '.ogg' for key in keys + config.get('preserved_keys', [])} | {'pack.json'}
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
