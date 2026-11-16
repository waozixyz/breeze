import difflib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location(
    'matcher_speech', ROOT / 'scripts/generate-lumi-guide-narration.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)

EXPECTED = (
    "À partir du point devant votre visage, déplacez-vous dans le sens des aiguilles "
    "d'une montre. Effleurez le côté droit de la pièce, puis l'espace derrière vous, "
    "puis le côté gauche, puis revenez au point devant votre visage. Laissez le circuit "
    "inclure plafond ou mur, surfaces latérales, sol ou lit, puis le retour. "
    "Déplacez-vous avec fluidité, sans forcer la vitesse.")
TRANSCRIPT = EXPECTED.replace('surfaces latérales', 'surface latérale')


class NarrationTextMatcherTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(minimum_match=.92, verify_directions=True, verify_numbers=True)

    def test_preserved_long_french_witness(self):
        expected = speech.normalized(EXPECTED)
        heard = speech.normalized(TRANSCRIPT)
        self.assertEqual((len(expected), len(heard)), (293, 291))
        self.assertAlmostEqual(difflib.SequenceMatcher(None, expected, heard).ratio(),
                               .7534246575342466)
        self.assertAlmostEqual(speech.match(EXPECTED, TRANSCRIPT), .9965753424657534)
        score, detail = speech.assessment(
            self.config, 'fr', EXPECTED, TRANSCRIPT, 25, local=True)
        self.assertGreaterEqual(score, self.config['minimum_match'])
        self.assertEqual(detail['reasons'], [])

    def test_short_comparisons_retain_existing_scores(self):
        for expected, heard in (('Relax.', 'Relax.'), ('Relax.', 'Release.'),
                                ('呼吸を整えて。', '呼吸を整える。'), ('', ''), ('', 'Relax.')):
            with self.subTest(expected=expected, heard=heard):
                previous = difflib.SequenceMatcher(
                    None, speech.normalized(expected), speech.normalized(heard)).ratio()
                self.assertEqual(speech.match(expected, heard), previous)

    def test_missing_short_tail_fails_above_whole_text_threshold(self):
        heard = EXPECTED.replace(', sans forcer la vitesse', '')
        self.assertGreaterEqual(speech.match(EXPECTED, heard), self.config['minimum_match'])
        score, detail = speech.assessment(
            self.config, 'fr', EXPECTED, heard, 25, local=True)
        self.assertEqual(score, 0)
        self.assertIn('ending', detail['reasons'])

    def test_wrong_long_text_is_rejected(self):
        heard = 'Respirez calmement et reposez chaque muscle du corps. ' * 8
        self.assertLess(speech.match(EXPECTED, heard), self.config['minimum_match'])
        self.assertLess(speech.complete_match(
            self.config, 'fr', EXPECTED, heard, 25, ming=True), self.config['minimum_match'])

    def test_repetition_and_insertion_fail_with_matching_ending(self):
        insertion = 'Respirez calmement et reposez chaque muscle du corps. ' * 3
        for heard in (EXPECTED + ' ' + EXPECTED,
                      EXPECTED.replace('Laissez le circuit', insertion + 'Laissez le circuit')):
            with self.subTest(heard=heard):
                score, detail = speech.assessment(
                    self.config, 'fr', EXPECTED, heard, 40, local=True)
                self.assertEqual(detail['ending_scores'], {'64': 1, '24': 1})
                self.assertLess(score, self.config['minimum_match'])
                self.assertIn('transcript', detail['reasons'])

    def test_direction_and_number_gates_are_unchanged(self):
        for heard in (EXPECTED.replace('côté droit', 'côté gauche'),
                      EXPECTED.replace('le retour', 'le retour 2')):
            with self.subTest(heard=heard):
                self.assertGreaterEqual(speech.match(EXPECTED, heard), self.config['minimum_match'])
                self.assertEqual(speech.verified_match(self.config, 'fr', EXPECTED, heard), 0)

    def test_normalization_is_unchanged(self):
        self.assertEqual(speech.normalized('ＲＥＬＡＸ — １２３!'), 'relax123')
        self.assertEqual(speech.match('ＲＥＬＡＸ — １２３!', 'relax 123'), 1)


if __name__ == '__main__':
    unittest.main()
