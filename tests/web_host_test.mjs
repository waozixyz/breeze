import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/web_host.js', import.meta.url), 'utf8');
function host(module = {}, extras = {}) {
  let library;
  const context = vm.createContext({
    Module: module,
    Asyncify: { handleAsync: start => start() },
    addToLibrary: value => { library = value; },
    setTimeout, clearTimeout, Date,
    console: { error() {} },
    ...extras
  });
  vm.runInContext(source, context);
  return library;
}

assert.equal(await host().browser_storage_wait(10, 0), 0);
assert.equal(await host({ __inbeFlushStorageSync() {} }).browser_storage_wait(10, 0), 1);
assert.equal(await host({ __inbeFlushStorageSync: () => Promise.resolve(true) })
  .browser_storage_wait(10, 1), 1);
assert.equal(await host({ __inbeFlushStorageSync: () => Promise.resolve(false) })
  .browser_storage_wait(10, 0), 0);
const rejected = { __inbeFlushStorageSync: () => Promise.reject(new Error('disk full')) };
assert.equal(await host(rejected).browser_storage_wait(10, 0), 0);
assert.equal(rejected.__inbeStorageSyncLastError, 'disk full');
const stalled = { __inbeFlushStorageSync: () => new Promise(() => {}) };
assert.equal(await host(stalled).browser_storage_wait(1, 0), 0);
assert.equal(stalled.__inbeStorageSyncLastError, 'timeout');
const scheduled = {
  __inbeScheduleStorageSync(delay, log) {
    assert.equal(delay, 0);
    assert.equal(log, true);
    scheduled.__inbeFlushStorageSync = () => Promise.resolve(true);
  }
};
assert.equal(await host(scheduled).browser_storage_wait(10, 1), 1);

const clickState = { __kryonContextClick: { x: 20, y: 30, time: Date.now() } };
const clicks = host(clickState);
assert.equal(clicks.web_context_click_in_bounds(30, 30, 40, 40), 0);
assert.equal(clicks.web_context_click_in_bounds(10, 20, 30, 40), 1);
assert.equal(clicks.web_context_click_in_bounds(10, 20, 30, 40), 0);
clickState.__kryonContextClick = { x: 20, y: 30, time: Date.now() - 1000 };
assert.equal(clicks.web_context_click_in_bounds(10, 20, 30, 40), 0);
assert.equal(clickState.__kryonContextClick, null);
assert.equal(host().web_extension_host_js(), 0);
assert.equal(host({}, { window: { __inbeExtension: true } }).web_extension_host_js(), 1);
assert.equal(host({}, {
  window: { location: { protocol: 'chrome-extension:' } },
  chrome: { runtime: {} }
}).web_extension_host_js(), 1);
async function pickFile(scenario, save = 0, capacity = 256) {
  let selectedPath;
  let removed = false;
  const writes = [];
  const callbacks = {};
  const input = {
    style: {},
    files: scenario === 'cancel' ? [] : [{
      arrayBuffer: async () => {
        if (scenario === 'read-error') {
          throw new Error('read failed');
        }
        return Uint8Array.from([1, 2, 3]).buffer;
      }
    }],
    setAttribute(name, value) {
      assert.equal(name, 'aria-label');
      assert.equal(value, 'Select data');
    },
    addEventListener(name, callback) { callbacks[name] = callback; },
    click() { callbacks[scenario === 'cancel' ? 'cancel' : 'change'](); },
    remove() { removed = true; }
  };
  const picker = host({}, {
    UTF8ToString: address => address === 1 ? 'Select data' : 'Data | *.zip *.json',
    lengthBytesUTF8: value => Buffer.byteLength(value),
    stringToUTF8: value => { selectedPath = value; },
    FS: { writeFile: (path, bytes) => { writes.push([path, [...bytes]]); } },
    document: {
      createElement: () => input,
      body: { appendChild() {} }
    }
  });
  const result = await picker.app_pick_file_web(1, 2, 0, save, 3, capacity);
  return { result, selectedPath, removed, writes, input };
}
const picked = await pickFile('selected');
assert.equal(picked.result, 1);
assert.equal(picked.input.accept, '.zip,.json');
assert.deepEqual(picked.writes, [[picked.selectedPath, [1, 2, 3]]]);
assert.equal(picked.removed, true);
const canceled = await pickFile('cancel');
assert.equal(canceled.result, 0);
assert.equal(canceled.removed, true);
assert.equal(canceled.writes.length, 0);
const readError = await pickFile('read-error');
assert.equal(readError.result, -1);
assert.equal(readError.removed, true);
const saved = await pickFile('selected', 1);
assert.equal(saved.result, 1);
assert.match(saved.selectedPath, /^\/tmp\/inbe-file-/);
assert.equal(saved.writes.length, 0);
assert.equal((await pickFile('selected', 0, 2)).result, -1);
let opened = 0;
let removedLink = 0;
const link = { click() { opened += 1; }, remove() { removedLink += 1; } };
const uriHost = host({}, {
  UTF8ToString: pointer => pointer,
  document: { createElement: () => link, body: { appendChild() {} } }
});
assert.equal(uriHost.browser_open_uri('javascript:alert(1)'), 0);
assert.equal(uriHost.browser_open_uri('file:///tmp/data'), 0);
assert.equal(uriHost.browser_open_uri('https://example.test/a'), 1);
assert.equal(opened, 1);
assert.equal(removedLink, 1);
assert.equal(link.target, '_blank');
assert.equal(link.rel, 'noopener');
const measured = new Int32Array(4);
host({}, { HEAP32: measured }).browser_viewport_size(640, 480, 0);
assert.deepEqual([...measured.slice(0, 2)], [640, 480]);
const frame = { getBoundingClientRect: () => ({ width: 280, height: 500 }) };
host({}, {
  HEAP32: measured,
  visualViewport: { width: 330, height: 600 },
  document: { getElementById: id => id === 'canvas-frame' ? frame : null }
}).browser_viewport_size(640, 480, 0);
assert.deepEqual([...measured.slice(0, 2)], [280, 500]);
host({}, { HEAP32: measured }).browser_viewport_size(0, 0, 0);
assert.deepEqual([...measured.slice(0, 2)], [1, 1]);
assert.equal(host({ __inbeStorageSyncing: true }).browser_storage_busy(), 1);
assert.equal(host({ __inbeStorageSyncPending: true }).browser_storage_busy(), 1);
assert.equal(host().browser_storage_busy(), 0);
console.log('web host effects passed');
