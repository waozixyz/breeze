#!/usr/bin/env python3
"""Decode every shipped frame set and validate the runtime crop geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedded-c", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "docs/sun-salutation-characters.json").read_text())
    table = (ROOT / "src/practices/sun_salutation/sun_salutation_frames.zi").read_text()
    characters = manifest["characters"]
    # The woman and the man, for the first round and for the next one, in
    # which the other leg steps back first.
    assert len(characters) == 4, "The woman and the man must ship on both sides"
    assert [c["other_side"] for c in characters] == [False, False, True, True], "Frame sets out of order"
    assert f"SUN_SALUTATION_FRAME_SETS :: {len(characters)}" in table, "Frame set count differs"
    stage = manifest["stage"]
    directories = re.findall(r'"(assets/practices/sunsalutation/characters/[^\"]+/)"', table)
    assert directories == [c["directory"] for c in characters], "Runtime character order differs"
    embedded = set()
    if args.embedded_c:
        for line in args.embedded_c.open():
            match = re.search(r'\{(?:\(uint8_t \*\))?"([^"]+)"', line)
            if match:
                embedded.add(match[1])
    total = 0
    held_signatures = set()
    lunges = {}
    for character in characters:
        assert character["fps"] == 30 and character["transition_frames"] == 90
        assert character["move_frames"] >= character["transition_frames"]
        assert len(character["steps"]) == 12
        expected = set()
        directory = ROOT / character["directory"]
        for step, entry in enumerate(character["steps"]):
            assert entry["frames"] == (1 if step == 0 else character["move_frames"])
            left, top, right, bottom = entry["box"]
            assert stage["left"] <= left < right <= stage["left"] + stage["width"]
            assert stage["top"] <= top < bottom <= stage["top"] + stage["height"]
            hx, hy, hr, hb = entry["held"]
            assert 0 <= hx < hr <= right - left
            assert 0 <= hy < hb <= bottom - top
            for index in range(entry["frames"]):
                filename = f"{step + 1:02d}-{index + 1:03d}.png"
                expected.add(filename)
                path = directory / filename
                with Image.open(path) as image:
                    image.load()
                    assert image.size == (right - left, bottom - top), str(path)
                    rgba = image.convert("RGBA")
                    alpha = rgba.getchannel("A")
                    assert alpha.getbbox(), "Empty frame: " + str(path)
                    assert alpha.getextrema()[0] == 0, "Opaque background: " + str(path)
                    if step == 0:
                        held_signatures.add(hashlib.sha256(rgba.tobytes()).hexdigest())
                    if step == 3 and index == entry["frames"] - 1:
                        lunges[character["id"]] = hashlib.sha256(rgba.tobytes()).hexdigest()
                if args.embedded_c:
                    assert str(path.relative_to(ROOT)) in embedded, "Frame not embedded: " + str(path)
                total += 1
        assert {p.name for p in directory.glob("*.png")} == expected, "Missing or stale frames"
    assert len(held_signatures) == 2, "The two characters must have distinct artwork"
    for first, other in zip(characters[:2], characters[2:]):
        assert lunges[first["id"]] != lunges[other["id"]], "The next round must lunge on the other leg"
    assert not (ROOT / "assets/practices/sunsalutation/girl").exists(), "Retired character still ships"
    print(f"Validated {total} transparent frames: two characters on both sides, twelve poses each")


if __name__ == "__main__":
    main()
