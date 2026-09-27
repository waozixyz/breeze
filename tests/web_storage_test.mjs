import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/web_boot.js', import.meta.url), 'utf8');

function boot(syncfs) {
  const element = { addEventListener() {} };
  const context = vm.createContext({
    console: { log() {}, error() {} },
    setTimeout, clearTimeout,
    window: { addEventListener() {} },
    document: {
      querySelector() { return element; },
      getElementById() { return element; },
      addEventListener() {}
    },
    FS: { syncfs }
  });
  vm.runInContext(source, context);
  return context.Module;
}

// IDBFS can complete synchronously when there is nothing to write.
const immediate = boot((populate, done) => done(null));
assert.equal(await immediate.__inbeFlushStorageSync(false), true);
assert.equal(immediate.__inbeStorageSyncLastOk, true);
assert.equal(await immediate.__inbeFlushStorageSync(false), true);

const failed = boot((populate, done) => done(new Error('write failed')));
assert.equal(await failed.__inbeFlushStorageSync(false), false);
assert.equal(failed.__inbeStorageSyncLastError, 'write failed');

const callbacks = [];
const queued = boot((populate, done) => callbacks.push(done));
const first = queued.__inbeFlushStorageSync(false);
const second = queued.__inbeFlushStorageSync(false);
assert.equal(first, second);
let resolved = false;
first.then(() => { resolved = true; });
callbacks.shift()(null);
await new Promise(resolve => setTimeout(resolve, 10));
assert.equal(resolved, false, 'flush must include writes queued during a save');
assert.equal(callbacks.length, 1);
callbacks.shift()(null);
assert.equal(await first, true);
assert.equal(await second, true);
assert.equal(queued.__inbeStorageSyncPending, false);
console.log('web storage tests passed');
