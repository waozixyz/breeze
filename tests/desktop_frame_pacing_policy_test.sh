#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
policy="$root/src/app/app_frame_pacing.zi"
main_host="$root/src/platform/app_host.zi"

if grep -Eq 'idle_fps[[:space:]]*=[[:space:]]*5([^0-9]|$)' "$policy"; then
    echo "desktop frame pacing must not idle at 5 FPS"
    exit 1
fi

if ! grep -Eq 'frame_pacing_state\.idle_fps[[:space:]]*=[[:space:]]*30' "$policy" ||
   ! grep -Eq 'frame_pacing_state\.active_fps[[:space:]]*=[[:space:]]*60' "$policy"; then
    echo "desktop frame pacing should idle at 30 FPS and stay active at 60 FPS"
    exit 1
fi

if ! grep -Fq 'SetTargetFPS(app.ui.frame_target_fps)' "$main_host"; then
    echo "frame host must apply the frame pacing decision"
    exit 1
fi

echo "desktop frame pacing policy test passed"
