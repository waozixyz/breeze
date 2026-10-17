#!/usr/bin/env python3
"""Generate src/cells/node_app_codec.zi with Kryon's widget codec generator.

These are the records every app the node offers exchanges with the host
through the generic app interface (src/cells/node_app_types.zi).
Pass --check to verify the file is current."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
KRYON = ROOT / 'build/packages/kryon'
KRYON_MODULES = ['session']
APP_TYPES = ['node_app_types']
ROOTS = ['AppMessage', 'AppUiFrame', 'AppPerson', 'AppShared', 'AppSharedItem',
         'AppInvitation', 'AppSharedCommand']

command = [sys.executable, str(KRYON / 'scripts/generate-widget-codecs.py'),
           '--output', str(ROOT / 'src/cells/node_app_codec.zi'),
           '--uses', str(KRYON / 'src/backend/widget_codec.zi'),
           '--generated-by', 'scripts/generate-node-app-codec.py']
for module in KRYON_MODULES:
    command += ['--source', str(KRYON / 'src/ui' / (module + '.zi'))]
for name in APP_TYPES:
    command += ['--source', str(ROOT / 'src/cells' / (name + '.zi'))]
for root in ROOTS:
    command += ['--root', root]
for line in ['"std/bundle_host"', '"std/byte_text_linux"', '"hosted_values"', '"widget_codec"',
             *(f', file "{name}.zi";' for name in APP_TYPES), *(f'"{module}"' for module in KRYON_MODULES)]:
    command += ['--import', line]
command += sys.argv[1:]
sys.exit(subprocess.run(command).returncode)
