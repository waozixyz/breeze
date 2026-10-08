#!/usr/bin/env node
// Exercise the actual Emscripten adapter without a browser, SDK or real files.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const sourcePath = fileURLToPath(new URL('../scripts/telegram_host.js', import.meta.url));
const source = readFileSync(sourcePath, 'utf8');
const bridgePath = fileURLToPath(new URL('../site/telegram-bridge.js', import.meta.url));
const bridgeSource = readFileSync(bridgePath, 'utf8');
const input = 1024;
const output = 4096;
const capacity = 65537;
const persistent = 2048;
const capsule = 'synthetic-delegate-capsule';
const entryId = 'a'.repeat(32);
const rawInit = 'query_id=synthetic&auth_date=1700000000&hash=synthetic';
let passed = 0;
let failed = 0;

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

async function settle() {
  // Host callbacks are Promise reactions, never real SDK or timer callbacks.
  for (let index = 0; index < 32; index++) await Promise.resolve();
}

function fixture({ methods = {}, current = true, valid = true, present = true,
  actualBridge = false, storage, initData = rawInit, href } = {}) {
  const heap = new Uint8Array(131072);
  const inputPointer = actualBridge ? 90000 : input;
  const heap32 = new Int32Array(heap.buffer);
  const calls = [];
  const elements = [];
  const blobs = [];
  const addresses = [];
  const revoked = [];
  const timers = [];
  let live = current;
  let library;
  let prohibited = 0;
  const context = Object.freeze({ valid, entryId, initData: rawInit });
  let bridge = {
    context,
    contextCurrent() { return live; },
    saveDelegate(text) {
      calls.push({ action: 'save', text });
      return methods.save ? methods.save(text) : Promise.resolve({ persistent: true });
    },
    loadDelegate() {
      calls.push({ action: 'load' });
      return methods.load ? methods.load() : Promise.resolve(capsule);
    },
    clearDelegate() {
      calls.push({ action: 'clear' });
      return methods.clear ? methods.clear() : Promise.resolve();
    },
  };
  const document = {
    createElement(tag) {
      assert.ok(tag === 'input' || tag === 'a', 'Adapter created an unexpected element');
      const element = {
        tag, clicks: 0, removals: 0,
        click() { this.clicks++; },
        remove() { this.removals++; },
      };
      elements.push(element);
      return element;
    },
  };
  class FakeBlob {
    constructor(parts, options) {
      this.parts = parts;
      this.type = options.type;
      blobs.push(this);
    }
  }
  class FakeURL extends URL {
    static createObjectURL(blob) {
      assert.ok(blobs.includes(blob));
      const address = `blob:synthetic-${addresses.length}`;
      addresses.push(address);
      return address;
    }
    static revokeObjectURL(address) { revoked.push(address); }
  }
  const sandbox = {
    HEAPU8: heap, HEAP32: heap32, TextEncoder, TextDecoder, Map, Promise, document,
    Blob: FakeBlob,
    URL: FakeURL, URLSearchParams, queueMicrotask,
    setTimeout(callback, delay) {
      timers.push({ callback, delay, cancelled: false });
      return timers.length;
    },
    clearTimeout(id) { if (timers[id - 1]) timers[id - 1].cancelled = true; },
    addToLibrary(value) { assert.equal(library, undefined); library = value; },
    InbeTelegramBridge: present ? bridge : undefined,
    console: new Proxy({}, { get() { return () => { prohibited++; throw Error('Unexpected host logging'); }; } }),
  };
  for (const name of ['fetch', 'XMLHttpRequest', 'WebSocket', 'localStorage',
    'sessionStorage', 'indexedDB', 'Telegram', 'SecureStorage', 'CloudStorage']) {
    if (actualBridge && name === 'Telegram') continue;
    Object.defineProperty(sandbox, name, { get() {
      prohibited++;
      throw Error('Adapter accessed a forbidden SDK, network or durable store');
    } });
  }
  let webApp;
  if (actualBridge) {
    webApp = { initData, SecureStorage: storage };
    for (const name of ['initDataUnsafe', 'CloudStorage', 'DeviceStorage', 'sendData']) {
      Object.defineProperty(webApp, name, { get() {
        prohibited++;
        throw Error('Bridge accessed an unverified identity or forbidden Telegram API');
      } });
    }
    sandbox.Telegram = present ? { WebApp: webApp } : undefined;
    sandbox.location = { href: href ?? `https://inbe.example/telegram/?r=${entryId}` };
    vm.runInNewContext(bridgeSource, sandbox, { filename: bridgePath, timeout: 1000 });
    bridge = sandbox.InbeTelegramBridge;
  }
  vm.runInNewContext(source, sandbox, { filename: sourcePath, timeout: 1000 });
  sandbox.TelegramHost = library.$TelegramHost;
  function write(text, pointer = inputPointer) {
    const bytes = new TextEncoder().encode(text);
    assert.ok(pointer + bytes.length + 1 <= heap.length);
    heap.set(bytes, pointer);
    heap[pointer + bytes.length] = 0;
    return bytes.length;
  }
  function read(pointer = output) {
    let end = pointer;
    while (end < heap.length && heap[end] !== 0) end++;
    return new TextDecoder('utf-8', { fatal: true }).decode(heap.subarray(pointer, end));
  }
  function zero(pointer = output, size = capacity) {
    assert.ok(heap.subarray(pointer, pointer + size).every(byte => byte === 0), 'Rejected output was not fully cleared');
  }
  function safe() {
    assert.equal(prohibited, 0);
  }
  return {
    heap, heap32, api: library, host: sandbox.TelegramHost, bridge, sandbox,
    calls, elements, blobs, addresses, revoked, timers, write, read, zero, safe,
    invalidate() {
      live = false;
      if (webApp) webApp.initData = 'changed-synthetic-identity';
    },
    replaceBridge() {
      sandbox.InbeTelegramBridge = { ...bridge,
        context: Object.freeze({ valid: true, entryId: 'b'.repeat(32), initData: 'synthetic-other-user' }),
        contextCurrent: () => true,
      };
    },
    start(action = 2, length = 0, size = capacity) {
      const id = library.telegram_storage_start(action, inputPointer, length, output, size);
      assert.ok(Number.isInteger(id) && id > 0, 'Storage operation did not start');
      return id;
    },
    picker(size = 17664) {
      const id = library.telegram_recovery_start(output, size);
      assert.ok(Number.isInteger(id) && id > 0, 'Recovery picker did not start');
      return { id, element: elements.at(-1) };
    },
  };
}

