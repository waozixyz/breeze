#!/usr/bin/env bash

set -e

AVD_NAME="${AVD_NAME:-inbe-test}"
EMULATOR_PORT="${ANDROID_EMULATOR_PORT:-}"
UNAME_S="$(uname -s)"
KERNEL_R="$(uname -r 2>/dev/null || true)"
SOFT_EMULATOR=0
if [ "$UNAME_S" = "FreeBSD" ] || echo "$KERNEL_R" | grep -qi FreeBSD || [ ! -e /dev/kvm ]; then
  SOFT_EMULATOR=1
fi

if [ "$UNAME_S" = "FreeBSD" ]; then
  mkdir -p "$HOME"
fi

# Check for Android SDK location
if [ -z "$ANDROID_SDK_ROOT" ] && [ -z "$ANDROID_HOME" ]; then
  echo "❌ Error: Neither ANDROID_SDK_ROOT nor ANDROID_HOME is set"
  exit 1
fi

# Set up writable SDK location
ORIGINAL_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
if [ "$UNAME_S" = "FreeBSD" ]; then
  PERSISTENT_SDK_ROOT="${ANDROID_SDK_WORK_ROOT:-/tmp/android-sdk}"
else
  PERSISTENT_SDK_ROOT="${ANDROID_SDK_WORK_ROOT:-$HOME/.android-sdk-writable}"
fi

mkdir -p "$PERSISTENT_SDK_ROOT"
for component in build-tools cmake cmdline-tools emulator licenses ndk platforms platform-tools tools; do
  if [ -n "$ORIGINAL_SDK_ROOT" ] && [ -e "$ORIGINAL_SDK_ROOT/$component" ] && [ ! -e "$PERSISTENT_SDK_ROOT/$component" ]; then
    if [ "$UNAME_S" = "FreeBSD" ]; then
      cp -R "$ORIGINAL_SDK_ROOT/$component" "$PERSISTENT_SDK_ROOT/$component"
      chmod -R u+w "$PERSISTENT_SDK_ROOT/$component" 2>/dev/null || true
    else
      ln -sf "$ORIGINAL_SDK_ROOT/$component" "$PERSISTENT_SDK_ROOT/$component"
    fi
  fi
done

NEED_CREATE_AVD=0
if [ ! -d "$PERSISTENT_SDK_ROOT" ] || [ ! -d "$PERSISTENT_SDK_ROOT/avd/$AVD_NAME.avd" ]; then
  NEED_CREATE_AVD=1
fi

if [ "$NEED_CREATE_AVD" -eq 0 ]; then
  export ANDROID_SDK_ROOT="$PERSISTENT_SDK_ROOT"
  export ANDROID_SDK_HOME="$PERSISTENT_SDK_ROOT"
  export ANDROID_AVD_HOME="$PERSISTENT_SDK_ROOT/avd"
else
  echo "ℹ️  AVD not found. Creating new Pixel 8 Pro AVD..."
  bash scripts/create-avd.sh "$AVD_NAME"

  # Re-export after creation
  export ANDROID_SDK_ROOT="$PERSISTENT_SDK_ROOT"
  export ANDROID_SDK_HOME="$PERSISTENT_SDK_ROOT"
  export ANDROID_AVD_HOME="$PERSISTENT_SDK_ROOT/avd"
fi

ADB_CMD="${ANDROID_SDK_ROOT}/platform-tools/adb"
if [ ! -x "$ADB_CMD" ]; then
  ADB_CMD="$(command -v adb)"
fi

if [ -n "$EMULATOR_PORT" ]; then
  EMULATOR_SERIAL="emulator-$EMULATOR_PORT"
  ADB_ARGS=(-s "$EMULATOR_SERIAL")
  PORT_ARGS=(-port "$EMULATOR_PORT")
else
  EMULATOR_SERIAL=""
  ADB_ARGS=(-e)
  PORT_ARGS=()
fi

if [ -n "${ANDROID_EMULATOR_AUDIO_BACKEND:-}" ]; then
  AUDIO_ARGS=(-audio "$ANDROID_EMULATOR_AUDIO_BACKEND")
elif [ "$SOFT_EMULATOR" -eq 1 ]; then
  AUDIO_ARGS=(-no-audio)
else
  AUDIO_ARGS=()
fi

if [ -n "${ANDROID_EMULATOR_RAM_MB:-}" ]; then
  MEMORY_ARGS=(-memory "$ANDROID_EMULATOR_RAM_MB")
  QEMU_MEMORY_ARGS=(-m "$ANDROID_EMULATOR_RAM_MB")
else
  MEMORY_ARGS=()
  QEMU_MEMORY_ARGS=()
fi

if [ "${ANDROID_EMULATOR_HEADLESS:-0}" = 1 ]; then
  WINDOW_ARGS=(-no-window)
else
  WINDOW_ARGS=()
fi

EMULATOR_CMD="${ANDROID_SDK_ROOT}/emulator/emulator"
if [ ! -x "$EMULATOR_CMD" ]; then
  EMULATOR_CMD="$(command -v emulator)"
fi

