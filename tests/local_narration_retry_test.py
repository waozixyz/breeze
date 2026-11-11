"""Fresh retry contracts with frozen production gates and synthetic PCM/ASR fixtures.

No speech or recognition model is loaded. Encoding and receipt validation are real.
"""
from array import array
from concurrent.futures import ThreadPoolExecutor
import copy
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('local_retry', ROOT / 'scripts/retry-local-narration.py')
retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retry)


class FakeEngine:
    """Controlled test double at the original model/recognizer boundary only."""
    def __init__(self, fixture, *, transcript=None, speaker=0.95, duration=1.0, errors=None):
        self.fixture = fixture
        self.profile = fixture.profile
        self.transcript = transcript
        self.speaker = speaker
        self.duration = duration
        self.errors = list(errors or [])
        self.calls = []
        self.last_generation = None

    def speak(self, config, text, code, work, attempt):
        self.calls.append(attempt)
        plan = self.fixture.plan(text)
        candidate = plan._candidate(attempt)
        if self.errors:
            error = self.errors.pop(0)
            if error == 'raw_peak':
                part = candidate['raw'][0]
                plan.cache.mkdir(parents=True, exist_ok=True)
                raw = plan.cache / (part['identity'] + '.wav')
                # A real finite IEEE float WAV retains its overshoot without scaling.
                data = struct.pack('<4f', 0.0, 1.125, -0.5, 0.0)
                header = (b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' +
                          struct.pack('<IHHIIHH', 16, 3, 1, 24000, 96000, 4, 32) +
                          b'data' + struct.pack('<I', len(data)))
                raw.write_bytes(header + data)
                evidence = dict(identity=part['identity'], seed=part['seed'], samples=4,
                    sample_rate=24000, finite=True, raw_peak=1.125, gain=1.0,
                    raw_sha256=retry.checksum(raw), budget={'test_fixture': True})
                (plan.cache / (part['identity'] + '.raw.json')).write_text(json.dumps(evidence))
                raise RuntimeError('Ming finite waveform peak exceeds PCM range: ' + json.dumps(evidence))
            if error is not None:
                raise error
        self.last_generation = dict(attempt=attempt, plan=retry.ming.segment_plan(
            retry.ming_verification.synthesis_profile(self.profile), text), chunks=candidate['raw'])
        pcm = array('h', (int(5000 * math.sin(2 * math.pi * 220 * index / 24000))
                          for index in range(round(24000 * self.duration)))).tobytes()
        return pcm, self.fixture.module.provenance(self.profile)

    def speaker_match(self, clip):
        return self.speaker

    def transcribe(self, clip, code):
        text = self.transcript if self.transcript is not None else self.fixture.text
        samples = len(subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(clip),
            '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
            check=True, capture_output=True).stdout) // 2
        identity = (self.fixture.module.verification_identity(self.profile, code)
                    if hasattr(self.fixture.module, 'verification_identity') else
                    dict(model=self.profile['transcriber'], revision=self.profile['asr_revision']))
        self.last_transcription = dict(identity, text=text, language=code,
            audio_sha256=retry.checksum(clip), input_samples=samples, seconds=samples / 16000,
            truncation=False, long_form=True)
        return text


class RetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = ('scripts/generate-lumi-guide-narration.py', 'scripts/ming_narration.py',
                 'scripts/ming_verification.py', 'scripts/local_narration_context.py',
                 'scripts/narration_segments.py', 'scripts/whisper_narration.py',
                 'scripts/f5_russian_narration.py', 'scripts/chatterbox_czech_narration.py',
                 'scripts/chatterbox_portuguese_narration.py', 'design/narration/ming-female.json',
                 'design/narration/short-context.json')
        cls.protected = {path: retry.checksum(ROOT / path) for path in paths}

    @classmethod
    def tearDownClass(cls):
        actual = {path: retry.checksum(ROOT / path) for path in cls.protected}
        if actual != cls.protected:
            raise AssertionError('Frozen narration source/profile/policy changed')

    def setUp(self):
        output = ROOT / 'build/local-narration-retry-test'
        output.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.pipeline = retry.load_pipeline()
        self.pipeline.ROOT = self.folder
        self.pipeline.MEDIA_ROOT = self.folder / 'media'
        self.pipeline.VOICE = self.pipeline.MEDIA_ROOT / 'taichi/voice'
        self.pipeline.LOCALES = self.folder / 'text'
        self.pipeline.LOCALES.mkdir()
        self.pipeline.RECEIPT = self.folder / 'receipt.json'
        self.config = json.loads((ROOT / 'design/tai-chi/narration.json').read_text())
        self.config.pop('keys_file')
        self.config['keys'] = ['cue', 'untouched']
        self.config['_local_engine'] = True
        self.module = self.pipeline.LOCAL_PROVIDERS['ming']
        self.profile = self.module.descriptor(self.config)
        self.code = 'en'
        self.text = 'Keep your left arm relaxed, bend the knees, and turn left.'
        (self.pipeline.LOCALES / 'en.txt').write_text('[cue]\n' + self.text + '\n---\n[untouched]\nRest.\n---\n')
        self.cache = self.folder / 'cache'
        self.ledger = retry.Reservations(self.folder / 'retry.sqlite3')

    def plan(self, text=None):
        return retry.RequestPlan('ming', self.module, self.config, self.profile, self.cache,
                                 text or self.text, self.code)

    def generate(self, engine, block=None):
        plan = self.plan()
        block = block or self.ledger.reserve('key', plan)
        return retry.generate_retry(self.pipeline, self.config, self.code, 'cue', self.text,
                                     engine, plan, self.ledger, block)

    def events(self):
        with self.ledger.connection() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT events FROM blocks ORDER BY id')]

    def test_fresh_pcm_identity_and_seed_match_each_actual_adapter(self):
        for provider, code in (('ming', 'en'), ('f5-russian', 'ru'),
                               ('chatterbox-czech', 'cs'), ('chatterbox-portuguese', 'pt')):
            with self.subTest(provider=provider):
                module = self.pipeline.LOCAL_PROVIDERS[provider]
                profile = module.descriptor(self.config)
                plan = retry.RequestPlan(provider, module, self.config, profile, self.cache, 'Cue.', code)
                row = plan.candidate(4)
                if provider == 'ming':
                    expected = retry.ming.json_hash(dict(synthesis=module.provenance(profile), text='Cue.',
                        language=code, attempt=4, request_sha256=module.text_hash(self.config, 'Cue.', profile, code),
                        pcm_sample_rate=self.config['pcm_sample_rate']))
                    self.assertEqual(row['raw'][0]['seed'], retry.ming.segment_seed(profile, 4, 0))
                else:
                    expected = retry.local.json_hash(dict(request=retry.local.text_hash(
                        self.config, 'Cue.', profile, code), attempt=4))
                    self.assertEqual(row['seed'], profile['seed'] + 4)
                self.assertEqual(row['pcm'], expected)
                with self.assertRaises(ValueError):
                    plan.candidate(3)

    def test_restart_reserves_a_new_block_without_cache_or_recorded_events(self):
        first = self.ledger.reserve('key', self.plan())
        restarted = retry.Reservations(self.ledger.path)
        second = restarted.reserve('key', self.plan())
        self.assertEqual([row['attempt'] for row in first['candidates']], [4, 5, 6, 7])
        self.assertEqual([row['attempt'] for row in second['candidates']], [8, 9, 10, 11])
        self.assertFalse(set(self.plan().identities(first['candidates'][0])) &
                         set(self.plan().identities(second['candidates'][0])))

    def test_concurrent_connections_never_reserve_shared_requests_twice(self):
        def reserve(index):
            return retry.Reservations(self.ledger.path).reserve(str(index), self.plan())
        with ThreadPoolExecutor(max_workers=4) as executor:
            blocks = list(executor.map(reserve, range(8)))
        identities = [identity for block in blocks for row in block['candidates']
                      for identity in self.plan().identities(row)]
        self.assertEqual(len(identities), len(set(identities)))
        self.assertEqual(len({block['id'] for block in blocks}), 8)

    def test_shared_span_is_reserved_across_different_requests_and_keys(self):
        prefix = ' '.join('word' + str(index) for index in range(24)) + '. '
        first = self.ledger.reserve('first', self.plan(prefix + 'First ending.'))
        second = self.ledger.reserve('second', self.plan(prefix + 'Second ending.'))
        self.assertNotEqual(first['request_sha256'], second['request_sha256'])
        self.assertEqual(first['candidates'][0]['attempt'], 4)
        self.assertEqual(second['candidates'][0]['attempt'], 8)

    def test_partial_corrupt_and_symlink_cache_files_are_preserved_and_skipped(self):
        self.cache.mkdir()
        plan = self.plan()
        paths = [plan.paths(plan.candidate(4))[0], plan.paths(plan.candidate(8))[3],
                 plan.paths(plan.candidate(12))[-1]]
        for path in paths:
            path.write_bytes(b'preserve corrupt or incomplete data')
        broken = plan.paths(plan.candidate(16))[0]
        broken.symlink_to(self.cache / 'missing')
        before = {path: (retry.checksum(path), path.stat().st_mtime_ns) for path in paths}
        block = self.ledger.reserve('key', plan)
        self.assertEqual(block['candidates'][0]['attempt'], 20)
        self.assertEqual(before, {path: (retry.checksum(path), path.stat().st_mtime_ns) for path in paths})
        self.assertTrue(broken.is_symlink())

    def test_real_encoding_and_current_accept_reserved_seed_and_truthful_metadata(self):
        engine = FakeEngine(self)
        row = self.generate(engine)
        self.assertEqual(engine.calls, [4])
        self.assertEqual(row['segmentation']['attempt'], 4)
        self.assertEqual(row['retry']['attempts'][0]['raw'], self.plan().candidate(4)['raw'])
        self.assertEqual(row['retry']['attempts'][0]['status'], 'accepted')
        self.assertEqual(row['synthesis'], self.module.provenance(self.profile))
        self.assertEqual(row['text_sha256'], self.module.text_hash(self.config, self.text, self.profile, 'en'))
        self.assertTrue(self.pipeline.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', self.text))
        self.assertEqual(self.pipeline.ATTEMPTS, 4)

    def test_four_speaker_failures_never_publish_audio_or_receipt(self):
        engine = FakeEngine(self, speaker=0.0)
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])
        self.assertFalse(self.pipeline.clip_path('en', 'cue').exists())
        self.assertFalse(self.pipeline.RECEIPT.exists())
        self.assertEqual(len(self.events()[0]), 4)

    def test_four_duration_failures_keep_the_existing_floor(self):
        engine = FakeEngine(self, duration=0.2)
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])
        self.assertFalse(self.pipeline.clip_path('en', 'cue').exists())

    def test_wrong_direction_is_rejected_by_original_gates(self):
        engine = FakeEngine(self, transcript=self.text.replace('left', 'right'))
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])

    def test_missing_ending_is_rejected_even_when_whole_text_score_would_pass(self):
        self.text = ('Settle comfortably and breathe naturally as you attend to the feeling in your hands. ' * 5
                     + 'Then turn left.')
        heard = self.text[:-15]
        self.assertGreater(self.pipeline.match(self.text, heard), self.config['minimum_match'])
        engine = FakeEngine(self, transcript=heard)
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])

    def test_raw_peak_rejection_uses_next_draw_without_clipping_or_deletion(self):
        engine = FakeEngine(self, errors=['raw_peak'])
        row = self.generate(engine)
        self.assertEqual(engine.calls, [4, 5])
        part = self.plan().candidate(4)['raw'][0]
        raw = self.cache / (part['identity'] + '.wav')
        evidence = json.loads((self.cache / (part['identity'] + '.raw.json')).read_text())
        self.assertEqual(retry.checksum(raw), evidence['raw_sha256'])
        self.assertEqual(evidence['gain'], 1.0)
        self.assertEqual(struct.unpack('<4f', raw.read_bytes()[-16:])[1], 1.125)
        self.assertEqual(row['attempts'], 2)
        self.assertEqual([event['status'] for event in row['retry']['attempts']],
                         ['raw_peak_rejected', 'accepted'])

    def test_four_raw_peaks_exhaust_only_four_draws_and_preserve_all_raws(self):
        engine = FakeEngine(self, errors=['raw_peak'] * 4)
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])
        self.assertEqual(len(list(self.cache.glob('*.wav'))), 4)
        self.assertFalse(self.pipeline.clip_path('en', 'cue').exists())

    def test_raw_peak_followed_by_quality_failures_cannot_reset_budget(self):
        engine = FakeEngine(self, speaker=0.0, errors=['raw_peak'])
        with self.assertRaises(retry.RetryRejected):
            self.generate(engine)
        self.assertEqual(engine.calls, [4, 5, 6, 7])

    def test_integrity_model_and_io_failures_are_fatal_without_second_draw(self):
        errors = [ValueError('Changed model artifact'), OSError('PCM write failed'),
                  RuntimeError('Model failed'), RuntimeError('Ming returned invalid waveform: {}'),
                  RuntimeError('Ming finite waveform peak exceeds PCM range: {}')]
        for error in errors:
            with self.subTest(error=str(error)):
                engine = FakeEngine(self, errors=[error])
                with self.assertRaises((type(error), ValueError)) as caught:
                    self.generate(engine)
                self.assertNotIsInstance(caught.exception, retry.RetryRejected)
                self.assertEqual(len(engine.calls), 1)

    def test_changed_request_and_occupied_reserved_path_stop_before_engine(self):
        plan = self.plan()
        block = self.ledger.reserve('key', plan)
        engine = FakeEngine(self)
        proxy = retry.RetryEngine(engine, plan, self.ledger, block)
        with self.assertRaises(ValueError):
            proxy.speak(self.config, 'Changed text.', 'en', self.folder, 0)
        self.cache.mkdir()
        plan.paths(block['candidates'][0])[0].write_bytes(b'other writer')
        with self.assertRaisesRegex(RuntimeError, 'became occupied'):
            proxy.speak(self.config, self.text, 'en', self.folder, 0)
        self.assertEqual(engine.calls, [])

    def test_existing_accepted_row_is_skipped_without_loading_any_model(self):
        row = self.generate(FakeEngine(self))
        receipt = {'clips': {'en/cue': row, 'de/untouched': {'preserve': True}}}
        self.pipeline.save(receipt)
        audio = self.pipeline.clip_path('en', 'cue')
        before = (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), copy.deepcopy(row))
        def forbidden():
            raise AssertionError('Accepted recording must not load a model')
        result = retry.run_selected(self.pipeline, self.config, 'en', ['cue'], receipt,
            'ming', self.module, self.profile, self.cache, self.ledger, forbidden, self.folder / 'originals')
        self.assertEqual(result, dict(accepted=[], failed=[], skipped=['cue']))
        self.assertEqual(before, (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), row))

    def test_selected_repair_preserves_original_audio_row_and_unselected_receipt(self):
        audio = self.pipeline.clip_path('en', 'cue')
        audio.parent.mkdir(parents=True)
        original = b'old recording preserved even if obsolete'
        audio.write_bytes(original)
        old_row = {'sha256': retry.checksum(audio), 'old': True}
        receipt = {'clips': {'en/cue': old_row, 'de/untouched': {'preserve': True}}}
        archive = self.folder / 'originals'
        result = retry.run_selected(self.pipeline, self.config, 'en', ['cue'], receipt,
            'ming', self.module, self.profile, self.cache, self.ledger,
            lambda: FakeEngine(self), archive)
        self.assertEqual(result['accepted'], ['en/cue'])
        self.assertEqual(receipt['clips']['de/untouched'], {'preserve': True})
        self.assertEqual((archive / (old_row['sha256'] + '.ogg')).read_bytes(), original)
        self.assertIn(old_row, [json.loads(path.read_text()) for path in archive.glob('*.json')])
        self.assertTrue(self.pipeline.current(receipt, self.config, 'en', 'cue', self.text))

    def test_same_voice_lock_matches_original_writer_and_releases(self):
        name = self.pipeline.digest(str(self.pipeline.VOICE.resolve()).encode())[:20]
        with retry.generation_lock(self.folder, self.pipeline.VOICE):
            self.assertTrue((self.folder / 'backup/narration' / (name + '.lock')).exists())
            with self.assertRaises(BlockingIOError):
                with retry.generation_lock(self.folder, self.pipeline.VOICE):
                    self.fail('Concurrent writer acquired the same root')
        with retry.generation_lock(self.folder, self.pipeline.VOICE):
            pass


    def test_all_base_providers_cap_uncached_new_sources_at_four_fresh_draws(self):
        for provider, code in (('f5-russian', 'ru'), ('chatterbox-czech', 'cs'),
                               ('chatterbox-portuguese', 'pt')):
            with self.subTest(provider=provider):
                module = self.pipeline.LOCAL_PROVIDERS[provider]
                profile = module.descriptor(self.config)
                text = 'New source without ordinary cached attempts.'
                plan = retry.RequestPlan(provider, module, self.config, profile, self.cache, text, code)
                block = self.ledger.reserve(provider, plan)
                class Boundary:
                    def __init__(inner):
                        inner.profile = profile
                        inner.calls = []
                    def speak(inner, config, source, locale, work, attempt):
                        inner.calls.append(attempt)
                        return b'fixture PCM boundary', module.provenance(profile)
                engine = Boundary()
                proxy = retry.RetryEngine(engine, plan, self.ledger, block)
                for index in range(4):
                    proxy.speak(self.config, text, code, self.folder, index)
                with self.assertRaises(retry.DrawBudgetExhausted):
                    proxy.speak(self.config, text, code, self.folder, 0)
                self.assertEqual(engine.calls, [4, 5, 6, 7])
                self.assertEqual([row['seed'] for row in proxy.events],
                                 [profile['seed'] + index for index in (4, 5, 6, 7)])

    def test_context_plan_reserves_actual_parent_input_with_the_same_four_draw_budget(self):
        config = json.loads((ROOT / 'design/sun-salutation/narration/narration.json').read_text())
        config['_context_profile'] = str(ROOT / 'design/narration/short-context-provider-v4.json')
        config['_context_voice_directory'] = 'sunsalutation/voice'
        code, text = 'pt', 'Solte o ar.'
        actual = retry.effective_text(config, code, text)
        self.assertNotEqual(actual, text)
        import local_narration_context as context
        self.assertEqual(context.words(actual)[:len(context.words(text))], context.words(text))
        module = self.pipeline.LOCAL_PROVIDERS['chatterbox-portuguese']
        profile = module.descriptor(config)
        plan = retry.RequestPlan('chatterbox-portuguese', module, config, profile, self.cache, actual, code)
        block = self.ledger.reserve('new-context-parent', plan)
        class Boundary:
            def __init__(inner):
                inner.profile = profile
                inner.calls = []
            def speak(inner, cfg, source, locale, work, attempt):
                inner.calls.append((source, locale, attempt))
                return b'fixture parent boundary', module.provenance(profile)
        engine = Boundary()
        proxy = retry.RetryEngine(engine, plan, self.ledger, block)
        for index in range(4):
            proxy.speak(config, text, code, self.folder, index)
        with self.assertRaises(retry.DrawBudgetExhausted):
            proxy.speak(config, text, code, self.folder, 0)
        self.assertEqual(engine.calls, [(text, code, index) for index in (4, 5, 6, 7)])
        self.assertEqual(plan.request, module.text_hash(config, actual, profile, code))


    def test_failed_selected_repair_leaves_original_recording_and_receipt_intact(self):
        audio = self.pipeline.clip_path('en', 'cue')
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b'preserved original audio')
        receipt = {'clips': {'en/cue': {'old': True}, 'de/untouched': {'preserve': True}}}
        self.pipeline.save(receipt)
        before = (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), copy.deepcopy(receipt))
        result = retry.run_selected(self.pipeline, self.config, 'en', ['cue'], receipt,
            'ming', self.module, self.profile, self.cache, self.ledger,
            lambda: FakeEngine(self, speaker=0.0), self.folder / 'originals')
        self.assertEqual(result['failed'], ['en/cue'])
        self.assertEqual(before, (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), receipt))

    def test_changed_raw_peak_evidence_is_fatal_and_never_reused(self):
        engine = FakeEngine(self, errors=['raw_peak'])
        plan = self.plan()
        candidate = plan.candidate(4)
        with self.assertRaises(RuntimeError) as caught:
            engine.speak(self.config, self.text, 'en', self.folder, 4)
        raw = self.cache / (candidate['raw'][0]['identity'] + '.wav')
        raw.write_bytes(raw.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed Ming raw-peak evidence'):
            retry.raw_peak(caught.exception, plan, candidate)
        self.assertEqual(engine.calls, [4])


    def publication_fixture(self):
        audio = self.pipeline.clip_path('en', 'cue')
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b'original accepted recording')
        receipt = {'clips': {'en/cue': {'original': True}, 'de/untouched': {'preserve': True}}}
        self.pipeline.save(receipt)
        before = (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), copy.deepcopy(receipt))
        return audio, receipt, before

    def run_publication_failure(self, engine, receipt):
        return retry.run_selected(self.pipeline, self.config, 'en', ['cue'], receipt,
            'ming', self.module, self.profile, self.cache, self.ledger,
            lambda: engine, self.folder / 'originals')

    def assert_publication_restored(self, audio, receipt, before, engine):
        self.assertEqual(before, (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), receipt))
        self.assertEqual(engine.calls, [4])
        self.assertEqual(self.events()[0][-1]['publication'], 'rolled_back')
        next_block = self.ledger.reserve('restart-after-fatal', self.plan())
        self.assertEqual(next_block['candidates'][0]['attempt'], 8)

    def test_current_rejection_after_real_publication_restores_original_pair(self):
        audio, receipt, before = self.publication_fixture()
        class InvalidMetadata(FakeEngine):
            def transcribe(inner, clip, code):
                text = super().transcribe(clip, code)
                inner.last_transcription['truncation'] = True
                return text
        engine = InvalidMetadata(self)
        with self.assertRaisesRegex(RuntimeError, 'ordinary current gate'):
            self.run_publication_failure(engine, receipt)
        self.assert_publication_restored(audio, receipt, before, engine)

    def test_source_drift_after_real_publication_restores_original_pair(self):
        audio, receipt, before = self.publication_fixture()
        class SourceChanged(FakeEngine):
            def transcribe(inner, clip, code):
                text = super().transcribe(clip, code)
                (self.pipeline.LOCALES / 'en.txt').write_text('[cue]\nChanged source.\n---\n')
                return text
        engine = SourceChanged(self)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.run_publication_failure(engine, receipt)
        self.assert_publication_restored(audio, receipt, before, engine)
        self.assertIn('Changed source.', (self.pipeline.LOCALES / 'en.txt').read_text())

    def test_receipt_write_failure_restores_original_pair_without_deleting_failed_part(self):
        audio, receipt, before = self.publication_fixture()
        blocked = self.pipeline.RECEIPT.with_suffix('.json.part')
        blocked.mkdir()
        engine = FakeEngine(self)
        with self.assertRaises(IsADirectoryError):
            self.run_publication_failure(engine, receipt)
        self.assert_publication_restored(audio, receipt, before, engine)
        self.assertTrue(blocked.is_dir())

    def test_receipt_failure_after_atomic_replace_restores_original_pair(self):
        audio, receipt, before = self.publication_fixture()
        class FailedSavePath(type(Path())):
            def replace(path, target):
                result = super().replace(target)
                if path.name.endswith('.json.part'):
                    raise OSError('Fixture receipt error after real replace')
                return result
        self.pipeline.RECEIPT = FailedSavePath(self.pipeline.RECEIPT)
        engine = FakeEngine(self)
        with self.assertRaisesRegex(OSError, 'after real replace'):
            self.run_publication_failure(engine, receipt)
        self.assert_publication_restored(audio, receipt, before, engine)

    def test_post_save_external_audio_change_is_preserved_and_reported(self):
        audio, receipt, before = self.publication_fixture()
        external = b'owner changed canonical audio'
        class ExternalSavePath(type(Path())):
            def replace(path, target):
                result = super().replace(target)
                if path.name.endswith('.json.part'):
                    audio.write_bytes(external)
                    raise OSError('Fixture external change after save')
                return result
        self.pipeline.RECEIPT = ExternalSavePath(self.pipeline.RECEIPT)
        engine = FakeEngine(self)
        with self.assertRaisesRegex(RuntimeError, 'Unexpected external audio change'):
            self.run_publication_failure(engine, receipt)
        self.assertEqual(audio.read_bytes(), external)
        self.assertEqual(receipt, before[2])
        self.assertEqual(engine.calls, [4])
        self.assertIn(before[0], [path.read_bytes() for path in (self.folder / 'originals').glob('*.ogg')])


    def test_post_publication_failure_removes_only_own_new_recording_when_no_original_exists(self):
        class InvalidMetadata(FakeEngine):
            def transcribe(inner, clip, code):
                text = super().transcribe(clip, code)
                inner.last_transcription['truncation'] = True
                return text
        receipt = {'clips': {'de/untouched': {'preserve': True}}}
        engine = InvalidMetadata(self)
        with self.assertRaisesRegex(RuntimeError, 'ordinary current gate'):
            self.run_publication_failure(engine, receipt)
        self.assertFalse(self.pipeline.clip_path('en', 'cue').exists())
        self.assertFalse(self.pipeline.RECEIPT.exists())
        self.assertEqual(receipt, {'clips': {'de/untouched': {'preserve': True}}})
        self.assertEqual(engine.calls, [4])
        self.assertEqual(self.events()[0][-1]['publication'], 'rolled_back')

    def test_post_save_external_receipt_change_is_preserved_and_reported(self):
        audio, receipt, before = self.publication_fixture()
        external = b'owner changed canonical receipt'
        class ExternalSavePath(type(Path())):
            def replace(path, target):
                result = super().replace(target)
                if path.name.endswith('.json.part'):
                    Path(target).write_bytes(external)
                    raise OSError('Fixture external receipt change after save')
                return result
        self.pipeline.RECEIPT = ExternalSavePath(self.pipeline.RECEIPT)
        engine = FakeEngine(self)
        with self.assertRaisesRegex(RuntimeError, 'Unexpected external receipt change'):
            self.run_publication_failure(engine, receipt)
        self.assertEqual(self.pipeline.RECEIPT.read_bytes(), external)
        self.assertEqual(receipt, before[2])
        self.assertEqual(engine.calls, [4])
        self.assertIn(before[0], [path.read_bytes() for path in (self.folder / 'originals').glob('*.ogg')])

    def exact_fixture(self, receipt=None, mutate=None, terminal_mutate=None, diagnostic_mutate=None):
        receipt = receipt if receipt is not None else {'clips': {}}
        plan = retry.ExactRequestPlan('ming', self.module, self.config, self.profile,
                                      self.cache, self.text, 'en')
        config_file = self.folder / 'config.json'
        config_file.write_text(json.dumps(self.config))
        binding = retry.manifest_binding(self.pipeline, self.config, 'taichi', 'ming', 'en',
                                        self.module, self.profile, self.cache, config_file)
        def file(path):
            return dict(path=str(path), sha256=retry.checksum(path))
        consumed = []
        self.cache.mkdir(exist_ok=True)
        for attempt in (0, 1):
            for path in plan.paths(plan._candidate(attempt)):
                if not path.name.endswith('.part'):
                    path.write_bytes(('consumed fixture ' + path.name).encode())
                    consumed.append(file(path))
        diagnostic = self.folder / 'diagnostics/cue/attempts.json'
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        previous = dict(locale='en', key='cue', text_sha256=retry.hashlib.sha256(self.text.encode()).hexdigest(),
            attempts=[dict(attempt=0, reasons=['speaker']), dict(attempt=1, reasons=['error'],
                error='ValueError: last page does not end the stream')])
        if diagnostic_mutate:
            diagnostic_mutate(previous)
        diagnostic.write_text(json.dumps(previous))
        terminal = dict(id='completed-fixture', done=True, status='finished', code=1,
            output=json.dumps(dict(child_exit_code=1, auto_retry=False, reported_subprocess_signal=None)))
        if terminal_mutate:
            terminal_mutate(terminal)
        terminal_file = self.folder / 'terminal.json'
        terminal_file.write_text(json.dumps(terminal))
        clip = self.pipeline.clip_path('en', 'cue')
        old = receipt['clips'].get('en/cue')
        entry = dict(key='cue', text=self.text, request_sha256=plan.request,
            candidates=[plan.candidate(index) for index in (2, 3)], diagnostic=file(diagnostic),
            consumed_cache_files=consumed, previous_row_sha256=retry.local.json_hash(old) if old is not None else None,
            previous_audio_sha256=retry.checksum(clip) if clip.exists() else None)
        manifest = dict(version=retry.EXACT_VERSION, binding=binding,
            config_sha256=retry.checksum(config_file), source_sha256=retry.checksum(Path(binding['source_file'])),
            completion=dict(file(terminal_file), command_id='completed-fixture'), entries=[entry])
        if mutate:
            mutate(manifest)
        path = self.folder / 'exact.json'
        path.write_text(json.dumps(manifest))
        return retry.ExactManifest(path, binding, root=self.folder), plan

    def run_exact(self, manifest, engine, receipt=None, factory=None):
        return retry.run_selected(self.pipeline, self.config, 'en', ['cue'],
            receipt if receipt is not None else {'clips': {}}, 'ming', self.module, self.profile,
            self.cache, self.ledger, factory or (lambda: engine), self.folder / 'originals',
            exact_manifest=manifest)

    def test_exact_unused_attempts_preserve_true_attempt_seed_and_current(self):
        manifest, plan = self.exact_fixture()
        class SecondDraw(FakeEngine):
            def speaker_match(inner, clip):
                return 0.0 if len(inner.calls) == 1 else 0.95
        engine = SecondDraw(self)
        result = self.run_exact(manifest, engine)
        self.assertEqual(result['accepted'], ['en/cue'])
        self.assertEqual(engine.calls, [2, 3])
        row = json.loads(self.pipeline.RECEIPT.read_text())['clips']['en/cue']
        self.assertEqual(row['retry']['source_attempt'], 3)
        self.assertEqual(row['segmentation']['attempt'], 3)
        self.assertEqual(row['segmentation']['chunks'], plan.candidate(3)['raw'])
        self.assertEqual(row['retry']['manifest_sha256'], manifest.sha256)
        self.assertTrue(self.pipeline.current({'clips': {'en/cue': row}}, self.config, 'en', 'cue', self.text))

    def test_exact_budget_stops_at_two_and_preserves_original_pair(self):
        audio, receipt, before = self.publication_fixture()
        manifest, plan = self.exact_fixture(receipt)
        engine = FakeEngine(self, speaker=0.0)
        result = self.run_exact(manifest, engine, receipt)
        self.assertEqual(result['failed'], ['en/cue'])
        self.assertEqual(engine.calls, [2, 3])
        self.assertEqual(before, (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), receipt))
        self.assertEqual([row['attempt'] for row in self.events()[0]], [2, 3])

    def test_exact_success_preserves_unrelated_rows_audio_and_consumed_caches(self):
        audio, receipt, before = self.publication_fixture()
        manifest, plan = self.exact_fixture(receipt)
        untouched = audio.with_name('untouched.ogg')
        untouched.write_bytes(b'keep unrelated sound')
        consumed = {path: retry.checksum(path) for row in (plan._candidate(0), plan._candidate(1))
                    for path in plan.paths(row) if path.is_file()}
        self.run_exact(manifest, FakeEngine(self), receipt)
        self.assertEqual(receipt['clips']['de/untouched'], before[2]['clips']['de/untouched'])
        self.assertEqual(untouched.read_bytes(), b'keep unrelated sound')
        self.assertEqual(consumed, {path: retry.checksum(path) for path in consumed})
        self.assertIn(before[0], [path.read_bytes() for path in (self.folder / 'originals').glob('*.ogg')])

    def assert_exact_refused(self, manifest, receipt=None, keys=None):
        def forbidden():
            self.fail('Refused exact request created an engine')
        with self.assertRaises((ValueError, FileNotFoundError, SystemExit)):
            retry.run_selected(self.pipeline, self.config, 'en', keys or ['cue'],
                receipt if receipt is not None else {'clips': {}}, 'ming', self.module,
                self.profile, self.cache, self.ledger, forbidden, self.folder / 'originals',
                exact_manifest=manifest)
        with self.ledger.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 0)

    def test_exact_invalid_or_duplicate_candidates_never_create_an_engine(self):
        mutations = [
            lambda row: row['candidates'].__setitem__(0, row['candidates'][1]),
            lambda row: row['candidates'][0].update(attempt=0),
            lambda row: row['candidates'][0].update(attempt=1),
            lambda row: row['candidates'][1].update(attempt=4),
            lambda row: row['candidates'][0].update(attempt=2.0),
            lambda row: row['candidates'][0].update(attempt=True),
            lambda row: row['candidates'][0].update(pcm='wrong'),
            lambda row: row['candidates'][0]['raw'][0].update(seed=0),
            lambda row: row.update(request_sha256='wrong'),
            lambda row: row.update(text='Unreviewed source.'),
            lambda row: row.update(key=['cue']),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                manifest, _ = self.exact_fixture(mutate=lambda data: mutate(data['entries'][0]))
                self.assert_exact_refused(manifest)
        manifest, _ = self.exact_fixture(mutate=lambda data: data['entries'].append(copy.deepcopy(data['entries'][0])))
        self.assert_exact_refused(manifest)
        manifest, _ = self.exact_fixture()
        self.assert_exact_refused(manifest, keys=['cue', 'cue'])
        self.assert_exact_refused(manifest, keys=['missing'])
        for attempt in (-1, 0, 1, 4, True, 2.0):
            with self.assertRaises(ValueError):
                retry.ExactRequestPlan('ming', self.module, self.config, self.profile,
                    self.cache, self.text, 'en').candidate(attempt)

    def test_exact_occupied_final_partial_and_broken_link_refuse_without_skipping(self):
        manifest, plan = self.exact_fixture()
        for candidate in (plan.candidate(2), plan.candidate(3)):
            for path in plan.paths(candidate):
                with self.subTest(path=path.name):
                    path.write_bytes(b'prior or partial outcome')
                    self.assert_exact_refused(manifest)
                    path.unlink()
        path = self.cache / (plan.candidate(2)['pcm'] + '.pcm')
        path.symlink_to(self.folder / 'missing')
        self.assert_exact_refused(manifest)
        path.unlink()

    def test_exact_completed_command_requires_unambiguous_original_outcome(self):
        mutations = [lambda row: row.update(done=False), lambda row: row.update(status='running'),
            lambda row: row.update(code=143), lambda row: row.update(code=True),
            lambda row: row.update(id='other-command'), lambda row: row.update(output=''),
            lambda row: row.update(output=json.dumps(dict(child_exit_code=1, auto_retry=True,
                                                          reported_subprocess_signal=None))),
            lambda row: row.update(output=json.dumps(dict(child_exit_code=1, auto_retry=False))),
            lambda row: row.update(output=json.dumps(dict(child_exit_code=143, auto_retry=False,
                                                          reported_subprocess_signal=15))),
            lambda row: row.update(output=row['output'] + chr(10) + row['output'])]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(ValueError):
                self.exact_fixture(terminal_mutate=mutate)

    def test_exact_ambiguous_prior_attempts_and_consumed_partial_are_refused(self):
        mutations = [lambda row: row['attempts'][0].update(attempt=1),
            lambda row: row['attempts'][1].update(attempt=2),
            lambda row: row['attempts'][0].update(attempt=False),
            lambda row: row['attempts'][0].update(reasons=['error']),
            lambda row: row['attempts'][1].update(error='Unknown model outcome'),
            lambda row: row['attempts'].append(dict(attempt=2, reasons=['speaker'])),
            lambda row: row.update(locale='pt'), lambda row: row.update(text_sha256='changed')]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                manifest, _ = self.exact_fixture(diagnostic_mutate=mutate)
                self.assert_exact_refused(manifest)
        manifest, plan = self.exact_fixture()
        extra = self.folder / 'diagnostics/cue/unknown-run.json'
        extra.write_text('{}')
        self.assert_exact_refused(manifest)
        extra.unlink()
        partial = self.cache / (plan._candidate(1)['pcm'] + '.pcm.part')
        partial.write_bytes(b'uncertain')
        self.assert_exact_refused(manifest)

    def test_exact_bound_evidence_source_profile_and_previous_pair_cannot_change(self):
        audio, receipt, before = self.publication_fixture()
        manifest, plan = self.exact_fixture(receipt)
        for path in [manifest.path] + [path for path, _ in manifest.files] + [
                Path(manifest.data['entries'][0]['diagnostic']['path']),
                Path(manifest.data['entries'][0]['consumed_cache_files'][0]['path'])]:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                self.assert_exact_refused(manifest, receipt)
                path.write_bytes(original)
        audio.write_bytes(b'changed selected audio')
        self.assert_exact_refused(manifest, receipt)
        audio.write_bytes(before[0])
        receipt['clips']['en/cue'] = dict(changed=True)
        self.assert_exact_refused(manifest, receipt)
        receipt['clips']['en/cue'] = before[2]['clips']['en/cue']
        original_voice = self.pipeline.VOICE
        self.pipeline.VOICE = self.folder / 'different-voice'
        self.assert_exact_refused(manifest, receipt)
        self.pipeline.VOICE = original_voice
        self.profile = dict(self.profile, seed=self.profile['seed'] + 1)
        self.assert_exact_refused(manifest, receipt)

    def test_exact_missing_or_duplicate_consumed_cache_evidence_refuses(self):
        for mutate in (lambda row: row['consumed_cache_files'].pop(),
                       lambda row: row['consumed_cache_files'].append(row['consumed_cache_files'][0])):
            manifest, _ = self.exact_fixture(mutate=lambda data: mutate(data['entries'][0]))
            self.assert_exact_refused(manifest)

    def test_exact_claims_survive_restart_with_unknown_or_started_outcome(self):
        for status in (None, 'started'):
            with self.subTest(status=status):
                manifest, plan = self.exact_fixture()
                ledger = retry.Reservations(self.folder / ('claims-' + str(status) + '.sqlite3'))
                block = ledger.reserve_exact([('cue', 'original-owner', plan)], manifest.sha256)['cue']
                if status:
                    ledger.record(block, [dict(plan.candidate(2), status=status)])
                restarted = retry.Reservations(ledger.path)
                with self.assertRaisesRegex(ValueError, 'refusing replay'):
                    restarted.reserve_exact([('cue', 'different-owner', plan)], manifest.sha256)
                with self.assertRaisesRegex(ValueError, 'refusing replay'):
                    restarted.reserve_exact([('cue', 'original-owner', plan)], manifest.sha256)
                with restarted.connection() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 1)
                    self.assertEqual(json.loads(db.execute('SELECT body FROM blocks').fetchone()[0])['candidates'],
                                     [plan.candidate(2), plan.candidate(3)])

    def test_exact_atomic_reservation_rolls_back_duplicate_and_cross_request_collision(self):
        manifest, plan = self.exact_fixture()
        for requests in ([], [('cue', 'owner', self.plan())],
                [('cue', 'one', plan), ('cue', 'two', plan)],
                [('cue', 'one', plan), ('other-key', 'two', plan)]):
            with self.subTest(requests=len(requests)), self.assertRaises(ValueError):
                self.ledger.reserve_exact(requests, manifest.sha256)
            with self.ledger.connection() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM claims').fetchone()[0], 0)

    def test_exact_claim_collision_blocks_all_keys_before_engine_creation(self):
        manifest, plan = self.exact_fixture()
        self.ledger.reserve_exact([('cue', 'other-owner', plan)], manifest.sha256)
        def forbidden():
            self.fail('Previously claimed request created an engine')
        with self.assertRaisesRegex(ValueError, 'refusing replay'):
            self.run_exact(manifest, None, factory=forbidden)
        with self.ledger.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 1)

    def test_exact_two_raw_peak_failures_never_make_a_third_draw(self):
        manifest, _ = self.exact_fixture()
        engine = FakeEngine(self, errors=['raw_peak', 'raw_peak'])
        self.assertEqual(self.run_exact(manifest, engine)['failed'], ['en/cue'])
        self.assertEqual(engine.calls, [2, 3])
        self.assertEqual([row['status'] for row in self.events()[0]], ['raw_peak_rejected'] * 2)

    def test_exact_post_publication_failure_restores_pair_and_keeps_claims(self):
        audio, receipt, before = self.publication_fixture()
        manifest, _ = self.exact_fixture(receipt)
        class InvalidMetadata(FakeEngine):
            def transcribe(inner, clip, code):
                text = super().transcribe(clip, code)
                inner.last_transcription['truncation'] = True
                return text
        engine = InvalidMetadata(self)
        with self.assertRaisesRegex(RuntimeError, 'ordinary current gate'):
            self.run_exact(manifest, engine, receipt)
        self.assertEqual(before, (audio.read_bytes(), self.pipeline.RECEIPT.read_bytes(), receipt))
        self.assertEqual(engine.calls, [2])
        self.assertEqual(self.events()[0][-1]['publication'], 'rolled_back')
        with self.assertRaisesRegex(ValueError, 'refusing replay'):
            self.run_exact(manifest, None, receipt, factory=lambda: self.fail('Replay created an engine'))

    def test_exact_concurrent_connections_allow_only_one_claimant(self):
        manifest, plan = self.exact_fixture()
        def reserve(index):
            try:
                return retry.Reservations(self.ledger.path).reserve_exact(
                    [('cue', str(index), plan)], manifest.sha256)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(reserve, range(4)))
        self.assertEqual(sum(result is not None for result in results), 1)
        with self.ledger.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 1)

    def test_exact_last_key_collision_leaves_no_partial_reservations(self):
        manifest, first = self.exact_fixture()
        plans = [first] + [retry.ExactRequestPlan('ming', self.module, self.config,
            self.profile, self.cache, self.text + suffix, 'en') for suffix in (' Again.', ' Rest.')]
        occupied = self.cache / (plans[-1].candidate(3)['pcm'] + '.json.part')
        occupied.write_bytes(b'uncertain third key')
        requests = [(str(index), str(index), plan) for index, plan in enumerate(plans)]
        with self.assertRaisesRegex(ValueError, 'refusing replay'):
            self.ledger.reserve_exact(requests, manifest.sha256)
        with self.ledger.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM claims').fetchone()[0], 0)
        occupied.unlink()
        blocks = self.ledger.reserve_exact(requests, manifest.sha256)
        self.assertEqual(set(blocks), {'0', '1', '2'})

    def test_exact_portuguese_receipt_keeps_original_attempt_and_seed(self):
        self.module = self.pipeline.LOCAL_PROVIDERS['chatterbox-portuguese']
        self.profile = self.module.descriptor(self.config)
        self.text = 'Abdominais. Comece.'
        self.pipeline.LOCALES.joinpath('pt.txt').write_text('[cue]' + chr(10) + self.text + chr(10) + '---' + chr(10))
        class Portuguese(FakeEngine):
            def speak(inner, config, text, code, work, attempt):
                inner.calls.append(attempt)
                pcm = array('h', (int(5000 * math.sin(2 * math.pi * 220 * index / 24000))
                                  for index in range(24000))).tobytes()
                return pcm, self.module.provenance(self.profile)
        engine = Portuguese(self)
        plan = retry.ExactRequestPlan('chatterbox-portuguese', self.module, self.config,
                                      self.profile, self.cache, self.text, 'pt')
        block = self.ledger.reserve_exact([('cue', 'pt-owner', plan)], 'fixture-manifest')['cue']
        row = retry.generate_retry(self.pipeline, self.config, 'pt', 'cue', self.text,
                                   engine, plan, self.ledger, block)
        self.assertEqual(engine.calls, [2])
        self.assertEqual(row['retry']['source_attempt'], 2)
        self.assertEqual(row['retry']['source_seed'], self.profile['seed'] + 2)
        self.assertEqual(row['retry']['attempts'][0]['seed'], self.profile['seed'] + 2)
        self.assertTrue(self.pipeline.current({'clips': {'pt/cue': row}}, self.config, 'pt', 'cue', self.text))

    def test_exact_engine_initialization_cannot_replace_changed_selected_pair(self):
        audio, receipt, before = self.publication_fixture()
        manifest, _ = self.exact_fixture(receipt)
        engine = FakeEngine(self)
        external = b'external recording after engine initialization'
        def factory():
            audio.write_bytes(external)
            return engine
        with self.assertRaisesRegex(ValueError, 'Previously selected'):
            self.run_exact(manifest, engine, receipt, factory=factory)
        self.assertEqual(engine.calls, [])
        self.assertEqual(audio.read_bytes(), external)
        self.assertEqual(self.pipeline.RECEIPT.read_bytes(), before[1])
        self.assertEqual(receipt, before[2])
        self.assertFalse((self.folder / 'originals').exists())

    def test_exact_disk_receipt_drift_is_refused_without_overwriting_it(self):
        audio, receipt, before = self.publication_fixture()
        manifest, _ = self.exact_fixture(receipt)
        for key in ('en/cue', 'de/untouched'):
            changed = copy.deepcopy(receipt)
            changed['clips'][key] = dict(external=True)
            self.pipeline.save(changed)
            disk = self.pipeline.RECEIPT.read_bytes()
            self.assert_exact_refused(manifest, receipt)
            self.assertEqual(audio.read_bytes(), before[0])
            self.assertEqual(self.pipeline.RECEIPT.read_bytes(), disk)

    def test_unknown_database_schema_is_fatal(self):
        with self.ledger.connection() as db:
            db.execute('PRAGMA user_version=99')
        with self.assertRaises(ValueError):
            retry.Reservations(self.ledger.path)


