#!/bin/sh
# Every locked dependency must be an unmodified checkout of its locked commit.
# Local ziran.local.toml overrides point at working repositories and are
# reported rather than checked; release builds use --locked, which rejects them.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
[ -f build/packages/.complete ] || sh scripts/packages.sh

status=0
for link in build/packages/*; do
    [ -L "$link" ] || continue
    name=$(basename "$link")
    path=$(readlink "$link")
    case "$path" in
        "${XDG_CACHE_HOME:-$HOME/.cache}"/ziran/sources/*) ;;
        *) echo "package $name uses local override $path"; continue ;;
    esac
    if [ -n "$(git -C "$path" status --porcelain --ignore-submodules=none)" ]; then
        echo "Modified package checkout: $name ($path)"
        git -C "$path" status --short
        status=1
    fi
done

if [ "$status" -ne 0 ]; then
    echo
    echo "Do not edit dependencies from Inbe. Change the owning repository, commit and push there, then run ziran update NAME here."
    exit 1
fi
