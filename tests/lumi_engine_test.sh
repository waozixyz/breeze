#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work="$root/build/lumi-engine-test"
mkdir -p "$work"
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --entry lumi_tool_budget_behavior:Answer -o "$work/tool-budget.zib" \
    "$root/tests/lumi_tool_budget_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/tool-budget.zib")
[ "$result" = 42 ]
printf '%s\n' 'Lumi tools: complete appearance workflow and bounded continuations passed'
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --entry lumi_engine_behavior:Answer -o "$work/engine.zib" \
    "$root/tests/lumi_engine_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/engine.zib")
[ "$result" = 42 ]
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --entry lumi_response_behavior:Answer -o "$work/response.zib" \
    "$root/tests/lumi_response_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/response.zib")
[ "$result" = 42 ]
printf '%s\n' 'Lumi responses: JSON trailing whitespace accepted; malformed and trailing data rejected'
printf '%s\n' 'Lumi engine: translated commands, Unicode titles, completion matching and bounded actions passed'
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --entry lumi_message_text_behavior:Answer -o "$work/message-text.zib" \
    "$root/tests/lumi_message_text_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/message-text.zib")
[ "$result" = 42 ]
printf '%s\n' 'Lumi emphasis: visible bold ranges, Unicode, escapes, code and literal user messages passed'
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --module-path "$root/build/packages/kryon/src/ui" --define KRYON_HOSTED_UI \
    --entry lumi_reply_cache_behavior:Answer -o "$work/reply-cache.zib" \
    "$root/tests/lumi_reply_cache_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/reply-cache.zib")
[ "$result" = 42 ]
printf '%s\n' 'Lumi reply cache: edited text, Unicode emphasis and slot eviction passed'
"$root/build/ziran-toolchain/bin/ziran" bundle --root "$root/tests" \
    --entry lumi_chart_behavior:Answer -o "$work/chart.zib" \
    "$root/tests/lumi_chart_behavior.zi"
result=$(env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$root/build/ziran-toolchain/bin/ziran" run "$work/chart.zib")
[ "$result" = 42 ]
python3 "$root/tests/lumi_progress_sql_test.py"
printf '%s\n' 'Lumi charts: snapshots, validation, leap days, year boundaries and account-scoped history passed'
