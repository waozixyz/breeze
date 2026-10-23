#!/bin/sh
# Run CI's checks here before a release, the way CI runs them, so a release
# cannot go red after its phone check. `make release` requires a pass for the
# exact content it commits.
#
# The container is the Test job's machine: Ubuntu 24.04 with
# .github/apt/test-packages.txt and Node 22 (.github/local-ci/Containerfile).
# It sees this checkout through an overlay and resets it to HEAD there, so it
# tests the committed content with the locked packages (no ziran.local.toml),
# without untracked files or secrets; nothing it writes reaches the checkout.
# Files nobody changed since HEAD are read live, so when another session
# edits files during the run, the run names them and records no pass.
# Build outputs stay in build/release-ready/; a run takes about 90 minutes.
#
# Covered: ci.yml Secret Scan, Package URLs, large-file guard, all three test
# shards, visual tests, Chrome/Firefox add-ons and smoke, the real pinned Daochi
# sync server, and release.yml's package compatibility test. Platform release
# builds remain separate. The server comes from its canonical checkout through
# another private overlay; no temporary source checkout is created.
#
#   sh scripts/release-ready.sh             every covered job; writes the stamp
#   sh scripts/release-ready.sh TARGET...   only these make targets; no stamp
# RELEASE_READY_DNS optionally supplies a resolver when rootless DNS is broken.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

output=build/release-ready
image_tag=$(cat .github/local-ci/Containerfile .github/apt/test-packages.txt .github/apt/web-packages.txt .github/emscripten-version | sha256sum | cut -c1-12)
image=localhost/inbe-ci:$image_tag
commit=$(git rev-parse HEAD)

# content COMMIT: what make release compares; tree: the tracked files on disk;
# untracked: untracked files; leaked BEFORE COMMIT LIST: files that changed on
# disk during the run while the container still read them from this checkout.
state() {
    python3 -c 'import importlib.util, subprocess, sys
import os
from pathlib import Path
spec = importlib.util.spec_from_file_location("phone_check", "scripts/phone-check.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = Path(os.environ.get("RELEASE_READY_STATE_ROOT", str(module.ROOT)))
command = sys.argv[1]
if command == "content":
    print(module.release_content(root, sys.argv[2]))
elif command == "tree":
    print(module.working_tree(root))
elif command == "untracked":
    print(module.git(root, "ls-files", "--others", "--exclude-standard"), end="")
else:
    before, commit, listing = sys.argv[2:5]
    after = module.working_tree(root)
    names = lambda *argv: set(module.git(root, "diff-tree", "-r", "--name-only", "--no-renames", *argv).split())
    # Files that differed from the commit at the start were rewritten inside
    # the container and are its own; the others were read live.
    leaked = names(before, after) - names(commit, before)
    leaked |= set(module.git(root, "ls-files", "--others", "--exclude-standard").split()) - set(open(listing).read().split())
    print("\n".join(sorted(leaked)))' "$@"
}

# Runs inside the container, from this variable rather than the script file,
# because resetting the overlay to HEAD may rewrite this script.
inside='set -eu
filesystem=$(awk '\''$5 == "/src" { for (i = 7; i <= NF; i++) if ($i == "-") { print $(i + 1); exit } }'\'' /proc/self/mountinfo)
if [ "$filesystem" != overlay ]; then
    echo "release-ready: /src is not an overlay; refusing to reset it" >&2
    exit 2
fi
git config --global --add safe.directory /src
git lfs install --skip-repo >/dev/null
git -c core.hooksPath=/dev/null reset -q --hard "$RELEASE_READY_COMMIT"
git clean -ffdxq -e /build
failed=""
job() {
    name=$1
    shift
    printf "\n==> %s\n" "$name"
    if ! "$@"; then
        failed="$failed
  $name"
    fi
}
package_urls() {
    test ! -f .gitmodules || { echo "Dependencies are Ziran packages, not submodules"; return 1; }
    bad=$(grep -nE "^[[:space:]]*git[[:space:]]*=" ziran.toml \
        | grep -vE "^[0-9]+:[[:space:]]*git[[:space:]]*=[[:space:]]*\"https://" || true)
    test -z "$bad" || { echo "Non-HTTPS package URL(s):$bad"; return 1; }
}
printf "\n==> Fetch Ziran packages (locked)\n"
sh scripts/packages.sh --locked
if [ "$#" -gt 0 ]; then
    job "make $*" make -k "$@"
else
    job "Secret Scan: app publisher" python3 scripts/check-package-publishers.py
    job "Secret Scan: version consistency" sh -c "python3 scripts/check-version.py && python3 tests/version_test.py"
    job "Secret Scan: tracked files and history" sh -c "python3 scripts/check-secrets.py --working-tree && python3 scripts/check-secrets.py --history"
    job "Package URLs are public HTTPS" package_urls
    job "Files over 1 MB" python3 scripts/check-file-size.py --since origin/master
    job "Test: make test" make -k test
    job "Test: make visual-test" make visual-test
    job "Test: make package-compat-test" make package-compat-test
    job "Browser add-ons: Chrome and Firefox" sh .github/local-ci/check-browser.sh
    job "Sync: pinned Daochi server" sh .github/local-ci/check-sync.sh
fi
if [ -n "$failed" ]; then
    printf "\nrelease-ready: FAILED:%s\n" "$failed"
    exit 1
fi
printf "\nrelease-ready: every covered CI job passed\n"'

mkdir -p "$output/build" "$output/home"
sync_server=""
sync_mount_source="$root/$output/sync-unused"
mkdir -p "$sync_mount_source"
if [ "$#" -eq 0 ]; then
    sync_server=${RELEASE_READY_DAOCHI_SOURCE:-"$root/../../kryonlabs/daochi"}
    sync_server=$(CDPATH= cd -- "$sync_server" && pwd)
    sync_commit=$(cat .github/sync-test-server-commit)
    git -C "$sync_server" cat-file -e "$sync_commit^{commit}"
    sync_mount_source=$sync_server
fi
# One run at a time: runs share build/release-ready/.
exec 9>"$output/lock"
if ! flock -n 9; then
    echo "release-ready: another run is using $output" >&2
    exit 1
fi

if ! podman image exists "$image"; then
    echo "release-ready: building $image"
    podman build -t "$image" -f .github/local-ci/Containerfile .github
    # Replace the images of older package lists; one still in use stays.
    podman images --format '{{.Repository}}:{{.Tag}}' localhost/inbe-ci \
        | grep -v ":$image_tag\$" | xargs -r podman rmi >/dev/null 2>&1 || true
fi

rm -f "$output/stamp.json"
content=$(state content "$commit")
tree_before=$(state tree)
state untracked > "$output/untracked-before"
if [ -n "$sync_server" ]; then
    sync_tree_before=$(RELEASE_READY_STATE_ROOT="$sync_server" state tree)
    RELEASE_READY_STATE_ROOT="$sync_server" state untracked > "$output/sync-untracked-before"
fi
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "release-ready: testing $(git log -1 --format='%h %s' "$commit")"

# Hosted runners have the Android SDK and NDK; the JNI layout tests use it.
android_sdk=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Android/Sdk}}
android_mount=""
if [ -d "$android_sdk/ndk" ]; then
    android_mount="-v $android_sdk:/opt/android-sdk:ro -e ANDROID_HOME=/opt/android-sdk -e ANDROID_SDK_ROOT=/opt/android-sdk"
