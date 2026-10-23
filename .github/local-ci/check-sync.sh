#!/bin/sh
# Reset only the server's private overlay, never its canonical checkout.
set -eu
server=/sync-server
filesystem=$(stat -f -c %T "$server")
if [ "$filesystem" != overlayfs ]; then
    echo "release-ready: sync server is not a private overlay" >&2
    exit 2
fi
commit=$(cat .github/sync-test-server-commit)
python3 -c "$RELEASE_READY_SNAPSHOT" "$server" "$commit"
expected=$(git -c safe.directory="$server" -C "$server" rev-parse HEAD:vendor/liboqs)
actual=$(git -c safe.directory="$server/vendor/liboqs" -C "$server/vendor/liboqs" rev-parse HEAD)
if [ "$expected" != "$actual" ]; then
    echo "release-ready: canonical Daochi's liboqs must match the CI pin" >&2
    exit 2
fi
if [ -n "$(git -c safe.directory="$server/vendor/liboqs" -C "$server/vendor/liboqs" status --porcelain --untracked-files=all)" ]; then
    echo "release-ready: canonical Daochi's liboqs must be pristine" >&2
    exit 2
fi
make -C "$server" BUILD_DIR=/src/build/sync-test-server build
DAOCHI_BIN="$server/daochi" make sync-server-test
git -c safe.directory="$server" -C "$server" diff --exit-code "$commit" -- .
