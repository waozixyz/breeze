#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

mkdir -p build/scratch
artifact=$(mktemp -d build/scratch/site-web-build.XXXXXX)
trap 'rm -rf "$artifact"' EXIT
key=$(sh site/web-build-key.sh)
receipt=site/web-build-receipt.sh

reject() {
    if sh "$receipt" verify "$artifact" "$1" 2>/dev/null; then
        printf 'Accepted %s\n' "$2" >&2
        exit 1
    fi
}

reject "$key" 'a cache miss'
for file in index.html index_boot.js index.js index.wasm webmanifest.json; do
    printf '%s\n' "$file" > "$artifact/$file"
done
mkdir "$artifact/web-assets"
printf 'asset\n' > "$artifact/web-assets/test asset.txt"
sh "$receipt" write "$artifact" "$key"
sh "$receipt" verify "$artifact" "$key"

other_key=$(printf '%s\n' "$key" | sha256sum | cut -d ' ' -f 1)
reject "$other_key" 'an artifact for a different source key'
printf '%s\ninvalid-revision\n' "$key" > "$artifact/source-build.txt"
reject "$key" 'an invalid build revision'
sh "$receipt" write "$artifact" "$key"
printf 'modified\n' >> "$artifact/web-assets/test asset.txt"
reject "$key" 'a modified app asset'
rm "$artifact/index.wasm"
reject "$key" 'a missing WASM binary'
printf 'Verified web build receipt and cache miss, stale and corrupt cases\n'
