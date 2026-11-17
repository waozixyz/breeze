#!/usr/bin/env python3
"""Compile the actual Android startup prelude in driver-free and driver builds."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
compiler = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'build/packages/ziran/build/bin/ziran'
work = root / 'build/android-startup-contract-test'
work.mkdir(parents=True, exist_ok=True)
source = (root / 'src/platform/main_platform.zi').read_text()
start = source.index('native_before_window :: () {')
end = source.index('        AndroidInsetsInit()', start)
# Exercise the production prelude, including its compile-time driver gate.
prelude = source[start:end] + '    }\n}\n'
fixture = work / 'startup.zi'
fixture.write_text('''temporary_calls: s32;
driver_calls: s32;
InstallAssetFiles :: () {}
AndroidTemporaryPrepare :: () { temporary_calls += 1 }
AndroidTestDriverPrepare :: () { driver_calls += 1 }
// This upstream aggregate also activates the driver from a stale directory.
AndroidProcessPrepare :: () {
    AndroidTemporaryPrepare()
    AndroidTestDriverPrepare()
}
''' + prelude + '''
#program_export
main :: () -> s32 {
    native_before_window()
    if temporary_calls != 1 { return 1 }
    #if #defined(KRYON_TEST_DRIVER) {
        if driver_calls != 1 { return 2 }
    } else {
        if driver_calls != 0 { return 3 }
    }
    return 0
}
''')
env = dict(os.environ)
env.pop('KRYON_TEST_DRIVER', None)
for driver in (False, True):
    output = work / ('driver' if driver else 'normal')
    command = ['sh', str(root / 'scripts/run-ziran.sh'), str(compiler),
               'build', '--target=c', '--exe', '--entry', 'startup:main', '--root', str(work),
               '--define', 'ANDROID_BUILD', '-o', str(output)]
    if driver:
        command.extend(['--define', 'KRYON_TEST_DRIVER'])
    subprocess.run([*command, str(fixture)], env=env, check=True)
    subprocess.run([str(output / 'startup')], env=env, check=True)
print('Android startup contract: normal and test-driver variants passed')
