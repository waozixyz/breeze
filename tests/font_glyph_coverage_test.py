#!/usr/bin/env python3
"""The shipped subset fonts contain the glyphs the UI renders and users type.

Fonts used to be checked only as files on disk, which is how a subset
regeneration that dropped ae oe ue ss / e' n~ c~ shipped silently. Invariants:
  1. The Latin subset covers every non-ASCII codepoint of the Latin/Cyrillic
     locale files, the language index, and assets/fonts/input_common.txt (the
     typed-input charset). Those locales render with the Latin font.
  2. Every non-ASCII codepoint of the CJK locale files and the language index
     is in at least one shipped font, so the picker and the cross-font
     fallback can render it.
"""
from pathlib import Path
import sys

from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parent.parent
fonts = {
    "latin": root / "assets/fonts/subset/NotoSans-App-Regular.ttf",
    "sc": root / "assets/fonts/subset/NotoSansSC-App-Regular.otf",
    "jp": root / "assets/fonts/subset/NotoSansJP-App-Regular.otf",
    "kr": root / "assets/fonts/subset/NotoSansKR-App-Regular.otf",
    "tc": root / "assets/fonts/subset/NotoSansTC-App-Regular.otf",
}
LATIN_LOCALES = ["en", "es", "cs", "de", "fr", "id", "it", "pt", "ru"]
CJK_LOCALES = ["ja", "ko", "zh"]


def is_cjk(cp):
    """Scripts that render with the CJK subset fonts, never the Latin one."""
    return (0x2E80 <= cp <= 0x303E or 0x3040 <= cp <= 0x30FF or
            0x3130 <= cp <= 0x318F or 0x3400 <= cp <= 0x4DBF or
            0x4E00 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF or
            0xF900 <= cp <= 0xFAFF or 0xFF00 <= cp <= 0xFFEF)


def codepoints(*paths):
    """Non-ASCII codepoints of the files (ASCII is always covered)."""
    found = set()
    for path in paths:
        for char in path.read_text(encoding="utf-8"):
            cp = ord(char)
            if cp > 0x7F and cp != 0xFEFF:
                found.add(cp)
    return found


def cmap_of(path):
    if not path.exists():
        return None
    return TTFont(path).getBestCmap()


failures = 0
cmaps = {name: cmap_of(path) for name, path in fonts.items()}
if cmaps["latin"] is None:
    print(f"FAIL: cannot parse cmap of {fonts['latin']}", file=sys.stderr)
    sys.exit(1)

latin_needed = codepoints(
    root / "assets/fonts/input_common.txt", root / "locales/index.txt",
    *[root / f"locales/{name}.txt" for name in LATIN_LOCALES])
for cp in sorted(latin_needed):
    if not is_cjk(cp) and cp not in cmaps["latin"]:
        print(f"FAIL: U+{cp:04X} has no glyph in the Latin font", file=sys.stderr)
        failures += 1
print(f"Latin font: {len(latin_needed)} required codepoints, {failures} missing")

cjk_needed = codepoints(
    root / "locales/index.txt", *[root / f"locales/{name}.txt" for name in CJK_LOCALES])
opened = [cmap for cmap in cmaps.values() if cmap is not None]
if not opened:
    print("FAIL: cannot parse any shipped font cmap", file=sys.stderr)
    sys.exit(1)
before = failures
for cp in sorted(cjk_needed):
    if not any(cp in cmap for cmap in opened):
        print(f"FAIL: U+{cp:04X} has no glyph in ANY shipped font", file=sys.stderr)
        failures += 1
print(f"CJK/picker: {len(cjk_needed)} required codepoints checked against "
      f"{len(opened)} fonts, {failures - before} missing")

if failures:
    print(f"font_glyph_coverage tests FAILED ({failures} missing glyphs)", file=sys.stderr)
    sys.exit(1)
print("font_glyph_coverage tests passed")
