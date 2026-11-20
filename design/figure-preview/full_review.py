#!/usr/bin/env python3
"""Full timeline playback plus slow transition reviews on a private display.

The native renderer writes raw RGBA into its own ffmpeg pipe. All sequences
are retained, without a large intermediate PNG directory. Completed receipts
are hash-bound to exact source, assets and binary.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / 'design/figure-preview'
BINARY = PREVIEW / 'build/app/figure_preview'
OUT = ROOT / 'build/practice-full-review'


def resolve_media():
    override = os.environ.get('FIGURE_PRACTICES')
    if override:
        return Path(override).resolve()
    compiler = ROOT / 'build/packages/ziran/build/bin/ziran'
    path = subprocess.check_output([compiler, 'pkg', 'path', 'practices', '--locked'], cwd=PREVIEW, text=True)
    return Path(path.strip()).resolve()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(media):
    paths = list(PREVIEW.glob('*.zi')) + [Path(__file__).resolve(), PREVIEW / 'ziran.toml', PREVIEW / 'ziran.lock']
    for directory in [ROOT / 'src/practices/tai_chi', ROOT / 'src/practices/sun_salutation', ROOT / 'apps/practice', media / 'figure']:
        paths += list(directory.glob('*.zi'))
    paths += [BINARY, media / 'taichi/course.tch']
    paths += list((media / 'shared/figure').glob('*.vrm'))
    paths += list((media / 'shared/figure/backdrops').glob('*.json'))
    paths += list((media / 'shared/figure/backdrops').glob('*.webp'))
    paths += list((media / 'astral_projection/sessions').glob('*.json'))
    return {str(path): sha(path) for path in sorted(paths)}


def render(item, person, rate, start, end, label, inputs):
    practice, number, duration, name = item
    folder = OUT / f'{practice}-{number:03d}-{person}'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{label}.mp4'
    receipt = folder / f'{label}.json'
    playback_speed = .25 if label.startswith('slow-') else 1
    expected = {'inputs': inputs, 'person': person, 'practice': practice, 'item': number,
                'name': name, 'duration': duration, 'from': start, 'to': end, 'render_fps': rate,
                'playback_speed': playback_speed}
    if receipt.exists() and target.exists():
        saved = json.loads(receipt.read_text())
        if saved.get('identity') == expected and saved.get('sha256') == sha(target):
            print('Reused completed review:', target, flush=True)
            return
    partial = target.with_suffix('.partial.mp4')
    if partial.exists():
        raise RuntimeError(f'Unresolved earlier render: {partial}; inspect its managed command before retrying')
    width, height = (480, 320) if practice == 3 else (360, 480)
    read_fd, write_fd = os.pipe()
    with (folder / f'{label}-native.log').open('w') as native_log, (folder / f'{label}-encoder.log').open('w') as encoder_log:
        encoder = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgba',
                                    '-video_size', f'{width}x{height}', '-framerate', str(rate * playback_speed), '-i', 'pipe:0',
                                    '-fps_mode', 'passthrough', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '22', '-pix_fmt', 'yuv420p',
                                    '-movflags', '+faststart', str(partial)], stdin=read_fd, stdout=encoder_log, stderr=encoder_log)
        os.close(read_fd)
        args = [BINARY, '--stream', str(practice), str(number), str(start), str(end), str(rate),
                str(width), str(height), str(write_fd)]
        if person == 'man':
            args.append('man')
        try:
            native = subprocess.Popen(args, cwd=PREVIEW, pass_fds=(write_fd,), stdout=native_log, stderr=subprocess.STDOUT)
        except BaseException:
            os.close(write_fd)
            encoder.wait()
            raise
        else:
            os.close(write_fd)
        code = native.wait()
        encoder_code = encoder.wait()
        if code or encoder_code:
            raise RuntimeError(f'{target}: native exit {code}, encoder exit {encoder_code}; preserve logs and partial file')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                                                '-of', 'json', partial]))
    frames = int(probe['streams'][0]['nb_read_frames'])
    last_frame = math.floor((end - start) * rate)
    if start + last_frame / rate < end:
        last_frame += 1
    if frames != last_frame + 1:
        raise RuntimeError(f'{target}: expected {last_frame + 1} frames, got {frames}')
    partial.replace(target)
    receipt.write_text(json.dumps({'identity': expected, 'sha256': sha(target), 'frames': frames}, indent=2) + '\n')
    print('Completed review:', target, 'frames:', frames, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fps', type=float, default=4)
    parser.add_argument('--practice', type=int, choices=range(4))
    parser.add_argument('--item', type=int)
    parser.add_argument('--transitions', action='store_true', help='also render each cued transition at 30 Hz, quarter speed')
    args = parser.parse_args()
    if not 1 <= args.fps <= 60:
        parser.error('--fps must be between 1 and 60')
    if not os.environ.get('DISPLAY') or os.environ.get('HARMONY_DESKTOP_RECOVERY') != '0':
        raise SystemExit('Use the documented scrubbed private Xvfb command')
    media = resolve_media()
    os.environ['FIGURE_PRACTICES'] = str(media)
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = identity(media)
    items = []
    for line in subprocess.check_output([BINARY, '--review-items'], cwd=PREVIEW, text=True).splitlines():
        if line.startswith('item\t'):
            _, practice, number, duration, name = line.split('\t', 4)
            items.append((int(practice), int(number), float(duration), name))
    if not items:
        raise RuntimeError('Empty review catalogue')
    (OUT / 'catalogue.json').write_text(json.dumps({'inputs': inputs, 'items': items}, indent=2) + '\n')
    selected = [item for item in items if (args.practice is None or item[0] == args.practice)
                and (args.item is None or item[1] == args.item)]
    if not selected:
        parser.error('no item matches the selected practice and item number')
    for item in selected:
        for person in ('woman', 'man'):
            render(item, person, args.fps, 0, item[2], 'complete', inputs)
    # Dense slow reviews are selected from native cue/segment boundary data,
    # never from an evenly spaced still-frame sample. Native boundary export
    # and the findings manifest are kept separately from completed video receipts.
    if args.transitions:
        spans = []
        for line in subprocess.check_output([BINARY, '--review-spans'], cwd=PREVIEW, text=True).splitlines():
            if line.startswith('span\t'):
                _, practice, number, start, end, name = line.split('\t', 5)
                spans.append((int(practice), int(number), float(start), float(end), name))
        (OUT / 'transition-spans.json').write_text(json.dumps(spans, indent=2) + '\n')
        by_item = {(item[0], item[1]): item for item in items}
        for index, (practice, number, start, end, name) in enumerate(spans):
            if args.practice is not None and practice != args.practice:
                continue
            if args.item is not None and number != args.item:
                continue
            if end <= start:
                continue
            for person in ('woman', 'man'):
                render(by_item[practice, number], person, 30, start, end,
                       f'slow-{index:04d}-{name}', inputs)
    print('Complete-timeline videos finished; human visual review remains required', flush=True)


if __name__ == '__main__':
    main()
