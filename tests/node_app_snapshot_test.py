"""Check installed apps, background icons and queued images with production SQLite."""
import argparse
import ctypes.util
import hashlib
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import tempfile
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ziran', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='Separate output for a concurrent diagnostic run')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = args.output.resolve() if args.output else root / 'build/node-app-snapshot-test'
    generated = work / 'c'
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                                  'SESSION_MANAGER', 'ZIRAN_PACKAGE_MAP')}
    environment.update(YUE_DESKTOP_RECOVERY='0')
    fixture = work / 'fixtures'
    fixture.mkdir(exist_ok=True)
    source = fixture / 'fixture.zi'
    source.write_text('#program_export\nMain :: () -> s32 { return 1 }\n')
    for name, shape in [('valid', 'S1.6rr:M5 5H10V10H5Z'), ('replacement', 'S1.6rr:M5 5H10V10H5Z'),
                        ('invalid', 'invalid'), ('empty', None)]:
        assets = fixture / name
        assets.mkdir(exist_ok=True)
        if shape is not None:
            (assets / 'sidebar.shape').write_text(shape)
        if name in ('valid', 'replacement'):
            def chunk(kind, data):
                return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
            pixel = bytes([0, 40, 160, 100]) if name == 'valid' else bytes([0, 60, 100, 180])
            (assets / 'picture.png').write_bytes(
                b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(pixel)) + chunk(b'IEND', b''))
        subprocess.run([str(args.ziran.resolve()), 'bundle', '--root', str(fixture),
                        '--entry', 'fixture:Main', '--asset-dir', f'assets/fixture={assets}',
                        '-o', str(fixture / f'{name}.zx'), str(source)],
                       cwd=root, env=environment, check=True)
    (fixture / 'corrupt.zx').write_bytes(b'ZX\0\0invalid envelope')
    package_paths = subprocess.check_output(['sh', str(root / 'scripts/package-paths.sh'),
                                            str(root / 'build/packages')], text=True).splitlines()
    module_paths = [item for path in ('src', 'build/packages/kryon/src/ui', 'build/packages/kryon/src/backend',
                                    'build/packages/kss/src', 'build/packages/game2d/src',
                                    'build/packages/ziran/std',
                                    os.environ.get('DAOCHI_CLIENT_DIR', 'build/packages/daochi-client'))
                    for item in ('--module-path', str(root / path))]
    guest = fixture / 'fixture_app.zi'
    guest.write_text('''#import "kryon/app_context"
#import "kryon/app_protocol"
#program_export
Main :: () -> s32 {
    if AppMode() == APP_IDENTIFY {
        AppIdentity("fixture")
        AppDescribe("Fixture", "")
        return APP_PROTOCOL
    }
    return 0
}
''')
    leaf = fixture / 'leaf.zx'
    packed_root = fixture / 'root.zx'
    packed_assets = fixture / 'root-assets'
    packed_assets.mkdir(exist_ok=True)
    for target, assets in ((leaf, None), (packed_root, packed_assets)):
        command = [str(args.ziran.resolve()), 'bundle', '--root', str(fixture),
                   '--entry', 'fixture_app:Main', *module_paths, *package_paths,
                   '-o', str(target)]
        if assets is not None:
            shutil.copyfile(leaf, packed_assets / 'leaf.zx')
            command += ['--asset-dir', f'assets/fixture={assets}']
        command.append(str(guest))
        subprocess.run(command, cwd=root, env=environment, check=True)
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
    curl_library = os.environ.get('CURL_LIBRARY')
    if not curl_library:
        curl_library = '-l:' + (ctypes.util.find_library('curl') or 'libcurl.so.4')
    result = subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O0', '-ffunction-sections', '-fdata-sections',
                    *shlex.split(os.environ.get('CFLAGS', '')),
                    '-I' + str(root / 'build/packages/ziran/include'), *includes,
                    '-I' + str(root / 'build/packages/monocypher/src'),
                    *map(str, sorted(generated.rglob('*.c'))),
                    str(root / 'tests/node_app_icons_host.c'),
                    str(root / 'build/packages/monocypher/src/monocypher.c'),
                    str(root / 'build/packages/monocypher/src/optional/monocypher-ed25519.c'),
                    str(root / 'vendor-builds/sqlite/sqlite3.c'), str(args.runtime.resolve()),
                    str(root / 'vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a'),
                    '-Wl,--gc-sections', '-Wl,--wrap=BundleOpenBytes',
                    '-Wl,--wrap=storage_user_id_buffer',
                    '-lm', '-ldl', '-lpthread', '-lz',
                    *shlex.split(curl_library),
                    '-o', str(work / 'test')])
    if result.returncode:
        raise SystemExit('Snapshot native link failed; see compiler diagnostics above')
    with tempfile.TemporaryDirectory(prefix='profile-', dir=work) as profile:
        subprocess.run([str(work / 'test')], env=environment | {
            'APP_DATA_ROOT': profile,
            'ICON_CACHE_PATH': str(Path(profile) / 'fixture.icon'),
            'IMAGE_REPLACEMENT_BUNDLE': str(fixture / 'replacement.zx'),
            'NODE_OPEN_ROOT_BUNDLE': str(packed_root),
            'NODE_OPEN_ROOT_SHA256': hashlib.sha256(packed_root.read_bytes()).hexdigest(),
            'NODE_OPEN_LEAF_SHA256': hashlib.sha256(leaf.read_bytes()).hexdigest(),
            **{f'ICON_{name.upper()}_BUNDLE': str(fixture / f'{name}.zx')
               for name in ('valid', 'invalid', 'empty', 'corrupt')},
        }, check=True)
    print('Installed apps: leaf discovery, background icons, stale-job isolation, deferred images and shared mappings passed')


if __name__ == '__main__':
    main()
