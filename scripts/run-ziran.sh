#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/build"
# Separate Make/Gradle invocations and Android ABIs share the same compiler slot.
exec flock "$root/build/ziran-compiler.lock" "$@"
