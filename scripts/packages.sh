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

link() {
    name=$1
    shift
    # shellcheck disable=SC2086
    path=$("$ziran" pkg path "$@" $flags)
    [ -d "$path" ] || { echo "packages: no checkout for $name" >&2; exit 1; }
    ln -s "$path" "$staging/$name"
}

link ziran ziran
link kryon kryon
link kss kss
link oqs oqs
link raylib raylib
link game2d game2d
link daochi-client daochi_client
link sqlite sqlite
link curl curl
link liboqs liboqs
link monocypher monocypher
link rini rini

rm -rf "$links"
mv "$staging" "$links"
printf '%s\n' "$tool_commit" > "$links/.complete"
