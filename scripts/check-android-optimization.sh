#!/usr/bin/env bash
# Verify the actual distributable, not merely the Gradle configuration.
set -euo pipefail

bundle="${1:-droid/app/build/outputs/bundle/gplay/app-gplay.aab}"
mapping='BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map'
if [[ ! -s "$bundle" ]]; then
    echo "FAIL: missing Play bundle: $bundle" >&2
    exit 1
fi
python3 scripts/check-package-size.py --assets "$bundle"

dex_bytes=$(unzip -l "$bundle" | awk '$4 ~ /\/dex\/classes[0-9]*\.dex$/ { total += $1 } END { printf "%.0f", total }')
if (( dex_bytes <= 0 || dex_bytes >= 10000000 )); then
    echo "FAIL: Play DEX size is $dex_bytes bytes; Inbe must stay below its 10 MB release budget." >&2
    exit 1
fi

# R8 embeds this mapping in optimized bundles. Renamed classes demonstrate
# obfuscation ran, but this is NOT Google's proprietary obfuscation percentage.
renamed=$(unzip -p "$bundle" "$mapping" | awk '
    /^# compiler: R8$/ { r8 = 1 }
    /^[^ #].* -> .*:$/ {
        name = $3
        sub(/:$/, "", name)
        if ($1 != name && name !~ /R8\$\$REMOVED/) renamed++
    }
    END {
        if (!r8 || !renamed) exit 1
        print renamed
    }') || {
    echo 'FAIL: bundle is missing an R8 mapping with obfuscated classes.' >&2
    exit 1
}

echo "PASS Play optimization: $dex_bytes uncompressed DEX bytes; $renamed renamed classes; embedded R8 mapping."
