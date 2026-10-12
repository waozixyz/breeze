"""Print the centre of a rendered word in a private UI test screenshot.

Usage: rendered_word.py IMAGE WORD [MIN_Y]. Exits 1 when the word is absent,
so a test can also check that a word is no longer shown.
"""

import csv
import io
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageOps


path = Path(sys.argv[1])
wanted = sys.argv[2].lower()
min_y = int(sys.argv[3]) if len(sys.argv) > 3 else 0
with Image.open(path) as original:
    gray = ImageOps.grayscale(original.convert("RGB"))
ocr_path = path.with_name(path.stem + "-word-ocr.png")


def find(region):
    """The word's centre in one region, read as dark text on a light page."""
    left, top = region[0], region[1]
    part = ImageOps.autocontrast(gray.crop(region))
    histogram = part.histogram()
    if sum(index * count for index, count in enumerate(histogram)) < 128 * sum(histogram):
        part = ImageOps.invert(part)
    part.resize((part.width * 3, part.height * 3)).save(ocr_path)
    try:
        result = subprocess.run(["tesseract", str(ocr_path), "stdout", "--psm", "11",
                                 "-c", "tessedit_create_tsv=1"],
                                text=True, capture_output=True, check=True, timeout=10)
    finally:
        ocr_path.unlink()
    for word in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        if word.get("text", "").strip().lower().strip(".,:()") != wanted:
            continue
        x = left + (int(word["left"]) + int(word["width"]) // 2) // 3
        y = top + (int(word["top"]) + int(word["height"]) // 2) // 3
        if y >= min_y:
            return x, y
    return None


# Buttons with their own backgrounds read better one band at a time, and
# a word beside an icon or a grip reads better in part of its band.
regions = [(0, 0, gray.width, gray.height)]
regions += [(0, top, gray.width, min(top + 80, gray.height))
            for top in range(0, gray.height, 40)]
window = min(240, gray.width)
regions += [(left, top, min(left + window, gray.width), min(top + 80, gray.height))
            for top in range(0, gray.height, 40)
            for left in range(0, max(gray.width - window, 0) + 1, 60)]
for region in regions:
    if region[3] <= min_y:
        continue
    found = find(region)
    if found:
        print(*found)
        sys.exit(0)
sys.exit(1)
