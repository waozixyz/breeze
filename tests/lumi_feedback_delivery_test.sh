#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/lumi-feedback-test"
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry lumi_feedback_delivery_behavior:Check -o "$work/generated" \
    "$root/tests/lumi_feedback_delivery_behavior.zi" "$root/tests/sync_test_host.zi"
# Calls within one translation unit cannot be intercepted by the linker's
# --wrap. Isolate the unused conversation branches in this generated fixture;
# either branch aborts if the feedback pump unexpectedly invokes it.
python3 - "$work/generated/lumi_online.c" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
for name in ("LumiOnlineAnswer", "LumiOnlineRequest"):
    source = source.replace(f"lumi_online_{name}(app)", f"__wrap_lumi_online_{name}(app)")
source = source.replace('#include "lumi_online.h"', '#include "lumi_online.h"\n'
    'extern bool __wrap_lumi_online_LumiOnlineAnswer(InnerBreeze *app);\n'
    'extern bool __wrap_lumi_online_LumiOnlineRequest(InnerBreeze *app);')
path.write_text(source)
PY
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include <stdlib.h>
#include "lumi_feedback_delivery_behavior.h"
#include "network_transport.h"
#include "lumi_online.h"
#include "lumi_telegram.h"
#include "app_nav_state.h"
#include "practice_actions.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return FeedbackTestTransport();
}
void __wrap_lumi_telegram_LumiTelegramPump(InnerBreeze *app)
{
    (void)app;
}
bool __wrap_lumi_online_LumiOnlineAnswer(InnerBreeze *app)
{
    (void)app;
    fputs("unexpected online conversation in feedback fixture\n", stderr);
    abort();
}
bool __wrap_lumi_online_LumiOnlineRequest(InnerBreeze *app)
{
    (void)app;
    fputs("unexpected online request in feedback fixture\n", stderr);
    abort();
}
void __wrap_app_apply_nav_route(InnerBreeze *app, int32_t route)
{
    (void)app;
    (void)route;
    abort();
}
bool __wrap_practice_actions_app_start_practice(InnerBreeze *app, int32_t practice)
{
    (void)app;
    (void)practice;
    abort();
}
int main(void)
{
    int result = Check();
    return result == 0 ? 0 : 1;
}
C
monocypher="$root/build/packages/monocypher/src"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport \
    -Wl,--wrap=lumi_telegram_LumiTelegramPump -Wl,--wrap=lumi_online_LumiOnlineAnswer \
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=practice_actions_app_start_practice \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-lumi-feedback-test/data "$work/test"
printf '%s\n' 'Lumi feedback approval, HTTP failure, receipt verification, retries, restart and older outbox upgrade checks passed'
