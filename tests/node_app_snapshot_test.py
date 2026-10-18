"""Run the installed-leaf projection against production SQLite storage.

The explicit source map is a local integration handoff, not a release lock.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module-map', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--crypto-source', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = root / 'build/node-app-snapshot-test'
    generated = work / 'c'
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True)
    rows = args.module_map.read_text().splitlines()
    packages = {parts[1]: Path(parts[2]) for row in rows
                if (parts := row.split('\t'))[0] == 'P'}
    substitutions = {}
    for identity, source in packages.items():
        manifest = source / 'ziran.toml'
        if manifest.exists() and tomllib.loads(manifest.read_text())['package']['name'].lower() == 'crypto':
            substitutions[str(source)] = str(args.crypto_source.resolve())
    if not substitutions:
        raise ValueError('Source map has no Crypto package')
    text = '\n'.join(rows) + '\n'
    for previous, current in substitutions.items():
        text = text.replace(previous + '/', current + '/').replace(previous + '\n', current + '\n')
    for module in ('node_app_snapshot_behavior', 'delegate_account_host', 'sync_test_host'):
        text += f'M\troot\t{module}\t{root / "tests" / (module + ".zi")}\n'
    module_map = work / 'module-map.tsv'
    module_map.write_text(text)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')}
    environment.update(ZIRAN_PACKAGE_MAP=str(module_map), YUE_DESKTOP_RECOVERY='0')
    subprocess.run([str(args.toolchain / 'build/bin/zi2c'), '--define', 'PLATFORM_DESKTOP',
                    '--no-main', '--root', str(root), '--module-path', str(root / 'src'),
                    '-o', str(generated), str(root / 'tests/node_app_snapshot_behavior.zi'),
                    str(root / 'tests/sync_test_host.zi')],
                   cwd=root, env=environment, check=True)
    (generated / 'main.c').write_text(
        '#include "node_app_snapshot_behavior.h"\n#include <stdio.h>\n'
        'int main(void) { int result = Check(); '
        'if (result) fprintf(stderr, "snapshot check %d failed\\n", result); return result; }\n')
    includes = [item for directory in [generated, *sorted(p for p in generated.rglob('*') if p.is_dir())]
                for item in ('-iquote', str(directory))]
    result = subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O0', '-ffunction-sections', '-fdata-sections',
                    '-I' + str(args.toolchain / 'include'), *includes,
                    *map(str, sorted(generated.rglob('*.c'))),
                    str(root / 'vendor-builds/sqlite/sqlite3.c'), str(args.runtime.resolve()),
                    str(root / 'vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a'),
                    '-Wl,--gc-sections', '-lm', '-ldl', '-lpthread', '-o', str(work / 'test')])
    if result.returncode:
        raise SystemExit('Snapshot native link failed; see compiler diagnostics above')
    with tempfile.TemporaryDirectory(prefix='profile-', dir=work) as profile:
        subprocess.run([str(work / 'test')], env=environment | {'APP_DATA_ROOT': profile}, check=True)
    print('Installed-leaf SQLite snapshot: duplicate roots, uninstall visibility, owned assets and revision passed')


if __name__ == '__main__':
    main()
