"""Check ZX resource inventories and the small native bootstrap table."""
from pathlib import Path
import io
import zipfile
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from animation_inventory import inventory
from practice_content import NAMES, bundle_assets
from practice_media import media_path, packaged_path
from tai_chi_preview import preview_course

def assets(data):
    return bundle_assets(data)

root = assets((ROOT / 'build/inbe.zx').read_bytes())
for name in ('apps', 'diary', 'lists', 'habits', 'practices', 'leaderboard'):
    path = 'assets/apps/icons/' + name + '.png'
    assert root[path] == (ROOT / path).read_bytes(), f'missing or stale launcher icon: {name}'
path = 'assets/app/back-home.avif'
assert root[path] == (ROOT / path).read_bytes(), 'missing or stale graphical Back control'
for name in ('radio', 'library'):
    shape = (ROOT / 'assets' / name / 'sidebar.shape').read_bytes()
    assert root['assets/apps/icons/' + name + '.shape'] == shape
    assert shape.startswith(b'S') and len(shape) < 4096
# Photos comes from the node; the root package carries neither its baseline nor its icon.
assert not any(name.startswith('assets/apps/bundled/photos') or name == 'assets/apps/icons/photos.shape'
               for name in root), 'the root package still bundles Photos'
assert set(name for name in root if name.startswith('cells/')) == {
    'cells/lumi.zx', 'cells/habits.zx', 'cells/practices.zx',
    'cells/lists.zx', 'cells/diary.zx', 'cells/leaderboard.zx'}
practices = assets(root['cells/practices.zx'])
assert not any(name.startswith('assets/practices/ui/') for name in practices), 'unused practice tab art'
assert root['cells/practices.zx'] == (ROOT / 'build/apps/practices.zx').read_bytes(), 'stale embedded Practices'
preview_prefix = 'assets/practices/taichi-preview/'
preview_outline = preview_prefix + 'flat-edge.png'
assert practices[preview_outline] == media_path('assets/practices/taichi/flat-edge.png').read_bytes()
preview, free_spoken = preview_course(media_path('assets/practices/taichi/course.tch').read_bytes())
with zipfile.ZipFile(io.BytesIO(practices[preview_prefix + 'course.zip'])) as archive:
    assert archive.namelist() == ['course.tch']
    assert archive.read('course.tch') == preview, 'packaged preview has stale or paid motion'
codes = [line.split('|', 1)[0] for line in (ROOT / 'locales/index.txt').read_text().splitlines() if '|' in line]
expected_preview_clips = {preview_prefix + voice + '/' + code + '/' + key + '.ogg'
                          for voice in ('voice', 'voice-male') for code in codes for key in free_spoken}
actual_preview_clips = {name for name in practices if name.startswith(preview_prefix) and name.endswith('.ogg')}
assert actual_preview_clips == expected_preview_clips, 'missing free speech or paid-only speech in shipped preview'
for name in sorted(expected_preview_clips):
    relative = name.removeprefix(preview_prefix)
    assert practices[name] == media_path('assets/practices/taichi/' + relative).read_bytes(), name
import json
catalog = json.loads(practices['assets/practices/catalog.json'])
content = {}
for pack in catalog['packs']:
    suffix = ('.' + pack['language'] if pack['language'] else '') + ('.' + pack['voice'] if pack.get('voice') else '')
    data = (ROOT / 'build/practice-content' / (pack['practice'] + suffix + '.zx')).read_bytes()
    from hashlib import sha256
    assert len(data) == pack['size'] and sha256(data).hexdigest() == pack['sha256']
    content.update(assets(data))
# Lumi's guide narration is downloaded per language, never shipped in Lumi.
codes = [line.split('|', 1)[0] for line in (ROOT / 'locales/index.txt').read_text().splitlines() if '|' in line]
assert sorted(pack['language'] for pack in catalog['guide']) == sorted(codes)
for pack in catalog['guide']:
    data = (ROOT / 'build/practice-content' / ('guide.' + pack['language'] + '.zx')).read_bytes()
    assert len(data) == pack['size'] and sha256(data).hexdigest() == pack['sha256']
    spoken = assets(data)
    folder = 'assets/practices/guide/voice/' + pack['language'] + '/'
    assert all(name.startswith(folder) for name in spoken), sorted(spoken)[:3]
    content.update(spoken)
