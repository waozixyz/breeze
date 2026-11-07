"""Exercise the real build wrappers with a fake container, without a checkout or device."""
import importlib.util
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_layout", ROOT / "scripts/check-build-layout.py")
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class BuildLayoutTest(unittest.TestCase):
    def setUp(self):
        # Only fixtures and fake output are removed, never the project's build/.
        parent = ROOT / "backup/build-layout-tests"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scripts").mkdir()
        (self.root / "bin").mkdir()
        (self.root / "server").mkdir()
        for name in ("release-ready.sh", "check-build-layout.py", "phone-install.sh"):
            shutil.copyfile(ROOT / "scripts" / name, self.root / "scripts" / name)
        (self.root / "scripts/phone-check.py").write_text(
            "ROOT = None\ndef release_content(root, commit):\n    return commit\n")
        (self.root / "scripts/check-release-overlay.py").write_text("# snapshot fixture\n")
        self.executable("git", '''#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
if args[0] == '-C':
    args = args[2:]
if args[0] == 'rev-parse':
    print(args[1].split('^')[0])
elif args[0] == 'show':
    print(os.environ.get('FIXTURE_WINDOWS_INPUT', 'windows-v1') if args[1].endswith('.github/apt/windows-packages.txt') else 'fixed image inputs')
elif args[0] == 'log':
    print('fixture revision')
elif args[0] == 'archive':
    pathlib.Path(args[args.index('-o') + 1]).write_text('fixture image context')
elif args[0] != 'cat-file':
    raise SystemExit('unexpected git: ' + repr(args))
''')
        self.executable("podman", '''#!/usr/bin/env python3
import hashlib, json, os, pathlib, sys, time
args = sys.argv[1:]
if args[:2] == ['image', 'exists']:
    sys.exit(int(os.environ.get('FIXTURE_IMAGE_STATUS', '0')))
if args[0] in ('pull', 'provision'):
    with open('image-builds.jsonl', 'a') as stream:
        stream.write(json.dumps(args) + '\\n')
    sys.exit(0)
assert args[0] == 'run', args
mounts = [args[i+1] for i, value in enumerate(args) if value == '-v']
home = pathlib.Path(next(value.rsplit(':', 1)[0] for value in mounts
                         if value.endswith(':/home/ubuntu')))
output = pathlib.Path(next(value.rsplit(':', 1)[0] for value in mounts
                           if value.endswith(':/src/build')))
environment = dict(args[i+1].split('=', 1) for i, value in enumerate(args) if value == '-e')
commit = environment['RELEASE_READY_COMMIT']
cache = home / '.cache/ziran/sources'
cache.mkdir(parents=True, exist_ok=True)
# A shared source and a commit-specific source must coexist across runs.
shared = cache / 'shared'
reuse = shared.exists()
shared.write_text('same dependency')
identity = hashlib.sha256(('https://example.invalid/package\\n' + commit).encode()).hexdigest()
(cache / identity).write_text(commit)
record = dict(home=str(home), output=str(output), commit=commit, reuse=reuse,
              mounts=mounts, environment=environment, image=next(value for value in args if value.startswith('localhost/inbe-ci:')))
with open('runs.jsonl', 'a') as stream:
    stream.write(json.dumps(record) + '\\n')
if os.environ.get('FIXTURE_BLOCK'):
    pathlib.Path('entered').touch()
    deadline = time.monotonic() + 15
    while not pathlib.Path('continue').exists():
        assert time.monotonic() < deadline, 'fixture lease timed out'
        time.sleep(.02)
if not os.environ.get('FIXTURE_NO_APK'):
    (output / 'android').mkdir(exist_ok=True)
    (output / 'android/app-arm64-v8a-debug.apk').write_bytes(b'fixture apk')
sys.exit(int(os.environ.get('FIXTURE_STATUS', '0')))
''')
        # The CI image runs JavaScript with Bun; tests may replace this one.
        self.executable("bun", "#!/bin/sh\nexit 0\n")
        self.environment = dict(os.environ, PATH=str(self.root / "bin") + ":" + os.environ["PATH"],
                                RELEASE_READY_REVISION="1" * 40,
                                RELEASE_READY_DAOCHI_SOURCE=str(self.root / "server"),
                                PYTHONDONTWRITEBYTECODE="1")
        for name in ("RELEASE_READY_OUTPUT", "RELEASE_READY_INCREMENTAL", "RELEASE_READY_DNS",
                     "JS_RUNTIME", "JS_TEST_FLAGS", "ADDONS_LINTER"):
            self.environment.pop(name, None)

    def executable(self, name, text):
        path = self.root / "bin" / name
        path.write_text(text)
        path.chmod(0o755)

    def run_build(self, output="build/release-ready", revision=None, status=0, targets=("android-debug",)):
        environment = dict(self.environment, RELEASE_READY_OUTPUT=output, FIXTURE_STATUS=str(status))
        if revision:
            environment["RELEASE_READY_REVISION"] = revision
        return subprocess.run(["sh", "scripts/release-ready.sh", *targets], cwd=self.root,
                              env=environment, capture_output=True, text=True, timeout=10)

    def records(self):
        path = self.root / "runs.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_bun_runtime_reaches_all_container_jobs(self):
        self.executable("bun", "#!/bin/sh\nprintf 'fixture Bun\\n'\n")
        self.environment["JS_RUNTIME"] = str(self.root / "bin/bun")
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = self.records()[0]
        environment = record["environment"]
        self.assertEqual(environment["JS_RUNTIME"], "/opt/js-runtime/bun")
        self.assertEqual(environment["JS_TEST_FLAGS"], "test")
        self.assertEqual(environment["ADDONS_LINTER"], "/opt/js-runtime/bun x --bun addons-linter")
        self.assertEqual(environment["EM_NODE_JS"], "/opt/js-runtime/bun")
        self.assertEqual(environment["EMSDK_NODE"], "/opt/js-runtime/bun")
        runtime = self.root / "build/release-ready/js-runtime/bun"
        self.assertEqual(runtime.read_bytes(), (self.root / "bin/bun").read_bytes())
        self.assertIn(str(runtime.parent) + ":/opt/js-runtime:ro", record["mounts"])

    def test_bun_preserves_explicit_test_flags_and_linter(self):
        self.executable("bun", "#!/bin/sh\nexit 0\n")
        self.environment.update(JS_RUNTIME=str(self.root / "bin/bun"),
                                JS_TEST_FLAGS="test --timeout 120000", ADDONS_LINTER="reviewed-linter")
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        environment = self.records()[0]["environment"]
        self.assertEqual(environment["JS_TEST_FLAGS"], "test --timeout 120000")
        self.assertEqual(environment["ADDONS_LINTER"], "reviewed-linter")

    def test_missing_image_is_provisioned_from_hashed_candidate_inputs(self):
        self.environment["FIXTURE_IMAGE_STATUS"] = "1"
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pull, provision = [json.loads(line) for line in
                           (self.root / "image-builds.jsonl").read_text().splitlines()]
        # The fixture's git show prints the same text for the base and the recipe.
        self.assertEqual(pull, ["pull", "fixed image inputs"])
        self.assertEqual(provision[:3], ["provision", "fixed image inputs", self.records()[0]["image"]])
        self.assertTrue(provision[2].endswith("-bun"), provision[2])
        folder = self.root / "build/release-ready/provision"
        self.assertEqual(provision[3], str(folder / "context.tar"))
        self.assertEqual(provision[4], hashlib.sha256(b"fixture image context").hexdigest())
        self.assertEqual(provision[5], str(folder / "provision.sh"))
        self.assertEqual(provision[6], hashlib.sha256(b"fixed image inputs\n").hexdigest())
        self.assertEqual(provision[7:], [
            "--env", "EM_NODE_JS=/usr/local/bin/bun", "--env", "EMSDK_NODE=/usr/local/bin/bun",
            "--env", "EM_CONFIG=/opt/emsdk/.emscripten",
            "--env", "PATH=/opt/emsdk/upstream/emscripten:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin"])
        self.assertEqual(self.records()[0]["environment"]["JS_RUNTIME"], "/opt/js-runtime/bun")

    def test_release_ready_refuses_without_bun(self):
        (self.root / "bin/bun").unlink()
        (self.root / "empty-home").mkdir()
        self.environment.update(PATH=str(self.root / "bin") + ":/usr/bin:/bin",
                                HOME=str(self.root / "empty-home"))
        result = self.run_build()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Bun", result.stderr)
        self.assertFalse(self.records())

    def test_windows_package_list_is_part_of_the_image_fingerprint(self):
        first = self.run_build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.environment["FIXTURE_WINDOWS_INPUT"] = "windows-v2"
        second = self.run_build()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        records = self.records()
        self.assertNotEqual(records[0]["image"], records[1]["image"])

    def test_container_query_failure_does_not_claim_a_missing_image(self):
        self.environment["FIXTURE_IMAGE_STATUS"] = "125"
        result = self.run_build()
        self.assertEqual(result.returncode, 125, result.stdout + result.stderr)
        self.assertIn("container engine could not inspect", result.stderr)
        self.assertFalse(self.records())

    def test_two_names_and_commits_share_cache_and_one_output(self):
        for name, revision in (("build/release-ready-61-apk", "1" * 40),
                               ("build/release-ready-62b", "2" * 40)):
            result = self.run_build(name, revision)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((self.root / name).exists())
        first, second = self.records()
        self.assertEqual(first["home"], second["home"])
        self.assertEqual(first["output"], second["output"])
        self.assertFalse(first["reuse"])
        self.assertTrue(second["reuse"])
        cache = Path(first["home"]) / ".cache/ziran/sources"
        self.assertEqual(len(list(cache.iterdir())), 3)
        self.assertEqual({p.name for p in (self.root / "build").iterdir()},
                         {"release-ready"})
        self.assertEqual(Path(first["home"]), self.root / "build/release-ready/home")
        self.assertTrue((self.root / "build/release-ready/build/android/app-arm64-v8a-debug.apk").is_file())

    def test_phone_has_stable_output_and_the_same_home(self):
        self.assertEqual(self.run_build().returncode, 0)
        result = self.run_build("build/release-ready-phone", "2" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = self.records()
        self.assertNotEqual(first["output"], second["output"])
        self.assertEqual(first["home"], second["home"])
        self.assertTrue(second["reuse"])
        self.assertEqual(second["environment"]["XDG_CACHE_HOME"], "/home/ubuntu/.cache")
        self.assertEqual(second["environment"]["GRADLE_USER_HOME"], "/home/ubuntu/.gradle")

    def test_full_run_stamp_uses_the_same_mapping_as_the_release_gate(self):
        alias = "build/release-ready-release61"
        result = self.run_build(alias, targets=())
        self.assertEqual(result.returncode, 0, result.stderr)
        stamp = self.root / layout.release_ready_output(alias) / "stamp.json"
        self.assertTrue(json.loads(stamp.read_text())["passed"])
        self.assertFalse((self.root / alias).exists())
        environment = dict(self.environment, RELEASE_READY_OUTPUT=alias)
        script = ("import importlib.util; "
                  "s=importlib.util.spec_from_file_location('release', 'scripts/release.py'); "
                  "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.READY_OUTPUT)")
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=environment,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "build/release-ready")

    def start_blocked(self):
        process = subprocess.Popen(["sh", "scripts/release-ready.sh", "android-debug"], cwd=self.root,
                                   env=dict(self.environment, FIXTURE_BLOCK="1"),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.finish_process, process)
        self.wait_for(lambda: (self.root / "entered").exists())
        return process

    def finish_process(self, process):
        (self.root / "continue").touch()
        process.communicate(timeout=20)

    def wait_for(self, condition):
        deadline = time.monotonic() + 5
        while not condition():
            self.assertLess(time.monotonic(), deadline, "fixture did not reach expected state")
            time.sleep(.02)

    def test_active_output_is_not_changed_and_cache_users_are_serialized(self):
        first = self.start_blocked()
        with (self.root / "build/release-ready/cache.lock").open("a") as lease:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stamp = self.root / "build/release-ready/stamp.json"
        stamp.write_text("active run's file")
        result = self.run_build("build/release-ready-another-task")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another run is using", result.stderr)
        self.assertEqual(stamp.read_text(), "active run's file")
        second = subprocess.Popen(["sh", "scripts/release-ready.sh", "android-debug"], cwd=self.root,
                                  env=dict(self.environment, RELEASE_READY_OUTPUT="build/release-ready-phone"),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.finish_process, second)
        # The second process owns its output lease before waiting on the cache.
        self.wait_for(lambda: (self.root / "build/release-ready-phone/lock").exists())
        self.assertIsNone(second.poll())
        self.assertEqual(len(self.records()), 1)
        (self.root / "continue").touch()
        for process in (first, second):
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(len(self.records()), 2)
        self.assertTrue(self.records()[1]["reuse"])

    def test_failed_build_releases_leases_and_invalidates_old_stamp(self):
        self.assertEqual(self.run_build(targets=()).returncode, 0)
        result = self.run_build(status=7)
        self.assertEqual(result.returncode, 7)
        self.assertFalse((self.root / "build/release-ready/stamp.json").exists())
        self.assertEqual(self.run_build().returncode, 0)

    def test_unrelated_outputs_and_old_folders_are_never_pruned(self):
        paths = ("build/promo-video", "build/package-releases", "build/dist", "build/release-ready-old")
        for name in paths:
            path = self.root / name
            path.mkdir(parents=True)
            (path / "keep").write_text("owner data")
        self.assertEqual(self.run_build().returncode, 0)
        for name in paths:
            self.assertEqual((self.root / name / "keep").read_text(), "owner data")
        for name in ("build/promo-video", "build/package-releases", "build/dist",
                     "build/release-ready-../promo-video", "build/release-ready-foo/bar"):
            result = self.run_build(name)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_symlink_output_is_refused_without_touching_target(self):
        target = self.root / "build/promo-video"
        target.mkdir(parents=True)
        (target / "keep").write_text("owner data")
        (self.root / "build/release-ready").symlink_to(target, target_is_directory=True)
        result = self.run_build()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list(target.iterdir()), [target / "keep"])
        self.assertEqual(self.records(), [])

    def test_phone_default_build_and_versioned_apks_reuse_signing_output(self):
        # Only these fixture executables are on the phone script's PATH.
        self.executable("adb", '''#!/usr/bin/env python3
import hashlib, pathlib, sys
args = sys.argv[3:]
if args == ['get-state']:
    print('device')
elif args == ['shell', 'getprop', 'ro.product.cpu.abi']:
    print('arm64-v8a')
elif args == ['shell', 'getprop', 'ro.product.model']:
    print('Fixture')
elif args[:3] == ['shell', 'pm', 'path']:
    print('package:/fixture/base.apk')
elif args[:2] == ['shell', 'sha256sum']:
    data = pathlib.Path('build/phone-install/app-arm64-v8a-debug-signed.apk').read_bytes()
    print(hashlib.sha256(data).hexdigest(), '/fixture/base.apk')
elif args[:2] not in (['install', '-r'], ['shell', 'am'], ['shell', 'pidof']):
    raise SystemExit('unexpected adb: ' + repr(args))
''')
        sdk = self.root / "sdk/build-tools/1"
        sdk.mkdir(parents=True)
        for name, source in {
            "zipalign": "import shutil, sys; shutil.copyfile(sys.argv[-2], sys.argv[-1])",
            "apksigner": ("import shutil, sys; "
                          "sys.exit(0) if sys.argv[1] == 'verify' else "
                          "shutil.copyfile(sys.argv[-1], sys.argv[sys.argv.index('--out')+1])"),
        }.items():
            path = sdk / name
            path.write_text("#!/usr/bin/env python3\n" + source + "\n")
            path.chmod(0o755)
        key = self.root / "debug.keystore"
        key.touch()
        environment = dict(self.environment, ANDROID_SDK_ROOT=str(self.root / "sdk"),
                           ANDROID_DEBUG_KEYSTORE=str(key))

        def install(*arguments):
            result = subprocess.run(["sh", "scripts/phone-install.sh", "--device", "fixture", *arguments],
                                    cwd=self.root, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        install()
        record = self.records()[0]
        self.assertEqual(Path(record["output"]), self.root / "build/release-ready-phone/build")
        for version in ("61", "62"):
            apk = self.root / ("inbe-" + version + ".apk")
            apk.write_bytes(version.encode())
            install("--apk", str(apk))
        self.assertEqual([p.name for p in (self.root / "build/phone-install").iterdir()],
                         ["app-arm64-v8a-debug-signed.apk"])
        signed = self.root / "build/phone-install/app-arm64-v8a-debug-signed.apk"
        self.assertEqual(signed.read_bytes(), b"62")
        failed = subprocess.run(["sh", "scripts/phone-install.sh", "--device", "fixture"],
                                cwd=self.root, env=dict(environment, FIXTURE_STATUS="9"),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(failed.returncode, 9, failed.stdout + failed.stderr)
        self.assertNotIn("phone-install: installed", failed.stdout)
        self.assertEqual(signed.read_bytes(), b"62")
        stale = subprocess.run(["sh", "scripts/phone-install.sh", "--device", "fixture"],
                               cwd=self.root, env=dict(environment, FIXTURE_NO_APK="1"),
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(stale.returncode, 1, stale.stdout + stale.stderr)
        self.assertIn("the build left no", stale.stderr)
        self.assertNotIn("phone-install: installed", stale.stdout)
        self.assertEqual(signed.read_bytes(), b"62")


if __name__ == "__main__":
    unittest.main()
