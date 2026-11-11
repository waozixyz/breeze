#!/usr/bin/env python3
"""Repair guide Opus playback gain, preserving speech packets and QA provenance."""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guide_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    media = speech.writable_media().resolve()
    backup = media / 'backup/guide-headroom'
    if subprocess.run(['git', '-C', str(media), 'check-ignore', '-q', str(backup / 'probe')]).returncode:
        raise SystemExit('Guide headroom backup must be ignored')
    config = json.loads(speech.CONFIG.read_text())
    config['keys'] = speech.narration_keys(config)
    receipt = json.loads(speech.RECEIPT.read_text())
    repaired = 0
    output = ROOT / 'build/guide-headroom'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as folder:
        candidate = Path(folder) / 'clip.ogg'
        for code, key, text in speech.wanted(config, speech.locale_codes(), config['keys']):
            path = speech.clip_path(code, key)
            original = path.read_bytes()
            row = receipt['clips'][code + '/' + key]
            stats = speech.encoded_audio_stats(path)
            peak = max(rate['peak'] for rate in stats['rates'].values())
            if peak < 1:
                continue
            # Local speaker/context proofs require their own QA workflow.
            if (row.get('synthesis') is not None or
                    speech.digest(original) != row['sha256'] or
                    speech.text_hash(config, text, code) != row['text_sha256'] or
                    abs(stats['frames'] / speech.ogg_opus.OPUS_RATE - row['seconds']) > .05 or
                    not .5 <= row['seconds'] <= speech.maximum_clip_seconds(config, key) or
                    speech.assessment(config, code, text, row['transcript'], row['seconds'])[0] < config['minimum_match']):
                raise ValueError(f'{code}/{key}: source recording does not match its QA receipt')
            body = 27 + original[26]
            previous = int.from_bytes(original[body + 16:body + 18], 'little', signed=True)
            gain = previous + math.floor(5120 * math.log10(.9 / peak))
            corrected = speech.ogg_opus.attenuate(original, gain)
            candidate.write_bytes(corrected)
            decoded = speech.encoded_audio_stats(candidate)
            if (decoded['frames'] != stats['frames'] or
                    any(rate['peak'] >= 1 for rate in decoded['rates'].values())):
                raise ValueError(f'{code}/{key}: corrected audio failed validation')
            updated = copy.deepcopy(row)
            updated.update(sha256=speech.digest(corrected), bytes=len(corrected))
            updated['encoding_headroom'] = dict(
                method='opus_header_output_gain', source_sha256=row['sha256'],
                previous_gain_q8=previous, gain_q8=gain, frames=stats['frames'],
                source_peak=peak, decoded=decoded,
                speech_packets_unchanged=True, transcript_source_sha256=row['sha256'])
            if args.apply:
                saved = backup / path.resolve().relative_to(media)
                saved.parent.mkdir(parents=True, exist_ok=True)
                if saved.exists() and saved.read_bytes() != original:
                    raise ValueError(f'{code}/{key}: different source backup already exists')
                saved.write_bytes(original)
                temporary = path.with_name(path.name + '.headroom-part')
                temporary.write_bytes(corrected)
                temporary.replace(path)
                receipt['clips'][code + '/' + key] = updated
                speech.save(receipt)
            repaired += 1
    print(f'{"Repaired" if args.apply else "Would repair"} {repaired} guide clips; speech packets and timing preserved.')


if __name__ == '__main__':
    main()
