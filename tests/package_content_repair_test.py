"""Repair one signed picture pack while preserving every app release pointer."""
import importlib.util
import io
import json
from hashlib import sha256
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('content_repair', ROOT / 'scripts/package-release.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def resource(path):
    def number(value):
        return struct.pack('<I', value)

    def text(value):
        value = value.encode()
        return number(len(value)) + value

    return (b'ZIB\0' + number(26) + text('content') + text('Main') + number(0) * 4 +
            number(1) + text(path) + number(3) + b'png')


class ContentRepairTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='inbe-content-repair-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.signer = Ed25519PrivateKey.generate()
        self.key = self.root / 'publisher.pem'
        self.key.write_bytes(self.signer.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public = self.signer.public_key().public_bytes(serialization.Encoding.Raw,
                 serialization.PublicFormat.Raw).hex()
        self.publishers = self.root / 'publishers.json'
        self.publishers.write_text(json.dumps([dict(key_id='test', public_key=public,
                                                 app_ids=['inbe.practices'])]))
        self.data = resource('assets/practices/sunsalutation/characters/girl/01.png')
        self.digest = sha256(self.data).hexdigest()
        pack = dict(practice='sunsalutation', language='', size=len(self.data), sha256=self.digest)
        catalog = self.root / 'build/package-assets/practices/assets/practices/catalog.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps(dict(schema=1, packs=[pack])))
        source = self.root / 'build/practice-content/sunsalutation.zib'
        source.parent.mkdir(parents=True)
        source.write_bytes(self.data)
        value = dict(app_id='inbe.practices', sequence=7, version='1.1.5', runtime='kryon-app-v1',
                     host_api=5, module_api=2, data_schema=0, key_id='test', dependencies=[],
                     artifacts=[dict(variant='module', size=8, sha256='0' * 64)])
        value['signature'] = self.signer.sign(publisher.signing_message(value)).hex()
        self.release = self.root / 'live.json'
        self.release.write_text(json.dumps(value))
        self.store = self.root / 'staged'
        with patch.object(publisher, 'ROOT', self.root):
            digest = publisher.stage_content_repair(self.store, 'sunsalutation', self.key,
                                                   'test', self.release, self.publishers)
        self.assertEqual(self.digest, digest)
        self.filename = 'inbe.practices/' + digest + '.zib'
        self.entries = {name: (self.store / name).read_bytes() for name in
                        (self.filename, self.filename + '.release-v2.json')}
        self.remote = self.root / 'remote'
        self.latest = self.remote / 'inbe.practices/latest-v2.json'
        self.latest.parent.mkdir(parents=True)
        self.latest.write_bytes(b'original latest metadata')
        self.pins = json.loads(self.publishers.read_text())

    def test_repair_is_idempotent_and_preserves_app_release(self):
        publisher.import_content_repair(self.entries, self.remote, self.pins)
        publisher.import_content_repair(self.entries, self.remote, self.pins)
        self.assertEqual(self.data, (self.remote / self.filename).read_bytes())
        self.assertEqual(b'original latest metadata', self.latest.read_bytes())
        self.assertFalse((self.store / 'inbe.practices/latest-v2.json').exists())

    def test_existing_receiver_dispatches_repair_archive(self):
        upload = self.root / 'upload'
        upload.mkdir()
        archive = upload / 'repair.tar'
        with tarfile.open(archive, 'w') as tar:
            for name, data in self.entries.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
        publisher.import_archive(archive, self.remote, self.publishers)
        self.assertEqual(self.data, (self.remote / self.filename).read_bytes())
        self.assertEqual(b'original latest metadata', self.latest.read_bytes())

    def test_tampered_bytes_signature_and_extra_files_are_rejected(self):
        for entries in (dict(self.entries, **{self.filename: b'bad'}),
                        dict(self.entries, **{self.filename + '.release-v2.json': b'{}'}),
                        dict(self.entries, **{'inbe.practices/latest-v2.json': b'new'})):
            with self.assertRaises((ValueError, KeyError)):
                publisher.import_content_repair(entries, self.remote, self.pins)
            self.assertFalse((self.remote / self.filename).exists())
        self.assertEqual(b'original latest metadata', self.latest.read_bytes())

    def test_paid_content_and_immutable_conflicts_are_preserved(self):
        marker = self.remote / (self.filename + '.product')
        marker.write_text('paid')
        with self.assertRaisesRegex(ValueError, 'paid content'):
            publisher.import_content_repair(self.entries, self.remote, self.pins)
        marker.unlink()
        target = self.remote / self.filename
        target.write_bytes(b'original')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            publisher.import_content_repair(self.entries, self.remote, self.pins)
        self.assertEqual(b'original', target.read_bytes())

    def test_other_practices_and_narration_are_rejected(self):
        for path in ('assets/practices/taichi/01.png', 'assets/practices/sunsalutation/voice/en/01.ogg'):
            with self.assertRaisesRegex(ValueError, 'Sun Salutation picture'):
                publisher.validate_repair_assets(resource(path))


if __name__ == '__main__':
    unittest.main()