lumi = assets(root['cells/lumi.zx'])
assert not any(name.endswith('.ogg') for name in lumi), [name for name in lumi if name.endswith('.ogg')][:3]
combined = root | practices | content
source = '\n'.join(path.read_text(errors='replace') for path in (ROOT / 'src').rglob('*.zi'))
paths = set(re.findall(r'"((?:assets/)?(?:practices|pet)/[^"\n]+\.(?:png|jpg|jpeg|webp))"', source))
assert paths
for path in paths:
    path = path if path.startswith('assets/') else 'assets/' + path
    assert path in combined, f'image is absent from package: {path}'
    original = path.replace(preview_prefix, 'assets/practices/taichi/', 1)
    assert combined[path] == media_path(original).read_bytes(), path
for path in ('icons/ui.webp', 'icons/pfp.webp'):
    assert root[path] == (ROOT / 'build/packages/kryon' / path).read_bytes()
for file in (ROOT / 'locales').glob('*.txt'):
    assert root['locales/' + file.name] == file.read_bytes()
for file in (ROOT / 'assets/fonts/subset').glob('*-App-Regular.*'):
    path = file.relative_to(ROOT).as_posix()
    assert root[path] == file.read_bytes(), f'stale font in root package: {path}'
assert any(name.startswith('assets/sounds/') for name in practices)
assert not any(name.startswith('assets/practices/') for name in root)
for name in root:
    assert not any(part in name for part in (
        'test-background', 'source-icon', 'readme-', 'badge-', '-prompt.')), \
        f'development artwork shipped: {name}'
assert not any(name.endswith('/banner.png') for name in practices)
# Practice pictures ship only in their packs, apart from every practice's
# banners: Practice's tabs show each practice before it is downloaded.
banner = re.compile(r'assets/practices/[a-z_]+/banner-(?:light|dark)\.webp')
assert not any(name.endswith(('.png', '.webp')) and name != preview_outline and not banner.fullmatch(name)
               for name in practices), \
    [name for name in practices if name.endswith(('.png', '.webp')) and name != preview_outline and not banner.fullmatch(name)]
for name in NAMES:
    for theme in ('light', 'dark'):
        path = f'assets/practices/{name}/banner-{theme}.webp'
        assert practices[path] == media_path(path).read_bytes(), path
# The small practices ship installed with Practices, each its pack's exact
# bytes; Sun Salutation and Tai Chi download.
for name in ('whm', 'meditation', 'patterns', 'astral_projection', 'workout'):
    pack = next(pack for pack in catalog['packs'] if pack['practice'] == name and not pack['language'])
    shipped = practices['assets/practices/default/' + name + '.zx']
    assert len(shipped) == pack['size'] and sha256(shipped).hexdigest() == pack['sha256'], name
assert {name for name in practices if name.startswith('assets/practices/default/')} == {
    'assets/practices/default/' + name + '.zx'
    for name in ('whm', 'meditation', 'patterns', 'astral_projection', 'workout')}
assert not any(name.startswith('assets/practices/shipped/') for name in practices)
paths, sources, unique_animation = inventory()
packaged_animation = {name for name in content if '/characters/' in name}
assert packaged_animation == {packaged_path(path) for path in unique_animation}
for index, original in enumerate(paths):
    stored = packaged_path(paths[sources[index]])
    assert content[stored] == original.read_bytes(), f'animation frame changed: {original}'
assert not any('/characters/' in name or
               (name.endswith('/course.zip') and name != preview_prefix + 'course.zip') for name in practices)
native = (ROOT / 'build/obj/inbe_embedded_assets.c').read_text()
entries = set(re.findall(r'\{(?:\(uint8_t \*\))?"([^"\n]+)"', native))
assert entries == {'assets/app/icon.webp', 'apps/publishers.json', 'inbe.zx', 'apps.zx'}, entries
print(f'Package assets: {len(root)} root resources, {len(practices)} Practice resources; exact image/font/locale ownership passed')
