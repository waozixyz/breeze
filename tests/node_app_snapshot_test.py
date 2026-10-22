"""Run installed-leaf discovery against production SQLite and locked packages."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ziran', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = root / 'build/node-app-snapshot-test'
    generated = work / 'c'
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                                  'ZIRAN_PACKAGE_MAP')}
    environment.update(YUE_DESKTOP_RECOVERY='0')
    package_paths = subprocess.check_output(['sh', str(root / 'scripts/package-paths.sh'),
                                            str(root / 'build/packages')], text=True).splitlines()
    module_paths = [item for path in ('src', 'build/packages/kryon/src/ui', 'build/packages/kryon/src/backend',
                                    'build/packages/kss/src', 'build/packages/game2d/src',
                                    'build/packages/ziran/std', 'build/packages/daochi-client')
                    for item in ('--module-path', str(root / path))]
    subprocess.run([str(args.ziran.resolve()), 'build', '--target=c', '--define', 'PLATFORM_DESKTOP',
                    '--no-main', '--root', str(root / 'tests'), *module_paths, *package_paths,
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
                    '-I' + str(root / 'build/packages/ziran/include'), *includes,
                    *map(str, sorted(generated.rglob('*.c'))),
                    str(root / 'vendor-builds/sqlite/sqlite3.c'), str(args.runtime.resolve()),
                    str(root / 'vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a'),
                    '-Wl,--gc-sections', '-lm', '-ldl', '-lpthread', '-o', str(work / 'test')])
    if result.returncode:
        raise SystemExit('Snapshot native link failed; see compiler diagnostics above')
    with tempfile.TemporaryDirectory(prefix='profile-', dir=work) as profile:
        subprocess.run([str(work / 'test')], env=environment | {'APP_DATA_ROOT': profile}, check=True)
    print('Installed-leaf SQLite snapshot: duplicate roots, visibility, owned assets, incremental discovery and safe cancellation passed')


if __name__ == '__main__':
    main()
