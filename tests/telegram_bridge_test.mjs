#!/usr/bin/env node
// SecureStorage callback shapes: https://core.telegram.org/bots/webapps#securestorage
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const sourcePath = fileURLToPath(new URL('../site/telegram-bridge.js', import.meta.url));
const source = readFileSync(sourcePath, 'utf8');
const storageKey = 'inbe_delegate_v1';
const entryId = 'a'.repeat(32);
const href = `https://inbe.example/build/telegram/?r=${entryId}`;
const rawIdentity = 'query_id=synthetic&auth_date=1791400000&hash=synthetic';
let passed = 0;
let failed = 0;

function capsule() {
  return {
    format: 'inbe-delegate-v1',
    signing_private: '1'.repeat(128),
    encryption_public: '2'.repeat(2368),
    encryption_private: '3'.repeat(4800),
    owner_public_key: '4'.repeat(2624),
    grant: {
      version: 1,
      grant_id: '5'.repeat(32),
      account_id: '6'.repeat(64),
      request_id: '9'.repeat(32),
      app_id: 'inbe',
      client_id: 'a'.repeat(64),
      node_id: '7'.repeat(64),
      audience: 'https://api.example.invalid',
      signing_key: 'b'.repeat(64),
      encryption_key: '2'.repeat(2368),
      issued_at: 1791400000,
      not_before: 1791400000,
      expires_at: 1791486400,
      nonce: 'c'.repeat(32),
      bot_id: 12345,
      telegram_id: 67890,
      scopes: [{ collection: 'private.inbe.v2.lumi', visibility: 'private',
        read: true, write: true, key_id: 'inbe-lumi-1', key_envelope: 'synthetic' }],
      signature: '8'.repeat(4840),
    },
  };
}

function secureStorage(values = new Map()) {
  const calls = [];
  const pending = [];
  const modes = { get: 'success', set: 'success', remove: 'success' };
  function respond(operation, callback, value, commit = () => {}) {
    const mode = modes[operation];
    if (mode === 'throw') throw new Error('Synthetic SecureStorage failure');
    if (mode === 'hold') {
      pending.push({ operation, callback, value, commit });
      return;
    }
    queueMicrotask(() => {
      if (mode === 'error') callback(new Error('Synthetic SecureStorage failure'));
      else if (mode === 'false') callback(null, false);
      else {
        commit();
        callback(null, value);
      }
    });
  }
  const api = {
    getItem(key, callback) {
      calls.push({ operation: 'get', key });
      respond('get', callback, values.get(key) ?? null);
      return api;
    },
    setItem(key, value, callback) {
      calls.push({ operation: 'set', key, value });
      respond('set', callback, true, () => values.set(key, value));
      return api;
    },
    removeItem(key, callback) {
      calls.push({ operation: 'remove', key });
      respond('remove', callback, true, () => values.delete(key));
      return api;
    },
    clear() {
      throw new Error('Bridge must preserve other secure-storage keys');
    },
    restoreItem() {
      throw new Error('Bridge must not prompt for restoration without consent');
    },
  };
  function flush(operation) {
    const index = pending.findIndex(call => call.operation === operation);
    assert.ok(index >= 0, 'No pending synthetic storage operation');
    const [call] = pending.splice(index, 1);
    call.commit();
    call.callback(null, call.value);
  }
  return { api, values, calls, modes, flush };
}

