"""make release keeps one unpushed release commit and checks what CI will build."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

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
        self.commit({".gitignore": "/build/\n", "src/main.zi": "one\n", "src/core/version.zi": "2.9.9\n", "docs/notes.md": "notes\n"},
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

    def test_late_release_notes_join_the_final_release_commit(self):
        note = "fastlane/metadata/android/en-US/changelogs/174.txt"
        old = self.commit({"src/core/version.zi": "3.0.0\n", "CHANGELOG.md": "First release note\n",
                           note: "First release note\n", "releases/phone-checks/3.0.0.json": "{}\n"},
                          "Release Inner Breeze 3.0.0")
        self.commit({"src/fix.zi": "late fix\n", "CHANGELOG.md": "The complete release notes\n",
                     note: "The complete release notes\n"}, "Fix a late bug and describe it")
        self.commit({note: "The complete, concise release notes\n"}, "Clarify the store notes")
        (self.root / "docs/notes.md").write_text("another session's work\n")
        tree = git(self.root, "rev-parse", "HEAD^{tree}")
        status = git(self.root, "status", "--porcelain")

        release.move_to_top(old, "3.0.0")

        self.assertEqual(self.subjects(), ["Release Inner Breeze 3.0.0", "Clarify the store notes",
                                          "Fix a late bug and describe it", "Start"])
        self.assertEqual(git(self.root, "rev-parse", "HEAD^{tree}"), tree)
        self.assertEqual(git(self.root, "status", "--porcelain"), status)
        self.assertEqual(git(self.root, "show", "HEAD:src/fix.zi"), "late fix\n")
        self.assertEqual(git(self.root, "show", "HEAD:" + note), "The complete, concise release notes\n")
        self.assertEqual(git(self.root, "ls-tree", "HEAD~1", "--", "CHANGELOG.md", note), "")
        self.assertEqual(git(self.root, "show", "HEAD~1:src/core/version.zi"), "2.9.9\n")
        self.assertTrue(release.release_at_head("3.0.0"))

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

    def test_a_new_receipt_commits_without_taking_other_staged_work(self):
        receipt = "releases/phone-checks/3.0.0.json"
        path = self.root / receipt
        path.parent.mkdir(parents=True)
        path.write_text('{"passed": true}\n')
        (self.root / "docs/notes.md").write_text("another session's work\n")
        git(self.root, "add", "docs/notes.md")

        release.commit_files([receipt], "3.0.0", amend=False)

        self.assertEqual(git(self.root, "show", "--format=", "--name-only", "HEAD").split(),
                         [receipt])
        self.assertEqual(git(self.root, "show", "HEAD:docs/notes.md"), "notes\n")
        self.assertEqual(git(self.root, "status", "--porcelain"), "M  docs/notes.md\n")

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

    def test_fixed_release_preserves_later_commits_and_staged_source(self):
        base = git(self.root, "rev-parse", "HEAD").strip()
        peer = self.commit({"src/main.zi": "peer committed\n"}, "Peer feature")
        (self.root / "src/main.zi").write_text("peer staged\n")
        git(self.root, "add", "src/main.zi")
        (self.root / "docs/notes.md").write_text("peer unfinished\n")
        receipt = self.root / "releases/phone-checks/3.0.0.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text('{"passed":true}\n')

        candidate = release.fixed_release_commit(base, "3.0.0", "Verified fixture")

        self.assertEqual(git(self.root, "show", candidate + ":src/main.zi"), "one\n")
        self.assertEqual(git(self.root, "show", "HEAD:src/main.zi"), "peer committed\n")
        self.assertEqual(git(self.root, "show", ":src/main.zi"), "peer staged\n")
        self.assertEqual((self.root / "src/main.zi").read_text(), "peer staged\n")
        self.assertEqual((self.root / "docs/notes.md").read_text(), "peer unfinished\n")
        self.assertEqual(git(self.root, "show", candidate + ":releases/phone-checks/3.0.0.json"),
                         receipt.read_text())
        self.assertEqual(git(self.root, "log", "-1", "--format=%P").split(), [peer, candidate])
        self.assertEqual(git(self.root, "log", "-1", "--format=%an <%ae>", candidate).strip(),
                         "Waozi <waozi@proton.me>")
        self.assertEqual(git(self.root, "status", "--porcelain"),
                         " M docs/notes.md\nM  src/main.zi\n")

    def test_fixed_release_appends_without_rewriting_history(self):
        base = git(self.root, "rev-parse", "HEAD").strip()
        receipt = self.root / "releases/phone-checks/3.0.0.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text('{"passed":true}\n')
        candidate = release.fixed_release_commit(base, "3.0.0", "Verified fixture")
        self.assertEqual(git(self.root, "rev-parse", "HEAD").strip(), candidate)
        self.assertEqual(git(self.root, "log", "-1", "--format=%P").strip(), base)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")


class MotoWorkflowGateTest(unittest.TestCase):
    def check_run(self, jobs, *, head=None, path=".github/workflows/release.yml"):
        workflow = (ROOT / ".github/workflows/android-moto.yml").read_text()
        script = workflow.split("          python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        script = "\n".join(line[10:] for line in script.splitlines())
        commit = "1" * 40
        run = {"head_sha": head or commit, "path": path}

        def response(command, **kwargs):
            self.assertEqual(command[:2], ["gh", "api"])
            value = {"jobs": jobs} if command[2].endswith("/jobs?per_page=100") else run
            return json.dumps(value)

        environment = {"SOURCE_COMMIT": commit, "VERIFIED_RUN": "123",
                       "GITHUB_REPOSITORY": "waozixyz/inbe"}
        with mock.patch.dict(os.environ, environment), \
                mock.patch("subprocess.check_output", side_effect=response), \
                contextlib.redirect_stdout(io.StringIO()):
            exec(compile(script, "android-moto gate", "exec"), {})

    def passing_jobs(self):
        return [{"name": name, "conclusion": "success"} for name in
                ("Secret Scan", "Test (0/3)", "Test (1/3)", "Test (2/3)", "Visual Tests")]

    def test_all_three_shards_allow_the_exact_release(self):
        self.check_run(self.passing_jobs())

    def test_missing_failed_cancelled_and_duplicate_checks_are_rejected(self):
        for index in range(len(self.passing_jobs())):
            with self.subTest(index=index, state="missing"), self.assertRaises(SystemExit):
                self.check_run(self.passing_jobs()[:index] + self.passing_jobs()[index + 1:])
            for state in ("failure", "cancelled", "skipped", None):
                jobs = self.passing_jobs()
                jobs[index]["conclusion"] = state
                with self.subTest(index=index, state=state), self.assertRaises(SystemExit):
                    self.check_run(jobs)
            jobs = self.passing_jobs()
            with self.subTest(index=index, state="duplicate"), self.assertRaises(SystemExit):
                self.check_run(jobs + [jobs[index]])

    def test_a_different_commit_or_workflow_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.check_run(self.passing_jobs(), head="2" * 40)
        with self.assertRaises(SystemExit):
            self.check_run(self.passing_jobs(), path=".github/workflows/ci.yml")


if __name__ == "__main__":
    unittest.main()
