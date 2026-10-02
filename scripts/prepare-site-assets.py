#!/usr/bin/env python3
"""Package large browser files within the Pages per-file limit."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

MAX_FILE_BYTES = 25 * 1024 * 1024


def prepare(path: Path, limit: int) -> None:
    if not path.exists() or path.stat().st_size <= limit:
        return
    compressed = gzip.compress(path.read_bytes(), compresslevel=9, mtime=0)
    if len(compressed) <= limit:
        path.with_name(path.name + ".gz").write_bytes(compressed)
    else:
        digest = hashlib.sha256(compressed).hexdigest()
        parts = []
        for index, offset in enumerate(range(0, len(compressed), limit)):
            name = f"{path.name}.gz.{digest[:16]}.part-{index:03d}"
            path.with_name(name).write_bytes(compressed[offset:offset + limit])
            parts.append(name)
        manifest = {"parts": parts, "sha256": digest, "size": len(compressed)}
        path.with_name(path.name + ".parts.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n")
    path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    args = parser.parse_args()
    if args.max_file_bytes <= 0:
        parser.error("--max-file-bytes must be positive")
    for app in ("web", "telegram"):
        for name in ("index.data", "index.wasm"):
            prepare(args.root / "build" / app / name, args.max_file_bytes)
    for path in args.root.rglob("*"):
        if path.is_file() and path.stat().st_size > args.max_file_bytes:
            raise SystemExit(f"Site asset exceeds the Pages limit: {path}")


if __name__ == "__main__":
    main()