EMULATOR_DIR="$(cd "$(dirname "$EMULATOR_CMD")" && pwd)"
EMULATOR_LD_LIBRARY_PATH="${ANDROID_EMULATOR_LD_LIBRARY_PATH:-$EMULATOR_DIR/lib64:$EMULATOR_DIR/lib64/qt/lib}"

if [ "$UNAME_S" = "FreeBSD" ] && command -v brandelf >/dev/null 2>&1; then
  find "$EMULATOR_DIR" -type f -perm -111 -exec brandelf -t Linux {} + >/dev/null 2>&1 || true
fi

# Check if emulator is already running
if [ -n "$EMULATOR_SERIAL" ] && "$ADB_CMD" devices | grep -q "^$EMULATOR_SERIAL[[:space:]]*device"; then
  echo "✅ Emulator already running"
  "$ADB_CMD" devices
  exit 0
elif [ -z "$EMULATOR_SERIAL" ] && "$ADB_CMD" devices | grep -q '^emulator-[0-9][0-9]*[[:space:]]*device'; then
  echo "✅ Emulator already running"
  "$ADB_CMD" devices
  exit 0
fi

if [ "$SOFT_EMULATOR" -eq 1 ]; then
  LD_LIBRARY_PATH="$EMULATOR_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$EMULATOR_CMD" -version >/dev/null
elif LD_LIBRARY_PATH="$EMULATOR_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd "$EMULATOR_CMD" 2>/dev/null | grep -q "not found"; then
  echo "❌ Emulator runtime libraries are missing."
  echo "   Install the emulator runtime libraries or set ANDROID_EMULATOR_LD_LIBRARY_PATH."
  exit 1
fi

echo "🚀 Launching Pixel 8 Pro emulator ($AVD_NAME)..."

# Set environment for emulator
unset ANDROID_HOME
export ANDROID_SDK_ROOT="$ANDROID_SDK_ROOT"

if [ "$SOFT_EMULATOR" -eq 1 ]; then
  LD_LIBRARY_PATH="$EMULATOR_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$EMULATOR_CMD" @"$AVD_NAME" \
    -no-window \
    "${AUDIO_ARGS[@]}" \
    "${PORT_ARGS[@]}" \
    "${MEMORY_ARGS[@]}" \
    -gpu off \
    -no-accel \
    -no-snapshot-load \
    -no-boot-anim \
    -verbose > /tmp/emulator.log 2>&1 &
else
  LD_LIBRARY_PATH="$EMULATOR_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$EMULATOR_CMD" @"$AVD_NAME" \
    "${WINDOW_ARGS[@]}" \
    "${AUDIO_ARGS[@]}" \
    "${PORT_ARGS[@]}" \
    "${MEMORY_ARGS[@]}" \
    -gpu host \
    -skin 1440x2960 \
    -no-snapshot-load \
    -no-boot-anim \
    -verbose \
    -qemu "${QEMU_MEMORY_ARGS[@]}" -enable-kvm > /tmp/emulator.log 2>&1 &
fi

echo "⏳ Waiting for boot (this may take a while)..."
timeout_seconds=120
if [ "$SOFT_EMULATOR" -eq 1 ]; then
  timeout_seconds=600
fi
elapsed=0

timeout 20 "$ADB_CMD" "${ADB_ARGS[@]}" wait-for-device >/dev/null 2>&1 || true
while ! "$ADB_CMD" "${ADB_ARGS[@]}" shell getprop sys.boot_completed 2>/dev/null | grep -q "1"; do
  if [ $elapsed -ge $timeout_seconds ]; then
    echo "❌ Timeout waiting for boot. Check /tmp/emulator.log"
    exit 1
  fi

  sleep 5
  elapsed=$((elapsed + 5))

  if ! pgrep -f "emulator.*$AVD_NAME" > /dev/null; then
    echo "❌ Emulator died. Check /tmp/emulator.log"
    tail -20 /tmp/emulator.log
    exit 1
  fi

  # Show progress
  if [ $((elapsed % 15)) -eq 0 ]; then
    echo "   Still booting... (${elapsed}s)"
  fi
done

echo "✅ Pixel 8 Pro emulator ready!"

echo "🎯 Enabling punch-hole display cutout overlay if available..."
if "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay list 2>/dev/null | grep -q "com.android.internal.display.cutout.emulation.hole"; then
  "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay enable --user 0 com.android.internal.display.cutout.emulation.hole || true
elif "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay list 2>/dev/null | grep -q "com.android.internal.display.cutout.emulation.corner"; then
  "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay enable --user 0 com.android.internal.display.cutout.emulation.corner || true
elif "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay list 2>/dev/null | grep -q "com.android.internal.display.cutout.emulation.tall"; then
  "$ADB_CMD" "${ADB_ARGS[@]}" shell cmd overlay enable --user 0 com.android.internal.display.cutout.emulation.tall || true
else
  echo "   No display cutout emulation overlay found on this image"
fi

echo ""
echo "📱 Device info:"
"$ADB_CMD" "${ADB_ARGS[@]}" shell getprop ro.product.model
"$ADB_CMD" "${ADB_ARGS[@]}" shell getprop ro.build.version.release
"$ADB_CMD" "${ADB_ARGS[@]}" shell getprop ro.build.version.sdk
echo ""
echo "   Connect with: $ADB_CMD -e shell"
