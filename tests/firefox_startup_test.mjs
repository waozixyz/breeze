import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import test from 'node:test';
import { waitForFirefoxBidi } from '../scripts/firefox-startup.mjs';

function child(t, source) {
  const process = spawn(globalThis.process.execPath, ['-e', source], {
    stdio: ['ignore', 'pipe', 'pipe']
  });
  t.after(() => process.kill());
  return process;
}

for (const stream of ['stdout', 'stderr']) {
  test(`BiDi announcement survives a large ${stream} chunk`, async t => {
    const process = child(t, `process.${stream}.write('WebDriver BiDi listening on ws://127.0.0.1:43210\\n' + 'x'.repeat(20000)); setInterval(() => {}, 1000);`);
    assert.equal(await waitForFirefoxBidi(process, 3000), 'ws://127.0.0.1:43210/session');
  });
}

test('BiDi announcement can span output chunks', async t => {
  const process = child(t, "process.stderr.write('WebDriver BiDi listen'); setTimeout(() => process.stderr.write('ing on ws://127.0.0.1:43210\\n'), 30); setInterval(() => {}, 1000);");
  assert.equal(await waitForFirefoxBidi(process, 3000), 'ws://127.0.0.1:43210/session');
});

test('a partial endpoint is not treated as the complete address', async t => {
  const process = child(t, "process.stderr.write('WebDriver BiDi listening on ws://127.0.0.1:43'); setTimeout(() => process.stderr.write('210\\n'), 30); setInterval(() => {}, 1000);");
  assert.equal(await waitForFirefoxBidi(process, 3000), 'ws://127.0.0.1:43210/session');
});

test('early exit retains bounded diagnostics from stdout', async t => {
  const process = child(t, "process.stdout.write('x'.repeat(20000) + 'startup fixture failed');");
  await assert.rejects(waitForFirefoxBidi(process, 3000), error => {
    assert.match(error.message, /exited before BiDi was ready/);
    assert.match(error.message, /startup fixture failed/);
    assert.ok(error.message.length < 4200);
    return true;
  });
});

test('a silent live launcher times out', async t => {
  const process = child(t, 'setInterval(() => {}, 1000);');
  await assert.rejects(waitForFirefoxBidi(process, 50), /timed out waiting for Firefox BiDi/);
});
