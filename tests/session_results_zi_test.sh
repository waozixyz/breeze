#!/bin/sh
set -eu

# Storage import/export and migration behaviour, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
runtime_library=$(dirname "$ziran")/../libziran.a
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/session-results-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
# Keep the production timer/storage behavior, without importing every practice
# screen and the full application beside this fixture's host-effect exports.
python3 - "$root" "$work" <<'PY'
from pathlib import Path
import os
import sys
root, work = map(Path, sys.argv[1:])
(work / 'session_results_test_root.zi').write_text(
    'SessionResultsTestRoot :: "' + str(work / 'data') + '";\n')
source = (root / 'src/practices/meditation/meditation_session.zi').read_text()
start = source.index('background_remainder_ms:')
end = source.index('\nsave_elapsed ::', start)
body = source[start:end]
assert 'meditation_start_configured ::' in body and 'meditation_advance_elapsed ::' in body
body = body.replace('meditation_advance_elapsed ::', '#program_export\nmeditation_advance_elapsed ::', 1)
imports = ['apps/shared_state', 'apps/module_host', 'apps/practice_types',
           'apps/app_codec', 'apps/hosted_assets', 'core/types', 'app/app_types',
           'app/session_screen', 'app/activity_start', 'app/app_notifications',
           'app/app_modal_state', 'app/app_route_state', 'app/text_buffers',
           'app/exercise_types', 'storage/data', 'practices/session_results']
header = ''.join('#import, file "' + os.path.relpath(root / 'src' / (name + '.zi'), work) + '";\n'
                 for name in imports)
header += '#import, file "' + os.path.relpath(root / 'apps/practice/recovery.zi', work) + '";\n'
header += '''#import "byte_text_linux"
c3 :: #system_library "c";
using ExerciseType;
practice_background_start :: (app: *InnerBreeze, id: s32) #foreign c3;
practice_active_background_stop :: (app: *InnerBreeze) #foreign c3;
app_auto_sync :: (app: *InnerBreeze) -> s32 #foreign c3;
sync_habits_for_activity :: (app: *InnerBreeze, activity: s32) #foreign c3;
meditation_music_start_session :: (app: *InnerBreeze) #foreign c3;
meditation_music_fade_out :: (app: *InnerBreeze) #foreign c3;
meditation_music_stop :: (app: *InnerBreeze) #foreign c3;
app_play_bell_cue :: (app: *InnerBreeze, volume: float32) #foreign c3;
'''
(work / 'meditation_session_behavior.zi').write_text(header + body)
PY
"$ziran" build --project ${PACKAGE_FLAGS:---offline} --target=c --define PLATFORM_DESKTOP --define DESKTOP_HOST \
    --define NATIVE_WINDOW_HAVE_SDL --root "$root/tests" \
    --module-path "$work" \
    --entry session_results_behavior:Check \
    -o "$work/generated" "$root/tests/session_results_behavior.zi" \
    "$work/meditation_session_behavior.zi" \
    "$root/tests/app_hooks_host.zi" "$root/tests/leaderboard_hooks_host.zi" \
    "$root/tests/habit_edit_hooks_host.zi" "$root/tests/clock_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "session_results_behavior.h"
#include <stdio.h>
void __wrap_meditation_music_stop(void *app) { (void)app; }
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
# Optimize the full application-state initializer, as the native app build does.
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -I"$include" -iquote"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$root/build/packages/monocypher/src" -I"$root/build/packages/monocypher/src/optional" \
    $(find "$work/generated" -type d -printf ' -iquote %p') \
    $(find "$work/generated" -type f -name '*.c') "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    "$root/build/packages/monocypher/src/monocypher.c" \
    "$root/build/packages/monocypher/src/optional/monocypher-ed25519.c" \
    "$runtime_library" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libziran_mp3.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbisfile.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbis.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libogg.a" \
    -Wl,--wrap=meditation_music_stop -Wl,--gc-sections -l:libcurl.so.4 -l:libopus.so.0 \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11 libwebp libwebpdemux) \
    -ldl -lpthread -lz -lm -latomic -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT="$work/data"
export APP_DATA_ROOT
cd "$root"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf "$work/data"
