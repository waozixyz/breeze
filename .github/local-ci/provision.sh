# The Test job's machine for `make release-ready`: the runner's Ubuntu, the
# packages CI installs for native/browser tests, its pinned SDK and Bun.
# scripts/release-ready.sh has Harmony's container service run this recipe as
# root on the pinned base image (.github/local-ci/base-image), with the
# candidate's .github folder at /run/harmony-container/context.tar, and commit
# the result with these settings:
#   EM_NODE_JS=/usr/local/bin/bun EMSDK_NODE=/usr/local/bin/bun
#   EM_CONFIG=/opt/emsdk/.emscripten
#   PATH=/opt/emsdk/upstream/emscripten:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin
set -eu
BUN_VERSION=1.4.2
BUN_SHA256=36368faef7527875d5ffa52e53cd48021741f2a83eb6208a8dd64068d422a913
GO_VERSION=1.24.4

context=/tmp/inbe-ci-context
mkdir -p "$context"
tar -xf /run/harmony-container/context.tar -C "$context"

# The hosted runner also ships git, Git LFS, curl, cmake, zip, jq, OpenSSL's
# headers, libsodium, D-Bus, Java 21, Go and the Android SDK
# (scripts/release-ready.sh mounts this machine's).
export DEBIAN_FRONTEND=noninteractive
apt-get update
# shellcheck disable=SC2046
apt-get install -y --no-install-recommends \
    git git-lfs python3 curl xz-utils make cmake zip unzip jq file libssl-dev \
    libsodium23 dbus openjdk-21-jdk-headless \
    libgtk-3-0t64 libasound2t64 libdbus-glib-1-2 libxt6t64 libxtst6 libpci3 \
    $(grep -hv '^#' "$context/apt/test-packages.txt" "$context/apt/web-packages.txt" \
        "$context/apt/windows-packages.txt" | cut -d: -f2- | sort -u | tr '\n' ' ')
if [ -x /usr/bin/x86_64-w64-mingw32-gcc-win32 ]; then
    update-alternatives --set x86_64-w64-mingw32-gcc /usr/bin/x86_64-w64-mingw32-gcc-win32
fi
curl -fsSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb
apt-get install -y --no-install-recommends /tmp/chrome.deb
rm -rf /var/lib/apt/lists/* /tmp/chrome.deb

# Bun only: nothing in the image executes Node, including the SDK's cache bootstrap.
mkdir -p /opt/js-runtime
curl -fsSL "https://github.com/oven-sh/bun/releases/download/bun-v${BUN_VERSION}/bun-linux-x64.zip" \
    -o /opt/js-runtime/bun.zip
printf '%s  %s\n' "$BUN_SHA256" /opt/js-runtime/bun.zip | sha256sum -c -
unzip -q /opt/js-runtime/bun.zip -d /opt/js-runtime
mv /opt/js-runtime/bun-linux-x64/bun /usr/local/bin/bun
rm -rf /opt/js-runtime/bun.zip /opt/js-runtime/bun-linux-x64
bun --version
export EM_NODE_JS=/usr/local/bin/bun EMSDK_NODE=/usr/local/bin/bun

mkdir -p /opt/emsdk /opt/firefox
curl -fsSL https://github.com/emscripten-core/emsdk/archive/refs/heads/main.tar.gz \
    | tar -xz -C /opt/emsdk --strip-components=1
emscripten=$(cat "$context/emscripten-version")
/opt/emsdk/emsdk install "$emscripten"
/opt/emsdk/emsdk activate "$emscripten"
/opt/emsdk/upstream/emscripten/embuilder build zlib
chmod -R a+rwX /opt/emsdk/upstream/emscripten/cache
curl -fsSL 'https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US' \
    | tar -xJ -C /opt/firefox --strip-components=1
ln -s /opt/firefox/firefox /usr/local/bin/firefox

curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" | tar -xz -C /usr/local
ln -s /usr/local/go/bin/go /usr/local/bin/go
/usr/local/go/bin/go version
rm -rf "$context"
