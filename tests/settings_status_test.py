#!/usr/bin/env python3
"""Status text owns caller bytes, survives mutation, and stays UTF-8 bounded."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'build/ziran-toolchain/bin'
ENV = dict(os.environ)
for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'GDK_DISPLAY'):
    ENV.pop(name, None)
with tempfile.TemporaryDirectory(prefix='settings-status-', dir=ROOT / 'build') as work:
    work = Path(work)
    generated = work / 'generated'
    subprocess.run(['sh', ROOT / 'scripts/run-ziran.sh', BIN / 'zi2c',
                    '--no-main', '--root', ROOT, '-o', generated,
                    ROOT / 'tests/settings_status_behavior.zi'], env=ENV, check=True)
    includes = ['-I' + str(ROOT / 'build/packages/ziran/include')]
    includes += ['-iquote' + str(p) for p in sorted({p.parent for p in generated.rglob('*.h')})]
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    *includes, *sorted(generated.rglob('*.c')), '-o', work / 'test'], env=ENV, check=True)
    subprocess.run([work / 'test'], env=ENV, check=True)
print('Settings status ownership, replacement and UTF-8 bounds passed')
