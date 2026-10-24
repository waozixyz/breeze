"""Exercise the restricted, signed archive receiver without a server account."""
from hashlib import sha256
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/package-release.py"
spec = importlib.util.spec_from_file_location("package_release", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class RestrictedUploadTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / "packages"
        self.key = Ed25519PrivateKey.generate()
        self.pins = self.directory / "publishers.json"
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw,
                                                   serialization.PublicFormat.Raw).hex()
        self.pins.write_text(json.dumps([dict(key_id="test", public_key=public,
                                              app_ids=["inbe", *["inbe." + name for name in release.NAMES[:-1]]])]))
        self.values = {}
        self.payloads = {}
        for name in release.NAMES:
            app_id = "inbe" if name == "inbe" else "inbe." + name
            data = b"ZX\0\0" + name.encode() + b"-fixture"
            dependencies = []
            if name == "inbe":
                for child in sorted(release.NAMES[:-1]):
                    value = self.values["inbe." + child]
                    data += self.payloads[value["app_id"]]
                    artifact = value["artifacts"][0]
                    dependencies.append(dict(app_id=value["app_id"], version=value["version"],
                                             sha256=artifact["sha256"], size=artifact["size"]))
            value = dict(app_id=app_id, sequence=1, version="1.0.0", runtime="kryon-app-v1",
                         host_api=2, module_api=2, data_schema=0, key_id="test",
                         artifacts=[dict(variant="module", sha256=sha256(data).hexdigest(), size=len(data))],
                         dependencies=dependencies)
            value["signature"] = self.key.sign(release.signing_message(value)).hex()
            self.values[app_id] = value
            self.payloads[app_id] = data

    def archive(self):
        stream = BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            for app_id, value in self.values.items():
                entries = {"latest-v2.json": json.dumps(value).encode(),
                           value["artifacts"][0]["sha256"] + ".zx": self.payloads[app_id]}
                for name, data in entries.items():
                    member = tarfile.TarInfo(app_id + "/" + name)
                    member.size = len(data)
                    tar.addfile(member, BytesIO(data))
        return stream.getvalue()

    def receive(self, command=None):
        env = os.environ | {"SSH_ORIGINAL_COMMAND": command or "inbe-packages " + str(self.store)}
        return subprocess.run(["python3", str(SCRIPT), "--receive-archive", "--store", str(self.store),
                               "--publishers", str(self.pins)], input=self.archive(), env=env,
                              capture_output=True)

    def test_receiver_publishes_and_is_idempotent(self):
        for _ in range(2):
            result = self.receive()
            self.assertEqual(result.returncode, 0, result.stderr)
        for app_id, value in self.values.items():
            self.assertEqual(json.loads((self.store / app_id / "latest-v2.json").read_bytes()), value)
            artifact = value["artifacts"][0]
            self.assertEqual((self.store / app_id / (artifact["sha256"] + ".zx")).read_bytes(), self.payloads[app_id])
            history = json.loads((self.store / app_id / "history-v2.json").read_bytes())
            self.assertEqual(history, dict(versions=[value]))

    def test_upload_key_cannot_run_commands_or_choose_another_store(self):
        for command in ("id", "python3 -", "scp -t /etc", "inbe-packages /other", "", "inbe-packages; id"):
            with self.subTest(command=command):
                env = os.environ | {"SSH_ORIGINAL_COMMAND": command}
                result = subprocess.run(["python3", str(SCRIPT), "--receive-archive", "--store", str(self.store),
                                         "--publishers", str(self.pins)], input=b"", env=env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.store.exists())

    def test_forged_metadata_cannot_replace_any_current_pointer(self):
        self.assertEqual(self.receive().returncode, 0)
        before = {path: path.read_bytes() for path in self.store.rglob("*") if path.is_file()}
        self.values["inbe.diary"]["version"] = "2.0.0"
        self.values["inbe.diary"]["sequence"] = 2
        result = self.receive()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"signature rejected", result.stderr)
        self.assertEqual(before, {path: path.read_bytes() for path in self.store.rglob("*") if path.is_file()})

    def test_publisher_streams_only_artifacts_to_fixed_command(self):
        self.assertEqual(self.receive().returncode, 0)
        # Publisher archives include immutable descriptors retained by the receiver.
        with patch.object(release.subprocess, "run") as run:
            def inspect(command, stdin, check):
                self.assertEqual(command[-2:], ["uploader@node.example", "inbe-packages /srv/inbe.packages"])
                self.assertIn("StrictHostKeyChecking=yes", command)
                self.assertTrue(check)
                with tarfile.open(fileobj=stdin) as tar:
                    names = tar.getnames()
                self.assertEqual(len(names), 4 * len(self.values))
                self.assertTrue(all(name.startswith(tuple(self.values)) for name in names))
                self.assertFalse(any(name.endswith((".py", ".pem", ".key")) for name in names))
            run.side_effect = inspect
            release.publish(self.store, "uploader@node.example", "/srv/inbe.packages")
            run.assert_called_once()


    def test_only_a_new_version_is_published(self):
        self.assertEqual(self.receive().returncode, 0)
        served = {app_id: json.dumps(value).encode() for app_id, value in self.values.items()}

        def open_url(url, timeout):
            app_id = url.split("/api/v2/packages/")[1].split("/")[0]
            if app_id not in served:
                raise release.HTTPError(url, 404, "Not Found", None, None)
            self.assertTrue(url.endswith("/latest?bucket=0&format=zx"))
            return BytesIO(served[app_id])

        changes = lambda: release.published_changes(self.store, "https://node.example/", open_url)
        self.assertEqual(changes(), ([], []))
        # A package that changed under the version the node serves waits.
        staged = self.store / "inbe.diary" / "latest-v2.json"
        changed = dict(self.values["inbe.diary"],
                       artifacts=[dict(variant="module", sha256="1" * 64, size=99)])
        staged.write_text(json.dumps(changed))
        self.assertEqual(changes(), ([], ["inbe.diary"]))
        # With a new version and sequence it is published.
        staged.write_text(json.dumps(dict(changed, version="1.0.1", sequence=2)))
        self.assertEqual(changes(), (["inbe.diary"], []))
        # An app the node has never served is new.
        del served["inbe.leaderboard"]
        self.assertEqual(changes(), (["inbe.diary", "inbe.leaderboard"], []))


if __name__ == "__main__":
    unittest.main()
