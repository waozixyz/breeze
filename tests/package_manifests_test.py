"""Preserve account scopes while authorizing separately signed app packages."""
import importlib.util
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("package_manifests", ROOT / "scripts/package-manifests.py")
manifests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifests)


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        self.publisher = Ed25519PrivateKey.generate()
        self.authority = Ed25519PrivateKey.generate()
        self.component = dict(name="inbe", id="inbe", version="2.1.2")
        self.existing = dict(app_id="inbe", display_name="Inner Breeze", status="active",
                             collections=[dict(app_id="inbe", collection_prefix="private.inbe.v1.*",
                                               visibility="private", schema_version=1)],
                             capabilities=["sync"],
                             features=[dict(id="sync.private_records", description="Keep <private> data & choices",
                                            collections=["private.inbe.v1.*"], requires_signed_tx=True)],
                             token_policies=[dict(asset_id="waozi:token", permission="purchase", status="active")])

    def manifest(self, existing=None):
        return manifests.manifest_for(self.component, self.existing if existing is None else existing,
                                      "publisher", manifests.public_hex(self.publisher))

    def test_signed_registration_keeps_scopes_and_uses_separate_authority(self):
        manifest = self.manifest()
        self.assertEqual(manifest["collections"], self.existing["collections"])
        self.assertEqual(manifest["features"], self.existing["features"])
        self.assertEqual(manifest["token_policies"], self.existing["token_policies"])
        request = manifests.signed_registration(manifest, self.publisher, self.authority)
        encoded = manifests.canonical_bytes(manifest)
        self.publisher.public_key().verify(bytes.fromhex(request["manifest_signature"]),
                                           b"daochi-app-manifest-v1\n" + encoded)
        message = f"daochi-app-approval-v1\ninbe\n{manifests.sha256(encoded).hexdigest()}\n".encode()
        self.authority.public_key().verify(bytes.fromhex(request["approval_signature"]), message)
        with self.assertRaises(Exception):
            self.publisher.public_key().verify(bytes.fromhex(request["approval_signature"]), message)
        self.assertIn(b"\\u003cprivate\\u003e", encoded)
        self.assertIn(b"\\u0026", encoded)
        self.assertEqual(list(manifest["features"][0]),
                         ["id", "collections", "requires_signed_tx", "description"])

    def test_existing_keys_remain_and_key_ids_cannot_be_replaced(self):
        self.existing["keys"] = [dict(key_id="other", algorithm="ed25519", public_key="12" * 32)]
        self.assertEqual(self.manifest()["keys"][0], self.existing["keys"][0])
        self.existing["keys"][0]["key_id"] = "publisher"
        with self.assertRaisesRegex(ValueError, "occupied or revoked"):
            self.manifest()

    def test_no_reactivation_or_node_scope_replacement(self):
        for field, value in (("status", "suspended"), ("app_id", "foreign"),
                             ("lan_only", True), ("registration_node_id", "local-node")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.manifest(dict(self.existing, **{field: value}))

    def test_app_updates_retain_the_registry_protocol_version(self):
        existing = self.manifest()
        self.assertEqual(self.manifest(existing), existing)
        self.component["version"] = "2.1.3"
        updated = self.manifest(existing)
        self.assertEqual(updated["manifest_version"], 1)
        self.assertEqual(updated["current_client_version"], "2.1.3")
        self.assertEqual(updated["collections"], existing["collections"])
        self.assertEqual(updated["keys"], existing["keys"])
        for version in (2, -1, True):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.manifest(dict(existing, manifest_version=version))

    def test_suspension_keeps_the_registration_and_raises_its_sequence(self):
        public = manifests.public_hex(self.publisher)
        existing = manifests.manifest_for(dict(name="chess", id="inbe.chess", version="1.0.1", title="Chess"),
                                          {}, "publisher", public)
        suspended = manifests.suspension_for("inbe.chess", existing, "publisher", public, 1)
        self.assertEqual(suspended["status"], "suspended")
        self.assertEqual(suspended["manifest_sequence"], 1)
        for field in ("app_id", "display_name", "keys", "current_client_version", "source_url"):
            self.assertEqual(suspended[field], existing[field])
        # Daochi signs its own field order: the sequence follows the version.
        self.assertEqual(list(suspended)[:3], ["manifest_version", "manifest_sequence", "app_id"])
        self.assertEqual(list(json.loads(manifests.canonical_bytes(suspended)))[:3],
                         ["manifest_version", "manifest_sequence", "app_id"])
        request = manifests.signed_registration(suspended, self.publisher, self.authority)
        self.publisher.public_key().verify(bytes.fromhex(request["manifest_signature"]),
                                           b"daochi-app-manifest-v1\n" + manifests.canonical_bytes(suspended))
        for app_id, registered, key_id, sequence in (
                ("inbe.chess", {}, "publisher", 1),
                ("inbe.chess", dict(existing, status="suspended"), "publisher", 2),
                ("inbe.chess", existing, "publisher", 0),
                ("inbe.chess", existing, "other", 1),
                ("inbe.arcade", existing, "publisher", 1)):
            with self.subTest(app_id=app_id, key_id=key_id, sequence=sequence), self.assertRaises(ValueError):
                manifests.suspension_for(app_id, registered, key_id, public, sequence)

    def test_one_app_from_an_owning_ledger(self):
        ledger = ROOT / "build/package-manifests-test/versions.json"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps({"node_apps": {
            "arcade": {"id": "inbe.arcade", "title": "Arcade", "version": "0.5.0", "sequence": 1},
            "chess": {"id": "inbe.chess", "title": "Chess", "version": "1.2.0", "sequence": 5},
            "pushy": {"id": "arcade.pushy", "title": "Pushy", "version": "0.3.0", "sequence": 4}}}))
        versions = json.loads((ROOT / "apps/versions.json").read_text())
        # Games inside a collection are not registered on their own.
        self.assertEqual([name for name, _ in manifests.ledger_components(versions, ledger, None)],
                         ["arcade", "chess"])
        self.assertEqual(manifests.ledger_components(versions, ledger, "arcade")[0][1]["id"], "inbe.arcade")
        with self.assertRaisesRegex(ValueError, "not an app"):
            manifests.ledger_components(versions, ledger, "pushy")
        self.assertEqual(manifests.ledger_components(versions, None, "lists")[0][1]["id"], "inbe.lists")

    def test_optional_apps_do_not_claim_root_account_collections(self):
        self.component = dict(name="lists", id="inbe.lists", version="1.0.1")
        manifest = self.manifest({})
        self.assertNotIn("collections", manifest)
        self.assertEqual(manifest["app_id"], "inbe.lists")
        self.assertEqual(json.loads(manifests.canonical_bytes(manifest)), manifest)


if __name__ == "__main__":
    unittest.main()