async function test(name, action) {
  try {
    await action();
    passed++;
  } catch (error) {
    failed++;
    const detail = error?.code === 'ERR_ASSERTION' ? 'contract assertion failed' : 'host operation failed';
    console.error(`FAIL: ${name}: ${detail}`);
  }
}

function protectedCapsule() {
  return JSON.stringify({
    format: 'inbe-delegate-v1', signing_private: '1'.repeat(128),
    encryption_public: '2'.repeat(2368), encryption_private: '3'.repeat(4800),
    owner_public_key: '4'.repeat(2624),
    grant: {
      version: 1, account_id: '5'.repeat(64), grant_id: '6'.repeat(32),
      request_id: '7'.repeat(32), app_id: 'inbe', client_id: '8'.repeat(64),
      node_id: '9'.repeat(64), audience: 'https://api.example.invalid',
      signing_key: 'a'.repeat(64), encryption_key: '2'.repeat(2368),
      issued_at: 1700000000, not_before: 1700000000, expires_at: 1700086400,
      nonce: 'b'.repeat(32), bot_id: 12345, telegram_id: 67890,
      scopes: [{ collection: 'private.inbe.v2.lumi', visibility: 'private',
        read: true, write: true, key_id: 'inbe-lumi-1', key_envelope: 'synthetic' }],
      signature: 'c'.repeat(4840),
    },
  });
}

