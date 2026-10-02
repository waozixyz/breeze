#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNAME_S="$(uname -s)"
UNAME_M="$(uname -m)"
case "$UNAME_S" in
  FreeBSD) PLATFORM="freebsd" ;;
  Linux) PLATFORM="linux" ;;
  *) PLATFORM="$(printf '%s' "$UNAME_S" | tr '[:upper:]' '[:lower:]')" ;;
esac
case "$UNAME_M" in
  amd64) ARCH="x86_64" ;;
  *) ARCH="$UNAME_M" ;;
esac
BIN="${1:-"$ROOT_DIR/build/bin/$PLATFORM/inbe-$PLATFORM-$ARCH"}"
OUT_DIR="${SCREENSHOT_OUT_DIR:-"$ROOT_DIR/build/screenshots"}"
DATA_BASE="$OUT_DIR/screenshot-data"
FASTLANE_IMAGES_DIR="${SCREENSHOT_FASTLANE_IMAGES_DIR:-"$ROOT_DIR/fastlane/metadata/android/en-US/images"}"
FASTLANE_SYNC="${SCREENSHOT_FASTLANE_SYNC:-1}"
FASTLANE_FORMAT="${SCREENSHOT_FASTLANE_FORMAT:-png}"
FASTLANE_JPEG_QUALITY="${SCREENSHOT_FASTLANE_JPEG_QUALITY:-92}"
ANALYSIS_FILE="$OUT_DIR/screenshot-analysis.tsv"

SCENES=(
  "home:01-practice-home:-1:0:Wim Hof Breathing practice card"
  "sun_salutation_home:02-sun-salutation-home:-1:0:Sun Salutation practice card"
  "sun_salutation_pose:03-sun-salutation-pose:-1:0:Sun Salutation Upward salute pose"
  "meditation_home:04-meditation-home:-1:0:Meditation practice card"
  "promo_habits:05-habits-overview:-1:0:Habits overview"
  "habits_stats:06-habit-statistics:-1:0:Habit statistics"
  "practice_manual_whm:07-wim-hof-how-to:-1:0:Wim Hof Method how to"
  "cobalt_dark:08-cobalt-dark-pattern-breathing:11:1:Cobalt dark Pattern Breathing"
)
# name:width:height:ui scale in tenths:Fastlane folder. The scale gives each
# device its real layout: a 432x768 phone and 1280x720 tablets.
BUCKETS=(
  "phone:1080:1920:25:phoneScreenshots"
  "tablet-7:1920:1080:15:sevenInchScreenshots"
  "tablet-10:2560:1440:20:tenInchScreenshots"
  "chromebook:2560:1440:20:"
)

if [[ ! -x "$BIN" ]]; then
  echo "Screenshot binary is missing or not executable: $BIN" >&2
  echo "Run: make native" >&2
  exit 1
fi
if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "xvfb-run is required so screenshots are not clamped by your monitor size." >&2
  echo "Install xvfb-run and ensure it is on PATH." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR/phone" "$OUT_DIR/tablet-7" "$OUT_DIR/tablet-10" \
       "$OUT_DIR/chromebook" "$DATA_BASE"
mkdir -p "$DATA_BASE"
printf 'bucket\tfastlane_dir\torder\tscene\tfile\tfastlane_file\twidth\theight\tscale\ttheme\tdark\texpected\n' > "$ANALYSIS_FILE"

if [[ "$FASTLANE_SYNC" = "1" ]]; then
  mkdir -p "$FASTLANE_IMAGES_DIR"
  for bucket in "${BUCKETS[@]}"; do
    IFS=: read -r _bucket_name _width _height _scale fastlane_subdir <<<"$bucket"
    if [[ -n "$fastlane_subdir" ]]; then
      rm -rf "$FASTLANE_IMAGES_DIR/$fastlane_subdir"
      mkdir -p "$FASTLANE_IMAGES_DIR/$fastlane_subdir"
    fi
  done
fi

run_app() {
  local width="$1"
  local height="$2"
  local data_root="$3"
  local scene="$4"
  local output="$5"
  local theme="$6"
  local dark="$7"
  local scale="$8"

  set +e
  env -u DISPLAY -u WAYLAND_DISPLAY -u SESSION_MANAGER \
    -u DBUS_SESSION_BUS_ADDRESS INBE_DATA_ROOT="$data_root" \
    xvfb-run -a -s "-screen 0 ${width}x${height}x24" \
    env -u WAYLAND_DISPLAY -u SESSION_MANAGER -u DBUS_SESSION_BUS_ADDRESS \
    SDL_VIDEODRIVER=x11 "$BIN" \
    --screenshot "$output" \
    --screenshot-scene "$scene" \
    --screenshot-width "$width" \
    --screenshot-height "$height" \
    --screenshot-theme "$theme" \
    --screenshot-dark "$dark" \
    --screenshot-ui-scale "$scale"
  app_status=$?
  set -e
  if [[ "$app_status" -ne 0 && ! -s "$output" ]]; then
    echo "Screenshot app failed for scene '$scene' with status $app_status" >&2
    exit "$app_status"
  fi
}

