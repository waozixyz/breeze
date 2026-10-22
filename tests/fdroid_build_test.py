"""Guard the isolated source scanner and the pre-publication release gate."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FDroidBuildTest(unittest.TestCase):
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
        self.assertIn("needs: [fdroid, build-android]", verifier)
        self.assertIn("apksigcopier compare --unsigned", verifier)
        self.assertIn("apksigner verify --print-certs", verifier)


if __name__ == "__main__":
    unittest.main()
