"""Generic context proof dispatch and binary publication boundaries."""
import copy
from array import array
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys
import wave

import ming_narration_test as fixtures

speech, ROOT = fixtures.speech, fixtures.ROOT


class ContextPipelineTests(unittest.TestCase):
    def setUp(self):
        fixtures.MingTests.setUp(self)
        self.media = self.folder / 'media'
        self.voice = self.media / 'sunsalutation/voice'
        self.voice.mkdir(parents=True)
        staging = ROOT / 'backup/narration/tmp'
        staging.mkdir(parents=True, exist_ok=True)
        self.sources = tempfile.TemporaryDirectory(dir=staging, prefix='context-unit-')
        self.addCleanup(self.sources.cleanup)
        self.source = Path(self.sources.name) / 'parent.wav'
        with wave.open(str(self.source), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b'\x01\x00' * 48000)
        self.checksum = speech.ming_narration.file_hash(self.source)
        self.artifact = dict(source=str(self.source), sha256=self.checksum,
            destination_relative='sunsalutation/voice-context/es/' + self.checksum + '.wav')
        self.proof = dict(scope='context_parent', actual_clip_cosine=0.25,
                          parent_cosine=0.8, recipe_sha256='a'*64)
        self.row = dict(speaker_cosine=0.25, speaker_verification=self.proof)
        self.addCleanup(patch.stopall)
        patch.object(speech, 'MEDIA_ROOT', self.media).start()
        patch.object(speech, 'VOICE', self.voice).start()

    def test_ordinary_thresholds_and_actual_context_scores_stay_distinct(self):
        module = speech.LOCAL_PROVIDERS['ming']
        with patch.object(speech, 'verify_context_speaker', return_value=True) as verify:
            self.assertTrue(speech.verified_speaker(self.config, module, self.profile, 'es',
                                                  'Inhale.', self.row, self.source))
            self.assertEqual(verify.call_args.args[4]['speaker_cosine'], 0.25)
            self.assertEqual(verify.call_args.args[4]['speaker_verification']['parent_cosine'], 0.8)
            self.assertFalse(speech.verified_speaker(self.config, module, self.profile, 'es',
                                                   'Inhale.', dict(speaker_cosine=0.69), self.source))
            self.assertTrue(speech.verified_speaker(self.config, module, self.profile, 'es',
                                                  'Inhale.', dict(speaker_cosine=0.7), self.source))
            bad = dict(self.row, speaker_verification=dict(self.proof, parent_cosine=0.69))
            self.assertFalse(speech.verified_speaker(self.config, module, self.profile, 'es',
                                                   'Inhale.', bad, self.source))
            # A Ming proof cannot authorize a locale served by another adapter.
            profile = dict(self.profile, minimum_speaker_cosine=0.65)
            for code in ('pt', 'cs', 'ru'):
                self.assertFalse(speech.verified_speaker(self.config, module, profile, code,
                                                       'Inspire.', bad, self.source))

    def test_context_gate_uses_selected_enabled_adapter_for_all_ten_locales(self):
        config = json.loads((ROOT / 'design/workout/narration.json').read_text())
        expected = {'en': 'ming', 'es': 'ming', 'cs': 'chatterbox-czech', 'de': 'ming',
                    'fr': 'ming', 'pt': 'chatterbox-portuguese', 'ru': 'f5-russian',
                    'ja': 'ming', 'ko': 'ming', 'zh': 'ming'}
        with patch.object(speech, 'verify_context_speaker', return_value=True) as verify:
            for code, provider in expected.items():
                with self.subTest(code=code, provider=provider):
                    module = speech.LOCAL_PROVIDERS[provider]
                    profile = module.descriptor(config)
                    row = dict(self.row, speaker_verification=dict(self.proof, parent_cosine=0.8))
                    self.assertIs(speech.local_adapter(config, code), module)
                    self.assertTrue(speech.verified_speaker(config, module, profile, code, 'cue', row, self.source))
                    verify.assert_called()
                    disabled = dict(config)
                    disabled.pop('ming' if provider == 'ming' else module.KEY)
                    self.assertFalse(speech.verified_speaker(disabled, module, profile, code, 'cue', row, self.source))
                    wrong = next(m for m in speech.LOCAL_PROVIDERS.values() if m is not module)
                    self.assertFalse(speech.verified_speaker(config, wrong, profile, code, 'cue', row, self.source))
                    self.assertFalse(speech.verified_speaker(config, module, dict(profile, minimum_speaker_cosine=0.1),
                                                            code, 'cue', row, self.source))
                    for value in (profile['minimum_speaker_cosine'] - 0.001, float('nan')):
                        bad = dict(row, speaker_verification=dict(row['speaker_verification'], parent_cosine=value))
                        self.assertFalse(speech.verified_speaker(config, module, profile, code, 'cue', bad, self.source))
            self.assertFalse(speech.verified_speaker(config, None, {}, 'unknown', 'cue', self.row, self.source))

    def test_missing_unsupported_mismatched_or_rejected_proof_cannot_bypass_speaker_gate(self):
        module = speech.LOCAL_PROVIDERS['ming']
        with patch.object(speech, 'verify_context_speaker', return_value=True):
            for field, value in [('scope', 'clip'), ('actual_clip_cosine', 0.9),
                                 ('parent_cosine', float('nan'))]:
                row = dict(self.row, speaker_verification=dict(self.proof, **{field: value}))
                self.assertFalse(speech.verified_speaker(self.config, module, self.profile,
                                                       'es', 'Inhale.', row, self.source))
            for code in ('de', 'en', 'ja', 'ko'):
                self.assertTrue(speech.verified_speaker(self.config, module, self.profile,
                                                      code, 'Inhale.', self.row, self.source))
        with patch.object(speech, 'verify_context_speaker', return_value=False):
            self.assertFalse(speech.verified_speaker(self.config, module, self.profile,
                                                   'es', 'Inhale.', self.row, self.source))
        with patch.object(speech, 'verify_context_speaker', side_effect=FileNotFoundError):
            self.assertFalse(speech.verified_speaker(self.config, module, self.profile,
                                                   'es', 'Inhale.', self.row, self.source))

    def test_context_recipe_identity_changes_only_explicit_context_rows(self):
        synthesis = speech.LOCAL_PROVIDERS['ming'].provenance(self.profile)
        normal = speech.text_hash(self.config, 'Inhale.', 'es', synthesis)
        self.assertEqual(normal, fixtures.ming.text_hash(self.config, 'Inhale.', self.profile, 'es'))
        contextual = speech.text_hash(self.config, 'Inhale.', 'es', synthesis, self.proof)
        self.assertNotEqual(normal, contextual)
        self.assertNotEqual(contextual, speech.text_hash(self.config, 'Inhale.', 'es', synthesis,
                                                        dict(self.proof, recipe_sha256='b'*64)))
        self.assertEqual('', speech.text_hash(self.config, 'Inhale.', 'es', synthesis, {}))

    def test_binary_parent_copy_is_exact_reusable_and_canonical(self):
        speech.publish_context_artifacts([self.artifact], 'es')
        target = self.media / self.artifact['destination_relative']
        self.assertEqual(self.source.read_bytes(), target.read_bytes())
        timestamp = target.stat().st_mtime_ns
        speech.publish_context_artifacts([self.artifact], 'es')
        self.assertEqual(target.stat().st_mtime_ns, timestamp)
        self.assertEqual(speech.ming_narration.file_hash(target), self.checksum)
        target.write_bytes(b'foreign file must be preserved')
        with self.assertRaises(ValueError):
            speech.publish_context_artifacts([self.artifact], 'es')
        self.assertEqual(target.read_bytes(), b'foreign file must be preserved')

    def test_artifact_source_hash_range_prefix_and_symlink_tampering_are_rejected(self):
        for relative in ('../escape.wav', '/absolute.wav',
                         'sunsalutation/voice/es/' + self.checksum + '.wav',
                         'sunsalutation/voice-context/fr/' + self.checksum + '.wav'):
            with self.assertRaises(ValueError):
                speech.context_artifacts([dict(self.artifact, destination_relative=relative)], 'es')
        with self.assertRaises(ValueError):
            speech.context_artifacts([dict(self.artifact, sha256='0'*64)], 'es')
        outside = self.folder / 'outside.wav'
        outside.write_bytes(self.source.read_bytes())
        with self.assertRaises(ValueError):
            speech.context_artifacts([dict(self.artifact, source=str(outside))], 'es')
        proof_directory = self.media / 'sunsalutation/voice-context'
        proof_directory.parent.mkdir(parents=True, exist_ok=True)
        proof_directory.symlink_to(self.folder)
        with self.assertRaises(ValueError):
            speech.context_artifacts([self.artifact], 'es')

    def test_generate_keeps_short_score_and_raw_asr_copies_binary_then_current_revalidates(self):
        text = 'Inhale naturally.'
        synthesis = speech.LOCAL_PROVIDERS['ming'].provenance(self.profile)
        pcm = array('h', [int(2000*math.sin(index*2*math.pi*220/24000))
                          for index in range(24000)]).tobytes()
        engine = SimpleNamespace(profile=self.profile, context_artifacts=[self.artifact],
            last_speaker_verification=None, last_transcription=None,
            speak=lambda *args: (pcm, synthesis))

        def speaker(clip):
            engine.last_speaker_verification = dict(self.proof,
                                                   clip_sha256=speech.ming_narration.file_hash(clip))
            return 0.25

        def transcribe(clip, code):
            engine.last_transcription = dict(text=text, model='offline fixture', revision='fixture',
                audio_sha256=speech.ming_narration.file_hash(clip), language=code,
                seconds=speech.seconds(clip), truncation=False, long_form=True)
            return text

        engine.speaker_match, engine.transcribe = speaker, transcribe
        config = dict(self.config, _local_engine=engine)
        original_diagnostics = speech.Attempts

        def diagnostic(*args):
            record = original_diagnostics(*args)
            record.path = self.folder / 'generated-diagnostics.json'
            return record

        def verify(config, profile, code, source, row, clip):
            # Proof semantics belong to the shared helper's independent tests.
            return (source == text and row['speaker_verification']['clip_sha256'] ==
                    speech.ming_narration.file_hash(clip) == row['sha256'])

        with patch.object(speech, 'Attempts', side_effect=diagnostic), \
                patch.object(speech, 'verify_context_speaker', side_effect=verify):
            row = speech.generate(config, None, 'es', 'cue', text)
            self.assertEqual(row['speaker_cosine'], 0.25)
            self.assertEqual(row['speaker_verification']['parent_cosine'], 0.8)
            self.assertEqual(row['transcription']['text'], text)
            self.assertEqual(row['synthesis'], synthesis)
            self.assertNotIn('_context_artifacts', row)
            self.assertTrue((self.media / self.artifact['destination_relative']).is_file())
            self.assertTrue(speech.current(dict(clips={'es/cue': row}), config, 'es', 'cue', text))
            diagnostics = json.loads((self.folder/'generated-diagnostics.json').read_text())
            self.assertEqual(diagnostics['attempts'][0]['speaker_cosine'], 0.25)
            self.assertEqual(diagnostics['attempts'][0]['speaker_verification']['parent_cosine'], 0.8)
            row['speaker_verification']['actual_clip_cosine'] = 0.8
            self.assertFalse(speech.current(dict(clips={'es/cue': row}), config, 'es', 'cue', text))

    def test_context_preflight_resolves_media_package_without_a_write_root(self):
        config_file = self.folder / 'narration.json'
        config_file.write_text(json.dumps(self.config))
        constructor = unittest.mock.Mock(return_value=SimpleNamespace(profile=self.profile))
        context_module = SimpleNamespace(ContextEngine=constructor)
        resolve = lambda path: self.media if str(path).startswith('assets/practices/') else ROOT / str(path)
        args = ['generate', '--ming-profile', str(self.local_path), '--preflight',
                '--context-profile', 'design/narration/short-context.json',
                '--context-local-profile', 'backup/narration/context-local.json']
        with patch.object(speech, 'CONFIG', config_file), patch.object(speech, 'MEDIA_ROOT', None), \
                patch.object(speech, 'media_path', side_effect=resolve), \
                patch.object(fixtures.ming, 'Engine', return_value=SimpleNamespace(profile=self.profile)), \
                patch.dict(sys.modules, local_narration_context=context_module), \
                patch.object(sys, 'argv', args):
            speech.main()
        self.assertEqual(constructor.call_args.kwargs['voice_directory'], 'sunsalutation/voice')

    def test_chinese_context_qa_records_actual_route_and_rejects_changed_asr_identity(self):
        import local_narration_context as context
        text = '吸气。'
        module = speech.LOCAL_PROVIDERS['ming']
        synthesis = module.provenance(self.profile)
        route = dict(model='openai/whisper-large-v3-turbo',
                     revision=speech.ming_verification.MODELS['openai/whisper-large-v3-turbo'],
                     artifacts={'fixture': 'b' * 64})
        rule = dict(text=text, crop_asr=route, sha256='a' * 64, policy_sha256='c' * 64)
        pcm = array('h', [int(2000 * math.sin(index * 2 * math.pi * 220 / 24000))
                          for index in range(24000)]).tobytes()
        engine = SimpleNamespace(profile=self.profile, context_artifacts=[],
            last_speaker_verification=None, last_transcription=None,
            speak=lambda *args: (pcm, synthesis))

        def speaker(clip):
            engine.last_speaker_verification = dict(self.proof,
                clip_sha256=speech.ming_narration.file_hash(clip))
            return 0.25

        def transcribe(clip, code):
            identity = context.crop_verification_identity(self.profile, code,
                                                         engine.last_speaker_verification)
            length = speech.seconds(clip)
            engine.last_transcription = dict(text=text, model=identity['model'],
                revision=identity['revision'], artifacts_sha256=identity['artifacts_sha256'],
                adapter_sha256=identity['adapter_sha256'], language=code,
                audio_sha256=speech.ming_narration.file_hash(clip), seconds=length,
                input_samples=round(length * 16000), truncation=False, long_form=True)
            return text

        engine.speaker_match, engine.transcribe = speaker, transcribe
        config = dict(self.config, _local_engine=engine)
        original_diagnostics = speech.Attempts

        def diagnostic(*args):
            record = original_diagnostics(*args)
            record.path = self.folder / 'chinese-context.json'
            return record

        with patch.object(context, '_crop_rule', return_value=rule), \
                patch.object(speech, 'verify_context_speaker', return_value=True), \
                patch.object(speech, 'Attempts', side_effect=diagnostic):
            # Parent proof semantics have their own shared-helper tests. This
            # exercises the real crop-ASR metadata validator and generic receipt.
            row = speech.generate(config, None, 'zh', 'cue', text)
            receipt = dict(clips={'zh/cue': row})
            self.assertEqual(row['transcriber'], route['model'] + '@' + route['revision'])
            self.assertEqual(row['verification']['context_recipe_sha256'], rule['sha256'])
            self.assertTrue(speech.current(receipt, config, 'zh', 'cue', text))
            changes = [('model', 'openai/whisper-small'), ('revision', 'wrong'),
                       ('artifacts_sha256', '0' * 64), ('adapter_sha256', '0' * 64),
                       ('audio_sha256', '0' * 64), ('language', 'en'), ('input_samples', 1),
                       ('seconds', 120), ('truncation', True), ('long_form', False),
                       ('text', '呼气。')]
            for field, value in changes:
                with self.subTest(asr_field=field):
                    changed = copy.deepcopy(row)
                    changed['transcription'][field] = value
                    self.assertFalse(speech.current(dict(clips={'zh/cue': changed}), config,
                                                    'zh', 'cue', text))
            for field, value in [('verification', {}), ('speaker_verification', None)]:
                changed = dict(row, **{field: value})
                self.assertFalse(speech.current(dict(clips={'zh/cue': changed}), config,
                                                'zh', 'cue', text))
            self.assertIsNone(speech.context_verification_identity(self.profile, 'en', self.proof))
            self.assertIsNone(speech.context_verification_identity(self.profile, 'zh', {}))
            self.assertIsNone(speech.context_verification_identity(dict(self.profile, model='other'),
                                                                  'zh', self.proof))
            with patch.object(speech, 'verify_context_speaker', return_value=False):
                self.assertFalse(speech.current(receipt, config, 'zh', 'cue', text))
            accepted_sha = speech.ming_narration.file_hash(speech.clip_path('zh', 'cue'))

            def changed_metadata(clip, code):
                result = transcribe(clip, code)
                engine.last_transcription['artifacts_sha256'] = '0' * 64
                return result

            engine.transcribe = changed_metadata
            with self.assertRaisesRegex(RuntimeError, 'ASR metadata failed verification'):
                speech.generate(config, None, 'zh', 'cue', text)
            self.assertEqual(speech.ming_narration.file_hash(speech.clip_path('zh', 'cue')), accepted_sha)


