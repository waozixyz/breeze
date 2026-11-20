#!/bin/sh
set -eu

mode=${1:?Specify write or verify}
directory=${2:?Specify the web build directory}
key=${3:?Specify the web build input key}
printf '%s\n' "$key" | grep -qEx '[0-9a-f]{64}'
if [ "$mode" = write ]; then
    revision=$(git rev-parse HEAD)
fi
cd "$directory"

for file in index.html index_boot.js index.js index.wasm webmanifest.json; do
    test -s "$file"
done

artifact_hashes() {
    find . -type f ! -path './source-build.txt' ! -path './source-build.sha256' -printf '%P\0' |
        LC_ALL=C sort -z | xargs -0 sha256sum --
}

case "$mode" in
    write)
        artifact_hashes > source-build.sha256
        printf '%s\n%s\n' "$key" "$revision" > source-build.txt
        ;;
    verify)
        {
            IFS= read -r built_key
            IFS= read -r revision
        } < source-build.txt
        test "$built_key" = "$key"
        printf '%s\n' "$revision" | grep -qEx '[0-9a-f]{40}'
        printf '%s\n%s\n' "$key" "$revision" | cmp -s - source-build.txt
        artifact_hashes | cmp -s - source-build.sha256
        ;;
    *)
        printf 'Unknown web build receipt mode: %s\n' "$mode" >&2
        exit 2
        ;;
esac
