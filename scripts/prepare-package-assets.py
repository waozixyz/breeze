#!/usr/bin/env python3
"""Stage deterministic package resources, keeping large practice art in Practices."""
from pathlib import Path
import json
import shutil
import zipfile
from animation_inventory import inventory

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'build/package-assets'
_, _, unique_animation = inventory()
unique_animation = set(unique_animation)
# Apps the node offers each keep their assets/<name>/ in their own package.
NODE_APPS = tuple(sorted(json.loads((ROOT / 'apps/versions.json').read_text()).get('node_apps', {})))
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
for name in ('inbe', 'lists', 'habits', 'practices', 'diary', 'lumi', 'leaderboard',
             'practice-whm', 'practice-meditation', 'practice-sunsalutation',
             'practice-patterns', 'practice-taichi') + NODE_APPS:
    (OUTPUT / name / 'assets').mkdir(parents=True)
patterns = (
    'assets/mcp/*.json', 'assets/app/icon.png', 'assets/app/icon-sky-cradle.png',
    'assets/app/icon-ink-and-air.png', 'assets/easteregg/*.png', 'assets/pet/*.png',
    'assets/social/*.png', 'assets/profile-pictures/*.png',
    'assets/practices/whm/1.png', 'assets/practices/whm/2.png',
    'assets/practices/meditation/1.png', 'assets/practices/*/banner-light.png',
    'assets/practices/*/banner-dark.png',
    'assets/practices/sunsalutation/characters/*/*.png',
    'assets/practices/sunsalutation/voice/**/*', 'assets/practices/sunsalutation/voice-male/**/*',
    'assets/practices/taichi/**/*', 'assets/practices/guide/voice/**/*',
    'assets/sounds/*.ogg',
    'assets/habits/**/*', 'assets/lists/**/*', 'assets/diary/**/*', 'assets/lumi/**/*',
    'assets/fonts/subset/*-App-Regular.*', 'assets/styles/*.kss',
    'locales/*.txt', 'themes/catalog_*.kss',
    'build/packages/kss/styles/*.kss', 'build/packages/kryon/icons/ui.png',
    'build/packages/kryon/icons/pfp.png',
) + tuple(f'assets/{name}/**/*' for name in NODE_APPS)
for file in sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()}):
    if '-prompt.' in file.name:
        continue
    if '/sunsalutation/characters/' in file.as_posix() and file not in unique_animation:
        continue
    path = file.relative_to(ROOT).as_posix()
    owner = 'inbe'
    if path.startswith(('assets/practices/', 'assets/sounds/')):
        owner = 'practices'
    # Each practice's pictures, banners included, ship only in its pack.
    if path.startswith('assets/practices/'):
        practice = path.split('/')[2]
        owner = 'practice-' + practice
        if '/voice/' in path:
            code = path.split('/voice/', 1)[1].split('/')[0]
            owner += '-voice-' + code
        elif '/voice-male/' in path:
            # The male recording is its own pack per language.
            code = path.split('/voice-male/', 1)[1].split('/')[0]
            owner += '-voice-' + code + '-male'
    for feature in ('habits', 'lists', 'diary', 'lumi') + NODE_APPS:
        if path.startswith('assets/' + feature + '/'):
            owner = feature
    for prefix in ('build/packages/kss/', 'build/packages/kryon/'):
        if path.startswith(prefix):
            path = path.removeprefix(prefix)
    target = OUTPUT / owner / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if path == 'assets/practices/taichi/course.bin':
        # Keep the exported data exact; only its packaged representation is
        # compressed. Fixed metadata makes repeated builds byte-identical.
        member = zipfile.ZipInfo('course.bin', (1980, 1, 1, 0, 0, 0))
        member.create_system = 3
        member.compress_type = zipfile.ZIP_DEFLATED
        member.external_attr = 0o644 << 16
        with zipfile.ZipFile(target.with_suffix('.zip'), 'w') as archive:
            archive.writestr(member, file.read_bytes(), compresslevel=9)
        continue
    shutil.copyfile(file, target)

# Diary's own translations travel with its bundle for other harnesses and
# the generic player; it does not need the Inner Breeze root package.
for locale in sorted((ROOT / 'locales').glob('*.txt')):
    entries = []
    for block in locale.read_text().split('---\n'):
        first = block.splitlines()[0] if block.splitlines() else ''
        if first.startswith(('[diary_', '[tab_diary', '[habit_day_', '[habit_month_')):
            entries.append(block.rstrip() + '\n---\n')
    target = OUTPUT / 'diary/locales' / locale.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(''.join(entries))
