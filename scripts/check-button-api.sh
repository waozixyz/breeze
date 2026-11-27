#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if rg -n '\b(StyledButton|TextButton|RenderTextButton|IconButton|PaddedIconBtn|IconBtn|OverlayButton|InvisibleButton|app_sidebar_clean_button|practice_home_action_button|practice_home_quiet_action_button|habit_session_keyboard_key|draw_duration_button|draw_audio_preview_button)\s*\(' src apps --glob '*.zi' --glob '*.ts' --glob '*.tsx' --glob '*.c' --glob '*.h'; then
    echo 'Use Kryon Button JSX with native props for authored UI; use standard Checkbox/Toggle for their own controls.' >&2
    exit 1
fi
if rg -n --pcre2 '(?<![\w.])(Button|Toggle|Checkbox)\s*\(|(?<![\w.])(Button|Toggle|Checkbox)Props\b' src apps --glob '*.zi' --glob '*.ts' --glob '*.tsx'; then
    echo 'Use Kryon TSX components with native widget props.' >&2
    exit 1
fi
if rg -n -U '(?s:\b\w+\s*::[^{}]*\{\s*return\s+Button\.Draw\([^,{}]*,\s*Button\.Props\.\{.*?\}\)\s*\})' src apps --glob '*.zi' --glob '*.ts' --glob '*.tsx'; then
    echo 'Inline thin Button forwarding helpers at their call sites.' >&2
    exit 1
fi
if rg -n -U '\b\w+\s*::[^{}]*\{\s*return\s+(Toggle|Checkbox)\.Draw\([^{}]*\)\s*\}' src apps --glob '*.zi' --glob '*.ts' --glob '*.tsx'; then
    echo 'Inline thin toggle and checkbox forwarding helpers at their call sites.' >&2
    exit 1
fi
if rg -n 'TitleBar\.Draw\(|<TitleBar\b' apps/lists --glob '*.zi' --glob '*.ts' --glob '*.tsx'; then
    echo 'The Lists screen starts with its list tabs, without a separate title bar.' >&2
    exit 1
fi
echo 'Canonical button API and title-free list tabs checks passed'
