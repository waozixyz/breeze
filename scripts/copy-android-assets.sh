#!/usr/bin/env bash
# Generate embedded assets for Android without requiring nix-shell.
# This script is used by GitHub Actions and F-Droid builds
# This script works from any directory by detecting the repository root

set -e

# Find the repository root by locating this script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to repository root so all relative paths work correctly
cd "$REPO_ROOT" || exit 1

echo "Running from repository root: $(pwd)"
echo "Generating embedded assets for Android..."

ANDROID_DIR="droid"
ASSETS_DIR="$ANDROID_DIR/app/src/main/assets"

# Keep APK assets empty; runtime assets are compiled into the native library.
rm -rf "$ASSETS_DIR"
mkdir -p "$ASSETS_DIR"

echo "Using Kryon-generated Noto font subsets..."

mkdir -p build
sh build/packages/kryon/scripts/embed-assets.sh build/inbe_embedded_assets.c \
    build/packages/kryon/styles/kryon/*.kss \
    locales/*.txt \
    assets/easteregg/art.png \
    assets/easteregg/waozi.png \
    assets/practices/whm/1.png \
    assets/practices/whm/2.png \
    assets/practices/meditation/1.png \
    assets/practices/*/banner*.png \
    assets/practices/sunsalutation/poses_man_sheet.png \
    assets/practices/sunsalutation/poses_woman_sheet.png \
    assets/fonts/subset/NotoSans-Inbe-Regular.ttf \
    assets/fonts/subset/NotoSansSC-Inbe-Regular.otf \
    assets/fonts/subset/NotoSansJP-Inbe-Regular.otf \
    assets/fonts/subset/NotoSansKR-Inbe-Regular.otf \
    assets/fonts/subset/NotoSansTC-Inbe-Regular.otf \
    assets/sounds/*.ogg

echo "Embedded assets generated successfully!"
