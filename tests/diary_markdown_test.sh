#!/bin/sh
# Diary Markdown: embeds, library places, insertion edits, the editor
# preview and spelling masking, natively with sanitizers and in the Ziran VM
# the package runs in.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/diary-markdown-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
modules=""

rm -rf "$work"
mkdir -p "$work/c"
# shellcheck disable=SC2086
"$bin/ziran" build --target=c --project --offline --no-main --root "$root" $modules \
    -o "$work/c" "$root/tests/diary_markdown_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "tests/diary_markdown_behavior.h"
int main(void)
{
    int result = Answer();
    if (result != 42) {
        fprintf(stderr, "diary markdown check %d failed\n", result);
        return 1;
    }
    return 0;
}
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -fsanitize=address,undefined \
    -I"$include" -I"$work/c" "$work/c"/*.c "$work/c/tests"/*.c -lm -o "$work/test"
# The package runs in the VM, which reclaims its temporary text; the native
# build of this check keeps it, so only memory errors fail here.
env -u DISPLAY -u WAYLAND_DISPLAY ASAN_OPTIONS=detect_leaks=0 "$work/test"
# shellcheck disable=SC2086
"$bin/ziran" bundle --project --offline --root "$root" $modules --define KRYON_HOSTED_UI \
    --entry diary_markdown_behavior:Answer -o "$work/check.zx" \
    "$root/tests/diary_markdown_behavior.zi"
test "$("$bin/ziran" run "$work/check.zx")" = 42
printf '%s\n' 'Diary Markdown: embeds, library places, inserted photos, the editor preview and spelling masking passed natively and in the VM'
