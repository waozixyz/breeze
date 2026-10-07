"""Reject module releases that disagree with their public version or package role."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_versions", ROOT / "scripts/check-package-versions.py")
versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versions)


class PackageVersionsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="inbe-package-versions-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.ledger = json.loads((ROOT / "apps/versions.json").read_text())
        for source in versions.NAMES.values():
            directory = self.root / "apps" / source
            directory.mkdir(parents=True)
            (directory / "CHANGELOG.md").write_text((ROOT / "apps" / source / "CHANGELOG.md").read_text())
        self.write(self.ledger)

    def write(self, ledger):
        (self.root / "apps/versions.json").write_text(json.dumps(ledger))

    def test_current_release(self):
        self.assertEqual(versions.validate(self.root), self.ledger)

    def test_each_module_needs_its_own_changelog_version(self):
        for name in versions.NAMES:
            with self.subTest(app=name):
                value = copy.deepcopy(self.ledger)
                value["apps"][name]["version"] = "9.8.7"
                self.write(value)
                with self.assertRaisesRegex(ValueError, "changelog and ledger differ"):
                    versions.validate(self.root)

    def test_invalid_sequences_versions_and_package_roles(self):
        for field, candidates in {
            "version": ("Unreleased", "01.0.0", "1.0", 1),
            "sequence": (0, -1, True, 1.5, 2147483648),
            "id": ("diary", "inbe.lists"),
            "bundled": (False, 0, "false"),
        }.items():
            for candidate in candidates:
                with self.subTest(field=field, value=candidate):
                    value = copy.deepcopy(self.ledger)
                    value["apps"]["diary"][field] = candidate
                    self.write(value)
                    with self.assertRaises(ValueError):
                        versions.validate(self.root)

    def test_every_cell_is_available_offline(self):
        value = copy.deepcopy(self.ledger)
        value["apps"]["habits"]["bundled"] = False
        self.write(value)
        with self.assertRaisesRegex(ValueError, "every cell must be bundled"):
            versions.validate(self.root)

    def test_changelog_requires_a_numeric_first_release(self):
        changelog = self.root / "apps/diary/CHANGELOG.md"
        changelog.write_text("# Diary\n## [Unreleased] - 2026-10-06\n")
        with self.assertRaisesRegex(ValueError, "numeric release"):
            versions.validate(self.root)

    def test_package_resources_do_not_trigger_an_apk_release(self):
        # Apply the ordered positive and negative path globs used by Actions.
        import fnmatch

        def triggered(workflow, path):
            text = (ROOT / ".github/workflows" / workflow).read_text()
            block = text.split("    paths:\n", 1)[1].split("  workflow_dispatch:", 1)[0]
            included = False
            for pattern in re.findall(r"^      - '([^']+)'$", block, re.M):
                excluded = pattern.startswith("!")
                if fnmatch.fnmatchcase(path, pattern.lstrip("!")):
                    included = not excluded
            return included

        for path in ("apps/diary/diary_view.zi", "assets/practices/breath.png",
                     "locales/en.txt", "themes/catalog_dark.kss",
                     "scripts/prepare-package-assets.py", "src/cells/versions.zi"):
            with self.subTest(path=path):
                self.assertTrue(triggered("packages.yml", path))
                self.assertFalse(triggered("release.yml", path))
        for path in ("src/cells/module_host.zi", "droid/app/build.gradle",
                     "CHANGELOG.md", "apps/publishers.json"):
            with self.subTest(path=path):
                self.assertTrue(triggered("release.yml", path))


if __name__ == "__main__":
    unittest.main()
