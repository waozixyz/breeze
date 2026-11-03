import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/web_boot.js', import.meta.url), 'utf8');

function handoff(value, { allocate = true, fail = false } = {}) {
  const element = { addEventListener() {} };
  const location = new URL('https://inbe.waozi.xyz/?keep=yes&referral=' + encodeURIComponent(value) + '#profile');
  const calls = [], freed = [];
  const context = vm.createContext({
    console: { log() {}, error() {} }, setTimeout, clearTimeout, TextEncoder,
    URLSearchParams,
    window: {
      location, addEventListener() {},
      history: { state: null, replaceState(_state, _title, url) { location.href = new URL(url, location).href; } }
    },
    document: { querySelector() { return element; }, getElementById() { return element; }, addEventListener() {} },
    FS: { syncfs(_populate, done) { done(null); } }
  });
  vm.runInContext(source, context);
  const module = context.Module;
  module.HEAPU8 = new Uint8Array(8192);
  module._malloc = () => allocate ? 8 : 0;
  module._free = pointer => freed.push(pointer);
  module._app_web_open_referral = pointer => {
    let end = pointer;
    while (module.HEAPU8[end]) end++;
    calls.push(new TextDecoder().decode(module.HEAPU8.slice(pointer, end)));
    if (fail) throw new Error('host rejected');
    return 1;
  };
  if (fail) assert.throws(() => vm.runInContext('runLaunchCommand()', context), /host rejected/);
  else vm.runInContext('runLaunchCommand()', context);
  assert.equal(location.search, '?keep=yes');
  assert.equal(location.hash, '#profile');
  vm.runInContext('runLaunchCommand()', context);
  return { calls, freed };
}

for (const input of ['invite_CODE-1', 'https://dew.waozi.xyz/invite/invite_CODE-1?from=friend']) {
  const result = handoff(input);
  assert.deepEqual(result.calls, [input], 'handoff must preserve public input for Entity validation and consume once');
  assert.deepEqual(result.freed, [8]);
}
assert.deepEqual(handoff('').calls, []);
assert.deepEqual(handoff('x'.repeat(4097)).calls, []);
assert.deepEqual(handoff('界'.repeat(1400)).calls, [], 'bound UTF-8 bytes before allocation');
assert.deepEqual(handoff('CODE', { allocate: false }).calls, []);
assert.deepEqual(handoff('CODE', { fail: true }).freed, [8], 'release memory when native validation fails');
console.log('Referral web handoff: exact input, consume once, bounds and allocation cleanup passed');
