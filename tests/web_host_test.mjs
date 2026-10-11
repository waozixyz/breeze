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
