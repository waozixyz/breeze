"""The size rule adds offline apps without removing the shipped baseline."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from small_app_bundling import inspect_bundle, stage, MANDATORY, LIMIT_BYTES
from node_app_games_test import fixture_bundle

ROOT = Path(__file__).resolve().parents[1]


class BundlingTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / 'work/small-app-bundling'
        work.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundles = self.root / 'apps'
        self.nodes = self.root / 'node-apps'
        self.bundles.mkdir()
        self.nodes.mkdir()
        # Mandatory apps larger than the limit must remain byte-identical.
        self.old = b'previously shipped' * 65000
        for name in MANDATORY:
            (self.bundles / (name + '.zx')).write_bytes(self.old)
        self.ledger = dict(node_apps={})
        self.optional = self.root / 'optional'
        self.mandatory = self.root / 'mandatory'

    def candidate(self, name, size):
        empty = fixture_bundle({'assets/payload': b''})
        data = fixture_bundle({'assets/payload': b'x' * (size - len(empty))})
        self.assertEqual(len(data), size)
        path = self.nodes / (name + '.zx')
        path.write_bytes(data)
        self.ledger['node_apps'][name] = dict(version='1.0.0', host_api=41, sequence=1)
        return path

    def test_strict_decimal_boundary_and_additive_baseline(self):
        self.candidate('small', LIMIT_BYTES - 1)
        self.candidate('equal', LIMIT_BYTES)
        self.candidate('large', LIMIT_BYTES + 1)
        report = stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        self.assertEqual(report['mandatory'], list(MANDATORY))
        self.assertEqual([p.name for p in sorted(self.optional.glob('*.zx'))], ['small.zx'])
        self.assertEqual((self.optional / 'catalog.txt').read_text(), 'small\n')
        for name in MANDATORY:
            self.assertEqual((self.mandatory / (name + '.zx')).read_bytes(), self.old)

    def test_external_art_counts_and_explicit_app_is_retained(self):
        path = self.candidate('collection', 100)
        art = fixture_bundle({'assets/collection/cover.png': b'x' * LIMIT_BYTES})
        digest = sha256(art).hexdigest()
        game = dict(bundle='assets/collection/game.zx', sha256='a' * 64, bytes=20_000_000)
        catalog = dict(children=[game], art=dict(sha256=digest, bytes=len(art)))
        path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
        resources = path.parent / 'collection.games'
        resources.mkdir()
        (resources / (digest + '.zx')).write_bytes(art)
        report = stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        info = report['optional']['collection']
        self.assertGreater(info['complete_bytes'], LIMIT_BYTES)
        self.assertFalse(info['included'])
        self.assertEqual(info['optional_download_bytes'], 20_000_000)
        self.assertEqual(info['required_art_bytes'], len(art))
        declaration = dict(path=str(path), id='inbe.collection', version='1.0.0', host_api=41,
                           bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest(), bundled=True)
        report = stage({}, {'collection': declaration}, self.bundles, self.optional, self.mandatory)
        self.assertTrue(report['optional']['collection']['included'])
        self.assertEqual((self.optional / 'collection' / (digest + '.zx')).read_bytes(), art)
        (resources / (digest + '.zx')).write_bytes(b'wrong artwork')
        with self.assertRaisesRegex(ValueError, 'missing required artwork'):
            stage({}, {'collection': declaration}, self.bundles, self.optional, self.mandatory)

    def test_reviewed_arcade_catalog_and_art_are_exact_without_games(self):
        declarations = json.loads((ROOT / 'apps/bundled.json').read_text())
        item = declarations['arcade']
        path = ROOT / item['path']
        info = inspect_bundle(path)
        self.assertEqual(info['bundle_bytes'], 7695)
        self.assertEqual(info['sha256'], item['sha256'])
        self.assertEqual(info['complete_bytes'], 349_082)
        info = stage({}, declarations, self.bundles, self.optional, self.mandatory)['optional']['arcade']
        self.assertTrue(info['included'])
        self.assertEqual(len(list((self.optional / 'arcade').glob('*.zx'))), 1)
        self.assertEqual(sum(info['optional_downloads'].values()), 65_639_505)
        item['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'reviewed declaration'):
            stage({}, declarations, self.bundles, self.optional, self.mandatory)

    def test_missing_inline_cover_cannot_qualify_as_complete(self):
        path = self.candidate('incomplete', 100)
        catalog = dict(children=[dict(bundle='assets/incomplete/game.zx', sha256='a' * 64,
                                     bytes=100, cover=dict(portrait='assets/incomplete/missing.png'))])
        path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
        report = stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        self.assertFalse(report['optional']['incomplete']['included'])

    def test_unhandled_required_dependencies_and_child_cycles_fail(self):
        path = self.candidate('collection', 100)
        for catalog in (dict(dependencies=['required-large-library']),
                        dict(children=[dict(id='one', dependencies=['missing'])]),
                        dict(children=[dict(id='one', dependencies=['two']),
                                       dict(id='two', dependencies=['one'])])):
            with self.subTest(catalog=catalog):
                path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
                with self.assertRaises(ValueError):
                    inspect_bundle(path)

    def test_art_bundle_must_contain_declared_covers(self):
        path = self.candidate('collection', 100)
        art = fixture_bundle({})
        digest = sha256(art).hexdigest()
        catalog = dict(children=[dict(bundle='game.zx', sha256='a' * 64, bytes=100,
                                     cover=dict(portrait='missing.png'))],
                       art=dict(sha256=digest, bytes=len(art)))
        path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
        resources = path.parent / 'collection.games'
        resources.mkdir()
        (resources / (digest + '.zx')).write_bytes(art)
        report = stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        self.assertFalse(report['optional']['collection']['included'])

    def test_reused_staging_drops_only_excluded_optional_inventory(self):
        self.candidate('small', LIMIT_BYTES - 1)
        stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        self.assertTrue((self.optional / 'small.zx').exists())
        self.candidate('small', LIMIT_BYTES)
        stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        self.assertFalse((self.optional / 'small.zx').exists())
        self.candidate('small', LIMIT_BYTES - 1)
        stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)
        stage({}, {}, self.bundles, self.optional, self.mandatory)
        self.assertFalse((self.optional / 'small.zx').exists())
        for name in MANDATORY:
            self.assertEqual((self.mandatory / (name + '.zx')).read_bytes(), self.old)

    def test_bad_art_metadata_never_becomes_a_filesystem_path(self):
        path = self.candidate('collection', 100)
        for digest, size in [('../outside', 10), ('a' * 64, -1), ('a' * 64, True), ('a' * 64, 100_000_000)]:
            catalog = dict(children=[], art=dict(sha256=digest, bytes=size))
            path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
            with self.assertRaisesRegex(ValueError, 'invalid catalog payload'):
                stage(self.ledger, {}, self.bundles, self.optional, self.mandatory)

    def test_inline_art_must_match_digest_and_resolve_covers(self):
        path = self.candidate('collection', 100)
        art = fixture_bundle({'assets/collection/portrait.png': b'image'})
        catalog = dict(children=[dict(bundle='game.zx', sha256='a' * 64, bytes=100,
                                     cover=dict(portrait='assets/collection/portrait.png'))],
                       art=dict(sha256=sha256(art).hexdigest(), bytes=len(art)))
        def pack():
            path.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode(),
                                             'assets/apps/art.zx': art}))
        pack()
        info = inspect_bundle(path)
        self.assertTrue(info['complete'])
        self.assertEqual(info['complete_bytes'], path.stat().st_size)
        catalog['children'][0]['cover']['portrait'] = 'missing.png'
        pack()
        self.assertFalse(inspect_bundle(path)['complete'])
        catalog['art']['sha256'] = '0' * 64
        pack()
        self.assertFalse(inspect_bundle(path)['complete'])


if __name__ == '__main__':
    unittest.main()
