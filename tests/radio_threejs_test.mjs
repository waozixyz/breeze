#!/usr/bin/env node
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';
import { connectProtocol, validateChromiumSocketPath } from '../scripts/web-smoke-protocol.mjs';

const root = resolve(import.meta.dirname, '..');
const staticRoot = join(root, 'site', 'static');
const screenshotPath = process.env.RADIO_SCREENSHOT
  ? resolve(root, process.env.RADIO_SCREENSHOT)
  : null;
if (screenshotPath) {
  assert(screenshotPath.startsWith(join(root, 'build') + sep),
    'RADIO_SCREENSHOT must remain below the project build directory');
}
const profile = await mkdtemp(join(root, 'build', 'rb-'));
validateChromiumSocketPath(profile);

const contentTypes = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.txt', 'text/plain; charset=utf-8'],
]);

const server = createServer(async (request, response) => {
  try {
    const pathname = new URL(request.url, 'http://127.0.0.1').pathname;
    const relative = normalize(pathname === '/' ? 'radio.html' : pathname.slice(1));
    assert(!relative.startsWith('..'), 'request escaped the fixture');
    const data = await readFile(join(staticRoot, relative));
    response.writeHead(200, {
      'Content-Type': contentTypes.get(extname(relative)) || 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    response.end(data);
  } catch {
    response.writeHead(404);
    response.end('Not found');
  }
});

await new Promise((resolveListen, rejectListen) => {
  server.once('error', rejectListen);
  server.listen(0, '127.0.0.1', resolveListen);
});
const origin = 'http://127.0.0.1:' + server.address().port;

const environment = { ...process.env };
for (const name of ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS']) {
  delete environment[name];
}
environment.YUE_DESKTOP_RECOVERY = '0';
// Chromium puts a short-lived singleton socket below TMPDIR. Harmony's command
// transport path is too long for a Unix socket, so use this user's runtime dir.
environment.TMPDIR = environment.XDG_RUNTIME_DIR || '/run/user/' + process.getuid();

const browser = spawn(process.env.CHROMIUM || 'chromium', [
  '--headless=new',
  '--no-sandbox',
  '--disable-dev-shm-usage',
  '--no-first-run',
  '--no-default-browser-check',
  '--enable-webgl',
  '--use-gl=angle',
  '--use-angle=swiftshader',
  '--remote-debugging-port=0',
  '--user-data-dir=' + profile,
  'about:blank',
], {
  detached: true,
  env: environment,
  stdio: ['ignore', 'ignore', 'pipe'],
});
const browserExited = new Promise((resolveExit) => browser.once('exit', resolveExit));

let browserErrors = '';
browser.stderr.on('data', (bytes) => {
  browserErrors = (browserErrors + bytes).slice(-5000);
});

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function until(operation, message, timeout = 15000) {
  const deadline = Date.now() + timeout;
  let lastError;
  while (Date.now() < deadline) {
    assert.equal(browser.exitCode, null, 'Private Chromium exited: ' + browserErrors);
    try {
      const value = await operation();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await delay(50);
  }
  throw new Error(message + (lastError ? ': ' + lastError.message : ''));
}

let protocol;
try {
  const port = await until(async () => {
    try {
      return (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0];
    } catch {
      return null;
    }
  }, 'Private Chromium did not expose its protocol');
  const pages = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
  const page = pages.find((candidate) => candidate.type === 'page');
  assert(page, 'Private Chromium did not create a page');
  protocol = await connectProtocol(page.webSocketDebuggerUrl, 'radio browser', 15000);

  async function call(method, params = {}) {
    return protocol.send(method, params);
  }

  async function evaluate(expression) {
    const answer = await call('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    assert(!answer.exceptionDetails, 'Browser evaluation failed: ' + expression);
    return answer.result.value;
  }

  await call('Runtime.enable');
  await call('Page.enable');
  await call('Log.enable');
  await call('Emulation.setDeviceMetricsOverride', {
    width: screenshotPath ? 1254 : 1280,
    height: screenshotPath ? 1254 : 820,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await call('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      class TestAudio extends EventTarget {
        constructor() {
          super();
          this.src = '';
          this.volume = 1;
          this.preload = 'none';
        }
        play() {
          queueMicrotask(() => this.dispatchEvent(new Event('playing')));
          return Promise.resolve();
        }
        pause() {}
        load() {}
        removeAttribute(name) {
          if (name === 'src') this.src = '';
        }
      }
      Object.defineProperty(globalThis, 'Audio', { value: TestAudio });
    `,
  });
  if (screenshotPath) {
    await call('Emulation.setDefaultBackgroundColorOverride', {
      color: { r: 0, g: 0, b: 0, a: 0 },
    });
  }
  await call('Page.navigate', {
    url: origin + '/radio.html' + (screenshotPath ? '?asset=1' : ''),
  });

  let initial;
  try {
    initial = await until(
      () => evaluate('globalThis.__breezeRadio?.getState()'),
      'Three.js radio did not become ready',
    );
  } catch (error) {
    const diagnostic = await evaluate(`({
      title: document.title,
      body: document.body?.innerText,
      scripts: [...document.scripts].map(script => script.src),
      ready: document.readyState,
    })`);
    throw new Error(error.message + ': ' + JSON.stringify(diagnostic)
      + ': ' + JSON.stringify(protocol.events.slice(-12)));
  }
  assert.equal(initial.powered, false);
  assert.equal(initial.volume, 62);
  assert.equal(initial.selectedStation, 0);
  assert.equal(initial.contextLost, false);
  assert(initial.width >= 1000 && initial.height >= 700, 'WebGL canvas did not fill the page');
  await until(
    () => evaluate('globalThis.__breezeRadio.getState().triangles > 1000'),
    'Three.js radio rendered no substantial geometry',
  );
  if (screenshotPath) {
    const screenshot = await call('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await writeFile(screenshotPath, Buffer.from(screenshot.data, 'base64'));
    const layout = await evaluate('globalThis.__breezeRadio.layout()');
    await writeFile(screenshotPath.replace(/\.png$/i, '') + '-layout.json',
      JSON.stringify(layout, null, 2) + '\n');
  }
  assert.equal(await evaluate(
    'document.querySelectorAll("input, select, textarea, button").length',
  ), 0, 'Radio page added a separate form control');

  async function clickControl(control) {
    const point = await evaluate(
      'globalThis.__breezeRadio.controlPoint(' + JSON.stringify(control) + ')',
    );
    assert(point && Number.isFinite(point.x) && Number.isFinite(point.y),
      'Missing projected control point for ' + control);
    await call('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x: point.x,
      y: point.y,
      button: 'left',
      buttons: 1,
      clickCount: 1,
    });
    await call('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x: point.x,
      y: point.y,
      button: 'left',
      buttons: 0,
      clickCount: 1,
    });
    return point;
  }

  await clickControl('power');
  await until(
    () => evaluate('globalThis.__breezeRadio.getState().status === "ON AIR"'),
    'Power knob did not start the radio',
  );
  assert.equal((await evaluate('globalThis.__breezeRadio.getState()')).powered, true);

  await clickControl('preset-2');
  await until(
    () => evaluate('globalThis.__breezeRadio.getState().selectedStation === 2'),
    'Third physical preset did not tune the station',
  );

  const volumePoint = await evaluate('globalThis.__breezeRadio.controlPoint("volume")');
  await call('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: volumePoint.x,
    y: volumePoint.y,
    button: 'left',
    buttons: 1,
    clickCount: 1,
  });
  await call('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: volumePoint.x + 70,
    y: volumePoint.y - 15,
    button: 'left',
    buttons: 1,
  });
  await call('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: volumePoint.x + 70,
    y: volumePoint.y - 15,
    button: 'left',
    buttons: 0,
    clickCount: 1,
  });
  assert((await evaluate('globalThis.__breezeRadio.getState().volume')) > 62,
    'Dragging the volume knob did not change volume');

  const tuningPoint = await evaluate('globalThis.__breezeRadio.controlPoint("tuning")');
  await call('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: tuningPoint.x,
    y: tuningPoint.y,
    button: 'left',
    buttons: 1,
    clickCount: 1,
  });
  await call('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: tuningPoint.x - 120,
    y: tuningPoint.y,
    button: 'left',
    buttons: 1,
  });
  await call('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: tuningPoint.x - 120,
    y: tuningPoint.y,
    button: 'left',
    buttons: 0,
    clickCount: 1,
  });
  assert((await evaluate('globalThis.__breezeRadio.getState().selectedStation')) < 2,
    'Dragging the tuning knob did not move the dial');

  const failures = protocol.events.filter((event) =>
    event.method === 'Runtime.exceptionThrown'
    || (event.method === 'Log.entryAdded' && event.params.entry.level === 'error'));
  assert.deepEqual(failures, [], 'Browser reported an exception: ' + JSON.stringify(failures));
  console.log('Radio Three.js model: WebGL render, physical power, volume, tuning and presets passed.');
} finally {
  if (protocol) {
    try {
      await protocol.send('Browser.close');
    } catch {}
  }
  if (browser.exitCode === null) {
    try {
      process.kill(-browser.pid, 'SIGTERM');
    } catch {}
  }
  await Promise.race([browserExited, delay(3000)]);
  if (browser.exitCode === null) {
    try {
      process.kill(-browser.pid, 'SIGKILL');
    } catch {}
    await browserExited;
  }
  await new Promise((resolveClose) => server.close(resolveClose));
  await delay(250);
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
