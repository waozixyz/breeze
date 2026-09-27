#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/sync-account-crypto-zi-test"
mkdir -p "$work/generated"

"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/generated" \
    "$root/src/storage/sync_crypto.zi" \
    "$root/src/storage/sync_account_crypto.zi" \
    "$root/src/storage/sync_account_text.zi" \
    "$root/src/storage/sync_account_parse.zi" \
    "$root/src/storage/sync_account_sign.zi" \
    "$root/src/storage/sync_account_host.zi" \
    "$root/src/storage/sync_crypto_random.zi" \
    "$root/src/storage/sync_crypto_hmac.zi" \
    "$root/src/storage/sync_crypto_poly1305.zi" \
    "$root/src/storage/sync_crypto_chacha.zi" \
    "$root/src/storage/sync_account_encrypted.zi"

"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-function \
    -I"$root/vendor/ziran/include" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$work/generated" -I"$work/generated/storage" \
    "$root/tests/sync_account_crypto_zi_test.c" \
    "$work/generated/storage/sync_crypto.c" \
    "$work/generated/storage/sync_account_crypto.c" \
    "$work/generated/storage/sync_account_text.c" \
    "$work/generated/storage/sync_account_parse.c" \
    "$work/generated/storage/sync_account_sign.c" \
    "$work/generated/storage/sync_account_host.c" \
    "$work/generated/storage/sync_crypto_random.c" \
    "$work/generated/storage/sync_crypto_hmac.c" \
    "$work/generated/storage/sync_crypto_poly1305.c" \
    "$work/generated/storage/sync_crypto_chacha.c" \
    "$work/generated/storage/sync_account_encrypted.c" \
    "$work/generated/byte_text_linux.c" \
    "$work/generated/text_buffers.c" \
    "$liboqs" -lm -lpthread -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
