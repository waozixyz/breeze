#!/usr/bin/env node
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, readdirSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { gunzipSync } from 'node:zlib';

const root = resolve(import.meta.dirname, '..');
const temporary = mkdtempSync(join(tmpdir(), 'inbe-site-assets-'));
const source = readFileSync(join(root, 'site/static/_worker.js'));
const { default: worker } = await import('data:text/javascript;base64,' + source.toString('base64'));
const limit = 4096;
const random = Buffer.concat(Array.from({ length: 400 }, (_, i) =>
  createHash('sha256').update(String(i)).digest()));
const payloads = new Map();
const requests = [];
const assets = {
  async fetch(request) {
    requests.push(request);
    const path = join(temporary, new URL(request.url).pathname);
    if (!existsSync(path)) {
      return new Response('Not found', { status: 404 });
    }
    const headers = { 'Content-Type': path.endsWith('.json')
      ? 'application/json' : 'application/octet-stream', 'Cache-Control': 'public, max-age=0' };
    return new Response(request.method === 'HEAD' ? null : readFileSync(path), { headers });
  },
};

async function serve(path, options = {}) {
  return worker.fetch(new Request('https://inbe.example' + path + '?v=test', options), { ASSETS: assets });
}

try {
  for (const app of ['web', 'telegram']) {
    const directory = join(temporary, 'build', app);
    mkdirSync(directory, { recursive: true });
    for (const [name, bytes] of [['index.data', random], ['index.wasm', Buffer.concat([random, random])]]) {
      writeFileSync(join(directory, name), bytes);
      payloads.set('/build/' + app + '/' + name, bytes);
    }
  }
  const result = spawnSync('python3', [join(root, 'scripts/prepare-site-assets.py'), temporary,
    '--max-file-bytes', String(limit)], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  for (const [path, original] of payloads) {
    const response = await serve(path, { headers: { Range: 'bytes=0-9' } });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Content-Encoding'), 'gzip');
    assert.equal(response.headers.get('Content-Type'), path.endsWith('.wasm')
      ? 'application/wasm' : 'application/octet-stream');
    assert.deepEqual(gunzipSync(Buffer.from(await response.arrayBuffer())), original);
    const head = await serve(path, { method: 'HEAD' });
    assert.equal((await head.arrayBuffer()).byteLength, 0);
    const cached = await serve(path, { headers: { 'If-None-Match': response.headers.get('ETag') } });
    assert.equal(cached.status, 304);
    assert.equal((await cached.arrayBuffer()).byteLength, 0);
    for (const part of readdirSync(join(temporary, 'build', path.split('/')[2]))) {
      assert.ok(readFileSync(join(temporary, 'build', path.split('/')[2], part)).byteLength <= limit);
    }
  }
  assert.ok(requests.filter(r => r.url.includes('.part-')).every(r => !r.headers.has('Range')));
  const manifestPath = join(temporary, 'build/web/index.data.parts.json');
  const manifest = JSON.parse(readFileSync(manifestPath));
  rmSync(join(temporary, 'build/web', manifest.parts[1]));
  const missing = await serve('/build/web/index.data');
  await assert.rejects(missing.arrayBuffer(), /Missing browser asset part/);

  const directory = join(temporary, 'build/web');
  rmSync(directory, { recursive: true });
  mkdirSync(directory);
  writeFileSync(join(directory, 'index.data'), Buffer.alloc(8192, 65));
  writeFileSync(join(directory, 'index.wasm'), Buffer.alloc(8192, 66));
  const compressed = spawnSync('python3', [join(root, 'scripts/prepare-site-assets.py'), temporary,
    '--max-file-bytes', String(limit)], { encoding: 'utf8' });
  assert.equal(compressed.status, 0, compressed.stderr);
  assert.deepEqual(gunzipSync(Buffer.from(await (await serve('/build/web/index.data')).arrayBuffer())), Buffer.alloc(8192, 65));
  const wasm = await serve('/build/web/index.wasm');
  assert.equal(wasm.headers.get('Content-Type'), 'application/wasm');
  assert.deepEqual(gunzipSync(Buffer.from(await wasm.arrayBuffer())), Buffer.alloc(8192, 66));
  writeFileSync(join(directory, 'index.wasm'), Buffer.from('small wasm'));
  rmSync(join(directory, 'index.wasm.gz'));
  assert.equal(await (await serve('/build/web/index.wasm')).text(), 'small wasm');
  console.log('Site assets: both apps, data/Wasm, streaming gzip, cache, HEAD, ranges and missing pieces passed');
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
