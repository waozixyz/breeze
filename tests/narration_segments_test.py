#!/usr/bin/env python3
"""Source fidelity and meaningful boundaries without any model inference."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import narration_segments as segments


class SegmentationTest(unittest.TestCase):
    def assert_lossless(self, text, maximum=24):
        result = segments.plan(text, maximum)
        self.assertEqual(''.join(span['text'] for span in result['spans']), text)
        for span in result['spans']:
            self.assertEqual(text[span['start']:span['end']], span['text'])
            self.assertTrue(any(c.isalnum() for c in span['text']))
        self.assertEqual(result['pause_ms'], 0)
        self.assertEqual(result, segments.plan(text, maximum))
        return [span['text'] for span in result['spans']]

    def test_sentences_keep_unicode_space_quotes_and_order(self):
        text = '  “Breathe slowly.”\u00a0\nFeel your hand!\tRest now.  '
        self.assertEqual(self.assert_lossless(text, 3),
                         ['  “Breathe slowly.”\u00a0\n', 'Feel your hand!\t', 'Rest now.  '])

    def test_decimal_numeric_tokens_and_abbreviated_tokens_stay_whole(self):
        text = 'Hold 1.5 seconds, then 1,000 steps; at 12:30 use U.S. time. Rest.'
        pieces = self.assert_lossless(text, 4)
        for token in ('1.5', '1,000', '12:30', 'U.S.'):
            self.assertEqual(sum(token in piece for piece in pieces), 1)

    def test_cjk_sentences_and_clauses_need_no_space(self):
        text = 'ゆっくり息を吸います。肩を緩め、手を感じます。\n静かに休みます。'
        pieces = self.assert_lossless(text, 9)
        self.assertGreater(len(pieces), 3)
        self.assertTrue(any(piece.endswith('、') for piece in pieces))

    def test_long_sentence_prefers_clause_before_word_boundaries(self):
        text = 'Feel the whole hand, let every finger relax, then rest here quietly.'
        self.assertEqual(self.assert_lossless(text, 5),
                         ['Feel the whole hand, ', 'let every finger relax, ', 'then rest here quietly.'])

    def test_long_unpunctuated_words_use_whitespace(self):
        text = 'one two three four five six seven eight nine ten'
        pieces = self.assert_lossless(text, 3)
        self.assertTrue(all(segments.semantic_units(piece) <= 3 for piece in pieces))
        self.assertEqual(pieces, ['one two three ', 'four five six ', 'seven eight nine ', 'ten'])

    def test_indivisible_clause_remains_available_for_budget_rejection(self):
        text = '非常に長い句にも安全な切れ目がありません'
        self.assertEqual(self.assert_lossless(text, 3), [text])

    def test_short_movement_cue_is_one_request(self):
        for text in ('Inhale. Raise your arms.', 'Einatmen, Arme heben.',
                     '吸って、腕を上げます。', 'Breathe out'):
            self.assertEqual(self.assert_lossless(text), [text])
        self.assertEqual(self.assert_lossless('Inhale and raise your arms.'),
                         ['Inhale and raise your arms.'])

    def test_rejects_invalid_configuration_and_unspoken_text(self):
        for text in ('', ' \n ', '…!?'):
            with self.assertRaises(ValueError):
                segments.plan(text)
        for maximum in (True, 0, -2, 1.5, '24'):
            with self.assertRaises(ValueError):
                segments.plan('Breathe.', maximum)


if __name__ == '__main__':
    unittest.main()
