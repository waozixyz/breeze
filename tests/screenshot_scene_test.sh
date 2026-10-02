#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/generate-screenshots.sh"

fail() {
  echo "FAIL $*" >&2
  exit 1
}

grep -q -- '--screenshot-ui-scale "$scale"' "$SCRIPT" ||
  fail "screenshots must render each device bucket at its own UI scale"
grep -q '"phone:1080:1920:25:phoneScreenshots"' "$SCRIPT" ||
  fail "phone screenshots must use the phone layout at 2.5x"

mapfile -t scenes < <(
  awk '
    /^SCENES=\(/ { in_scenes = 1; next }
    in_scenes && /^\)/ { exit }
    in_scenes {
      gsub(/^[[:space:]]*"/, "")
      gsub(/"[[:space:]]*$/, "")
      if($0 != "") print
    }
  ' "$SCRIPT"
)

[[ "${#scenes[@]}" -eq 8 ]] ||
  fail "expected 8 Play screenshot scenes, got ${#scenes[@]}"

for forbidden in 'rest_break' '08-cobalt-dark-practice'; do
  if printf '%s\n' "${scenes[@]}" | grep -q "$forbidden"; then
    fail "forbidden screenshot scene is still present: $forbidden"
  fi
done

IFS=: read -r scene slug theme dark expected <<<"${scenes[1]}"
[[ "$scene" = "sun_salutation_home" ]] ||
  fail "slot 2 must show the Sun Salutation practice card"
IFS=: read -r scene slug theme dark expected <<<"${scenes[4]}"
[[ "$scene" = "promo_habits" ]] ||
  fail "slot 5 must use the showcase habits, not test fixtures"

for i in 0 1 2 3 4 5 6; do
  IFS=: read -r scene slug theme dark expected <<<"${scenes[$i]}"
  [[ "$theme" = "-1" ]] ||
    fail "$slug should keep the current/system theme, got theme=$theme"
  [[ "$dark" = "0" ]] ||
    fail "$slug should not force dark mode, got dark=$dark"
done

IFS=: read -r scene slug theme dark expected <<<"${scenes[6]}"
[[ "$scene" = "practice_manual_whm" && "$slug" = "07-wim-hof-how-to" ]] ||
  fail "slot 7 must be Wim Hof Method How To"

IFS=: read -r scene slug theme dark expected <<<"${scenes[7]}"
[[ "$scene" = "cobalt_dark" && "$slug" = "08-cobalt-dark-pattern-breathing" ]] ||
  fail "slot 8 must be Cobalt Dark Pattern Breathing"
[[ "$theme" = "11" && "$dark" = "1" ]] ||
  fail "Cobalt Dark must explicitly force theme=11 dark=1"

echo "PASS screenshot scene contract"
