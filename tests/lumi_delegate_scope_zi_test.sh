#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"${ZIRAN_BIN:-"$root/build/packages/ziran/build/bin/ziran"}"}
launcher=$compiler
ziran_dir=$(cd "$root" && "$launcher" pkg path ziran)
monocypher=$(cd "$root" && "$launcher" pkg path monocypher)
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d /tmp/inbe-lumi-delegate-scope.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
python3 "$root/scripts/stage-practice-figure.py"
cd "$root"
"$compiler" build --project --offline ${PACKAGE_FLAGS:-} --module-path "$root/build/practice-figure" --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --entry lumi_delegate_scope_behavior:Check \
    -o "$work/generated" "$root/tests/lumi_delegate_scope_behavior.zi" "$root/tests/sync_test_host.zi" "$root/tests/delegate_account_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "lumi_delegate_scope_behavior.h"
#include "zir_string.h"
#include <stdio.h>
#include <stdint.h>
// The fixture exercises scope and permissions without a display or raster assets.
int32_t ImageWidth(String path) { (void)path; return 0; }
int32_t ImageHeight(String path) { (void)path; return 0; }
// No fake bundle is called.
int32_t __wrap_AppsInstalledMask(void) { return 1 | 2 | 8 | 16; }
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "Lumi delegated scope check failed with code %d\n", result);
    return result ? 1 : 0;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$ziran_dir/include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" -I"$monocypher/src" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/src/monocypher.c" "$monocypher/src/optional/monocypher-ed25519.c" "$liboqs" \
    -Wl,--gc-sections -Wl,--wrap=AppsInstalledMask -ldl -lpthread -lm -o "$work/test"
APP_DATA_ROOT="$work/data" "$work/test"
printf '%s\n' 'Lumi delegated history scope, private tools, expiry and owner policy checks passed'
