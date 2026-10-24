#!/bin/sh
# Prints the app's source roots and each linked dependency's named module
# paths. scripts/packages.sh links dependencies under build/packages.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Read the app's source roots from its manifest so every platform resolves
# the same named modules without file-relative imports.
python3 - "$root" <<'PY'
from pathlib import Path
import sys
import tomllib

root = Path(sys.argv[1])
manifest = tomllib.loads((root / "ziran.toml").read_text())
for directory in manifest["package"]["module_roots"]:
    print("--module-path")
    print(root / directory)
PY
packages=${1:-build/packages}
for path in kryon=kryon/src/ui kryon=kryon/src/backend apps=apps/src \
    crypto=crypto/src entity=entity/src plot=plot/src qrcode=qrcode/src \
    oqs=oqs/src mingcute=mingcute/src daochi_client=daochi-client; do
    printf '%s\n' --module-path "${path%%=*}=$packages/${path#*=}"
done