function runtime({ storage, initData = rawIdentity, url = href,
  telegramPresent = true, timerScale = 1 } = {}) {
  const accesses = { unsafe: 0, forbidden: 0, logs: 0 };
  const webApp = { initData, SecureStorage: storage };
  webApp.sendData = () => {
    accesses.forbidden++;
    throw new Error('Delegate keys must never be sent to the bot');
  };
  Object.defineProperty(webApp, 'initDataUnsafe', { get() {
    accesses.unsafe++;
    throw new Error('Unverified Telegram identity must never be read');
  } });
  for (const name of ['CloudStorage', 'DeviceStorage']) {
    Object.defineProperty(webApp, name, { get() {
      accesses.forbidden++;
      throw new Error('Delegate keys must use SecureStorage or session memory');
    } });
  }
  const telegram = telegramPresent ? { WebApp: webApp } : undefined;
  const sandbox = {
    URL, URLSearchParams, TextEncoder, TextDecoder,
    setTimeout: (callback, delay) => setTimeout(callback, delay * timerScale), clearTimeout,
    queueMicrotask, location: { href: url }, Telegram: telegram,
    console: new Proxy({}, { get() { return () => { accesses.logs++; }; } }),
  };
  for (const name of ['localStorage', 'sessionStorage', 'indexedDB', 'fetch',
    'XMLHttpRequest', 'WebSocket']) {
    Object.defineProperty(sandbox, name, { get() {
      accesses.forbidden++;
      throw new Error('Bridge attempted an unauthorized storage or network operation');
    } });
  }
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.runInNewContext(source, sandbox, { filename: sourcePath, timeout: 1000 });
  assert.equal(typeof sandbox.createInbeTelegramBridge, 'function', 'Bridge factory is missing');
  assert.ok(sandbox.InbeTelegramBridge, 'Installed global bridge is missing');
  for (const name of ['saveDelegate', 'loadDelegate', 'clearDelegate']) {
    assert.equal(typeof sandbox.InbeTelegramBridge[name], 'function', 'Installed bridge API is incomplete');
  }
  const bridge = sandbox.createInbeTelegramBridge({ telegram, href: url });
  function safe() {
    assert.equal(accesses.unsafe, 0, 'Bridge accessed initDataUnsafe');
    assert.equal(accesses.forbidden, 0, 'Bridge accessed a forbidden store or network');
    assert.equal(accesses.logs, 0, 'Bridge logged account or storage data');
  }
  return { bridge, sandbox, webApp, accesses, safe };
}

