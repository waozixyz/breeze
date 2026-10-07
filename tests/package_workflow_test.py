"""Execute the package workflow's configuration and publishing shell steps."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/packages.yml"


def script(name):
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index("      - name: " + name) + 1
    end = next((index for index in range(start, len(lines))
                if lines[index].startswith("      - ")), len(lines))
    block = lines[start:end]
    run = block.index("        run: |") + 1
    return textwrap.dedent("\n".join(block[run:])) + "\n"


class PackageWorkflowTest(unittest.TestCase):
    def test_private_node_configuration_is_masked_by_github(self):
        workflow = WORKFLOW.read_text()
        for name in ("INBE_NODE_KNOWN_HOSTS", "INBE_NODE_SSH_TARGET", "INBE_NODE_PACKAGE_STORE"):
            self.assertIn("secrets." + name, workflow)
            self.assertNotIn("vars." + name, workflow)

    def test_configuration_branches_and_private_files(self):
        cases = (({}, False, False),
                 ({"SIGNING_KEY": "test-private-key", "KEY_ID": "test"}, True, False),
                 ({"SIGNING_KEY": "test-private-key", "KEY_ID": "test",
                   "SSH_KEY": "test-ssh-key", "SSH_HOSTS": "test-host",
                   "TARGET": "test@example.invalid", "STORE": "/test/packages"}, True, True))
        for values, signing, configured in cases:
            with self.subTest(signing=signing, configured=configured), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                output = directory / "output"
                env = {key: value for key, value in os.environ.items()
                       if key not in ("SIGNING_KEY", "KEY_ID", "SSH_KEY", "SSH_HOSTS", "TARGET", "STORE")}
                env.update(values, RUNNER_TEMP=temporary, GITHUB_OUTPUT=str(output))
                result = subprocess.run(["bash", "-eu"], input=script("Configure publisher"),
                                        text=True, capture_output=True, env=env, check=True)
                self.assertEqual(result.stderr, "")
                self.assertNotIn("test-private-key", result.stdout)
                self.assertNotIn("test-ssh-key", result.stdout)
                self.assertEqual(output.read_text(),
                                 f"signing={str(signing).lower()}\nconfigured={str(configured).lower()}\n")
                publisher = directory / "inbe-publisher"
                self.assertEqual(publisher.exists(), signing)
                if signing:
                    self.assertEqual(publisher.stat().st_mode & 0o777, 0o700)
                    expected = {"publisher.pem": "test-private-key\n"}
                    if configured:
                        expected.update({"node.key": "test-ssh-key\n", "known_hosts": "test-host\n"})
                    self.assertEqual({path.name for path in publisher.iterdir()}, set(expected))
                    for filename, content in expected.items():
                        path = publisher / filename
                        self.assertEqual(path.read_text(), content)
                        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_sign_and_publish_command_steps(self):
        # Crypto/payload publication has a separate real integration test.
        # Here the actual workflow shell must invoke the correct commands and
        # must not execute a misplaced heredoc delimiter as a shell command.
        for name in ("Sign app releases", "Sign and publish to Waozi's Daochi node"):
            with self.subTest(step=name), tempfile.TemporaryDirectory() as temporary:
                log = Path(temporary) / "commands"
                stub = "python3() { printf '%s\\n' \"$*\" >> " + shlex.quote(str(log)) + "; }\n"
                env = os.environ | {"RUNNER_TEMP": temporary, "KEY_ID": "test",
                                    "TARGET": "test@example.invalid", "STORE": "/test/packages"}
                result = subprocess.run(["bash", "-eu"], input=stub + script(name),
                                        text=True, capture_output=True, env=env, check=True)
                self.assertEqual(result.stderr, "")
                commands = log.read_text().splitlines()
                self.assertTrue(commands[-1].startswith("scripts/package-release.py --store build/package-releases "))
                self.assertIn("--key-id test", commands[-1])
                self.assertIn(f"--key {temporary}/inbe-publisher/publisher.pem", commands[-1])
                if name == "Sign app releases":
                    self.assertEqual(commands[0], "scripts/check-package-publishers.py")
                else:
                    self.assertIn("--ssh-target test@example.invalid --remote-store /test/packages", commands[-1])


if __name__ == "__main__":
    unittest.main()
