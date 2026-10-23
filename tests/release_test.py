"""make release keeps one unpushed release commit and checks what CI will build."""
import importlib.util
import ast
import contextlib
import io
import json
import os
import re
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


class ReleaseArtifactReuseTest(unittest.TestCase):
    def setUp(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        section = workflow.split("      - name: Verify identical source and every gate before reusing artifacts\n", 1)[1]
        script = section.split("          python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        self.script = "\n".join(line[10:] for line in script.splitlines())
        tree = ast.parse(self.script)
        self.required = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                             if isinstance(node, ast.Assign) and any(
                                 isinstance(target, ast.Name) and target.id == "required"
                                 for target in node.targets))
        self.workflow = workflow

    def evaluate(self, *, jobs=None, changed=None, run_changes=None, source_receipt=False,
                 ancestor=True, phone_passes=True, run_id="123"):
        source = "1" * 40
        candidate = "2" * 40
        run = {"path": ".github/workflows/release.yml", "event": "push", "head_branch": "master",
               "repository": {"full_name": "waozixyz/inbe"}, "head_sha": source}
        run.update(run_changes or {})
        if jobs is None:
            jobs = [{"name": name, "status": "completed", "conclusion": "success"}
                    for name in sorted(self.required)]
        if changed is None:
            changed = ["releases/phone-checks/3.0.0.json"]

        def read(command, **kwargs):
            if command[:2] == ["gh", "api"]:
                return json.dumps({"jobs": jobs} if command[-1].endswith("/jobs?per_page=100") else run)
            if command[:2] == ["git", "diff"]:
                self.assertEqual(command[-2:], [source, candidate])
                return "\n".join(changed) + "\n"
            if command == ["python3", "scripts/check-version.py", "--print-version"]:
                return "3.0.0\n"
            self.fail("Unexpected read: " + repr(command))

        def check(command, **kwargs):
            if command[:2] == ["git", "merge-base"]:
                self.assertEqual(command[-2:], [source, candidate])
                if not ancestor:
                    raise subprocess.CalledProcessError(1, command)
            elif command[:2] == ["git", "cat-file"]:
                self.assertEqual(command[-1], source + ":releases/phone-checks/3.0.0.json")
                return subprocess.CompletedProcess(command, 0 if source_receipt else 1)
            elif command[:2] == ["python3", "scripts/check-phone-check.py"]:
                self.assertEqual(command[-2:], ["--revision", candidate])
                if not phone_passes:
                    raise subprocess.CalledProcessError(1, command)
            else:
                self.fail("Unexpected command: " + repr(command))
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory(prefix="inbe-reuse-gate-") as temporary:
            output = Path(temporary) / "output"
            environment = {"VERIFIED_RUN": run_id, "CANDIDATE": candidate,
                           "GITHUB_REPOSITORY": "waozixyz/inbe", "GITHUB_OUTPUT": str(output)}
            with mock.patch.dict(os.environ, environment), \
                    mock.patch("subprocess.check_output", side_effect=read) as reads, \
                    mock.patch("subprocess.run", side_effect=check) as commands, \
                    contextlib.redirect_stdout(io.StringIO()):
                try:
                    exec(compile(self.script, "release artifact reuse", "exec"), {})
                except SystemExit as error:
                    if error.code != 0:
                        raise
                if not run_id:
                    reads.assert_not_called()
                    commands.assert_not_called()
                return output.read_text()

    def test_receipt_only_candidate_reuses_every_passing_platform(self):
        self.assertEqual(self.evaluate(), "reuse_artifacts=true\n")

    def test_normal_build_does_not_need_a_previous_run(self):
        self.assertEqual(self.evaluate(run_id=""), "reuse_artifacts=false\n")

    def test_missing_failed_skipped_cancelled_or_duplicate_gates_are_rejected(self):
        jobs = [{"name": name, "status": "completed", "conclusion": "success"}
                for name in sorted(self.required)]
        for index in range(len(jobs)):
            with self.subTest(job=jobs[index]["name"], state="missing"), self.assertRaises(SystemExit):
                self.evaluate(jobs=jobs[:index] + jobs[index + 1:])
            for state in ("failure", "cancelled", "skipped", None):
                damaged = [dict(job) for job in jobs]
                damaged[index]["conclusion"] = state
                with self.subTest(job=jobs[index]["name"], state=state), self.assertRaises(SystemExit):
                    self.evaluate(jobs=damaged)
            with self.subTest(job=jobs[index]["name"], state="duplicate"), self.assertRaises(SystemExit):
                self.evaluate(jobs=jobs + [jobs[index]])
            damaged = [dict(job) for job in jobs]
            damaged[index]["status"] = "in_progress"
            with self.subTest(job=jobs[index]["name"], state="unfinished"), self.assertRaises(SystemExit):
                self.evaluate(jobs=damaged)

    def test_changed_application_tests_tooling_or_unrelated_source_are_rejected(self):
        for extra in ("src/main.zi", "ziran.lock", "droid/app/build.gradle", "tests/new_test.py",
                      ".github/workflows/release.yml", "CHANGELOG.md", "docs/notes.md"):
            with self.subTest(path=extra), self.assertRaises(SystemExit):
                self.evaluate(changed=["releases/phone-checks/3.0.0.json", extra])
        for changed in ([], ["releases/phone-checks/2.9.9.json"]):
            with self.subTest(changed=changed), self.assertRaises(SystemExit):
                self.evaluate(changed=changed)

    def test_wrong_repository_workflow_event_branch_or_run_is_rejected(self):
        for change in ({"repository": {"full_name": "elsewhere/inbe"}},
                       {"path": ".github/workflows/ci.yml"}, {"event": "workflow_dispatch"},
                       {"head_branch": "other"}, {"head_sha": "master"}):
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.evaluate(run_changes=change)
        for run_id in ("0", "123;echo", "master"):
            with self.subTest(run_id=run_id), self.assertRaises(SystemExit):
                self.evaluate(run_id=run_id)

    def test_invalid_phone_result_unrelated_history_and_existing_receipt_are_rejected(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.evaluate(phone_passes=False)
        with self.assertRaises(subprocess.CalledProcessError):
            self.evaluate(ancestor=False)
        with self.assertRaises(SystemExit):
            self.evaluate(source_receipt=True)

    def test_reuse_policy_covers_every_declared_build_and_reproducibility_gate(self):
        builds = set()
        for identifier, body in re.findall(r"^  (build-[a-z-]+):\n(.*?)(?=^  [a-z][a-z-]*:|\Z)",
                                           self.workflow, re.M | re.S):
            name = re.search(r"^    name: (.+)$", body, re.M)[1]
            matrix = re.findall(r"^\s+- arch: (.+)\n\s+runner: (.+)(?:\n\s+tool_arch: (.+))?", body, re.M)
            if matrix:
                builds.update(name + " (" + ", ".join(value for value in row if value) + ")" for row in matrix)
            else:
                builds.add(name)
            self.assertIn("if: needs.secret-scan.outputs.reuse_artifacts != 'true'", body)
        self.assertEqual({name for name in self.required if name.startswith("Build ")}, builds)
        self.assertTrue({"Secret Scan", "Visual Tests", "Test (0/3)", "Test (1/3)", "Test (2/3)",
                         "F-Droid / F-Droid security and clean build", "Verify F-Droid reproducibility"}
                        <= self.required)
        release_job = self.workflow.split("\n  release:\n", 1)[1].split("\n  notify-waozi-site:", 1)[0]
        for state in ("failure", "cancelled", "skipped"):
            self.assertIn("!contains(needs.*.result, '" + state + "')", release_job)
        for download in self.workflow.split("uses: actions/download-artifact@")[1:]:
            settings = download.split("\n      - name:", 1)[0]
            self.assertIn("run-id: ${{ inputs.reuse_run || github.run_id }}", settings)
            self.assertIn("github-token: ${{ github.token }}", settings)


if __name__ == "__main__":
    unittest.main()
