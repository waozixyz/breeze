#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
emcc=${2:-"$HOME/emsdk/upstream/emscripten/emcc"}
work=$(mktemp -d "$root/build/browser-network-wasm.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --define PLATFORM_WEB --root "$root" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/tests/browser_network_wasm.zi"
cat > "$work/fixture.js" <<'JS'
globalThis.fetch = async (url, options) => {
  if (options.headers.get('Authorization') !== 'Bearer secret' ||
      options.headers.get('X-Test') !== 'zi' ||
      new TextDecoder().decode(options.body) !== '{"test":true}' ||
      options.redirect !== 'error') throw new Error('request ABI mismatch');
  if (url.endsWith('/cancel')) await new Promise(resolve => setTimeout(resolve, 2));
  return new Response(url.endsWith('/overflow') ? 'oversized' : 'accepted', { status: 201 });
};
globalThis.WebSocket = class {
  constructor(url, protocols) {
    if (protocols.join(',') !== 'daochi-sync-v1,bearer.secret') throw new Error('protocol ABI');
    this.readyState = 0;
    setTimeout(() => {
      this.readyState = 1;
      this.onopen?.({});
      this.onmessage?.({data: 'event'});
    }, 1);
  }
  close() { this.readyState = 3; this.onclose?.({}); }
};
JS
find "$work/c" -type f -name '*.c' -exec \
    "$emcc" -O1 -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$work/c/src/platform" -I"$work/c/tests" \
    --js-library "$root/scripts/browser_network.js" --pre-js "$work/fixture.js" \
    -sASYNCIFY -sEXIT_RUNTIME=1 -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 \
    -o "$work/test.js" {} +
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY node "$work/test.js"
echo "Browser network typed Ziran WebAssembly ABI test passed"
