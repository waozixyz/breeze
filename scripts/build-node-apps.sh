#!/bin/sh
# Apps the node offers build independently into build/node-apps. Complete
# small apps also ship as optional baselines, outside the root's cells/ IDs.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/packages/ziran/build/bin/ziran}
# Package flags select the same development or locked graph as Make.
bundle() {
    # shellcheck disable=SC2086
    "$ziran" bundle --project --offline ${PACKAGE_FLAGS:-} "$@"
}
output=${2:-build/node-apps}
mkdir -p build "$output"
exec 9>build/apps-build.lock
flock 9
python3 scripts/check-package-versions.py
python3 scripts/prepare-package-assets.py --node-only --output build/node-package-assets
for name in $(python3 -c 'import json; print(" ".join(sorted(json.load(open("apps/versions.json")).get("node_apps", {}))))'); do
    assets=build/node-package-assets/$name/assets
    mkdir -p "$assets"
    # shellcheck disable=SC2086
    bundle --root . \
        --define KRYON_HOSTED_UI \
        --asset-dir "assets=$assets" \
        --entry "$name:Main" -o "$output/$name.zx" "apps/$name/$name.zi"
    # The compiler preserves the mtime when the bundle's bytes match.
    # Mark a verified output current so Make can skip rebuilding it.
    test -s "$output/$name.zx"
    touch "$output/$name.zx"
done