function protectedStorage() {
  const key = 'inbe_delegate_v1';
  const values = new Map([['unrelated-owner-app', 'preserve-synthetic-value']]);
  const pending = [];
  let holdSet = false;
  let holdGet = false;
  const api = {
    getItem(name, callback) {
      assert.equal(name, key);
      if (holdGet) pending.push(() => callback(null, values.get(name) ?? null));
      else queueMicrotask(() => callback(null, values.get(name) ?? null));
    },
    setItem(name, value, callback) {
      assert.equal(name, key);
      const complete = () => { values.set(name, value); callback(null, true); };
      if (holdSet) pending.push(complete);
      else queueMicrotask(complete);
    },
    removeItem(name, callback) {
      assert.equal(name, key);
      queueMicrotask(() => { values.delete(name); callback(null, true); });
    },
  };
  return {
    api, values, key,
    holdWrite() { holdSet = true; },
    holdRead() { holdGet = true; },
    flush() {
      assert.equal(pending.length, 1, 'Expected one pending synthetic SDK callback');
      pending.shift()();
    },
    safe() { assert.equal(values.get('unrelated-owner-app'), 'preserve-synthetic-value'); },
  };
}

await test('raw signed context and entry are transferred exactly', () => {
  const f = fixture();
  assert.equal(f.api.telegram_current(), 1);
  assert.equal(f.api.telegram_context(1, output, 33), 32);
  assert.equal(f.read(), entryId);
  assert.equal(f.api.telegram_context(2, output, 16385), rawInit.length);
  assert.equal(f.read(), rawInit);
  f.safe();
});

await test('missing, invalid and changed contexts deny transfer and storage', () => {
  for (const options of [{ present: false }, { valid: false }, { current: false }]) {
    const f = fixture(options);
    assert.equal(f.api.telegram_current(), 0);
    assert.equal(f.api.telegram_context(1, output, 33), 0);
    assert.equal(f.api.telegram_storage_start(1, input, 0, output, capacity), 0);
    assert.equal(f.api.telegram_storage_start(2, input, 0, output, capacity), 0);
    assert.equal(f.api.telegram_recovery_start(output, 17664), 0);
    assert.equal(f.api.telegram_recovery_download(input, 1), 0);
    assert.equal(f.calls.length, 0);
    f.safe();
  }
});

await test('context capacity and output bounds preserve surrounding memory', () => {
  const f = fixture();
  f.heap.fill(0x7e);
  assert.equal(f.api.telegram_context(1, output, 32), 0);
  f.zero(output, 32);
  assert.equal(f.heap[output - 1], 0x7e);
  assert.equal(f.heap[output + 32], 0x7e);
  for (const [pointer, size] of [[-1, 33], [output, 0], [f.heap.length - 16, 33]]) {
    const before = f.heap.slice();
    assert.equal(f.api.telegram_context(1, pointer, size), 0);
    assert.deepEqual(f.heap, before);
  }
  assert.equal(f.api.telegram_context(99, output, 33), 0);
  f.safe();
});

await test('invalid operation/input/output bounds do not call protected storage', () => {
  const f = fixture();
  const invalid = [[0, input, 0, output, capacity], [4, input, 0, output, capacity],
    [1, -1, 1, output, capacity], [1, input, -1, output, capacity],
    [1, input, 65537, output, capacity], [1, f.heap.length - 1, 2, output, capacity],
    [2, input, 0, -1, capacity], [2, input, 0, output, 0],
    [2, input, 0, f.heap.length - 10, 20]];
  for (const arguments_ of invalid) assert.equal(f.api.telegram_storage_start(...arguments_), 0);
  assert.equal(f.calls.length, 0);
  f.safe();
});

