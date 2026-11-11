#!/bin/sh
# Fetch the dependencies pinned in ziran.lock and link each checkout under
# build/packages/<name>. The Ziran package tool comes from the toolchain commit
# in the same lock, so a fresh clone needs only git, make, and a C compiler.
#
# Sources already on disk are used before the network: set
# ZIRAN_PACKAGE_SOURCES to a directory of checkouts, or build from F-Droid,
# whose srclibs in ../srclib are found automatically. Each must contain the
# locked commit; see scripts/seed-package-sources.py.
#
#   sh scripts/packages.sh            # use ziran.local.toml overrides if present
#   sh scripts/packages.sh --locked   # release/CI: exact lock, no overrides
#   sh scripts/packages.sh --offline  # use only the package cache
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

# Builds started together share build/ziran-bootstrap and build/packages.
# One run at a time: a concurrent relink once followed another run's fresh
# links and planted self-links inside every package checkout.
if [ -z "${PACKAGES_LOCK_HELD:-}" ] && command -v flock >/dev/null 2>&1; then
    mkdir -p build
    PACKAGES_LOCK_HELD=1 exec flock build/packages.lock sh "$root/scripts/packages.sh" "$@"
fi

flags=""
for argument in "$@"; do
    case "$argument" in
        --locked|--offline) flags="$flags $argument" ;;
        *) echo "usage: sh scripts/packages.sh [--locked] [--offline]" >&2; exit 2 ;;
    esac
done

# Ziran's Makefile is GNU make; on the BSDs that is gmake, not make.
gnu_make=$(command -v gmake || command -v make)

toolchain_field() {
    python3 -c 'import json, sys; print(json.load(open("ziran.lock"))["toolchain"][sys.argv[1]])' "$1"
}

tool_url=$(toolchain_field url)
tool_commit=$(toolchain_field commit)
bootstrap="$root/build/ziran-bootstrap"
ziran=${ZIRAN:-"$bootstrap/build/bin/ziran"}

python3 scripts/seed-package-sources.py
tool_cache="${XDG_CACHE_HOME:-$HOME/.cache}/ziran/sources/$(python3 -c 'import hashlib, sys; print("p" + hashlib.sha256(f"{sys.argv[1]}\n{sys.argv[2]}".encode()).hexdigest()[:16])' "$tool_url" "$tool_commit")"

if [ -z "${ZIRAN:-}" ]; then
    current=$(git -C "$bootstrap" rev-parse HEAD 2>/dev/null || true)
    if [ "$current" != "$tool_commit" ]; then
        case " $flags " in
            *" --offline "*)
                echo "packages: Ziran $tool_commit is not bootstrapped" >&2
                exit 1 ;;
        esac
        rm -rf "$bootstrap"
        if [ -d "$tool_cache" ]; then
            git clone -q --no-checkout "$tool_cache" "$bootstrap"
            git -C "$bootstrap" checkout -q --detach "$tool_commit"
        else
            mkdir -p "$bootstrap"
            git -C "$bootstrap" init -q
            git -C "$bootstrap" fetch -q --depth 1 "$tool_url" "$tool_commit"
            git -C "$bootstrap" checkout -q --detach FETCH_HEAD
        fi
    fi
    if [ ! -x "$ziran" ]; then
        env -u DISPLAY -u WAYLAND_DISPLAY "$gnu_make" -C "$bootstrap" -s all >&2
    fi
fi

# shellcheck disable=SC2086
"$ziran" fetch $flags

links="$root/build/packages"
staging="$links.tmp"
rm -rf "$staging"
mkdir -p "$staging"

# Resolve the complete requested set in one validated graph. JSON keeps paths
# containing spaces, quotes or newlines intact; validate every row before links.
# shellcheck disable=SC2086
python3 - "$ziran" "$staging" $flags <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys

packages = [
    ("ziran", "ziran"),
    ("kryon", "kryon"),
    ("css", "css"),
    ("oqs", "oqs"),
    ("raylib", "raylib"),
    ("libwebp", "libwebp"),
    # Kryon's image decoders and their pinned native source packages.
    ("webp", "webp"),
    ("image-codec", "image-codec"),
    ("avif", "avif"),
    ("libavif", "libavif"),
    ("libaom", "libaom"),
    # Kryon's Ogg Opus decoder and its pinned native source packages.
    ("audio", "audio"),
    ("libopus", "libopus"),
    ("libsamplerate", "libsamplerate"),
    ("game2d", "game2d"),
    ("qrcode", "qrcode"),
    ("plot", "plot"),
    ("mingcute", "mingcute"),
    ("entity", "entity"),
    ("apps", "apps"),
    ("crypto", "crypto"),
    ("daochi-client", "daochi_client"),
    ("practices", "practices"),
    ("sqlite", "sqlite"),
    ("curl", "curl"),
    ("liboqs", "liboqs"),
    ("monocypher", "monocypher"),
    ("rini", "rini"),
]
command = [sys.argv[1], "pkg", "paths", *(selector for _, selector in packages), *sys.argv[3:]]
result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
if result.returncode != 0:
    raise SystemExit(result.returncode)
try:
    rows = json.loads(result.stdout)
except ValueError:
    raise SystemExit("packages: invalid batch path response")
if not isinstance(rows, list) or len(rows) != len(packages):
    raise SystemExit("packages: incomplete batch path response")
for (name, selector), row in zip(packages, rows):
    if (not isinstance(row, dict) or set(row) != {"selector", "path"} or
            row["selector"] != selector or not isinstance(row["path"], str) or
            "\0" in row["path"] or not Path(row["path"]).is_absolute()):
        raise SystemExit("packages: invalid batch path for " + name)
    if not Path(row["path"]).is_dir():
        raise SystemExit("packages: no checkout for " + name)
for (name, _), row in zip(packages, rows):
    os.symlink(row["path"], Path(sys.argv[2]) / name)
PY

rm -rf "$links"
mv "$staging" "$links"
printf '%s\n' "$tool_commit" > "$links/.complete"
