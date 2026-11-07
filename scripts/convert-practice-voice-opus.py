#!/usr/bin/env python3
"""Re-encode the practices' Ogg Vorbis voice clips as Ogg Opus, in place.

Each clip keeps its packaged path and .ogg name, so downloaded packs, pack
lists and the app's lookups stay the same; Kryon reads the codec from the
content. Without --apply this only checks every clip and reports the sizes
it would produce.

With --apply, each original goes to the practices checkout's ignored
backup/opus-voice/ first, with backup/opus-voice/checksums.json recording the
original and new SHA-256 of every clip. A converted clip replaces its
original only after ffprobe reads it as mono Opus that plays exactly as many
samples as the Vorbis stream (its final granule, or fewer when the stream ends
before it): ffmpeg's padded last frame is trimmed at the end
(scripts/ogg_opus.py), and decoding the new clip must give that count. The
narration receipts then take each new clip's SHA-256, size and length; their
text hashes stay, so no line is marked to be spoken again.

Usage: convert-practice-voice-opus.py PRACTICES_CHECKOUT [--apply] [--bitrate 16k]
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'apps/practice/content.json'
PREFIX = 'assets/practices/'
_spec = importlib.util.spec_from_file_location('ogg_opus', ROOT / 'scripts/ogg_opus.py')
ogg_opus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ogg_opus)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def probe(path):
    """(codec, channels, samples at 48 kHz) as ffprobe reads the stream.

    A Vorbis stream's duration_ts is its own sample count (its final granule),
    which already leaves out the encoder's padding."""
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_name,channels,sample_rate,duration_ts', '-of', 'json',
        str(path)], check=True, capture_output=True, text=True).stdout
    stream = json.loads(out)['streams'][0]
    rate = int(stream['sample_rate'])
    samples = int(stream.get('duration_ts') or 0)
    if ogg_opus.OPUS_RATE % rate:
        raise ValueError(f'{path}: {rate} Hz does not divide 48 kHz')
    return stream['codec_name'], int(stream['channels']), samples * (ogg_opus.OPUS_RATE // rate)


def decoded_frames(path):
    """Samples ffmpeg's decoder actually plays from the clip, at 48 kHz."""
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-ac', '1',
        '-ar', str(ogg_opus.OPUS_RATE), '-f', 'f32le', '-'], check=True, capture_output=True).stdout
    return len(raw) // 4


def encode(source, bitrate, frames, work):
    """The clip as Ogg Opus that plays exactly frames samples at 48 kHz."""
    target = work / 'clip.opus'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(source),
        '-ac', '1', '-c:a', 'libopus', '-b:a', bitrate, '-application', 'voip',
        '-vbr', 'on', '-map_metadata', '-1', '-f', 'ogg', str(target)],
        check=True, capture_output=True)
    target.write_bytes(ogg_opus.end_trim(target.read_bytes(), frames))
    return target


def clips(practices):
    voice = [path for path in sorted(practices.rglob('*.ogg'))
             if not {'.git', 'backup', 'work', 'build'} & set(path.relative_to(practices).parts)]
    if not voice:
        raise SystemExit(f'No .ogg clips under {practices}')
    return voice


def ignored(practices, path):
    return subprocess.run(['git', '-C', str(practices), 'check-ignore', '-q', str(path)]).returncode == 0


def update_receipts(changed):
    """Point every narration receipt row at its converted clip."""
    narration = json.loads(CONTENT.read_text())['narration']
    updated = 0
    for settings in narration.values():
        path = ROOT / settings['receipt']
        receipt = json.loads(path.read_text())
        dirty = False
        for row in receipt.get('clips', {}).values():
            new = changed.get(row.get('file', ''))
            if new is None:
                continue
            row['sha256'], row['bytes'], row['seconds'] = new['sha256'], new['bytes'], round(new['seconds'], 2)
            dirty = True
            updated += 1
        if dirty:
            temporary = path.with_suffix('.json.part')
            temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
            os.replace(temporary, path)
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('practices', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--bitrate', default='16k')
    args = parser.parse_args()
    practices = args.practices.resolve()
    backup = practices / 'backup/opus-voice'
    if args.apply and not ignored(practices, backup / 'probe'):
        raise SystemExit(f'{backup} is not ignored by git; refusing to write backups there')
    manifest_path = backup / 'checksums.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    before = after = converted = skipped = 0
    failures = []
    changed = {}
    with tempfile.TemporaryDirectory(dir=ROOT / 'build', prefix='opus-voice-') as scratch:
        work = Path(scratch)
        for path in clips(practices):
            relative = path.relative_to(practices).as_posix()
            data = path.read_bytes()
            codec, channels, frames = probe(path)
            if codec == 'opus':
                skipped += 1
                continue
            if codec != 'vorbis' or channels != 1 or frames <= 0:
                failures.append(f'{relative}: {codec} with {channels} channels and {frames} samples')
                continue
            # A stream that ends before its final granule plays only the
            # samples it holds; those are the recording.
            frames = min(frames, decoded_frames(path))
            try:
                target = encode(path, args.bitrate, frames, work)
            except ValueError as error:
                failures.append(f'{relative}: {error}')
                continue
            new = target.read_bytes()
            new_codec, new_channels, _ = probe(target)
            played = decoded_frames(target)
            if new_codec != 'opus' or new_channels != 1 or ogg_opus.opus_frames(new) != frames or played != frames:
                failures.append(f'{relative}: {new_codec}/{new_channels} plays {played} samples, not {frames}')
                continue
            timing = frames / ogg_opus.OPUS_RATE
            before += len(data)
            after += len(new)
            converted += 1
            if not args.apply:
                continue
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            if not saved.exists():
                saved.write_bytes(data)
            if digest(saved.read_bytes()) != digest(data):
                failures.append(f'{relative}: a different backup already exists')
                continue
            manifest[relative] = {'vorbis_sha256': digest(data), 'opus_sha256': digest(new),
                                  'vorbis_bytes': len(data), 'opus_bytes': len(new)}
            temporary = path.with_name(path.name + '.opus-part')
            temporary.write_bytes(new)
            os.replace(temporary, path)
            changed[PREFIX + relative] = {'sha256': digest(new), 'bytes': len(new), 'seconds': timing}
    if args.apply:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(dict(sorted(manifest.items())), indent=1) + '\n')
    rows = update_receipts(changed) if args.apply else 0
    mode = 'Converted' if args.apply else 'Would convert'
    print(f'{mode} {converted} clips: {before / 1e6:.2f} MB of Vorbis to {after / 1e6:.2f} MB of Opus'
          + (f' ({100 - after * 100 / before:.0f}% smaller)' if before else '')
          + f'; {skipped} already Opus; {rows} receipt rows updated.')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
