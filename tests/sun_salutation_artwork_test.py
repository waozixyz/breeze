#!/usr/bin/env python3
"""Regression checks for painted parts imported from a white background."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sun_salutation_artwork",
    ROOT / "character-proposals/2026-09-30-banner-style/build_proposals.py",
)
ARTWORK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTWORK)


class WhiteBackgroundCutoutTest(unittest.TestCase):
    def fixture(self):
        paint = np.array([54, 102, 71], dtype=np.float32)
        alpha = np.zeros((80, 80), dtype=np.float32)
        alpha[9:71, 9:71] = 0.03
        alpha[10:70, 10:70] = 0.10
        alpha[11:69, 11:69] = 0.35
        alpha[12:68, 12:68] = 1
        rgb = np.round(paint * alpha[..., None] + 255 * (1 - alpha[..., None]))
        return rgb.astype(np.uint8), alpha, paint

    def test_antialiased_edges_recover_paint_instead_of_white(self):
        rgb, expected_alpha, paint = self.fixture()
        image = ARTWORK.white_background_cutout(Image.fromarray(rgb), "leg.png")
        result = np.asarray(image)
        for point in ((9, 40), (10, 40), (11, 40), (12, 40)):
            y, x = point
            self.assertLessEqual(abs(int(result[y, x, 3]) - expected_alpha[y, x] * 255), 2)
            # A pale edge on white must become the original fabric color
            # with low coverage, rather than an opaque white line on dark.
            self.assertLess(np.max(np.abs(result[y, x, :3].astype(float) - paint)), 8)
        self.assertTrue(np.all(result[0, :, 3] == 0))
        self.assertTrue(np.all(result[-1, :, 3] == 0))

    def test_ivory_and_white_inside_the_paint_stay_opaque(self):
        rgb, _, _ = self.fixture()
        rgb[30:40, 30:40] = [248, 246, 243]
        rgb[40:45, 40:45] = 255
        result = np.asarray(ARTWORK.white_background_cutout(Image.fromarray(rgb), "torso.png"))
        np.testing.assert_array_equal(result[35, 35], [248, 246, 243, 255])
        np.testing.assert_array_equal(result[42, 42], [255, 255, 255, 255])

    def test_disconnected_marks_do_not_become_character_pixels(self):
        rgb, _, _ = self.fixture()
        rgb[1:4, 1:4] = [50, 60, 40]
        result = np.asarray(ARTWORK.white_background_cutout(Image.fromarray(rgb), "leg.png"))
        self.assertTrue(np.all(result[1:4, 1:4, 3] == 0))
        self.assertEqual(int(result[40, 40, 3]), 255)


if __name__ == "__main__":
    unittest.main()
