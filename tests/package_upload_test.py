"""Exercise the restricted, signed archive receiver without a server account."""
from hashlib import sha256
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
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
spec = importlib.util.spec_from_file_location('practice_upload', ROOT / 'scripts/upload-practice-packs.py')
uploader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploader)
OUTPUT = ROOT / 'build/package-upload-test'


class RestrictedUploadTest(unittest.TestCase):
    def setUp(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=OUTPUT)
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


class ExactPracticeUploadTest(unittest.TestCase):
    def setUp(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=OUTPUT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'apps').mkdir()
        (self.root / 'build/apps').mkdir(parents=True)
        (self.root / 'build/apps/practices.zx').write_bytes(b'catalog fixture')
        content = self.root / 'build/practice-content'
        content.mkdir()
        self.key = Ed25519PrivateKey.generate()
        self.key_file = self.root / 'publisher.pem'
        self.key_file.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw,
                                                   serialization.PublicFormat.Raw).hex()
        self.publishers = [dict(key_id='test', public_key=public, app_ids=['inbe.practices'])]
        (self.root / 'apps/publishers.json').write_text(json.dumps(self.publishers))
        (self.root / 'apps/versions.json').write_text(json.dumps(dict(host_api=2, module_api=2,
            apps=dict(practices=dict(id='inbe.practices', version='1.2.3', sequence=4)))))
        (self.root / 'apps/practice').mkdir()
        (self.root / 'apps/practice/content.json').write_text(json.dumps(dict(
            practices=['astral_projection', 'taichi', 'workout', 'sunsalutation'])))
        self.catalog, self.payloads = [], {}
        for identifier in ('astral_projection', 'astral_projection.pt', 'astral_projection.de',
                           'taichi.en.male', 'guide.pt', 'workout.en', 'sunsalutation', 'sunsalutation.pt'):
            parts = identifier.split('.')
            data = b'ZX' + identifier.encode() * 8
            row = dict(practice=parts[0], language=parts[1] if len(parts) > 1 else '',
                       sha256=sha256(data).hexdigest(), size=len(data))
            if len(parts) > 2:
                row.update(voice=parts[2], product='inbe.practice.taichi')
            self.catalog.append(row)
            self.payloads[row['sha256']] = data
            (content / (identifier + '.zx')).write_bytes(data)
        self.remote, self.requests, self.transports, self.staged = {}, [], [], []

    def run_upload(self, arguments, selected, *, existing=False, corrupt=False):
        allowed = {row['sha256'] for row in self.catalog if uploader.pack_identifier(row) in selected}
        if existing:
            self.remote.update({digest: self.payloads[digest] for digest in allowed})
        temporary_directory = tempfile.TemporaryDirectory

        def open_url(request, timeout):
            route = request.full_url.removeprefix(uploader.NODE)
            self.assertEqual(len(route), 67)
            digest = route[:-3]
            self.assertIn(digest, allowed)
            self.requests.append((request.get_method(), digest))
            paid = next(row for row in self.catalog if row['sha256'] == digest).get('product')
            if digest not in self.remote or paid:
                raise uploader.urllib.error.HTTPError(request.full_url,
                    403 if digest in self.remote and paid else 404, 'fixture', None, None)
            response = BytesIO(b'wrong bytes' if corrupt else self.remote[digest])
            response.status = 200
            return response

        def transport(command, input, check):
            self.assertEqual(command[:3], ['ssh', '-o', 'BatchMode=yes'])
            self.assertEqual(command[-2], uploader.TARGET)
            self.assertIn('--keep-old-files', command[-1])
            if '--signed-metadata' in arguments:
                self.assertIn('StrictHostKeyChecking=yes', command)
                self.assertLess(command[-1].index('test-store-match'), command[-1].index('tar -x'))
            self.assertTrue(check)
            names = []
            with tarfile.open(fileobj=BytesIO(input)) as tar:
                for member in tar:
                    names.append(member.name)
                    digest = member.name.split('/')[1][:64]
                    self.assertIn(digest, allowed)
                    data = tar.extractfile(member).read()
                    if member.name.endswith('.zx'):
                        self.assertEqual(sha256(data).hexdigest(), digest)
                        self.remote[digest] = data
                    elif member.name.endswith('.release-v2.json'):
                        value = json.loads(data)
                        uploader.package_release.validate_release(value, 'inbe.practices', self.publishers)
                        self.assertEqual(value['artifacts'][0]['sha256'], digest)
                    else:
                        self.assertTrue(member.name.endswith('.zx.product'))
                        self.assertEqual(data, b'inbe.practice.taichi')
            self.assertFalse(any('latest' in name for name in names))
            if '--pack' in arguments:
                ownership_command, permissions = command[-1].split(' && chmod 600 -- ', 1)
                ownership = ownership_command.split('chown --reference=inbe.practices -- ', 1)[1]
                self.assertEqual(set(ownership.split()), set(names))
                self.assertEqual(set(permissions.split()), set(names))
            self.transports.append(names)

        original_selected = uploader.stage_selected_packs

        def stage_selected(store, rows):
            self.staged.append([uploader.pack_identifier(row) for row in rows])
            original_selected(store, rows)
            self.assertEqual({p.parent.name for p in store.rglob('*') if p.is_file()}, {'inbe.practices'})
            self.assertEqual({p.name[:64] for p in store.rglob('*') if p.is_file()},
                             {row['sha256'] for row in rows})

        with (patch.object(uploader, 'ROOT', self.root), patch.object(uploader, 'KEY', self.key_file),
              patch.object(uploader, 'KEY_ID', 'test'),
              patch.object(uploader, 'RECEIPT', self.root / 'uploads.txt'),
              patch.object(uploader.package_release, 'catalog_from_bundle', return_value=self.catalog),
              patch.object(uploader, 'stage_selected_packs', side_effect=stage_selected) as exact_stage,
              patch.object(uploader.package_release, 'stage',
                  side_effect=AssertionError('content delivery must not stage unrelated app releases')) as legacy_stage,
              patch.object(uploader.tempfile, 'TemporaryDirectory',
                  side_effect=temporary_directory),
              patch.object(uploader.urllib.request, 'urlopen', side_effect=open_url),
              patch.object(uploader, 'archive_destination_guard', return_value='test-store-match'),
              patch.object(uploader.subprocess, 'run', side_effect=transport),
              patch.object(sys, 'argv', ['upload-practice-packs.py', *arguments]),
              redirect_stdout(StringIO()), redirect_stderr(StringIO())):
            try:
                result = uploader.main()
            finally:
                self.exact_stages = exact_stage.call_count
                self.legacy_stages = legacy_stage.call_count
        return result


    def archive_for(self, identifier):
        rows = [row for row in self.catalog if uploader.pack_identifier(row) == identifier]
        store = self.root / 'signed-archive'
        with (patch.object(uploader, 'ROOT', self.root), patch.object(uploader, 'KEY', self.key_file),
              patch.object(uploader, 'KEY_ID', 'test')):
            uploader.stage_selected_packs(store, rows)
        return store / 'inbe.practices'

    def test_archived_signature_restores_exact_public_pack_without_private_key(self):
        archive = self.archive_for('guide.pt')
        self.key_file.unlink()
        self.assertEqual(self.run_upload(['--signed-metadata', str(archive), '--pack', 'guide.pt'],
                                        {'guide.pt'}), 0)
        self.assertEqual((self.exact_stages, self.legacy_stages), (0, 0))
        self.assertEqual(len(self.transports), 1)
        self.assertEqual([method for method, _ in self.requests], ['HEAD', 'GET'])

    def test_invalid_archived_signature_never_reaches_transport(self):
        archive = self.archive_for('guide.pt')
        descriptor = next(archive.glob('*.release-v2.json'))
        value = json.loads(descriptor.read_bytes())
        value['signature'] = '00' * 64
        descriptor.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.run_upload(['--signed-metadata', str(archive), '--pack', 'guide.pt'], {'guide.pt'})
        self.assertEqual((self.requests, self.transports), ([], []))

    def test_archived_restore_refuses_a_gated_pack(self):
        archive = self.archive_for('taichi.en.male')
        with self.assertRaisesRegex(ValueError, 'requires a public pack'):
            self.run_upload(['--signed-metadata', str(archive), '--pack', 'taichi.en.male'],
                            {'taichi.en.male'})
        self.assertEqual((self.requests, self.transports), ([], []))

    def test_exact_language_pack_excludes_all_other_content(self):
        self.assertEqual(self.run_upload(['--pack', 'astral_projection.pt'], {'astral_projection.pt'}), 0)
        self.assertEqual(self.staged, [['astral_projection.pt']])
        self.assertEqual((self.exact_stages, self.legacy_stages), (1, 0))
        self.assertEqual(len(self.transports), 1)
        self.assertEqual([method for method, _ in self.requests], ['HEAD', 'GET'])

    def test_repeated_exact_guide_and_paid_selectors_keep_paid_gate(self):
        self.assertEqual(self.run_upload(['--pack', 'guide.pt', '--pack', 'taichi.en.male',
                                         '--pack', 'guide.pt'], {'guide.pt', 'taichi.en.male'}), 0)
        self.assertEqual(len(self.transports), 1)
        names = self.transports[0]
        marker = next(name for name in names if name.endswith('.product'))
        self.assertLess(names.index(marker), names.index(marker.removesuffix('.product')))
        self.assertEqual(len([method for method, _ in self.requests if method == 'GET']), 1)

    def test_language_only_sun_selection_never_downloads_base_pack(self):
        self.assertEqual(self.run_upload(['--pack', 'sunsalutation.pt'], {'sunsalutation.pt'}), 0)

    def test_existing_exact_pack_is_fully_verified_without_upload(self):
        self.assertEqual(self.run_upload(['--pack', 'astral_projection.pt'],
                                        {'astral_projection.pt'}, existing=True), 0)
        self.assertEqual(self.transports, [])
        self.assertEqual([method for method, _ in self.requests], ['HEAD', 'GET'])

    def test_existing_exact_pack_with_wrong_bytes_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, 'not served exactly'):
            self.run_upload(['--pack', 'astral_projection.pt'],
                            {'astral_projection.pt'}, existing=True, corrupt=True)
        self.assertEqual(self.transports, [])

    def test_check_is_scoped_and_never_uploads_missing_pack(self):
        self.key_file.unlink()
        self.assertEqual(self.run_upload(['--check', '--pack', 'guide.pt'], {'guide.pt'}), 1)
        self.assertEqual((self.exact_stages, self.legacy_stages), (0, 0))
        self.assertEqual(self.transports, [])
        self.assertEqual([method for method, _ in self.requests], ['HEAD'])

    def test_check_existing_content_needs_no_key_or_unrelated_app_bundles(self):
        self.key_file.unlink()
        self.assertEqual(self.run_upload(['--check'],
            {uploader.pack_identifier(row) for row in self.catalog}, existing=True), 0)
        self.assertEqual((self.exact_stages, self.legacy_stages), (0, 0))
        self.assertEqual(self.transports, [])
        self.assertEqual([method for method, _ in self.requests].count('GET'), 1)

    def test_keyless_check_rejects_corrupted_existing_exact_content(self):
        self.key_file.unlink()
        with self.assertRaisesRegex(SystemExit, 'not served exactly'):
            self.run_upload(['--check', '--pack', 'guide.pt'],
                {'guide.pt'}, existing=True, corrupt=True)
        self.assertEqual((self.exact_stages, self.legacy_stages), (0, 0))
        self.assertEqual(self.transports, [])

    def test_content_flag_still_selects_only_base(self):
        self.assertEqual(self.run_upload(['--content', 'astral_projection'], {'astral_projection'}), 0)
        self.assertEqual((self.exact_stages, self.legacy_stages), (1, 0))

    def test_default_still_uses_all_catalog_packs(self):
        self.assertEqual(self.run_upload([], {uploader.pack_identifier(row) for row in self.catalog}), 0)
        self.assertEqual((self.exact_stages, self.legacy_stages), (1, 0))

    def test_invalid_empty_or_mixed_selection_has_no_signing_or_remote_actions(self):
        for args in (['--pack', 'unknown.pt'], ['--pack', ''],
                     ['--pack', 'guide.pt', '--content', 'astral_projection']):
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.run_upload(args, set())
            self.assertEqual((self.exact_stages, self.legacy_stages), (0, 0))
            self.assertEqual((self.requests, self.transports), ([], []))

    def test_changed_selected_payload_never_reaches_transport(self):
        (self.root / 'build/practice-content/guide.pt.zx').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs from its signed catalog'):
            self.run_upload(['--pack', 'guide.pt'], {'guide.pt'})
        self.assertEqual((self.requests, self.transports), ([], []))

    def test_untrusted_signer_never_reaches_transport(self):
        self.publishers[0]['app_ids'] = ['inbe.diary']
        (self.root / 'apps/publishers.json').write_text(json.dumps(self.publishers))
        with self.assertRaises(ValueError):
            self.run_upload(['--pack', 'guide.pt'], {'guide.pt'})
        self.assertEqual((self.requests, self.transports), ([], []))

    def test_verification_streams_and_rejects_wrong_size(self):
        data = b'fixture' * 30000

        class BoundedResponse(BytesIO):
            def read(inner, size=-1):
                self.assertEqual(size, 65536)
                return super().read(size)

        for actual, expected in ((data, True), (data[:-1], False), (data + b'extra', False)):
            with self.subTest(size=len(actual)), patch.object(uploader.urllib.request, 'urlopen',
                    return_value=BoundedResponse(actual)):
                self.assertEqual(uploader.matches(sha256(data).hexdigest(), len(data)), expected)


