import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, writeFileSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { connectProtocol, fetchWithDeadline, withDeadline, validateChromiumSocketPath } from '../scripts/web-smoke-protocol.mjs';

async function fixture(t, { upgrade, request } = {}) {
  const sockets = new Set();
  const server = createServer(request || ((_request, response) => response.end('healthy')));
  server.on('connection', socket => {
    sockets.add(socket);
    socket.on('close', () => sockets.delete(socket));
  });
  server.on('upgrade', (request, socket) => {
    if (upgrade === 'silent-handshake') return;
    const accept = createHash('sha1').update(request.headers['sec-websocket-key'] +
      '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n\r\n');
    upgrade?.(socket);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    for (const socket of sockets) socket.destroy();
    await new Promise(resolve => server.close(resolve));
  });
  const port = server.address().port;
  return { ws: `ws://127.0.0.1:${port}/fixture`, http: `http://127.0.0.1:${port}/`, sockets };
}

function sendText(socket, value) {
  const data = Buffer.from(JSON.stringify(value));
  assert.ok(data.length < 126);
  socket.write(Buffer.concat([Buffer.from([0x81, data.length]), data]));
}

test('real protocol replies and browser events are retained', async t => {
  const server = await fixture(t, { upgrade(socket) {
    socket.once('data', () => {
      sendText(socket, { method: 'fixture.event', params: { live: true } });
      sendText(socket, { id: 1, result: { healthy: true } });
    });
  }});
  const client = await connectProtocol(server.ws, 'CDP', 1000);
  t.after(() => client.close());
  assert.deepEqual(await client.send('Runtime.enable'), { healthy: true });
  assert.equal(client.events[0].method, 'fixture.event');
});

for (const label of ['Chrome CDP', 'Firefox BiDi']) {
  test(`${label} rejects a live unanswered command within its deadline`, async t => {
    const server = await fixture(t);
    const client = await connectProtocol(server.ws, label, 80);
    const started = Date.now();
    await assert.rejects(client.send('fixture.hang'), /fixture.hang timed out after 80ms/);
    assert.ok(Date.now() - started < 2000);
    await assert.rejects(client.send('fixture.later'), /timed out/);
  });
  test(`${label} rejects every pending and later command on connection close`, async t => {
    const server = await fixture(t, { upgrade(socket) {
      socket.once('data', () => socket.end(Buffer.from([0x88, 0])));
    }});
    const client = await connectProtocol(server.ws, label, 1000);
    const results = await Promise.allSettled([client.send('fixture.first'), client.send('fixture.second')]);
    assert.ok(results.every(result => result.status === 'rejected' && /connection closed/.test(result.reason.message)));
    await assert.rejects(client.send('fixture.later'), /connection closed/);
  });
}

test('a silent WebSocket handshake terminates', async t => {
  const server = await fixture(t, { upgrade: 'silent-handshake' });
  await assert.rejects(connectProtocol(server.ws, 'CDP', 80), /connection timed out after 80ms/);
});

test('HTTP timeout includes both headers and response body', async t => {
  for (const bodyOnly of [false, true]) {
    const server = await fixture(t, { request(_request, response) {
      if (bodyOnly) {
        response.writeHead(200, { 'content-type': 'application/json', 'content-length': '1000' });
        response.flushHeaders();
      }
    }});
    await assert.rejects(fetchWithDeadline(server.http, {}, 80, undefined,
      response => response.json()), /HTTP request timed out after 80ms/);
  }
});

test('overall deadline aborts only its owned pending transport', async t => {
  const owned = await fixture(t);
  const unrelated = await fixture(t);
  let client;
  await assert.rejects(withDeadline(async signal => {
    client = await connectProtocol(owned.ws, 'CDP', 3000, signal);
    return client.send('fixture.hang');
  }, 100, 'whole fixture timed out'), /whole fixture timed out/);
  await assert.rejects(client.send('fixture.later'), /whole fixture timed out/);
  const response = await fetchWithDeadline(unrelated.http, {}, 1000);
  assert.equal(await response.text(), 'healthy');
});


test('whole smoke watchdog cleans its own silent browser and profile', async t => {
  const parent = resolve('build/web-smoke-protocol-test');
  mkdirSync(parent, { recursive: true });
  const folder = mkdtempSync(join(parent, 'fixture-'));
  const browser = join(folder, 'silent-browser.py');
  const pidfile = join(folder, 'browser.pid');
  const profiles = join(folder, 'profiles');
  for (const name of ['index.html', 'index.js', 'index.wasm']) writeFileSync(join(folder, name), 'fixture');
  mkdirSync(profiles);
  writeFileSync(join(profiles, 'unrelated-profile'), 'keep');
  writeFileSync(browser, `#!/usr/bin/python3
import os, pathlib, time
pathlib.Path(${JSON.stringify(pidfile)}).write_text(str(os.getpid()))
while True: time.sleep(1)
`, { mode: 0o755 });
  const child = spawn(process.execPath, ['scripts/web-smoke-test.mjs', folder], {
    env: { ...process.env, WEB_SMOKE_BROWSER: browser,
      WEB_SMOKE_PROFILE_ROOT: profiles, WEB_SMOKE_TIMEOUT_MS: '3000',
      WEB_SMOKE_TOTAL_TIMEOUT_MS: '800' },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let output = '';
  for (const stream of [child.stdout, child.stderr]) stream.on('data', data => {
    output = (output + data.toString()).slice(-8000);
  });
  t.after(() => {
    // A failed assertion may still clean only the fixture process whose exact
    // executable path is recorded here, within this test's PID namespace.
    try {
      const pid = Number(readFileSync(pidfile, 'utf8'));
      if (readFileSync(`/proc/${pid}/cmdline`, 'utf8').includes(browser))
        process.kill(pid, 'SIGKILL');
    } catch {}
    if (child.exitCode === null) child.kill('SIGTERM');
    rmSync(folder, { recursive: true, force: true });
  });
  const result = await withDeadline(() => new Promise((resolveExit, reject) => {
    child.once('error', reject);
    child.once('exit', (code, signal) => resolveExit({ code, signal }));
  }), 6000, 'smoke fixture did not exit');
  assert.equal(result.code, 1, output);
  assert.match(output, /web smoke exceeded its 800ms fixture deadline/);
  const pid = Number(readFileSync(pidfile, 'utf8'));
  assert.throws(() => process.kill(pid, 0), error => error.code === 'ESRCH');
  assert.deepEqual(readdirSync(profiles), ['unrelated-profile']);
});


test('Chromium scratch paths fail before launching when the Unix socket would overflow', () => {
  assert.doesNotThrow(() => validateChromiumSocketPath('/src/build/scratch'));
  assert.throws(() => validateChromiumSocketPath('/src/' + 'long/'.repeat(30)),
    /WEB_SMOKE_PROFILE_ROOT is too long.*shorter directory inside this project/);
});
