#!/usr/bin/env python3
"""ABI type names must not exempt real paths from the storage vocabulary gate."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
ABI_NAMES = '''    value.type_name = ModuleTextData("BreathSession")
    if value.kind != cast(s32)HostRecord || TextFromCString(value.type_name) != "BreathSession" ||
'''


class StorageLiteralsTest(unittest.TestCase):
    def check_source(self, source, path='cells/value_codec.zi'):
        with tempfile.TemporaryDirectory(prefix='inbe-storage-literals-') as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/check-storage-literals.sh', root / 'scripts')
            fixture = root / 'src' / path
            fixture.parent.mkdir(parents=True)
            fixture.write_text(source)
            result = subprocess.run(['bash', str(root / 'scripts/check-storage-literals.sh')],
                                    capture_output=True, text=True, check=False)
            return result.returncode

    def test_record_names_are_not_directory_names(self):
        self.assertEqual(self.check_source(ABI_NAMES), 0)

    def test_paths_in_the_codec_still_fail(self):
        self.assertNotEqual(self.check_source(ABI_NAMES + 'path := "BreathSession"\n'), 0)
        self.assertNotEqual(self.check_source(ABI_NAMES + 'path := "inbe.db"\n'), 0)

    def test_directory_copies_in_other_modules_fail(self):
        self.assertNotEqual(self.check_source('path := "BreathSession"\n', 'app/example.zi'), 0)


if __name__ == '__main__':
    unittest.main()