class PortuguesePolicyTests(unittest.TestCase):
    policy = ROOT / 'design/narration/workout-portuguese-context-v1.json'
    expected = {
        'workout_say_push_up_rotation': ('Flexão com rotação. Comece.',
            'Flexão com rotação. Comece. Mantenha o movimento controlado.'),
        'workout_say_switch': ('Troque de lado.', 'Troque de lado. Continue o exercício com calma.'),
        'workout_say_count_3': ('Três.', 'Três. Prepare o corpo para o próximo exercício.'),
        'workout_say_count_2': ('Dois.', 'Dois. Prepare o corpo para o próximo exercício.'),
        'workout_say_count_1': ('Um.', 'Um. Prepare o corpo para o próximo exercício.'),
        'workout_say_go': ('Já!', 'Já! Comece o exercício e mantenha o ritmo.'),
    }

    def test_exact_policy_scope_and_source(self):
        import local_narration_context as context
        policy = json.loads(self.policy.read_text())
        self.assertEqual(set(policy), {'version', 'voice_directory', 'asr_model', 'asr_revision',
            'asr_artifacts', 'helper_sha256', 'verifier_sha256', 'rules'})
        self.assertEqual(policy['voice_directory'], 'workout/voice')
        self.assertEqual(policy['verifier_sha256'],
            'a89de167b6f76b428437c22116a0647dd85a3cdb6e8ac58c01e1af5d754fa02f')
        self.assertEqual(policy['helper_sha256'],
            'fcf1d55218627c04fbe787d1b66987d4f7f34e7261822f02e8cc8b2beef47c1f')
        baseline = context.load_policy(ROOT / 'design/narration/short-context-provider-v4.json')
        for field in ('asr_model', 'asr_revision', 'asr_artifacts'):
            self.assertEqual(policy[field], baseline[field])
        self.assertEqual(len(policy['rules']), 6)
        self.assertEqual({row['text']: row['parent_text'] for row in policy['rules']},
                         dict(self.expected.values()))
        pipeline = retry.load_pipeline()
        settings = json.loads((ROOT / 'apps/practice/content.json').read_text())['narration']['workout']
        pipeline.LOCALES = retry.media_path(settings['text_directory']).resolve()
        config = json.loads((ROOT / settings['config']).read_text())
        actual = {key: text for _, key, text in pipeline.wanted(config, ['pt'], list(self.expected))}
        self.assertEqual(actual, {key: values[0] for key, values in self.expected.items()})
        for row in policy['rules']:
            self.assertEqual(set(row), {'locale', 'text', 'parent_text',
                                       'maximum_parent_seconds', 'minimum_parent_match'})
            self.assertEqual(row['locale'], 'pt')
            self.assertEqual(row['maximum_parent_seconds'], 5.8)
            self.assertEqual(row['minimum_parent_match'], 0.92)
            resolved = context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', row['text'], 'workout/voice')
            self.assertEqual(resolved['parent_text'], row['parent_text'])
        for key in ('workout_say_count_3', 'workout_say_count_2', 'workout_say_count_1', 'workout_say_go'):
            self.assertEqual(config['maximum_clip_seconds_by_key'][key], 0.95)
        self.assertEqual(pipeline.LOCAL_PROVIDERS['chatterbox-portuguese'].descriptor(config)['minimum_speaker_cosine'], 0.65)

    def test_policy_rejects_other_locale_voice_and_unregistered_text(self):
        import local_narration_context as context
        for text, _ in self.expected.values():
            for code in ('en', 'cs', 'ru'):
                self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', code, text, 'workout/voice'))
            for voice in ('workout/voice_male', 'taichi/voice', 'sunsalutation/voice'):
                self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, voice))
            self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text + ' ', 'workout/voice'))
        for text in ('3.', '2.', '1.', 'Start!', 'Três', 'Inspire.'):
            self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, 'workout/voice'))



