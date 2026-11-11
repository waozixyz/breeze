"""Exercise package linking through the real shell wrapper and a controlled CLI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/package-sources-test'
OUTPUT.mkdir(parents=True, exist_ok=True)
NAMES = ('ziran kryon css oqs raylib libwebp webp image-codec avif libavif libaom '
         'audio libopus libsamplerate game2d qrcode plot mingcute entity apps crypto '
         'daochi-client practices sqlite curl liboqs monocypher rini').split()
SELECTORS = ['daochi_client' if name == 'daochi-client' else name for name in NAMES]

CLI = '''#!/usr/bin/env python3
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent
arguments = sys.argv[1:]
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps(arguments) + '\\n')
mode = (root / 'mode').read_text()
if arguments[0] == 'fetch':
    raise SystemExit(9 if mode == 'fetch-error' else 0)
if arguments[:2] != ['pkg', 'paths']:
    raise SystemExit('Unexpected CLI command')
if mode == 'batch-error':
    raise SystemExit(10)
if mode == 'malformed':
    print('not-json')
else:
    print((root / 'response.json').read_text())
'''


class PackageSources(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fixture-', dir=OUTPUT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'fixture'
        (self.root / 'scripts').mkdir(parents=True)
        for name in ('packages.sh', 'seed-package-sources.py'):
            shutil.copy2(ROOT / 'scripts' / name, self.root / 'scripts' / name)
        self.commit = '1' * 40
        (self.root / 'ziran.lock').write_text(json.dumps({
            'toolchain': {'url': 'https://github.com/ziranlang/ziran.git', 'commit': self.commit}}))
        self.cli = self.root / 'controlled-cli'
        self.cli.write_text(CLI)
        self.cli.chmod(0o700)
        (self.root / 'mode').write_text('complete')
        self.rows = []
        for index, selector in enumerate(SELECTORS):
            directory = self.root / ('resolved ' + str(index) + ' "quote"\\slash\nü')
            directory.mkdir()
            (directory / 'sentinel').write_text(selector)
            self.rows.append({'selector': selector, 'path': str(directory)})
        self.write_response()
        self.links = self.root / 'build/packages'
        self.links.mkdir(parents=True)
        (self.links / '.complete').write_text('previous-toolchain')
        (self.links / 'preserved').symlink_to(self.root)

    def write_response(self):
        (self.root / 'response.json').write_text(json.dumps(self.rows))

    def run_wrapper(self, mode='complete'):
        (self.root / 'mode').write_text(mode)
        env = {key: value for key, value in os.environ.items()
               if key not in ('ZIRAN_PACKAGE_SOURCES', 'PACKAGES_LOCK_HELD')}
        env.update(ZIRAN=str(self.cli), XDG_CACHE_HOME=str(self.root / 'cache'))
        return subprocess.run(['sh', 'scripts/packages.sh', '--locked', '--offline'],
                              cwd=self.root, env=env, text=True, capture_output=True, timeout=20)

    def calls(self):
        return [json.loads(line) for line in (self.root / 'calls.jsonl').read_text().splitlines()]

    def assert_preserved(self):
        self.assertEqual((self.links / '.complete').read_text(), 'previous-toolchain')
        self.assertEqual(os.readlink(self.links / 'preserved'), str(self.root))
        self.assertEqual({path.name for path in self.links.iterdir()}, {'.complete', 'preserved'})

    def test_single_batch_maps_all_paths_and_preserves_escaped_names(self):
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls(), [['fetch', '--locked', '--offline'],
                         ['pkg', 'paths', *SELECTORS, '--locked', '--offline']])
        self.assertEqual({path.name for path in self.links.iterdir()}, {*NAMES, '.complete'})
        self.assertEqual((self.links / '.complete').read_text().strip(), self.commit)
        for name, row in zip(NAMES, self.rows):
            self.assertEqual(os.readlink(self.links / name), row['path'])
            directory = Path(row['path'])
            self.assertEqual({path.name for path in directory.iterdir()}, {'sentinel'})
            self.assertEqual((directory / 'sentinel').read_text(), row['selector'])

    def test_fetch_failure_preserves_previous_links_without_batch(self):
        result = self.run_wrapper('fetch-error')
        self.assertEqual(result.returncode, 9)
        self.assertEqual(self.calls(), [['fetch', '--locked', '--offline']])
        self.assert_preserved()

    def test_batch_failure_preserves_previous_links(self):
        result = self.run_wrapper('batch-error')
        self.assertEqual(result.returncode, 10)
        self.assert_preserved()

    def test_malformed_json_preserves_previous_links(self):
        result = self.run_wrapper('malformed')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid batch path response', result.stderr)
        self.assert_preserved()

    def test_missing_row_preserves_previous_links(self):
        self.rows.pop()
        self.write_response()
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incomplete batch path response', result.stderr)
        self.assert_preserved()

    def test_mismatched_selector_is_rejected_before_any_link(self):
        self.rows[-1]['selector'] = self.rows[0]['selector']
        self.write_response()
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid batch path for rini', result.stderr)
        self.assert_preserved()
        self.assertEqual(list((self.root / 'build/packages.tmp').iterdir()), [])

    def test_missing_final_directory_is_rejected_before_any_link(self):
        self.rows[-1]['path'] = str(self.root / 'missing')
        self.write_response()
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no checkout for rini', result.stderr)
        self.assert_preserved()
        self.assertEqual(list((self.root / 'build/packages.tmp').iterdir()), [])

    def test_relative_path_is_rejected(self):
        self.rows[-1]['path'] = 'scripts'
        self.write_response()
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assert_preserved()

    def test_nonstring_path_is_rejected(self):
        self.rows[-1]['path'] = None
        self.write_response()
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assert_preserved()


if __name__ == '__main__':
    unittest.main(verbosity=2)