async function test(name, check) {
  let timer;
  try {
    await Promise.race([
      check(),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${name}: callback did not settle`)), 2000);
      }),
    ]);
    passed++;
  } catch (error) {
    // A bridge exception may contain the input capsule. Keep diagnostics bounded
    // and never print exception messages or values supplied by the implementation.
    const detail = error?.code === 'ERR_ASSERTION' ? 'contract assertion failed' : 'bridge operation failed';
    failed++;
    console.error(`Telegram bridge: ${name}: ${detail}`);
  } finally {
    clearTimeout(timer);
  }
}

function sameCapsule(actual, expected) {
  // Never let assertion diagnostics print private fields, even synthetic ones.
  assert.ok(actual === expected, 'Delegate capsule was not preserved exactly');
}

async function waitForCall(storage, operation, count = 1) {
  for (let attempt = 0; attempt < 20; attempt++) {
    if (storage.calls.filter(call => call.operation === operation).length >= count) return;
    await new Promise(resolve => setImmediate(resolve));
  }
  throw new Error('Expected synthetic SDK operation did not start');
}

await test('raw context and immutability', async () => {
  const environment = runtime();
  const context = environment.bridge.context;
  assert.ok(context.valid, 'Valid raw Telegram context was refused');
  assert.equal(context.entryId, entryId);
  assert.ok(context.initData === rawIdentity, 'Raw signed initData was modified');
  assert.ok(Object.isFrozen(context), 'Telegram context must be immutable');
  assert.ok(environment.bridge.contextCurrent(), 'Initial context was not current');
  try { context.entryId = 'b'.repeat(32); } catch {}
  try { environment.bridge.context = { valid: false }; } catch {}
  environment.webApp.initData = 'changed-after-creation';
  assert.ok(!environment.bridge.contextCurrent(), 'Changed SDK identity was still current');
  assert.ok(environment.bridge.context === context, 'Bridge replaced its immutable context');
  assert.equal(context.entryId, entryId);
  assert.ok(context.initData === rawIdentity, 'Context changed after SDK mutation');
  environment.safe();
});

await test('Telegram SDK fragment is ignored', async () => {
  const environment = runtime({ url: `${href}#tgWebAppData=synthetic&r=${'b'.repeat(32)}` });
  assert.ok(environment.bridge.context.valid);
  assert.equal(environment.bridge.context.entryId, entryId);
  environment.safe();
});

await test('factory uses its explicit context', async () => {
  const environment = runtime();
  const otherId = 'b'.repeat(32);
  const otherRaw = 'synthetic-explicit-identity';
  const bridge = environment.sandbox.createInbeTelegramBridge({
    telegram: { WebApp: { initData: otherRaw } },
    href: `https://another.example/?r=${otherId}`,
  });
  assert.ok(bridge.context.valid, 'Explicit factory context was refused');
  assert.equal(bridge.context.entryId, otherId);
  assert.ok(bridge.context.initData === otherRaw, 'Factory used global identity instead of explicit input');
  environment.safe();
});

await test('strict entry URLs', async () => {
  const invalid = [
    '', 'not a URL', `http://inbe.example/?r=${entryId}`,
    `https://user@inbe.example/?r=${entryId}`,
    `https://user:password@inbe.example/?r=${entryId}`,
    `https://:443/?r=${entryId}`, 'https://inbe.example/',
    'https://inbe.example/?r=', `https://inbe.example/?r=${entryId.slice(1)}`,
    `https://inbe.example/?r=${entryId}a`, `https://inbe.example/?r=${'A'.repeat(32)}`,
    `https://inbe.example/?r=${'g'.repeat(32)}`,
    `${href}&r=${entryId}`, `${href}&mode=create`,
    `${href}&private_key=synthetic`, `${href}&`, `${href}&&`,
    `https://inbe.example/?%72=${entryId}`, `https://inbe.example/?r=%61${entryId.slice(1)}`,
  ];
  for (const url of invalid) {
    const environment = runtime({ url });
    assert.ok(!environment.bridge.context.valid, 'Malformed entry URL was accepted');
    environment.safe();
  }
});

await test('missing and bounded raw initData', async () => {
  for (const initData of ['', null, {}, 42, false, 'x'.repeat(16385)]) {
    const environment = runtime({ initData });
    assert.ok(!environment.bridge.context.valid, 'Missing or oversized raw identity was accepted');
    environment.safe();
  }
  const maximum = runtime({ initData: 'x'.repeat(16384) });
  assert.ok(maximum.bridge.context.valid, 'Maximum bounded raw identity was refused');
  maximum.safe();
  const outside = runtime({ telegramPresent: false });
  assert.ok(!outside.bridge.context.valid, 'Browser launch outside Telegram was trusted');
  assert.ok(!outside.bridge.contextCurrent(), 'Missing Telegram context was current');
  outside.safe();
});

await test('secure save and restore', async () => {
  const storage = secureStorage(new Map([['other_app_key', 'untouched']]));
  const environment = runtime({ storage: storage.api });
  const raw = JSON.stringify(capsule());
  const saved = await environment.bridge.saveDelegate(raw);
  assert.equal(saved.persistent, true);
  sameCapsule(storage.values.get(storageKey), raw);
  sameCapsule(await environment.bridge.loadDelegate(), raw);
  const restarted = runtime({ storage: storage.api });
  sameCapsule(await restarted.bridge.loadDelegate(), raw);
  assert.ok(storage.calls.every(call => call.key === storageKey), 'Bridge used another storage key');
  environment.safe();
  restarted.safe();
});

await test('synchronous SDK callbacks preserve this binding', async () => {
  const values = new Map();
  const storage = {
    getItem(key, callback) {
      assert.ok(this === storage, 'getItem lost its SDK receiver');
      callback(null, values.get(key) ?? null);
    },
    setItem(key, value, callback) {
      assert.ok(this === storage, 'setItem lost its SDK receiver');
      values.set(key, value);
      callback(null, true);
    },
    removeItem(key, callback) {
      assert.ok(this === storage, 'removeItem lost its SDK receiver');
      values.delete(key);
      callback(null, true);
    },
  };
  const environment = runtime({ storage });
  const raw = JSON.stringify(capsule());
  assert.equal((await environment.bridge.saveDelegate(raw)).persistent, true);
  const restarted = runtime({ storage });
  sameCapsule(await restarted.bridge.loadDelegate(), raw);
  await restarted.bridge.clearDelegate();
  assert.ok(await restarted.bridge.loadDelegate() === null);
  environment.safe();
  restarted.safe();
});

await test('clear only owned key', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())],
    ['other_app_key', 'untouched']]));
  const environment = runtime({ storage: storage.api });
  await environment.bridge.clearDelegate();
  assert.equal(storage.values.has(storageKey), false);
  assert.equal(storage.values.get('other_app_key'), 'untouched');
  assert.equal(await environment.bridge.loadDelegate(), null);
  assert.ok(storage.calls.every(call => call.key === storageKey), 'Clear touched another key');
  environment.safe();
});

