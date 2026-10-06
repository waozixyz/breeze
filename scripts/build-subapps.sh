#!/bin/sh
# Each application is compiled independently. APKs include recommended apps.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/ziran-toolchain/bin/ziran}
output=${2:-build/subapps}
python3 scripts/generate-package-versions.py
mkdir -p "$output" build/bundled-subapps
rm -f "$output/practice.zib"
for feature in lists habits practices diary; do
    source=$feature
    entry=$feature
    if [ "$feature" = practices ]; then source=practice; entry=practice; fi
    "$ziran" bundle --root . --module-path src \
        --module-path build/packages/kryon/src/ui \
        --module-path build/packages/ziran/std \
        --entry "$entry:Main" -o "$output/$feature.zib" \
        "apps/$source/$source.zi"
done
# The source/optional artifacts remain available for publishing and tests.
rm -f build/bundled-subapps/lists.zib build/bundled-subapps/diary.zib build/bundled-subapps/practice.zib
cp "$output/habits.zib" "$output/practices.zib" build/bundled-subapps/
"$ziran" bundle --root . --module-path src \
    --module-path build/packages/ziran/std --entry inbe:Main \
    --asset-dir "subapps=build/bundled-subapps" -o build/inbe.zib apps/inbe/inbe.zi
"$ziran" bundle --root . --module-path src \
    --module-path build/packages/ziran/std --entry inbe:Main \
    --asset-dir "subapps=$output" -o build/inbe-full.zib apps/inbe/inbe.zi
