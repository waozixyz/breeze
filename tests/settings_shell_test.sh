#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
screen="$root/src/screens/settings/settings_screen.zi"

for symbol in \
    "settings_screen_normalize" \
    "settings_screen_prepare" \
    "settings_desktop_layout" \
    "settings_desktop_draw_nav" \
    "settings_desktop_draw_panel"; do
    if ! grep -Fq "$symbol" "$screen"; then
        echo "settings shell is missing $symbol"
        exit 1
    fi
done

if grep -Fq "IsMouseButtonReleased" "$screen"; then
    echo "settings screen shell must not handle raw pointer release"
    exit 1
fi

if grep -Fq "save_settings(app)" "$screen"; then
    echo "settings screen shell must leave persistence to app_flush_deferred_settings or leaf controls"
    exit 1
fi

echo "settings shell test passed"
