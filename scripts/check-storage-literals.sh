#!/usr/bin/env bash
# Storage vocabulary lives only in the proved laws package:
# laws/storage_layout -> scripts/generate-storage-layout.mjs ->
# storage_layout.h and the generated src/storage layout modules.
# Hand-typed copies in src/ drift during renames and orphan user data.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v rg >/dev/null 2>&1; then
    echo 'Storage literal checks require ripgrep (rg).' >&2
    exit 1
fi

status=0

check_pattern() {
    local pattern="$1"
    local message="$2"
    if rg -n "$pattern" src --glob '*.zi' --glob '*.c' --glob '*.h' \
        --glob '!layout.zi' --glob '!storage_layout.zi'; then
        echo "$message" >&2
        status=1
    fi
}

check_pattern '"(breathing|inbe)\.db"' \
    'Database names come from the generated storage layout.'
check_pattern '"(breathing|inbe)-data/' \
    'Export and import entry names come from the generated storage layout.'
check_pattern '"(breathing|inbe)-data-sqlite"' \
    'The export metadata format comes from the generated storage layout.'
check_pattern '"/home/(breathing|inbe)"' \
    'Web home paths come from the generated storage layout.'
check_pattern '"BreathSession"' \
    'Directory names come from the generated storage layout.'
check_pattern '"(breathing|inbe)-sessions\.csv"|"breathing-web-export' \
    'Export artifact names come from the generated storage layout.'
check_pattern '\bjoin_path2\b' \
    'Use storage_join_path (src/storage/db.zi) for path assembly.'
check_pattern 'snprintf\([^;]*"(breathing|inbe)["/]' \
    'Paths are assembled from storage_layout.h constants, not hand-typed names.'

if [ "$status" -ne 0 ]; then
    echo 'Storage vocabulary must be defined only by the proved storage layout laws.' >&2
    exit 1
fi
echo 'Storage literal checks passed'
