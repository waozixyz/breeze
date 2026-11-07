"""Lumi and store notes share short core Breeze changes, without game entries."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_notes import GAME_NOTES, PLAY_LISTINGS, release_notes, translations


class ReleaseNotesTest(unittest.TestCase):
    def temporary_folder(self):
        folder = ROOT / "build" / "release-notes-test"
        folder.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=folder)

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
        with self.temporary_folder() as folder:
            Path(folder, "de.md").write_text("## [2.1.36] - 2026-10-18\n- Eins.\n- Zwei.\n")
            Path(folder, "fr.md").write_text("## [2.1.35] - 2026-10-17\n- Ancien.\n")
            self.assertEqual(translations(Path(folder), english),
                             {"de": {"version": "2.1.36", "notes": ["Eins.", "Zwei."]}})
            Path(folder, "it.md").write_text("## [2.1.36] - 2026-10-18\n- Uno.\n")
            with self.assertRaises(ValueError):
                translations(Path(folder), english)

    def test_games_are_filtered_before_the_three_note_limit(self):
        notes = release_notes("""## [2.1.36] - 2026-10-18
- Arcade opens offline.
- Shovey loads faster.
- Wurm keeps saved progress.
- Apfelwurm has new skins.
- Catalog games award achievements.
- Keep this practice change.
- A wrapped change mentions
  Arcade artwork.
### Games
- Unbranded puzzle controls.
#### Fixed
- Unbranded editor crash.
### Habits
- Keep this habit change.
- Keep this sync change.
- A fourth core note.
""")
        self.assertEqual(notes["notes"], ["Keep this practice change.",
                                         "Keep this habit change.", "Keep this sync change."])

    def test_game_only_release_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "core Breeze"):
            release_notes("## [2.1.36] - 2026-10-18\n### Games\n- New puzzle controls.\n")

    def test_game_filter_covers_every_translated_language(self):
        entries = ["Arcadeライブラリ", "Arcade와 이미지", "Hry z katalogu", "Neue Spiele",
                   "Juegos del catálogo", "Les jeux du catalogue", "Game baru",
                   "Giochi del catalogo", "Jogos do catálogo", "Игры из каталога",
                   "カタログのゲーム", "카탈로그 게임", "目录中的游戏"]
        for entry in entries:
            with self.subTest(entry=entry):
                document = f"## [2.1.36] - 2026-10-18\n- {entry}\n- Habit reminders.\n"
                self.assertEqual(release_notes(document)["notes"], ["Habit reminders."])

    def test_lumi_fdroid_and_play_use_the_same_game_filter(self):
        with self.temporary_folder() as folder:
            root = Path(folder)
            changelog = root / "CHANGELOG.md"
            changelog.write_text("""## [Unreleased]
- This must wait for the next release.
## [2.1.36] - 2026-10-18
- Practice guidance.
- Include Arcade offline.
### Games
- New puzzle controls.
### Habits
- Habit reminders.
""", encoding="utf-8")
            translated = root / "locales/changelog/de.md"
            translated.parent.mkdir(parents=True)
            translated.write_text("""## [2.1.36] - 2026-10-18
- Übungsanleitung.
- Arcade offline nutzen.
### Spiele
- Neue Rätselsteuerung.
### Gewohnheiten
- Gewohnheitserinnerungen.
""", encoding="utf-8")
            output = root / "assets/app/release-notes.json"
            command = [sys.executable, str(ROOT / "scripts/release_notes.py"), str(changelog)]
            subprocess.run(command + [str(output)], check=True, capture_output=True, text=True)
            subprocess.run(command + ["--play", "123"], check=True, capture_output=True, text=True)
            for locale, language, expected in (
                ("en-US", "", ["Practice guidance.", "Habit reminders."]),
                ("de-DE", "-de", ["Übungsanleitung.", "Gewohnheitserinnerungen."]),
            ):
                with self.subTest(locale=locale):
                    document = json.loads(output.with_name(f"release-notes{language}.json").read_text())
                    self.assertEqual(document, {"version": "2.1.36", "notes": expected})
                    store = root / f"fastlane/metadata/android/{locale}/changelogs/123.txt"
                    self.assertEqual(store.read_text(), "".join(f"- {note}\n" for note in expected))

    def test_current_sources_are_short_core_notes(self):
        for path in [ROOT / "CHANGELOG.md", *sorted((ROOT / "locales/changelog").glob("*.md"))]:
            document = path.read_text()
            latest = release_notes(document)["version"]
            # Unreleased notes collect toward the next release, which ships 2 or 3.
            versions = [latest]
            if "## [Unreleased]" in document:
                versions.insert(0, "Unreleased")
            for version in versions:
                with self.subTest(path=path.name, version=version):
                    section = document.split(f"## [{version}]", 1)[1].split("\n## [", 1)[0]
                    entries = [line[2:] for line in section.splitlines() if line.startswith("- ")]
                    self.assertGreaterEqual(len(entries), 1 if version == "Unreleased" else 2)
                    self.assertLessEqual(len(entries), 3)
                    for entry in entries:
                        self.assertLessEqual(len(entry), 120)
                        self.assertIsNone(GAME_NOTES.search(entry), entry)
                        self.assertNotRegex(entry, r"https?://|\[[^]]+\]\(|Android\s+\d")
                    self.assertFalse(any(line.startswith("  ") for line in section.splitlines()))

    def test_current_fdroid_and_play_notes_match_lumi(self):
        english = release_notes((ROOT / "CHANGELOG.md").read_text())
        translated = translations(ROOT / "locales/changelog", english)
        listings = {"en-US": english}
        listings.update({PLAY_LISTINGS[language]: notes for language, notes in translated.items()})
        code = re.search(r"versionCode (\d+)", (ROOT / "droid/app/build.gradle").read_text())[1]
        for locale, notes in listings.items():
            with self.subTest(locale=locale):
                path = ROOT / f"fastlane/metadata/android/{locale}/changelogs/{code}.txt"
                text = path.read_text()
                self.assertEqual(text, "".join(f"- {note}\n" for note in notes["notes"]))
                self.assertIsNone(GAME_NOTES.search(text))
                self.assertLessEqual(len(text), 500)

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