await test('successful clear permits a fresh persistent delegate', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
  const environment = runtime({ storage: storage.api });
  await environment.bridge.clearDelegate();
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  assert.equal((await environment.bridge.saveDelegate(replacement)).persistent, true);
  const restarted = runtime({ storage: storage.api });
  sameCapsule(await restarted.bridge.loadDelegate(), replacement);
  environment.safe();
  restarted.safe();
});

await test('failed clear never restores old keys in this session', async () => {
  for (const failure of ['error', 'throw', 'false']) {
    const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
    const environment = runtime({ storage: storage.api });
    sameCapsule(await environment.bridge.loadDelegate(), storage.values.get(storageKey));
    storage.modes.remove = failure;
    await environment.bridge.clearDelegate();
    assert.ok(await environment.bridge.loadDelegate() === null, 'Clear resurrected stored keys');
    environment.safe();
  }
});

await test('delayed restore cannot undo clear', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
  storage.modes.get = 'hold';
  const environment = runtime({ storage: storage.api });
  const read = environment.bridge.loadDelegate();
  await environment.bridge.clearDelegate();
  storage.flush('get');
  assert.ok(await read === null, 'An in-flight read restored cleared keys');
  assert.ok(await environment.bridge.loadDelegate() === null, 'Cleared keys survived in memory');
  environment.safe();
});

await test('delayed restore cannot overwrite a replacement', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
  storage.modes.get = 'hold';
  const environment = runtime({ storage: storage.api });
  const read = environment.bridge.loadDelegate();
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  await environment.bridge.saveDelegate(replacement);
  storage.flush('get');
  sameCapsule(await read, replacement);
  sameCapsule(await environment.bridge.loadDelegate(), replacement);
  environment.safe();
});

await test('clear waits for an in-flight save and erases its keys', async () => {
  const storage = secureStorage();
  storage.modes.set = 'hold';
  const environment = runtime({ storage: storage.api });
  const saving = environment.bridge.saveDelegate(JSON.stringify(capsule()));
  await waitForCall(storage, 'set');
  const clearing = environment.bridge.clearDelegate();
  assert.ok(await environment.bridge.loadDelegate() === null, 'Clear did not invalidate memory immediately');
  storage.flush('set');
  assert.equal((await saving).persistent, false, 'Stale save reported persistence after clear');
  await clearing;
  assert.equal(storage.values.has(storageKey), false, 'In-flight save survived clear in SecureStorage');
  const restarted = runtime({ storage: storage.api });
  assert.ok(await restarted.bridge.loadDelegate() === null, 'Restart restored cleared delegate');
  environment.safe();
  restarted.safe();
});

await test('replacement waits for in-flight old-key removal', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
  storage.modes.remove = 'hold';
  const environment = runtime({ storage: storage.api });
  const clearing = environment.bridge.clearDelegate();
  await waitForCall(storage, 'remove');
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  const saving = environment.bridge.saveDelegate(replacement);
  sameCapsule(await environment.bridge.loadDelegate(), replacement);
  assert.equal(storage.calls.filter(call => call.operation === 'set').length, 0,
    'Replacement wrote while old-key removal was outstanding');
  storage.modes.remove = 'success';
  storage.flush('remove');
  await clearing;
  assert.equal((await saving).persistent, true);
  const restarted = runtime({ storage: storage.api });
  sameCapsule(await restarted.bridge.loadDelegate(), replacement);
  environment.safe();
  restarted.safe();
});

