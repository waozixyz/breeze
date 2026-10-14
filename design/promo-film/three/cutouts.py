#!/usr/bin/env python3
"""Mia's cutouts for the film: the difference between a plate with her and
the same plate without her (both Codex edits of one picture).

Writes plates/NAME-mia.webp (RGBA, cropped to the figure, feathered alpha) and crops the
"-empty" plates to plates/NAME-empty.jpg. The meadow cutout comes from the
approved keyframe itself, because its plate removed Mia entirely.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / "build/promo-video/threejs/plates"
PLATES = HERE / "plates"
SCENES = {"cabin": "cabin", "dock": "dock", "ledge": "ledge", "desk": "desk", "sofa": "sofa"}


def frame(image):
    """The film's 16:9 band of a 1536x1024 picture, at 1920x1080."""
    image = image.convert("RGB")
    band = round(image.width * 9 / 16)
    top = (image.height - band) // 2
    return image.crop((0, top, image.width, top + band)).resize((1920, 1080), Image.LANCZOS)


def mask_between(with_mia, without, keep=1, grow=3):
    a = np.asarray(with_mia.filter(ImageFilter.GaussianBlur(1.5)), np.float32)
    b = np.asarray(without.filter(ImageFilter.GaussianBlur(1.5)), np.float32)
    difference = np.sqrt(((a - b) ** 2).sum(axis=2))
    rough = ndimage.binary_opening(difference > 28, iterations=2)
    labels, count = ndimage.label(rough)
    if count == 0:
        raise SystemExit("no difference found")
    sizes = ndimage.sum(rough, labels, range(1, count + 1))
    biggest = np.argsort(sizes)[::-1][:keep] + 1
    region = np.isin(labels, biggest)
    region = ndimage.binary_closing(region, iterations=6)
    region = ndimage.binary_fill_holes(region)
    region = ndimage.binary_dilation(region, iterations=grow)
    alpha = Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))
    return alpha


def refine_standing(picture, alpha):
    """Keeps only Mia from the meadow difference: drops the sky patches, the
    sparkle arc and Lumi, which the keyframe drew around her raised arms."""
    rgb = np.asarray(picture, np.int32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sky = (b > r + 25) & ((r + g + b) / 3 > 150)
    sparkle = (r + g + b) / 3 > 228
    region = (np.asarray(alpha) > 127) & ~sky & ~sparkle
    left, top, right, bottom = alpha.getbbox()
    # Lumi hovers above her right hand; the sparkle arc leaves her left hand.
    region[top:top + 170, left + 495:right] = False
    region[top:top + 215, left:left + 215] = False
    region = ndimage.binary_opening(region, iterations=2)
    labels, count = ndimage.label(region)
    sizes = ndimage.sum(region, labels, range(1, count + 1))
    region = labels == (int(np.argmax(sizes)) + 1)
    # No hole filling: the sky between her raised arms must stay open.
    region = ndimage.binary_closing(region, iterations=2)
    return Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))


def main():
    for name, source in SCENES.items():
        with_mia = Image.open(PLATES / f"{source}.jpg").convert("RGB")
        empty = frame(Image.open(RAW / f"{name}-empty.png"))
        empty.save(PLATES / f"{name}-empty.jpg", quality=90)
        alpha = mask_between(with_mia, empty)
        cut = with_mia.copy()
        cut.putalpha(alpha)
        cut.crop(alpha.getbbox()).save(PLATES / f"{name}-mia.webp", "WEBP", quality=92, method=6)
        box = alpha.getbbox()
        print(name, "bbox", box)
        (PLATES / f"{name}-mia.box").write_text(" ".join(map(str, box)) + "\n")
    keyframe = frame(Image.open(ROOT / "build/promo-video/keyframes/shot-05.png"))
    meadow = Image.open(PLATES / "meadow.jpg").convert("RGB")
    alpha = refine_standing(keyframe, mask_between(keyframe, meadow))
    cut = keyframe.copy()
    cut.putalpha(alpha)
    cut.crop(alpha.getbbox()).save(PLATES / "meadow-mia.webp", "WEBP", quality=92, method=6)
    print("meadow bbox", alpha.getbbox())
    (PLATES / "meadow-mia.box").write_text(" ".join(map(str, alpha.getbbox())) + "\n")


if __name__ == "__main__":
    main()
