#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

# Pages needs the three meditation tracks. The published app bundle already
# contains its own assets, so no native or design LFS objects are needed here.
sources=$(git ls-files -- 'unpackaged_assets/audio/*.ogg')
test -n "$sources"
printf '%s\n' "$sources" | while IFS= read -r audio; do
    test -f "$audio"
    if [ "$(head -c 4 "$audio")" = OggS ]; then
        continue
    fi
    git lfs pointer --check --file="$audio"
    oid=$(sed -n 's/^oid sha256://p' "$audio")
    size=$(sed -n 's/^size //p' "$audio")
    download=$(mktemp "$audio.XXXXXX")
    trap 'rm -f "$download"' 0
    curl -fsSL --max-time 120 --retry 2 \
        "https://git.waozi.xyz/waozi/breeze.git/info/lfs/objects/$oid" -o "$download"
    test "$(wc -c < "$download")" -eq "$size"
    printf '%s  %s\n' "$oid" "$download" | sha256sum --check --status
    test "$(head -c 4 "$download")" = OggS
    chmod 644 "$download"
    mv -f "$download" "$audio"
    trap - 0
    printf 'Verified %s from Gitea LFS\n' "$audio"
done
