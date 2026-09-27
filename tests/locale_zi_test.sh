#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/locale-zi-test
mkdir -p "$work/c" "$work/dropdown-c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" "$root/src/app/locale.zi"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/app/locale_dropdown.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/dropdown-c" "$root/src/app/locale_dropdown.zi"
"${CC:-cc}" -std=c11 -I"$root/vendor/ziran/include" \
    -I"$work/dropdown-c" -c "$work/dropdown-c/app/locale_dropdown.c" \
    -o "$work/locale_dropdown.o"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/locale_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/locales/index.txt" "$root/locales/en.txt" \
    "$root/locales/es.txt" "$root/locales/ru.txt" "$root/locales/ja.txt"
cat > "$work/c/main.c" <<'C'
#include "locale_link_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections -I"$root/vendor/ziran/include" \
    -I"$work/c" -I"$root/src/app" \
    "$work/assets.c" \
    "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY LANGUAGE=es_AR.UTF-8 "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY ZIRAN_BIN="$bin/ziran" \
    sh "$root/tests/locale_parser_portability_test.sh"
env -u DISPLAY -u WAYLAND_DISPLAY ZIRAN_BIN="$bin/ziran" \
    sh "$root/tests/locale_policy_portability_test.sh"
echo "Inbe locale Ziran/native link test passed"
