"""Exercise all three host-bridge paths on a private, non-OpenGL SDL window."""
import os
from pathlib import Path
import subprocess
import sys
import time

assert int(os.environ['DISPLAY'].split(':')[-1].split('.')[0]) >= 300
binary = Path(sys.argv[1]).resolve()


def command(*arguments):
    return subprocess.check_output(arguments, text=True, timeout=5).strip()


with subprocess.Popen([str(binary)]) as process:
    try:
        deadline = time.monotonic() + 15
        window = ''
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Bridge fixture exited before publishing state'
            found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(process.pid)],
                                   capture_output=True, text=True, timeout=5)
            if found.returncode == 0:
                window = found.stdout.splitlines()[0]
                if 'bridge-ready' in command('xprop', '-id', window, '_HARMONY_APP_STATE'):
                    break
            time.sleep(.05)
        else:
            raise AssertionError('Cairo host did not publish its ready state')
        command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
                '-set', '_HARMONY_APP_ACTION', 'bridge-ping')
        command('xprop', '-id', window, '-f', '_HARMONY_APP_FEATURE', '32c',
                '-set', '_HARMONY_APP_FEATURE', '16')
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Bridge fixture exited before consuming requests'
            if 'bridge-done' in command('xprop', '-id', window, '_HARMONY_APP_STATE'):
                break
            time.sleep(.02)
        else:
            raise AssertionError('Cairo host did not consume its action and feature requests')
        command('xprop', '-id', window, '-f', '_HARMONY_APP_ACTION', '8s',
                '-set', '_HARMONY_APP_ACTION', 'bridge-close')
        assert process.wait(timeout=5) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
print('Cairo desktop bridge: state, action and feature request passed')
