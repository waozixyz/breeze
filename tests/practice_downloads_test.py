"""Exercise actual content mounting, offline cache and language downloads."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from practice_content import NAMES

work = Path(os.environ.get('INBE_PRACTICE_TEST_OUTPUT', str(ROOT / 'build/practice-downloads-test')))
if work.exists():
    shutil.rmtree(work)
work.mkdir(parents=True)
fixtures = work / 'fixtures'
(fixtures / 'cache/packages').mkdir(parents=True)
compiler = ROOT / 'build/ziran-toolchain/bin/ziran'
packs = []
for name in NAMES:
    data = (ROOT / 'build/practice-content' / (name + '.zib')).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    (fixtures / (digest + '.zib')).write_bytes(data)
    pack = dict(practice=name, language='', sha256=digest, size=len(data))
    if name == 'taichi':
        pack['product'] = 'inbe.practice.taichi'
    packs.append(pack)
for code in ('en', 'es'):
    assets = work / code / 'assets'
    voice = assets / ('practices/taichi/voice/' + code)
    voice.mkdir(parents=True)
    (voice / 'test.ogg').write_bytes(b'fixture audio')
    bundle = work / (code + '.zib')
    subprocess.run([str(compiler), 'bundle', '--root', str(ROOT), '--entry', 'content:Main',
        '--asset-dir', 'assets=' + str(assets), '-o', str(bundle),
        str(ROOT / 'apps/practice/content.zi')], check=True)
    data = bundle.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    (fixtures / (digest + '.zib')).write_bytes(data)
    packs.append(dict(practice='taichi', language=code, sha256=digest, size=len(data),
                      product='inbe.practice.taichi'))
# The male recording is a separate English pack in its own folder.
assets = work / 'en-male' / 'assets'
voice = assets / 'practices/taichi/voice-male/en'
voice.mkdir(parents=True)
(voice / 'test.ogg').write_bytes(b'fixture male audio')
bundle = work / 'en-male.zib'
subprocess.run([str(compiler), 'bundle', '--root', str(ROOT), '--entry', 'content:Main',
    '--asset-dir', 'assets=' + str(assets), '-o', str(bundle),
    str(ROOT / 'apps/practice/content.zi')], check=True)
data = bundle.read_bytes()
digest = hashlib.sha256(data).hexdigest()
(fixtures / (digest + '.zib')).write_bytes(data)
packs.append(dict(practice='taichi', language='en', voice='male', sha256=digest, size=len(data),
                  product='inbe.practice.taichi'))
# Lumi's guide lists its narration on its own, one free pack per language.
assets = work / 'guide-en' / 'assets'
voice = assets / 'practices/guide/voice/en'
voice.mkdir(parents=True)
(voice / 'test.ogg').write_bytes(b'fixture guide audio')
bundle = work / 'guide-en.zib'
subprocess.run([str(compiler), 'bundle', '--root', str(ROOT), '--entry', 'content:Main',
    '--asset-dir', 'assets=' + str(assets), '-o', str(bundle),
    str(ROOT / 'apps/practice/content.zi')], check=True)
data = bundle.read_bytes()
digest = hashlib.sha256(data).hexdigest()
(fixtures / (digest + '.zib')).write_bytes(data)
guide = [dict(language='en', sha256=digest, size=len(data))]
(fixtures / 'catalog.json').write_text(json.dumps(dict(schema=1, packs=packs, guide=guide)) + '\n')
(fixtures / 'default-whm.zib').write_bytes((ROOT / 'build/practice-content/whm.zib').read_bytes())
(fixtures / 'shipped-patterns.zib').write_bytes((ROOT / 'build/practice-content/patterns.zib').read_bytes())
# Stale content in a stable cache slot must be verified and replaced.
(fixtures / 'cache/packages/practice-whm.zib').write_bytes(b'old release')
(fixtures / 'cache/packages/practice-taichi.fr.zib').write_bytes(b'retired language')
preserved = {
    'progress.json': b'preserve progress',
    'practice-taichi.bad.zib': b'unrelated file',
    'practice-taichix.zib': b'other namespace',
}
for name, data in preserved.items():
    (fixtures / 'cache/packages' / name).write_bytes(data)
generated = work / 'generated'
arguments = [str(compiler), 'build', '--target=c', '--no-main', '--root', str(ROOT / 'tests'),
             '--define', 'PLATFORM_DESKTOP']
for path in ('src', 'build/packages/ziran/std', 'build/packages/kryon/src/ui',
             'build/packages/kryon/src/backend', 'build/packages/daochi-client'):
    arguments += ['--module-path', str(ROOT / path)]
arguments += ['--module-path', 'oqs=' + str(ROOT / 'build/packages/oqs/src'),
              '--module-path', 'kryon=' + str(ROOT / 'build/packages/kryon/src/ui')]
subprocess.run([*arguments, '-o', str(generated), str(ROOT / 'tests/practice_downloads_behavior.zi')], check=True)
monocypher = ROOT / 'build/packages/monocypher/src'
subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-D_GNU_SOURCE', '-O1',
    '-ffunction-sections', '-fdata-sections', '-I' + str(generated),
    '-I' + str(ROOT / 'build/packages/ziran/include'), '-I' + str(monocypher),
    '-I' + str(monocypher / 'optional'), str(ROOT / 'tests/practice_downloads_host.c'),
    *map(str, generated.rglob('*.c')), str(monocypher / 'monocypher.c'),
    str(monocypher / 'optional/monocypher-ed25519.c'),
    str(ROOT / 'build/ziran-toolchain/libziran.a'), '-Wl,--gc-sections',
    '-Wl,--wrap=file_download_FileDownloadStart', '-Wl,--wrap=file_download_FileDownloadPoll',
    '-Wl,--wrap=file_download_FileDownloadRelease', '-Wl,--wrap=storage_db_path',
    '-Wl,--wrap=Sha256Hex',
    '-lm', '-pthread', '-o', str(work / 'test')], check=True)
subprocess.run([str(work / 'test'), str(fixtures)], check=True, timeout=120,
               env={key: value for key, value in os.environ.items()
                    if key not in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')})
cache = fixtures / 'cache/packages'
assert not list(cache.glob('practice-taichi.??.zib'))
# Removing Tai Chi forgets its removed languages; Lumi's guide keeps its own.
assert not list(cache.glob('practice-taichi.*.removed'))
assert (cache / 'practice-guide.en.removed').exists()
# Wim Hof ends installed from the app's own copy, with no removal marker.
assert not (cache / 'practice-whm.zib').exists() and not (cache / 'practice-whm.removed').exists()
for name, data in preserved.items():
    assert (cache / name).read_bytes() == data
print('Practice downloads: verified content, corrupt-download retry, offline cache, narration in the app '
      "language, chosen and removed languages, Lumi's guide narration, removal, shipped Wim Hof, granted "
      'paid packs, and Sun Salutation downloading and updating an older copy passed')
