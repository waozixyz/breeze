#!/usr/bin/env python3
"""Cuts a painted character's part sheets into transparent part images.

    python3 tools/cut-parts.py characters/monk

Reads `sheets.json` in the character folder. Each sheet is an image on a
plain white background split into equal tiles; each named tile holds one
isolated part. The part is the painted area connected to its largest
piece: white that is reachable from the tile border is background. Edge
pixels recover their coverage and colour from the white they were painted
on, and transparent pixels take the colour of the nearest paint so that
filtered textures do not show a white or black fringe.

A sheet's `fade` names parts whose cut edges fade out under the part that
covers them (see `fade`). Writes `parts/<name>.png`, cropped with a small
margin, and
`parts/parts.json` with each part's size and its position in the sheet.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

WHITE_LEVEL = 236
MARGIN = 6


def background_mask(rgb):
    """White pixels connected to the tile border."""
    near_white = rgb.min(axis=2) >= WHITE_LEVEL
    seeds = np.zeros(near_white.shape, bool)
    seeds[0, :] = seeds[-1, :] = seeds[:, 0] = seeds[:, -1] = True
    return ndimage.binary_propagation(seeds & near_white, mask=near_white)


def cut_tile(tile):
    rgb = np.asarray(tile.convert("RGB")).astype(np.float64)
    background = background_mask(rgb.astype(np.uint8))
    painted = ~background
    labels, count = ndimage.label(painted)
    if count == 0:
        raise RuntimeError("empty tile")
    areas = ndimage.sum(np.ones_like(labels), labels, index=np.arange(1, count + 1))
    largest = areas.max()
    # Keep the main piece and any sizeable piece near it (an ear, a strap);
    # drop specks.
    keep = np.zeros_like(painted)
    for index, area in enumerate(areas, start=1):
        if area >= 0.02 * largest:
            keep |= labels == index
    keep = ndimage.binary_fill_holes(keep)
    # Coverage: inside the piece the paint is opaque; on its outer rim the
    # painted contour was blended with white, so coverage is how far the
    # pixel's darkest channel is from white.
    rim = keep & ~ndimage.binary_erosion(keep, iterations=2)
    darkest = rgb.min(axis=2)
    rim_coverage = np.clip((250.0 - darkest) / (250.0 - 140.0), 0.0, 1.0)
    alpha = np.where(keep, 1.0, 0.0)
    alpha = np.where(rim, rim_coverage, alpha)
    # Un-blend rim colours from white: c = a * paint + (1 - a) * 255.
    safe = np.maximum(alpha, 1e-3)[..., None]
    colour = np.where(alpha[..., None] < 0.999, (rgb - (1.0 - alpha[..., None]) * 255.0) / safe, rgb)
    colour = np.clip(colour, 0, 255)
    # Bleed colour into transparent pixels from the nearest opaque pixel.
    solid = alpha > 0.6
    if solid.any():
        _, (rows, cols) = ndimage.distance_transform_edt(~solid, return_indices=True)
        colour = np.where(solid[..., None], colour, colour[rows, cols])
    rgba = np.dstack([colour, alpha * 255.0]).round().astype(np.uint8)
    ys, xs = np.nonzero(alpha > 0.02)
    top = max(0, ys.min() - MARGIN)
    bottom = min(rgba.shape[0], ys.max() + MARGIN + 1)
    left = max(0, xs.min() - MARGIN)
    right = min(rgba.shape[1], xs.max() + MARGIN + 1)
    return Image.fromarray(rgba[top:bottom, left:right], "RGBA"), (left, top)


def fade(part, edges):
    """Fades a cut edge that another part covers, so no painted cut line
    shows where the two meet. `edges` maps "top"/"bottom"/"left"/"right" to
    [start, end] fractions of the part's height or width, ordered from the
    inside out: opaque before `start`, transparent beyond `end`. The image
    keeps its size so its points stay put."""
    if not edges:
        return part
    pixels = np.asarray(part).astype(np.float64)
    rows = ((np.arange(part.height) + 0.5) / part.height)[:, None]
    columns = ((np.arange(part.width) + 0.5) / part.width)[None, :]
    weight = np.ones((part.height, part.width))
    if "top" in edges:
        clear, solid = edges["top"]
        weight *= np.clip((rows - clear) / (solid - clear), 0.0, 1.0)
    if "bottom" in edges:
        solid, clear = edges["bottom"]
        weight *= np.clip((clear - rows) / (clear - solid), 0.0, 1.0)
    if "left" in edges:
        clear, solid = edges["left"]
        weight *= np.clip((columns - clear) / (solid - clear), 0.0, 1.0)
    if "right" in edges:
        solid, clear = edges["right"]
        weight *= np.clip((clear - columns) / (clear - solid), 0.0, 1.0)
    pixels[..., 3] *= weight
    return Image.fromarray(pixels.round().astype(np.uint8), "RGBA")


def main():
    folder = Path(sys.argv[1]).resolve()
    sheets = json.loads((folder / "sheets.json").read_text())
    output = folder / "parts"
    output.mkdir(exist_ok=True)
    record = {}
    for sheet in sheets["sheets"]:
        image = Image.open(folder / sheet["file"]).convert("RGB")
        columns, rows = sheet["grid"]
        # Tiles are equal unless the sheet gives their edges: parts are not
        # always painted in the middle of their tile.
        column_edges = sheet.get("columnEdges") or [round(column * image.width / columns) for column in range(columns + 1)]
        row_edges = sheet.get("rowEdges") or [round(row * image.height / rows) for row in range(rows + 1)]
        for index, name in enumerate(sheet["tiles"]):
            if not name:
                continue
            column = index % columns
            row = index // columns
            box = (column_edges[column], row_edges[row], column_edges[column + 1], row_edges[row + 1])
            part, (left, top) = cut_tile(image.crop(box))
            part = fade(part, sheet.get("fade", {}).get(name))
            part.save(output / f"{name}.png", optimize=True)
            record[name] = {"size": list(part.size), "sheet": sheet["file"], "at": [int(box[0] + left), int(box[1] + top)]}
            print(f"{name}: {part.size[0]}x{part.size[1]}")
    (output / "parts.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