fi

status=0
dns_option=""
if [ -n "${RELEASE_READY_DNS:-}" ]; then
    case "$RELEASE_READY_DNS" in
        *[!0-9a-fA-F.:]*) echo "release-ready: RELEASE_READY_DNS must be an IP address" >&2; exit 2 ;;
    esac
    dns_option="--dns=$RELEASE_READY_DNS"
fi
# shellcheck disable=SC2086
podman run --rm --pull=never --userns=keep-id \
    $dns_option \
    -v "$root:/src:O" \
    -v "$root/$output/build:/src/build" \
    -v "$root/$output/home:/home/ubuntu" \
    -v "$sync_mount_source:/sync-server:O" \
    $android_mount \
    -e HOME=/home/ubuntu -e CI=true -e RELEASE_READY_COMMIT="$commit" \
    -w /src "$image" sh -c "$inside" release-ready "$@" || status=$?

# The container sees files nobody changed since HEAD live through the
# overlay, so another session's edits during the run can reach the tests.
leaked=$(state leaked "$tree_before" "$commit" "$output/untracked-before")
rm -f "$output/untracked-before"
if [ -n "$sync_server" ]; then
    sync_leaked=$(RELEASE_READY_STATE_ROOT="$sync_server" state leaked "$sync_tree_before" "$sync_commit" "$output/sync-untracked-before")
    rm -f "$output/sync-untracked-before"
    if [ -n "$sync_leaked" ]; then
        echo "release-ready: Daochi source changed during the run; refusing a clean result:" >&2
        printf '%s\n' "$sync_leaked" | head -n 10 | sed 's/^/  /' >&2
        exit 3
    fi
fi
if [ -n "$leaked" ]; then
    count=$(printf '%s\n' "$leaked" | grep -c .)
    echo "release-ready: $count files changed in the checkout during the run and may have reached" >&2
    echo "the tests, so this is not a clean result; run again when other sessions are idle:" >&2
    printf '%s\n' "$leaked" | head -n 10 | sed 's/^/  /' >&2
    exit 3
fi
if [ "$status" -ne 0 ] || [ "$#" -gt 0 ]; then
    exit "$status"
fi
printf '{\n  "passed": true,\n  "commit": "%s",\n  "content": "%s",\n  "started": "%s",\n  "finished": "%s"\n}\n' \
    "$commit" "$content" "$started" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$output/stamp.json"
echo "release-ready: recorded $output/stamp.json for $(git log -1 --format=%h "$commit")"
