#!/bin/sh

set -eu

if [ $# -gt 0 ]; then
	version=$1
else
	script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
	root_dir=$(dirname -- "$script_dir")
	version=$(python3 "$root_dir/scripts/check-version.py" --print-version)
fi

case "$version" in
	''|*[!0-9.]*)
		printf 'Error: version must be numeric X.Y.Z\n' >&2
		exit 1
		;;
esac
if ! printf '%s\n' "$version" | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'; then
	printf 'Error: version must be numeric X.Y.Z\n' >&2
	exit 1
fi

cat <<EOF
inbe-$version.apk
inbe-$version-gplay.apk
inbe-$version-gplay.aab
inbe-web.zip
inbe-chrome-web-store.zip
inbe-firefox-addons.zip
inbe-windows.zip
inbe-windows-setup-$version.exe
inbe-linux-x86_64.AppImage
inbe-linux-aarch64.AppImage
inbe_${version}_amd64.deb
inbe_${version}_arm64.deb
inbe-${version}-1.x86_64.rpm
inbe-${version}-1.aarch64.rpm
inbe_${version}_x86_64.snap
inbe_${version}_aarch64.snap
inbe-${version}-x86_64.flatpak
inbe-${version}-aarch64.flatpak
EOF