await test('concurrent saves persist only the newest delegate', async () => {
  const storage = secureStorage();
  storage.modes.set = 'hold';
  const environment = runtime({ storage: storage.api });
  const first = environment.bridge.saveDelegate(JSON.stringify(capsule()));
  await waitForCall(storage, 'set');
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  const second = environment.bridge.saveDelegate(replacement);
  sameCapsule(await environment.bridge.loadDelegate(), replacement);
  storage.modes.set = 'success';
  storage.flush('set');
  assert.equal((await first).persistent, false, 'Superseded save reported persistence');
  assert.equal((await second).persistent, true);
  const restarted = runtime({ storage: storage.api });
  sameCapsule(await restarted.bridge.loadDelegate(), replacement);
  environment.safe();
  restarted.safe();
});

await test('clear invalidates another bridge cache on the same SDK store', async () => {
  const storage = secureStorage();
  const environment = runtime({ storage: storage.api });
  await environment.bridge.saveDelegate(JSON.stringify(capsule()));
  const other = environment.sandbox.createInbeTelegramBridge({
    telegram: { WebApp: { initData: rawIdentity, SecureStorage: storage.api } }, href,
  });
  await other.clearDelegate();
  assert.ok(await environment.bridge.loadDelegate() === null, 'Another bridge returned cleared cached keys');
  environment.safe();
});

await test('replacement invalidates another bridge cache on the same SDK store', async () => {
  const storage = secureStorage();
  const environment = runtime({ storage: storage.api });
  await environment.bridge.saveDelegate(JSON.stringify(capsule()));
  const other = environment.sandbox.createInbeTelegramBridge({
    telegram: { WebApp: { initData: rawIdentity, SecureStorage: storage.api } }, href,
  });
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  await other.saveDelegate(replacement);
  const restored = await environment.bridge.loadDelegate();
  assert.ok(restored === null || restored === replacement, 'Another bridge returned superseded cached keys');
  environment.safe();
});

await test('late timed-out save cannot resurrect a cleared delegate', async () => {
  const storage = secureStorage();
  storage.modes.set = 'hold';
  const environment = runtime({ storage: storage.api, timerScale: 0.01 });
  const saving = environment.bridge.saveDelegate(JSON.stringify(capsule()));
  await waitForCall(storage, 'set');
  assert.equal((await saving).persistent, false);
  await environment.bridge.clearDelegate();
  storage.flush('set');
  await new Promise(resolve => setImmediate(resolve));
  const restarted = runtime({ storage: storage.api });
  assert.ok(await restarted.bridge.loadDelegate() === null, 'Late SDK write revived a cleared delegate');
  environment.safe();
  restarted.safe();
});

await test('late timed-out clear cannot delete a newer persistent delegate', async () => {
  const storage = secureStorage(new Map([[storageKey, JSON.stringify(capsule())]]));
  storage.modes.remove = 'hold';
  const environment = runtime({ storage: storage.api, timerScale: 0.01 });
  const clearing = environment.bridge.clearDelegate();
  await waitForCall(storage, 'remove');
  await clearing;
  storage.modes.remove = 'success';
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  const saved = await environment.bridge.saveDelegate(replacement);
  storage.flush('remove');
  await new Promise(resolve => setImmediate(resolve));
  sameCapsule(await environment.bridge.loadDelegate(), replacement);
  if (saved.persistent) {
    const restarted = runtime({ storage: storage.api });
    sameCapsule(await restarted.bridge.loadDelegate(), replacement);
    restarted.safe();
  }
  environment.safe();
});

await test('session memory fallback', async () => {
  const environment = runtime();
  const raw = JSON.stringify(capsule());
  const saved = await environment.bridge.saveDelegate(raw);
  assert.equal(saved.persistent, false);
  sameCapsule(await environment.bridge.loadDelegate(), raw);
  const restarted = runtime();
  assert.equal(await restarted.bridge.loadDelegate(), null, 'Session memory survived a fresh runtime');
  await environment.bridge.clearDelegate();
  assert.equal(await environment.bridge.loadDelegate(), null);
  environment.safe();
  restarted.safe();
});

await test('session memory is isolated between bridge instances', async () => {
  const environment = runtime();
  const raw = JSON.stringify(capsule());
  await environment.bridge.saveDelegate(raw);
  const other = environment.sandbox.createInbeTelegramBridge({
    telegram: { WebApp: { initData: 'another-synthetic-identity' } }, href,
  });
  assert.ok(await other.loadDelegate() === null, 'Factory reused another bridge session keys');
  await other.clearDelegate();
  sameCapsule(await environment.bridge.loadDelegate(), raw);
  environment.safe();
});

