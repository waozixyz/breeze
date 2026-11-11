"""Validate the real public preview against the canonical complete course."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_media import MEDIA
from ogg_opus import ogg_crc, opus_frames, pages
from tai_chi_preview import integer, item_free, preview_course, read_course, stage_preview

source = MEDIA / 'taichi/course.tch'
original = source.read_bytes()
original_hash = sha256(original).hexdigest()
preview, spoken = preview_course(original)
assert preview_course(original) == (preview, spoken), 'nondeterministic preview'
full_strings, full_sets, full_characters, full_modules = read_course(original)
strings, sets, characters, modules = read_course(preview)


def entries(table, outline):
    return [(table[integer(header)], header, marks)
            for _, lessons in outline for _, items in lessons for header, marks in items]


def keys(table, timelines, header):
    first, last = integer(header, 17), integer(header, 21)
    timeline = timelines[first] if header[15] == 1 else timelines[0][first:last + 1]
    return [(key[:4] + key[8:], None if integer(key, 4) < 0 else table[integer(key, 4)])
            for key in timeline]


full_items = entries(full_strings, full_modules)
items = entries(strings, modules)
assert [item[0] for item in items] == [item[0] for item in full_items], 'progress indices changed'
free = 0
for (identifier, full_header, full_marks), (_, header, marks) in zip(full_items, items):
    if item_free(identifier):
        free += 1
        assert header[15] in (0, 1), identifier
        assert keys(strings, sets, header) == keys(full_strings, full_sets, full_header), identifier
        assert header[25:37] == full_header[25:37], 'timing changed: ' + identifier
        assert [(strings[integer(m)], m[4:]) for m in marks] == [
            (full_strings[integer(m)], m[4:]) for m in full_marks], identifier
    else:
        assert header[15] == 2 and integer(header, 17) == integer(header, 21) == -1, identifier
        assert not marks and header[33:37] == bytes(4), identifier
assert free == 44, free
assert len(sets) < len(full_sets)
assert len(sets[0]) == max(integer(header, 21) for identifier, header, _ in items
                           if item_free(identifier) and header[15] == 0) + 1
assert not item_free('full/normal') and not item_free('full/slow')
assert not item_free('lesson-4/all') and not item_free('lesson-8/all')
assert not item_free('lesson-10/all') and not item_free('lesson-1/')
assert item_free('lesson-3/all') and item_free('foundations/breathing')
for broken in (original[:-1], b'TCH1' + original[4:], original + b'extra'):
    try:
        preview_course(broken)
    except ValueError:
        pass
    else:
        raise AssertionError('malformed course accepted')
output = ROOT / 'build/tai-chi-preview-test'
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=output, prefix='assets-') as directory:
    stage_preview(MEDIA, Path(directory))
    target = Path(directory) / 'practices/taichi-preview'
    with zipfile.ZipFile(target / 'course.zip') as archive:
        assert archive.namelist() == ['course.tch']
        assert archive.read('course.tch') == preview
    assert (target / 'flat-edge.png').read_bytes() == (MEDIA / 'taichi/flat-edge.png').read_bytes()
    clips = list(target.rglob('*.ogg'))
    assert clips, 'no existing free Opus narration staged'
    assert all(clip.stem in spoken for clip in clips), 'paid-only cue staged'
    languages = {line.split('|', 1)[0] for line in
                 (ROOT / 'locales/index.txt').read_text().splitlines() if '|' in line}
    expected_profiles = {(voice, code) for voice in ('voice', 'voice-male') for code in languages}
    actual_profiles = {(voice, folder.name) for voice in ('voice', 'voice-male')
                       for folder in (target / voice).iterdir() if folder.is_dir()}
    assert len(expected_profiles) == 20 and len(spoken) == 184
    assert actual_profiles == expected_profiles, 'missing or unsupported preview voice profile'
    profiles = []
    for voice, code in sorted(expected_profiles):
        folder = target / voice / code
        recordings = sorted(folder.glob('*.ogg'))
        assert {clip.stem for clip in recordings} == spoken, f'incomplete preview: {voice}/{code}'
        frames = 0
        for clip in recordings:
            audio = clip.read_bytes()
            original_audio = MEDIA / 'taichi' / voice / code / clip.name
            assert sha256(audio).digest() == sha256(original_audio.read_bytes()).digest(), clip
            stream_pages = pages(audio)
            assert stream_pages[0][2] & 2 and stream_pages[-1][2] & 4, clip
            frames += opus_frames(audio)
            for at, length, _, _ in stream_pages:
                page = bytearray(audio[at:at + length])
                checksum = int.from_bytes(page[22:26], 'little')
                page[22:26] = bytes(4)
                assert ogg_crc(page) == checksum, f'corrupt Ogg page: {clip}'
        profiles.append(dict(voice=voice, language=code, clips=len(recordings),
                             bytes=sum(clip.stat().st_size for clip in recordings), frames_48000=frames))
    staged_bytes = sum(file.stat().st_size for file in target.rglob('*') if file.is_file())
    budget = json.loads((ROOT / 'packaging/size-budgets.json').read_text())['app_package_bytes']
    assert staged_bytes < budget, 'preview alone exceeds the existing app package budget'
    measurement = dict(free_items=free, cues_per_profile=len(spoken), profiles=profiles,
                       course_bytes=len(preview), course_zip_bytes=(target / 'course.zip').stat().st_size,
                       voice_bytes=sum(profile['bytes'] for profile in profiles),
                       staged_preview_bytes=staged_bytes, app_package_budget_bytes=budget)
    (output / 'measurement.json').write_text(json.dumps(measurement, indent=2) + '\n')
    print(f'LOCAL TEST: all {len(profiles)} voice profiles contain {len(spoken)} exact source Opus clips; '
          f'complete Ogg pages, CRCs and positive duration; staged preview {staged_bytes:,} bytes '
          f'(whole package budget {budget:,}; complete app size still pending)')
assert sha256(source.read_bytes()).hexdigest() == original_hash, 'canonical course changed'
print(f'LOCAL TEST: {free} free items retain exact motion/timing; later/full timelines absent; stable progress and existing Opus staged')
