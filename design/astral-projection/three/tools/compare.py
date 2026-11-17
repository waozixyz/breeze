#!/usr/bin/env python3
"""Label immutable before/after captures without resizing their source pixels."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'build/astral-compare'
OUTPUT = BASE / 'side-by-side'
OUTPUT.mkdir(exist_ok=True)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
results = []
for capture in json.loads((BASE / 'after/captures.json').read_text()):
    name = capture['name'] + '.png'
    before_path = BASE / 'before' / name
    after_path = BASE / 'after' / name
    before = Image.open(before_path).convert('RGB')
    after = Image.open(after_path).convert('RGB')
    assert before.width == after.width == capture['width'], name
    width = before.width
    height = max(before.height, after.height)
    comparison = Image.new('RGB', (width * 2, height + 58), '#101728')
    comparison.paste(before, (0, 58))
    comparison.paste(after, (width, 58))
    draw = ImageDraw.Draw(comparison)
    draw.text((22, 16), 'BEFORE', font=font, fill='#b5c1d0')
    draw.text((width + 22, 16), 'AFTER · SHADER STUDY', font=font, fill='#a1ecdf')
    comparison.save(OUTPUT / name)
    # Same stage crop, excluding the unchanged player and narration. This
    # detects accidental capture of the old page, not subjective visual quality.
    crop = (12, 340, width - 12, 780) if width < 650 else (40, 240, width - 40, 745)
    difference = ImageChops.difference(before.crop(crop), after.crop(crop))
    mean_change = sum(ImageStat.Stat(difference).mean) / 3
    assert mean_change > 3, f'Unchanged stage: {name}: {mean_change}'
    results.append({
        **capture,
        'before_sha256': hashlib.sha256(before_path.read_bytes()).hexdigest(),
        'after_sha256': hashlib.sha256(after_path.read_bytes()).hexdigest(),
        'stage_mean_channel_change': round(mean_change, 3),
        'comparison': str((OUTPUT / name).relative_to(ROOT)),
    })
(BASE / 'comparison.json').write_text(json.dumps(results, indent=2) + '\n')
print(f'PASS: {len(results)} labelled comparisons; matching widths, cue times and cameras; before originals untouched.')