await test('partial SecureStorage stays unused', async () => {
  for (const missing of ['getItem', 'setItem', 'removeItem']) {
    const storage = secureStorage();
    delete storage.api[missing];
    const environment = runtime({ storage: storage.api });
    const raw = JSON.stringify(capsule());
    assert.equal((await environment.bridge.saveDelegate(raw)).persistent, false);
    sameCapsule(await environment.bridge.loadDelegate(), raw);
    await environment.bridge.clearDelegate();
    assert.equal(storage.calls.length, 0, 'Partial SecureStorage API was called');
    environment.safe();
  }
});

await test('unanswered storage callbacks fall back within a deadline', async () => {
  const storage = secureStorage();
  storage.modes.set = 'hold';
  const environment = runtime({ storage: storage.api, timerScale: 0.01 });
  const raw = JSON.stringify(capsule());
  assert.equal((await environment.bridge.saveDelegate(raw)).persistent, false);
  storage.flush('set');
  sameCapsule(await environment.bridge.loadDelegate(), raw);
  const coldStorage = secureStorage(new Map([[storageKey, raw]]));
  coldStorage.modes.get = 'hold';
  const cold = runtime({ storage: coldStorage.api, timerScale: 0.01 });
  assert.ok(await cold.bridge.loadDelegate() === null, 'Timed out read returned keys');
  coldStorage.flush('get');
  assert.ok(await cold.bridge.loadDelegate() === null, 'Late callback restored keys after timeout');
  environment.safe();
  cold.safe();
});

await test('missing restorable keys do not trigger an SDK prompt', async () => {
  const storage = secureStorage();
  storage.api.getItem = (key, callback) => {
    storage.calls.push({ operation: 'get', key });
    queueMicrotask(() => callback(null, null, true));
    return storage.api;
  };
  const environment = runtime({ storage: storage.api });
  assert.ok(await environment.bridge.loadDelegate() === null, 'Missing key returned a capsule');
  assert.ok(storage.calls.every(call => call.key === storageKey));
  environment.safe();
});

await test('failed save retains session memory', async () => {
  for (const failure of ['error', 'throw', 'false']) {
    const storage = secureStorage();
    storage.modes.set = failure;
    const environment = runtime({ storage: storage.api });
    const raw = JSON.stringify(capsule());
    assert.equal((await environment.bridge.saveDelegate(raw)).persistent, false);
    sameCapsule(await environment.bridge.loadDelegate(), raw);
    assert.equal(storage.values.has(storageKey), false);
    environment.safe();
  }
});

await test('failed replacement never reloads previous persistent keys', async () => {
  const previous = JSON.stringify(capsule());
  const next = capsule();
  next.signing_private = 'a'.repeat(128);
  const replacement = JSON.stringify(next);
  for (const failure of ['error', 'throw', 'false']) {
    const storage = secureStorage(new Map([[storageKey, previous]]));
    storage.modes.set = failure;
    const environment = runtime({ storage: storage.api });
    assert.equal((await environment.bridge.saveDelegate(replacement)).persistent, false);
    sameCapsule(await environment.bridge.loadDelegate(), replacement);
    environment.safe();
  }
});

await test('failed reads and clear do not restore stale keys', async () => {
  for (const failure of ['error', 'throw', 'false']) {
    const storage = secureStorage();
    const environment = runtime({ storage: storage.api });
    const raw = JSON.stringify(capsule());
    await environment.bridge.saveDelegate(raw);
    storage.modes.get = failure;
    sameCapsule(await environment.bridge.loadDelegate(), raw);
    storage.modes.remove = failure;
    await environment.bridge.clearDelegate();
    assert.equal(await environment.bridge.loadDelegate(), null, 'Clear resurrected a stale delegate');
    environment.safe();
    const cold = runtime({ storage: storage.api });
    assert.equal(await cold.bridge.loadDelegate(), null, 'Failed cold read exposed a capsule');
    cold.safe();
  }
});

