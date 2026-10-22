"""The release gate accepts only a passing phone check of the released app content."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_phone_check", ROOT / "scripts/check-phone-check.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
phone_check = gate.phone_check

RECEIPT = {
    "schema": 2, "version": "3.0.0", "app_tree": "", "source_commit": "", "uncommitted": [],
    "apk": {"sha256": "0" * 64, "package": "xyz.waozi.inbe.debug", "version_code": 300, "version_name": "3.0.0"},
    "device": {"model": "moto e6 play", "android": "9"},
    "practice": {"name": "Wim Hof", "seconds": 60.0, "frames": 3580, "refresh_hz": 60.0, "fps": 59.6,
                 "late_percent": 0.4, "p95_frame_ms": 16.9, "worst_frame_ms": 41.2,
                 "resume_layout_shift": 0.4},
    "passed": True,
}


class PhoneCheckGateTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="inbe-phone-gate-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.commit({"src/main.zi": "one\n", "src/core/version.zi": "VersionString :: \"2.9.9\"\n",
                     "scripts/build-cells.sh": "build\n", "scripts/check-version.py": "check\n",
                     "CHANGELOG.md": "## [3.0.0]\n"})
        self.checked = self.git("rev-parse", "HEAD").strip()
        self.checked_app = phone_check.app_tree(self.root, "HEAD")

    def git(self, *argv):
        return subprocess.run(["git", "-C", str(self.root), *argv], check=True, capture_output=True,
                              text=True).stdout

    def write(self, files):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def commit(self, files, message="change"):
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def receipt(self, change=None):
        receipt = copy.deepcopy(RECEIPT)
        receipt["source_commit"] = self.checked
        receipt["app_tree"] = self.checked_app
        if change:
            change(receipt)
        return json.dumps(receipt)

    def record(self, change=None):
        self.commit({"releases/phone-checks/3.0.0.json": self.receipt(change)})

    def test_passing_check_of_the_released_app(self):
        self.record()
        self.assertEqual(gate.validate(self.root, "3.0.0")["version"], "3.0.0")

    def test_docs_tests_and_tooling_may_change_after_the_check(self):
        self.record()
        later = {"docs/notes.md": "later documentation\n", "tests/extra.py": "\n",
                 "scripts/check-version.py": "stricter check\n", "scripts/web-smoke-test.mjs": "\n",
                 "scripts/release.py": "\n", ".github/workflows/ci.yml": "\n", "mk/tests-ui.mk": "\n",
                 "CHANGELOG.md": "## [3.0.0]\n- shorter store notes\n", "TODO.md": "\n"}
        for name, text in later.items():
            with self.subTest(path=name):
                self.commit({name: text})
                self.assertEqual(gate.validate(self.root, "3.0.0")["version"], "3.0.0")

    def test_app_changed_after_the_check(self):
        self.record()
        for name in ("src/main.zi", "ziran.lock", "droid/app/build.gradle", "Makefile", "mk/sync.mk",
                     "scripts/build-cells.sh", "scripts/new-generator.py", "assets/app/icon.png",
                     "locales/pt.txt", "apps/diary/diary.zi", "design/tai-chi/text/en.txt"):
            with self.subTest(path=name):
                self.commit({name: "changed " + name + "\n"})
                with self.assertRaisesRegex(ValueError, "changed after its phone check"):
                    gate.validate(self.root, "3.0.0")

    def test_the_checked_content_counts_not_the_commit(self):
        # One final release commit may replace an earlier unpushed one: the
        # checked commit is then no longer an ancestor, but its app content is.
        self.commit({"src/main.zi": "two\n"})
        self.commit({"src/main.zi": "one\n"}, "revert to the checked content")
        self.record(lambda value: value.update(source_commit="1" * 40))
        self.assertEqual(gate.validate(self.root, "3.0.0")["version"], "3.0.0")

    def test_uncommitted_version_files_check_the_commit_that_holds_them(self):
        self.write({"src/core/version.zi": "VersionString :: \"3.0.0\"\n"})
        on_disk = phone_check.app_tree(self.root)
        self.assertNotEqual(on_disk, self.checked_app)
        self.commit({"releases/phone-checks/3.0.0.json":
                     self.receipt(lambda value: value.update(app_tree=on_disk))})
        self.assertEqual(phone_check.app_tree(self.root, "HEAD"), on_disk)
        self.assertEqual(gate.validate(self.root, "3.0.0")["version"], "3.0.0")

    def test_untracked_app_files_are_reported(self):
        self.write({"src/cells/new.zi": "draft\n", "docs/draft.md": "draft\n"})
        changed, untracked = phone_check.changed_app_files(self.root)
        self.assertEqual((changed, untracked), ([], ["src/cells/new.zi"]))

    def test_missing_check(self):
        with self.assertRaisesRegex(ValueError, "no phone check"):
            gate.validate(self.root, "3.0.0")

    def test_explicit_owner_waiver_is_bound_to_the_version_and_app(self):
        waiver = {"schema": 3, "status": "waived", "version": "3.0.0",
                  "app_tree": self.checked_app, "reason": "Owner explicitly waived the Moto check"}
        target = "releases/phone-checks/3.0.0.json"
        self.commit({target: json.dumps(waiver)})
        self.assertEqual(gate.validate(self.root, "3.0.0")["status"], "waived")
        for changes in ({"version": "3.0.1"}, {"app_tree": "0" * 64}, {"reason": " "},
                        {"passed": True}, {"practice": {"fps": 60}}):
            with self.subTest(changes=changes):
                self.commit({target: json.dumps(waiver | changes)})
                with self.assertRaises(ValueError):
                    gate.validate(self.root, "3.0.0")

    def test_failed_or_mismatched_checks(self):
        cases = {
            "slow": lambda value: value["practice"].update(fps=41.0),
            "late frames": lambda value: value["practice"].update(late_percent=9.0),
            "long stall": lambda value: value["practice"].update(worst_frame_ms=600.0),
            "short run": lambda value: value["practice"].update(seconds=20.0),
            "shifted after resume": lambda value: value["practice"].update(resume_layout_shift=11.4),
            "resume not checked": lambda value: value["practice"].pop("resume_layout_shift"),
            "marked failed": lambda value: value.update(passed=False),
            "other version": lambda value: value.update(version="2.9.9"),
            "other APK": lambda value: value["apk"].update(version_name="2.9.9"),
            "old schema": lambda value: value.update(schema=1),
            "no app content": lambda value: value.pop("app_tree"),
            "other app content": lambda value: value.update(app_tree="1" * 64),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                self.record(change)
                with self.assertRaises(ValueError):
                    gate.validate(self.root, "3.0.0")


if __name__ == "__main__":
    unittest.main()
