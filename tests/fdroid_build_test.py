"""Guard the isolated source scanner and the pre-publication release gate."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FDroidBuildTest(unittest.TestCase):
    def test_thinlto_builds_match_across_checkout_locations(self):
        sdk = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
                   or Path.home() / "Android/Sdk")
        clang = sdk / "ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"
        if not clang.is_file():
            self.skipTest("Android NDK 28.2.13676358 is not installed")

        with tempfile.TemporaryDirectory(prefix="inbe-thinlto-repro-") as temporary:
            binaries = []
            for name in ("release", "different-fdroid-checkout"):
                root = Path(temporary) / name
                source = root / "src"
                build = root / "build"
                source.mkdir(parents=True)
                build.mkdir()
                (source / "shared.h").write_text("int external(int);\n")
                (source / "one.c").write_text(
                    '#include "shared.h"\n'
                    'static int lookup[8] = {1, 3, 5, 7, 9, 11, 13, 15};\n'
                    '__attribute__((noinline)) static int local(int x) {\n'
                    '    return lookup[x & 7];\n'
                    '}\n'
                    'int external(int x) { return local(x) + local(x + 1); }\n')
                (source / "two.c").write_text(
                    '#include "shared.h"\n'
                    'int api(int x) { return external(x) + external(x + 2); }\n')
                objects = []
                for stem in ("one", "two"):
                    target = build / f"{stem}.o"
                    objects.append(str(target))
                    subprocess.run([
                        sys.executable, str(ROOT / "scripts/relative-compile.py"), str(clang),
                        "--target=i686-none-linux-android21", "-Oz", "-g1", "-fPIC",
                        "-fdebug-compilation-dir=.", f"-ffile-prefix-map={root}=.",
                        "-flto=thin", "-c", str(source / f"{stem}.c"), "-o", str(target),
                    ], cwd=build, check=True, capture_output=True)
                target = build / "libtest.so"
                subprocess.run([
                    str(clang), "--target=i686-none-linux-android21", "-fuse-ld=lld",
                    "-flto=thin", "-nostdlib", "-shared", "-Wl,--build-id=sha1",
                    *objects, "-o", str(target),
                ], cwd=build, check=True, capture_output=True)
                binaries.append(target.read_bytes())
            # Compare the unstripped libraries, including build IDs and crash
            # symbols. Stripping or ignoring the identifier would hide the bug.
            self.assertEqual(binaries[0], binaries[1])

    def test_refuses_the_owner_checkout_even_with_ci_environment(self):
        for actions in ("false", "true"):
            with self.subTest(actions=actions):
                result = subprocess.run(
                    ["python3", "scripts/check-fdroid.py"], cwd=ROOT,
                    env=os.environ | {"GITHUB_ACTIONS": actions},
                    text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Refusing to reset an ordinary checkout", result.stderr)

    def test_recipe_keeps_source_scanning_and_the_store_variant(self):
        recipe = json.loads((ROOT / "packaging/fdroid-build.json").read_text())
        self.assertEqual(recipe["gradleprops"], ["fDroidBuild=true"])
        self.assertEqual(recipe["gradle"], ["yes"])
        self.assertEqual(recipe["output"],
                         "build/outputs/apk/release/app-universal-release-unsigned.apk")
        self.assertNotIn("scanignore", recipe)
        self.assertEqual(recipe["scandelete"],
                         ["build/ziran-bootstrap", "site/static/assets-sqljs-1.12.0"])

    def test_release_waits_for_independent_signature_verification(self):
        # Inspect the actual publication job, rather than a parallel CI result
        # that could stay red while the release still publishes.
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        release = workflow.split("\n  release:\n", 1)[1].split("\n    outputs:", 1)[0]
        self.assertIn("      - verify-fdroid", release.splitlines())
        verifier = workflow.split("\n  verify-fdroid:\n", 1)[1].split("\n  build-web:\n", 1)[0]
        dependencies = re.search(r"needs: \[([^]]+)\]", verifier)[1].split(",")
        self.assertTrue({"fdroid", "build-android"} <= {value.strip() for value in dependencies})
        self.assertIn("apksigcopier compare --unsigned", verifier)
        self.assertIn("apksigner verify --print-certs", verifier)


if __name__ == "__main__":
    unittest.main()
