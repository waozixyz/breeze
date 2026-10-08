"""Locate Yoga's controls in the screenshot taken by the private UI test."""

import csv
import io
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageChops, ImageOps


path = Path(sys.argv[1])
with Image.open(path) as original:
    image = original.convert("RGB")
gray = ImageOps.autocontrast(ImageOps.invert(ImageOps.grayscale(image)))
ocr_path = path.with_name(path.stem + "-ocr.png")
gray.resize((gray.width * 3, gray.height * 3)).save(ocr_path)
try:
    result = subprocess.run(["tesseract", str(ocr_path), "stdout", "--psm", "11",
                             "-c", "tessedit_create_tsv=1"],
                            text=True, capture_output=True, check=True, timeout=10)
finally:
    ocr_path.unlink()
words = []
for word in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
    if word.get("text", "").strip():
        words.append({"text": word["text"].lower(),
                      **{key: round(int(word[key]) / 3)
                         for key in ("left", "top", "width", "height")}})
yoga = next((word for word in words if word["text"] == "yoga"), None)
assert yoga, "The Habits fixture did not render Yoga"


def center_of_ink(bounds):
    tile = image.crop(bounds)
    colors = tile.getcolors(tile.width * tile.height)
    background = max(colors)[1]
    difference = ImageChops.difference(tile, Image.new("RGB", tile.size, background))
    red, green, blue = difference.split()
    strongest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    box = strongest.point(lambda value: 255 if value > 10 else 0).getbbox()
    assert box, f"Rendered control is missing from {bounds}"
    return bounds[0] + (box[0] + box[2]) // 2, bounds[1] + (box[1] + box[3]) // 2


if sys.argv[2] == "chevron":
    # The circular action is aligned with the rendered habit heading.
    print(*center_of_ink((image.width - 75, yoga["top"] - 5,
                          image.width - 25, yoga["top"] + 45)))
else:
    today = min((word for word in words if word["text"] == "today"
                 and word["top"] > yoga["top"] and word["left"] < image.width // 4),
                key=lambda word: word["top"])
    x = today["left"] + today["width"] // 2
    bottom = today["top"] + today["height"]
    position = center_of_ink((x - 14, bottom + 5, x + 14, bottom + 42))
    text = " ".join(word["text"] for word in words)
    if sys.argv[2] == "expanded":
        assert "week" in text and "streak" in text, "Yoga never expanded before the day gesture"
    else:
        assert "streak" not in text, "Yoga remained expanded after collapse"
    print(*position)
