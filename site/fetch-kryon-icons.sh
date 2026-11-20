#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

destination=${1:?Usage: fetch-kryon-icons.sh DESTINATION}
revision=$(python3 - <<'PY'
import json
import re
from pathlib import Path

lock = json.loads(Path('ziran.lock').read_text())
pins = [package['commit'] for package in lock['packages'] if package['name'] == 'kryon']
if len(pins) != 1 or not re.fullmatch(r'[0-9a-f]{40}', pins[0]):
    raise SystemExit('Expected one pinned Kryon commit in ziran.lock')
print(pins[0])
PY
)
mkdir -p "$destination/icons" "$destination/scripts"
for file in scripts/sync-icons.sh icons/platforms.png icons/platforms.json \
    icons/language.png icons/language.json icons/tiles.png icons/tiles.json; do
    temporary=$(mktemp "$destination/$file.XXXXXX")
    trap 'rm -f "$temporary"' 0
    curl -fsSL --max-time 30 --retry 2 \
        "https://git.waozi.xyz/kryonlabs/kryon/raw/commit/$revision/$file" -o "$temporary"
    test -s "$temporary"
    chmod 644 "$temporary"
    mv -f "$temporary" "$destination/$file"
    trap - 0
done
printf 'Fetched the site icon sheets from Kryon commit %s\n' "$revision"
