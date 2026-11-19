#!/usr/bin/env python3
"""Package large browser files within the Pages per-file limit."""

from __future__ import annotations

import argparse
import ctypes
import filecmp
import gzip
import hashlib
import json
import shutil
from ctypes.util import find_library
from pathlib import Path

MAX_FILE_BYTES = 25 * 1024 * 1024


class ZstdEncoder:
    """Use the host libzstd when it is installed. Browsers decode this natively."""

    def __init__(self, library: ctypes.CDLL):
        self.library = library
        size = ctypes.c_size_t
        pointer = ctypes.c_void_p
        signatures = {
            "createCCtx": (pointer, []),
            "freeCCtx": (size, [pointer]),
            "CCtx_setParameter": (size, [pointer, ctypes.c_int, ctypes.c_int]),
            "compressBound": (size, [size]),
            "compress2": (size, [pointer, pointer, size, ctypes.c_char_p, size]),
            "isError": (ctypes.c_uint, [size]),
            "getErrorName": (ctypes.c_char_p, [size]),
        }
        for name, (result, parameters) in signatures.items():
            function = getattr(library, "ZSTD_" + name)
            function.restype = result
            function.argtypes = parameters

    def checked(self, result: int) -> int:
        if self.library.ZSTD_isError(result):
            raise ValueError(self.library.ZSTD_getErrorName(result).decode())
        return result

    def encode(self, path: Path, limit: int) -> list[bytes]:
        zstd = self.library
        context = zstd.ZSTD_createCCtx()
        if not context:
            raise MemoryError("Could not allocate a Zstd compression context")
        parts = []
        try:
            self.checked(zstd.ZSTD_CCtx_setParameter(context, 100, 22))  # compressionLevel
            self.checked(zstd.ZSTD_CCtx_setParameter(context, 101, 23))  # windowLog, RFC 9659
            with path.open("rb") as source:
                while block := source.read(min(limit, MAX_FILE_BYTES)):
                    output = ctypes.create_string_buffer(zstd.ZSTD_compressBound(len(block)))
                    size = self.checked(zstd.ZSTD_compress2(context, output, len(output), block, len(block)))
                    frame = output[:size]
                    for offset in range(0, size, limit):
                        parts.append(frame[offset:offset + limit])
        finally:
            zstd.ZSTD_freeCCtx(context)
        return parts


def load_zstd() -> ZstdEncoder | None:
    name = find_library("zstd")
    if name:
        try:
            return ZstdEncoder(ctypes.CDLL(name))
        except (OSError, AttributeError):
            pass
    return None


def write_parts(path: Path, coding: str, parts: list[bytes]) -> list[str]:
    sha256 = hashlib.sha256()
    for part in parts:
        sha256.update(part)
    digest = sha256.hexdigest()
    names = []
    for index, part in enumerate(parts):
        name = f"{path.name}.{coding}.{digest[:16]}.part-{index:03d}"
        path.with_name(name).write_bytes(part)
        names.append(name)
    manifest = {"parts": names, "sha256": digest, "size": sum(map(len, parts))}
    suffix = ".parts.json" if coding == "gz" else ".zstd.parts.json"
    manifest_path = path.with_name(path.name + suffix)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    return names + [manifest_path.name]


def prepare(path: Path, limit: int, zstd: ZstdEncoder | None = None) -> list[str]:
    if not path.exists() or path.stat().st_size <= limit:
        return []
    compressed = gzip.compress(path.read_bytes(), compresslevel=9, mtime=0)
    if len(compressed) <= limit:
        output = path.with_name(path.name + ".gz")
        output.write_bytes(compressed)
        names = [output.name]
    else:
        names = write_parts(path, "gz", [compressed[i:i + limit] for i in range(0, len(compressed), limit)])
        if zstd:
            parts = zstd.encode(path, limit)
            if sum(map(len, parts)) < len(compressed):
                names.extend(write_parts(path, "zstd", parts))
    path.unlink()
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    args = parser.parse_args()
    if args.max_file_bytes <= 0:
        parser.error("--max-file-bytes must be positive")
    web = args.root / "build" / "web"
    telegram = args.root / "build" / "telegram"
    for directory in (web, telegram):
        prepare(directory / "index.data", args.max_file_bytes)
    web_wasm = web / "index.wasm"
    telegram_wasm = telegram / "index.wasm"
    same_wasm = web_wasm.is_file() and telegram_wasm.is_file() and filecmp.cmp(
        web_wasm, telegram_wasm, shallow=False)
    encoder = load_zstd()
    prepared = prepare(web_wasm, args.max_file_bytes, encoder)
    if same_wasm:
        if prepared:
            for name in prepared:
                shutil.copyfile(web / name, telegram / name)
            telegram_wasm.unlink()
    else:
        prepare(telegram_wasm, args.max_file_bytes, encoder)
    for path in args.root.rglob("*"):
        if path.is_file() and path.stat().st_size > args.max_file_bytes:
            raise SystemExit(f"Site asset exceeds the Pages limit: {path}")


if __name__ == "__main__":
    main()