await test('save sends exact UTF-8 bytes and reports actual persistence', async () => {
  for (const isPersistent of [true, false]) {
    const f = fixture({ methods: { save: () => Promise.resolve({ persistent: isPersistent }) } });
    const text = 'opaque-synthetic-élève-習慣';
    const length = f.write(text);
    const id = f.start(1, length);
    await settle();
    assert.deepEqual(f.calls, [{ action: 'save', text }]);
    assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
    assert.equal(f.heap32[persistent >> 2], isPersistent ? 1 : 0);
    f.zero();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.safe();
  }
});

await test('save never interprets opaque bytes as JSON or app policy', async () => {
  const f = fixture();
  const text = 'synthetic-data-without-a-JSON-shape';
  const id = f.start(1, f.write(text));
  await settle();
  assert.equal(f.calls[0].text, text);
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  f.safe();
});

await test('invalid UTF-8 save fails without passing malformed bytes to bridge', async () => {
  const f = fixture();
  f.heap.set([0xc3, 0x28], input);
  const id = f.start(1, 2);
  await settle();
  assert.equal(f.calls.length, 0);
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.zero();
  f.safe();
});

await test('pending operation becomes a bounded completed restore', async () => {
  const wait = deferred();
  const f = fixture({ methods: { load: () => wait.promise } });
  const id = f.start();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 0);
  assert.equal(f.heap32[persistent >> 2], 0);
  wait.resolve(capsule);
  await settle();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  assert.equal(f.read(), capsule);
  assert.equal(f.heap32[persistent >> 2], 0);
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.safe();
});

await test('missing restore yields empty output without stale bytes', async () => {
  const f = fixture({ methods: { load: () => Promise.resolve(null) } });
  f.heap.fill(0x7e, output, output + capacity);
  const id = f.start();
  await settle();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  f.zero();
  f.safe();
});

await test('oversized or non-text restores fail and clear their entire output', async () => {
  for (const value of ['x'.repeat(64), 123, {}, undefined]) {
    const f = fixture({ methods: { load: () => Promise.resolve(value) } });
    const id = f.start(2, 0, 64);
    await settle();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero(output, 64);
    f.safe();
  }
});

await test('synchronous bridge errors and promise rejections fail cleanly', async () => {
  for (const action of [1, 2, 3]) {
    for (const mode of ['throw', 'reject']) {
      const method = () => {
        if (mode === 'throw') throw Error('Synthetic bridge error');
        return Promise.reject(Error('Synthetic bridge error'));
      };
      const f = fixture({ methods: { save: method, load: method, clear: method } });
      const id = f.start(action, action === 1 ? f.write(capsule) : 0);
      await settle();
      assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
      f.zero();
      f.safe();
    }
  }
});

await test('clear remains possible after context expiry and never invokes other storage actions', async () => {
  const f = fixture({ current: false });
  const id = f.start(3);
  await settle();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  assert.deepEqual(f.calls, [{ action: 'clear' }]);
  f.zero();
  f.safe();
});

await test('context change before restore callback denies capsule delivery', async () => {
  const wait = deferred();
  const f = fixture({ methods: { load: () => wait.promise } });
  const id = f.start();
  f.invalidate();
  wait.resolve(capsule);
  await settle();
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.zero();
  f.safe();
});

await test('context change after callback is rechecked at poll', async () => {
  const f = fixture();
  const id = f.start();
  await settle();
  f.invalidate();
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.zero();
  f.safe();
});

await test('replacement bridge cannot receive an old restore completion', async () => {
  for (const afterCallback of [false, true]) {
    const wait = deferred();
    const f = fixture({ methods: { load: () => wait.promise } });
    const id = f.start();
    if (!afterCallback) f.replaceBridge();
    wait.resolve(capsule);
    await settle();
    if (afterCallback) f.replaceBridge();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero();
    f.safe();
  }
});

await test('context loss rejects a pending poll and prevents a late restore from overwriting reused memory', async () => {
  for (const replace of [false, true]) {
    const wait = deferred();
    const f = fixture({ methods: { load: () => wait.promise } });
    const id = f.start();
    if (replace) f.replaceBridge();
    else f.invalidate();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero();
    f.write('reused-after-failed-poll', output);
    wait.resolve(capsule);
    await settle();
    assert.equal(f.read(), 'reused-after-failed-poll');
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.safe();
  }
});

