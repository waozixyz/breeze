#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
output="$root/build/native-screenshot-test"
mkdir -p "$output"

# Home exercises the layered crescent that previously drew forever because
# its inner loop never advanced. Run the whole app on an isolated display.
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    APP_NO_TRAY=1 timeout 30s xvfb-run -a -n 300 -e /dev/stderr \
    -s '-screen 0 1280x900x24' "$binary" \
    --screenshot "$output/home.png" --screenshot-scene home \
    --screenshot-width 900 --screenshot-height 720 > "$output/app.log" 2>&1 || {
        result=$?
        cat "$output/app.log" >&2
        exit "$result"
    }
if rg --quiet 'APP: frame rejected with status' "$output/app.log"; then
    cat "$output/app.log" >&2
    exit 1
fi
python3 - "$output/home.png" <<'PY'
from pathlib import Path
import struct
import sys
from PIL import Image

data = Path(sys.argv[1]).read_bytes()
assert data[:8] == b'\x89PNG\r\n\x1a\n', 'screenshot is not a PNG'
assert data[12:16] == b'IHDR', 'screenshot has no PNG dimensions'
assert struct.unpack('>II', data[16:24]) == (900, 720), 'wrong viewport'
with Image.open(sys.argv[1]) as screenshot:
    total = screenshot.width * screenshot.height
    dominant = max(count for count, _ in screenshot.convert('RGB').getcolors(total))
    assert dominant < total * 0.97, 'widget frame is missing: only background rendered'
print('Native home rendered and exited within 30 seconds')
PY
