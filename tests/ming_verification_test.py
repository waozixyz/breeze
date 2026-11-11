"""Pinned ASR routing, complete audio and unchanged speech-cache identity."""
from contextlib import nullcontext
from array import array
import copy
import gc
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import ming_narration as ming
import ming_verification as qa
import ming_narration_test as fixtures


class VerificationTests(unittest.TestCase):
    def setUp(self):
        fixtures.MingTests.setUp(self)
        self.original = copy.deepcopy(self.profile)
        self.local['verification_models'] = {model: self.local['asr'] for model in qa.MODELS}
        self.local_path.write_text(json.dumps(self.local))
        routes = {}
        for code in qa.LANGUAGES:
            model = 'openai/whisper-large-v3-turbo' if code in ('ja', 'ko') else 'openai/whisper-small'
            routes[code] = dict(model=model, revision=qa.MODELS[model],
                                artifacts=copy.deepcopy(self.profile['artifacts']['asr']))
        self.profile['verification'] = dict(mode='per-locale-whisper-v1', routes=routes,
                                            adapter_sha256=ming.file_hash(qa.__file__))

    def test_qa_upgrade_preserves_exact_original_generation_profile_and_cache_keys(self):
        qa.validate(self.profile)
        self.assertEqual(qa.synthesis_profile(self.profile), self.original)
        self.assertEqual(qa.provenance(self.profile), ming.provenance(self.original))
        self.assertEqual(qa.text_hash(self.config, 'Exact source.', self.profile, 'ja'),
                         ming.text_hash(self.config, 'Exact source.', self.original, 'ja'))
        with patch.object(ming, 'Engine') as generation:
            generation.return_value.speak.return_value = (b'original PCM', ming.provenance(self.original))
            engine = qa.Engine(self.profile, self.local_path)
            generation.assert_called_once_with(self.original, self.local_path)
            self.assertEqual(engine.speak(self.config, 'Exact source.', 'ja', self.folder, 0),
                             (b'original PCM', ming.provenance(self.original)))

    def test_cached_only_fails_before_any_new_speech_if_original_pcm_is_missing(self):
        with patch.object(ming, 'Engine') as generation:
            engine = qa.Engine(self.profile, self.local_path)
            with self.assertRaisesRegex(RuntimeError, 'Cached-only QA requires'):
                engine.speak(dict(self.config, _cached_only=True), 'Unique missing cached fixture.',
                             'ja', self.folder, 0)
            generation.return_value.speak.assert_not_called()

    def test_routes_pin_model_revision_and_artifacts_before_loading(self):
        for code in qa.LANGUAGES:
            route = self.profile['verification']['routes'][code]
            self.assertEqual(route['model'].endswith('turbo'), code in ('ja', 'ko'))
            changed = copy.deepcopy(self.profile)
            changed['verification']['routes'][code]['revision'] = 'wrong'
            with self.assertRaises(ValueError):
                qa.Engine(changed, self.local_path)
        changed = copy.deepcopy(self.profile)
        changed['verification']['routes']['ja']['artifacts']['fixture'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'Changed verification model artifact'):
            qa.Engine(changed, self.local_path)

    def test_switch_releases_prior_recognizer_and_uses_actual_selected_identity(self):
        clip = self.folder / 'audio.ogg'
        clip.write_bytes(b'fixture not decoded by recognizer double')
        live = []
        models = []

        def construct(path, route, threads):
            gc.collect()
            self.assertTrue(all(reference() is None for reference in live))
            models.append(route['model'])
            class Fake:
                def transcribe(inner, path, code):
                    return dict(text='Exact source.', language=code, model=route['model'],
                                revision=route['revision'], audio_sha256=ming.file_hash(path),
                                artifacts_sha256=ming.json_hash(route['artifacts']),
                                seconds=2, input_samples=32000, truncation=False, long_form=True)
            instance = Fake()
            live.append(weakref.ref(instance))
            return instance

        with patch.object(qa, 'Recognizer', side_effect=construct):
            engine = qa.Engine(self.profile, self.local_path)
            for code in ('ja', 'ko', 'ja', 'de', 'en', 'ko', 'ja'):
                self.assertEqual(engine.transcribe(clip, code), 'Exact source.')
                identity = qa.verification_identity(self.profile, code)
                self.assertTrue(qa.verified_transcription(self.profile, code,
                                                       engine.last_transcription, identity))
            self.assertEqual(models, ['openai/whisper-large-v3-turbo', 'openai/whisper-small',
                                      'openai/whisper-large-v3-turbo'])

    def test_receipt_rejects_small_relabel_wrong_revision_artifacts_or_partial_audio(self):
        identity = qa.verification_identity(self.profile, 'ja')
        row = dict(language='ja', model=identity['model'], revision=identity['revision'],
                   artifacts_sha256=identity['artifacts_sha256'], seconds=40, input_samples=640000)
        self.assertTrue(qa.verified_transcription(self.profile, 'ja', row, identity))
        for key, bad in [('model', 'openai/whisper-small'), ('revision', 'wrong'),
                         ('artifacts_sha256', '0' * 64), ('input_samples', 480000),
                         ('language', 'en')]:
            with self.subTest(key=key):
                self.assertFalse(qa.verified_transcription(self.profile, 'ja', dict(row, **{key: bad}), identity))
        self.assertFalse(qa.verified_transcription(self.profile, 'ja', row, {}))

    def test_current_receipt_binds_new_actual_verifier_to_original_speech_and_encoded_audio(self):
        speech = fixtures.speech
        clip = speech.encode(self.config, array('h', [1000, -1000] * 24000).tobytes(), self.folder)
        length = speech.seconds(clip)
        text = '左脚を後ろに引き、膝を床へ。'
        identity = qa.verification_identity(self.profile, 'ja')
        row = dict(text_sha256=qa.text_hash(self.config, text, self.profile, 'ja'),
                   sha256=ming.file_hash(clip), seconds=length, transcript=text,
                   synthesis=ming.provenance(self.original), speaker_cosine=0.9,
                   transcriber=qa.transcriber(self.profile, 'ja'), verification=identity,
                   transcription=dict(text=text, language='ja', model=identity['model'],
                       revision=identity['revision'], artifacts_sha256=identity['artifacts_sha256'],
                       audio_sha256=ming.file_hash(clip), seconds=length, input_samples=round(length*16000),
                       truncation=False, long_form=True))
        receipt = dict(clips={'ja/cue': row})
        with patch.object(speech, 'clip_path', return_value=clip):
            self.assertTrue(speech.current(receipt, self.config, 'ja', 'cue', text))
            for field, value in [('model', 'openai/whisper-small'), ('revision', 'unverified'),
                                 ('artifacts_sha256', '0'*64), ('text', '酒区を後ろに引き、膝を床へ。'),
                                 ('input_samples', 16000), ('truncation', True)]:
                original = row['transcription'][field]
                row['transcription'][field] = value
                self.assertFalse(speech.current(receipt, self.config, 'ja', 'cue', text), field)
                row['transcription'][field] = original
            row.pop('verification')
            self.assertFalse(speech.current(receipt, self.config, 'ja', 'cue', text))

    def test_unchanged_locale_keeps_pinned_prior_qa_but_korean_small_is_rejected(self):
        previous = copy.deepcopy(self.profile)
        previous['verification']['adapter_sha256'] = 'd' * 64
        previous['verification']['routes']['ko']['model'] = 'openai/whisper-small'
        previous['verification']['routes']['ko']['revision'] = qa.MODELS['openai/whisper-small']
        self.profile['verification']['compatible'] = {
            code: [qa.verification_identity(previous, code)] for code in ('ja', 'en')}
        qa.validate(self.profile)
        for code in ('ja', 'en'):
            old = qa.verification_identity(previous, code)
            row = dict(language=code, model=old['model'], revision=old['revision'],
                       artifacts_sha256=old['artifacts_sha256'], seconds=2, input_samples=32000)
            self.assertTrue(qa.verified_transcription(self.profile, code, row, old))
            self.assertFalse(qa.verified_transcription(self.profile, code, row,
                                                     dict(old, adapter_sha256='f'*64)))
        old = qa.verification_identity(previous, 'ko')
        row = dict(language='ko', model=old['model'], revision=old['revision'],
                   artifacts_sha256=old['artifacts_sha256'], seconds=2, input_samples=32000)
        self.assertFalse(qa.verified_transcription(self.profile, 'ko', row, old))
        self.profile['verification']['compatible']['ko'] = [old]
        with self.assertRaisesRegex(ValueError, 'same actual locale model'):
            qa.validate(self.profile)

    def test_recognizer_receives_all_40_seconds_without_source_text(self):
        import numpy  # Available in the native offline speech runtime.
        wav = self.folder / 'long.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'sine=frequency=220:duration=40', '-ar', '16000', '-ac', '1', str(wav)], check=True)
        calls = {}

        class Processor:
            def __call__(inner, audio, **kwargs):
                calls.update(samples=len(audio), processor=kwargs)
                return SimpleNamespace(input_features='all features', attention_mask='all samples')

            def batch_decode(inner, tokens, **kwargs):
                return ['Complete blind transcript.']

        def generate(**kwargs):
            calls['generate'] = kwargs
            return [1]

        recognizer = qa.Recognizer.__new__(qa.Recognizer)
        recognizer.processor = Processor()
        recognizer.model = SimpleNamespace(generate=generate)
        recognizer.torch = SimpleNamespace(inference_mode=nullcontext)
        recognizer.route = self.profile['verification']['routes']['ja']
        row = recognizer.transcribe(wav, 'ja')
        self.assertEqual(row['input_samples'], 640000)
        self.assertEqual(row['model'], 'openai/whisper-large-v3-turbo')
        self.assertEqual(row['audio_sha256'], ming.file_hash(wav))
        self.assertFalse(calls['processor']['truncation'])
        self.assertTrue(calls['generate']['return_timestamps'])
        self.assertNotIn('prompt_ids', calls['generate'])
        self.assertNotIn('expected', calls['generate'])


if __name__ == '__main__':
    unittest.main()
