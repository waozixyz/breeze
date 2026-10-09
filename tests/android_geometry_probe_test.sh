#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$root/build/scratch/android-geometry-probe
mkdir -p "$work"
ziran=${ZIRAN_BIN:-"$root/build/ziran-toolchain/bin/ziran"}
"$ziran" build --target=c --define ANDROID_BUILD --define ANDROID_DEBUG \
    --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/android_geometry_probe_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$work/c" "$work/c"/*.c -ldl -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
python3 - "$root" <<'PYTEST'
import importlib.util
from pathlib import Path
import sys
spec = importlib.util.spec_from_file_location("geometry", Path(sys.argv[1]) / "tests/android_rotation_geometry_device.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
line = "ANDROID_GEOMETRY: ready=1 sample=2 launch=1080x2220 screen=2220x1080 render=2220x1080 viewport=0,0,2220x1080 offset=0,0 scale=1.000000,1.000000 projection=0.000900901,-0.001851852 layout=740x360 render_scale=3.000000 practice=-1 paused=0"
sample = m.parse_geometry(line)
m.validate_geometry(sample)
for key, value in (("scale", [0.5, 1.0]), ("offset", [100, 0]), ("projection", [2/1080, -2/2220]), ("practice", 0), ("layout", [360, 740])):
    broken = sample | {key: value}
    try:
        m.validate_geometry(broken)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Accepted invalid " + key)
print("Debug geometry bypasses suppressed INFO, refreshes readings, carries practice guard and rejects stale projection/scale/layout")
PYTEST
