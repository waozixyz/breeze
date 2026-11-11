"""Offline migration boundaries using synthetic audio, never model inference."""
from array import array
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('migration', ROOT / 'scripts/stage-context-narration-migration.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
c = migration.context


class MigrationTests(unittest.TestCase):
    def setUp(self):
        store = ROOT / 'backup/narration/tmp'
        store.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=store, prefix='migration-test-')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.speech = migration.speech_module()
        for owner, name in [(c, 'align_audio'), (c, 'transcribe_audio'), (c, 'ContextEngine'),
                            (self.speech, 'local_engine'), (self.speech, 'generate')]:
            guard = patch.object(owner, name, side_effect=AssertionError('Inference forbidden'))
            guard.start()
            self.addCleanup(guard.stop)
        for provider in self.speech.LOCAL_PROVIDERS.values():
            guard = patch.object(provider, 'Engine', side_effect=AssertionError('Engine forbidden'))
            guard.start()
            self.addCleanup(guard.stop)

    def fixture(self, chinese=False):
        practice, code, text, policy = ('sunsalutation', 'zh', '吸气。', 'short-context') if chinese else (
            'workout', 'cs', 'Start!', 'workout-czech-context')
        voice = practice + '/voice'
        config = migration.read_json(ROOT / ('design/sun-salutation/narration/narration.json' if chinese else
                                             'design/workout/narration.json'))
        profile = self.speech.local_adapter(config, code).descriptor(config)
        identity = c.source_identity(profile)
        rule = c.recipe(ROOT / ('design/narration/' + policy + '-provider-v4.json'), code, text, voice)
        pcm = array('h', [int(2000 * math.sin(index * 2 * math.pi * 220 / 24000))
                          for index in range(48000)]).tobytes()
        parent = self.folder / 'parent.wav'
        c.write_wav(parent, pcm)
        parent_hash = c.file_hash(parent)
        relative = practice + '/voice-context/' + code + '/' + parent_hash + '.wav'
        public = self.folder / 'media' / relative
        public.parent.mkdir(parents=True, exist_ok=True)
        public.write_bytes(parent.read_bytes())
        parent_text = rule['parent_text']
        first, rest = (parent_text[:2], parent_text[2:]) if chinese else parent_text.split(' ', 1)
        alignment = dict(text=parent_text, language=code, model=c.ASR_MODEL, revision=c.ASR_REVISION,
            audio_sha256=parent_hash, helper_sha256=c.file_hash(c.__file__), seconds=2.0, input_samples=32000,
            truncation=False, long_form=True, words=[dict(text=first, start=0.0, end=0.56),
                                                    dict(text=rest, start=0.56, end=1.9)])
        work = self.folder / 'encode'
        work.mkdir(exist_ok=True)
        encoded = self.speech.encode(config, pcm[:26880], work)
        clip = self.folder / 'media' / voice / code / 'cue.ogg'
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(encoded.read_bytes())
        duration = self.speech.seconds(clip)
        old_alignment = copy.deepcopy(alignment)
        old_alignment['helper_sha256'] = '0' * 64
        proof = dict(scope='context_parent', version=c.VERSION, policy_path='design/narration/' + policy + '.json',
            recipe_sha256='a' * 64, locale=code, text_sha256=c.pcm_hash(text.encode()), voice_directory=voice,
            source_identity=identity, actual_clip_cosine=0.4, parent_cosine=0.8, gender_verified=False,
            clip_sha256=c.file_hash(clip), parent=dict(file=relative, sha256=parent_hash,
                pcm_sha256=c.pcm_hash(pcm), text=parent_text, text_sha256=c.pcm_hash(parent_text.encode()),
                alignment=old_alignment), crop=dict(start_sample=0, end_sample=13440,
                pcm_sha256=c.pcm_hash(pcm[:26880]), encoded_packets_sha256=c.packet_hash(clip), float_peak=0.1))
        proof['proof_sha256'] = c.json_hash(proof)
        transcript = dict(text=text, language=code, model=c.ASR_MODEL if chinese else profile['transcriber'],
            revision=c.ASR_REVISION if chinese else profile['asr_revision'], audio_sha256=c.file_hash(clip),
            seconds=duration, input_samples=round(duration * 16000), truncation=False, long_form=True)
        if chinese:
            transcript.update(adapter_sha256=c.file_hash(c.__file__),
                              artifacts_sha256=c.json_hash(rule['crop_asr']['artifacts']))
        row = dict(synthesis=identity, speaker_cosine=0.4, speaker_verification=proof, seconds=duration,
            sha256=c.file_hash(clip), transcript=text, transcription=copy.deepcopy(transcript),
            transcriber='stale' if chinese else profile['transcriber'], text_sha256='b' * 64, match=1.0)
        entry = dict(item=dict(practice=practice, config=config, code=code, key='cue', text=text, row=row),
                     profile=profile, rule=rule, clip=clip, parent=public)
        return entry, alignment, transcript if chinese else None

    def test_success_preserves_audio_scores_identities_and_original_raw_execution(self):
        for chinese in (False, True):
            with self.subTest(chinese=chinese):
                entry, alignment, transcript = self.fixture(chinese)
                original = copy.deepcopy(entry['item']['row'])
                audio = (c.file_hash(entry['clip']), c.file_hash(entry['parent']))
                row, evidence = migration.migrate_row(self.speech, entry, alignment, transcript)
                self.assertEqual(entry['item']['row'], original)
                for field in ('synthesis', 'speaker_cosine', 'sha256', 'seconds'):
                    self.assertEqual(row[field], original[field])
                self.assertEqual(evidence['previous_proof'], original['speaker_verification'])
                self.assertEqual(evidence['previous_transcription'], original['transcription'])
                self.assertEqual(evidence['previous_proof']['parent']['alignment']['helper_sha256'], '0' * 64)
                self.assertEqual(row['speaker_verification']['parent']['alignment'], alignment)
                self.assertEqual(row['speaker_verification']['parent_cosine'], 0.8)
                self.assertFalse(row['speaker_verification']['gender_verified'])
                self.assertEqual(audio, (c.file_hash(entry['clip']), c.file_hash(entry['parent'])))
                self.assertNotEqual(row['text_sha256'], original['text_sha256'])

    def test_old_or_tampered_asr_and_changed_crop_cannot_migrate(self):
        entry, alignment, _ = self.fixture()
        mutations = [lambda a: a.update(helper_sha256='0' * 64), lambda a: a.update(audio_sha256='0' * 64),
                     lambda a: a.update(model='other'), lambda a: a.update(truncation=True),
                     lambda a: a.update(input_samples=1), lambda a: a['words'][0].update(end=0.50),
                     lambda a: a['words'][0].update(start=0.31), lambda a: a.update(text='wrong words')]
        for index, mutate in enumerate(mutations):
            bad = copy.deepcopy(alignment)
            mutate(bad)
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                migration.migrate_row(self.speech, entry, bad)
        changed = copy.deepcopy(entry)
        changed['item']['row']['speaker_verification']['parent_cosine'] = 0.1
        with self.assertRaises(ValueError):
            migration.migrate_row(self.speech, changed, alignment)

    def test_fresh_timestamps_can_differ_only_when_actual_crop_samples_stay_equal(self):
        entry, alignment, _ = self.fixture()
        original = copy.deepcopy(entry['item']['row'])
        alignment['words'][0]['end'] = 0.55
        # 25 ms padding clamps to the following word at .56: still 13,440 samples.
        self.assertEqual(c.prefix_range('Start!', alignment, 48000), (0, 13440))
        row, evidence = migration.migrate_row(self.speech, entry, alignment)
        self.assertEqual(row['speaker_verification']['crop'], original['speaker_verification']['crop'])
        self.assertEqual(row['speaker_verification']['parent']['alignment'], alignment)
        self.assertEqual(evidence['previous_proof'], original['speaker_verification'])

    def test_chinese_requires_fresh_crop_metadata_and_exact_transcript(self):
        entry, alignment, transcript = self.fixture(True)
        for bad in (None, dict(transcript, adapter_sha256='0' * 64),
                    dict(transcript, audio_sha256='0' * 64), dict(transcript, text='呼气。'),
                    dict(transcript, artifacts_sha256='0' * 64), dict(transcript, long_form=False)):
            with self.subTest(transcription=bad), self.assertRaises(ValueError):
                migration.migrate_row(self.speech, entry, alignment, bad)

    def test_incomplete_stage_never_changes_live_receipts(self):
        entry, _, _ = self.fixture()
        receipt = self.folder / 'receipt.json'
        document = dict(clips={'cs/cue': entry['item']['row'], 'cs/unrelated': dict(preserve='owner')})
        migration.write_json(receipt, document)
        original = receipt.read_bytes()
        receipts = dict(workout=dict(path=receipt, sha256=c.file_hash(receipt), document=document))
        with self.assertRaises(FileNotFoundError):
            migration.stage(self.speech, receipts, [entry], self.folder / 'missing')
        self.assertEqual(receipt.read_bytes(), original)
        self.assertEqual(document['clips']['cs/unrelated'], dict(preserve='owner'))

    def test_staging_preserves_unrelated_rows_and_detects_live_writer(self):
        entry, alignment, _ = self.fixture()
        receipt = self.folder / 'receipt.json'
        document = dict(clips={'cs/cue': entry['item']['row'], 'cs/unrelated': dict(preserve='owner')})
        migration.write_json(receipt, document)
        receipts = dict(workout=dict(path=receipt, sha256=c.file_hash(receipt), document=document))
        migration.write_json(self.folder / (migration.stem(entry) + '.alignment.json'), alignment)
        candidates, changes = migration.stage(self.speech, receipts, [entry], self.folder)
        self.assertEqual(len(changes), 1)
        self.assertEqual(candidates['workout']['clips']['cs/unrelated'], dict(preserve='owner'))
        self.assertEqual(migration.read_json(receipt), document)
        receipt.write_text(json.dumps(dict(clips={'new/writer': {}})))
        with self.assertRaisesRegex(ValueError, 'writer changed'):
            migration.stage(self.speech, receipts, [entry], self.folder)

    def test_plan_is_bounded_and_never_invokes_asr(self):
        entry, _, _ = self.fixture()
        chinese, _, _ = self.fixture(True)
        plan = migration.jobs([entry] * 11 + [chinese] * 2,
            dict(python='forbidden', model='forbidden'), self.folder / 'results')
        self.assertEqual(len(plan), 15)
        self.assertEqual(sum(x['kind'] == 'alignment' for x in plan), 13)
        self.assertEqual(sum(x['kind'] == 'transcription' for x in plan), 2)
        for job in plan:
            self.assertEqual(job['command'][:3], ['build-queue', '--', 'forbidden'])
            self.assertFalse(Path(job['output']).exists())
        with self.assertRaises(ValueError):
            migration.jobs([entry], dict(python='forbidden', model='forbidden'), self.folder)


    def successor_fixture(self, chinese=False):
        spec = importlib.util.spec_from_file_location('successors', ROOT / 'scripts/stage-context-narration-successors.py')
        successors = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(successors)
        # Pure reseal tests use current sealed synthetic rules. The historical
        # command's fixed helper seal is independently tested below.
        successors.SUCCESSORS = {old: new.replace('-provider-v3.json', '-provider-v4.json')
                                 for old, new in successors.SUCCESSORS.items()}
        entry, alignment, crop = self.fixture(chinese)
        accepted, _ = migration.migrate_row(self.speech, entry, alignment, crop)
        key = 'sun_salutation_voice_breathe_in' if chinese else 'workout_say_go'
        renamed = entry['clip'].with_name(key + '.ogg')
        entry['clip'].rename(renamed)
        entry['clip'] = renamed
        entry['item']['key'] = key
        proof = accepted['speaker_verification']
        old_path = next(old for old, new in successors.SUCCESSORS.items() if new == proof['policy_path'])
        old_rule = {k: v for k, v in entry['rule'].items() if k != 'sha256'}
        old_rule.update(policy_path=old_path, policy_sha256=successors.POLICY_SHAS[old_path])
        proof.update(policy_path=old_path, recipe_sha256=c.json_hash(old_rule))
        proof['proof_sha256'] = c.json_hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
        if chinese:
            accepted['verification'].update(profile_sha256=successors.POLICY_SHAS[old_path],
                                            context_recipe_sha256=proof['recipe_sha256'])
        accepted['text_sha256'] = self.speech.text_hash(entry['item']['config'], entry['item']['text'],
            entry['item']['code'], accepted['synthesis'], proof)
        entry['item']['row'] = accepted
        return successors, entry

    def reseal_fixture(self, successors, entry, previous=None):
        item = entry['item']
        return successors.reseal_row(self.speech, item['practice'], item['config'], item['code'],
            item['key'], item['text'], item['row'], item['row'] if previous is None else previous, entry['clip'])

    def test_successor_reseal_reuses_actual_asr_and_preserves_all_other_evidence(self):
        for chinese in (False, True):
            with self.subTest(chinese=chinese):
                successors, entry = self.successor_fixture(chinese)
                original = copy.deepcopy(entry['item']['row'])
                updated, evidence = self.reseal_fixture(successors, entry)
                self.assertFalse(evidence['inference_executed'])
                self.assertEqual(updated['transcription'], original['transcription'])
                self.assertEqual(updated['speaker_verification']['parent'], original['speaker_verification']['parent'])
                self.assertEqual(updated['speaker_verification']['crop'], original['speaker_verification']['crop'])
                self.assertEqual(updated['synthesis'], original['synthesis'])
                if chinese:
                    self.assertEqual(updated['verification'], dict(original['verification'],
                        profile_sha256=entry['rule']['policy_sha256'],
                        context_recipe_sha256=entry['rule']['sha256']))
                    self.assertEqual(evidence['derived_binding']['previous'], original['verification'])
                    self.assertEqual(evidence['derived_binding']['successor'], updated['verification'])
                else:
                    self.assertEqual(updated.get('verification'), original.get('verification'))
                    self.assertIsNone(evidence['derived_binding'])
                self.assertNotEqual(updated['text_sha256'], original['text_sha256'])
                self.assertEqual(c.file_hash(entry['clip']), original['sha256'])

    def test_historical_reseal_command_rejects_a_changed_helper(self):
        successors, _ = self.successor_fixture()
        seals = dict(successors.POLICY_SHAS, **{
            'scripts/generate-lumi-guide-narration.py': successors.GENERATOR_SHA,
            'scripts/local_narration_context.py': successors.HELPER_SHA})
        original_hash = c.file_hash
        archived = self.folder / 'old-generator.py'
        with patch.object(c, 'file_hash', side_effect=lambda path: successors.GENERATOR_SHA
                          if path == archived else original_hash(path)):
            with self.assertRaisesRegex(ValueError, 'Changed context helper'):
                successors.validate_seals(seals, archived)

    def test_successor_reseal_rejects_changed_predecessor_and_unknown_key(self):
        successors, entry = self.successor_fixture()
        previous = copy.deepcopy(entry['item']['row'])
        previous['speaker_cosine'] += .01
        with self.assertRaisesRegex(ValueError, 'predecessor row changed'):
            self.reseal_fixture(successors, entry, previous)
        entry['item']['key'] = 'unrequested'
        with self.assertRaisesRegex(ValueError, 'exact 13-row scope'):
            self.reseal_fixture(successors, entry)

    def test_successor_reseal_cannot_accept_unsafe_encoded_audio(self):
        successors, entry = self.successor_fixture()
        observed = dict(frames=round(entry['item']['row']['seconds'] * 48000),
                        rates={'16000': dict(peak=.1), '48000': dict(peak=1.001)})
        with patch.object(self.speech, 'encoded_audio_stats', return_value=observed):
            with self.assertRaisesRegex(ValueError, 'complete offline validation'):
                self.reseal_fixture(successors, entry)
        self.assertEqual(entry['item']['row']['speaker_verification']['policy_path'],
                         'design/narration/workout-czech-context-provider-v2.json')

    def test_successor_reseal_rejects_changed_recording(self):
        successors, entry = self.successor_fixture()
        entry['clip'].write_bytes(entry['clip'].read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed original clip'):
            self.reseal_fixture(successors, entry)


    def test_successor_derived_binding_cannot_change_the_asr_execution(self):
        successors, entry = self.successor_fixture(True)
        entry['item']['row']['verification']['adapter_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed ASR execution identity'):
            self.reseal_fixture(successors, entry)


class HelperSuccessorScopeTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('helper_successors',
            ROOT / 'scripts/stage-context-narration-helper-successors.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_exact_fifteen_row_seventeen_job_plan_and_partial_rejection(self):
        successor = self.module()
        entries = []
        for practice, full_key in sorted(successor.EXPECTED):
            code, key = full_key.split('/', 1)
            policy = ('short-context-provider-v4.json' if practice == 'sunsalutation' else
                      'workout-portuguese-context-v3.json' if code == 'pt' else
                      'workout-czech-context-provider-v4.json')
            entries.append(dict(item=dict(practice=practice,code=code,key=key),
                parent=Path(__file__),clip=Path(__file__),
                rule=dict(policy_path='design/narration/'+policy,
                          **({'crop_asr': {'version':'fixture'}} if code == 'zh' else {}))))
        plan = successor.jobs(entries,dict(python='forbidden',model='forbidden'),ROOT/'backup/narration/unused')
        self.assertEqual(len(plan),17)
        self.assertEqual(sum(job['kind']=='alignment' for job in plan),15)
        self.assertEqual(sum(job['kind']=='transcription' for job in plan),2)
        for job in plan:
            self.assertEqual(job['command'][:3],['build-queue','--','forbidden'])
            self.assertFalse(Path(job['output']).exists())
        for partial in [entries[:-1],entries+[entries[0]]]:
            with self.assertRaisesRegex(ValueError,'Incomplete fifteen-row'):
                successor.jobs(partial,{},ROOT)
            with self.assertRaisesRegex(ValueError,'Incomplete fifteen-row'):
                successor.stage(None,{},partial,ROOT)

    def test_unreviewed_manifest_is_rejected_before_loading(self):
        successor = self.module()
        with self.assertRaisesRegex(ValueError,'Changed reviewed inventory'):
            successor.inventory(Path(__file__))


if __name__ == '__main__':
    unittest.main()
