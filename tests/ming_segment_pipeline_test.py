#!/usr/bin/env python3
"""Real float-WAV/cache/PCM assembly tests in the existing Ming environment.

No model is loaded. Synthesis is a finite fixture; encoding, disk persistence,
resume, source routing and invalid waveform diagnostics are exercised for real.
"""
from contextlib import nullcontext
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ming_narration as ming


class Waveform:
    def __init__(self, values):
        self.values = np.asarray(values, dtype='float32')

    def detach(self):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.values


class PipelineTest(unittest.TestCase):
    def setUp(self):
        output = ROOT / 'build/ming-segment-pipeline-test'
        output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=output)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        self.engine = ming.Engine.__new__(ming.Engine)
        self.engine.profile = dict(model='fixture', model_revision='fixture', runtime_revision='fixture',
            reference_sha256='a' * 64, embedding_sha256='b' * 64, instruction='Calm.', seed=17,
            segmentation=dict(maximum_units=24))
        self.engine.local = dict(embedding='original-female.pt')
        self.engine.model = SimpleNamespace(sample_rate=24000,
            synthesize=Mock(return_value=Waveform([0.1] * 2400)))
        self.engine.torch = SimpleNamespace(manual_seed=Mock(), bfloat16='fixture',
                                            autocast=lambda *a, **k: nullcontext())
        self.engine.load = Mock()
        self.engine.request_budget = Mock(return_value=dict(input_tokens=100, decode_seconds=32.96))

    def test_span_reuses_float_waveform_without_duplicate_synthesis(self):
        first, metadata = self.engine.synthesize_span('Breathe.', 'de', 0, 0, self.cache)
        second, cached = self.engine.synthesize_span('Breathe.', 'de', 0, 0, self.cache)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(metadata, cached)
        self.engine.model.synthesize.assert_called_once()
        request = self.engine.model.synthesize.call_args.kwargs
        self.assertEqual(request['text'], 'Breathe.')
        self.assertEqual(request['language_id'], 'de')
        self.assertEqual(request['spk_emb_path'], 'original-female.pt')
        self.assertTrue(request['raw_text'])

    def test_retry_and_order_seeds_change_cache_identity(self):
        rows = [self.engine.synthesize_span('Breathe.', 'de', attempt, index, self.cache)[1]
                for attempt, index in ((0, 0), (0, 1), (1, 0))]
        self.assertEqual([row['seed'] for row in rows], [17, 18, 1000020])
        self.assertEqual(len({row['identity'] for row in rows}), 3)
        self.assertEqual(self.engine.model.synthesize.call_count, 3)

    def test_finite_overshoot_is_saved_as_float_and_rejected_without_clipping(self):
        self.engine.model.synthesize.return_value = Waveform([0.1, 1.125, -1.25])
        with self.assertRaisesRegex(RuntimeError, 'peak exceeds PCM range'):
            self.engine.synthesize_span('Breathe.', 'ja', 0, 0, self.cache)
        path = next(self.cache.glob('*.wav'))
        self.assertEqual(sf.info(path).subtype, 'FLOAT')
        audio, _ = sf.read(path)
        self.assertEqual(float(audio.min()), -1.25)
        row = json.loads(next(self.cache.glob('*.raw.json')).read_text())
        self.assertEqual(row['raw_peak'], 1.25)
        self.assertEqual(row['gain'], 1.0)
        with self.assertRaises(RuntimeError):
            self.engine.synthesize_span('Breathe.', 'ja', 0, 0, self.cache)
        self.engine.model.synthesize.assert_called_once()

    def test_nonfinite_and_empty_audio_fail_with_numeric_diagnostics(self):
        for index, values in enumerate(([float('nan')], [], [float('inf')])):
            with self.subTest(values=values):
                self.engine.model.synthesize.return_value = Waveform(values)
                with self.assertRaisesRegex(RuntimeError, 'invalid waveform'):
                    self.engine.synthesize_span('Breathe.', 'ja', 0, index, self.cache)
        rows = [json.loads(path.read_text()) for path in self.cache.glob('*.raw.json')]
        self.assertEqual(len(rows), 3)
        self.assertFalse(any(self.cache.glob('*.wav')))
        self.assertTrue(all(row['raw_peak'] is None for row in rows))

    def test_whole_cue_concatenates_and_resumes_exact_span_audio(self):
        text = ' '.join(['Breathe slowly.'] * 14)
        config = dict(pcm_sample_rate=24000, sample_rate=16000)
        call = subprocess.run
        source = self.root / 'scripts/ming_narration.py'
        source.parent.mkdir()
        source.write_text('test source identity fixture\n')

        def command(argv, **kwargs):
            if argv[0] == 'git':
                return SimpleNamespace(returncode=0)
            return call(argv, **kwargs)

        with patch.object(ming, '__file__', str(self.root / 'scripts/ming_narration.py')), \
                patch.object(ming.subprocess, 'run', side_effect=command):
            audio, _ = self.engine.speak(config, text, 'de', self.root, 0)
            metadata = copy.deepcopy(self.engine.last_generation)
            again, _ = self.engine.speak(config, text, 'de', self.root, 0)
        spans = ming.segment_plan(self.engine.profile, text)['spans']
        self.assertEqual(audio, again)
        self.assertEqual(len(audio), 2400 * len(spans) * 2)
        self.assertEqual(metadata, self.engine.last_generation)
        self.assertEqual(self.engine.model.synthesize.call_count, len(spans))
        calls = self.engine.model.synthesize.call_args_list
        self.assertEqual(''.join(call.kwargs['text'] for call in calls), text)
        self.assertTrue(all(call.kwargs['spk_emb_path'] == 'original-female.pt' for call in calls))


if __name__ == '__main__':
    unittest.main()
