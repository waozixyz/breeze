#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if rg -n '\b(StyledButton|TextButton|RenderTextButton|IconButton|PaddedIconBtn|IconBtn|OverlayButton|InvisibleButton|app_sidebar_clean_button|practice_home_action_button|practice_home_quiet_action_button|habit_session_keyboard_key|draw_duration_button|draw_audio_preview_button)\s*\(' src --glob '*.zi' --glob '*.c' --glob '*.h'; then
    echo 'Use Button(ButtonProps) for buttons; use standard Checkbox/Toggle for their own controls.' >&2
    exit 1
fi
if rg -n -U '(?s:\b\w+\s*::[^{}]*\{\s*return\s+Button\(\(ButtonProps\)\{.*?\}\)\s*\})' src --glob '*.zi'; then
    echo 'Inline thin Button forwarding helpers at their call sites.' >&2
    exit 1
fi
if rg -n -U '\b\w+\s*::[^{}]*\{\s*return\s+(Toggle|Checkbox)\([^{}]*\)\s*\}' src --glob '*.zi'; then
    echo 'Inline thin toggle and checkbox forwarding helpers at their call sites.' >&2
    exit 1
fi
if rg -n 'TitleBar\(' src/screens/elist_screen.zi; then
    echo 'The Lists screen starts with its list tabs, without a separate title bar.' >&2
    exit 1
fi
echo 'Canonical button API and title-free list tabs checks passed'
