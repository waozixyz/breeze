import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

let api;
let nextTimer = 1;
const timers = new Map();
const players = [];
class Audio {
  constructor() { players.push(this); }
  play() { return new Promise((resolve, reject) => { this.resolve = resolve; this.reject = reject; }); }
  pause() { this.paused = true; }
  removeAttribute() { this.src = ''; }
  load() {}
}
const context = {
  Module: {}, Audio,
  UTF8ToString: value => value,
  addToLibrary: value => { api = value; },
  setTimeout: (callback, delay) => { const id = nextTimer++; timers.set(id, {callback, delay}); return id; },
  clearTimeout: id => timers.delete(id),
};
vm.runInNewContext(fs.readFileSync(new URL('../src/web_host.js', import.meta.url), 'utf8'), context);
const call = (action, volume = 60) => api.browser_radio(action, 'https://radio.stereoscenic.com/asp-s', volume);
assert.equal(call(3), 0);
assert.equal(call(1), 1);
const first = players.at(-1);
first.onplaying();
assert.equal(call(3), 2);
assert.equal(timers.size, 0);
call(2, 25);
assert.equal(first.volume, 0.25);
first.onerror();
assert.equal(call(3), 3);
assert.equal(first.paused, true);
assert.equal([...timers.values()][0].delay, 2000);
const retry = [...timers.values()][0].callback;
call(0);
assert.equal(timers.size, 0);
retry();
assert.equal(players.length, 1);
assert.equal(call(3), 0);

call(1);
const second = players.at(-1);
const staleError = second.onerror;
call(1);
const third = players.at(-1);
staleError();
second.reject(new Error('old connection'));
await Promise.resolve();
assert.equal(call(3), 1);
assert.equal(third.paused, undefined);
third.onplaying();
third.onwaiting();
assert.equal(call(3), 1);
assert.equal([...timers.values()][0].delay, 20000);
third.onplaying();
assert.equal(timers.size, 0);
call(0);
assert.equal(third.src, '');
assert.equal(timers.size, 0);

call(1);
players.at(-1).reject(Object.assign(new Error('blocked'), {name: 'NotAllowedError'}));
await Promise.resolve();
assert.equal(call(3), -1);
assert.equal(timers.size, 0);
call(0);
console.log('Radio web: live state, volume, retries, stale callbacks, buffering and autoplay rejection passed.');
