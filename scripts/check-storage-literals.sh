#!/usr/bin/env bash
# Storage vocabulary lives only in src/storage/storage_layout.zi, whose values
# are fixed by the laws in src/storage/storage_layout_laws.zi.
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
    local allowed="${3:-^$}"
    if rg -n "$pattern" src --glob '*.zi' --glob '*.c' --glob '*.h' \
        --glob '!layout.zi' --glob '!storage_layout.zi' \
        --glob '!storage_layout_laws.zi' | rg -v "$allowed"; then
        echo "$message" >&2
        status=1
    fi
}

check_pattern '"(breathing|inbe)\.db"' \
    'Database names come from the storage layout.'
check_pattern '"(breathing|inbe)-data/' \
    'Export and import entry names come from the storage layout.'
check_pattern '"(breathing|inbe)-data-sqlite"' \
    'The export metadata format comes from the storage layout.'
check_pattern '"/home/(breathing|inbe)"' \
    'Web home paths come from the storage layout.'
# The portable ABI record has the same name as the legacy directory. Only
# its two type-name operations are allowed; paths in this file still fail.
check_pattern '"BreathSession"' \
    'Directory names come from the storage layout.' \
    '^src/cells/value_codec\.zi:[0-9]+:    (value\.type_name = ModuleTextData\("BreathSession"\)|if value\.kind != cast\(s32\)HostRecord \|\| TextFromCString\(value\.type_name\) != "BreathSession" \|\|)$'
check_pattern '"(breathing|inbe)-sessions\.csv"|"breathing-web-export' \
    'Export artifact names come from the storage layout.'
check_pattern '\bjoin_path2\b' \
    'Use storage_join_path (src/storage/db.zi) for path assembly.'
check_pattern 'snprintf\([^;]*"(breathing|inbe)["/]' \
    'Paths are assembled from storage_layout.zi constants, not hand-typed names.'

if [ "$status" -ne 0 ]; then
    echo 'Storage vocabulary must be defined only by the storage layout module and its laws.' >&2
    exit 1
fi
echo 'Storage literal checks passed'
