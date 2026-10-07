#!/bin/sh
# Each cell is compiled independently and included for offline use.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
# Asset preparation replaces shared directories. Keep simultaneous native,
# package and test builds from removing resources another bundle is reading.
mkdir -p build
exec 9>build/cells-build.lock
flock 9
ziran=${1:-build/ziran-toolchain/bin/ziran}
output=${2:-build/cells}
python3 scripts/check-package-versions.py
python3 tests/font_glyph_coverage_test.py
python3 tests/locale_translated_test.py
python3 tests/locale_used_keys_test.py
python3 scripts/generate-package-versions.py
python3 scripts/prepare-package-assets.py
mkdir -p "$output" build/bundled-cells
rm -f "$output/practice.zib"
for feature in lists habits practices diary lumi; do
    source=$feature
    entry=$feature
    if [ "$feature" = practices ]; then source=practice; entry=practice; fi
    "$ziran" bundle --root . --module-path src \
        --module-path build/packages/kryon/src/ui \
        --define KRYON_HOSTED_UI \
        --module-path build/packages/ziran/std \
        --asset-dir "assets=build/package-assets/$feature/assets" \
        --entry "$entry:Main" -o "$output/$feature.zib" \
        "apps/$source/$source.zi"
done
# Removing a sidebar shortcut never removes its bundled package.
rm -f build/bundled-cells/practice.zib
for feature in lists habits practices diary lumi; do
    cp "$output/$feature.zib" build/bundled-cells/
done
"$ziran" bundle --root . --module-path src \
    --module-path build/packages/ziran/std --module-path build/packages/kryon/src/ui \
    --define KRYON_HOSTED_UI --entry inbe:Main \
    --asset-dir "assets=build/package-assets/inbe/assets" \
    --asset-dir "styles=build/package-assets/inbe/styles" \
    --asset-dir "themes=build/package-assets/inbe/themes" \
    --asset-dir "locales=build/package-assets/inbe/locales" \
    --asset-dir "icons=build/package-assets/inbe/icons" \
    --asset-dir "cells=build/bundled-cells" -o build/inbe.zib apps/inbe/inbe.zi
"$ziran" bundle --root . --module-path src \
    --module-path build/packages/ziran/std --module-path build/packages/kryon/src/ui \
    --define KRYON_HOSTED_UI --entry inbe:Main \
    --asset-dir "assets=build/package-assets/inbe/assets" \
    --asset-dir "styles=build/package-assets/inbe/styles" \
    --asset-dir "themes=build/package-assets/inbe/themes" \
    --asset-dir "locales=build/package-assets/inbe/locales" \
    --asset-dir "icons=build/package-assets/inbe/icons" \
    --asset-dir "cells=$output" -o build/inbe-full.zib apps/inbe/inbe.zi
