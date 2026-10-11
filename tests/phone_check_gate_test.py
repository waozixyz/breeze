"""The release gate accepts only a passing phone check of the released sources."""
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

RECEIPT = {
    "schema": 1, "version": "3.0.0", "source_commit": "",
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
        self.commit({"src/main.zi": "one\n"})
        self.checked = self.git("rev-parse", "HEAD").strip()

    def git(self, *argv):
        return subprocess.run(["git", "-C", str(self.root), *argv], check=True, capture_output=True,
                              text=True).stdout

    def commit(self, files):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")

    def record(self, change=None):
        receipt = copy.deepcopy(RECEIPT)
        receipt["source_commit"] = self.checked
        if change:
            change(receipt)
        self.commit({"releases/phone-checks/3.0.0.json": json.dumps(receipt)})

    def test_passing_check_of_the_released_sources(self):
        self.record()
        self.commit({"docs/notes.md": "later documentation\n", "tests/extra.py": "\n"})
        self.assertEqual(gate.validate(self.root, "3.0.0")["version"], "3.0.0")

    def test_missing_check(self):
        with self.assertRaisesRegex(ValueError, "no phone check"):
            gate.validate(self.root, "3.0.0")

    def test_app_changed_after_the_check(self):
        self.record()
        for name in ("src/main.zi", "ziran.lock", "droid/app/build.gradle", "CHANGELOG.md"):
            with self.subTest(path=name):
                self.commit({name: "changed " + name + "\n"})
                with self.assertRaisesRegex(ValueError, "changed after its phone check"):
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
            "short commit": lambda value: value.update(source_commit=value["source_commit"][:12]),
            "unknown commit": lambda value: value.update(source_commit="1" * 40),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                self.record(change)
                with self.assertRaises(ValueError):
                    gate.validate(self.root, "3.0.0")


if __name__ == "__main__":
    unittest.main()