await test('invalid persistence pointers deny completed restores and wipe output', async () => {
  for (const pointer of [-1, 2049, 131072, 131070]) {
    const f = fixture();
    const id = f.start();
    await settle();
    assert.equal(f.api.telegram_storage_poll(id, pointer), -1);
    f.zero();
    f.safe();
  }
});

await test('cancelled restore rejects late callbacks without touching reused memory', async () => {
  const wait = deferred();
  const f = fixture({ methods: { load: () => wait.promise } });
  const id = f.start();
  f.api.telegram_storage_cancel(id);
  f.zero();
  f.write('reused-buffer-sentinel', output);
  wait.resolve(capsule);
  await settle();
  assert.equal(f.read(), 'reused-buffer-sentinel');
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  assert.equal(f.calls.filter(call => call.action === 'clear').length, 0);
  f.safe();
});

await test('cancelled save clears only its original bridge and ignores late completion', async () => {
  const wait = deferred();
  const f = fixture({ methods: { save: () => wait.promise } });
  const id = f.start(1, f.write(capsule));
  let otherClears = 0;
  f.replaceBridge();
  f.sandbox.InbeTelegramBridge.clearDelegate = async () => { otherClears++; };
  f.api.telegram_storage_cancel(id);
  await settle();
  assert.equal(otherClears, 0);
  assert.equal(f.calls.filter(call => call.action === 'clear').length, 1);
  f.write('reused-buffer-sentinel', output);
  wait.resolve({ persistent: true });
  await settle();
  assert.equal(f.read(), 'reused-buffer-sentinel');
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.safe();
});

await test('cancelled save tolerates a cleanup failure without throwing', async () => {
  for (const mode of ['throw', 'reject']) {
    const wait = deferred();
    const f = fixture({ methods: {
      save: () => wait.promise,
      clear: () => {
        if (mode === 'throw') throw Error('Synthetic cleanup error');
        return Promise.reject(Error('Synthetic cleanup error'));
      },
    } });
    const id = f.start(1, f.write(capsule));
    assert.doesNotThrow(() => f.api.telegram_storage_cancel(id));
    wait.resolve({ persistent: true });
    await settle();
    f.zero();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.safe();
  }
});

await test('independent pending IDs preserve each operation result', async () => {
  const wait = deferred();
  let loads = 0;
  const f = fixture({ methods: { load: () => ++loads === 1 ? wait.promise : Promise.resolve(null) } });
  const first = f.start();
  const secondOutput = output + capacity;
  const second = f.api.telegram_storage_start(2, input, 0, secondOutput, 1024);
  assert.ok(second > 0 && second !== first);
  await settle();
  assert.equal(f.api.telegram_storage_poll(first, persistent), 0);
  assert.equal(f.api.telegram_storage_poll(second, persistent), 1);
  wait.resolve(capsule);
  await settle();
  assert.equal(f.api.telegram_storage_poll(first, persistent), 1);
  assert.equal(f.read(), capsule);
  f.zero(secondOutput, 1024);
  f.safe();
});

await test('fresh unknown poll and cancellation are safe no-ops', () => {
  const f = fixture();
  f.heap.fill(0x7e);
  const before = f.heap.slice();
  assert.equal(f.api.telegram_storage_poll(42, persistent), -1);
  assert.doesNotThrow(() => f.api.telegram_storage_cancel(42));
  assert.deepEqual(f.heap, before);
  f.safe();
});

await test('picker accepts an opaque bounded encrypted file without interpreting it', async () => {
  const f = fixture();
  const { id, element } = f.picker();
  assert.equal(element.type, 'file');
  assert.equal(element.accept, '.key,application/octet-stream');
  assert.equal(element.clicks, 1);
  const text = 'synthetic-opaque-encrypted-recovery';
  element.files = [{ size: text.length, text: async () => text }];
  await element.onchange();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  assert.equal(f.read(), text);
  assert.ok(element.removals > 0);
  assert.equal(f.calls.length, 0);
  f.safe();
});

