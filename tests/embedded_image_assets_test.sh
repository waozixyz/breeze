#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EMBEDDED_C="$ROOT_DIR/build/obj/inbe_embedded_assets.c"

fail() {
  echo "FAIL $*" >&2
  exit 1
}

[[ -f "$EMBEDDED_C" ]] ||
  fail "embedded asset table missing; run make native or make build/obj/inbe_embedded_assets.c first"

if command -v rg >/dev/null 2>&1; then
  mapfile -t image_paths < <(
    rg -No '"(assets/)?(practices|easteregg|pet)/[^"]+\.(png|jpg|jpeg)"' \
      "$ROOT_DIR/src" "$ROOT_DIR/tests" \
      -g '!vendor/**' |
      sed -E 's/^.*"([^"]+)".*$/\1/' |
      sort -u
  )
else
  mapfile -t image_paths < <(
    find "$ROOT_DIR/src" "$ROOT_DIR/tests" -type f \
      \( -name '*.zi' -o -name '*.c' -o -name '*.h' -o -name '*.sh' \) -print0 |
      xargs -0 grep -Eho '"(assets/)?(practices|easteregg|pet)/[^"]+\.(png|jpg|jpeg)"' |
      sed -E 's/^"([^"]+)"$/\1/' |
      sort -u
  )
fi

[[ "${#image_paths[@]}" -gt 0 ]] ||
  fail "no app image path literals found"

for path in "${image_paths[@]}"; do
  embedded_path="$path"
  if [[ "$embedded_path" != assets/* ]]; then
    embedded_path="assets/$embedded_path"
  fi

  [[ -f "$ROOT_DIR/$embedded_path" ]] ||
    fail "image literal '$path' points at missing file '$embedded_path'"

  grep -Fq "{\"$embedded_path\"" "$EMBEDDED_C" ||
    fail "image literal '$path' is not embedded as '$embedded_path'"
done

for required in \
  assets/practices/whm/banner.png \
  assets/practices/whm/banner-light.png \
  assets/practices/whm/banner-dark.png \
  assets/practices/meditation/banner.png \
  assets/practices/meditation/banner-light.png \
  assets/practices/meditation/banner-dark.png \
  assets/practices/sunsalutation/banner.png \
  assets/practices/sunsalutation/banner-light.png \
  assets/practices/sunsalutation/banner-dark.png \
  assets/practices/patterns/banner.png \
  assets/practices/patterns/banner-light.png \
  assets/practices/patterns/banner-dark.png; do
  [[ -f "$ROOT_DIR/$required" ]] ||
    fail "required practice banner missing: $required"
  grep -Fq "{\"$required\"" "$EMBEDDED_C" ||
    fail "required practice banner is not embedded: $required"
done

[[ -f "$ROOT_DIR/vendor/kryon/icons/ui.png" ]] ||
  fail "Kryon UI icon atlas missing"
grep -Fq '{"icons/ui.png"' "$EMBEDDED_C" ||
  fail "Kryon UI icon atlas is not embedded as icons/ui.png"
[[ -f "$ROOT_DIR/vendor/kryon/icons/pfp.png" ]] ||
  fail "profile picture icon atlas missing"
grep -Fq '{"icons/pfp.png"' "$EMBEDDED_C" ||
  fail "profile picture icon atlas is not embedded as icons/pfp.png"

echo "PASS embedded image asset contract"
