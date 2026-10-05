#!/bin/sh
# Compile each feature closure independently; never pass the host application.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/ziran-toolchain/bin/ziran}
output=${2:-build/subapps}
mkdir -p "$output"
for feature in lists habits practice; do
    "$ziran" bundle --root . --module-path src \
        --module-path build/packages/kryon/src/ui \
        --module-path build/packages/ziran/std \
        --entry "$feature:Main" -o "$output/$feature.zib" \
        "apps/$feature/$feature.zi"
done
"$ziran" bundle --root . --module-path src \
    --module-path build/packages/ziran/std --entry inbe:Main \
    --asset-dir "subapps=$output" -o build/inbe.zib apps/inbe/inbe.zi
