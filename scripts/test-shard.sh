#!/bin/sh
# Run one shard of `make test`: every COUNT-th of its prerequisites, starting
# at INDEX (0-based). CI runs the shards on separate runners at once.
#
#   sh scripts/test-shard.sh INDEX COUNT
#   sh scripts/test-shard.sh --list     # every test target, one per line
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

targets() {
    # make's database lists all of test's prerequisites on one line, with
    # .WAIT markers between them because test runs them one at a time.
    make -pq test 2>/dev/null |
        awk '/^test:/ { for (i = 2; i <= NF; i++) if ($i != ".WAIT") print $i; exit }' |
        awk '!seen[$0]++'
}

if [ "${1:-}" = --list ]; then
    targets
    exit 0
fi
if [ $# -ne 2 ]; then
    echo "usage: sh scripts/test-shard.sh INDEX COUNT | --list" >&2
    exit 2
fi
index=$1
count=$2
case "$index$count" in
    *[!0-9]*) echo "test-shard: INDEX and COUNT must be numbers" >&2; exit 2 ;;
esac
if [ "$count" -lt 1 ] || [ "$index" -ge "$count" ]; then
    echo "test-shard: need 0 <= INDEX < COUNT" >&2
    exit 2
fi

all=$(targets)
total=$(printf '%s\n' "$all" | grep -c .)
if [ "$total" -lt 1 ]; then
    echo "test-shard: found no test targets" >&2
    exit 1
fi
shard=$(printf '%s\n' "$all" | awk -v shard="$index" -v count="$count" '(NR - 1) % count == shard')
echo "test-shard: $index of $count runs $(printf '%s\n' "$shard" | grep -c .) of $total targets" >&2
# shellcheck disable=SC2086
exec make $shard
