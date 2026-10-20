#!/usr/bin/env python3
"""The shipped catalog, plan, translations and package resources agree."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"inbe": 10, "practice": 60, "diary": 20, "habits": 20,
            "lists": 15, "lumi": 10, "photos": 10, "radio": 10, "leaderboard": 5}


def entries(path):
    return dict(re.findall(r"\[([a-z0-9_]+)\]\n(.*?)\n---", path.read_text(), re.S))


class AchievementCatalogs(unittest.TestCase):
    def test_catalog_and_translations(self):
        all_ids = set()
        groups = set()
        for app, count in EXPECTED.items():
            directory = ROOT / "apps" / app
            catalog = json.loads((directory / "achievements.json").read_text())
            owner = "inbe" if app == "inbe" else "inbe." + ("practices" if app == "practice" else app)
            self.assertEqual(catalog["app"], owner)
            self.assertEqual(catalog["schema"], 1)
            self.assertEqual(len(catalog["achievements"]), count)
            keys = set()
            for achievement in catalog["achievements"]:
                identity = achievement["id"]
                self.assertRegex(identity, r"^[a-z0-9_.-]{1,96}$")
                self.assertNotIn(identity, all_ids)
                all_ids.add(identity)
                groups.add(achievement["group"])
                self.assertIsInstance(achievement["target"], int)
                self.assertGreater(achievement["target"], 0)
                namespace = "app" if app == "inbe" else ("practices" if app == "practice" else app)
                self.assertEqual(achievement["badge"], f"assets/{namespace}/badges/{identity}.shape")
                artwork = (directory / "badges" / (identity + ".shape")).read_text()
                self.assertTrue(artwork.startswith("S1.5rr:"))
                self.assertLess(len(artwork), 1024)
                self.assertGreater(achievement["badge_tier"], 0)
                self.assertLessEqual(achievement["badge_tier"], 99)
                keys.update((achievement["title_key"], achievement["description_key"]))
            for locale in sorted((ROOT / "locales").glob("*.txt")):
                if locale.stem == "index":
                    continue
                translations = json.loads((directory / "achievement-locales" / (locale.stem + ".json")).read_text())
                self.assertEqual(set(translations), keys)
                root_text = entries(locale)
                for key, value in translations.items():
                    self.assertTrue(value.strip())
                    self.assertEqual(root_text[key], value)
        self.assertEqual(len(all_ids), 160)
        plan = (ROOT / "docs/achievements-plan.md").read_text()
        listed = set(re.findall(r"\*\* — `([a-z0-9_.-]+)`:", plan))
        self.assertEqual(all_ids, listed)
        for locale in sorted((ROOT / "locales").glob("*.txt")):
            if locale.stem != "index":
                self.assertTrue({"achievement_group_" + group for group in groups} <= set(entries(locale)))


if __name__ == "__main__":
    unittest.main()
