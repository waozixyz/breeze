#!/bin/sh
# Prepare the source tree for a Gradle Android build. Used by the release
# workflow and by F-Droid's prebuild step, from any working directory.
#
# Runtime assets are compiled into libmain.so by the CMake build
# (scripts/embed-app-assets.py), so the APK assets directory stays empty.
# The CMake build needs the locked Ziran packages under build/packages.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

rm -rf droid/app/src/main/assets
mkdir -p droid/app/src/main/assets
sh scripts/packages.sh --locked