await test('picker bounds reject before creating or opening a DOM element', () => {
  const f = fixture();
  for (const [pointer, size] of [[output, 17663], [output, 0], [-1, 17664], [f.heap.length - 1, 17664]]) {
    assert.equal(f.api.telegram_recovery_start(pointer, size), 0);
  }
  assert.equal(f.elements.length, 0);
  f.safe();
});

await test('picker missing, empty and oversized files fail without reading content', async () => {
  for (const size of [null, 0, 17664, 17665]) {
    const f = fixture();
    const { id, element } = f.picker();
    let reads = 0;
    element.files = size === null ? [] : [{ size, text: async () => { reads++; return 'ignored'; } }];
    await element.onchange();
    assert.equal(reads, 0);
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero(output, 17664);
    f.safe();
  }
});

await test('picker checks actual encoded content against capacity', async () => {
  const f = fixture();
  const { id, element } = f.picker();
  element.files = [{ size: 1, text: async () => '習'.repeat(6000) }];
  await element.onchange();
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.zero(output, 17664);
  f.safe();
});

await test('picker read failure and owner cancellation fail cleanly', async () => {
  for (const mode of ['reject', 'cancel']) {
    const f = fixture();
    const { id, element } = f.picker();
    if (mode === 'cancel') element.oncancel();
    else {
      element.files = [{ size: 1, text: async () => { throw Error('Synthetic file error'); } }];
      await element.onchange();
    }
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero(output, 17664);
    assert.ok(element.removals > 0);
    f.safe();
  }
});

await test('cancelled picker ignores an already running late file read', async () => {
  const wait = deferred();
  const f = fixture();
  const { id, element } = f.picker();
  element.files = [{ size: 10, text: () => wait.promise }];
  const read = element.onchange();
  f.api.telegram_storage_cancel(id);
  f.zero(output, 17664);
  f.write('reused-recovery-buffer', output);
  wait.resolve('synthetic-encrypted-backup');
  await read;
  assert.equal(f.read(), 'reused-recovery-buffer');
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  assert.equal(f.calls.length, 0);
  f.safe();
});

await test('cancelled picker ignores an onchange that arrives after cancellation', async () => {
  const f = fixture();
  const { id, element } = f.picker();
  f.api.telegram_storage_cancel(id);
  f.write('reused-recovery-buffer', output);
  let reads = 0;
  element.files = [{ size: 10, text: async () => { reads++; return 'synthetic-encrypted-backup'; } }];
  await element.onchange();
  assert.equal(reads, 0);
  assert.equal(f.read(), 'reused-recovery-buffer');
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.safe();
});

await test('context change while reading a recovery file denies delivery', async () => {
  const wait = deferred();
  const f = fixture();
  const { id, element } = f.picker();
  element.files = [{ size: 10, text: () => wait.promise }];
  const read = element.onchange();
  f.invalidate();
  wait.resolve('synthetic-encrypted-backup');
  await read;
  assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
  f.zero(output, 17664);
  f.safe();
});

await test('context and bridge changes after file read are rechecked at poll', async () => {
  for (const replace of [false, true]) {
    const f = fixture();
    const { id, element } = f.picker();
    element.files = [{ size: 10, text: async () => 'synthetic-encrypted-backup' }];
    await element.onchange();
    if (replace) f.replaceBridge();
    else f.invalidate();
    assert.equal(f.api.telegram_storage_poll(id, persistent), -1);
    f.zero(output, 17664);
    f.safe();
  }
});

