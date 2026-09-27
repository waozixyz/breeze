#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
emcc=${2:-"$HOME/emsdk/upstream/emscripten/emcc"}
work=$(mktemp -d "$root/build/browser-asset-wasm.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --define PLATFORM_WEB --root "$root" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/browser_asset_download_wasm.zi" \
    "$root/src/app/host_services.zi" "$root/src/platform/web_bridge.zi"
cat > "$work/fixture.js" <<'JS'
Module.__inbeScheduleStorageSync = () => {};
globalThis.fetch = async (url, options) => {
  if (options.redirect !== 'follow' || options.credentials !== 'omit') {
    throw new Error('asset fetch policy mismatch');
  }
  if (url.endsWith('/cancel')) await new Promise(resolve => setTimeout(resolve, 2));
  if (url.endsWith('/missing')) return new Response('missing', {status: 404});
  if (url.endsWith('/empty')) return new Response(null, {status: 200});
  if (url.endsWith('/oversized')) {
    return new Response('invalid', {status: 200, headers: {'content-length': '536870913'}});
  }
  const body = new Uint8Array(70000).fill(42);
  body[body.length - 1] = 79;
  return new Response(body, {status: 200, headers: {'content-length': String(body.length)}});
};
JS
find "$work/c" -type f -name '*.c' -exec \
    "$emcc" -O1 -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$work/c/src/app" -I"$work/c/src/platform" -I"$work/c/tests" \
    --js-library "$root/scripts/browser_network.js" --js-library "$root/src/web_host.js" \
    --pre-js "$work/fixture.js" -sASYNCIFY -sEXIT_RUNTIME=1 \
    -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 -o "$work/test.js" {} +
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY node "$work/test.js"
echo "Browser asset download lifecycle and filesystem Wasm test passed"
