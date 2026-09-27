#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

OUT=${1:-build/dist/inbe-firefox-addons-source.zip}
case $OUT in
    /*) OUT_ABS=$OUT ;;
    *) OUT_ABS=$ROOT_DIR/$OUT ;;
esac
STAGE_ROOT=${TMPDIR:-/tmp}/inbe-firefox-addons-source-$$
STAGE_DIR=$STAGE_ROOT/inbe-firefox-addons-source

cleanup() {
    rm -rf "$STAGE_ROOT"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$STAGE_DIR" "$(dirname -- "$OUT_ABS")"

copy_path() {
    src=$1
    if [ -e "$src" ]; then
        mkdir -p "$STAGE_DIR/$(dirname -- "$src")"
        cp -R "$src" "$STAGE_DIR/$src"
    fi
}

for path in \
    .gitignore \
    ziran.toml \
    ziran.lock \
    .github \
    Makefile \
    README.md \
    manifest.json \
    assets \
    locales \
    packaging \
    scripts \
    site-icons \
    src \
    tests \
    unpackaged_assets \
    web-assets
 do
    copy_path "$path"
 done

# Dependencies are pinned in ziran.lock. Ship the resolved checkouts so the
# reviewed source builds without fetching, but not their build output.
[ -f build/packages/.complete ] || sh scripts/packages.sh --locked
mkdir -p "$STAGE_DIR/build"
cp -RL build/packages "$STAGE_DIR/build/packages"
find "$STAGE_DIR/build/packages" -depth -type d -name build -exec rm -rf {} +

rm -f "$OUT_ABS"
(
    cd "$STAGE_ROOT"
    zip -q -9 -r "$OUT_ABS" inbe-firefox-addons-source \
        -x '*/.git' \
           '*/.git/*' \
           '*/.claude' \
           '*/.claude/*' \
           '*/.codex' \
           '*/.codex/*' \
           '*/.ccache/*' \
           '*/.gradle/*' \
           '*/node_modules/*' \
           'inbe-firefox-addons-source/build/obj/*' \
           '*/vendor-builds/*' \
           '*/unpackaged_assets/audio/*' \
           '*/web-assets/dl/*' \
           '*/build/packages/sqlite/art/*' \
           '*/build/packages/sqlite/doc/*' \
           '*/build/packages/sqlite/mptest/*' \
           '*/build/packages/sqlite/test/*' \
           '*/build/packages/kryon/docs/site/*' \
           '*/build/packages/kryon/fonts/noto/*' \
           '*/build/packages/kryon/vendor/liboqs/docs/*' \
           '*/build/packages/kryon/vendor/liboqs/tests/*' \
           '*/build/packages/kryon/vendor/raylib/examples/*' \
           '*/build/packages/kryon/vendor/raylib/logo/*' \
           '*/build/packages/kryon/vendor/raylib/projects/*' \
           '*/tmp/*'
)

if [ ! -f "$OUT_ABS" ]; then
    printf 'ERROR: expected source zip not found: %s\n' "$OUT_ABS" >&2
    exit 1
fi

printf 'Firefox add-on source zip created: %s\n' "$OUT_ABS"
