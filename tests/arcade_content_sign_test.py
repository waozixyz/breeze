#!/usr/bin/env python3
"""Catalog binding and trust-pin checks for immutable Arcade content signing."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("arcade_content_sign", ROOT / "scripts/sign-arcade-content.py")
signer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signer)


class ContentSigning(unittest.TestCase):
    def setUp(self):
        base = ROOT / "backup/arcade/signing-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.directory.name)
        (self.root / "apps/bundled").mkdir(parents=True)
        for name in ("bundled.json", "versions.json", "bundled/arcade.zx"):
            shutil.copyfile(ROOT / "apps" / name, self.root / "apps" / name)
        declaration = json.loads((self.root / "apps/bundled.json").read_text())["arcade"]
        self.digest = declaration["sha256"]
        self.key_id = declaration["key_id"]
        self.key = Ed25519PrivateKey.generate()
        self.key_bytes = self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw,
                                                    serialization.PublicFormat.Raw).hex()
        self.pins = [dict(key_id=self.key_id, public_key=public, app_ids=[signer.APP])]
        (self.root / "apps/publishers.json").write_text(json.dumps(self.pins))
        api_path = Path(os.environ.get("APPS_RELEASE_API", ROOT / "build/packages/apps/scripts/node_release.py"))
        self.api = signer.load_release_api(api_path)
        self.output = self.root / "signed"

    def tearDown(self):
        self.directory.cleanup()

    def sign(self):
        return signer.sign(self.root, self.digest, self.key_bytes, self.key_id, self.output, self.api)

    def test_exact_catalog_signs_only_content_and_signature_tampering_fails(self):
        descriptors = self.sign()
        _, entries = signer.catalog_entries(self.root, self.digest)
        self.assertEqual(set(descriptors), {e["sha256"] + ".zx.release-v2.json" for e in entries})
        self.assertEqual(set(p.name for p in self.output.iterdir()), set(descriptors))
        for raw in descriptors.values():
            value = json.loads(raw)
            self.api.validate_release(value, signer.APP, self.pins)
            value["artifacts"][0]["size"] += 1
            with self.assertRaises(ValueError):
                self.api.validate_release(value, signer.APP, self.pins)

    def test_wrong_key_rejected_before_writing(self):
        self.pins[0]["public_key"] = "00" * 32
        (self.root / "apps/publishers.json").write_text(json.dumps(self.pins))
        with self.assertRaisesRegex(ValueError, "trust pin"):
            self.sign()
        self.assertFalse(self.output.exists())

    def test_unrequested_catalog_rejected(self):
        self.digest = "00" * 32
        with self.assertRaisesRegex(ValueError, "requested catalog"):
            self.sign()

    def test_changed_catalog_bytes_rejected(self):
        path = self.root / "apps/bundled/arcade.zx"
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "catalog bytes"):
            self.sign()

    def test_other_app_scope_rejected(self):
        self.pins[0]["app_ids"] = ["inbe.practices"]
        (self.root / "apps/publishers.json").write_text(json.dumps(self.pins))
        with self.assertRaisesRegex(ValueError, "trust pin"):
            self.sign()

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        existing = self.output / "keep"
        existing.write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "empty regular directory"):
            self.sign()
        self.assertEqual(existing.read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
