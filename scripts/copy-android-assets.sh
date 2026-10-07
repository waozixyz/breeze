#!/bin/sh
# Prepare the source tree for a Gradle Android build. Used by the release
# workflow and by F-Droid's prebuild step, from any working directory.
#
# Gradle stages the portable app package once in generated APK assets.
# Only the tiny native bootstrap assets are compiled into each libmain.so.
# The CMake build needs the locked Ziran packages under build/packages.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

rm -rf droid/app/src/main/assets
mkdir -p droid/app/src/main/assets
sh scripts/packages.sh --locked
