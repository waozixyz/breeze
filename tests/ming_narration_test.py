"""Offline adapter contracts. Synthetic test audio never enters practice media."""
from array import array
from contextlib import nullcontext
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ming_narration as ming
import whisper_narration as whisper
import practice_media
spec = importlib.util.spec_from_file_location('narration', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


class MingTests(unittest.TestCase):
    def setUp(self):
        output = ROOT / 'build/ming-narration-test'
        output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.local = {}
        manifests = {}
        for kind in ('runtime', 'model', 'asr'):
            directory = self.folder / kind
            directory.mkdir()
            artifact = directory / 'fixture'
            artifact.write_bytes(b'local unit fixture')
            self.local[kind] = str(directory)
            manifests[kind] = {'fixture': ming.file_hash(artifact)}
        for kind in ('reference', 'embedding'):
            artifact = self.folder / kind
            artifact.write_bytes(kind.encode())
            self.local[kind] = str(artifact)
        self.profile = dict(schema=1, model=ming.MODEL, model_revision=ming.MODEL_REVISION,
                            runtime_revision=ming.RUNTIME_REVISION, task='FREEFORM',
                            instruction='Calm meditation delivery.', minimum_speaker_cosine=0.7,
                            reference_sha256=ming.file_hash(self.local['reference']),
                            embedding_sha256=ming.file_hash(self.local['embedding']),
                            transcriber='unit fixture only', artifacts=manifests,
                            adapter_sha256=ming.file_hash(ROOT / 'scripts/ming_narration.py'),
                            segmenter_sha256=ming.file_hash(ROOT / 'scripts/narration_segments.py'),
                            segmentation=dict(version=1, maximum_units=24, pause_ms=0,
                                assembly='concatenate', seed_rule='base+attempt*1000003+span',
                                minimum_decode_budget_seconds=16),
                            asr_adapter_sha256=ming.file_hash(ROOT / 'scripts/whisper_narration.py'))
        self.local_path = self.folder / 'local.json'
        self.local_path.write_text(json.dumps(self.local))
        self.config = json.loads((ROOT / 'design/astral-projection/bruce-narration.json').read_text())
        self.config['ming'] = self.profile

    def test_explicit_language_and_reference_for_every_supported_locale(self):
        for code in ming.LANGUAGES:
            request = ming.request_arguments(self.profile, 'Exact supplied words.', code, 'female.pt')
            self.assertEqual(request['language_id'], code)
            self.assertEqual(request['spk_emb_path'], 'female.pt')
            self.assertTrue(request['use_spk_emb'])
            self.assertEqual(request['task'], 'FREEFORM')
            self.assertNotIn('controls', request)
            self.assertNotIn('use_zero_spk_emb', request)
        for code in ('cs', 'id', 'it', 'pt', 'ru'):
            with self.assertRaises(ValueError):
                ming.request_arguments(self.profile, 'Words.', code, 'female.pt')

    def test_preflight_hashes_actual_files_and_never_loads_models(self):
        with patch.object(ming.Engine, 'load', side_effect=AssertionError('Unexpected model load')):
            ming.Engine(self.profile, self.local_path)
            Path(self.local['model'], 'fixture').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Changed local Ming artifact'):
                ming.Engine(self.profile, self.local_path)

    def test_reference_and_adapter_changes_rejected(self):
        for field in ('reference_sha256', 'embedding_sha256', 'adapter_sha256', 'asr_adapter_sha256',
                      'segmenter_sha256'):
            changed = copy.deepcopy(self.profile)
            changed[field] = '0' * 64
            with self.assertRaises(ValueError):
                ming.Engine(changed, self.local_path)

    def test_cli_rejects_male_and_unsupported_locale_before_generation(self):
        base = [sys.executable, str(ROOT / 'scripts/generate-lumi-guide-narration.py'),
                '--check', '--ming-profile', str(self.local_path)]
        for arguments, message in [(['--practice', 'taichi_male'], 'must not overwrite male'),
                                   (['--locale', 'cs'], 'no fallback is performed')]:
            result = subprocess.run(base + arguments, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(message, result.stderr)

    def test_supported_regeneration_preserves_other_locale_receipts(self):
        config = dict(self.config, keys=['cue'])
        config.pop('keys_file')
        config_path = self.folder / 'narration.json'
        config_path.write_text(json.dumps(config))
        receipt_path = self.folder / 'receipt.json'
        content_path = self.folder / 'apps/practice/content.json'
        content_path.parent.mkdir(parents=True)
        content_path.write_text(json.dumps({'narration': {'guide': {}}}))
        unsupported = dict(bytes=7, sha256='unchanged legacy fixture')
        receipt_path.write_text(json.dumps({'clips': {'cs/cue': unsupported}}))
        rows = [('en', 'cue', 'Relax.'), ('cs', 'cue', 'Uvolněte se.')]
        generated = dict(bytes=8, seconds=2, match=1)
        with patch.object(speech, 'ROOT', self.folder), \
                patch.object(speech, 'CONFIG', config_path), \
                patch.object(speech, 'RECEIPT', receipt_path), \
                patch.object(speech, 'VOICE', self.folder / 'voice'), \
                patch.object(speech, 'MEDIA_ROOT', None), \
                patch.object(speech, 'writable_media', return_value=self.folder), \
                patch.object(speech, 'locale_codes', return_value=['en', 'cs']), \
                patch.object(speech, 'wanted', side_effect=lambda cfg, codes, keys: [row for row in rows if row[0] in codes]), \
                patch.object(speech.ming_narration, 'Engine', return_value=SimpleNamespace(profile=self.profile)), \
                patch.object(speech, 'generate', return_value=generated) as generate, \
                patch.object(sys, 'argv', ['generate', '--ming-profile', str(self.local_path)]):
            speech.main()
        updated = json.loads(receipt_path.read_text())
        self.assertEqual(updated['clips']['cs/cue'], unsupported)
        self.assertEqual(updated['clips']['en/cue'], generated)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(generate.call_args.args[2], 'en')

    def test_metadata_uses_frozen_media_root_after_package_graph_changes(self):
        stable = self.folder / 'canonical'
        cache = self.folder / 'different-package'
        target = stable / 'astral_projection/voice/en/cue.ogg'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'fixture')
        cache.mkdir()
        with patch.object(practice_media, 'MEDIA', cache):
            self.assertEqual(practice_media.packaged_path(target, stable),
                             'assets/practices/astral_projection/voice/en/cue.ogg')
            with self.assertRaises(ValueError):
                practice_media.packaged_path(target)

    def test_receipt_resume_identity_and_complete_audio_binding(self):
        target = self.folder / 'test.ogg'
        # The fixture is an actual mono Opus recording with measured end trim.
        pcm = array('h', [int(4000 * math.sin(index * 2 * math.pi * 220 / 24000))
                          for index in range(24000 * 2)]).tobytes()
        clip = speech.encode(self.config, pcm, self.folder)
        target.write_bytes(clip.read_bytes())
        text = 'Relax your hands and keep breathing naturally.'
        length = speech.seconds(target)
        row = dict(text_sha256=ming.text_hash(self.config, text, self.profile, 'de'),
                   sha256=ming.file_hash(target), seconds=length, transcript=text,
                   synthesis=ming.provenance(self.profile), speaker_cosine=0.9,
                   transcriber=self.profile['transcriber'],
                   transcription=dict(audio_sha256=ming.file_hash(target),
                                      seconds=length, truncation=False, long_form=True))
        receipt = {'clips': {'de/cue': row}}
        with patch.object(speech, 'clip_path', return_value=target):
            self.assertTrue(speech.current(receipt, self.config, 'de', 'cue', text))
            self.assertFalse(speech.current(receipt, self.config, 'de', 'cue', text + ' Changed.'))
            self.assertFalse(speech.current(receipt, self.config, 'cs', 'cue', text))
            receipt['clips']['en/cue'] = row
            self.assertFalse(speech.current(receipt, self.config, 'en', 'cue', text))
            with patch.object(ming, 'file_hash', return_value='0' * 64):
                self.assertFalse(speech.current(receipt, self.config, 'de', 'cue', text))
            original_arguments = ming.request_arguments

            def changed_arguments(*args):
                return dict(original_arguments(*args), temperature=0.1)

            with patch.object(ming, 'request_arguments', side_effect=changed_arguments):
                self.assertFalse(speech.current(receipt, self.config, 'de', 'cue', text))
            for field, value in [('speaker_cosine', float('nan')), ('speaker_cosine', 0.1),
                                 ('synthesis', {}), ('transcription', {'seconds': 30})]:
                original = row[field]
                row[field] = value
                self.assertFalse(speech.current(receipt, self.config, 'de', 'cue', text))
                row[field] = original
            changed = copy.deepcopy(self.config)
            changed['ming']['instruction'] = 'Different delivery.'
            self.assertFalse(speech.current(receipt, changed, 'de', 'cue', text))
            target.write_bytes(b'corrupted')
            self.assertFalse(speech.current(receipt, self.config, 'de', 'cue', text))

    def test_quiet_time_and_long_cue_tail_are_checked(self):
        config = dict(maximum_clip_seconds=50, maximum_clip_seconds_by_key={'cue': 45},
                      cue_interval_seconds_by_key={'cue': 120}, quiet_after_seconds_by_key={'cue': 80})
        with self.assertRaisesRegex(ValueError, 'reserved quiet time'):
            speech.maximum_clip_seconds(config, 'cue')
        text = ('Keep your attention relaxed. ' * 80) + 'Return to your body and open your eyes.'
        truncated = text[:-40]
        self.assertGreater(speech.verified_match({}, 'en', text, truncated), 0.92)
        self.assertEqual(speech.complete_match({}, 'en', text, truncated, 45, True), 0)
        self.assertEqual(speech.complete_match({}, 'en', text, text, 45, True), 1)

    def test_short_german_pilot_missing_final_clause_is_rejected(self):
        expected = ('Willkommen. Dies ist Grundberührung, eine vorbereitende Übung für '
                    'Körperbewusstsein nach Bruces Art. Sitze bequem oder liege, die Hände '
                    'mit den Handflächen nach unten ruhend und die Finger leicht gespreizt. '
                    'Lass deine Augen sich schließen. Du darfst das Ziel kurz berühren, '
                    'wenn ich dich dazu einlade, aber lass deinen physischen Körper sonst '
                    'still bleiben. Dies ist ein Training, kein Test. Kribbeln, Wärme, '
                    'Druck oder gar nichts – alles ist akzeptabel.')
        heard = (expected[:expected.index('Kribbeln,')] + 'Kribbeln, werden.').replace(
            'Bruces Art', 'brusches Art').replace('nach unten ruhend', 'nach unten ruhen')
        self.assertAlmostEqual(speech.verified_match(self.config, 'de', expected, heard),
                               0.9295774647887324)
        self.assertEqual(speech.complete_match(self.config, 'de', expected, heard, 23.065, True), 0)
        self.assertEqual(speech.complete_match({}, 'en', 'Welcome. All sensations are acceptable.',
                                              'Welcome! All sensations are acceptable!', 24.008, True), 1)
        alias = {'homophones': {'de': {'Ming': 'Mingh'}}}
        self.assertEqual(speech.complete_match(alias, 'de', 'Ruhig mit Ming.',
                                              'Ruhig mit Mingh!', 3, True), 1)

        # Exercise both resume and new-generation acceptance, using a real Opus
        # fixture while keeping all synthetic audio outside production media.
        pcm = array('h', [int(4000 * math.sin(index * 2 * math.pi * 220 / 24000))
                          for index in range(48000)]).tobytes()
        clip = speech.encode(self.config, pcm, self.folder)
        length = speech.seconds(clip)
        synthesis = ming.provenance(self.profile)
        row = dict(text_sha256=ming.text_hash(self.config, expected, self.profile, 'de'),
                   sha256=ming.file_hash(clip), seconds=length, transcript=heard,
                   synthesis=synthesis, speaker_cosine=0.9, transcriber=self.profile['transcriber'],
                   transcription=dict(audio_sha256=ming.file_hash(clip), seconds=length,
                                      truncation=False, long_form=True))
        with patch.object(speech, 'clip_path', return_value=clip):
            self.assertFalse(speech.current({'clips': {'de/cue': row}}, self.config,
                                            'de', 'cue', expected))
        engine = SimpleNamespace(profile=self.profile, speak=lambda *args: (b'pcm', synthesis),
                                 speaker_match=lambda path: 0.9,
                                 transcribe=lambda path, code: heard, last_transcription=row['transcription'])
        with patch.object(speech, 'ATTEMPTS', 1), patch.object(speech, 'encode', return_value=clip):
            with self.assertRaisesRegex(RuntimeError, 'never matched'):
                speech.generate(dict(self.config, _ming_engine=engine), None, 'de', 'cue', expected)

    def test_whisper_receives_all_40_seconds_with_no_text_hints(self):
        wav = self.folder / 'long.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'sine=frequency=220:duration=40', '-ar', '16000', '-ac', '1', str(wav)], check=True)
        calls = {}

        class Processor:
            def __call__(self, audio, **kwargs):
                calls['samples'] = len(audio)
                calls['processor'] = kwargs
                return SimpleNamespace(input_features='all features', attention_mask='all samples')

            def batch_decode(self, tokens, **kwargs):
                return ['unit transcript only']

        def generate(**kwargs):
            calls['generate'] = kwargs
            return [1]

        recognizer = whisper.Transcriber.__new__(whisper.Transcriber)
        recognizer.processor = Processor()
        recognizer.model = SimpleNamespace(generate=generate)
        recognizer.torch = SimpleNamespace(inference_mode=nullcontext)
        for code in ('de', 'ru', 'cs'):
            result = recognizer.transcribe(wav, code)
            self.assertEqual(calls['generate']['language'], code)
        self.assertEqual(calls['samples'], 640000)
        self.assertFalse(calls['processor']['truncation'])
        self.assertEqual(calls['processor']['padding'], 'longest')
        self.assertTrue(calls['generate']['return_timestamps'])
        self.assertNotIn('prompt_ids', calls['generate'])
        self.assertEqual(result['seconds'], 40)
        self.assertEqual(result['audio_sha256'], ming.file_hash(wav))


if __name__ == '__main__':
    unittest.main()
