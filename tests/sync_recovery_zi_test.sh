#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
webp=${WEBP_A:-$root/vendor-builds/linux/x86_64/kryon-webp/libkryonwebp.a}
test -f "$webp"
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/sync-recovery-zi-test
native_libraries=$(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11)

# Serialize concurrent checks before replacing the stable generated output.
exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/c"
# Use the application's package graph so public UI imports retain their aliases.
cd "$root"
python3 scripts/stage-practice-figure.py
# shellcheck disable=SC2086
sh scripts/run-ziran.sh "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main \
    --module-path "$root/build/practice-figure" \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root/tests" --module-path "$root/tests" \
    -o "$work/c" "$root/tests/sync_recovery_behavior.zi"
# The app's SQLite amalgamation resolves the database calls that the kept
# storage helpers reach; no database opens here, so they return early.
# The harness's GetTime stands in for the host's monotonic clock, so the
# retry deadlines follow the test's own time.
"${CC:-cc}" -std=gnu11 -w -DZIRAN_BOUNDS_CHECK \
    -DGetTime=__wrap_app_monotonic_seconds -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    -I"$root/vendor-builds/sqlite" \
    "$root/tests/sync_recovery_link_test.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    $(find "$work/c" -name '*.c' -type f | grep -v -e '/storage_core.c$' -e '/sync_nodes.c$' \
        -e '/storage_settings.c$' -e '/storage_json_sql.c$' -e '/sync_outbox.c$' \
        -e '/sync_state.c$' -e '/sync_migrations.c$' -e '/sync_record_codec.c$' \
        -e '/sync_collections.c$' -e '/sync_record_crypto.c$' -e '/sync_apply.c$' \
        -e '/sync_exchange.c$' -e '/storage_profile_stats.c$' \
        -e '/storage_export_csv.c$') \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libziran_mp3.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbisfile.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbis.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libogg.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libopus/libopus.a" \
    "$webp" $native_libraries -Wl,--wrap=app_monotonic_seconds \
    -ldl -lpthread -lz -lm -latomic -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo "sync recovery Ziran/native test passed"
