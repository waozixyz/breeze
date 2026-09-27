#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/sync-crypto-zi-test"
mkdir -p "$work/generated"

"$bin/zi2c" --no-main --root "$root/src" \
    -o "$work/generated" \
    "$root/src/storage/sync_crypto.zi" \
    "$root/src/storage/sync_crypto_hmac.zi" \
    "$root/src/storage/sync_crypto_poly1305.zi" \
    "$root/src/storage/sync_crypto_chacha.zi"

"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror \
    -I"$root/vendor/ziran/include" -I"$work/generated" \
    "$root/tests/sync_crypto_zi_test.c" \
    "$work/generated/storage/sync_crypto.c" \
    "$work/generated/storage/sync_crypto_hmac.c" \
    "$work/generated/storage/sync_crypto_poly1305.c" \
    "$work/generated/storage/sync_crypto_chacha.c" -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
