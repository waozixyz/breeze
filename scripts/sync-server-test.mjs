import { spawn } from 'node:child_process';
import { mkdtemp, open } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import net from 'node:net';
import http from 'node:http';

const binary = process.env.DAOCHI_BIN;
if (!binary) throw new Error('Set DAOCHI_BIN to a built Daochi server binary.');
const root = await mkdtemp(join(tmpdir(), 'inbe-sync-server-'));
const probe = net.createServer();
await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve));
const port = probe.address().port;
await new Promise(resolve => probe.close(resolve));
const url = `http://127.0.0.1:${port}`;
const log = await open(join(root, 'server.log'), 'w');
const server = spawn(resolve(binary), [], {
  cwd: root,
  env: { PATH: process.env.PATH, DAOCHI_ADDR: `127.0.0.1:${port}`,
    DAOCHI_DB: join(root, 'server.db'), DAOCHI_ALLOW_EPHEMERAL_TOKEN_SECRET: '1' },
  stdio: ['ignore', log.fd, log.fd],
});
let serverError;
server.on('error', error => { serverError = error; });
let dropped = false;
const proxy = http.createServer((request, response) => {
  const upstream = http.request(`${url}${request.url}`, {
    method: request.method, headers: request.headers,
  }, result => {
    if (!dropped && request.method === 'POST' && request.url === '/api/v1/sync') {
      dropped = true;
      result.resume();
      result.on('end', () => response.destroy());
    } else {
      response.writeHead(result.statusCode, result.headers);
      result.pipe(response);
    }
  });
  upstream.on('error', () => response.destroy());
  request.pipe(upstream);
});
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (serverError) throw serverError;
    if (server.exitCode !== null) throw new Error(`Server exited: ${server.exitCode}`);
    try { ready = (await fetch(`${url}/healthz`, { signal: AbortSignal.timeout(1000) })).ok; } catch {}
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!ready) throw new Error('Server did not become ready');
  await new Promise(resolve => proxy.listen(0, '127.0.0.1', resolve));
  const faultUrl = `http://127.0.0.1:${proxy.address().port}`;
  const clientEnv = {
    ...process.env,
    HTTP_PROXY: '', HTTPS_PROXY: '', ALL_PROXY: '',
    http_proxy: '', https_proxy: '', all_proxy: '',
    NO_PROXY: '127.0.0.1,localhost', no_proxy: '127.0.0.1,localhost',
  };
  // The client is the Ziran program built by tests/sync_server_zi_test.sh.
  const clientBinary = process.env.SYNC_SERVER_TEST_BIN || resolve('build/sync-server-zi-test/test');
  const client = spawn(clientBinary, [], {
    stdio: 'inherit',
    env: { ...clientEnv, SYNC_TEST_URL: url, SYNC_TEST_FAULT_URL: faultUrl, APP_DATA_ROOT: root },
  });
  const status = await new Promise((resolve, reject) => {
    client.on('error', reject); client.on('exit', resolve);
  });
  if (status !== 0) {
    throw new Error(`Client test exited: ${status}; server exit=${server.exitCode}, signal=${server.signalCode}`);
  }
  if (!dropped) throw new Error('The interrupted upload was not exercised');
} finally {
  proxy.closeAllConnections();
  proxy.close();
  server.kill('SIGTERM');
  await log.close();
  console.log(`Disposable test data and logs: ${root}`);
}