# Raw text/times from the 19 saved Czech diagnostics; no audio is certified here.
# Evidence SHA256: 37ed70fa532af3afc28b643464a799c3023257e314b1f29c4241548259bddd6b.
COUNT_DIAGNOSTICS = [{'id': 'spelled_parent_input/3/0',
  'text': '3.',
  'transcript': '3, 2, 1, připrav se na další cvik.',
  'words': [{'text': '3,', 'start': 0.0, 'end': 0.56},
            {'text': '2,', 'start': 0.56, 'end': 1.26},
            {'text': '1,', 'start': 1.26, 'end': 1.96},
            {'text': 'připrav', 'start': 1.96, 'end': 2.58},
            {'text': 'se', 'start': 2.58, 'end': 2.84},
            {'text': 'na', 'start': 2.84, 'end': 3.0},
            {'text': 'další', 'start': 3.0, 'end': 3.36},
            {'text': 'cvik.', 'start': 3.36, 'end': 3.84}],
  'seconds': 3.86,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 13440},
 {'id': 'spelled_parent_input/3/1',
  'text': '3.',
  'transcript': '3, 2, 1, připrav se na další cvik.',
  'words': [{'text': '3,', 'start': 0.06, 'end': 0.5},
            {'text': '2,', 'start': 0.5, 'end': 1.0},
            {'text': '1,', 'start': 1.0, 'end': 1.38},
            {'text': 'připrav', 'start': 1.38, 'end': 2.14},
            {'text': 'se', 'start': 2.14, 'end': 2.44},
            {'text': 'na', 'start': 2.44, 'end': 2.6},
            {'text': 'další', 'start': 2.6, 'end': 2.94},
            {'text': 'cvik.', 'start': 2.94, 'end': 3.44}],
  'seconds': 3.46,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 12000},
 {'id': 'spelled_parent_input/3/2',
  'text': '3.',
  'transcript': '3, 2, 1, připrav se na další clik.',
  'words': [{'text': '3,', 'start': 0.04, 'end': 0.54},
            {'text': '2,', 'start': 0.54, 'end': 0.84},
            {'text': '1,', 'start': 0.84, 'end': 1.28},
            {'text': 'připrav', 'start': 1.28, 'end': 1.76},
            {'text': 'se', 'start': 1.76, 'end': 1.92},
            {'text': 'na', 'start': 1.92, 'end': 2.06},
            {'text': 'další', 'start': 2.06, 'end': 2.38},
            {'text': 'clik.', 'start': 2.38, 'end': 2.88}],
  'seconds': 2.9,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': 12960},
 {'id': 'spelled_parent_input/3/3',
  'text': '3.',
  'transcript': '3, 2, 1, připrav se na další cvik.',
  'words': [{'text': '3,', 'start': 0.0, 'end': 0.44},
            {'text': '2,', 'start': 0.44, 'end': 0.84},
            {'text': '1,', 'start': 0.84, 'end': 1.44},
            {'text': 'připrav', 'start': 1.44, 'end': 1.82},
            {'text': 'se', 'start': 1.82, 'end': 2.0},
            {'text': 'na', 'start': 2.0, 'end': 2.12},
            {'text': 'další', 'start': 2.12, 'end': 2.44},
            {'text': 'cvik.', 'start': 2.44, 'end': 2.92}],
  'seconds': 2.94,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': None},
 {'id': 'spelled_parent_input/2/0',
  'text': '2.',
  'transcript': 'A 2. 1. Připrav se na další cvik.',
  'words': [{'text': 'A', 'start': 0.0, 'end': 0.18},
            {'text': '2.', 'start': 0.18, 'end': 0.64},
            {'text': '1.', 'start': 0.64, 'end': 1.3},
            {'text': 'Připrav', 'start': 1.3, 'end': 1.7},
            {'text': 'se', 'start': 1.7, 'end': 1.88},
            {'text': 'na', 'start': 1.88, 'end': 2.04},
            {'text': 'další', 'start': 2.04, 'end': 2.38},
            {'text': 'cvik.', 'start': 2.38, 'end': 2.84}],
  'seconds': 2.86,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None},
 {'id': 'spelled_parent_input/2/1',
  'text': '2.',
  'transcript': '2. 1. Připrav se na další cvik',
  'words': [{'text': '2.', 'start': 0.44, 'end': 0.84},
            {'text': '1.', 'start': 0.84, 'end': 1.28},
            {'text': 'Připrav', 'start': 1.28, 'end': 1.72},
            {'text': 'se', 'start': 1.72, 'end': 2.0},
            {'text': 'na', 'start': 2.0, 'end': 2.16},
            {'text': 'další', 'start': 2.16, 'end': 2.46},
            {'text': 'cvik', 'start': 2.46, 'end': 2.84}],
  'seconds': 2.94,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': None},
 {'id': 'spelled_parent_input/2/2',
  'text': '2.',
  'transcript': '2. 1. Připrav se na další cvik.',
  'words': [{'text': '2.', 'start': 0.26, 'end': 0.78},
            {'text': '1.', 'start': 0.78, 'end': 1.38},
            {'text': 'Připrav', 'start': 1.38, 'end': 1.76},
            {'text': 'se', 'start': 1.76, 'end': 1.92},
            {'text': 'na', 'start': 1.92, 'end': 2.06},
            {'text': 'další', 'start': 2.06, 'end': 2.36},
            {'text': 'cvik.', 'start': 2.36, 'end': 2.84}],
  'seconds': 2.86,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 18720},
 {'id': 'spelled_parent_input/2/3',
  'text': '2.',
  'transcript': '2. 1. Připrav se na další cvik.',
  'words': [{'text': '2.', 'start': 0.3, 'end': 0.94},
            {'text': '1.', 'start': 0.94, 'end': 1.72},
            {'text': 'Připrav', 'start': 1.72, 'end': 2.12},
            {'text': 'se', 'start': 2.12, 'end': 2.26},
            {'text': 'na', 'start': 2.26, 'end': 2.42},
            {'text': 'další', 'start': 2.42, 'end': 2.74},
            {'text': 'cvik.', 'start': 2.74, 'end': 3.16}],
  'seconds': 3.18,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 22560},
 {'id': 'spelled_parent_input/1/0',
  'text': '1.',
  'transcript': '1. Připrav se na další cvik a klidně dýchej.',
  'words': [{'text': '1.', 'start': 0.08, 'end': 0.58},
            {'text': 'Připrav', 'start': 0.58, 'end': 0.92},
            {'text': 'se', 'start': 0.92, 'end': 1.06},
            {'text': 'na', 'start': 1.06, 'end': 1.22},
            {'text': 'další', 'start': 1.22, 'end': 1.48},
            {'text': 'cvik', 'start': 1.48, 'end': 1.8},
            {'text': 'a', 'start': 1.8, 'end': 1.98},
            {'text': 'klidně', 'start': 1.98, 'end': 2.26},
            {'text': 'dýchej.', 'start': 2.26, 'end': 2.76}],
  'seconds': 2.78,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 13920},
 {'id': 'spelled_parent_input/1/1',
  'text': '1.',
  'transcript': 'Jedna připrav se na další cvik a klidně dýchej.',
  'words': [{'text': 'Jedna', 'start': 0.42, 'end': 0.74},
            {'text': 'připrav', 'start': 0.74, 'end': 1.24},
            {'text': 'se', 'start': 1.24, 'end': 1.42},
            {'text': 'na', 'start': 1.42, 'end': 1.56},
            {'text': 'další', 'start': 1.56, 'end': 1.9},
            {'text': 'cvik', 'start': 1.9, 'end': 2.24},
            {'text': 'a', 'start': 2.24, 'end': 2.4},
            {'text': 'klidně', 'start': 2.4, 'end': 2.72},
            {'text': 'dýchej.', 'start': 2.72, 'end': 3.28}],
  'seconds': 3.3,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': None},
 {'id': 'spelled_parent_input/1/2',
  'text': '1.',
  'transcript': 'Jedna, připrav se na další clik a klidně dýchej.',
  'words': [{'text': 'Jedna,', 'start': 0.28, 'end': 0.94},
            {'text': 'připrav', 'start': 0.94, 'end': 1.36},
            {'text': 'se', 'start': 1.36, 'end': 1.52},
            {'text': 'na', 'start': 1.52, 'end': 1.68},
            {'text': 'další', 'start': 1.68, 'end': 2.04},
            {'text': 'clik', 'start': 2.04, 'end': 2.48},
            {'text': 'a', 'start': 2.48, 'end': 2.88},
            {'text': 'klidně', 'start': 2.88, 'end': 3.28},
            {'text': 'dýchej.', 'start': 3.28, 'end': 3.8}],
  'seconds': 3.82,
  'crop_transcript': 'Jedna půjde.',
  'parent_exact': False,
  'end_sample': 22560},
 {'id': 'spelled_parent_input/1/3',
  'text': '1.',
  'transcript': '1. Připrav se na další cvik a klidně dýchej.',
  'words': [{'text': '1.', 'start': 0.24, 'end': 0.9},
            {'text': 'Připrav', 'start': 0.9, 'end': 1.26},
            {'text': 'se', 'start': 1.26, 'end': 1.44},
            {'text': 'na', 'start': 1.44, 'end': 1.58},
            {'text': 'další', 'start': 1.58, 'end': 1.92},
            {'text': 'cvik', 'start': 1.92, 'end': 2.26},
            {'text': 'a', 'start': 2.26, 'end': 2.46},
            {'text': 'klidně', 'start': 2.46, 'end': 2.74},
            {'text': 'dýchej.', 'start': 2.74, 'end': 3.28}],
  'seconds': 3.3,
  'crop_transcript': None,
  'parent_exact': True,
  'end_sample': 21600},
 {'id': 'numeric_parent_input/3/0',
  'text': '3.',
  'transcript': '3, 2, 1, připrav se na další cvik.',
  'words': [{'text': '3,', 'start': 0.04, 'end': 0.7},
            {'text': '2,', 'start': 0.7, 'end': 1.28},
            {'text': '1,', 'start': 1.28, 'end': 1.66},
            {'text': 'připrav', 'start': 1.66, 'end': 2.26},
            {'text': 'se', 'start': 2.26, 'end': 2.4},
            {'text': 'na', 'start': 2.4, 'end': 2.56},
            {'text': 'další', 'start': 2.56, 'end': 2.88},
            {'text': 'cvik.', 'start': 2.88, 'end': 3.32}],
  'seconds': 3.34,
  'crop_transcript': 'Ži...',
  'parent_exact': True,
  'end_sample': 16800},
 {'id': 'numeric_parent_input/3/1',
  'text': '3.',
  'transcript': '',
  'words': [],
  'seconds': 1.0,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None},
 {'id': 'numeric_parent_input/2/0',
  'text': '2.',
  'transcript': '',
  'words': [],
  'seconds': 1.0,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None},
 {'id': 'numeric_parent_input/1/0',
  'text': '1.',
  'transcript': 'Sje, jedna, připrav se na další cvik a klidně dýchej.',
  'words': [{'text': 'Sje,', 'start': 0.06, 'end': 0.74},
            {'text': 'jedna,', 'start': 0.74, 'end': 1.46},
            {'text': 'připrav', 'start': 1.46, 'end': 1.78},
            {'text': 'se', 'start': 1.78, 'end': 1.92},
            {'text': 'na', 'start': 1.92, 'end': 2.06},
            {'text': 'další', 'start': 2.06, 'end': 2.4},
            {'text': 'cvik', 'start': 2.4, 'end': 2.86},
            {'text': 'a', 'start': 2.86, 'end': 3.36},
            {'text': 'klidně', 'start': 3.36, 'end': 3.74},
            {'text': 'dýchej.', 'start': 3.74, 'end': 4.32}],
  'seconds': 4.34,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None},
 {'id': 'numeric_parent_input/1/1',
  'text': '1.',
  'transcript': 'C20. Třiprav se na další cvik a klidně dýchej.',
  'words': [{'text': 'C20.', 'start': 0.04, 'end': 0.94},
            {'text': 'Třiprav', 'start': 0.94, 'end': 1.26},
            {'text': 'se', 'start': 1.26, 'end': 1.4},
            {'text': 'na', 'start': 1.4, 'end': 1.56},
            {'text': 'další', 'start': 1.56, 'end': 1.92},
            {'text': 'cvik', 'start': 1.92, 'end': 2.3},
            {'text': 'a', 'start': 2.3, 'end': 2.5},
            {'text': 'klidně', 'start': 2.5, 'end': 2.86},
            {'text': 'dýchej.', 'start': 2.86, 'end': 3.44}],
  'seconds': 3.46,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None},
 {'id': 'numeric_parent_input/1/2',
  'text': '1.',
  'transcript': 'Jedna připrav se na další cilik a klidně dýchej.',
  'words': [{'text': 'Jedna', 'start': 0.28, 'end': 0.58},
            {'text': 'připrav', 'start': 0.58, 'end': 1.02},
            {'text': 'se', 'start': 1.02, 'end': 1.16},
            {'text': 'na', 'start': 1.16, 'end': 1.32},
            {'text': 'další', 'start': 1.32, 'end': 1.64},
            {'text': 'cilik', 'start': 1.64, 'end': 1.98},
            {'text': 'a', 'start': 1.98, 'end': 2.18},
            {'text': 'klidně', 'start': 2.18, 'end': 2.54},
            {'text': 'dýchej.', 'start': 2.54, 'end': 3.08}],
  'seconds': 3.1,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': 13920},
 {'id': 'numeric_parent_input/1/3',
  'text': '1.',
  'transcript': 'Připrav se na další celik a klidně dýchej.',
  'words': [{'text': 'Připrav', 'start': 0.22, 'end': 0.7},
            {'text': 'se', 'start': 0.7, 'end': 0.9},
            {'text': 'na', 'start': 0.9, 'end': 1.06},
            {'text': 'další', 'start': 1.06, 'end': 1.4},
            {'text': 'celik', 'start': 1.4, 'end': 1.74},
            {'text': 'a', 'start': 1.74, 'end': 1.88},
            {'text': 'klidně', 'start': 1.88, 'end': 2.18},
            {'text': 'dýchej.', 'start': 2.18, 'end': 2.72}],
  'seconds': 2.74,
  'crop_transcript': None,
  'parent_exact': False,
  'end_sample': None}]

class CzechCountComparisonTests(unittest.TestCase):
    def setUp(self):
        import local_narration_context as context
        self.context = context
        self.config = json.loads((ROOT / 'design/workout/narration.json').read_text())
        self.policy = ROOT / 'design/narration/workout-czech-count-semantics-v3.json'

    def rule(self, text):
        return self.context.recipe(self.policy, 'cs', text, 'workout/voice')

    def test_all_19_actual_diagnostic_text_and_time_results(self):
        context = self.context
        for case in COUNT_DIAGNOSTICS:
            with self.subTest(case=case['id']):
                rule = self.rule(case['text'])
                before = copy.deepcopy(case)
                self.assertEqual(context.parent_match(speech.complete_match, self.config, 'cs', rule,
                    case['transcript'], case['seconds']), float(case['parent_exact']))
                alignment = dict(text=case['transcript'], words=case['words'])
                if case['end_sample'] is None:
                    with self.assertRaises(ValueError):
                        context.prefix_range(case['text'], alignment, round(case['seconds'] * 24000),
                                             comparison=context.rule_comparison(rule))
                else:
                    self.assertEqual(context.prefix_range(case['text'], alignment, round(case['seconds'] * 24000),
                        comparison=context.rule_comparison(rule)), (0, case['end_sample']))
                if case['crop_transcript'] is not None:
                    expected, heard = context.comparison_views(rule, case['text'], case['crop_transcript'])
                    self.assertNotEqual(expected, heard)
                self.assertEqual(case, before)

    def test_equivalence_is_exact_ordered_and_requires_its_registered_rule(self):
        c = self.context
        for n, word in [('1', 'Jedna'), ('2', 'Dva'), ('3', 'Tři')]:
            rule = self.rule(n + '.')
            for transcript in (word + '.', n + '.'):
                a, b = c.comparison_views(rule, n + '.', transcript)
                self.assertEqual(a, b)
            for transcript in ('Ži...', 'A ' + word, word + ' půjde.', word + ' připrav', '',
                               '4.', '0.', '12.', word + ' ' + word, 'vlevo ' + word, 'dva tři jedna'):
                self.assertNotEqual(*c.comparison_views(rule, n + '.', transcript))
            for parent in (rule['parent_text'].replace('cvik', 'clik'),
                           rule['parent_text'] + ' vlevo', 'A ' + rule['parent_text'],
                           rule['parent_text'].replace('připrav', 'vpravo'),
                           rule['parent_text'].replace(word, '', 1)):
                self.assertEqual(c.parent_match(speech.complete_match, self.config, 'cs', rule, parent, 3.0), 0.0)
            self.assertNotEqual(c.words(n), c.words(word))
            self.assertEqual(c.comparison_words(word), c.words(word))
            for field, value in [('locale', 'de'), ('voice_directory', 'workout/voice-male'),
                                 ('parent_text', '3, 2, 1, připrav se na další cvik.'),
                                 ('comparison', {'version': 'unknown'}), ('text', '4.')]:
                with self.assertRaises(ValueError):
                    c.rule_comparison(dict(rule, **{field: value}))
            for field in ('prefix_alignment', 'crop_asr', 'parent_source'):
                with self.assertRaises(ValueError):
                    c.rule_comparison(dict(rule, **{field: {}}))
            with self.assertRaises(ValueError):
                c.comparison_views(rule, 'unregistered', word)
        rule = self.rule('3.')
        parent = rule['parent_text']
        for transcript in ('Dva, tři, jedna, připrav se na další cvik.',
                           'Tři, jedna, připrav se na další cvik.',
                           'Tři, dva, dva, jedna, připrav se na další cvik.'):
            self.assertEqual(c.parent_match(speech.complete_match, self.config, 'cs', rule, transcript, 3.0), 0.0)
        self.assertEqual(c.comparison_views({}, '3.', 'Tři.'), ('3.', 'Tři.'))

    def test_numeric_alignment_cannot_relax_time_or_coherence_guards(self):
        c = self.context
        comparison = c.rule_comparison(self.rule('3.'))
        aligned = dict(text='3, 2, 1.', words=[dict(text='Tři,', start=0.0, end=0.6),
            dict(text='2,', start=0.6, end=1.2), dict(text='jedna.', start=1.2, end=1.8)])
        self.assertEqual(c.prefix_range('3.', aligned, 48000, comparison=comparison), (0, 14400))
        with self.assertRaises(ValueError):
            c.prefix_range('3.', aligned, 48000)
        for changed in (dict(aligned, text='3, 1, 2.'),
                        dict(aligned, words=[dict(aligned['words'][0], start=0.31)] + aligned['words'][1:]),
                        dict(aligned, words=[dict(aligned['words'][0], end=0.61)] + aligned['words'][1:]),
                        dict(aligned, words=aligned['words'][:1]),
                        dict(aligned, words=aligned['words'][:2] + [dict(aligned['words'][2], end=3.0)])):
            with self.assertRaises(ValueError):
                c.prefix_range('3.', changed, 48000, comparison=comparison)
        with self.assertRaises(ValueError):
            c.prefix_range('3.', aligned, 48000, comparison=comparison, retain_leading_pcm0=True)

    def test_successors_are_sealed_and_old_policies_stay_immutable(self):
        c = self.context
        old_hashes = {'short-context.json': 'de104d838db7bb079f7686dbbb21e8602a590c5137729e23457ea6e653087e39',
            'workout-czech-context.json': '1f587946f9feae942d5ff8fa09a6a0962614c67d75a01544b9f5a486b17c23ab',
            'tai-chi-short-context.json': '7135f8462512de5345ad056b1ff79852b93c82edbb156e153f9dc30c7036a9de',
            'workout-czech-numeric-context.json': 'a2ce323bc7c85a3f968fc6e293519023dbff51bf06d5728c05f9a76e11a8e1f2'}
        old_hashes.update({
            'short-context-provider-v2.json': '5a56a9525cb2714868d995709549be6aa171f2ff138a549af3f16908d3670d1f',
            'workout-czech-context-provider-v2.json': '4558186f263b4880ecadcbd7a8f62f6ef6af460a362c04346d22a61d0ba87596',
            'tai-chi-short-context-provider-v2.json': 'def352e915dc4e03af25691402ff56201368f6783f7e5dd0f32def7e9e9fde72',
            'workout-czech-count-semantics-v1.json': 'e88494e1032f09d7b0c3b5085a4e9a78a65602747fea79c15b74bf36b72d1e13',
        })
        for name, checksum in old_hashes.items():
            path = ROOT / 'design/narration' / name
            self.assertEqual(c.file_hash(path), checksum)
            with self.assertRaises(ValueError):
                c.load_policy(path)
        for old, new in [('short-context.json', 'short-context-provider-v4.json'),
                         ('workout-czech-context.json', 'workout-czech-context-provider-v4.json'),
                         ('tai-chi-short-context.json', 'tai-chi-short-context-provider-v4.json')]:
            original = json.loads((ROOT / 'design/narration' / old).read_text())
            successor = c.load_policy(ROOT / 'design/narration' / new)
            for field in ('voice_directory', 'rules', 'asr_model', 'asr_revision', 'asr_artifacts'):
                self.assertEqual(successor[field], original[field])
            for rule in successor['rules']:
                self.assertIsNotNone(c.recipe(ROOT / 'design/narration' / new,
                    rule['locale'], rule['text'], successor['voice_directory']))
        numeric = c.load_policy(self.policy)
        self.assertEqual(len(numeric['rules']), 3)
        for rule in numeric['rules']:
            self.assertEqual(rule['parent_text'], c.CZECH_COUNT_PARENTS[rule['text']])
            self.assertEqual(c.rule_comparison(dict(rule, voice_directory=numeric['voice_directory'])),
                             c.CZECH_COUNT_COMPARISON)

    def test_generate_and_current_replay_semantics_keep_raw_asr_and_all_proof_gates(self):
        c = self.context
        staging = ROOT / 'backup/narration/tmp'
        staging.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=staging, prefix='count-proof-unit-') as temporary:
            folder = Path(temporary)
            media = folder / 'media'
            voice = media / 'workout/voice'
            voice.mkdir(parents=True)
            profile = speech.LOCAL_PROVIDERS['chatterbox-czech'].descriptor(self.config)
            identity = c.source_identity(profile)
            pcm = array('h', [int(2000 * math.sin(index * 2 * math.pi * 220 / 24000))
                              for index in range(48000)]).tobytes()
            cache = folder / 'cache'
            cache.mkdir()
            parent = cache / (c.pcm_hash(pcm) + '.wav')
            c.write_wav(parent, pcm)
            local = folder / 'local.json'
            local.write_text(json.dumps(dict(cache=str(cache), python=sys.executable, model='forbidden')))
            requests = []
            base = SimpleNamespace(profile=profile, last_transcription=None,
                speaker_match=lambda path: 0.8 if Path(path).suffix == '.wav' else 0.4)
            def speak(config, text, code, work, attempt):
                requests.append(text)
                return pcm, identity
            base.speak = speak
            original_attempts = speech.Attempts
            def diagnostics(*args):
                record = original_attempts(*args)
                record.path = folder / 'diagnostic.json'
                return record
            with patch.object(speech, 'MEDIA_ROOT', media), patch.object(speech, 'VOICE', voice), \
                    patch.object(speech, 'Attempts', side_effect=diagnostics), \
                    patch.object(c, 'align_audio', side_effect=AssertionError('Inference forbidden')), \
                    patch.object(c, 'transcribe_audio', side_effect=AssertionError('Inference forbidden')), \
                    patch.object(speech.chatterbox_czech_narration, 'Engine', side_effect=AssertionError('Engine forbidden')):
                for n, word in [('3', 'Tři'), ('2', 'Dva'), ('1', 'Jedna')]:
                    rule = self.rule(n + '.')
                    raw_parent = rule['parent_text'].replace('Tři', '3').replace('Dva', '2').replace('Jedna', '1')
                    raw_parent = raw_parent.replace('dva', '2').replace('jedna', '1')
                    first, rest = raw_parent.split(' ', 1)
                    alignment = dict(text=raw_parent, words=[dict(text=first, start=0.0, end=0.56),
                        dict(text=rest, start=0.56, end=1.9)], language='cs', model=c.ASR_MODEL,
                        revision=c.ASR_REVISION, audio_sha256=c.file_hash(parent), helper_sha256=c.file_hash(c.__file__),
                        input_samples=32000, seconds=2.0, truncation=False, long_form=True)
                    parent.with_suffix('.alignment.json').write_text(json.dumps(alignment))
                    wrapped = c.ContextEngine(base, self.config, self.policy, local, encode=speech.encode,
                        complete_match=speech.complete_match, identity=identity, voice_directory='workout/voice')
                    config = dict(self.config, _local_engine=wrapped, _context_profile=str(self.policy))
                    for raw in (word + '.', n + '.'):
                        def transcribe(path, code):
                            duration = speech.seconds(path)
                            base.last_transcription = dict(text=raw, language=code, model=profile['transcriber'],
                                revision=profile['asr_revision'], audio_sha256=c.file_hash(path),
                                seconds=duration, input_samples=round(duration * 16000), truncation=False, long_form=True)
                            return raw
                        base.transcribe = transcribe
                        key = 'workout_say_count_' + n
                        row = speech.generate(config, None, 'cs', key, n + '.')
                        receipt = dict(clips={'cs/' + key: row})
                        clip = voice / 'cs' / (key + '.ogg')
                        self.assertEqual(requests[-1], c.CZECH_COUNT_PARENTS[n + '.'])
                        self.assertEqual(row['transcript'], raw)
                        self.assertEqual(row['transcription']['text'], raw)
                        self.assertEqual(row['speaker_verification']['parent']['alignment'], alignment)
                        self.assertEqual(row['speaker_cosine'], 0.4)
                        self.assertEqual(row['speaker_verification']['parent_cosine'], 0.8)
                        self.assertEqual(row['match'], 1.0)
                        self.assertEqual(row['synthesis'], identity)
                        self.assertTrue(speech.current(receipt, config, 'cs', key, n + '.'))
                        self.assertNotEqual(speech.text_hash(config, n + '.', 'cs', identity), row['text_sha256'])
                        for heard in ('Ži...', word + ' půjde.', 'A ' + word, 'vpravo ' + word, ''):
                            bad = copy.deepcopy(row)
                            bad['transcript'] = bad['transcription']['text'] = heard
                            self.assertFalse(speech.current(dict(clips={'cs/' + key: bad}), config, 'cs', key, n + '.'))
                            base.transcribe = lambda *args: heard
                            with self.assertRaises(c.ContextRejected):
                                wrapped.transcribe(clip, 'cs')
                        for mutate in (
                                lambda proof: proof.update(parent_cosine=profile['minimum_speaker_cosine'] - .001),
                                lambda proof: proof['crop'].update(start_sample=1),
                                lambda proof: proof['parent']['alignment'].update(helper_sha256='0' * 64),
                                lambda proof: proof['parent']['alignment'].update(text=raw_parent + ' vlevo')):
                            bad = copy.deepcopy(row)
                            proof = bad['speaker_verification']
                            mutate(proof)
                            proof['proof_sha256'] = c.json_hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
                            self.assertFalse(speech.current(dict(clips={'cs/' + key: bad}), config, 'cs', key, n + '.'))
                        bad = copy.deepcopy(row)
                        bad['seconds'] = .96
                        self.assertFalse(speech.current(dict(clips={'cs/' + key: bad}), config, 'cs', key, n + '.'))
                        disabled = dict(config)
                        disabled.pop('chatterbox_czech')
                        self.assertFalse(speech.current(receipt, disabled, 'cs', key, n + '.'))

if __name__ == '__main__':
    unittest.main()
