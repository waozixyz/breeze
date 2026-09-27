#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
standard=${ZIRAN_STD:-"$root/vendor/ziran/std"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$standard" -o "$work/c" \
    "$root/src/practices/meditation/meditation_audio_archive.zi"
"${CC:-cc}" -std=c11 -I"$root/vendor/ziran/include" -I"$work/c" \
    "$work/c"/*.c \
    "$work/c/practices/meditation/meditation_audio_archive.c" \
    "$root/tests/meditation_audio_archive_test.c" -lz -o "$work/test"

python3 - "$work" <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile
import sys
import warnings

work = Path(sys.argv[1])
names = [
    "Elijah_K/deep-meditation.ogg",
    "Elijah_K/path-of-meditation.ogg",
    "Elijah_K/truth-of-silence.ogg",
]
payloads = [b"OggSdeep", b"OggSpath" * 12000, b"OggStruth"]
with ZipFile(work / "valid.zip", "w") as archive:
    for index, (name, payload) in enumerate(zip(names, payloads)):
        archive.writestr(name, payload,
                         compress_type=ZIP_STORED if index == 0 else ZIP_DEFLATED)
    archive.writestr("../escape.ogg", b"OggSescape")
with ZipFile(work / "missing.zip", "w") as archive:
    for name, payload in zip(names[:2], payloads[:2]):
        archive.writestr(name, payload)
with ZipFile(work / "not-ogg.zip", "w") as archive:
    for index, (name, payload) in enumerate(zip(names, payloads)):
        archive.writestr(name, b"bad!" if index == 1 else payload)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    with ZipFile(work / "duplicate.zip", "w") as archive:
        for name, payload in zip(names, payloads):
            archive.writestr(name, payload)
        archive.writestr(names[0], payloads[0])
corrupt = (work / "valid.zip").read_bytes()
at = corrupt.index(b"OggSdeep")
corrupt = corrupt[:at] + b"X" + corrupt[at + 1:]
(work / "corrupt.zip").write_bytes(corrupt)
PY

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$work/valid.zip" "$work/valid-cache" 3
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$work/missing.zip" "$work/missing-cache" 0
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$work/not-ogg.zip" "$work/not-ogg-cache" 0
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$work/duplicate.zip" "$work/duplicate-cache" 0
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$work/corrupt.zip" "$work/corrupt-cache" 0

python3 - "$work" <<'PY'
from pathlib import Path
import sys

work = Path(sys.argv[1])
track_dir = work / "valid-cache" / "audio" / "Elijah_K"
assert (track_dir / "deep-meditation.ogg").read_bytes() == b"OggSdeep"
assert (track_dir / "path-of-meditation.ogg").read_bytes() == b"OggSpath" * 12000
assert (track_dir / "truth-of-silence.ogg").read_bytes() == b"OggStruth"
assert not (work / "escape.ogg").exists()
for cache in work.glob("*-cache"):
    assert not list(cache.rglob("*.part")), cache
PY
echo "meditation audio ZIP install passed"
