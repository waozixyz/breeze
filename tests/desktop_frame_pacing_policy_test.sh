#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
app_host="$root/src/platform/app_host.zi"
frame_host="$root/src/platform/host_frame.zi"
window_host="$root/src/platform/host_window.zi"

# The app reports retained paint to the same Kryon host that presents and
# waits for desktop frames. The separate frame pacing test covers the app's
# FPS decisions for hosts that accept a target rate.
if ! grep -Fq 'HostFramePaintUnchanged(retained &&' "$app_host" ||
   ! grep -Fq 'Desktop.DesktopFrameUnchanged(unchanged)' "$window_host" ||
   ! grep -Fq 'Desktop.PauseDesktop()' "$frame_host"; then
    echo "desktop frame host must pace frames using the retained paint state"
    exit 1
fi

if ! grep -Fq 'HostSetFrameTarget(app.ui.frame_target_fps)' "$app_host" ||
   ! grep -Fq 'CanvasWindow.SetTargetFPS(fps)' "$frame_host" ||
   ! grep -Fq 'host_frame_target_fps = ifx fps > 0 then fps else 60' "$frame_host"; then
    echo "Android and web frame hosts must apply the app's target rate"
    exit 1
fi

echo "desktop frame pacing policy test passed"
