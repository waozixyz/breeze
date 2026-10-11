import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const memory = new ArrayBuffer(131072);
const heap = new Uint8Array(memory);
const words = new Int32Array(memory);
let library;
let next = 64;
let fetchRequest;
const sockets = [];
class Socket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    sockets.push(this);
  }
  close(code) {
    this.closedCode = code;
    this.onclose?.();
  }
}
const context = vm.createContext({
  HEAPU8: heap, HEAP32: words, URL, Headers, AbortController,
  TextDecoder, TextEncoder, setTimeout, clearTimeout,
  WebSocket: Socket,
  fetch: (...args) => fetchRequest(...args),
  addToLibrary: value => { library = value; }
});
vm.runInContext(readFileSync(new URL('../scripts/browser_network.js', import.meta.url), 'utf8'), context);
context.BrowserNetwork = library.$BrowserNetwork;

function text(value) {
  const data = Buffer.from(value);
  const at = next;
  next += data.length + 1;
  heap.set(data, at);
  heap[at + data.length] = 0;
  return [at, data.length];
}
function output() {
  let end = 65536;
  while (heap[end] !== 0) {
    end++;
  }
  return Buffer.from(heap.subarray(65536, end)).toString();
}

// HTTP requests run in Kryon's http_transfer; this host keeps sockets.
function open() {
  const id = library.browser_ws_open(...text('wss://example.org/events'),
    ...text('daochi-sync-v1'), ...text('bearer.secret'), 128);
  assert.ok(id > 0);
  const socket = sockets.at(-1);
  socket.onopen();
  return [id, socket];
}
let [socketHandle, socket] = open();
assert.deepEqual([...socket.protocols], ['daochi-sync-v1', 'bearer.secret']);
assert.equal(socket.url.includes('secret'), false);
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), -1);
socket.onmessage({ data: '{"type":"changed"}' });
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), 18);
assert.equal(output(), '{"type":"changed"}');
socket.onclose();
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), 0);
assert.equal(library.$BrowserNetwork.sockets.size, 0);

[socketHandle, socket] = open();
socket.onmessage({ data: 'x'.repeat(128) });
assert.equal(socket.closedCode, 1009);
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), 0);
[socketHandle, socket] = open();
for (let index = 0; index < 17; index++) {
  socket.onmessage({ data: '{}' });
}
assert.equal(socket.closedCode, 1009);
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), 0);
[socketHandle, socket] = open();
library.browser_ws_close(socketHandle);
socket.onmessage({ data: 'late' });
assert.equal(library.$BrowserNetwork.sockets.size, 0);
assert.equal(library.browser_ws_poll(socketHandle, 65536, 128), 0);

console.log('Browser WebSocket lifecycle passed');

let handle;
let finishLate;
let abortSignal;
// Streaming transfers apply backpressure: only one bounded chunk is retained,
// and asynchronous callbacks never write into the caller's memory.
function stream(maximum = 100000, timeout = 1000) {
  return library.browser_stream_open(...text('https://example.org/asset'), maximum, timeout);
}
async function nextChunk(id, capacity = 16384) {
  for (let attempt = 0; attempt < 100; attempt++) {
    const state = library.browser_stream_poll(id, 65536, capacity, 32768, 32772, 32776);
    if (state >= 0) return state;
    await new Promise(resolve => setTimeout(resolve, 1));
  }
  throw new Error('stream did not progress');
}
let reads = 0;
fetchRequest = async (_url, options) => {
  assert.equal(options.redirect, 'follow');
  assert.equal(options.credentials, 'omit');
  return {
    status: 200, headers: new Headers({'content-length': '70000'}),
    body: { getReader: () => ({
      read: async () => {
        reads++;
        return reads === 1 ? {value: new Uint8Array(70000).fill(42), done: false} : {done: true};
      },
      cancel: async () => {}
    })}
  };
};
handle = stream();
assert.ok(handle > 0);
let received = 0;
for (;;) {
  const state = await nextChunk(handle);
  assert.equal(words[32772 >> 2], 200);
  assert.equal(words[32776 >> 2], 70000);
  if (state === 2) break;
  assert.equal(state, 1);
  const count = words[32768 >> 2];
  assert.ok(count > 0 && count <= 16384);
  assert.equal(heap[65536], 42);
  received += count;
  if (received < 70000) assert.equal(reads, 1, 'stream must retain only the current chunk');
}
assert.equal(received, 70000);
library.browser_stream_close(handle);
assert.equal(library.$BrowserNetwork.streams.size, 0);
for (const declared of [true, false]) {
  fetchRequest = async () => new Response('oversized', {
    headers: declared ? {'content-length': '9'} : {}
  });
  handle = stream(8);
  assert.equal(await nextChunk(handle), 0);
  library.browser_stream_close(handle);
}
fetchRequest = async () => new Response(new Uint8Array(1048577));
handle = stream(2000000);
assert.equal(await nextChunk(handle), 0, 'each browser chunk is bounded');
library.browser_stream_close(handle);
fetchRequest = () => new Promise(() => {});
handle = stream(100, 2);
assert.equal(await nextChunk(handle), 0);
library.browser_stream_close(handle);
let canceledReader = false;
fetchRequest = (_url, options) => {
  abortSignal = options.signal;
  return new Promise(resolve => { finishLate = resolve; });
};
handle = stream();
library.browser_stream_close(handle);
heap[65536] = 99;
finishLate({status: 200, headers: new Headers(), body: {
  cancel: async () => { canceledReader = true; }
}});
await new Promise(resolve => setTimeout(resolve, 5));
assert.equal(abortSignal.aborted, true);
assert.equal(canceledReader, true);
assert.equal(heap[65536], 99);
assert.equal(library.$BrowserNetwork.streams.size, 0);
console.log('Browser stream bounds, backpressure, timeout and late-callback cancellation passed');
