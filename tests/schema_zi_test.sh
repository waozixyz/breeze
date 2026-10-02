#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/schema-zi-test
rm -rf "$work/generated"
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/schema.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/sql_query.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/user.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/meta.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/vendor-builds/sqlite" \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    "$root/tests/schema_zi_test.c" \
    "$work/generated/c_string.c" "$work/generated/byte_text_linux.c" \
    "$work/generated/schema_sql.c" "$work/generated/sql_transaction.c" \
    "$work/generated/storage/schema.c" \
    "$work/generated/storage/sql_query.c" \
    "$work/generated/storage/user.c" "$work/generated/storage/meta.c" \
    "$work/generated/sqlite.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" -ldl -lpthread -lm \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" \
    "$root/tests/fixtures/schema-1.8.9.sql"