class PortuguesePolicySuccessorTests(unittest.TestCase):
    policy = ROOT / 'design/narration/workout-portuguese-context-v2.json'
    additions = {
        'workout_say_crunches': ('Abdominais. Comece.',
            'Abdominais. Comece. Mantenha o movimento controlado.'),
        'workout_say_step_ups': ('Subidas no degrau. Vai!',
            'Subidas no degrau. Vai! Suba e desça com controle.'),
        'workout_say_squats': ('Agachamentos. Comece.',
            'Agachamentos. Comece. Mantenha o movimento controlado.'),
    }

    def test_three_new_rules_match_actual_canonical_requests(self):
        import local_narration_context as context
        pipeline = retry.load_pipeline()
        settings = json.loads((ROOT / 'apps/practice/content.json').read_text())['narration']['workout']
        pipeline.LOCALES = retry.media_path(settings['text_directory']).resolve()
        config = json.loads((ROOT / settings['config']).read_text())
        actual = {key: text for _, key, text in pipeline.wanted(config, ['pt'], list(self.additions))}
        self.assertEqual(actual, {key: values[0] for key, values in self.additions.items()})
        policy = json.loads(self.policy.read_text())
        self.assertEqual(len(policy['rules']), 9)
        self.assertEqual({r['text']: r['parent_text'] for r in policy['rules'][6:]}, dict(self.additions.values()))
        for text, parent in self.additions.values():
            resolved = context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, 'workout/voice')
            self.assertEqual(resolved['parent_text'], parent)
            self.assertTrue(parent.startswith(text + ' '))
            self.assertEqual(context.words(parent)[:len(context.words(text))], context.words(text))
            self.assertGreater(len(context.words(parent)), len(context.words(text)))

    def test_v1_bytes_and_every_existing_rule_and_seal_are_preserved(self):
        import local_narration_context as context
        self.assertEqual(retry.checksum(PortuguesePolicyTests.policy),
            '0c92d84fde6c1b69f32dca0d52199df58eab9487238c90f897089fce39d0183d')
        original = json.loads(PortuguesePolicyTests.policy.read_text())
        successor = json.loads(self.policy.read_text())
        self.assertEqual(successor['rules'][:6], original['rules'])
        self.assertEqual({k: v for k, v in successor.items() if k != 'rules'},
                         {k: v for k, v in original.items() if k != 'rules'})
        self.assertEqual(len({(r['locale'], r['text']) for r in successor['rules']}), 9)
        for row in successor['rules']:
            self.assertEqual(set(row), {'locale', 'text', 'parent_text',
                'maximum_parent_seconds', 'minimum_parent_match'})
            self.assertEqual(row['locale'], 'pt')
            self.assertEqual(row['maximum_parent_seconds'], 5.8)
            self.assertEqual(row['minimum_parent_match'], 0.92)

    def test_all_nine_rules_reject_other_locales_voices_and_aliases(self):
        import local_narration_context as context
        policy = json.loads(self.policy.read_text())
        for row in policy['rules']:
            text = row['text']
            for code in ('en', 'es', 'cs', 'de', 'fr', 'ru', 'ja', 'ko', 'zh'):
                self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', code, text, 'workout/voice'))
            for voice in ('workout/voice_male', 'taichi/voice', 'sunsalutation/voice'):
                self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, voice))
            for alias in (text + ' ', text.lower(), text[:-1], row['parent_text']):
                self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', alias, 'workout/voice'))
        for text in ('3.', '2.', '1.', 'Start!', 'Abdominais', 'Agachamento. Comece.',
                     'Subida no degrau. Vai!', 'Inspire.'):
            self.assertIsNone(context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, 'workout/voice'))

    def test_existing_six_recipes_keep_identical_verification_parameters(self):
        import local_narration_context as context
        for text, _ in PortuguesePolicyTests.expected.values():
            old = dict(next(r for r in json.loads(PortuguesePolicyTests.policy.read_text())['rules'] if r['text'] == text), voice_directory='workout/voice')
            new = context.recipe(ROOT / 'design/narration/workout-portuguese-context-v3.json', 'pt', text, 'workout/voice')
            for field in ('policy_path', 'policy_sha256', 'sha256'):
                new.pop(field)
            self.assertEqual(new, old)

    def test_final_duration_speaker_source_and_verifier_gates_stay_sealed(self):
        import local_narration_context as context
        pins = {
            'scripts/retry-local-narration.py': '64d08e6ff3267b0e84c1c7f0710c03cd6f413b0e329c96c0acdb0dd001c26308',
            'scripts/generate-lumi-guide-narration.py': '7c16b2311d476322e31a4d8f187d585fc0c482a9e50440bd2775965cd681bb27',
            'scripts/local_narration_context.py': '8a1d08a8ad9a3bfec2e75150ebfa5ef9e76a2060857e14f352a4d1b18321e6cb',
            'design/workout/narration.json': 'b4297ddf2a6acc746096910e7b443b5e5e38f7f3dcfa39e7638989c498a03d36',
        }
        for name, digest in pins.items():
            self.assertEqual(retry.checksum(ROOT / name), digest)
        pipeline = retry.load_pipeline()
        settings = json.loads((ROOT / 'apps/practice/content.json').read_text())['narration']['workout']
        source = retry.media_path(settings['text_directory']).resolve() / 'pt.txt'
        self.assertEqual(retry.checksum(source),
            '368bcb52e080f034604b1e41452acec0b8cff17afcfffd9dafa1630f6030455a')
        config = json.loads((ROOT / settings['config']).read_text())
        self.assertEqual(pipeline.LOCAL_PROVIDERS['chatterbox-portuguese'].descriptor(config)['minimum_speaker_cosine'], 0.65)
        for key in ('workout_say_count_3', 'workout_say_count_2', 'workout_say_count_1', 'workout_say_go'):
            self.assertEqual(config['maximum_clip_seconds_by_key'][key], 0.95)
        baseline = context.load_policy(ROOT / 'design/narration/short-context-provider-v4.json')
        successor = json.loads(self.policy.read_text())
        for field in ('asr_model', 'asr_revision', 'asr_artifacts'):
            self.assertEqual(successor[field], baseline[field])


if __name__ == '__main__':
    unittest.main()