class AndroidPracticeDeliveryTest(unittest.TestCase):
    """Run the actual install recipe against disposable tools, never a phone."""

    def setUp(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=OUTPUT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/upload-practice-packs.py').write_text(
            "from pathlib import Path\nimport os, sys\n"
            "Path('delivery-arguments').write_text(' '.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ['DELIVERY_STATUS']))\n")
        (self.root / 'scripts/android-install-apk.sh').write_text(
            "#!/bin/sh\nset -eu\ntouch installed\n")
        self.adb = self.root / 'adb'
        self.adb.write_text('#!/bin/sh\necho arm64-v8a\n')
        self.adb.chmod(0o700)

    def install(self, *, publisher=False, status=0):
        if publisher:
            key = self.root / 'backup/package-publisher/2026-10/publisher.pem'
            key.parent.mkdir(parents=True)
            key.touch()
        return subprocess.run(['make', '--no-print-directory', '-f', str(ROOT / 'mk/android.mk'),
            '-o', 'android-copy-assets', '-o', 'android-local-properties', 'android-install',
            'MAKE=true', 'GRADLE=true', 'ADB=' + str(self.adb),
            'ANDROID_DEBUG_APP_ID=fixture', 'ANDROID_ACTIVITY=Fixture'], cwd=self.root,
            env=os.environ | {'DELIVERY_STATUS': str(status)}, capture_output=True, text=True)

    def test_missing_remote_content_stops_install_without_a_signing_key(self):
        result = self.install(status=1)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / 'delivery-arguments').read_text(), '--check')
        self.assertFalse((self.root / 'installed').exists())

    def test_failed_content_upload_stops_install(self):
        result = self.install(publisher=True, status=1)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / 'delivery-arguments').read_text(), '')
        self.assertFalse((self.root / 'installed').exists())

    def test_available_content_allows_install_without_a_signing_key(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / 'delivery-arguments').read_text(), '--check')
        self.assertTrue((self.root / 'installed').exists())


if __name__ == "__main__":
    unittest.main()