await test('download copies opaque bytes into a disposable blob and releases its URL', () => {
  const f = fixture();
  const bytes = [0, 0xff, 0x80, 1, 2, 3, 13, 10];
  f.heap.set(bytes, input);
  assert.equal(f.api.telegram_recovery_download(input, bytes.length), 1);
  assert.equal(f.blobs.length, 1);
  assert.equal(f.blobs[0].type, 'application/octet-stream');
  assert.deepEqual(Array.from(f.blobs[0].parts[0]), bytes);
  const link = f.elements.at(-1);
  assert.equal(link.tag, 'a');
  assert.equal(link.download, 'inbe-recovery.key');
  assert.equal(link.href, f.addresses[0]);
  assert.equal(link.clicks, 1);
  assert.equal(link.removals, 1);
  assert.equal(f.calls.length, 0);
  assert.equal(f.revoked.length, 0);
  assert.equal(f.timers.length, 1);
  assert.equal(f.timers[0].delay, 1000);
  f.heap.fill(0, input, input + bytes.length);
  assert.deepEqual(Array.from(f.blobs[0].parts[0]), bytes, 'Download retained a mutable heap view');
  f.timers[0].callback();
  assert.deepEqual(f.revoked, f.addresses);
  f.safe();
});

await test('download bounds and context reject without blobs or link effects', () => {
  const f = fixture();
  for (const [pointer, length] of [[input, -1], [input, 0], [input, 17664], [-1, 1], [f.heap.length - 1, 2]]) {
    assert.equal(f.api.telegram_recovery_download(pointer, length), 0);
  }
  f.invalidate();
  assert.equal(f.api.telegram_recovery_download(input, 1), 0);
  assert.equal(f.blobs.length, 0);
  assert.equal(f.elements.length, 0);
  assert.equal(f.timers.length, 0);
  f.safe();
});

await test('largest supported download remains a binary copy', () => {
  const f = fixture();
  const size = 17663;
  f.heap.fill(0xab, input, input + size);
  assert.equal(f.api.telegram_recovery_download(input, size), 1);
  assert.equal(f.blobs[0].parts[0].length, size);
  assert.ok(f.blobs[0].parts[0].every(byte => byte === 0xab));
  f.safe();
});

await test('actual bridge and host persist then restore an exact scoped capsule after factory restart', async () => {
  const storage = protectedStorage();
  const f = fixture({ actualBridge: true, storage: storage.api });
  const text = protectedCapsule();
  const id = f.start(1, f.write(text));
  await settle();
  assert.equal(f.api.telegram_storage_poll(id, persistent), 1);
  assert.equal(f.heap32[persistent >> 2], 1);
  assert.ok(storage.values.get(storage.key) === text, 'Scoped capsule was changed during persistence');
  const restarted = fixture({ actualBridge: true, storage: storage.api });
  assert.equal(restarted.api.telegram_current(), 1);
  const restore = restarted.start();
  await settle();
  assert.equal(restarted.api.telegram_storage_poll(restore, persistent), 1);
  assert.ok(restarted.read() === text, 'Restart did not restore the exact scoped capsule');
  storage.safe();
  f.safe();
  restarted.safe();
});

await test('actual bridge and host preserve session-only fallback without claiming persistence', async () => {
  const f = fixture({ actualBridge: true });
  const text = protectedCapsule();
  const save = f.start(1, f.write(text));
  await settle();
  assert.equal(f.api.telegram_storage_poll(save, persistent), 1);
  assert.equal(f.heap32[persistent >> 2], 0);
  const restore = f.start();
  await settle();
  assert.equal(f.api.telegram_storage_poll(restore, persistent), 1);
  assert.ok(f.read() === text, 'Session fallback changed the scoped capsule');
  const clear = f.start(3);
  await settle();
  assert.equal(f.api.telegram_storage_poll(clear, persistent), 1);
  const empty = f.start();
  await settle();
  assert.equal(f.api.telegram_storage_poll(empty, persistent), 1);
  f.zero();
  f.safe();
});

