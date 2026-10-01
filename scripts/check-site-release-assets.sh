#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(dirname -- "$script_dir")
site_index=${SITE_INDEX:-"$root_dir/build/site/index.html"}

version=$(python3 "$root_dir/scripts/check-version.py" --print-version)
version=${SITE_RELEASE_VERSION:-$version}
if [ -z "$version" ]; then
	printf 'Error: could not read APP_VERSION_STRING\n' >&2
	exit 1
fi

if [ ! -f "$site_index" ]; then
	printf 'Error: site index missing: %s\n' "$site_index" >&2
	exit 1
fi

tmp_dir=${TMPDIR:-/tmp}/inbe-site-assets-check.$$
mkdir -p "$tmp_dir"
trap 'rm -rf "$tmp_dir"' EXIT INT TERM

release_assets=$tmp_dir/release-assets.txt
site_assets=$tmp_dir/site-assets.txt
missing_assets=$tmp_dir/missing-assets.txt

if command -v gh >/dev/null 2>&1; then
	gh release view "v$version" --repo waozixyz/inbe --json assets --jq '.assets[].name' > "$release_assets"
else
	curl -fsSL "https://api.github.com/repos/waozixyz/inbe/releases/tags/v$version" |
		awk -F'"' '/"name":/ { print $4 }' > "$release_assets"
fi

sed -n "s#.*https://github.com/waozixyz/inbe/releases/download/v$version/\\([^\"?#]*\\).*#\\1#p" "$site_index" |
	sort -u > "$site_assets"

if [ ! -s "$site_assets" ]; then
	printf 'Error: no GitHub release download links found in %s\n' "$site_index" >&2
	exit 1
fi

sort -u "$release_assets" > "$release_assets.sorted"
mv "$release_assets.sorted" "$release_assets"

comm -23 "$site_assets" "$release_assets" > "$missing_assets"
if [ -s "$missing_assets" ]; then
	printf 'Error: site links missing GitHub release assets for v%s:\n' "$version" >&2
	sed 's/^/  /' "$missing_assets" >&2
	exit 1
fi

printf 'site release links match GitHub release v%s\n' "$version"
