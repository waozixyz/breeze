#!/usr/bin/env python3
"""Render repeatable, resumable before/after motion reviews on a private display.

Run from Breeze: env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY
-u DBUS_SESSION_BUS_ADDRESS HARMONY_DESKTOP_RECOVERY=0 xvfb-run -a python3
 design/figure-preview/review.py
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageStat
from full_review import resolve_media

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / 'design/figure-preview'
OUT = ROOT / 'build/practice-motion-review'
# The audit's worst moments, plus a floor transition and the astral breath.
SHOTS = [('tai-chi', 0, 19, 9, 11), ('sun-salutation', 1, 0, 21, 23),
         ('workout', 2, 11, 15, 18), ('astral', 3, 4, 60, 62)]


def run(args, log):
    with log.open('w') as stream:
        subprocess.run([str(a) for a in args], cwd=PREVIEW, check=True,
                       stdout=stream, stderr=subprocess.STDOUT)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def media_identity(media, person):
    paths = [media / f'shared/figure/{person}.vrm']
    paths.extend(sorted((media / 'shared/figure/backdrops').glob('*.json')))
    paths.extend(sorted((media / 'shared/figure/backdrops').glob('*.webp')))
    paths.extend(sorted((media / 'astral_projection/sessions').glob('*.json')))
    return {str(path.relative_to(media)): digest(path) for path in paths}


def shot_path(directory, at):
    # Native FormatDecimal writes one decimal place and trims trailing zeros.
    matches = [path for path in directory.glob('*.png')
               if abs(float(path.stem) - at) <= 0.051]
    return matches[0] if len(matches) == 1 else None


def all_poses(media):
    """Cover all twelve Workout items and every step of both Sun rounds."""
    binary = PREVIEW / 'build/app/figure_preview'
    groups = {}
    output = subprocess.check_output([binary, '--review-points'], cwd=PREVIEW, text=True)
    for line in output.splitlines():
        if not line.startswith('review\t'):
            continue
        _, practice, item, at, label = line.split('\t', 4)
        groups.setdefault((int(practice), int(item)), []).append((float(at), label))
    if sum(map(len, groups.values())) != 60:
        raise RuntimeError('Incomplete Workout/Sun review point catalogue')
    sheets = {2: Image.new('RGB', (1200, 12 * 290), '#171a24'),
              1: Image.new('RGB', (800, 12 * 290), '#171a24')}
    records = []
    for (practice, item), points in groups.items():
        for person_index, person in enumerate(('woman', 'man')):
            frames = OUT / f'coverage-{practice}-{item}-{person}'
            frames.mkdir(exist_ok=True)
            expected = {'binary': digest(binary), 'course': digest(media / 'taichi/course.tch'),
                        'practice': practice, 'item': item, 'person': person, 'points': points,
                        'media': media_identity(media, person)}
            # JSON normalizes point tuples to lists for the resumable receipt.
            expected = json.loads(json.dumps(expected))
            receipt = frames / 'render.json'
            complete = receipt.exists() and json.loads(receipt.read_text()) == expected
            complete = complete and all(shot_path(frames, at) is not None for at, _ in points)
            if not complete:
                args = [binary, '--shot', frames, practice, item, *[str(at) for at, _ in points]]
                if person == 'man':
                    args.append('man')
                run(args, OUT / f'coverage-{practice}-{item}-{person}.log')
                if not all(shot_path(frames, at) is not None for at, _ in points):
                    raise RuntimeError(f'{frames}: incomplete coverage')
                receipt.write_text(json.dumps(expected, indent=2) + '\n')
            for index, (at, label) in enumerate(points):
                with Image.open(shot_path(frames, at)) as image:
                    if max(ImageStat.Stat(image.convert('RGB')).stddev) < 8:
                        raise RuntimeError(f'{frames}: blank render at {at}')
                    tile = Image.new('RGB', (200, 290), '#171a24')
                    thumb = image.convert('RGB')
                    thumb.thumbnail((190, 250))
                    tile.paste(thumb, ((200 - thumb.width) // 2, 25))
                    draw = ImageDraw.Draw(tile)
                    draw.text((5, 5), f'{label} / {person}', fill='white')
                    draw.text((5, 275), f'{at:g} seconds', fill='white')
                    if practice == 2:
                        row, column = item, index * 2 + person_index
                    else:
                        row, column = index % 12, (index // 12) * 2 + person_index
                    sheets[practice].paste(tile, (column * 200, row * 290))
            records.append({**expected, 'frames': str(frames)})
    for practice, name in ((2, 'workout-all-poses'), (1, 'sun-salutation-all-poses')):
        path = OUT / f'{name}.jpg'
        sheets[practice].save(path, quality=94)
        print(f'Coverage sheet: {path}', flush=True)
    (OUT / 'coverage.json').write_text(json.dumps(records, indent=2) + '\n')


def main():
    if not os.environ.get('DISPLAY') or os.environ.get('HARMONY_DESKTOP_RECOVERY') != '0':
        raise SystemExit('Run this review with the documented private Xvfb command.')
    OUT.mkdir(parents=True, exist_ok=True)
    media = resolve_media()
    os.environ['FIGURE_PRACTICES'] = str(media)
    if sys.argv[1:] == ['--coverage-only']:
        all_poses(media)
        return
    if sys.argv[1:]:
        raise SystemExit('Usage: review.py [--coverage-only]')
    records = []
    thumbs = []
    for name, practice, item, start, end in SHOTS:
        for version in ('before', 'after'):
            binary = PREVIEW / ('build/before/figure_preview' if version == 'before' else 'build/app/figure_preview')
            identity = digest(binary)
            for person in ('woman', 'man'):
                stem = f'{name}-{version}-{person}'
                frames = OUT / stem
                frames.mkdir(exist_ok=True)
                receipt = frames / 'render.json'
                expected = {'binary': identity, 'practice': practice, 'item': item,
                            'start': start, 'end': end, 'person': person,
                            'course': digest(media / 'taichi/course.tch')}
                if version == 'after':
                    expected['media'] = media_identity(media, person)
                # Men get a still for the contact sheet; women get a full clip.
                count = (end - start) * 30 + 1 if person == 'woman' else 1
                complete = receipt.exists() and json.loads(receipt.read_text()) == expected
                complete = complete and len(list(frames.glob('*.png'))) == count
                if not complete:
                    args = [binary, '--video', frames, practice, item, start, end]
                    if person == 'man':
                        args = [binary, '--video', frames, practice, item, start, start, 'man']
                    run(args, OUT / f'{stem}.log')
                    if len(list(frames.glob('*.png'))) != count:
                        raise RuntimeError(f'{stem}: incomplete frames')
                    receipt.write_text(json.dumps(expected, indent=2) + '\n')
                with Image.open(frames / '0000.png') as image:
                    if max(ImageStat.Stat(image.convert('RGB')).stddev) < 8:
                        raise RuntimeError(f'{stem}: blank render')
                    thumb = image.convert('RGB')
                    thumb.thumbnail((300, 400))
                    tile = Image.new('RGB', (320, 440), '#171a24')
                    tile.paste(thumb, ((320 - thumb.width) // 2, 30))
                    draw = ImageDraw.Draw(tile)
                    draw.text((10, 8), f'{name} / {version} / {person}', fill='white')
                    draw.text((10, 416), f'{start} seconds', fill='white')
                    thumbs.append(tile)
                records.append({**expected, 'frames': str(frames), 'count': count})
        video = OUT / f'{name}-before-after.mp4'
        before = OUT / f'{name}-before-woman/%04d.png'
        after = OUT / f'{name}-after-woman/%04d.png'
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2',
             '-framerate', '30', '-i', before, '-framerate', '30', '-i', after,
             '-filter_complex_threads', '1', '-filter_complex',
             "[0:v]drawtext=text='Before':x=16:y=16:fontcolor=white:box=1:boxcolor=black@0.6[a];"
             "[1:v]drawtext=text='After':x=16:y=16:fontcolor=white:box=1:boxcolor=black@0.6[b];[a][b]hstack[v]",
             '-map', '[v]', '-c:v', 'libx264', '-threads', '2', '-crf', '20',
             '-pix_fmt', 'yuv420p', video], OUT / f'{name}-encode.log')
        print(f'Review video: {video}', flush=True)
    sheet = Image.new('RGB', (1280, 440 * len(SHOTS)), '#171a24')
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % 4) * 320, (index // 4) * 440))
    sheet.save(OUT / 'contact-sheet.jpg', quality=94)
    (OUT / 'review.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'Contact sheet: {OUT / "contact-sheet.jpg"}', flush=True)
    all_poses(media)
    floor_sheets()


def floor_sheets():
    for name, _, _, _, _ in SHOTS:
        sheet = Image.new('RGB', (1280, 880), '#171a24')
        for row, person in enumerate(('woman', 'man')):
            for column, version in enumerate(('before', 'after')):
                path = (OUT / f'floor-before-{name}-{person}.png' if version == 'before' else
                        OUT / f'{name}-after-{person}/0000.png')
                with Image.open(path) as image:
                    thumb = image.convert('RGB')
                    thumb.thumbnail((620, 395))
                    tile = Image.new('RGB', (640, 440), '#171a24')
                    tile.paste(thumb, ((640 - thumb.width) // 2, 30))
                    ImageDraw.Draw(tile).text((12, 8), f'{name} / {person} / {version}', fill='white')
                    sheet.paste(tile, (column * 640, row * 440))
        path = OUT / f'{name}-floor-before-after.jpg'
        sheet.save(path, quality=94)
        print(f'Floor comparison: {path}', flush=True)


if __name__ == '__main__':
    main()
