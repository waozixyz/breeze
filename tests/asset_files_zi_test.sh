#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
raylib=${2:-"$root/vendor-builds/linux/x86_64/raylib/libraylib.a"}
work=$(mktemp -d "$root/build/asset-files-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src/app" --module-path "$root/src/platform" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/asset_files_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c "$raylib" -lm -o "$work/test"
python3 - "$work/disk.bin" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes(bytes((30, 0, 40, 254)))
PY
cd "$work"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY ./test
echo 'Embedded raylib assets, owned copies, disk fallback and missing files: passed'
