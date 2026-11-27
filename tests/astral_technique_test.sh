#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
stdlib=${2:-"$root/build/packages/ziran/std"}
out="$root/build/astral-technique-test"
mkdir -p "$out"
cd "$root"
set -- --root "$root/tests"  
"$bin/ziran" ir --project --offline ${PACKAGE_FLAGS:-} "$@" -o "$out/ir" "$root/tests/astral_technique_test.zi"
for form in source saved; do
    source="$root/tests/astral_technique_test.zi"
    if test "$form" = saved; then
        source="$out/ir/astral_technique_test.zir"
    fi
    LDLIBS=-lm "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} "$@" --entry astral_technique_test:main --exe -o "$out/$form" "$source"
    "$out/$form/astral_technique_test"
done
