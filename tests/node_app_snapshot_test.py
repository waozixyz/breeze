"""Check installed apps, background icons and queued images with production SQLite."""
import argparse
from contextlib import nullcontext
from photos_client_fixture import photos_client_fixture
import ctypes.util
import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import tempfile
import zlib
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ziran', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--controller', type=Path, help='The reviewed Apps controller used by this build')
    parser.add_argument('--photos-module', type=Path, help='Test this actual current Photos module through signed local download')
    parser.add_argument('--legacy-photos-module', type=Path, help='Validate an exact published legacy Photos bundle')
    parser.add_argument('--output', type=Path, help='Separate output for a concurrent diagnostic run')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    controller = args.controller.resolve() if args.controller else root / 'build/apps-ui/apps.zx'
    work = args.output.resolve() if args.output else root / 'build/node-app-snapshot-test'
    generated = work / 'c'
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                                  'SESSION_MANAGER', 'ZIRAN_PACKAGE_MAP')}
    environment.update(HARMONY_DESKTOP_RECOVERY='0', YUE_DESKTOP_RECOVERY='0')
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
        command = [str(args.ziran.resolve()), 'bundle', '--project', '--offline',
                   '--root', str(root), '--module-path', str(fixture),
                   '--entry', 'fixture_app:Main',
                   '-o', str(target)]
        if assets is not None:
            shutil.copyfile(leaf, packed_assets / 'leaf.zx')
            command += ['--asset-dir', f'assets/fixture={assets}']
        command.append(str(guest))
        subprocess.run(command, cwd=root, env=environment, check=True)
    sys.path.insert(0, str(root / 'build/packages/apps/scripts'))
    from node_release import signing_message
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    publishers = [dict(key_id='baseline', public_key='1' * 64, app_ids=['inbe.fixture', 'inbe.photos', 'inbe.diary']),
                  dict(key_id='other', public_key=public, app_ids=['inbe.fixture']),
                  dict(key_id='outside', public_key='3' * 64, app_ids=['inbe.someone-else'])]
    photos_key = Ed25519PrivateKey.generate()
    photos_public = photos_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    publishers.append(dict(key_id='photos-fixture', public_key=photos_public, app_ids=['inbe.photos']))
    publishers += json.loads((root / 'apps/publishers.json').read_text())
    (fixture / 'publishers.json').write_text(json.dumps(publishers))
    sys.path.insert(0, str(root / 'scripts'))
    from practice_content import bundle_assets
    # Read only release metadata from the complete local root, keeping large
    # embedded media out of the fixture's Python heap. Network packs retain
    # the resource parser's default bound.
    with (root / 'build/inbe.zx').open('rb') as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            root_assets = bundle_assets(data, maximum=128 * 1024 * 1024,
                include_paths={'assets/apps/bundled/releases.json'})
    arcade_assets = bundle_assets((root / 'apps/bundled/arcade.zx').read_bytes())
    arcade_art = json.loads(arcade_assets['assets/apps/catalog.json'])['art']['sha256'] + '.zx'
    (fixture / 'embedded-releases.json').write_bytes(root_assets['assets/apps/bundled/releases.json'])
    release = dict(app_id='inbe.fixture', sequence=2, version='2.0.0', runtime='kryon-app-v1',
                   host_api=43, module_api=2, data_schema=0, key_id='other', dependencies=[],
                   artifacts=[dict(variant='module', sha256=hashlib.sha256(packed_root.read_bytes()).hexdigest(),
                                   size=packed_root.stat().st_size)])
    release['signature'] = key.sign(signing_message(release)).hex()
    (fixture / 'update.json').write_text(json.dumps(release))
    subprocess.run([str(args.ziran.resolve()), 'build', '--target=c', '--project', '--offline',
                    '--define', 'PLATFORM_DESKTOP', '--no-main', '--root', str(root / 'tests'),
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
                    '-Wl,--wrap=TraceLog',
                    '-Wl,--wrap=storage_user_id_buffer',
                    '-lm', '-ldl', '-lpthread', '-lz',
                    *shlex.split(curl_library),
                    '-o', str(work / 'test')])
    if result.returncode:
        raise SystemExit('Snapshot native link failed; see compiler diagnostics above')
    server = photos_client_fixture(args.photos_module, photos_key, signing_message) if args.photos_module else nullcontext({})
    with tempfile.TemporaryDirectory(prefix='profile-', dir=work) as profile, server as photos_env:
        (Path(profile) / 'packages').mkdir()
        subprocess.run([str(work / 'test')], env=environment | {
            'APP_DATA_ROOT': profile,
            **photos_env,
            'PHOTOS_LEGACY_MODULE': str(args.legacy_photos_module.resolve()) if args.legacy_photos_module else '',
            'ICON_CACHE_PATH': str(Path(profile) / 'fixture.icon'),
            'IMAGE_REPLACEMENT_BUNDLE': str(fixture / 'replacement.zx'),
            'NODE_OPEN_ROOT_BUNDLE': str(packed_root),
            'NODE_OPEN_ROOT_SHA256': hashlib.sha256(packed_root.read_bytes()).hexdigest(),
            'NODE_OPEN_LEAF_SHA256': hashlib.sha256(leaf.read_bytes()).hexdigest(),
            'NODE_OPEN_LEAF_BUNDLE': str(leaf),
            'NODE_EMBEDDED_PUBLISHERS': str(fixture / 'publishers.json'),
            'NODE_EMBEDDED_UPDATE': str(fixture / 'update.json'),
            'NODE_EMBEDDED_REAL_METADATA': str(fixture / 'embedded-releases.json'),
            'NODE_EMBEDDED_ARCADE': str(root / 'apps/bundled/arcade.zx'),
            'NODE_EMBEDDED_ART': str(root / 'apps/bundled/arcade.games' / arcade_art),
            'NODE_EMBEDDED_ART_PATH': 'assets/apps/bundled/arcade/' + arcade_art,
            'NODE_EMBEDDED_CONTROLLER': str(controller),
            **{f'ICON_{name.upper()}_BUNDLE': str(fixture / f'{name}.zx')
               for name in ('valid', 'invalid', 'empty', 'corrupt')},
        }, check=True)
    if args.legacy_photos_module:
        print('Legacy Photos module: launcher validation and read-only identification passed')
    if args.photos_module:
        print('Actual Photos module: corrupt retries rejected; terminal state retained during metadata check; explicit signed retry, portrait/desktop wrench grant and offline reopen passed')
    print('Installed apps: leaf discovery, background icons, stale-job isolation, deferred images and shared mappings passed')
    print('Photos compression: grant queues once; wrong app, publisher, account, validation, scanning and malformed request rejected')
    print('Embedded apps: identity, publisher scope, API, size and digest rejection; fallback publisher binding; newer signed update precedence; actual Arcade with complete art and no games opened offline')


if __name__ == '__main__':
    main()
