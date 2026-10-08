#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d "${TMPDIR:-/tmp}/inbe-settings-telegram-ui.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/c"
"$bin/zi2c" --no-main --define PLATFORM_DESKTOP --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/src/screens/settings/settings_telegram.zi"
# The fixture supplies the raster host; keep the real retained UI and protocol code.
set -- "$root/tests/settings_telegram_ui_test.c"
find "$work/c" -type f -name '*.c' ! -name 'raylib_runtime.c' -print > "$work/c-files"
while IFS= read -r generated; do
    set -- "$@" "$generated"
done < "$work/c-files"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -Wl,--wrap=storage_get_setting_text -Wl,--wrap=storage_has_sync_account \
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=lumi_telegram_LumiTelegramOpen \
    -Wl,--wrap=LocaleText -Wl,--wrap=FrameTextHold \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$work/c/screens/settings" \
    "$@" "$liboqs" -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