await test('malformed capsules cannot replace a valid delegate', async () => {
  const storage = secureStorage();
  const environment = runtime({ storage: storage.api });
  const original = JSON.stringify(capsule());
  await environment.bridge.saveDelegate(original);
  const invalid = [undefined, null, 42, capsule(), '', 'not JSON', 'null', '[]', '{}',
    JSON.stringify({ ...capsule(), format: 'other' })];
  for (const field of ['format', 'grant']) {
    const omitted = capsule();
    delete omitted[field];
    invalid.push(JSON.stringify(omitted));
  }
  for (const [field, size] of [['signing_private', 128], ['encryption_public', 2368],
    ['encryption_private', 4800], ['owner_public_key', 2624]]) {
    for (const value of ['a'.repeat(size - 1), 'a'.repeat(size + 1),
      'A'.repeat(size), 'g'.repeat(size), null]) {
      invalid.push(JSON.stringify({ ...capsule(), [field]: value }));
    }
    const omitted = capsule();
    delete omitted[field];
    invalid.push(JSON.stringify(omitted));
  }
  for (const grant of [null, [], 'synthetic', 1]) {
    invalid.push(JSON.stringify({ ...capsule(), grant }));
  }
  for (const forbidden of ['owner_private_key', 'private_key', 'master_key', 'recovery_passphrase',
    'passphrase', 'session', 'sessions', 'bearer', 'bearers', 'auth_token', 'extra']) {
    invalid.push(JSON.stringify({ ...capsule(), [forbidden]: 'synthetic' }));
  }
  invalid.push(JSON.stringify({ ...capsule(), grant: { padding: 'x'.repeat(65536) } }));
  for (const raw of invalid) {
    const before = storage.calls.filter(call => call.operation === 'set').length;
    try {
      const result = await environment.bridge.saveDelegate(raw);
      assert.ok(!result?.persistent, 'Malformed capsule reported persistent storage');
    } catch (error) {
      if (error?.code === 'ERR_ASSERTION') throw error;
    }
    assert.equal(storage.calls.filter(call => call.operation === 'set').length, before,
      'Malformed capsule reached SecureStorage');
    sameCapsule(await environment.bridge.loadDelegate(), original);
  }
  environment.safe();
});

await test('capsule length boundary', async () => {
  const environment = runtime();
  const raw = JSON.stringify(capsule());
  const maximum = raw + ' '.repeat(65536 - raw.length);
  assert.equal(maximum.length, 65536, 'Boundary fixture has the wrong length');
  assert.equal((await environment.bridge.saveDelegate(maximum)).persistent, false);
  sameCapsule(await environment.bridge.loadDelegate(), maximum);
  try {
    await environment.bridge.saveDelegate(maximum + ' ');
  } catch {}
  sameCapsule(await environment.bridge.loadDelegate(), maximum);
  environment.safe();
});

