"""Actual attempt persistence, best/last reporting and Chinese negative controls."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import ming_narration_test as fixtures
from narration_diagnostics import Attempts

speech = fixtures.speech
ROOT = fixtures.ROOT


class AttemptTests(unittest.TestCase):
    def setUp(self):
        fixtures.MingTests.setUp(self)

    def test_rejected_attempts_persist_distinct_duration_speaker_and_transcript_reasons(self):
        clip = self.folder / 'existing.ogg'
        clip.write_bytes(b'test encoded bytes; duration measured by fixture')
        saved = self.folder / 'diagnostics.json'
        expected = 'Keep breathing naturally. Open your eyes and return to the room.'
        best_heard = 'Keep breathing naturally.'
        last_heard = 'A completely different final transcript.'
        texts = iter((best_heard, last_heard))
        speakers = iter((0.1, 0.9, 0.9))
        engine = SimpleNamespace(profile=self.profile,
            speak=lambda *args: (b'cached PCM', fixtures.ming.provenance(self.profile)),
            speaker_match=lambda *args: next(speakers), last_transcription=None)

        def transcribe(path, code):
            text = next(texts)
            engine.last_transcription = dict(text=text, model='fixture', revision='pinned', language=code)
            return text

        engine.transcribe = transcribe

        def diagnostic(*args):
            result = Attempts(*args)
            result.path = saved
            return result

        config = dict(self.config, _local_engine=engine)
        with patch.object(speech, 'Attempts', side_effect=diagnostic), \
                patch.object(speech, 'encode', return_value=clip), \
                patch.object(speech, 'seconds', side_effect=[121, 2, 2, 2]):
            with self.assertRaises(RuntimeError) as raised:
                speech.generate(config, None, 'de', 'cue', expected)
        message = str(raised.exception)
        self.assertIn('best heard: ' + best_heard, message)
        self.assertIn('last attempt 3', message)
        self.assertIn(last_heard, message)
        data = json.loads(saved.read_text())
        self.assertEqual(len(data['attempts']), 4)
        rows = data['attempts']
        self.assertEqual(rows[0]['reasons'], ['duration'])
        self.assertIsNone(rows[0]['transcript'])
        self.assertEqual(rows[1]['reasons'], ['speaker'])
        self.assertEqual(rows[1]['minimum_speaker_cosine'], 0.7)
        self.assertIn('ending', rows[2]['reasons'])
        self.assertEqual(rows[3]['asr']['model'], 'fixture')
        self.assertEqual(rows[3]['transcript'], last_heard)
        self.assertFalse((self.folder / 'voice').exists())

    def test_record_is_bounded_and_cannot_escape_identifiers(self):
        record = Attempts(ROOT, 'ja', 'cue', 'voice-unit', 'a' * 64)
        record.path = self.folder / 'bounded.json'
        record.save(dict(transcript='x' * 9000, reasons=['transcript']))
        data = json.loads(record.path.read_text())['attempts'][0]
        self.assertEqual(len(data['transcript']), 8192)
        self.assertTrue(data['transcript_truncated'])
        with self.assertRaises(ValueError):
            Attempts(ROOT, 'ja', '../escape', 'voice-unit', 'a' * 64)

    def context_retry_fixture(self):
        import local_narration_context
        clip = self.folder / 'candidate.ogg'
        clip.write_bytes(b'encoded fixture; duration measured separately')
        diagnostics = self.folder / 'context-attempts.json'
        synthesis = fixtures.ming.provenance(self.profile)
        engine = SimpleNamespace(profile=self.profile, speaker_match=Mock(return_value=0.9),
            transcribe=Mock(return_value='Inhala.'),
            last_transcription=dict(text='Inhala.', model='fixture', revision='pinned', language='es'),
            speak=Mock(return_value=(b'PCM', synthesis)))
        rejected = local_narration_context.ContextRejected('parent_speaker',
            dict(parent_cosine=0.69, minimum_parent_cosine=0.7, seconds=3.1,
                 synthesis=synthesis, parent_sha256='b' * 64))

        def diagnostic(*args):
            record = Attempts(*args)
            record.path = diagnostics
            return record

        self.addCleanup(patch.stopall)
        patch.object(speech, 'Attempts', side_effect=diagnostic).start()
        patch.object(speech, 'encode', return_value=clip).start()
        patch.object(speech, 'seconds', return_value=1.0).start()
        patch.object(speech, 'clip_path', return_value=self.folder / 'accepted.ogg').start()
        patch.object(speech, 'packaged_path', return_value='sunsalutation/voice/es/cue.ogg').start()
        return engine, rejected, diagnostics

    def test_context_parent_rejection_preserves_metrics_and_uses_next_candidate(self):
        engine, rejected, diagnostics = self.context_retry_fixture()
        engine.speak.side_effect = [rejected, (b'PCM', fixtures.ming.provenance(self.profile))]
        config = dict(self.config, _local_engine=engine,
                      _context_profile='design/narration/short-context.json')
        row = speech.generate(config, None, 'es', 'cue', 'Inhala.')
        self.assertEqual(row['attempts'], 2)
        self.assertEqual([call.args[-1] for call in engine.speak.call_args_list], [0, 1])
        attempts = json.loads(diagnostics.read_text())['attempts']
        self.assertEqual(attempts[0]['reasons'], ['context'])
        self.assertEqual(attempts[0]['context'], rejected.diagnostics)
        self.assertEqual(attempts[0]['context']['parent_cosine'], 0.69)
        self.assertEqual(attempts[1]['transcript'], 'Inhala.')
        self.assertTrue((self.folder / 'accepted.ogg').is_file())

    def test_context_rejections_stop_at_four_and_publish_no_failed_candidate(self):
        engine, rejected, diagnostics = self.context_retry_fixture()
        engine.speak.side_effect = rejected
        config = dict(self.config, _local_engine=engine,
                      _context_profile='design/narration/short-context.json')
        with self.assertRaisesRegex(RuntimeError, 'last attempt 3'):
            speech.generate(config, None, 'es', 'cue', 'Inhala.')
        self.assertEqual(engine.speak.call_count, 4)
        engine.speaker_match.assert_not_called()
        engine.transcribe.assert_not_called()
        attempts = json.loads(diagnostics.read_text())['attempts']
        self.assertEqual(len(attempts), 4)
        self.assertTrue(all(row['reasons'] == ['context'] for row in attempts))
        self.assertFalse((self.folder / 'accepted.ogg').exists())

    def test_integrity_config_and_io_errors_stay_fatal_and_context_is_explicit(self):
        engine, rejected, diagnostics = self.context_retry_fixture()
        config = dict(self.config, _local_engine=engine,
                      _context_profile='design/narration/short-context.json')
        for error in (ValueError('Changed reference hash'), KeyError('missing config'),
                      OSError('Missing model file')):
            with self.subTest(error=type(error).__name__):
                engine.speak.reset_mock(side_effect=True)
                engine.speak.side_effect = error
                with self.assertRaises(type(error)):
                    speech.generate(config, None, 'es', 'cue', 'Inhala.')
                self.assertEqual(engine.speak.call_count, 1)
                self.assertEqual(json.loads(diagnostics.read_text())['attempts'][0]['reasons'], ['error'])
        engine.speak.reset_mock(side_effect=True)
        engine.speak.side_effect = rejected
        with self.assertRaises(type(rejected)):
            speech.generate(dict(self.config, _local_engine=engine), None, 'es', 'cue', 'Inhala.')
        self.assertEqual(engine.speak.call_count, 1)

    def test_only_source_bound_chinese_phrase_matches_both_scripts_without_erasing_controls(self):
        config = json.loads((ROOT / 'design/sun-salutation/narration/narration.json').read_text())
        text = '吸气，右腿向后迈，膝盖落地。'
        for heard in ('吸气,右腿向后脉,膝盖落地。', '吸氣 右腿向後脈 膝蓋落地',
                      '吸氣，右腿向後邁，膝蓋落地。', '吸氣,右腿向後賣,膝蓋落地',
                      '吸气，右腿向后卖，膝盖落地。'):
            self.assertEqual(speech.complete_match(config, 'zh', text, heard, 3.2, True), 1)
        for heard in ('吸氣 左腿向後脈 膝蓋落地', '吸氣 右腿向後脈',
                      '吸氣 右腿向後脈 膝蓋落地2次', '吸氣,左腿向後賣,膝蓋落地',
                      '吸氣,右腿向後賣', '吸氣,右腿向後賣,膝蓋落地2次'):
            self.assertEqual(speech.complete_match(config, 'zh', text, heard, 3.2, True), 0)
        # Pulse words outside this movement remain distinct from the step verb.
        self.assertEqual(speech.comparison_spellings(config, 'zh', '检查脉搏。', '检查迈搏。'),
                         ('检查脉搏。', '检查迈搏。'))
        self.assertEqual(speech.comparison_spellings(config, 'zh', '出售物品。', '賣出物品。'),
                         ('出售物品。', '賣出物品。'))
        untouched = copy.deepcopy(config)
        self.assertNotIn('酒区', json.dumps(untouched, ensure_ascii=False))
        self.assertEqual(speech.complete_match(config, 'ja', '左脚を後ろに引き、膝を床へ。',
                                               '酒区を後ろに引き、膝を床へ。', 4.4, True), 0)


if __name__ == '__main__':
    unittest.main()
