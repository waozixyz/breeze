#!/bin/sh
# Prints the app's source roots and each linked dependency's named module
# paths. scripts/packages.sh links dependencies under build/packages.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -n "${DAOCHI_CLIENT_DIR:-}" ]; then
    # Standalone storage tests also retain unqualified protocol imports.
    printf '%s\n' --module-path "$DAOCHI_CLIENT_DIR"
fi
# Read the app's source roots from its manifest so every platform resolves
# the same named modules without file-relative imports.
python3 - "$root" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
text = (root / "ziran.toml").read_text()
try:
    import tomllib
    roots = tomllib.loads(text)["package"]["module_roots"]
except ModuleNotFoundError:
    # Python before 3.11, as on the Ubuntu 22.04 package builders: the
    # manifest keeps module_roots as one list of strings on one line.
    import ast
    import re
    roots = ast.literal_eval(re.search(r"^module_roots\s*=\s*(\[[^\]]*\])", text, re.M).group(1))
for directory in roots:
    print("--module-path")
    print(root / directory)
PY
packages=${1:-build/packages}
for path in kryon=kryon/src/ui kryon=kryon/src/backend apps=apps/src \
    crypto=crypto/src entity=entity/src plot=plot/src qrcode=qrcode/src \
    oqs=oqs/src mingcute=mingcute/src daochi_client=daochi-client; do
    directory="$packages/${path#*=}"
    if [ "${path%%=*}" = daochi_client ] && [ -n "${DAOCHI_CLIENT_DIR:-}" ]; then
        directory=$DAOCHI_CLIENT_DIR
    fi
    printf '%s\n' --module-path "${path%%=*}=$directory"
done