sync_fastlane_screenshot() {
  local input="$1"
  local output="$2"

  case "$FASTLANE_FORMAT" in
    jpg|jpeg)
      if command -v magick >/dev/null 2>&1; then
        magick "$input" -strip -interlace Plane -quality "$FASTLANE_JPEG_QUALITY" "$output"
      elif command -v convert >/dev/null 2>&1; then
        convert "$input" -strip -interlace Plane -quality "$FASTLANE_JPEG_QUALITY" "$output"
      else
        echo "ImageMagick is required for JPEG Fastlane exports; falling back to PNG copy." >&2
        cp "$input" "${output%.*}.png"
      fi
      ;;
    png)
      if command -v magick >/dev/null 2>&1; then
        magick "$input" -strip -define png:compression-level=9 "$output"
      elif command -v convert >/dev/null 2>&1; then
        convert "$input" -strip -define png:compression-level=9 "$output"
      else
        cp "$input" "$output"
      fi
      ;;
    *)
      echo "Unsupported SCREENSHOT_FASTLANE_FORMAT: $FASTLANE_FORMAT" >&2
      exit 1
      ;;
  esac
}

count=0
for bucket in "${BUCKETS[@]}"; do
  IFS=: read -r bucket_name width height scale fastlane_subdir <<<"$bucket"
  bucket_dir="$OUT_DIR/$bucket_name"
  mkdir -p "$bucket_dir"

  for scene_def in "${SCENES[@]}"; do
    IFS=: read -r scene slug theme dark expected <<<"$scene_def"
    output="$bucket_dir/${slug}-${width}x${height}.png"
    data_root="$DATA_BASE/${bucket_name}-${scene}"
    mkdir -p "$data_root"
    echo "Generating $bucket_name/$slug ${width}x${height} [$expected]"
    run_app "$width" "$height" "$data_root" "$scene" "$output" "$theme" "$dark" "$scale"
    if [[ ! -s "$output" ]]; then
      echo "Screenshot was not created: $output" >&2
      exit 1
    fi
    actual_size="$(file "$output")"
    if [[ "$actual_size" != *"${width} x ${height}"* && "$actual_size" != *"${width}x${height}"* ]]; then
      echo "Screenshot has wrong dimensions: $output" >&2
      echo "Expected ${width}x${height}; got: $actual_size" >&2
      exit 1
    fi
    bytes="$(stat -c %s "$output" 2>/dev/null || wc -c <"$output")"
    if [[ "$bytes" -gt 8388608 ]]; then
      echo "Warning: $output is larger than 8 MB" >&2
    fi
    fastlane_file=""
    if [[ "$FASTLANE_SYNC" = "1" && -n "$fastlane_subdir" ]]; then
      fastlane_ext="$FASTLANE_FORMAT"
      [[ "$fastlane_ext" = "jpeg" ]] && fastlane_ext="jpg"
      fastlane_file="$FASTLANE_IMAGES_DIR/$fastlane_subdir/${slug}.${fastlane_ext}"
      sync_fastlane_screenshot "$output" "$fastlane_file"
      fastlane_bytes="$(stat -c %s "$fastlane_file" 2>/dev/null || wc -c <"$fastlane_file")"
      if [[ "$fastlane_bytes" -gt 8388608 ]]; then
        echo "Warning: $fastlane_file is larger than 8 MB" >&2
      fi
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$bucket_name" "$fastlane_subdir" "${slug%%-*}" "$scene" "$output" "$fastlane_file" \
      "$width" "$height" "$scale" "$theme" "$dark" "$expected" \
      >> "$ANALYSIS_FILE"
    count=$((count + 1))
  done
done

echo "Wrote $count screenshots to $OUT_DIR"
if [[ "$FASTLANE_SYNC" = "1" ]]; then
  echo "Synced Play/F-Droid screenshots to $FASTLANE_IMAGES_DIR"
fi
echo "Wrote screenshot analysis to $ANALYSIS_FILE"
