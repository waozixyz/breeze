"""Build a public TCH2 preview without later lessons' motion or speech.

The complete outline and item order stay stable for progress and purchases.
Locked entries carry source=2 and no timeline; the host refuses to play them.
Only Foundations and the configured numbered lessons retain actual keyframes.
"""
import io
from pathlib import Path
import re
import shutil
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 64 * 1024 * 1024
LOCKED_SOURCE = 2


def free_lesson_count():
    source = (ROOT / 'apps/practice/src/native/course_access.zi').read_text()
    match = re.search(r'^TAI_CHI_FREE_FORM_LESSONS :: ([1-8])$', source, re.M)
    if match is None:
        raise ValueError('missing Tai Chi free lesson boundary')
    return int(match[1])


def item_free(identifier):
    if identifier.startswith('foundations/'):
        return len(identifier) > len('foundations/')
    match = re.fullmatch(r'lesson-([1-8])/.+', identifier)
    return match is not None and int(match[1]) <= free_lesson_count()


class Reader:
    def __init__(self, data):
        if len(data) > LIMIT:
            raise ValueError('Tai Chi course exceeds size bound')
        self.data = io.BytesIO(data)

    def take(self, size):
        if size < 0 or size > LIMIT:
            raise ValueError('invalid Tai Chi section size')
        value = self.data.read(size)
        if len(value) != size:
            raise ValueError('truncated Tai Chi course')
        return value

    def count(self, bound):
        value = struct.unpack('<I', self.take(4))[0]
        if value > bound:
            raise ValueError('Tai Chi section exceeds count bound')
        return value


def read_course(data):
    reader = Reader(data)
    if reader.take(4) != b'TCH2':
        raise ValueError('unsupported Tai Chi course')
    strings = [reader.take(struct.unpack('<H', reader.take(2))[0]).decode('utf-8')
               for _ in range(reader.count(10000))]
    sets = [[reader.take(220) for _ in range(reader.count(50000))]
            for _ in range(reader.count(256))]
    characters = []
    for _ in range(reader.count(16)):
        header = reader.take(112)
        images = [reader.take(96) for _ in range(reader.count(1024))]
        characters.append((header, images))
    modules = []
    for _ in range(reader.count(64)):
        title = reader.take(4)
        lessons = []
        for _ in range(reader.count(256)):
            heading = reader.take(12)
            items = []
            for _ in range(reader.count(1024)):
                header = reader.take(37)
                marks = [reader.take(12) for _ in range(reader.count(1024))]
                items.append((header, marks))
            lessons.append((heading, items))
        modules.append((title, lessons))
    if reader.data.read(1):
        raise ValueError('trailing Tai Chi bytes')
    return strings, sets, characters, modules


def integer(raw, offset=0):
    return struct.unpack_from('<i', raw, offset)[0]


