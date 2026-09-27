#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
standard=${2:-"$root/vendor/ziran/std"}
include=${ZIRAN_INCLUDE:-"$root/vendor/ziran/include"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

source=$root/tests/friend_requests_behavior.zi
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$standard" -o "$work/ir" "$source"
"$bin/zi2zib" bundle --root "$root/tests" --module-path "$root/src" \
    --module-path "$standard" --entry friend_requests_behavior:Answer \
    -o "$work/source.zib" "$source"
"$bin/zi2zib" bundle --root "$work/ir" --module-path "$work/ir" \
    --entry friend_requests_behavior:Answer -o "$work/saved.zib" \
    "$work/ir/friend_requests_behavior.zir"
cmp "$work/source.zib" "$work/saved.zib"
test "$("$bin/zi2zib" run "$work/source.zib")" = 42
test "$("$bin/zi2zib" run "$work/saved.zib")" = 42

"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$standard" -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/c" \
    "$root/tests/friend_requests_host_test.c" \
    "$work/c"/*.c \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
