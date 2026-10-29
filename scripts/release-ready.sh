#!/bin/sh
# Run CI's checks here before a release, the way CI runs them, so a release
# cannot go red after its phone check. `make release` requires a pass for the
# exact content it commits.
#
# The container is the Test job's machine: Ubuntu 24.04 with
# .github/apt/test-packages.txt and Node 22 (.github/local-ci/Containerfile).
# It materializes one fixed commit in this checkout’s private overlay, including
# every tracked file. Source directories are recreated in the overlay so later
# edits and new files in the canonical checkout cannot enter the tests. Peers
# keep working on master; nothing this container writes reaches their checkout.
# Packages use the fixed lock without local overrides or untracked secrets.
# Build outputs stay in build/release-ready/ (or RELEASE_READY_OUTPUT); a run
# takes about 90 minutes.
#
# Covered: ci.yml Secret Scan, Package URLs, large-file guard, all three test
# shards, Chrome/Firefox add-ons and smoke, the real pinned Daochi
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

# RELEASE_READY_OUTPUT gives a second run its own build/release-ready-NAME
# outputs, so a fixed-commit build can run beside an active check.
output=${RELEASE_READY_OUTPUT:-build/release-ready}
case "$output" in
    build/release-ready|build/release-ready-[a-z0-9]*) ;;
    *) echo "release-ready: RELEASE_READY_OUTPUT must be build/release-ready-NAME" >&2; exit 2 ;;
esac
case "$output" in
    *[!a-z0-9/-]*) echo "release-ready: RELEASE_READY_OUTPUT must be build/release-ready-NAME" >&2; exit 2 ;;
esac
commit=$(git rev-parse "${RELEASE_READY_REVISION:-HEAD}^{commit}")
image_tag=$({
    git show "$commit:.github/local-ci/Containerfile"
    git show "$commit:.github/apt/test-packages.txt"
    git show "$commit:.github/apt/web-packages.txt"
    git show "$commit:.github/emscripten-version"
} | sha256sum | cut -c1-12)
image=localhost/inbe-ci:$image_tag

# Read the candidate from Git objects, never the changing files on disk.
content=$(python3 - "$commit" <<'PY_CONTENT'
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("phone_check", "scripts/phone-check.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.release_content(module.ROOT, sys.argv[1]))
PY_CONTENT
)
snapshot=$(cat scripts/check-release-overlay.py)

# Runs inside the container, from this variable rather than the script file,
# because resetting the overlay to HEAD may rewrite this script.
inside='set -eu
python3 -c "$RELEASE_READY_SNAPSHOT" /src "$RELEASE_READY_COMMIT"
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
    job "Test: make package-compat-test" make package-compat-test
    job "Browser add-ons: Chrome and Firefox" sh .github/local-ci/check-browser.sh
    job "Sync: pinned Daochi server" sh .github/local-ci/check-sync.sh
fi
if [ -n "$failed" ]; then
    printf "\nrelease-ready: FAILED:%s\n" "$failed"
    exit 1
fi
git diff --exit-code "$RELEASE_READY_COMMIT" -- .
printf "\nrelease-ready: every covered local CI job passed\n"'

mkdir -p "$output/build" "$output/home"
sync_server=""
sync_mount_source="$root/$output/sync-unused"
mkdir -p "$sync_mount_source"
if [ "$#" -eq 0 ]; then
    sync_server=${RELEASE_READY_DAOCHI_SOURCE:-"$root/../../../kryonlabs/daochi"}
    sync_server=$(CDPATH= cd -- "$sync_server" && pwd)
    sync_commit=$(git show "$commit:.github/sync-test-server-commit")
    git -C "$sync_server" cat-file -e "$sync_commit^{commit}"
    sync_mount_source=$sync_server
fi
# One run at a time: runs share build/release-ready/.
exec 9>"$output/lock"
if ! flock -n 9; then
    echo "release-ready: another run is using $output" >&2
    exit 1
fi

# Containers here need no session keyring. Creating one counts against the
# account's kernel key quota (200 keys), which long-lived sessions fill, and
# a full quota stops every container from starting.
printf '[containers]\nkeyring = false\n' > "$output/containers.conf"
CONTAINERS_CONF_OVERRIDE="$root/$output/containers.conf"
export CONTAINERS_CONF_OVERRIDE

if ! podman image exists "$image"; then
    echo "release-ready: building $image"
    git archive "$commit:.github" | podman build -t "$image" -f local-ci/Containerfile -
    # Replace the images of older package lists; one still in use stays.
    podman images --format '{{.Repository}}:{{.Tag}}' localhost/inbe-ci \
        | grep -v ":$image_tag\$" | xargs -r podman rmi >/dev/null 2>&1 || true
fi

rm -f "$output/stamp.json"
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
    -e RELEASE_READY_SNAPSHOT="$snapshot" \
    -w /src "$image" sh -c "$inside" release-ready "$@" || status=$?

if [ "$status" -ne 0 ] || [ "$#" -gt 0 ]; then
    exit "$status"
fi
printf '{\n  "passed": true,\n  "commit": "%s",\n  "content": "%s",\n  "started": "%s",\n  "finished": "%s"\n}\n' \
    "$commit" "$content" "$started" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$output/stamp.json"
echo "release-ready: recorded $output/stamp.json for $(git log -1 --format=%h "$commit")"
