"""Explicit PT count views; frozen real diagnostics and synthetic proof replay."""
import copy
from array import array
import math
import tempfile
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import patch
import json
import unittest
import narration_speaker_context_test as fixtures
import local_narration_context as c
ROOT, speech = fixtures.ROOT, fixtures.speech


class PortugueseCountTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'design/workout/narration.json').read_text())
        self.policy = ROOT / 'design/narration/workout-portuguese-count-semantics-v1.json'

    def rule(self, text):
        return c.recipe(self.policy, 'pt', text, 'workout/voice')

    def test_exact_count_views_and_raw_numeric_boundaries(self):
        for digit, word in [('1', 'Um'), ('2', 'Dois'), ('3', 'Três')]:
            text = word + '.'
            rule = self.rule(text)
            for heard in [word, word.lower() + '!', digit, digit + '.', digit + ',', digit + '!']:
                self.assertEqual(*c.comparison_views(rule, text, heard))
            for heard in ['+{n}', '-{n}', '{n}.0', '{n},0', '0{n}', '{n}º', '{n}ª', '{n}st',
                          '{n}e0', '{n}x', 'x{n}', '1 2', '13', '31', '0', '4', '',
                          'a {n}', '{n} {n}', 'já', 'um dois três']:
                self.assertNotEqual(*c.comparison_views(rule, text, heard.format(n=digit)))
            for heard in ['１２３'[int(digit)-1], '¹²³'[int(digit)-1]]:
                self.assertNotEqual(*c.comparison_views(rule, text, heard))
            parent = rule['parent_text']
            numeric_parent = digit + parent[len(word):]
            self.assertEqual(c.parent_match(speech.complete_match, self.config, 'pt', rule,
                                           numeric_parent, 3), 1.0)
            for heard in [parent + ' agora', 'A ' + parent, parent.replace('corpo', 'braço'),
                          parent.replace(word, '', 1), '4' + parent[len(word):],
                          digit + ' ' + numeric_parent, parent.replace('Prepare', '3 Prepare')]:
                self.assertEqual(c.parent_match(speech.complete_match, self.config, 'pt', rule, heard, 3), 0)
            self.assertNotEqual(c.words(digit), c.words(word))
            self.assertEqual(c.comparison_words(digit), c.words(digit))
            self.assertEqual(c.comparison_views({}, text, digit), (text, digit))

    def test_registration_is_exact_and_cannot_extend_to_go_or_other_sources(self):
        rule = self.rule('Três.')
        for key, value in [('locale', 'cs'), ('voice_directory', 'taichi/voice'), ('text', 'Já!'),
                           ('parent_text', 'Três. Outro exercício.'),
                           ('comparison', {'version': 'unknown'}),
                           ('comparison', {'version': c.PORTUGUESE_COUNT_COMPARISON, 'extra': 1})]:
            with self.assertRaises(ValueError):
                c.rule_comparison(dict(rule, **{key: value}))
        for key in ['prefix_alignment', 'crop_asr', 'parent_source']:
            with self.assertRaises(ValueError):
                c.rule_comparison(dict(rule, **{key: {}}))
        with self.assertRaises(ValueError):
            c.comparison_views(rule, '3.', '3.')
        ordinary = c.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json',
                            'pt', 'Três.', 'workout/voice')
        self.assertIsNone(c.rule_comparison(ordinary))
        self.assertEqual(c.parent_match(speech.complete_match, self.config, 'pt', rule,
                                       'Dois. Prepare o corpo para o próximo exercício.', 3), 0)

    def test_all_six_successors_keep_historical_descriptor_bytes_and_semantics(self):
        historical_pins = {
            'design/narration/workout-portuguese-context-v2.json':
                '2acb06d934e227dde984a36a7831b5bb2ac27f76256c76721652428800fbacd6',
            'design/narration/tai-chi-short-context-provider-v2.json':
                'def352e915dc4e03af25691402ff56201368f6783f7e5dd0f32def7e9e9fde72',
            'design/narration/short-context-provider-v2.json':
                '5a56a9525cb2714868d995709549be6aa171f2ff138a549af3f16908d3670d1f',
            'design/narration/workout-czech-context-provider-v2.json':
                '4558186f263b4880ecadcbd7a8f62f6ef6af460a362c04346d22a61d0ba87596',
            'design/narration/tai-chi-short-context-provider-v3.json':
                '963cc6730505ea3e1ed279f2b5de8be870cef910187bd6461df8213e2c4b18cc',
            'design/narration/workout-czech-count-semantics-v1.json':
                'e88494e1032f09d7b0c3b5085a4e9a78a65602747fea79c15b74bf36b72d1e13',
            'design/narration/workout-czech-context-provider-v3.json':
                '6edec4363bc37dd7f677d004b814e7a177e4ee3bb00830c71faf7bb4b6c015d3',
            'design/narration/workout-portuguese-context-v1.json':
                '0c92d84fde6c1b69f32dca0d52199df58eab9487238c90f897089fce39d0183d',
            'design/narration/short-context-provider-v3.json':
                '7610dafbfff8de7dc8cfcd12a60b77711bfde0953c7c72d18130971d35775a7c',
            'design/narration/workout-czech-count-semantics-v2.json':
                '3538755837ff282696382b07859ba2cc26a1a39e78c6100a57e52de3c32bb5d3',
        }
        for name, digest in historical_pins.items():
            self.assertEqual(c.file_hash(ROOT / name), digest)
        pairs = [('short-context-provider-v3', 'short-context-provider-v4'),
                 ('workout-czech-context-provider-v3', 'workout-czech-context-provider-v4'),
                 ('tai-chi-short-context-provider-v3', 'tai-chi-short-context-provider-v4'),
                 ('workout-czech-count-semantics-v2', 'workout-czech-count-semantics-v3'),
                 ('workout-portuguese-context-v2', 'workout-portuguese-context-v3')]
        for old, new in pairs:
            previous = json.loads((ROOT / 'design/narration' / (old + '.json')).read_text())
            current = c.load_policy(ROOT / 'design/narration' / (new + '.json'))
            self.assertEqual(current, dict(previous, helper_sha256=c.file_hash(c.__file__),
                                           verifier_sha256=c.file_hash(ROOT / "scripts/generate-lumi-guide-narration.py")))
            with self.assertRaises(ValueError):
                c.load_policy(ROOT / 'design/narration' / (old + '.json'))
        numeric = c.load_policy(self.policy)
        previous = c.load_policy(ROOT / 'design/narration/workout-portuguese-context-v3.json')
        expected = [dict(r, comparison={'version': c.PORTUGUESE_COUNT_COMPARISON})
                    for r in previous['rules'] if r['text'] in c.PORTUGUESE_COUNT_PARENTS]
        self.assertEqual(numeric, dict(previous, rules=expected))

    def test_sixteen_real_diagnostics_keep_raw_qa_and_voice_time_gates(self):
        rows = json.loads((ROOT / 'tests/fixtures/portuguese-count-diagnostics.json').read_text())
        self.assertEqual(len(rows), 16)
        semantic, viable = [], []
        for row in rows:
            before = copy.deepcopy(row)
            if row['target'] in c.PORTUGUESE_COUNT_PARENTS:
                rule = self.rule(row['target'])
            else:
                rule = c.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json',
                                'pt', row['target'], 'workout/voice')
            try:
                start, end = c.prefix_range(row['target'], row['actual_alignment'],
                    round(row['parent_seconds'] * 24000), comparison=c.rule_comparison(rule))
                match = c.parent_match(speech.complete_match, self.config, 'pt', rule,
                                       row['actual_alignment']['text'], row['parent_seconds'])
                prefix_ok = match >= .92
            except ValueError:
                prefix_ok = False
            if prefix_ok:
                semantic.append((row['key'], row['source_attempt']))
                if row['actual_parent_cosine'] >= .65 and .5 <= (end-start)/24000 <= .95:
                    viable.append((row['key'], row['source_attempt']))
            self.assertEqual(row, before)
        self.assertEqual(set(viable), {('workout_say_count_3', n) for n in [4,5,6]} |
                                     {('workout_say_count_1', n) for n in [4,7]})
        self.assertNotIn(('workout_say_count_2', 7), semantic)
        self.assertFalse(any(key == 'workout_say_go' for key, _ in viable))

    def test_prefix_coherence_onset_contiguity_and_full_audio_boundaries(self):
        rule = self.rule('Três.')
        version = c.rule_comparison(rule)
        alignment = dict(text='3. Prepare o corpo para o próximo exercício.', words=[
            dict(text='3.', start=.04, end=.72),
            dict(text='Prepare o corpo para o próximo exercício.', start=.72, end=3)])
        self.assertEqual(c.prefix_range('Três.', alignment, 96000, comparison=version), (0,17280))
        for modify in [lambda a:a.update(text='2. Prepare o corpo para o próximo exercício.'),
                       lambda a:a['words'][0].update(start=.31),
                       lambda a:a['words'][0].update(end=.74),
                       lambda a:a['words'][1].update(end=5),
                       lambda a:a.update(words=a['words'][:1])]:
            bad = copy.deepcopy(alignment)
            modify(bad)
            with self.assertRaises(ValueError):
                c.prefix_range('Três.', bad, 96000, comparison=version)
        with self.assertRaises(ValueError):
            c.prefix_range('Três.', alignment, 96000, comparison=version, retain_leading_pcm0=True)
        with self.assertRaises(ValueError):
            c.prefix_range('Três.', alignment, 96000)

    def test_generate_and_current_replay_semantics_keep_raw_asr_and_all_proof_gates(self):
        staging = ROOT / 'backup/narration/tmp'
        staging.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=staging, prefix='count-proof-unit-') as temporary:
            folder = Path(temporary)
            media = folder / 'media'
            voice = media / 'workout/voice'
            voice.mkdir(parents=True)
            profile = speech.LOCAL_PROVIDERS['chatterbox-portuguese'].descriptor(self.config)
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
                    patch.object(speech.chatterbox_portuguese_narration, 'Engine', side_effect=AssertionError('Engine forbidden')):
                for n, word in [('3', 'Três'), ('2', 'Dois'), ('1', 'Um')]:
                    rule = self.rule(word + '.')
                    raw_parent = rule['parent_text'].replace(word, n, 1)
                    first, rest = raw_parent.split(' ', 1)
                    alignment = dict(text=raw_parent, words=[dict(text=first, start=0.0, end=0.56),
                        dict(text=rest, start=0.56, end=1.9)], language='pt', model=c.ASR_MODEL,
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
                        row = speech.generate(config, None, 'pt', key, word + '.')
                        receipt = dict(clips={'pt/' + key: row})
                        clip = voice / 'pt' / (key + '.ogg')
                        self.assertEqual(requests[-1], c.PORTUGUESE_COUNT_PARENTS[word + '.'])
                        self.assertEqual(row['transcript'], raw)
                        self.assertEqual(row['transcription']['text'], raw)
                        self.assertEqual(row['speaker_verification']['parent']['alignment'], alignment)
                        self.assertEqual(row['speaker_cosine'], 0.4)
                        self.assertEqual(row['speaker_verification']['parent_cosine'], 0.8)
                        self.assertEqual(row['match'], 1.0)
                        self.assertEqual(row['synthesis'], identity)
                        self.assertTrue(speech.current(receipt, config, 'pt', key, word + '.'))
                        self.assertNotEqual(speech.text_hash(config, word + '.', 'pt', identity), row['text_sha256'])
                        for heard in ('Já!', word + ' agora.', 'A ' + word, 'direita ' + word, ''):
                            bad = copy.deepcopy(row)
                            bad['transcript'] = bad['transcription']['text'] = heard
                            self.assertFalse(speech.current(dict(clips={'pt/' + key: bad}), config, 'pt', key, word + '.'))
                            base.transcribe = lambda *args: heard
                            with self.assertRaises(c.ContextRejected):
                                wrapped.transcribe(clip, 'pt')
                        for mutate in (
                                lambda proof: proof.update(parent_cosine=profile['minimum_speaker_cosine'] - .001),
                                lambda proof: proof['crop'].update(start_sample=1),
                                lambda proof: proof['parent']['alignment'].update(helper_sha256='0' * 64),
                                lambda proof: proof['parent']['alignment'].update(text=raw_parent + ' vlevo')):
                            bad = copy.deepcopy(row)
                            proof = bad['speaker_verification']
                            mutate(proof)
                            proof['proof_sha256'] = c.json_hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
                            self.assertFalse(speech.current(dict(clips={'pt/' + key: bad}), config, 'pt', key, word + '.'))
                        bad = copy.deepcopy(row)
                        bad['seconds'] = .96
                        self.assertFalse(speech.current(dict(clips={'pt/' + key: bad}), config, 'pt', key, word + '.'))
                        disabled = dict(config)
                        disabled.pop('chatterbox-portuguese')
                        self.assertFalse(speech.current(receipt, disabled, 'pt', key, word + '.'))

if __name__ == '__main__':
    unittest.main()
