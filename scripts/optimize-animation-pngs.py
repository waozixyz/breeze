#!/usr/bin/env python3
"""Losslessly recompress animation PNG streams; requires Python zopfli.

Only IDAT compression changes. Palette, transparency, filtered pixels and
animation metadata remain byte-for-byte identical. Builds use the committed
PNGs and do not need zopfli; character regeneration runs this authoring step.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def optimize(job):
    import zopfli.zlib

    path, iterations = job
    original = path.read_bytes()
    if original[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG: {path}")
    chunks = []
    offset = 8
    while offset < len(original):
        size = struct.unpack_from(">I", original, offset)[0]
        chunk = original[offset:offset + size + 12]
        if len(chunk) != size + 12:
            raise ValueError(f"Truncated PNG: {path}")
        chunks.append(chunk)
        offset += size + 12
    compressed = b"".join(chunk[8:-4] for chunk in chunks if chunk[4:8] == b"IDAT")
    filtered_pixels = zlib.decompress(compressed)
    smaller = zopfli.zlib.compress(filtered_pixels, numiterations=iterations)
    if zlib.decompress(smaller) != filtered_pixels:
        raise ValueError(f"Pixel data changed: {path}")
    result = bytearray(original[:8])
    emitted = False
    for chunk in chunks:
        if chunk[4:8] != b"IDAT":
            result.extend(chunk)
        elif not emitted:
            payload = b"IDAT" + smaller
            result.extend(struct.pack(">I", len(smaller)))
            result.extend(payload)
            result.extend(struct.pack(">I", zlib.crc32(payload)))
            emitted = True
    if len(result) < len(original):
        path.write_bytes(result)
        return len(original), len(result)
    return len(original), len(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()
    if args.jobs < 1 or args.iterations < 1:
        parser.error("jobs and iterations must be positive")
    paths = sorted((ROOT / "assets/practices/sunsalutation/characters").glob("*/*.png"))
    if not paths:
        raise SystemExit("No character animation frames found")
    before = 0
    after = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for count, sizes in enumerate(pool.map(optimize,
                ((path, args.iterations) for path in paths)), 1):
            before += sizes[0]
            after += sizes[1]
            if count % 200 == 0 or count == len(paths):
                print(f"{count}/{len(paths)} PNGs; saved {before - after:,} bytes", flush=True)
    print(f"Identical pixels: {before:,} -> {after:,} bytes", flush=True)


if __name__ == "__main__":
    main()
