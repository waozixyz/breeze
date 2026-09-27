#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
emcc=${2:-"$HOME/emsdk/upstream/emscripten/emcc"}
work=$(mktemp -d "$root/build/web-bridge-wasm.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$bin/zi2c" --no-main --define PLATFORM_WEB --root "$root" \
    --module-path "$root/src" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/web_storage_bridge_link.zi" \
    "$root/src/app/host_services.zi" "$root/src/platform/web_bridge.zi"
cat > "$work/fixture.js" <<'JS'
Module.__inbeFlushStorageSync = () => new Promise(resolve => {
  setTimeout(() => resolve(true), 2);
});
JS
find "$work/c" -type f -name '*.c' -exec \
    "$emcc" -O1 -I"$root/vendor/ziran/include" -I"$work/c" \
    -I"$work/c/src/app" -I"$work/c/src/platform" -I"$work/c/tests" \
    --js-library "$root/src/web_host.js" --pre-js "$work/fixture.js" \
    -sASYNCIFY -sEXIT_RUNTIME=1 -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 \
    -o "$work/test.js" {} +
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    node "$work/test.js"
echo "Inbe Ziran browser storage WebAssembly test passed"
