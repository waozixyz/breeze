#!/bin/sh
# Apps the node offers (node_apps in apps/versions.json) are built on their
# own into build/node-apps. They never go into the root package or its
# cells: released hosts reject a root that carries an app they don't know.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/ziran-toolchain/bin/ziran}
output=${2:-build/node-apps}
mkdir -p build "$output"
exec 9>build/cells-build.lock
flock 9
packages=$(sh scripts/package-paths.sh)
python3 scripts/check-package-versions.py
python3 scripts/prepare-package-assets.py
for name in $(python3 -c 'import json; print(" ".join(sorted(json.load(open("apps/versions.json")).get("node_apps", {}))))'); do
    assets=build/package-assets/$name/assets
    mkdir -p "$assets"
    # shellcheck disable=SC2086
    "$ziran" bundle --root . --module-path src $packages \
        --module-path build/packages/kryon/src/ui \
        --define KRYON_HOSTED_UI \
        --module-path build/packages/ziran/std \
        --asset-dir "assets=$assets" \
        --entry "$name:Main" -o "$output/$name.zx" "apps/$name/$name.zi"
done
