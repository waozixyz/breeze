#!/usr/bin/env python3
"""Depth maps for the film's plates: depth.py MODEL.onnx [NAME...].

Runs Depth Anything V2 (small, ONNX) on plates/NAME.jpg and writes
plates/NAME-depth.png: 960x540 8-bit, white = near. Run with a venv that
has onnxruntime, numpy and pillow (build/promo-video/threejs/venv).
"""
import sys
from pathlib import Path

import numpy as np
import onnxruntime
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
PLATES = HERE / "plates"
SIZE = (518 * 16 // 9 // 14 * 14, 518)  # multiples of the 14-pixel patch
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def depth(session, path):
    image = Image.open(path).convert("RGB")
    tensor = (np.asarray(image.resize(SIZE, Image.BICUBIC), np.float32) / 255 - MEAN) / STD
    tensor = tensor.transpose(2, 0, 1)[None]
    name = session.get_inputs()[0].name
    raw = session.run(None, {name: tensor})[0].squeeze()
    raw = (raw - raw.min()) / max(1e-6, raw.max() - raw.min())
    out = Image.fromarray((raw * 255).astype(np.uint8)).resize((960, 540), Image.BICUBIC)
    # A light blur keeps the displaced mesh from tearing at fine edges.
    return out.filter(ImageFilter.GaussianBlur(1.2))


def main():
    session = onnxruntime.InferenceSession(sys.argv[1], providers=["CPUExecutionProvider"])
    wanted = set(sys.argv[2:])
    for path in sorted(PLATES.glob("*.jpg")):
        if wanted and path.stem not in wanted:
            continue
        depth(session, path).save(PLATES / f"{path.stem}-depth.png")
        print(path.stem)


if __name__ == "__main__":
    main()
