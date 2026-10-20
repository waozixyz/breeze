#!/usr/bin/env python3
"""Stage deterministic package resources, keeping large practice art in Practices."""
from pathlib import Path
import argparse
import json
import shutil
import zipfile
import os
import hashlib
import re
from animation_inventory import inventory

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default='build/package-assets',
                    help='Build directory for staged package assets')
options = parser.parse_args()
OUTPUT = (ROOT / options.output).resolve()
if not OUTPUT.is_relative_to(ROOT / 'build') or OUTPUT == ROOT / 'build':
    parser.error('output must be a directory below the project build directory')
_, _, unique_animation = inventory()
unique_animation = set(unique_animation)
# Apps the node offers each keep their assets/<name>/ in their own package.
NODE_APPS = tuple(sorted(json.loads((ROOT / 'apps/versions.json').read_text()).get('node_apps', {})))
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
for name in ('inbe', 'lists', 'habits', 'practices', 'diary', 'lumi', 'leaderboard',
             'practice-whm', 'practice-meditation', 'practice-sunsalutation',
             'practice-patterns', 'practice-taichi', 'practice-astral_projection',
             'practice-workout') + NODE_APPS:
    (OUTPUT / name / 'assets').mkdir(parents=True)
patterns = (
    'assets/mcp/*.json', 'assets/app/icon.png', 'assets/app/icon-sky-cradle.png',
    'assets/app/icon-ink-and-air.png', 'assets/easteregg/*.png', 'assets/pet/*.png',
    'assets/social/*.png', 'assets/profile-pictures/*.png',
    'assets/practices/whm/1.png', 'assets/practices/whm/2.png',
    'assets/practices/meditation/1.png', 'assets/practices/*/banner-light.png',
    'assets/practices/*/banner-dark.png',
    'assets/practices/sunsalutation/characters/*/*.png',
    'assets/practices/sunsalutation/flat-edge.png',
    'assets/practices/sunsalutation/voice/**/*', 'assets/practices/sunsalutation/voice-male/**/*',
    'assets/practices/astral_projection/**/*',
    'assets/practices/workout/**/*',
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
    # Each practice's pictures ship only in its pack. Its banners ship with
    # Practices, whose tabs show every practice before it is downloaded.
    if path.startswith('assets/practices/') and '/banner-' not in path:
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

# Root launcher cards share the reviewed Apps controller. A node-only build
# can omit it; the root bundle build below requires this asset explicitly.
apps_bundle = ROOT / 'build/apps-ui/apps.zib'
if apps_bundle.is_file():
    controller = apps_bundle.read_bytes()
    source = (ROOT / 'src/cells/apps_controller.zi').read_text()
    expected = re.search(r'AppsControllerSha256\s*::\s*"([0-9a-f]{64})"', source)
    if not expected or hashlib.sha256(controller).hexdigest() != expected[1]:
        raise SystemExit('Apps controller differs from the reviewed native digest')
    destination = OUTPUT / 'inbe/assets/apps/apps.zib'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(controller)

# Preserve the existing launcher atlas art as complete packed images. The
# portable card needs no native atlas handle or renderer-specific crop state.
from PIL import Image
with Image.open(OUTPUT / 'inbe/icons/ui.png') as atlas:
    for name, x, y in (('diary', 64, 448), ('lists', 320, 0), ('habits', 128, 448),
                       ('practices', 192, 448), ('leaderboard', 192, 320)):
        destination = OUTPUT / 'inbe/assets/apps/icons' / (name + '.png')
        destination.parent.mkdir(parents=True, exist_ok=True)
        atlas.crop((x, y, x + 64, y + 64)).save(destination)

# Each app owns its bounded achievement catalog and translations, including
# optional node apps. Source presence never determines device visibility.
for catalog in sorted((ROOT / 'apps').glob('*/achievements.json')):
    source_name = catalog.parent.name
    owner = 'practices' if source_name == 'practice' else source_name
    resource_name = 'app' if owner == 'inbe' else owner
    destination = OUTPUT / owner / 'assets' / resource_name
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(catalog, destination / 'achievements.json')
    for translation in sorted((catalog.parent / 'achievement-locales').glob('*.json')):
        target = destination / 'achievement-locales' / translation.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(translation, target)

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
