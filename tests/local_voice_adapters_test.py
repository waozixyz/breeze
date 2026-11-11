"""Offline contract tests: pin validation, request identity and verified resume."""
import copy
import array
import importlib.util
import json
import math
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import f5_russian_narration as ru
import chatterbox_czech_narration as cs
import chatterbox_portuguese_narration as pt
import local_narration_context as context


class LocalVoiceAdaptersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = ROOT / 'backup/narration/local-models/tmp'
        subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(cls.scratch / 'probe')], check=True)
        cls.scratch.mkdir(parents=True, exist_ok=True)

    def profile(self, module=ru):
        return dict(schema=1, model=module.MODEL, model_revision=module.MODEL_REVISION,
                    locale=module.LANGUAGES[0], status='ready', reference_sha256='a'*64,
                    adapter_sha256='b'*64, reference_text='Exact reference.',
                    parameters={'temperature': 0.8}, environment={'torch': '2.6.0'},
                    artifacts={'weights.safetensors': 'c'*64}, seed=1,
                    provider='test', runtime_version='1',
                    segmentation=dict(mode='bounded-text-v1', maximum_characters=160, pause_seconds=0.12),
                    source_files={name:ru.file_hash(ROOT / 'scripts' / name) for name in
                        (['f5_russian_narration.py','prepare-local-voice-profile.py','whisper_narration.py'] +
                         (['chatterbox_czech_narration.py'] if module is cs else ['chatterbox_portuguese_narration.py'] if module is pt else []))})

    def test_exact_model_revision_locale_required(self):
        for module in (ru, cs, pt):
            p = self.profile(module)
            module.validate(p)
            for key in ('model', 'model_revision', 'locale'):
                changed = dict(p, **{key: 'other'})
                with self.assertRaises(ValueError): module.validate(changed)

    def test_blocked_profile_never_certifies(self):
        for module in (ru, cs, pt):
            with self.assertRaises(ValueError):
                module.validate(dict(self.profile(module), status='blocked'))

    def test_unsafe_artifacts_rejected(self):
        for name in ('../outside', '/outside'):
            with self.assertRaises(ValueError): ru.validate(dict(self.profile(), artifacts={name:'c'*64}))

    def test_hash_covers_output_reference_model_sampling(self):
        cfg = dict(pcm_sample_rate=24000, sample_rate=16000)
        p = self.profile()
        base = ru.text_hash(cfg, 'Hello', p, 'ru')
        for key, value in [('reference_sha256', 'd'*64), ('model_revision', 'new'),
                           ('parameters', {'temperature':0.1}), ('seed', 2), ('reference_text', 'Changed')]:
            self.assertNotEqual(base, ru.text_hash(cfg, 'Hello', dict(p, **{key:value}), 'ru'))
        self.assertNotEqual(base, ru.text_hash(dict(cfg, pcm_sample_rate=16000), 'Hello', p, 'ru'))
        self.assertNotEqual(base, ru.text_hash(dict(cfg, opus_bitrate='24k'), 'Hello', p, 'ru'))
        with self.assertRaises(ValueError): ru.text_hash(cfg, 'Hello', p, 'cs')

    def test_offline_source_edits_invalidate_identity(self):
        cfg = dict(pcm_sample_rate=24000, sample_rate=16000)
        for module in (ru, cs, pt):
            profile = self.profile(module)
            with patch.object(ru, 'file_hash', return_value='0'*64):
                with self.assertRaisesRegex(ValueError, 'Changed local voice source'):
                    module.text_hash(cfg, 'Text', profile, module.LANGUAGES[0])

    def test_registered_practice_pilot_budgets(self):
        spec = importlib.util.spec_from_file_location('voice_preparer', ROOT / 'scripts/prepare-local-voice-profile.py')
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        config, directory = helper.cue_definition('sun_salutation_voice_breathe_in')
        self.assertEqual(config['maximum_clip_seconds'],5.8)
        config, directory = helper.cue_definition('astral_text_foundation_01')
        self.assertEqual(config['maximum_clip_seconds_by_key']['astral_text_foundation_01'],45)
        self.assertEqual(directory, Path('/mnt/storage/Projects/waozixyz/modules/practices/astral_projection/text'))
        with self.assertRaises(ValueError): helper.cue_definition('../unknown')

    def test_portuguese_descriptor_uses_configured_provider_key(self):
        self.assertIsNotNone(pt.descriptor({'chatterbox-portuguese':self.profile(pt)}))

    def test_portuguese_chunks_preserve_complete_canonical_text(self):
        path = Path('/mnt/storage/Projects/waozixyz/modules/practices/astral_projection/text/pt.txt')
        text = path.read_text().split('[astral_text_foundation_01]\n')[1].split('\n---')[0]
        chunks = pt.chunk_text(text, 160)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(' '.join(chunks), ' '.join(text.split()))
        self.assertTrue(all(0 < len(chunk) <= 160 for chunk in chunks))
        self.assertEqual(pt.chunk_text('Inspire.', 160), ['Inspire.'])
        for text, maximum in [('', 160), ('x' * 161, 160), ('text', 0)]:
            with self.assertRaises(ValueError):
                pt.chunk_text(text, maximum)
        for recipe in ({}, dict(mode='other'), dict(mode='bounded-text-v1', maximum_characters=160, pause_seconds=-1)):
            with self.assertRaises(ValueError):
                pt.validate(dict(self.profile(pt), segmentation=recipe))

    def test_portuguese_chunk_audio_preserves_channels_pauses_and_reference(self):
        import numpy as np
        engine = object.__new__(pt.Engine)
        engine.profile = self.profile(pt)
        engine.local = dict(reference='selected-female.wav')
        text = 'Primeira frase com palavras. ' * 12 + 'Última instrução completa.'
        seen = []

        class Wave:
            def detach(self): return self
            def float(self): return self
            def cpu(self): return self
            def numpy(self): return np.array([[0.25, 0.5]], dtype=np.float32)

        def generate(chunk, **parameters):
            seen.append(chunk)
            self.assertEqual(parameters['audio_prompt_path'], engine.local['reference'])
            self.assertEqual(parameters['temperature'], 0.8)
            return Wave()

        engine.model = types.SimpleNamespace(generate=generate, sr=24000)
        audio, rate = engine.synthesize(text)
        self.assertEqual(' '.join(seen), ' '.join(text.split()))
        self.assertEqual(rate, 24000)
        self.assertEqual(audio.ndim, 1)
        self.assertEqual(len(audio), 2 * len(seen) + 2880 * (len(seen) - 1))
        np.testing.assert_array_equal(audio[:2], [0.25, 0.5])
        np.testing.assert_array_equal(audio[2:2882], np.zeros(2880))
        np.testing.assert_array_equal(audio[-2:], [0.25, 0.5])

    def test_context_boundary_consumes_actual_chunks_including_chinese(self):
        for chunks in ([dict(text='吸', start=0, end=0.3), dict(text='氣', start=0.3, end=0.65)],
                       [dict(text='吸氣', start=0, end=0.65)]):
            alignment = dict(words=chunks + [dict(text='右腿', start=0.8, end=1.2)])
            self.assertEqual(context.prefix_range('吸气。', alignment, 48000), (0, 16200))
        for chunks in ([dict(text='吸气然后', start=0, end=0.8)],
                       [dict(text='呼气', start=0, end=0.65)],
                       [dict(text='吸气', start=0, end=0.9)]):
            alignment = dict(words=chunks + [dict(text='右腿', start=0.8, end=1.2)])
            with self.assertRaises(ValueError):
                context.prefix_range('吸气。', alignment, 48000)

    def test_context_preserves_ming_original_synthesis_identity(self):
        import ming_verification
        profile = json.loads((ROOT / 'design/narration/ming-female.json').read_text())
        self.assertEqual(context.source_identity(profile), ming_verification.provenance(profile))

    def test_context_coherence_reconstructs_only_actual_letter_connectors(self):
        for text, chunks in [
                ('Expirez et penchez-vous en avant.', ['Expirez', 'et', 'penchez', '-vous', 'en', 'avant.']),
                ("Expirez et sentez l'air.", ['Expirez', 'et', 'sentez', "l'", 'air.']),
                ('Expirez et sentez l’air.', ['Expirez', 'et', 'sentez', 'l’', 'air.'])]:
            alignment = dict(text=text, words=[dict(text=word, start=index * 0.6, end=(index + 1) * 0.6)
                                              for index, word in enumerate(chunks)])
            original = copy.deepcopy(alignment)
            self.assertEqual(context.prefix_range('Expirez.', alignment, 120000), (0, 14400))
            self.assertEqual(alignment, original)
        for chunks in [
                ['Expirez', 'et', 'penchez', '-nous', 'en', 'avant.'],
                ['Expirez', 'penchez', '-vous', 'en', 'avant.'],
                ['Expirez', 'et', 'penchez', '-vous', 'encore', 'en', 'avant.'],
                ['Expirez', 'et', 'penchez', '-vous', '2', 'fois', 'en', 'avant.'],
                ['Expirez', 'et', 'penchez', '-vous', 'à', 'droite.']]:
            alignment = dict(text='Expirez et penchez-vous en avant.',
                words=[dict(text=word, start=index * 0.6, end=(index + 1) * 0.6)
                       for index, word in enumerate(chunks)])
            with self.assertRaisesRegex(ValueError, 'actual full transcription'):
                context.prefix_range('Expirez.', alignment, 120000)

    def test_chinese_crop_route_is_explicit_and_pins_actual_complete_transcription(self):
        profile = json.loads((ROOT / 'design/narration/ming-female.json').read_text())
        route = dict(model=context.ASR_MODEL, revision=context.ASR_REVISION, artifacts={'model.safetensors': 'a' * 64})
        rule = dict(locale='zh', text='吸气。', sha256='b' * 64, policy_sha256='c' * 64, crop_asr=route)
        proof = dict(scope='context_parent', version=context.VERSION, locale='zh', voice_directory='sunsalutation/voice',
            policy_path='design/narration/short-context.json', text_sha256=context.pcm_hash('吸气。'.encode()),
            recipe_sha256=rule['sha256'], source_identity=context.source_identity(profile), clip_sha256='d' * 64)
        proof['proof_sha256'] = ru.json_hash(proof)
        with patch.object(context, 'load_policy', return_value=dict(rules=[rule])), \
                patch.object(context, 'recipe', return_value=rule):
            identity = context.crop_verification_identity(profile, 'zh', proof)
            self.assertEqual(identity['model'], context.ASR_MODEL)
            self.assertEqual(identity['context_recipe_sha256'], rule['sha256'])
            row = dict(model=context.ASR_MODEL, revision=context.ASR_REVISION,
                artifacts_sha256=ru.json_hash(route['artifacts']), adapter_sha256=ru.file_hash(context.__file__),
                audio_sha256=proof['clip_sha256'], language='zh', text='吸气。', input_samples=10000,
                seconds=0.625, truncation=False, long_form=True)
            self.assertTrue(context.verified_crop_transcription(profile, 'zh', proof, row, identity))
            for key, value in [('model', 'wrong'), ('revision', 'wrong'), ('artifacts_sha256', 'wrong'),
                    ('adapter_sha256', 'wrong'), ('audio_sha256', 'wrong'), ('language', 'en'),
                    ('input_samples', 9990), ('input_samples', True), ('seconds', 0.7),
                    ('truncation', True), ('long_form', False), ('text', '吸气然后')]:
                with self.subTest(field=key, value=value):
                    self.assertFalse(context.verified_crop_transcription(profile, 'zh', proof, dict(row, **{key: value}), identity))
            self.assertFalse(context.verified_crop_transcription(profile, 'zh', proof, row, dict(identity, model='wrong')))
            for key, value in [('locale', 'fr'), ('voice_directory', 'guide/voice'),
                    ('recipe_sha256', 'wrong'), ('text_sha256', 'wrong'), ('proof_sha256', 'wrong')]:
                self.assertIsNone(context.crop_verification_identity(profile, 'zh', dict(proof, **{key: value})))
            self.assertIsNone(context.crop_verification_identity(profile, 'fr', proof))
            self.assertIsNone(context.crop_verification_identity(self.profile(pt), 'zh', proof))
            with patch.object(context, 'recipe', return_value={key: value for key, value in rule.items() if key != 'crop_asr'}):
                self.assertIsNone(context.crop_verification_identity(profile, 'zh', proof))

    def test_crop_route_requires_exact_chinese_rule_and_registered_parent(self):
        source = ROOT / 'design/sun-salutation/narration/text/zh.txt'
        import re
        entries = dict(re.findall(r'\[([^\]]+)\]\n(.*?)(?=\n---|\Z)', source.read_text(), re.S))
        artifacts = {'model.safetensors': 'a' * 64}
        rule = dict(locale='zh', text='呼气。', parent_text=entries['sun_salutation_voice_plank'].strip(),
            parent_source=dict(file=str(source.relative_to(ROOT)), key='sun_salutation_voice_plank', sha256=ru.file_hash(source)),
            maximum_parent_seconds=5.8, minimum_parent_match=0.92,
            crop_asr=dict(model=context.ASR_MODEL, revision=context.ASR_REVISION, artifacts=artifacts))
        policy = dict(voice_directory='sunsalutation/voice', rules=[rule], asr_artifacts=artifacts)
        with patch.object(context, 'load_policy', return_value=policy):
            accepted = context.recipe(context.POLICY, 'zh', '呼气。', 'sunsalutation/voice')
            self.assertEqual(accepted['parent_source']['key'], 'sun_salutation_voice_plank')
        for changed in [dict(rule, crop_asr=dict(rule['crop_asr'], model='wrong')),
                        dict(rule, crop_asr=dict(rule['crop_asr'], revision='wrong')),
                        dict(rule, crop_asr=dict(rule['crop_asr'], artifacts={})),
                        {key: value for key, value in rule.items() if key != 'parent_source'},
                        dict(rule, parent_source=dict(rule['parent_source'], sha256='b' * 64)),
                        dict(rule, parent_text=rule['parent_text'] + '改')]:
            with patch.object(context, 'load_policy', return_value=dict(policy, rules=[changed])):
                with self.assertRaises(ValueError):
                    context.recipe(context.POLICY, 'zh', '呼气。', 'sunsalutation/voice')
        with patch.object(context, 'load_policy', return_value=dict(policy, voice_directory='guide/voice')):
            with self.assertRaises(ValueError):
                context.recipe(context.POLICY, 'zh', '呼气。', 'guide/voice')

    def test_russian_context_keeps_ordinary_pinned_final_recognizer(self):
        profile = json.loads((ROOT / 'design/narration/f5-russian.json').read_text())
        metadata = dict(text='Вдохните.', model=profile['transcriber'], revision=profile['asr_revision'])
        wrapped = context.ContextEngine.__new__(context.ContextEngine)
        wrapped.profile = profile
        wrapped.engine = types.SimpleNamespace(transcribe=lambda *args: metadata['text'], last_transcription=metadata)
        wrapped.context = dict(text='Вдохните.', rule=dict(parent_text='Вдохните и отведите правую ногу назад.'))
        wrapped.last_speaker_verification = None
        wrapped.last_context_verification = None
        wrapped.last_transcription = None
        self.assertEqual(wrapped.transcribe('actual.ogg', 'ru'), 'Вдохните.')
        self.assertIs(wrapped.last_transcription, metadata)
        self.assertEqual(wrapped.last_transcription['model'], 'openai/whisper-small')
        self.assertIsNone(wrapped.last_context_verification)
        self.assertIsNone(context.crop_verification_identity(profile, 'ru', None))

    def test_explicit_leading_pcm_mode_preserves_start_and_boundary_guards(self):
        for onset in (0.32, 0.52):
            alignment = dict(text='Vydechněte a předkloňte se.', words=[
                dict(text='Vydechněte', start=onset, end=1.2),
                dict(text='a', start=1.2, end=1.4), dict(text='předkloňte se.', start=1.4, end=1.9)])
            with self.assertRaises(ValueError):
                context.prefix_range('Vydechněte.', alignment, 48000)
            start, end = context.prefix_range('Vydechněte.', alignment, 48000, retain_leading_pcm0=True)
            self.assertEqual((start, end), (0, 28800))
            pcm = array.array('h', [12345] * 48000).tobytes()
            self.assertEqual(pcm[start * 2:end * 2], pcm[:57600])
            for changed in [dict(alignment, text='Vydechněte a předkloňte se ještě.'),
                            dict(alignment, words=alignment['words'][1:]),
                            dict(alignment, words=[dict(alignment['words'][0], text='Nadechněte')] + alignment['words'][1:]),
                            dict(alignment, words=[dict(alignment['words'][0], start=-0.1)] + alignment['words'][1:]),
                            dict(alignment, words=[dict(alignment['words'][0], end=1.3)] + alignment['words'][1:]),
                            dict(alignment, words=alignment['words'][:2] + [dict(alignment['words'][2], end=2.5)])]:
                with self.assertRaises(ValueError):
                    context.prefix_range('Vydechněte.', changed, 48000, retain_leading_pcm0=True)
        with self.assertRaises(ValueError):
            context.prefix_range('Vydechněte.', alignment, 48000, retain_leading_pcm0='yes')

    def test_leading_pcm_policy_is_scoped_and_rejects_unknown_modes(self):
        source = ROOT / 'design/sun-salutation/narration/text/cs.txt'
        rule = dict(locale='cs', text='Vydechněte.', parent_text='Vydechněte a předkloňte se.',
            parent_source=dict(file=str(source.relative_to(ROOT)), key='sun_salutation_voice_fold', sha256=ru.file_hash(source)),
            prefix_alignment=context.RETAIN_LEADING_PCM0, maximum_parent_seconds=5.8, minimum_parent_match=0.92)
        policy = dict(voice_directory='sunsalutation/voice', rules=[rule])
        with patch.object(context, 'load_policy', return_value=policy):
            accepted = context.recipe(context.POLICY, 'cs', 'Vydechněte.', 'sunsalutation/voice')
            self.assertEqual(accepted['prefix_alignment'], context.RETAIN_LEADING_PCM0)
        for changed in [dict(rule, prefix_alignment='unknown'), dict(rule, prefix_alignment=True),
                        {key: value for key, value in rule.items() if key != 'parent_source'},
                        dict(rule, text='Nadechněte.')]:
            with patch.object(context, 'load_policy', return_value=dict(policy, rules=[changed])):
                with self.assertRaises(ValueError):
                    context.recipe(context.POLICY, 'cs', changed['text'], 'sunsalutation/voice')

    def test_cached_only_context_never_synthesizes_missing_or_changed_pcm(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            cache = Path(tmp)
            profile = self.profile(cs)
            config = dict(pcm_sample_rate=24000, sample_rate=16000, _cached_only=True)
            identity = ru.json_hash(dict(request=ru.text_hash(config, 'Text.', profile, 'cs'), attempt=0))
            pcm, receipt = cache / (identity + '.pcm'), cache / (identity + '.json')
            calls = []
            wrapped = context.ContextEngine.__new__(context.ContextEngine)
            wrapped.profile = profile
            wrapped.engine = types.SimpleNamespace(local=dict(cache=str(cache)),
                speak=lambda *args: calls.append(args) or (b'pcm', 'identity'))
            with self.assertRaisesRegex(RuntimeError, 'original local PCM'):
                wrapped.base_speak(config, 'Text.', 'cs', cache, 0)
            self.assertEqual(calls, [])
            pcm.write_bytes(b'\x01\x00' * 24000)
            receipt.write_text(json.dumps(dict(request=identity, sha256=ru.file_hash(pcm))))
            self.assertEqual(wrapped.base_speak(config, 'Text.', 'cs', cache, 0), (b'pcm', 'identity'))
            self.assertEqual(len(calls), 1)
            pcm.write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'changed local PCM'):
                wrapped.base_speak(config, 'Text.', 'cs', cache, 0)
            self.assertEqual(len(calls), 1)

    def test_context_candidate_rejection_preserves_diagnostics_and_integrity_errors(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            folder = Path(tmp)
            config, profile, row, clip, parent, rule = self.context_fixture(folder)
            pcm = context.read_wav(parent)
            identity = row['synthesis']
            engine = types.SimpleNamespace(profile=profile,
                speak=lambda *args: (pcm, identity), speaker_match=lambda audio: 0.64,
                transcribe=lambda *args: 'Inspire e')
            local = folder / 'local.json'
            local.write_text(json.dumps(dict(cache=str(folder / 'cache'), python=sys.executable, model='unused')))
            with patch.object(context, 'load_policy'), patch.object(context, 'recipe', return_value=rule):
                wrapped = context.ContextEngine(engine, config, context.POLICY, local,
                    encode=None, complete_match=lambda *args: 1.0, identity=identity,
                    voice_directory='sunsalutation/voice')
                engine.speak = lambda *args: (pcm * 3, identity)
                with self.assertRaises(context.ContextRejected) as rejected:
                    wrapped.speak(config, 'Inspire.', 'pt', folder, 0)
                self.assertEqual(rejected.exception.diagnostics['parent_seconds'], 6.0)
                self.assertEqual(rejected.exception.diagnostics['source_identity'], identity)
                engine.speak = lambda *args: (pcm, dict(identity, model='wrong'))
                with self.assertRaises(RuntimeError) as fatal:
                    wrapped.speak(config, 'Inspire.', 'pt', folder, 1)
                self.assertNotIsInstance(fatal.exception, context.ContextRejected)
                engine.speak = lambda *args: (pcm, identity)
                cached = folder / 'cache' / (context.pcm_hash(pcm) + '.wav')
                context.write_wav(cached, pcm)
                alignment = copy.deepcopy(row['speaker_verification']['parent']['alignment'])
                cached.with_suffix('.alignment.json').write_text(json.dumps(alignment))
                with self.assertRaises(context.ContextRejected) as rejected:
                    wrapped.speak(config, 'Inspire.', 'pt', folder, 2)
                self.assertEqual(rejected.exception.diagnostics['parent_cosine'], 0.64)
                self.assertEqual(rejected.exception.diagnostics['parent_transcription'], alignment)
                engine.speaker_match = lambda audio: 0.8
                crop, actual_identity = wrapped.speak(config, 'Inspire.', 'pt', folder, 3)
                self.assertEqual(actual_identity, identity)
                self.assertEqual(len(crop), 30000)
                with self.assertRaises(context.ContextRejected) as rejected:
                    wrapped.transcribe(clip, 'pt')
                self.assertEqual(rejected.exception.diagnostics['crop_transcript'], 'Inspire e')
                alignment['model'] = 'wrong'
                cached.with_suffix('.alignment.json').write_text(json.dumps(alignment))
                with self.assertRaises(RuntimeError) as fatal:
                    wrapped.speak(config, 'Inspire.', 'pt', folder, 0)
                self.assertNotIsInstance(fatal.exception, context.ContextRejected)

    def context_fixture(self, folder):
        spec = importlib.util.spec_from_file_location('context_fixture_driver', ROOT / 'scripts/generate-lumi-guide-narration.py')
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        profile = self.profile(pt)
        profile['minimum_speaker_cosine'] = 0.65
        profile['transcriber'] = context.ASR_MODEL
        profile['asr_revision'] = context.ASR_REVISION
        config = dict(pcm_sample_rate=24000, sample_rate=16000, opus_bitrate='16k', minimum_match=0.92)
        pcm = array.array('h', [round(3000 * math.sin(i * 2 * math.pi * 200 / 24000)) for i in range(48000)]).tobytes()
        parent = folder / 'parent.wav'
        context.write_wav(parent, pcm)
        alignment = dict(text='Inspire e siga.', language='pt', model=context.ASR_MODEL,
                         revision=context.ASR_REVISION, audio_sha256=ru.file_hash(parent),
                         helper_sha256=ru.file_hash(context.__file__), input_samples=32000, seconds=2.0,
                         truncation=False, long_form=True,
                         words=[dict(text='Inspire', start=0.0, end=0.6), dict(text='e', start=0.7, end=0.9),
                                dict(text='siga.', start=0.9, end=1.8)])
        start, end = context.prefix_range('Inspire.', alignment, 48000)
        clip = driver.encode(config, pcm[start * 2:end * 2], folder)
        sha = ru.file_hash(parent)
        relative = 'sunsalutation/voice-context/pt/' + sha + '.wav'
        rule = dict(sha256='d' * 64, parent_text='Inspire e siga.', maximum_parent_seconds=5.8,
                    minimum_parent_match=0.92)
        proof = dict(scope='context_parent', version=context.VERSION,
                     policy_path='design/narration/short-context.json', recipe_sha256=rule['sha256'],
                     locale='pt', text_sha256=context.pcm_hash(b'Inspire.'), voice_directory='sunsalutation/voice',
                     source_identity=context.source_identity(profile), actual_clip_cosine=0.4,
                     parent_cosine=0.8, gender_verified=False, clip_sha256=ru.file_hash(clip),
                     parent=dict(file=relative, sha256=sha, pcm_sha256=context.pcm_hash(pcm),
                                 text=alignment['text'], text_sha256=context.pcm_hash(alignment['text'].encode()), alignment=alignment),
                     crop=dict(start_sample=start, end_sample=end, pcm_sha256=context.pcm_hash(pcm[start * 2:end * 2]),
                               encoded_packets_sha256=context.packet_hash(clip), float_peak=0.2))
        proof['proof_sha256'] = ru.json_hash(proof)
        row = dict(speaker_verification=proof, synthesis=proof['source_identity'],
                   speaker_cosine=0.4, seconds=0.625, sha256=ru.file_hash(clip))
        config['_context_artifacts'] = [dict(source=str(parent), destination_relative=relative, sha256=sha)]
        return config, profile, row, clip, parent, rule

    def test_leading_pcm_offline_proof_requires_zero_start_and_full_crop_words(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            folder = Path(tmp)
            config, _, row, clip, parent, rule = self.context_fixture(folder)
            profile = self.profile(cs)
            profile.update(minimum_speaker_cosine=0.65, transcriber=context.ASR_MODEL, asr_revision=context.ASR_REVISION)
            proof = row['speaker_verification']
            alignment = proof['parent']['alignment']
            alignment.update(text='Vydechněte a předkloňte se.', language='cs', words=[
                dict(text='Vydechněte', start=0.52, end=1.2), dict(text='a', start=1.2, end=1.4),
                dict(text='předkloňte se.', start=1.4, end=1.9)])
            pcm = context.read_wav(parent)
            spec = importlib.util.spec_from_file_location('leading_pcm_encoder', ROOT / 'scripts/generate-lumi-guide-narration.py')
            driver = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(driver)
            clip = driver.encode(config, pcm[:57600], folder)
            duration = context.ogg_opus.opus_seconds(clip.read_bytes())
            relative = 'sunsalutation/voice-context/cs/' + ru.file_hash(parent) + '.wav'
            rule.update(parent_text=alignment['text'], prefix_alignment=context.RETAIN_LEADING_PCM0)
            proof.update(locale='cs', text_sha256=context.pcm_hash('Vydechněte.'.encode()),
                source_identity=context.source_identity(profile), clip_sha256=ru.file_hash(clip))
            proof['parent'].update(file=relative, text=alignment['text'], text_sha256=context.pcm_hash(alignment['text'].encode()))
            proof['crop'].update(start_sample=0, end_sample=28800, pcm_sha256=context.pcm_hash(pcm[:57600]),
                encoded_packets_sha256=context.packet_hash(clip))
            proof['proof_sha256'] = ru.json_hash({key: value for key, value in proof.items() if key != 'proof_sha256'})
            row.update(synthesis=proof['source_identity'], sha256=ru.file_hash(clip), seconds=round(duration, 3),
                transcription=dict(text='Vydechněte.', model=context.ASR_MODEL, revision=context.ASR_REVISION,
                    language='cs', audio_sha256=ru.file_hash(clip), input_samples=round(duration * 16000),
                    seconds=duration, truncation=False, long_form=True))
            config['_context_artifacts'] = [dict(source=str(parent), destination_relative=relative, sha256=ru.file_hash(parent))]
            matcher = lambda config, code, expected, actual, length, local: float(expected == actual)
            with patch.object(context, 'recipe', return_value=rule), patch.object(context, 'verifier', return_value=matcher):
                self.assertTrue(context.verify_speaker(config, profile, 'cs', 'Vydechněte.', row, clip))
                changed = copy.deepcopy(row)
                changed['speaker_verification']['crop'].update(start_sample=1, pcm_sha256=context.pcm_hash(pcm[2:57600]))
                changed_proof = changed['speaker_verification']
                changed_proof['proof_sha256'] = ru.json_hash({key: value for key, value in changed_proof.items() if key != 'proof_sha256'})
                self.assertFalse(context.verify_speaker(config, profile, 'cs', 'Vydechněte.', changed, clip))
                for text in ('Nadechněte.', 'Vydechněte a', ''):
                    changed = copy.deepcopy(row)
                    changed['transcription']['text'] = text
                    self.assertFalse(context.verify_speaker(config, profile, 'cs', 'Vydechněte.', changed, clip))
            without_opt_in = {key: value for key, value in rule.items() if key != 'prefix_alignment'}
            with patch.object(context, 'recipe', return_value=without_opt_in):
                self.assertFalse(context.verify_speaker(config, profile, 'cs', 'Vydechněte.', row, clip))

    def test_context_proof_offline_and_negative_audio_integrity(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            folder = Path(tmp)
            config, profile, row, clip, parent, rule = self.context_fixture(folder)
            matcher = lambda config, code, expected, actual, length, local: float(expected == actual)
            with patch.object(context, 'recipe', return_value=rule), patch.object(context, 'verifier', return_value=matcher):
                self.assertTrue(context.verify_speaker(config, profile, 'pt', 'Inspire.', row, clip))
                media = folder / 'media'
                exported_parent = media / row['speaker_verification']['parent']['file']
                exported_parent.parent.mkdir(parents=True)
                shutil.copyfile(parent, exported_parent)
                public_clip = media / 'sunsalutation/voice/pt/cue.ogg'
                public_clip.parent.mkdir(parents=True)
                shutil.copyfile(clip, public_clip)
                offline_config = {key: value for key, value in config.items() if key != '_context_artifacts'}
                self.assertTrue(context.verify_speaker(offline_config, profile, 'pt', 'Inspire.', row, public_clip))
                duration = context.ogg_opus.opus_seconds(clip.read_bytes())
                final = copy.deepcopy(row)
                final['transcription'] = dict(audio_sha256=final['sha256'], text='Inspire.', truncation=False,
                                             long_form=True, language='pt', model=context.ASR_MODEL,
                                             revision=context.ASR_REVISION, input_samples=round(duration * 16000), seconds=duration)
                self.assertTrue(context.verify_speaker(config, profile, 'pt', 'Inspire.', final, clip))
                for key, value in [('model', 'wrong'), ('revision', 'wrong'), ('language', 'cs'),
                                   ('input_samples', 1), ('seconds', 120), ('truncation', True)]:
                    changed = copy.deepcopy(final)
                    changed['transcription'][key] = value
                    with self.subTest(asr_field=key):
                        self.assertFalse(context.verify_speaker(config, profile, 'pt', 'Inspire.', changed, clip))
                changed = copy.deepcopy(row)
                changed['transcription'] = dict(audio_sha256=changed['sha256'], text='Inspire extra.', truncation=False, long_form=True)
                self.assertFalse(context.verify_speaker(config, profile, 'pt', 'Inspire.', changed, clip))
                for change in ('range', 'parent_hash', 'phrase', 'truncation', 'wrong_voice', 'packet_hash', 'reference'):
                    changed = copy.deepcopy(row)
                    proof = changed['speaker_verification']
                    if change == 'range': proof['crop']['end_sample'] += 1
                    if change == 'parent_hash': proof['parent']['pcm_sha256'] = '0' * 64
                    if change == 'phrase': proof['parent']['text'] = 'Other source phrase.'
                    if change == 'truncation': proof['parent']['alignment']['truncation'] = True
                    if change == 'wrong_voice': proof['parent_cosine'] = 0.2
                    if change == 'packet_hash': proof['crop']['encoded_packets_sha256'] = '0' * 64
                    if change == 'reference': proof['source_identity']['reference_sha256'] = '0' * 64
                    proof['proof_sha256'] = ru.json_hash({key: value for key, value in proof.items() if key != 'proof_sha256'})
                    with self.subTest(change=change):
                        self.assertFalse(context.verify_speaker(config, profile, 'pt', 'Inspire.', changed, clip))
                clip.write_bytes(b'wrong voice audio')
                self.assertFalse(context.verify_speaker(config, profile, 'pt', 'Inspire.', row, clip))

    def test_czech_native_token_route_is_scoped(self):
        registry = types.SimpleNamespace(SUPPORTED_LANGUAGES={'en':'English'})
        parent = types.ModuleType('chatterbox'); parent.mtl_tts = registry
        engine = object.__new__(cs.Engine)
        engine.profile = dict(language_id='cs', language_token_id=719, normalization='NFC', parameters={})
        engine.local = dict(reference='selected-female.wav')
        class Wave:
            def detach(self): return self
            def float(self): return self
            def cpu(self): return self
            def numpy(self): return [0.2]
        seen = []
        def generate(text, **args):
            self.assertEqual(registry.SUPPORTED_LANGUAGES['cs'], 'Czech')
            self.assertFalse(engine.model.tokenizer.text_to_tokens(text)['nfkd_normalize'])
            seen.append(args); return Wave()
        tokenizer = types.SimpleNamespace(token_to_id=lambda text: 719 if text == '[cs]' else 1)
        engine.model = types.SimpleNamespace(tokenizer=types.SimpleNamespace(tokenizer=tokenizer, text_to_tokens=lambda text, **kw: kw),
                                             generate=generate, sr=24000)
        with patch.dict(sys.modules, {'chatterbox':parent}):
            self.assertEqual(engine.synthesize('Czech cue'), ([0.2],24000))
            self.assertEqual(seen[0]['language_id'],'cs')
            self.assertNotIn('cs', registry.SUPPORTED_LANGUAGES)
            engine.profile['language_token_id']=999
            with self.assertRaises(RuntimeError): engine.synthesize('Czech cue')

    def test_cache_returns_verified_pcm_without_loading_model(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            e = object.__new__(ru.LocalEngine)
            e.profile = self.profile()
            e.local = {'cache':tmp}
            cfg = dict(pcm_sample_rate=24000, sample_rate=16000)
            identity = ru.json_hash(dict(request=ru.text_hash(cfg,'Hello',e.profile,'ru'), attempt=0))
            pcm = Path(tmp)/(identity+'.pcm'); pcm.write_bytes(b'\x01\x00'*10)
            (Path(tmp)/(identity+'.json')).write_text(json.dumps(dict(request=identity,sha256=ru.file_hash(pcm))))
            with patch.object(ru.subprocess, 'run'), patch.object(e, 'load', create=True) as load:
                actual, _ = e.speak(cfg,'Hello','ru',Path(tmp),0)
                self.assertEqual(actual, pcm.read_bytes()); load.assert_not_called()
                pcm.write_bytes(b'corrupt')
                load.side_effect = RuntimeError('fresh inference needed')
                with self.assertRaisesRegex(RuntimeError,'fresh inference'):
                    e.speak(cfg,'Hello','ru',Path(tmp),0)

    def test_incomplete_asr_receipt_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            f = Path(tmp)/'clip'; f.write_bytes(b'audio')
            e = object.__new__(ru.LocalEngine)
            e.local = dict(asr_command=['python',str(f),'{audio}','{language}'])
            e.profile = dict(asr_command_files={'1':ru.file_hash(f)}, transcriber='openai/whisper-small', asr_revision='pinned')
            row = dict(language='ru', audio_sha256=ru.file_hash(f), truncation=True, long_form=True,seconds=4,text='x')
            with patch.object(ru.subprocess,'run') as run:
                run.return_value.stdout=json.dumps(row)
                with self.assertRaises(RuntimeError): e.transcribe(f,'ru')

    def test_changed_reference_fails_before_importing_models(self):
        p=self.profile()
        p['adapter_sha256']=ru.file_hash(ru.__file__)
        with tempfile.TemporaryDirectory(dir=self.scratch) as tmp:
            ref=Path(tmp)/'ref';ref.write_bytes(b'changed')
            local=Path(tmp)/'local.json';local.write_text(json.dumps(dict(reference=str(ref))))
            with self.assertRaisesRegex(ValueError,'reference'):
                ru.Engine(p,local)


if __name__ == '__main__': unittest.main()
