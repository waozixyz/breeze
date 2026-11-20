#!/bin/sh
# Package the website with the supplied web artifact and published downloads.
set -eu
cd "$(dirname "$0")/.."

release_dir=build/released-web
mkdir -p "$release_dir"
curl -fsSL --retry 3 https://api.github.com/repos/waozixyz/breeze/releases/latest -o "$release_dir/release.json"
python3 - "$release_dir/release.json" "${SITE_WEB_DIR:-}" > "$release_dir/release.env" <<'PY'
import json
import re
import sys
from pathlib import Path

release = json.loads(Path(sys.argv[1]).read_text())
match = re.fullmatch(r"v((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))", release["tag_name"])
if not match:
    raise SystemExit("Unexpected published release tag")
version = match[1]
assets = {asset["name"] for asset in release["assets"]}
android = next((name for name in (f"inbe-{version}-arm64-v8a.apk", f"inbe-{version}.apk") if name in assets), None)
if not android:
    raise SystemExit("Published release is missing an Android APK")
if not sys.argv[2] and "inbe-web.zip" not in assets:
    raise SystemExit("Published release is missing the web bundle")
print(f"export SITE_RELEASE_VERSION={version}")
print(f"export SITE_ANDROID_APK_ASSET={android}")
PY
. "./$release_dir/release.env"
release_url="https://github.com/waozixyz/breeze/releases/download/v$SITE_RELEASE_VERSION"
if [ -z "${SITE_WEB_DIR:-}" ]; then
    curl -fsSL --retry 3 "$release_url/inbe-web.zip" -o "$release_dir/inbe-web.zip"
    rm -rf "$release_dir/app"
    mkdir -p "$release_dir/app"
    unzip -q "$release_dir/inbe-web.zip" -d "$release_dir/app"
    SITE_WEB_DIR="$PWD/$release_dir/app"
fi
test -s "$SITE_WEB_DIR/index.wasm"

make -f site/production.mk package-unpackaged-assets
SITE_WEB_DIR="$SITE_WEB_DIR" sh site/build.sh
# Gitea's job token is only valid on Gitea. Downloads still follow the public release.
env -u GITHUB_TOKEN -u GH_TOKEN make -f site/production.mk site-release-assets-check

if [ -n "${APT_SIGNING_KEY:-}" ]; then
    deb_dir="$release_dir/debs"
    mkdir -p "$deb_dir"
    for arch in amd64 arm64; do
        deb="inbe_${SITE_RELEASE_VERSION}_${arch}.deb"
        curl -fsSL --retry 3 "$release_url/$deb" -o "$deb_dir/$deb"
    done
    APT_DEB_DIR="$deb_dir" sh scripts/build-apt-repo.sh build/site/apt "$SITE_RELEASE_VERSION"
else
    python3 site/preserve-apt.py build/site/apt
fi
