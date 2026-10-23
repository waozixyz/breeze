#!/bin/sh
# End-to-end desktop window tests for Inner Breeze.
#
# Drives the real binary on a private Xvfb display with a window manager,
# using xdotool, exactly like a user: clicks the title-bar close button and
# answers the close prompt.
#
# Covered cases (the "closing windows in different inbe modes" matrix):
#   1. startup        main window maps on a fresh profile
#   2. close-keep     no tray icon -> close exits, even with Keep running set
#   3. close-ask      no tray icon -> close exits without a hidden process
#   4. startup-hidden no tray icon -> app stays visible; minimize exits
#
# Requirements: xvfb-run/Xvfb, xfwm4, xdotool, xwininfo (x11-utils), sqlite3.
# The user's session and data are never touched. Break HUD dragging needs a
# separate tray-ready harness; this no-tray close-window test intentionally does
# not assert HUD behavior.
#
# Usage: scripts/test-desktop-windows.sh [path-to-binary]

set -u

BIN=${1:-./build/bin/linux/breeze-linux-x86_64}
GEOMETRY="1280x800x24"

[ -x "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 1; }
for tool in xvfb-run Xvfb xfwm4 xdotool xwininfo sqlite3; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "FAIL: missing tool: $tool (install xvfb, xfwm4, xdotool, x11-utils, sqlite3)"
        exit 1
    }
done

if [ -z "${INBE_DESKTOP_WINDOW_TEST_XVFB:-}" ]; then
    exec env -u DISPLAY -u WAYLAND_DISPLAY -u SESSION_MANAGER \
        -u DBUS_SESSION_BUS_ADDRESS xvfb-run -a -s "-noreset -screen 0 $GEOMETRY" \
        env -u WAYLAND_DISPLAY INBE_DESKTOP_WINDOW_TEST_XVFB=1 "$0" "$@"
fi

DISPLAY_TEST=${DISPLAY:?xvfb-run did not set DISPLAY}
WORK=$(mktemp -d /tmp/inbe-winmode.XXXXXX)
PASS=0
FAIL=0
APP_PID=""

