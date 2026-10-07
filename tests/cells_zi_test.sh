#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/cells-test
mkdir -p "$work/generated" "$work/wrong-record" "$work/wrong-scalar"
sh "$root/scripts/build-cells.sh" "$ziran"
# These are valid portable bundles with an identity handshake and all three
# named capabilities. Their mismatched values must never reach a decoder.
for shape in wrong-record wrong-scalar; do
    if [ "$shape" = wrong-record ]; then
        declaration='Bad :: struct { unexpected: s32; }'
        argument='Bad.{.unexpected = 1}'
        type='Bad'
    else
        declaration=''
        argument='"wrong"'
        type='string'
    fi
    cat > "$work/$shape/lists.zi" <<ZIRAN
#import, file "../../../src/cells/lists_types.zi";
#import, file "../../../apps/lists/lists_view.zi";
host_api :: #system_library "host_api";
ReadListsHost :: () -> ListsMessage #foreign host_api;
WriteListsHost :: (value: $type) #foreign host_api;
PersistListsHost :: (value: $type) -> s32 #foreign host_api;
$declaration
#program_export
Main :: () -> s32 {
    message := ReadListsHost()
    if message.action == 0 { return 1 }
    if message.action == LISTS_FRAME { unused ListsView(message) }
    WriteListsHost($argument)
    return PersistListsHost($argument)
}
ZIRAN
    "$ziran" bundle --root "$work/$shape" --module-path "$root/build/packages/kryon/src/ui" \
        --define KRYON_HOSTED_UI --entry lists:Main -o "$work/$shape.zib" "$work/$shape/lists.zi"
done
"$ziran" bundle --root "$root" --module-path "$root/build/packages/kryon/src/ui" \
    --define KRYON_HOSTED_UI --entry inbe:Main -o "$work/missing-assets.zib" \
    "$root/apps/inbe/inbe.zi"
mkdir -p "$work/invalid-nested"
printf 'ZIB' > "$work/invalid-nested/lists.zib"
cp "$root/build/cells/habits.zib" "$root/build/cells/practices.zib" "$work/invalid-nested/"
"$ziran" bundle --root "$root" --module-path "$root/build/packages/kryon/src/ui" \
    --define KRYON_HOSTED_UI --entry inbe:Main \
    --asset-dir "cells=$work/invalid-nested" -o "$work/invalid-nested.zib" \
    "$root/apps/inbe/inbe.zi"
"$ziran" build --target=c --no-main --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" \
    -o "$work/generated" "$root/tests/cells_behavior.zi" "$root/tests/sync_test_host.zi"
"${CC:-cc}" -D_GNU_SOURCE -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" -iquote "$work/generated/cells" \
    -I"$root/build/packages/monocypher/src" -I"$root/build/packages/monocypher/src/optional" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$root/tests/cells_host_test.c" "$work/generated"/*.c \
    "$root/build/packages/monocypher/src/monocypher.c" \
    "$root/build/packages/monocypher/src/optional/monocypher-ed25519.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" "$root/build/ziran-toolchain/libziran.a" \
    -Wl,--wrap=tmpfile -Wl,--wrap=BundleInstanceRun -Wl,--wrap=BundleInstantiate \
    -Wl,--wrap=package_manager_PackageInstalledBytes -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
# All data and fixture upgrade paths are disposable. No owner profile is used.
data=$(mktemp -d)
trap 'rm -rf "$data"' EXIT HUP INT TERM
mkdir -p "$data/module-data"
cp "$root/tests/fixtures/schema-1.8.9.sql" "$data/"
cd "$data"
env -u INBE_DIARY_IMPORT -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    APP_DATA_ROOT="$data/module-data" "$work/test" "$root/build/cells/lists.zib" \
    "$root/build/cells/habits.zib" "$root/build/cells/practices.zib" \
    "$work/wrong-record.zib" "$work/wrong-scalar.zib" "$root/build/inbe-full.zib" \
    "$work/missing-assets.zib" "$work/invalid-nested.zib" "$root/build/cells/diary.zib" "$root/build/cells/lumi.zib"
