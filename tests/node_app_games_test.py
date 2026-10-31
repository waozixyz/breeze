"""Separate game downloads stay bound to the checked collection's digests."""
from hashlib import sha256
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from node_app_games import required_games, stage_games


def fixture_bundle(assets, version=26):
    def text(value):
        data = value.encode()
        return struct.pack('<I', len(data)) + data
    data = b'ZX\0\0' + struct.pack('<I', version) + text('collection') + text('Main')
    data += struct.pack('<IIIII', 0, 0, 0, 0, len(assets))
    for name, content in assets.items():
        data += text(name) + struct.pack('<I', len(content)) + content
    return data


class GameArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='node-game-archive-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.game = b'ZX\0\0game bytes'
        self.name = sha256(self.game).hexdigest() + '.zx'
        self.child = dict(bundle='assets/games/example.zx', sha256=self.name[:-3])
        self.bundle = self.root / 'arcade.zx'
        self.bundle.write_bytes(fixture_bundle({'assets/apps/catalog.json':
                                               json.dumps({'children': [self.child]}).encode()}))
        self.archive = self.root / 'arcade.games.tar'
        self.output = self.root / 'arcade.games'

    def archive_games(self, entries):
        with tarfile.open(self.archive, 'w') as archive:
            for name, data in entries:
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))

    def test_only_unpacked_children_need_downloads(self):
        self.assertEqual(required_games(self.bundle), {self.name})
        assets = {'assets/apps/catalog.json': json.dumps({'children': [self.child]}).encode(),
                  self.child['bundle']: self.game}
        self.bundle.write_bytes(fixture_bundle(assets))
        self.assertEqual(required_games(self.bundle), set())
        self.bundle.write_bytes(fixture_bundle({}))
        self.assertEqual(required_games(self.bundle), set())

    def test_current_bundle_format_keeps_archive_validation(self):
        catalog = json.dumps({'children': [self.child]}).encode()
        self.bundle.write_bytes(fixture_bundle({'assets/apps/catalog.json': catalog}, version=27))
        self.assertEqual(required_games(self.bundle), {self.name})
        self.archive_games([(self.name, self.game)])
        stage_games(self.bundle, self.archive, self.output)
        self.assertEqual((self.output / self.name).read_bytes(), self.game)
        self.archive_games([(self.name, b'ZX\0\0wrong bytes')])
        with self.assertRaises(ValueError):
            stage_games(self.bundle, self.archive, self.output)
        self.assertEqual((self.output / self.name).read_bytes(), self.game)
        for data in (fixture_bundle({}, version=28), self.bundle.read_bytes()[:-1],
                     self.bundle.read_bytes() + b'extra'):
            self.bundle.write_bytes(data)
            with self.assertRaises(ValueError):
                required_games(self.bundle)
    def test_unpacked_art_downloads_like_a_game(self):
        art = b'ZX\0\0library art'
        name = sha256(art).hexdigest() + '.zx'
        catalog = {'children': [self.child], 'art': {'sha256': name[:-3], 'bytes': len(art)}}
        self.bundle.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
        self.assertEqual(required_games(self.bundle), {self.name, name})
        self.archive_games([(self.name, self.game), (name, art)])
        stage_games(self.bundle, self.archive, self.output)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), sorted([self.name, name]))
        catalog['art']['sha256'] = 'not a digest'
        self.bundle.write_bytes(fixture_bundle({'assets/apps/catalog.json': json.dumps(catalog).encode()}))
        with self.assertRaisesRegex(ValueError, 'invalid art digest'):
            required_games(self.bundle)

    def test_exact_download_is_staged_without_stale_games(self):
        self.output.mkdir()
        (self.output / 'old.zx').write_bytes(b'old')
        self.archive_games([(self.name, self.game)])
        stage_games(self.bundle, self.archive, self.output)
        self.assertEqual(list(self.output.iterdir()), [self.output / self.name])
        self.assertEqual((self.output / self.name).read_bytes(), self.game)

    def test_wrong_or_missing_bytes_preserve_previous_output(self):
        self.output.mkdir()
        marker = self.output / 'previous.zx'
        marker.write_bytes(b'previous')
        for entries in ([], [(self.name, b'ZX\0\0different')],
                        [(self.name, self.game), (self.name, self.game)],
                        [('../escape.zx', self.game)], [('extra.zx', self.game)]):
            with self.subTest(entries=entries):
                self.archive_games(entries)
                with self.assertRaises(ValueError):
                    stage_games(self.bundle, self.archive, self.output)
                self.assertEqual(marker.read_bytes(), b'previous')
        self.assertFalse((self.root / 'escape.zx').exists())

    def test_link_is_rejected(self):
        with tarfile.open(self.archive, 'w') as archive:
            entry = tarfile.TarInfo(self.name)
            entry.type = tarfile.SYMTYPE
            entry.linkname = '../elsewhere'
            archive.addfile(entry)
        with self.assertRaises(ValueError):
            stage_games(self.bundle, self.archive, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
