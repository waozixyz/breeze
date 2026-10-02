#!/bin/sh
set -eu

unset DISPLAY WAYLAND_DISPLAY
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/app-clock-test
std=$root/build/packages/ziran/std
mkdir -p "$work"

# Both browser defines occur in the build; each must select the browser ABI
# even when a caller supplies only one of them.
for platform in native web emscripten windows; do
    out=$work/$platform
    case $platform in
        native) set -- ;;
        web) set -- --define PLATFORM_WEB ;;
        emscripten) set -- --define __EMSCRIPTEN__ ;;
        windows) set -- --define _WIN32 ;;
    esac
    "$bin/zi2c" --no-main --prune-stale --root "$root/src" \
        --module-path "$std" "$@" -o "$out" \
        "$root/src/app/app_clock_host.zi"
    if test "$platform" = native; then
        test -f "$out/date_time_linux.c"
    else
        test ! -f "$out/date_time_linux.c"
        test -f "$out/time_parts.c"
    fi
    if test "$platform" = windows; then
        # The Windows foreign calls use the CRT's 64-bit time entry points.
        # Cross-compile when MinGW is available; native runs below also cover
        # the portable API and both browser selection conventions.
        if command -v "${WINDOWS_CC:-x86_64-w64-mingw32-gcc}" >/dev/null 2>&1; then
            "${WINDOWS_CC:-x86_64-w64-mingw32-gcc}" -std=c11 -Wall -Wextra -Werror \
                -Wno-unused-function -I"$out" \
                "$root/tests/app_clock_host_test.c" \
                "$out/app/app_clock_host.c" "$out"/*.c \
                -o "$out/test.exe"
        fi
        continue
    fi
    "${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
        -I"$out" "$root/tests/app_clock_host_test.c" \
        "$out/app/app_clock_host.c" "$out"/*.c \
        -o "$out/test"
    for timezone in UTC0 'EST5EDT,M3.2.0/2,M11.1.0/2' JST-9; do
        TZ=$timezone "$out/test"
    done
done
echo 'app-clock-test-ok: native provider, browser guards, Windows generation, local timezones'
