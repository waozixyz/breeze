"""Check ZIB resource inventories and the small native bootstrap table."""
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from animation_inventory import inventory

def assets(data):
    assert data[:8] == b'ZIB\0\x1a\0\0\0'
    at = 8
    def number():
        nonlocal at
        value = struct.unpack_from('<I', data, at)[0]
        at += 4
        return value
    def take(count):
        nonlocal at
        value = data[at:at + count]
        assert len(value) == count
        at += count
        return value
    def text():
        return take(number())
    text(); text()
    for _ in range(number()):
        text(); text()
    for _ in range(number()):
        for _ in range(7): text()
        take(8); text(); take(4)
    for _ in range(number()):
        for _ in range(3): text()
    take(number())
    result = {}
    for _ in range(number()):
        name = text().decode()
        assert name not in result
        result[name] = take(number())
    assert at == len(data)
    return result

root = assets((ROOT / 'build/inbe.zib').read_bytes())
assert set(name for name in root if name.startswith('cells/')) == {
    'cells/lumi.zib', 'cells/habits.zib', 'cells/practices.zib',
    'cells/lists.zib', 'cells/diary.zib'}
practices = assets(root['cells/practices.zib'])
combined = root | practices
source = '\n'.join(path.read_text(errors='replace') for path in (ROOT / 'src').rglob('*.zi'))
paths = set(re.findall(r'"((?:assets/)?(?:practices|easteregg|pet)/[^"\n]+\.(?:png|jpg|jpeg))"', source))
assert paths
for path in paths:
    path = path if path.startswith('assets/') else 'assets/' + path
    assert path in combined, f'image is absent from package: {path}'
    assert combined[path] == (ROOT / path).read_bytes(), path
for path in ('icons/ui.png', 'icons/pfp.png'):
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
paths, sources, unique_animation = inventory()
packaged_animation = {name for name in practices if '/characters/' in name}
assert packaged_animation == {path.relative_to(ROOT).as_posix() for path in unique_animation}
for index, original in enumerate(paths):
    stored = paths[sources[index]].relative_to(ROOT).as_posix()
    assert practices[stored] == original.read_bytes(), f'animation frame changed: {original}'
native = (ROOT / 'build/obj/inbe_embedded_assets.c').read_text()
entries = set(re.findall(r'\{(?:\(uint8_t \*\))?"([^"\n]+)"', native))
assert entries == {'assets/app/icon.png', 'apps/publishers.json', 'inbe.zib'}, entries
print(f'Package assets: {len(root)} root resources, {len(practices)} Practice resources; exact image/font/locale ownership passed')
