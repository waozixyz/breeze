"""Shared local-provider routing and encoded-clip resume contracts."""
from array import array
import copy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('narration', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


class LocalNarrationPipelineTests(unittest.TestCase):
    def setUp(self):
        output = ROOT / 'build/local-narration-pipeline-test'
        output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.config = json.loads((ROOT / 'design/astral-projection/bruce-narration.json').read_text())

    def profile(self, module):
        sources = ['f5_russian_narration.py', 'prepare-local-voice-profile.py', 'whisper_narration.py']
        if module.LANGUAGES[0] != 'ru':
            sources.append(module.__name__ + '.py')
        profile = dict(schema=1, provider=module.__name__, model=module.MODEL,
                    model_revision=module.MODEL_REVISION, runtime_version='test',
                    locale=module.LANGUAGES[0], status='ready', seed=1,
                    reference_sha256='a' * 64, adapter_sha256='b' * 64,
                    reference_text='Exact reference.', parameters={'temperature': 0.8},
                    environment={'torch': 'test'}, artifacts={'weights': 'c' * 64},
                    minimum_speaker_cosine=0.7, transcriber='offline fixture',
                    source_files={name: speech.ming_narration.file_hash(ROOT / 'scripts' / name)
                                  for name in sources})
        if module.KEY == 'chatterbox-portuguese':
            profile['segmentation'] = dict(mode='bounded-text-v1',
                                           maximum_characters=160, pause_seconds=0.12)
        return profile

    def test_female_portuguese_text_variant_preserves_male_and_other_languages(self):
        directory = ROOT / 'design/sun-salutation/narration/text'
        female = json.loads((ROOT / 'design/sun-salutation/narration/narration.json').read_text())
        male = json.loads((ROOT / 'design/sun-salutation/narration/narration-male.json').read_text())
        keys = speech.narration_keys(female)
        with patch.object(speech, 'LOCALES', directory):
            female_pt = dict((key, text) for _, key, text in speech.wanted(female, ['pt'], keys))
            male_pt = dict((key, text) for _, key, text in speech.wanted(male, ['pt'], keys))
            changed = {key for key in keys if female_pt[key] != male_pt[key]}
            self.assertEqual(changed, {'sun_salutation_voice_breathe_out', 'sun_salutation_voice_downward_dog'})
            self.assertEqual(female_pt['sun_salutation_voice_breathe_out'], 'Solte o ar.')
            self.assertEqual(male_pt['sun_salutation_voice_breathe_out'], 'Expire.')
            for code in set(speech.LANGUAGES) - {'pt'}:
                self.assertEqual(speech.wanted(female, [code], keys), speech.wanted(male, [code], keys))
            invalid = dict(female, locale_text_files={'pt': str(self.folder / 'missing.txt')})
            with self.assertRaises(FileNotFoundError):
                speech.wanted(invalid, ['pt'], keys)
        module = speech.LOCAL_PROVIDERS['chatterbox-portuguese']
        profile = module.descriptor(female)
        old_config = dict(female)
        old_config.pop('locale_text_files')
        self.assertEqual(module.provenance(profile), module.provenance(module.descriptor(old_config)))
        self.assertEqual(module.text_hash(female, male_pt[keys[0]], profile, 'pt'),
                         module.text_hash(old_config, male_pt[keys[0]], profile, 'pt'))
        import local_narration_context as context
        rule = context.recipe(ROOT / 'design/narration/short-context-provider-v4.json', 'pt', 'Solte o ar.', 'sunsalutation/voice')
        self.assertEqual(rule['parent_source']['file'], female['locale_text_files']['pt'])
        self.assertEqual(rule['parent_text'], female_pt['sun_salutation_voice_downward_dog'])
        self.assertIsNone(context.recipe(ROOT / 'design/narration/short-context-provider-v4.json', 'pt', 'Expire.', 'sunsalutation/voice'))
        self.assertIsNone(context.recipe(ROOT / 'design/narration/short-context-provider-v4.json', 'pt', 'Solte o ar.', 'sunsalutation/voice-male'))
        bad = copy.deepcopy(context.load_policy(ROOT / 'design/narration/short-context-provider-v4.json'))
        for candidate in bad['rules']:
            if candidate['locale'] == 'pt':
                candidate['parent_source'].update(file='design/sun-salutation/narration/text/pt.txt',
                    sha256=speech.ming_narration.file_hash(directory / 'pt.txt'))
        with patch.object(context, 'load_policy', return_value=bad):
            with self.assertRaises(ValueError):
                context.recipe(ROOT / 'design/narration/short-context-provider-v4.json', 'pt', 'Solte o ar.', 'sunsalutation/voice')

    def test_russian_guide_voice_text_preserves_ui_other_lines_and_profiles(self):
        config = json.loads((ROOT / 'design/lumi-guide/narration.json').read_text())
        original = dict(config)
        original.pop('locale_text_files')
        keys = speech.narration_keys(config)
        with patch.object(speech, 'LOCALES', ROOT / 'locales'):
            spoken = {key: text for _, key, text in speech.wanted(config, ['ru'], keys)}
            displayed = {key: text for _, key, text in speech.wanted(original, ['ru'], keys)}
            self.assertEqual(len(keys), 32)
            self.assertEqual({key for key in keys if spoken[key] != displayed[key]}, {'profile_guide_more'})
            self.assertEqual(spoken['profile_guide_more'],
                             'Ниже — твои друзья, данные, аккаунт и Телеграм. Каждый раздел открывается одним нажатием.')
            self.assertEqual(displayed['profile_guide_more'],
                             'Ниже твои друзья, данные, аккаунт и Telegram, каждое в одно касание.')
            for code in set(speech.LANGUAGES) - {'ru'}:
                self.assertEqual(speech.wanted(config, [code], keys), speech.wanted(original, [code], keys))
        module = speech.LOCAL_PROVIDERS['f5-russian']
        profile = module.descriptor(config)
        self.assertEqual(profile, module.descriptor(original))
        for key in keys:
            old_hash = module.text_hash(original, displayed[key], profile, 'ru')
            new_hash = module.text_hash(config, spoken[key], profile, 'ru')
            if key == 'profile_guide_more':
                self.assertNotEqual(old_hash, new_hash)
            else:
                self.assertEqual(old_hash, new_hash)

    def test_each_provider_routes_only_its_language_and_preserves_other_receipts(self):
        for provider in ('f5-russian', 'chatterbox-czech', 'chatterbox-portuguese'):
            with self.subTest(provider=provider):
                module = speech.LOCAL_PROVIDERS[provider]
                code = module.LANGUAGES[0]
                profile = self.profile(module)
                config = dict(self.config, keys=['cue'], **{module.KEY: profile})
                config.pop('keys_file')
                config_path = self.folder / 'config.json'
                config_path.write_text(json.dumps(config))
                local_path = self.folder / 'local.json'
                local_path.write_text(json.dumps({'python': sys.executable}))
                receipt_path = self.folder / 'receipt.json'
                untouched = {'bytes': 7, 'sha256': 'preserved existing recording'}
                receipt_path.write_text(json.dumps({'clips': {'en/cue': untouched}}))
                content = self.folder / 'apps/practice/content.json'
                content.parent.mkdir(parents=True, exist_ok=True)
                content.write_text(json.dumps({'narration': {'guide': {}}}))
                engine = SimpleNamespace(profile=profile)
                generated = {'bytes': 10, 'seconds': 2, 'match': 1}
                rows = [('en', 'cue', 'Relax.'), ('ru', 'cue', 'Расслабьтесь.'),
                        ('cs', 'cue', 'Uvolněte se.'), ('pt', 'cue', 'Relaxe.')]
                with patch.object(speech, 'ROOT', self.folder), \
                        patch.object(speech, 'CONFIG', config_path), \
                        patch.object(speech, 'RECEIPT', receipt_path), \
                        patch.object(speech, 'VOICE', self.folder / provider / 'voice'), \
                        patch.object(speech, 'LOCALES', self.folder / 'text'), \
                        patch.object(speech, 'MEDIA_ROOT', None), \
                        patch.object(speech, 'writable_media', return_value=self.folder), \
                        patch.object(speech, 'locale_codes', return_value=['en', 'ru', 'cs', 'pt']), \
                        patch.object(speech, 'wanted', side_effect=lambda cfg, codes, keys:
                                     [row for row in rows if row[0] in codes]), \
                        patch.object(module, 'Engine', return_value=engine) as construct, \
                        patch.object(speech, 'generate', return_value=generated) as generate, \
                        patch.object(sys, 'argv', ['generate', '--local-provider', provider,
                                                   '--local-voice-profile', str(local_path)]):
                    speech.main()
                construct.assert_called_once_with(profile, local_path)
                self.assertEqual(generate.call_count, 1)
                self.assertEqual(generate.call_args.args[2], code)
                self.assertIs(generate.call_args.args[0]['_local_engine'], engine)
                saved = json.loads(receipt_path.read_text())
                self.assertEqual(saved['clips']['en/cue'], untouched)
                self.assertEqual(saved['clips'][code + '/cue'], generated)

    def test_real_female_configs_reference_the_portuguese_provider_key(self):
        module = speech.LOCAL_PROVIDERS['chatterbox-portuguese']
        self.assertEqual(module.KEY, 'chatterbox-portuguese')
        content = json.loads((ROOT / 'apps/practice/content.json').read_text())
        for name, settings in content['narration'].items():
            with self.subTest(practice=name):
                config = json.loads((ROOT / settings['config']).read_text())
                if name.endswith('_male'):
                    self.assertNotIn(module.KEY, config)
                else:
                    self.assertEqual(config[module.KEY], 'design/narration/chatterbox-portuguese.json')

    def test_cached_local_preflight_requires_and_constructs_the_context_guard(self):
        local_path = self.folder / 'local.json'
        local_path.write_text(json.dumps({'python': sys.executable}))
        context_path = self.folder / 'context.json'
        context_local_path = self.folder / 'context-local.json'
        media = self.folder / 'media'
        for provider in ('f5-russian', 'chatterbox-czech', 'chatterbox-portuguese'):
            module = speech.LOCAL_PROVIDERS[provider]
            profile = self.profile(module)
            config = dict(self.config, keys=['cue'], **{module.KEY: profile})
            config.pop('keys_file')
            config_path = self.folder / 'config.json'
            config_path.write_text(json.dumps(config))
            engine = SimpleNamespace(profile=profile)
            constructor = Mock(return_value=SimpleNamespace(profile=profile))
            base = ['generate', '--local-provider', provider,
                    '--local-voice-profile', str(local_path), '--cached-only', '--preflight']
            valid = ['--context-profile', str(context_path),
                     '--context-local-profile', str(context_local_path)]
            for arguments in ([], valid[:2], valid[2:], valid):
                with self.subTest(provider=provider, arguments=arguments), \
                        patch.object(speech, 'CONFIG', config_path), \
                        patch.object(speech, 'VOICE', media / 'sunsalutation/voice'), \
                        patch.object(speech, 'MEDIA_ROOT', None), \
                        patch.object(speech, 'media_path', return_value=media), \
                        patch.object(module, 'Engine', return_value=engine) as construct, \
                        patch.dict(sys.modules, local_narration_context=SimpleNamespace(ContextEngine=constructor)), \
                        patch.object(sys, 'stderr', io.StringIO()), \
                        patch.object(sys, 'argv', base + arguments):
                    constructor.reset_mock()
                    if arguments != valid:
                        with self.assertRaises(SystemExit) as error:
                            speech.main()
                        self.assertEqual(error.exception.code, 2)
                        construct.assert_not_called()
                        constructor.assert_not_called()
                        continue
                    speech.main()
                    construct.assert_called_once_with(profile, local_path)
                    constructor.assert_called_once()
                    self.assertIs(constructor.call_args.args[0], engine)
                    self.assertTrue(constructor.call_args.args[1]['_cached_only'])
                    self.assertEqual(constructor.call_args.args[2:4], (context_path, context_local_path))
                    self.assertEqual(constructor.call_args.kwargs['voice_directory'], 'sunsalutation/voice')

    def test_wrong_interpreter_and_wrong_locale_fail_before_models_or_network(self):
        local_path = self.folder / 'local.json'
        local_path.write_text(json.dumps({'python': '/unselected/runtime/python'}))
        base = [sys.executable, str(ROOT / 'scripts/generate-lumi-guide-narration.py'),
                '--local-provider', 'f5-russian', '--local-voice-profile', str(local_path)]
        for arguments, message in [(['--preflight'], 'profile Python interpreter'),
                                   (['--check', '--locale', 'en'], 'no fallback is performed')]:
            result = subprocess.run(base + arguments, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(message, result.stderr)

    def test_portuguese_directions_reject_swapped_limbs_despite_high_full_match(self):
        text = ('Mantenha a respiração calma e os ombros relaxados enquanto sente os pés. '
                'Levante a mão esquerda e mantenha a mão direita junto ao corpo.')
        heard = text.replace('esquerda', 'direita', 1)
        self.assertGreater(speech.match(text, heard), 0.92)
        config = dict(self.config, verify_directions=True)
        self.assertEqual(speech.verified_match(config, 'pt', text, heard), 0)
        self.assertEqual(speech.verified_match(config, 'pt', text, text), 1)
        self.assertEqual(speech.direction_tokens('pé esquerdo, mãos direitas', 'pt'), ('left', 'right'))

    def test_resume_binds_provider_profile_language_and_full_encoded_audio(self):
        pcm = array('h', [int(4000 * math.sin(index * 2 * math.pi * 220 / 24000))
                          for index in range(48000)]).tobytes()
        clip = speech.encode(self.config, pcm, self.folder)
        length = speech.seconds(clip)
        text = 'Keep breathing calmly. Open your eyes.'
        for provider in ('f5-russian', 'chatterbox-czech', 'chatterbox-portuguese'):
            module = speech.LOCAL_PROVIDERS[provider]
            code = module.LANGUAGES[0]
            profile = self.profile(module)
            config = dict(self.config, **{module.KEY: profile})
            row = dict(text_sha256=module.text_hash(config, text, profile, code),
                       sha256=module.file_hash(clip) if hasattr(module, 'file_hash') else
                       speech.ming_narration.file_hash(clip), seconds=length,
                       transcript=text, synthesis=module.provenance(profile), speaker_cosine=0.9,
                       transcriber=profile['transcriber'])
            row['transcription'] = dict(audio_sha256=row['sha256'], seconds=length,
                                        truncation=False, long_form=True)
            receipt = {'clips': {code + '/cue': row}}
            with patch.object(speech, 'clip_path', return_value=clip):
                self.assertTrue(speech.current(receipt, config, code, 'cue', text))
                for field, value in [('reference_sha256', 'd' * 64), ('seed', 2),
                                     ('parameters', {'temperature': 0.1}),
                                     ('adapter_sha256', 'e' * 64)]:
                    changed = copy.deepcopy(config)
                    changed[module.KEY][field] = value
                    self.assertFalse(speech.current(receipt, changed, code, 'cue', text))
                row['transcription']['truncation'] = True
                self.assertFalse(speech.current(receipt, config, code, 'cue', text))
                row['transcription']['truncation'] = False
                row['transcript'] = 'Keep breathing calmly.'
                self.assertFalse(speech.current(receipt, config, code, 'cue', text))


if __name__ == '__main__':
    unittest.main()
