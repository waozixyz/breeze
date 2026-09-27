#!/bin/sh
# Fetch the dependencies pinned in ziran.lock and link each checkout under
# build/packages/<name>. The Ziran package tool comes from the toolchain commit
# in the same lock, so a fresh clone needs only git, make, and a C compiler.
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

toolchain_field() {
    python3 -c 'import json, sys; print(json.load(open("ziran.lock"))["toolchain"][sys.argv[1]])' "$1"
}

tool_url=$(toolchain_field url)
tool_commit=$(toolchain_field commit)
bootstrap="$root/build/ziran-bootstrap"
ziran=${ZIRAN:-"$bootstrap/build/bin/ziran"}

if [ -z "${ZIRAN:-}" ]; then
    current=$(git -C "$bootstrap" rev-parse HEAD 2>/dev/null || true)
    if [ "$current" != "$tool_commit" ]; then
        case " $flags " in
            *" --offline "*)
                echo "packages: Ziran $tool_commit is not bootstrapped" >&2
                exit 1 ;;
        esac
        rm -rf "$bootstrap"
        mkdir -p "$bootstrap"
        git -C "$bootstrap" init -q
        git -C "$bootstrap" fetch -q --depth 1 "$tool_url" "$tool_commit"
        git -C "$bootstrap" checkout -q --detach FETCH_HEAD
    fi
    if [ ! -x "$ziran" ]; then
        env -u DISPLAY -u WAYLAND_DISPLAY make -C "$bootstrap" -s all >&2
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
link kryon kryon --submodules
link game2d game2d
link daochi-client daochi_client
link sqlite sqlite
link curl curl
link liboqs liboqs
link monocypher monocypher
link rini rini
link bend bend

rm -rf "$links"
mv "$staging" "$links"
printf '%s\n' "$tool_commit" > "$links/.complete"
