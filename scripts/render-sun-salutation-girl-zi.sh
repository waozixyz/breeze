#!/bin/sh
# Build scripts/sun_salutation_girl.zi to Python with Inbe's pinned Ziran
# toolchain (zi2py) and run it: the Ziran version of
# scripts/render-sun-salutation-girl.py. It writes
# build/sun-salutation-girl-zi/THEME/sun-salutation.mp4, or one frame with
# STILL=seconds. Needs Python 3, Cairo, and FFmpeg with libx264.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
[ -f build/packages/.complete ] || sh scripts/packages.sh

toolchain="$root/build/ziran-toolchain"
make -s -C build/packages/ziran BUILD_DIR="$toolchain" "$toolchain/bin/zi2py"

program="$root/build/sun-salutation-girl-zi/program"
LDLIBS=-lcairo "$toolchain/bin/zi2py" --exe --entry sun_salutation_girl:Main \
    --root scripts --module-path build/packages/ziran/std \
    -o "$program" scripts/sun_salutation_girl.zi
exec python3 "$program"