await test('strict public grant and Lumi scope shapes', async () => {
  const environment = runtime();
  const original = JSON.stringify(capsule());
  await environment.bridge.saveDelegate(original);
  const invalid = [];
  function grantChange(field, value) {
    const changed = capsule();
    changed.grant[field] = value;
    invalid.push(JSON.stringify(changed));
  }
  for (const field of Object.keys(capsule().grant)) {
    const omitted = capsule();
    delete omitted.grant[field];
    invalid.push(JSON.stringify(omitted));
  }
  for (const field of ['owner_private_key', 'master_key', 'passphrase', 'session', 'bearer', 'GRANT_ID']) {
    grantChange(field, 'synthetic');
  }
  for (const [field, length] of [['account_id', 64], ['grant_id', 32], ['request_id', 32],
    ['client_id', 64], ['node_id', 64], ['signing_key', 64], ['encryption_key', 2368],
    ['nonce', 32], ['signature', 4840]]) {
    for (const value of ['f'.repeat(length - 1), 'F'.repeat(length), null]) grantChange(field, value);
  }
  for (const [field, values] of [
    ['version', [0, '1']], ['app_id', ['diary', 'Inbe']],
    ['encryption_key', ['a'.repeat(2368)]],
    ['bot_id', [0, -1, 1.5, '12345', 9007199254740992]],
    ['telegram_id', [0, -1, 1.5, '67890', 4503599627370496]],
    ['issued_at', [0, 1.5, '1791400000']],
    ['not_before', [1791399999, '1791400000']],
    ['expires_at', [1791400000, 1793992001, '1791486400']],
    ['audience', ['http://api.example/', 'https://user:pass@api.example/',
      'https://api.example/?token=synthetic', 'https://api.example/#secret', 'not a URL']],
    ['scopes', [null, [], [{ ...capsule().grant.scopes[0] }, { ...capsule().grant.scopes[0] }]]],
  ]) {
    for (const value of values) grantChange(field, value);
  }
  const scopeFields = Object.keys(capsule().grant.scopes[0]);
  for (const field of scopeFields) {
    const omitted = capsule();
    delete omitted.grant.scopes[0][field];
    invalid.push(JSON.stringify(omitted));
  }
  for (const [field, value] of [['collection', 'private.inbe.v1.sessions'],
    ['visibility', 'public'], ['key_id', 'diary-key'], ['read', 1], ['write', 'true'],
    ['key_envelope', ''], ['key_envelope', 'x'.repeat(16385)], ['extra', 'synthetic']]) {
    const changed = capsule();
    changed.grant.scopes[0][field] = value;
    invalid.push(JSON.stringify(changed));
  }
  const denied = capsule();
  denied.grant.scopes[0].read = false;
  denied.grant.scopes[0].write = false;
  invalid.push(JSON.stringify(denied));
  for (const raw of invalid) {
    try { await environment.bridge.saveDelegate(raw); } catch {}
    sameCapsule(await environment.bridge.loadDelegate(), original);
  }
  environment.safe();
});

await test('duplicate, escaped duplicate and case-alias keys are rejected', async () => {
  const environment = runtime();
  const original = JSON.stringify(capsule());
  await environment.bridge.saveDelegate(original);
  const invalid = [
    original.replace('"format":', '"format":"inbe-delegate-v1","format":'),
    original.replace('"grant_id":', '"grant_id":"' + '5'.repeat(32) + '","grant_id":'),
    original.replace('"read":', '"read":false,"read":'),
    original.replace('"read":', '"r\\u0065ad":false,"read":'),
    original.replace('"grant_id":', '"GRANT_ID":'),
    original.replace('"read":', '"READ":'),
    original.replace('"format":', '"Format":'),
  ];
  for (const raw of invalid) {
    try { await environment.bridge.saveDelegate(raw); } catch {}
    sameCapsule(await environment.bridge.loadDelegate(), original);
  }
  environment.safe();
});

await test('valid public grant boundaries remain usable', async () => {
  for (const [read, write] of [[true, false], [false, true], [true, true]]) {
    const environment = runtime();
    const value = capsule();
    value.grant.telegram_id = 4503599627370495;
    value.grant.not_before += 1;
    value.grant.expires_at = value.grant.issued_at + 2592000;
    value.grant.scopes[0].read = read;
    value.grant.scopes[0].write = write;
    value.grant.scopes[0].key_envelope = 'a'.repeat(16384);
    const raw = JSON.stringify(value);
    assert.equal((await environment.bridge.saveDelegate(raw)).persistent, false);
    sameCapsule(await environment.bridge.loadDelegate(), raw);
    environment.safe();
  }
});

await test('corrupt persistent capsules are never restored', async () => {
  for (const raw of ['not JSON', JSON.stringify({ ...capsule(), master_key: 'synthetic' }),
    JSON.stringify({ ...capsule(), signing_private: 'INVALID' }), 'x'.repeat(65537)]) {
    const storage = secureStorage(new Map([[storageKey, raw], ['other_app_key', 'untouched']]));
    const environment = runtime({ storage: storage.api });
    assert.equal(await environment.bridge.loadDelegate(), null, 'Corrupt secure data was restored');
    assert.equal(storage.values.has(storageKey), false, 'Corrupt capsule was not removed');
    assert.equal(storage.values.get('other_app_key'), 'untouched');
    assert.ok(storage.calls.every(call => call.key === storageKey));
    environment.safe();
  }
});

console.log(`Telegram bridge: ${passed} synthetic context, capsule and secure-storage checks passed; ${failed} failed`);
process.exitCode = failed === 0 ? 0 : 1;
