"""The installed SSH launcher accepts only the configured upload command."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('receiver_install', ROOT / 'scripts/install-package-receiver.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)


class ReceiverLauncherTest(unittest.TestCase):
    def test_direct_and_forced_ssh_commands_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            effect = directory / 'effect.py'
            effect.write_text('import os,sys,json\nprint(json.dumps({"arguments":sys.argv[1:],"command":os.environ["SSH_ORIGINAL_COMMAND"]}))\n')
            launcher = directory / 'launcher.py'
            launcher.write_text(receiver.wrapper('/packages').replace(
                '/opt/daochi/inbe-package-receiver/package-release.py', str(effect)))
            environment = {key: value for key, value in os.environ.items() if key != 'SSH_ORIGINAL_COMMAND'}
            for arguments, original in ((['/packages'], ''), ([], 'inbe-packages /packages')):
                result = subprocess.run(['python3', str(launcher), *arguments],
                    env=environment | {'SSH_ORIGINAL_COMMAND': original}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual(value['command'], 'inbe-packages /packages')
                self.assertEqual(value['arguments'][:3], ['--receive-archive', '--store', '/packages'])
            for original in ('inbe-packages /other', 'sh -c whoami', 'inbe-packages /packages extra'):
                result = subprocess.run(['python3', str(launcher)],
                    env=environment | {'SSH_ORIGINAL_COMMAND': original}, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
