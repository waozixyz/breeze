#!/usr/bin/env python3
"""Exercise rejected Android picker ownership with native fixture callbacks."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get('ZI2C', str(ROOT / 'build/ziran-toolchain/bin/zi2c'))
STD = Path(os.environ.get('ZIRAN_STD_ROOT', str(ROOT / 'build/packages/ziran')))
ENV = {key: value for key, value in os.environ.items()
       if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                      'ZIRAN_PACKAGE_MAP')}
package_args = subprocess.check_output(
    ['sh', str(ROOT / 'scripts/package-paths.sh'), str(ROOT / 'build/packages')],
    cwd=ROOT, text=True).split()
module_paths = [ROOT / 'src', STD / 'std', ROOT / 'build/packages/kryon/src/ui',
                ROOT / 'build/packages/kryon/src/backend', ROOT / 'build/packages/kss/src',
                ROOT / 'build/packages/game2d/src', ROOT / 'build/packages/daochi-client']
output = ROOT / 'build/entity-picker-test'
generated = output / 'generated'
output.mkdir(parents=True, exist_ok=True)
shutil.rmtree(generated, ignore_errors=True)
subprocess.run([COMPILER, '--no-main', '--define', 'PLATFORM_DESKTOP', '--root', str(ROOT),
                *[arg for path in module_paths for arg in ('--module-path', str(path))],
                *package_args,
                '-o', str(generated), str(ROOT / 'tests/entity_picker_behavior.zi')],
               cwd=ROOT, env=ENV, check=True)
header = next(generated.rglob('*entity_picker_behavior.h'))
(generated / 'main.c').write_text('#include "' + str(header.relative_to(generated)) + '"\n'
    '#include <stdio.h>\nint main(void) { int result = Check(); '
    'if (result) fprintf(stderr, "Picker fixture %d failed\\n", result); return result != 0; }\n')
subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O0', '-ffunction-sections', '-fdata-sections',
                '-Wl,--gc-sections', '-I' + str(STD / 'include'), '-I' + str(generated),
                *map(str, generated.rglob('*.c')), '-lpthread', '-lm', '-o', str(output / 'test')],
               cwd=ROOT, env=ENV, check=True)
subprocess.run([str(output / 'test')], cwd=ROOT, env=ENV, check=True)
print('Abandoned picker: deferred selection, new-request isolation, copied-file cleanup and cancellation passed.')
