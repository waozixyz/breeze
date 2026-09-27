#!/usr/bin/env bash
set -euo pipefail

root="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
state="$root/src/app/app_route_state.zi"
app_h="$root/src/app/app_types.zi"
app_c="$root/src/app/application.zi"

[[ -f "$state" && -f "$app_h" && -f "$app_c" ]] || {
  echo "FAIL route navigation test: missing app route files" >&2
  exit 1
}

if grep -R "pending_route" "$state" "$app_h" >/dev/null; then
  echo "FAIL route navigation test: app routes must not queue pending_route" >&2
  exit 1
fi

if grep -n "InvalidateTree" "$state" >/dev/null; then
  echo "FAIL route navigation test: route switching must not invalidate full UI tree" >&2
  exit 1
fi

request_body="$(
  awk '
    /^app_request_route ::/ { in_body = 1 }
    in_body { print }
    in_body && /^}/ { exit }
  ' "$state"
)"

switch_line="$(printf '%s\n' "$request_body" | grep -n "app_switch_route(app, route)" | cut -d: -f1 || true)"
router_line="$(printf '%s\n' "$request_body" | grep -n "app->route_router = RouterNavigate(app->route_router, route.screen)" | cut -d: -f1 || true)"

if [[ -z "$switch_line" || -z "$router_line" ]]; then
  echo "FAIL route navigation test: app_request_route must switch then notify Router" >&2
  exit 1
fi

if (( switch_line >= router_line )); then
  echo "FAIL route navigation test: app_switch_route must run before RouterNavigate" >&2
  exit 1
fi

early_nav_line="$(grep -n "app_draw_bottom_nav(app)" "$app_c" | head -n 1 | cut -d: -f1 || true)"
final_nav_line="$(grep -n "app_draw_bottom_nav(app)" "$app_c" | tail -n 1 | cut -d: -f1 || true)"
screen_draw_line="$(grep -n "settings_screen_draw(app)" "$app_c" | head -n 1 | cut -d: -f1 || true)"

if [[ -z "$early_nav_line" || -z "$final_nav_line" || -z "$screen_draw_line" ]]; then
  echo "FAIL route navigation test: missing nav or screen draw phases" >&2
  exit 1
fi

if (( early_nav_line >= screen_draw_line )); then
  echo "FAIL route navigation test: desktop rail must evaluate before screen content draw" >&2
  exit 1
fi

if (( final_nav_line <= screen_draw_line )); then
  echo "FAIL route navigation test: nav must paint after screen content draw" >&2
  exit 1
fi

echo "route navigation test passed"
