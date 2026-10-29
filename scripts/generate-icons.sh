#!/usr/bin/env bash
set -euo pipefail

# Icon Generation Script for Inner Breeze
# Generates transparent artwork plus pale blue adaptive/maskable backgrounds.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ICON_BACKGROUND="#E6F1FA"
AIR_SOURCE="$PROJECT_ROOT/assets/app/source-icon-air.png"
SOURCE_IMAGE="${1:-$PROJECT_ROOT/assets/app/source-icon.png}"

if [[ "$SOURCE_IMAGE" != /* ]]; then
    SOURCE_IMAGE="$PROJECT_ROOT/$SOURCE_IMAGE"
fi

echo "🔨 Inner Breeze Icon Generator"
echo "=============================="
echo

# Validate ImageMagick installation
if ! command -v magick &> /dev/null; then
    echo "❌ Error: ImageMagick v7 not found. Please install ImageMagick:"
    echo "   Ubuntu/Debian: sudo apt-get install imagemagick"
    echo "   macOS: brew install imagemagick"
    echo "   Fedora: sudo dnf install imagemagick"
    exit 1
fi

# Validate source image
if [ ! -f "$SOURCE_IMAGE" ]; then
    echo "❌ Error: Source image not found: $SOURCE_IMAGE"
    exit 1
fi

echo "✅ Using source image: $SOURCE_IMAGE"
echo "🎨 Maskable/adaptive background color: $ICON_BACKGROUND (Pale Blue)"
echo

# Create output directories
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/drawable"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-mdpi"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-hdpi"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-xhdpi"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-xxhdpi"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-xxxhdpi"
mkdir -p "$PROJECT_ROOT/droid/app/src/main/res/mipmap-anydpi-v26"
mkdir -p "$PROJECT_ROOT/windows"
mkdir -p "$PROJECT_ROOT/assets/app"
mkdir -p "$PROJECT_ROOT/packaging/linux/appimage"
mkdir -p "$PROJECT_ROOT/packaging/snap/snap/gui"
mkdir -p "$PROJECT_ROOT/packaging/chrome-web-store/icons"
mkdir -p "$PROJECT_ROOT/web-assets/icons"
mkdir -p "$PROJECT_ROOT/site-icons"
mkdir -p "$PROJECT_ROOT/fastlane/metadata/android/en-US/images"

# Normalize from visible artwork rather than the source canvas. Thresholding is
# used only to find bounds; the artwork keeps its original translucent edges.
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
normalize_source() {
    local source=$1 output=$2 bounds
    bounds=$(magick "$source" -alpha extract -threshold 50% -format '%@' info:)
    magick "$source" -crop "$bounds" +repage "$output"
}
normalize_source "$SOURCE_IMAGE" "$WORK_DIR/sky.png"
normalize_source "$AIR_SOURCE" "$WORK_DIR/air.png"
ARTWORK="$WORK_DIR/sky.png"

generate_transparent() {
    local size=$1 output=$2
    local logo_size=${3:-$((size * 9 / 10))}
    magick "$ARTWORK" -filter Lanczos -resize "${logo_size}x${logo_size}" \
        -background none -gravity center -extent "${size}x${size}" \
        -strip +set date:create +set date:modify +set date:timestamp \
        -define png:exclude-chunk=time "$output"
}

generate_maskable() {
    local size=$1 output=$2
    local logo_size=$((size * 4 / 5))
    generate_transparent "$size" "$WORK_DIR/maskable.png" "$logo_size"
    magick "$WORK_DIR/maskable.png" -background "$ICON_BACKGROUND" \
        -alpha remove -alpha off -strip \
        -define png:exclude-chunk=time "$output"
}

write_android_background() {
    cat > "$PROJECT_ROOT/droid/app/src/main/res/drawable/ic_launcher_background.xml" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="$ICON_BACKGROUND" />
</shape>
EOF
}

echo "📱 Generating Android icons..."

# Both choices have legacy assets plus adaptive layers with a 60dp drawing
# inside the 108dp layer (240px in 432px). The launcher crops to its own mask.
write_android_background
for variant in sky air; do
    ARTWORK="$WORK_DIR/$variant.png"
    name=ic_launcher
    preview=sky-cradle
    if [[ "$variant" == air ]]; then
        name=ic_launcher_air
        preview=ink-and-air
    fi
    for density_size in mdpi:48 hdpi:72 xhdpi:96 xxhdpi:144 xxxhdpi:192; do
        density=${density_size%:*}
        size=${density_size#*:}
        generate_transparent "$size" "$PROJECT_ROOT/droid/app/src/main/res/mipmap-$density/$name.png"
    done
    generate_transparent 432 "$PROJECT_ROOT/droid/app/src/main/res/drawable/${name}_foreground.png" 240
    # Round icons are the same pictures: res/values/launcher_round.xml names
    # them as aliases of these, so the APK carries one copy.
    cat > "$PROJECT_ROOT/droid/app/src/main/res/mipmap-anydpi-v26/${name}.xml" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/${name}_foreground" />
</adaptive-icon>
EOF
    # Settings previews contain only the person and cloud.
    generate_transparent 192 "$PROJECT_ROOT/assets/app/icon-$preview.png"
done
ARTWORK="$WORK_DIR/sky.png"

echo "✅ Android icons generated"

echo "🪟 Generating Windows icon..."

# ICO contains separate transparent sizes with the same centered artwork.
for size in 256 192 48 32 16; do
    generate_transparent "$size" "$WORK_DIR/windows-$size.png"
done
magick "$WORK_DIR/windows-256.png" "$WORK_DIR/windows-192.png" \
    "$WORK_DIR/windows-48.png" "$WORK_DIR/windows-32.png" "$WORK_DIR/windows-16.png" \
    "$PROJECT_ROOT/windows/inbe.ico"

echo "✅ Windows icon generated"

echo "🖥️ Generating app runtime icon..."

# Runtime desktop window icon embedded into the native app binary.
generate_transparent 64 "$PROJECT_ROOT/assets/app/icon.png"

echo "✅ App runtime icon generated"

echo "🐧 Generating Linux AppImage icon..."

# AppImage desktop icons are PNGs and support transparency.
generate_transparent 256 "$PROJECT_ROOT/packaging/linux/appimage/inbe.png"
generate_transparent 256 "$PROJECT_ROOT/packaging/snap/snap/gui/inbe.png"

echo "✅ Linux AppImage icon generated"

echo "🏪 Generating Fastlane store icon..."

# F-Droid/Fastlane store listing icon expects a 512x512 PNG.
generate_maskable 512 "$PROJECT_ROOT/fastlane/metadata/android/en-US/images/icon.png"

echo "✅ Fastlane store icon generated"

echo "🌐 Generating Chrome Web Store icons..."

# Chrome Web Store icons (transparent, various sizes)
generate_transparent 16 "$PROJECT_ROOT/packaging/chrome-web-store/icons/icon-16.png"
generate_transparent 32 "$PROJECT_ROOT/packaging/chrome-web-store/icons/icon-32.png"
generate_transparent 48 "$PROJECT_ROOT/packaging/chrome-web-store/icons/icon-48.png"
generate_transparent 128 "$PROJECT_ROOT/packaging/chrome-web-store/icons/icon-128.png"

echo "✅ Chrome Web Store icons generated"

echo "🌐 Generating Web/PWA icons..."

# Web/PWA icons (for manifest.json and web_shell.html)
generate_transparent 192 "$PROJECT_ROOT/site-icons/icon-192x192.png"
generate_transparent 512 "$PROJECT_ROOT/site-icons/icon-512x512.png"
generate_maskable 192 "$PROJECT_ROOT/site-icons/maskable-192x192.png"
generate_maskable 512 "$PROJECT_ROOT/site-icons/maskable-512x512.png"
generate_transparent 180 "$PROJECT_ROOT/site-icons/apple-touch-icon.png"

# Favicon PNG supports transparency.
generate_transparent 32 "$PROJECT_ROOT/site-icons/favicon-32x32.png"
generate_transparent 64 "$PROJECT_ROOT/web-assets/icons/inbe.png"

echo "✅ Web/PWA icons generated"

echo
echo "🎉 Icon generation complete!"
echo
echo "Generated icons:"
echo "  📱 Android: mipmap PNGs + adaptive drawable foreground/background"
echo "  🪟 Windows: windows/inbe.ico (256, 192, 48, 32, 16 resolutions)"
echo "  🖥️ App:     assets/app/icon.png (64x64 transparent runtime icon)"
echo "  🐧 Linux:   packaging/linux/appimage/inbe.png + snap/gui/inbe.png (256x256)"
echo "  🏪 Store:   fastlane/metadata/android/en-US/images/icon.png (512x512)"
echo "  🌐 Chrome:  packaging/chrome-web-store/icons/ (16, 32, 48, 128)"
echo "  🌐 Web:    site-icons/ (transparent + maskable PWA icons)"
echo "            web-assets/icons/inbe.png (64x64)"
echo
echo "💡 Tip: Review generated icons before committing to version control."
