"""The offline chat notes follow the changelog without mixing releases."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tempfile

from release_notes import release_notes, translations


class ReleaseNotesTest(unittest.TestCase):
    def test_latest_release_keeps_whole_entries_and_unicode(self):
        notes = release_notes("""# Changelog

## [2.1.36] - 2026-10-18
### Added
- Lumi’s update message.
  Keeps visible paragraphs.
### Fixed
- An older problem.

## [2.1.35] - 2026-10-17
- Do not include this older release.
""")
        self.assertEqual(notes, {"version": "2.1.36", "notes": [
            "Lumi’s update message. Keeps visible paragraphs.", "An older problem."]})

    def test_missing_version_or_notes_is_rejected(self):
        for document in ("# Changelog", "## [2.1.36] - 2026-10-18\n"):
            with self.subTest(document=document), self.assertRaises(ValueError):
                release_notes(document)

    def test_translations_follow_the_latest_release(self):
        english = {"version": "2.1.36", "notes": ["One.", "Two."]}
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "de.md").write_text("## [2.1.36] - 2026-10-18\n- Eins.\n- Zwei.\n")
            Path(folder, "fr.md").write_text("## [2.1.35] - 2026-10-17\n- Ancien.\n")
            self.assertEqual(translations(Path(folder), english),
                             {"de": {"version": "2.1.36", "notes": ["Eins.", "Zwei."]}})
            Path(folder, "it.md").write_text("## [2.1.36] - 2026-10-18\n- Uno.\n")
            with self.assertRaises(ValueError):
                translations(Path(folder), english)

    def test_every_language_translates_the_latest_release(self):
        english = release_notes((ROOT / "CHANGELOG.md").read_text())
        languages = [line.split("|")[0] for line in
                     (ROOT / "locales/index.txt").read_text().splitlines() if line.strip()]
        self.assertEqual(sorted(translations(ROOT / "locales/changelog", english)),
                         sorted(language for language in languages if language != "en"))

    def test_real_changelog_matches_the_application_version(self):
        notes = release_notes((ROOT / "CHANGELOG.md").read_text())
        self.assertIn('VersionString :: "' + notes["version"] + '"',
                      (ROOT / "src/core/version.zi").read_text())
        self.assertTrue(notes["notes"])


if __name__ == "__main__":
    unittest.main()
