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
packages=$(sh scripts/package-paths.sh)
output=${2:-build/cells}
python3 scripts/check-package-versions.py
python3 tests/font_glyph_coverage_test.py
python3 tests/locale_translated_test.py
python3 tests/locale_used_keys_test.py
python3 tests/lumi_guide_narration_test.py "$ziran"
python3 scripts/generate-package-versions.py
python3 scripts/animation_inventory.py --check
python3 scripts/prepare-package-assets.py
if [ ! -s build/package-assets/inbe/assets/apps/apps.zx ]; then
    echo 'Root Apps requires the reviewed Apps controller bundle; run make cells' >&2
    exit 1
fi
python3 scripts/release_notes.py CHANGELOG.md build/package-assets/inbe/assets/app/release-notes.json
python3 scripts/practice_content.py "$ziran"
# Bundles are embedded by directory, so staging starts empty: a renamed or
# removed bundle, or one in an older format, must not ride along.
mkdir -p "$output"
rm -f "$output"/*.zx "$output"/*.zib
rm -rf build/bundled-cells build/entity
mkdir -p build/bundled-cells
entity_dir="$root/build/packages/entity"
mkdir -p build/entity
"$ziran" bundle --root "$entity_dir" --module-path "$entity_dir/src" \
    --module-path kryon=build/packages/kryon/src/backend \
    --module-path kryon=build/packages/kryon/src/ui --module-path build/packages/kryon/src/ui \
    --module-path build/packages/ziran/std --module-path qrcode=build/packages/qrcode/src \
    --define KRYON_HOSTED_UI \
    --asset-dir "assets=$entity_dir/assets" --entry entity:Main -o build/entity/entity.zx "$entity_dir/src/entity.zi"
for feature in lists habits practices diary lumi leaderboard; do
    source=$feature
    entry=$feature
    if [ "$feature" = practices ]; then source=practice; entry=practice; fi
    locale_args=
    if [ "$feature" = diary ]; then locale_args="--asset-dir locales=build/package-assets/diary/locales"; fi
    # shellcheck disable=SC2086
    "$ziran" bundle --root . --module-path src $locale_args $packages \
        --module-path build/packages/kryon/src/ui \
        --define KRYON_HOSTED_UI \
        --module-path build/packages/ziran/std \
        --asset-dir "assets=build/package-assets/$feature/assets" \
        --entry "$entry:Main" -o "$output/$feature.zx" \
        "apps/$source/$source.zi"
done
# Removing a sidebar shortcut never removes its bundled package.
for feature in lists habits practices diary lumi leaderboard; do
    cp "$output/$feature.zx" build/bundled-cells/
done
# shellcheck disable=SC2086
"$ziran" bundle --root . --module-path src $packages \
    --module-path build/packages/ziran/std --module-path build/packages/kryon/src/ui \
    --define KRYON_HOSTED_UI --entry inbe:Main \
    --asset-dir "assets=build/package-assets/inbe/assets" \
    --asset-dir "styles=build/package-assets/inbe/styles" \
    --asset-dir "themes=build/package-assets/inbe/themes" \
    --asset-dir "locales=build/package-assets/inbe/locales" \
    --asset-dir "icons=build/package-assets/inbe/icons" \
    --asset-dir "assets/entity=$entity_dir/assets/entity" --asset-dir "assets/entity/bundles=build/entity" \
    --asset-dir "cells=build/bundled-cells" -o build/inbe.zx apps/inbe/inbe.zi
# shellcheck disable=SC2086
"$ziran" bundle --root . --module-path src $packages \
    --module-path build/packages/ziran/std --module-path build/packages/kryon/src/ui \
    --define KRYON_HOSTED_UI --entry inbe:Main \
    --asset-dir "assets=build/package-assets/inbe/assets" \
    --asset-dir "styles=build/package-assets/inbe/styles" \
    --asset-dir "themes=build/package-assets/inbe/themes" \
    --asset-dir "locales=build/package-assets/inbe/locales" \
    --asset-dir "icons=build/package-assets/inbe/icons" \
    --asset-dir "assets/entity=$entity_dir/assets/entity" --asset-dir "assets/entity/bundles=build/entity" \
    --asset-dir "cells=$output" -o build/inbe-full.zx apps/inbe/inbe.zi
