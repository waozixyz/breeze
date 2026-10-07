#!/usr/bin/env python3
"""Stage deterministic package resources, keeping large practice art in Practices."""
from pathlib import Path
import shutil
from animation_inventory import inventory

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'build/package-assets'
_, _, unique_animation = inventory()
unique_animation = set(unique_animation)
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
for name in ('inbe', 'lists', 'habits', 'practices', 'diary', 'lumi'):
    (OUTPUT / name / 'assets').mkdir(parents=True)
patterns = (
    'assets/mcp/*.json', 'assets/app/icon.png', 'assets/app/icon-sky-cradle.png',
    'assets/app/icon-ink-and-air.png', 'assets/easteregg/*.png', 'assets/pet/*.png',
    'assets/social/*.png', 'assets/profile-pictures/*.png',
    'assets/practices/whm/1.png', 'assets/practices/whm/2.png',
    'assets/practices/meditation/1.png', 'assets/practices/*/banner-light.png',
    'assets/practices/*/banner-dark.png',
    'assets/practices/sunsalutation/characters/*/*.png', 'assets/sounds/*.ogg',
    'assets/habits/**/*', 'assets/lists/**/*', 'assets/diary/**/*', 'assets/lumi/**/*',
    'assets/fonts/subset/*-App-Regular.*', 'assets/styles/*.kss',
    'locales/*.txt', 'themes/catalog_*.kss',
    'build/packages/kss/styles/*.kss', 'build/packages/kryon/icons/ui.png',
    'build/packages/kryon/icons/pfp.png',
)
for file in sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()}):
    if '-prompt.' in file.name:
        continue
    if '/sunsalutation/characters/' in file.as_posix() and file not in unique_animation:
        continue
    path = file.relative_to(ROOT).as_posix()
    owner = 'inbe'
    if path.startswith(('assets/practices/', 'assets/sounds/')):
        owner = 'practices'
    for feature in ('habits', 'lists', 'diary', 'lumi'):
        if path.startswith('assets/' + feature + '/'):
            owner = feature
    for prefix in ('build/packages/kss/', 'build/packages/kryon/'):
        if path.startswith(prefix):
            path = path.removeprefix(prefix)
    target = OUTPUT / owner / path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file, target)
