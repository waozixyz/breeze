"""A deterministic RGBA PNG, generated as binary test input with no owner data."""
from pathlib import Path
import random
import struct
import sys
import zlib

def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

rng = random.Random(37)
rows = bytearray()
for y in range(96):
    rows.append(0)
    for x in range(128):
        rows.extend((rng.randrange(256), rng.randrange(256), rng.randrange(256),
                     0 if x < 8 else 255 if x > 120 else (x * 2)))
png = bytes((137, 80, 78, 71, 13, 10, 26, 10))
png += chunk(b'IHDR', struct.pack('>IIBBBBB', 128, 96, 8, 6, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
Path(sys.argv[1]).write_bytes(png)
