#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/sync-recovery-zi-test

# Serialize concurrent checks before replacing the stable generated output.
exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "self=$root/build/packages/self/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" --module-path "kryon=$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "qrcode=$root/build/packages/qrcode/src" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/tests/sync_recovery_behavior.zi"
"${CC:-cc}" -std=gnu11 -w -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    "$root/tests/sync_recovery_link_test.c" \
    $(ls "$work/c"/*.c | grep -v -e '/storage_core.c$' -e '/sync_nodes.c$' \
        -e '/storage_settings.c$' -e '/storage_json_sql.c$' -e '/sync_outbox.c$' \
        -e '/sync_state.c$' -e '/sync_migrations.c$' -e '/sync_record_codec.c$' \
        -e '/sync_collections.c$' -e '/sync_record_crypto.c$' -e '/sync_apply.c$' \
        -e '/sync_exchange.c$' -e '/storage_profile_stats.c$' \
        -e '/storage_export_csv.c$') \
    -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "sync recovery Ziran/native test passed"