def preview_course(data):
    strings, source_sets, characters, modules = read_course(data)
    selected_sets = set()
    form_end = -1
    spoken = set()
    for _, lessons in modules:
        for _, items in lessons:
            for header, _ in items:
                if not item_free(strings[integer(header)]):
                    continue
                first, last = integer(header, 17), integer(header, 21)
                if header[15] == 0:
                    selected_sets.add(0)
                    form_end = max(form_end, last)
                elif header[15] == 1:
                    selected_sets.add(first)
                else:
                    raise ValueError('invalid free Tai Chi timeline')
    ordered_sets = sorted(selected_sets)
    mapping = {old: new for new, old in enumerate(ordered_sets)}
    sets = [source_sets[old][:form_end + 1] if old == 0 else source_sets[old]
            for old in ordered_sets]
    references = set()

    def reference(index):
        if index == -1:
            return
        if index < 0 or index >= len(strings):
            raise ValueError('invalid Tai Chi string reference')
        references.add(index)

    for keys in sets:
        if len(keys) < 2:
            raise ValueError('free Tai Chi timeline is empty')
        for key in keys:
            reference(integer(key, 4))
    for header, images in characters:
        reference(integer(header))
        reference(integer(header, 4))
        for image in images:
            reference(integer(image))
            reference(integer(image, 4))
    outline = []
    for title, lessons in modules:
        reference(integer(title))
        copied_lessons = []
        for heading, items in lessons:
            for offset in (0, 4, 8):
                reference(integer(heading, offset))
            copied_items = []
            for header, marks in items:
                header = bytearray(header)
                for offset in (0, 4, 8):
                    reference(integer(header, offset))
                if item_free(strings[integer(header)]):
                    if header[15] == 1:
                        struct.pack_into('<i', header, 17, mapping[integer(header, 17)])
                    for mark in marks:
                        reference(integer(mark))
                    if header[16]:
                        first, last = integer(header, 17), integer(header, 21)
                        keys = sets[first] if header[15] == 1 else sets[0][first:last + 1]
                        spoken.update(strings[integer(key, 4)] for key in keys if integer(key, 4) >= 0)
                    else:
                        spoken.update(strings[integer(mark)] for mark in marks if integer(mark) >= 0)
                else:
                    header[15] = LOCKED_SOURCE
                    header[16] = 0
                    struct.pack_into('<ii', header, 17, -1, -1)
                    struct.pack_into('<f', header, 33, 0.0)
                    marks = []
                copied_items.append((header, marks))
            copied_lessons.append((heading, copied_items))
        outline.append((title, copied_lessons))

    ordered_strings = sorted(references)
    string_map = {old: new for new, old in enumerate(ordered_strings)}
    result = io.BytesIO()

    def count(value):
        result.write(struct.pack('<I', value))

    def remap(raw, offsets):
        copied = bytearray(raw)
        for offset in offsets:
            old = integer(raw, offset)
            struct.pack_into('<i', copied, offset, -1 if old == -1 else string_map[old])
        result.write(copied)

    result.write(b'TCH2')
    count(len(ordered_strings))
    for old in ordered_strings:
        encoded = strings[old].encode('utf-8')
        result.write(struct.pack('<H', len(encoded)))
        result.write(encoded)
    count(len(sets))
    for keys in sets:
        count(len(keys))
        for key in keys:
            remap(key, (4,))
    count(len(characters))
    for header, images in characters:
        remap(header, (0, 4))
        count(len(images))
        for image in images:
            remap(image, (0, 4))
    count(len(outline))
    for title, lessons in outline:
        remap(title, (0,))
        count(len(lessons))
        for heading, items in lessons:
            remap(heading, (0, 4, 8))
            count(len(items))
            for header, marks in items:
                remap(header, (0, 4, 8))
                count(len(marks))
                for mark in marks:
                    remap(mark, (0,))
    return result.getvalue(), spoken


def app_locale_codes():
    """Language codes the app ships, from locales/index.txt."""
    codes = set()
    for line in (ROOT / 'locales/index.txt').read_text(encoding='utf-8').splitlines():
        if '|' in line:
            codes.add(line.split('|', 1)[0])
    return codes


def stage_preview(media, assets):
    """Copy only existing free clips; never generate or publish narration.

    Practice media can carry voices for languages the app does not ship;
    only the app's own locales are staged.
    """
    source = media / 'taichi'
    target = assets / 'practices/taichi-preview'
    target.mkdir(parents=True, exist_ok=True)
    data, spoken = preview_course((source / 'course.tch').read_bytes())
    member = zipfile.ZipInfo('course.tch', (1980, 1, 1, 0, 0, 0))
    member.create_system = 3
    member.compress_type = zipfile.ZIP_DEFLATED
    member.external_attr = 0o644 << 16
    with zipfile.ZipFile(target / 'course.zip', 'w') as archive:
        archive.writestr(member, data, compresslevel=9)
    shutil.copyfile(source / 'flat-edge.png', target / 'flat-edge.png')
    languages = app_locale_codes()
    for voice in ('voice', 'voice-male'):
        for language in sorted((source / voice).glob('*')):
            if not language.is_dir():
                continue
            if language.name not in languages:
                continue
            copied = 0
            for key in sorted(spoken):
                clip = language / (key + '.ogg')
                if not clip.is_file():
                    continue
                with clip.open('rb') as stream:
                    header = stream.read(64)
                if not header.startswith(b'OggS') or b'OpusHead' not in header:
                    continue
                output = target / voice / language.name / clip.name
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(clip, output)
                copied += 1
            if copied:
                (target / voice / language.name / 'pack.json').write_text('{"schema":1}\n')
            print(f'Tai Chi preview {voice}/{language.name}: {copied}/{len(spoken)} existing Opus cues')
    print(f'Tai Chi preview: {len(data)} bytes; Foundations + {free_lesson_count()} numbered lessons')
