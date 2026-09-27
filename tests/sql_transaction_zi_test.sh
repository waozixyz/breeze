#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/sql-transaction-zi-test
mkdir -p "$work/generated"

"$bin/zi2c" --no-main --root "$root/src" \
    -o "$work/generated" "$root/src/storage/sql_transaction.zi"

"${CC:-cc}" -std=c11 -O0 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor/ziran/include" \
    -I"$work/generated" \
    "$root/tests/sql_transaction_zi_test.c" \
    "$work/generated/storage/sql_transaction.c" \
    "$work/generated/sqlite.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" -ldl -lpthread -lm \
    -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY timeout 10s "$work/test"
