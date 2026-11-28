#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
sqlite=${3:-"$root/vendor-builds/sqlite/sqlite3.c"}
work=$(mktemp -d "${TMPDIR:-/tmp}/inbe-settings-telegram-ui.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/c" "$work/storage"
cd "$root"
python3 scripts/stage-practice-figure.py
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --module-path "$root/build/practice-figure" --target=c --no-main \
    --define PLATFORM_DESKTOP --root "$root/src" \
    -o "$work/c" "$root/src/screens/settings/settings_telegram.zi"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --define PLATFORM_DESKTOP --root "$root/src" \
    -o "$work/storage" "$root/src/storage/storage_thread_buffers.zi"
for header in "$work/c"/kryon__session.h "$work/c"/kryon__tree.h "$work/c"/kryon__tree_input.h "$work/c"/kryon__paint_queue.h "$work/c"/kryon__scroll_device.h "$work/c"/kryon__scroll.h; do
    test -f "$header"
    printf '#include "%s"\n' "${header##*/}"
done > "$work/c/settings_telegram_ui_backend.h"
printf '#define DrawTestScroll(session, props) kryon__scroll_Draw((session), (props), (Source_Code_Location){0})\n' >> "$work/c/settings_telegram_ui_backend.h"
printf 'typedef kryon__scroll_props_Props TestScrollProps;\n' >> "$work/c/settings_telegram_ui_backend.h"
set -- "$root/tests/settings_telegram_ui_test.c"
find "$work/c" -type f -name '*.c' -print > "$work/c-files"
while IFS= read -r generated; do
    set -- "$@" "$generated"
done < "$work/c-files"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -Wl,--wrap=storage_get_setting_text -Wl,--wrap=storage_has_sync_account \
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=lumi_telegram_LumiTelegramOpen \
    -Wl,--wrap=bundled_app_records_BundledAppRecordRead \
    -Wl,--wrap=LocaleText -Wl,--wrap=FrameTextHold \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$work/c/screens/settings" \
    "$@" "$work/storage/storage_thread_buffers.c" "$sqlite" "$liboqs" -lm -pthread -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    HARMONY_DESKTOP_RECOVERY=0 "$work/test"
