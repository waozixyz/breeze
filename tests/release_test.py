"""make release keeps one unpushed release commit and checks what CI will build."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def git(root, *argv):
    return subprocess.run(["git", "-C", str(root), *argv], check=True, capture_output=True,
                          text=True).stdout


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="inbe-release-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.origin = base / "origin.git"
        self.root = base / "inbe"
        git(base, "init", "-q", "--bare", "-b", "master", str(self.origin))
        git(base, "init", "-q", "-b", "master", str(self.root))
        for key, value in (("user.email", "test@example.invalid"), ("user.name", "Test")):
            git(self.root, "config", key, value)
        git(self.root, "remote", "add", "origin", str(self.origin))
        self.commit({"src/main.zi": "one\n", "src/core/version.zi": "2.9.9\n", "docs/notes.md": "notes\n"},
                    "Start")
        git(self.root, "push", "-q", "origin", "master")
        git(self.root, "fetch", "-q", "origin")
        self.previous_root = release.ROOT
        release.ROOT = self.root
        self.addCleanup(setattr, release, "ROOT", self.previous_root)

    def commit(self, files, message):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            git(self.root, "add", name)
        git(self.root, "commit", "-q", "-m", message)
        return git(self.root, "rev-parse", "HEAD").strip()

    def subjects(self):
        return git(self.root, "log", "--format=%s").splitlines()

    def release_commit(self, receipt="{}\n"):
        return self.commit({"src/core/version.zi": "3.0.0\n",
                            "releases/phone-checks/3.0.0.json": receipt}, "Release Inner Breeze 3.0.0")

    def test_a_buried_release_commit_moves_to_the_top(self):
        old = self.release_commit()
        self.commit({"src/fix.zi": "late fix\n"}, "Fix a late bug")
        (self.root / "docs/notes.md").write_text("another session's work\n")
        tree = git(self.root, "rev-parse", "HEAD^{tree}")
        self.assertEqual(release.unpushed_release("3.0.0"), old)
        self.assertFalse(release.release_at_head("3.0.0"))

        release.move_to_top(old, "3.0.0")

        self.assertEqual(self.subjects(), ["Release Inner Breeze 3.0.0", "Fix a late bug", "Start"])
        self.assertEqual(git(self.root, "rev-parse", "HEAD^{tree}"), tree)
        self.assertEqual(git(self.root, "show", "--format=", "--name-only", "HEAD").split(),
                         ["releases/phone-checks/3.0.0.json", "src/core/version.zi"])
        self.assertEqual(git(self.root, "show", "HEAD~1:src/core/version.zi"), "2.9.9\n")
        self.assertEqual(git(self.root, "status", "--porcelain"), " M docs/notes.md\n")
        self.assertTrue(release.release_at_head("3.0.0"))

    def test_a_pushed_release_commit_never_moves(self):
        old = self.release_commit()
        git(self.root, "push", "-q", "origin", "master")
        self.commit({"src/fix.zi": "late fix\n"}, "Fix a late bug")
        head = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(release.Refused, "already pushed"):
            release.move_to_top(old, "3.0.0")
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), head)

    def test_later_changes_to_its_files_keep_the_history(self):
        old = self.release_commit()
        self.commit({"src/core/version.zi": "3.0.1\n"}, "Change the version again")
        head = git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(release.Refused, "cannot move"):
            release.move_to_top(old, "3.0.0")
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), head)

    def test_one_release_commit_at_most(self):
        self.release_commit()
        self.release_commit('{"passed": true}\n')
        with self.assertRaisesRegex(release.Refused, "several"):
            release.unpushed_release("3.0.0")

    def test_the_release_commit_takes_only_version_files(self):
        files = ["droid/app/build.gradle", "src/core/version.zi", "packaging/snap/snap/snapcraft.yaml",
                 "fastlane/metadata/android/en-US/changelogs/173.txt", "apps/diary/CHANGELOG.md",
                 "apps/versions.json", "src/cells/versions.zi"]
        stray = ["src/screens/diary_screen.zi", "locales/pt.txt", "apps/diary/diary.zi"]
        allowed = [path for path in files + stray
                   if any(release.fnmatch.fnmatchcase(path, pattern) for pattern in release.VERSION_FILES)]
        self.assertEqual(allowed, files)

    def test_package_overrides_must_sit_clean_on_the_lock(self):
        package = self.root.parent / "kryon"
        git(self.root.parent, "init", "-q", str(package))
        for key, value in (("user.email", "test@example.invalid"), ("user.name", "Test")):
            git(package, "config", key, value)
        (package / "ui.zi").write_text("one\n")
        git(package, "add", "ui.zi")
        git(package, "commit", "-q", "-m", "one")
        locked = git(package, "rev-parse", "HEAD").strip()
        (self.root / "ziran.lock").write_text(json.dumps(
            {"format": 1, "packages": [{"name": "kryon", "commit": locked}]}))
        (self.root / "ziran.local.toml").write_text('[overrides]\nKryon = "../kryon"\n')
        release.require_locked_overrides()

        (package / "ui.zi").write_text("work in progress\n")
        with self.assertRaisesRegex(release.Refused, "uncommitted changes"):
            release.require_locked_overrides()
        git(package, "commit", "-q", "-am", "two")
        with self.assertRaisesRegex(release.Refused, "the lock pins"):
            release.require_locked_overrides()


if __name__ == "__main__":
    unittest.main()
