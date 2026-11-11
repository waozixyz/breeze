"""Real Opus output safety, complete decode and bounded cached-PCM encoding."""
from array import array
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ogg_opus
spec = importlib.util.spec_from_file_location('encoding_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


class EncodingHeadroomTests(unittest.TestCase):
    def setUp(self):
        output = ROOT / 'build/narration-encoding-headroom-test'
        output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.config = dict(model='fixture', voice='fixture', pcm_sample_rate=16000,
                           sample_rate=16000, vorbis_bitrate='32k', opus_bitrate='16k',
                           transcriber='fixture', minimum_match=.92)

    def folder_for(self, name):
        result = self.folder / name
        result.mkdir()
        return result

    def tone(self, amplitude=.95, seconds=1):
        return array('h', (round(32767 * amplitude * math.sin(2 * math.pi * 997 * i / 16000))
                           for i in range(round(16000 * seconds)))).tobytes()

    def legacy_clip(self, pcm=None):
        """An independent encoder without output attenuation, for unsafe fixtures."""
        pcm = self.tone() if pcm is None else pcm
        path = self.folder / 'legacy.ogg'
        result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 's16le',
            '-ar', '16000', '-ac', '1', '-i', 'pipe:0', '-c:a', 'libopus', '-b:a', '16k',
            '-application', 'voip', '-vbr', 'on', '-map_metadata', '-1', '-f', 'ogg', 'pipe:1'],
            input=pcm, capture_output=True, check=True)
        path.write_bytes(ogg_opus.end_trim(result.stdout, len(pcm) // 2 * 3))
        return path

    def row(self, clip):
        return dict(text_sha256=speech.text_hash(self.config, 'Relax.', 'en'),
                    seconds=speech.seconds(clip), sha256=speech.digest(clip.read_bytes()),
                    transcript='Relax.', match=1)

    def change_page(self, data, index, change):
        data = bytearray(data)
        offset, length, _, _ = ogg_opus.pages(data)[index]
        page = data[offset:offset + length]
        change(page)
        page[22:26] = bytes(4)
        page[22:26] = ogg_opus.ogg_crc(page).to_bytes(4, 'little')
        data[offset:offset + length] = page
        return bytes(data)

    def test_real_overshoot_is_attenuated_without_changing_source_or_frames(self):
        original = self.tone()
        unsafe = speech.encoded_audio_stats(self.legacy_clip(original))
        self.assertGreaterEqual(max(x['peak'] for x in unsafe['rates'].values()), 1)
        work = self.folder_for('corrected')
        clip = speech.encode(self.config, original, work)
        proof = json.loads((work / 'encoding-headroom.json').read_text())
        stats = speech.encoded_audio_stats(clip)
        self.assertEqual((work / 'speech.pcm').read_bytes(), original)
        self.assertEqual(proof['source_pcm_sha256'], speech.digest(original))
        self.assertEqual(proof['trimmed_pcm_sha256'], speech.digest((work / 'speech-clip-rate.pcm').read_bytes()))
        self.assertEqual(proof['frames'], stats['frames'])
        self.assertEqual(stats['rates']['48000']['samples'], stats['frames'])
        self.assertLessEqual(len(proof['passes']), 3)
        self.assertGreater(len(proof['passes']), 1)
        self.assertTrue(all(x['peak'] < 1 and x['full_scale_samples'] == 0 for x in stats['rates'].values()))
        gains = [p['gain'] for p in proof['passes']]
        self.assertEqual(gains[0], 1)
        self.assertTrue(all(0 < b < a for a, b in zip(gains, gains[1:])))
        self.assertEqual(proof['passes'][-1]['audio_sha256'], speech.digest(clip.read_bytes()))

    def test_safe_audio_uses_one_pass_and_remains_current(self):
        work = self.folder_for('safe')
        clip = speech.encode(self.config, self.tone(.15), work)
        proof = json.loads((work / 'encoding-headroom.json').read_text())
        self.assertEqual(len(proof['passes']), 1)
        self.assertEqual(proof['passes'][0]['gain'], 1)
        self.assertFalse((work / 'speech-headroom.pcm').exists())
        row = self.row(clip)
        with patch.object(speech, 'clip_path', return_value=clip):
            self.assertTrue(speech.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', 'Relax.'))
            row['seconds'] += .1
            self.assertFalse(speech.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', 'Relax.'))

    def test_header_attenuation_keeps_speech_packets_and_exact_frames(self):
        clip = self.legacy_clip()
        original = clip.read_bytes()
        changed = ogg_opus.attenuate(original, -512)
        header_length = ogg_opus.pages(original)[0][1]
        self.assertEqual(changed[header_length:], original[header_length:])
        self.assertEqual(ogg_opus.opus_frames(changed), ogg_opus.opus_frames(original))
        self.assertEqual(len(changed), len(original))
        clip.write_bytes(changed)
        stats = speech.encoded_audio_stats(clip)
        self.assertTrue(all(rate['peak'] < 1 for rate in stats['rates'].values()))
        self.assertEqual(ogg_opus.attenuate(changed, -512), changed)
        with self.assertRaises(ValueError):
            ogg_opus.attenuate(changed, 0)
        with self.assertRaises(ValueError):
            ogg_opus.attenuate(changed, -32769)
        damaged = bytearray(original)
        damaged[22] ^= 1
        with self.assertRaises(ValueError):
            ogg_opus.attenuate(bytes(damaged), -512)

    def test_real_native_overshoot_is_rejected_even_when_16k_is_safe(self):
        clip = self.legacy_clip()
        before = speech.encoded_audio_stats(clip)
        low, high = (before['rates'][r]['peak'] for r in ('16000', '48000'))
        self.assertGreater(high, low)
        gain_db = 20 * math.log10(1 / math.sqrt(low * high))
        gain_q8 = round(gain_db * 256)
        def output_gain(page):
            header = 27 + page[26]
            page[header + 16:header + 18] = gain_q8.to_bytes(2, 'little', signed=True)
        clip.write_bytes(self.change_page(clip.read_bytes(), 0, output_gain))
        stats = speech.encoded_audio_stats(clip)
        self.assertLess(stats['rates']['16000']['peak'], 1)
        self.assertGreaterEqual(stats['rates']['48000']['peak'], 1)
        row = self.row(clip)
        with patch.object(speech, 'clip_path', return_value=clip):
            self.assertFalse(speech.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', 'Relax.'))

    def test_silence_is_rejected_before_opus_encoding(self):
        work = self.folder_for('silent')
        with patch.object(speech.subprocess, 'run', wraps=subprocess.run) as run:
            with self.assertRaisesRegex(ValueError, 'no complete speech samples'):
                speech.encode(self.config, bytes(32000), work)
        self.assertEqual(run.call_count, 1)
        self.assertFalse((work / 'clip.ogg').exists())

    def test_overshoot_after_three_passes_is_a_hard_failure(self):
        work = self.folder_for('bounded')
        observed = dict(frames=48000, rates={'16000': dict(peak=1.1), '48000': dict(peak=1.2)})
        with patch.object(speech, 'encoded_audio_stats', return_value=observed) as check:
            with self.assertRaisesRegex(ValueError, 'three bounded passes'):
                speech.encode(self.config, self.tone(), work)
        self.assertEqual(check.call_count, 3)
        proof = json.loads((work / 'encoding-headroom.json').read_text())
        self.assertEqual(len(proof['passes']), 3)
        self.assertEqual((work / 'speech.pcm').read_bytes(), self.tone())
        self.assertTrue(all(0 < p['gain'] <= 1 for p in proof['passes']))

    def test_truncation_checksum_eos_and_false_granule_are_rejected(self):
        clip = self.legacy_clip(self.tone(.15))
        original = clip.read_bytes()
        def remove_eos(page):
            page[5] &= ~4
        def extend_granule(page):
            frames = int.from_bytes(page[6:14], 'little', signed=True) + 48000
            page[6:14] = frames.to_bytes(8, 'little', signed=True)
        damaged = bytearray(original)
        damaged[-1] ^= 1
        cases = [original[:-5], bytes(damaged), self.change_page(original, -1, remove_eos),
                 self.change_page(original, -1, extend_granule)]
        for data in cases:
            with self.subTest(bytes=len(data)):
                clip.write_bytes(data)
                with self.assertRaises((ValueError, subprocess.SubprocessError)):
                    speech.encoded_audio_stats(clip)

    def test_nonfinite_partial_and_missing_decoded_samples_are_rejected(self):
        clip = self.legacy_clip(self.tone(.15))
        cases = [(array('f', [float('nan')] * 16000).tobytes(), 'Nonfinite'),
                 (array('f', [0.] * 10).tobytes(), 'Incomplete Opus'),
                 (b'x', 'Incomplete decoded')]
        for raw, error in cases:
            with self.subTest(error=error), patch.object(speech.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], 0, raw, b'')):
                with self.assertRaisesRegex(ValueError, error):
                    speech.encoded_audio_stats(clip)

    def test_decoder_failure_is_not_current_and_short_duration_is_not_accepted(self):
        clip = self.legacy_clip(self.tone(.15))
        row = self.row(clip)
        with patch.object(speech, 'clip_path', return_value=clip), patch.object(speech.subprocess, 'run',
                side_effect=subprocess.CalledProcessError(1, ['ffmpeg'])):
            self.assertFalse(speech.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', 'Relax.'))
        row['seconds'] = .2
        with patch.object(speech, 'clip_path', return_value=clip):
            self.assertFalse(speech.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', 'Relax.'))


if __name__ == '__main__':
    unittest.main()