cleanup() {
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
    if [ -n "${XVFB_PID:-}" ]; then kill "$XVFB_PID" 2>/dev/null; fi
    if [ -n "${WM_PID:-}" ]; then kill "$WM_PID" 2>/dev/null; fi
    sleep 0.5
    rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

say() { printf '%s\n' "$*"; }
ok()  { PASS=$((PASS + 1)); say "PASS: $1"; }
bad() { FAIL=$((FAIL + 1)); say "FAIL: $1"; }

XD() { env -u WAYLAND_DISPLAY DISPLAY="$DISPLAY_TEST" xdotool "$@" 2>/dev/null; }
XW() { env -u WAYLAND_DISPLAY DISPLAY="$DISPLAY_TEST" xwininfo "$@" 2>/dev/null; }

capture_visual() { # $1 = capture name
    [ -n "${INBE_VISUAL_OUTPUT_DIR:-}" ] || return 0
    mkdir -p "$INBE_VISUAL_OUTPUT_DIR"
    env -u WAYLAND_DISPLAY DISPLAY="$DISPLAY_TEST" \
        xwd -root -silent -out "$WORK/$1.xwd"
    convert "$WORK/$1.xwd" "$INBE_VISUAL_OUTPUT_DIR/$1.png"
}

# Main (client) window id: named, wider than 500px.
main_window() {
    for w in $(XD search --name "Inner Breeze"); do
        width=$(XD getwindowgeometry --shell "$w" | grep '^WIDTH' | cut -d= -f2)
        [ "${width:-0}" -gt 500 ] && { echo "$w"; return; }
    done
}

# Title-bar close button position, derived from the WM frame geometry.
close_button() {
    frame=$(XW -root -children | grep -E "904x754\+[0-9]+\+" |
            grep -oE '0x[0-9a-f]+' | head -1)
    [ -n "$frame" ] || return 1
    fx=$(XW -id "$frame" | grep 'Absolute upper-left X' | grep -oE '[0-9-]+$')
    fy=$(XW -id "$frame" | grep 'Absolute upper-left Y' | grep -oE '[0-9-]+$')
    fw=$(XW -id "$frame" | grep '^  Width' | grep -oE '[0-9]+$')
    [ -n "$fw" ] || return 1
    echo "$((fx + fw - 24)) $((fy + 13))"
}

launch_app() { # $1 = root dir, $2 = log name
    [ -n "$APP_PID" ] && { kill "$APP_PID" 2>/dev/null; sleep 1; }
    rm -f "$WORK/$2"
    env -u WAYLAND_DISPLAY DISPLAY="$DISPLAY_TEST" APP_DATA_ROOT="$1" APP_NO_TRAY=1 \
        setsid "$BIN" >"$WORK/$2" 2>&1 &
    APP_PID=$!
    sleep 8
}

fresh_root() { # $1 = root; prepares an empty data root
    rm -rf "$1"
    mkdir -p "$1"
}

set_setting() { # $1 = root, $2 = key, $3 = value
    sqlite3 "$1/inbe.db" \
        "insert into settings(user_id,key,value,updated_at) select id,'$2','$3',strftime('%s','now') from users limit 1 on conflict(user_id,key) do update set value=excluded.value, updated_at=excluded.updated_at"
}

# --- environment -----------------------------------------------------------
env -u WAYLAND_DISPLAY DISPLAY="$DISPLAY_TEST" setsid xfwm4 >/dev/null 2>&1 &
WM_PID=$!
sleep 1.5

# Fresh profile template: run once with breaks enabled so the DB exists.
ROOT0="$WORK/r0"
fresh_root "$ROOT0"
launch_app "$ROOT0" log0
kill "$APP_PID" 2>/dev/null; APP_PID=""; sleep 1
# The profile's tables may still live in the WAL; checkpoint before copying.
sqlite3 "$ROOT0/inbe.db" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null 2>&1
rm -f "$ROOT0/inbe.db-wal" "$ROOT0/inbe.db-shm"
cp "$ROOT0/inbe.db" "$WORK/template.db"
# --- 1. startup maps the window -------------------------------------------
ROOT1="$WORK/r-keep"
fresh_root "$ROOT1"; cp "$WORK/template.db" "$ROOT1/inbe.db"
mkdir -p "$ROOT1/runtime-assets"
set_setting "$ROOT1" desktop_close_action 1   # KEEP_RUNNING
launch_app "$ROOT1" log-keep
MW=$(main_window)
if [ -n "$MW" ] && XW -id "$MW" | grep -q IsViewable; then
    ok "startup: main window maps"
    capture_visual "01-window-visible"
else
    bad "startup: main window does not map"
fi

# --- 2. close = keep running, but no indicator -> exits --------------------
if CB=$(close_button); then
    XD mousemove ${CB% *} ${CB#* }
    XD click 1
    sleep 2.5
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        ok "close-keep: no indicator, so app exits"
        capture_visual "02-after-close"
        APP_PID=""
    else
        bad "close-keep: app stayed alive without an indicator"
    fi
else
    bad "close-keep: no WM frame found"
fi

# --- 3. close = ask, but no indicator -> exits ------------------------------
ROOT2="$WORK/r-ask"
fresh_root "$ROOT2"; cp "$WORK/template.db" "$ROOT2/inbe.db"
mkdir -p "$ROOT2/runtime-assets"
set_setting "$ROOT2" desktop_close_action 0   # ASK
launch_app "$ROOT2" log-ask
if CB=$(close_button); then
    XD mousemove ${CB% *} ${CB#* }
    XD click 1
    sleep 2.5
    if kill -0 "$APP_PID" 2>/dev/null; then
        bad "close-ask: app stayed alive without an indicator"
    else
        ok "close-ask: no indicator, so app exits"
        APP_PID=""
    fi
else
    bad "close-ask: no WM frame found"
fi

# --- 4. startup hidden without a tray -> visible, then minimize exits -----
ROOT3="$WORK/r-start-hidden"
fresh_root "$ROOT3"; cp "$WORK/template.db" "$ROOT3/inbe.db"
mkdir -p "$ROOT3/runtime-assets"
set_setting "$ROOT3" desktop_startup_mode 1   # STARTUP_HIDDEN
launch_app "$ROOT3" log-start-hidden
MW=$(main_window)
if [ -n "$MW" ] && XW -id "$MW" | grep -q IsViewable; then
    ok "startup-hidden: no indicator, so window stays visible"
    capture_visual "03-start-hidden-without-indicator"
    XD windowminimize "$MW"
    sleep 2.5
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        ok "minimize: no indicator, so app exits"
        APP_PID=""
    else
        bad "minimize: app stayed alive without an indicator"
    fi
else
    bad "startup-hidden: window did not remain visible"
fi

# Break HUD dragging used to live here, but this harness deliberately runs with
# APP_NO_TRAY=1 so close-window behavior can be tested without a desktop tray.
# HUD behavior requires a separate tray-ready harness.

say ""
say "desktop window-mode tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