await test('actual bridge cancellation cleans a late physical SDK save and never overwrites reused heap', async () => {
  for (const afterDeadline of [false, true]) {
    const storage = protectedStorage();
    storage.holdWrite();
    const f = fixture({ actualBridge: true, storage: storage.api });
    const save = f.start(1, f.write(protectedCapsule()));
    await settle();
    if (afterDeadline) {
      const deadline = f.timers.find(timer => timer.delay === 3000 && !timer.cancelled);
      assert.ok(deadline, 'Protected storage caller did not have a bounded deadline');
      deadline.callback();
      await settle();
    }
    f.api.telegram_storage_cancel(save);
    f.zero();
    f.write('reused-after-actual-save-cancel', output);
    storage.flush();
    await settle();
    assert.equal(f.read(), 'reused-after-actual-save-cancel');
    assert.equal(f.api.telegram_storage_poll(save, persistent), -1);
    assert.ok(!storage.values.has(storage.key), 'Late physical SDK write survived cancellation');
    assert.equal(await f.bridge.loadDelegate(), null);
    storage.safe();
    f.safe();
  }
});

await test('actual bridge identity change rejects a late secure restore without touching reused heap', async () => {
  const storage = protectedStorage();
  storage.values.set(storage.key, protectedCapsule());
  storage.holdRead();
  const f = fixture({ actualBridge: true, storage: storage.api });
  const restore = f.start();
  await settle();
  f.invalidate();
  assert.equal(f.api.telegram_storage_poll(restore, persistent), -1);
  f.zero();
  f.write('reused-after-actual-context-change', output);
  storage.flush();
  await settle();
  assert.equal(f.read(), 'reused-after-actual-context-change');
  assert.equal(f.api.telegram_storage_poll(restore, persistent), -1);
  storage.safe();
  f.safe();
});

await test('actual bridge factory presence preserves ordinary web startup outside Telegram', () => {
  for (const options of [{ present: false }, { initData: '' }]) {
    const f = fixture({ actualBridge: true, ...options });
    assert.ok(f.sandbox.InbeTelegramBridge, 'Actual bridge factory did not install its normal global');
    assert.equal(f.api.telegram_hosted(), 0);
    assert.equal(f.api.telegram_current(), 0);
    f.safe();
  }
});

await test('actual Telegram raw context keeps malformed entry in the hosted gate', () => {
  const f = fixture({ actualBridge: true, href: 'https://inbe.example/telegram/' });
  assert.equal(f.api.telegram_hosted(), 1);
  assert.equal(f.api.telegram_current(), 0);
  assert.equal(f.api.telegram_context(1, output, 33), 0);
  f.safe();
});

await test('pinned host never adopts a replacement bridge for new operations', () => {
  const f = fixture();
  assert.equal(f.api.telegram_context(1, output, 33), 32);
  f.replaceBridge();
  assert.equal(f.api.telegram_current(), 0);
  assert.equal(f.api.telegram_context(2, output, 16385), 0);
  assert.equal(f.api.telegram_storage_start(1, input, f.write(capsule), output, capacity), 0);
  assert.equal(f.api.telegram_storage_start(2, input, 0, output, capacity), 0);
  assert.equal(f.api.telegram_recovery_start(output, 17664), 0);
  assert.equal(f.api.telegram_recovery_download(input, 1), 0);
  assert.equal(f.calls.length, 0);
  assert.equal(f.elements.length, 0);
  f.safe();
});

await test('pinned host denies in-place context replacement even if callback claims it is current', () => {
  const f = fixture();
  assert.equal(f.api.telegram_current(), 1);
  f.bridge.context = Object.freeze({ valid: true, entryId, initData: 'synthetic-new-identity' });
  assert.equal(f.api.telegram_current(), 0);
  assert.equal(f.api.telegram_context(1, output, 33), 0);
  assert.equal(f.api.telegram_storage_start(2, input, 0, output, capacity), 0);
  assert.equal(f.calls.length, 0);
  f.safe();
});

console.log(`Telegram host: ${passed} synthetic heap, context, storage and file checks passed; ${failed} failed`);
process.exitCode = failed === 0 ? 0 : 1;
