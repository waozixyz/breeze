#!/usr/bin/env node

import { createServer } from 'node:http';
import { createReadStream, mkdtempSync, rmSync, existsSync, accessSync, constants, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, normalize, resolve, sep } from 'node:path';
import { spawn } from 'node:child_process';
import { inflateSync } from 'node:zlib';

if (typeof WebSocket === 'undefined') {
  console.error('web smoke: FAIL: this script needs the global WebSocket API. Use Node >= 21, or pass --experimental-websocket on Node 20.');
  process.exit(1);
}

const root = resolve(process.argv[2] || 'build/dist/web');
const browserSetting = process.env.WEB_SMOKE_BROWSER || 'auto';
const browserArgs = (process.env.WEB_SMOKE_BROWSER_ARGS || '').split(/\s+/).filter(Boolean);
const timeoutMs = Number(process.env.WEB_SMOKE_TIMEOUT_MS || 90000);
const rendererSetting = (process.env.WEB_SMOKE_RENDERER || '').toLowerCase();
const renderer = rendererSetting || 'canvas';
if (renderer !== 'canvas') {
  console.error(`web smoke: FAIL: Inbe web builds only support WEB_SMOKE_RENDERER="canvas" now; got ${JSON.stringify(renderer)}`);
  process.exit(1);
}
const allowWebglDisabled = process.env.WEB_SMOKE_ALLOW_WEBGL_DISABLED
  ? !/^(0|false|no)$/i.test(process.env.WEB_SMOKE_ALLOW_WEBGL_DISABLED)
  : false;
const useNoSandbox = process.env.WEB_SMOKE_NO_SANDBOX
  ? !/^(0|false|no)$/i.test(process.env.WEB_SMOKE_NO_SANDBOX)
  : !!process.env.CI || (typeof process.getuid === 'function' && process.getuid() === 0);
const userDataDir = mkdtempSync(join(tmpdir(), 'inbe-web-smoke-'));
const mime = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.wasm', 'application/wasm'],
  ['.json', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.css', 'text/css; charset=utf-8'],
  ['.zip', 'application/zip'],
  ['.ogg', 'audio/ogg']
]);

if (!existsSync(join(root, 'index.html')) || !existsSync(join(root, 'index.js')) || !existsSync(join(root, 'index.wasm'))) {
  console.error(`web smoke: missing web build outputs in ${root}`);
  process.exit(1);
}

function canExecute(path) {
  try {
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function findOnPath(command) {
  if (command.includes('/') || command.includes('\\'))
    return canExecute(command) ? command : '';

  for (const dir of (process.env.PATH || '').split(':')) {
    if (!dir) continue;
    const path = join(dir, command);
    if (canExecute(path))
      return path;
  }
  return '';
}

function browserCandidates() {
  const candidates = [];
  if (process.env.CHROME) candidates.push(process.env.CHROME);
  if (process.platform === 'freebsd') {
    candidates.push('firefox', 'librewolf');
  }
  candidates.push(
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/snap/bin/chromium',
    '/opt/google/chrome/chrome',
    '/opt/chromium/chrome',
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
    'chrome',
    'firefox',
    'librewolf'
  );
  return [...new Set(candidates.filter(Boolean))];
}

function resolveBrowser() {
  if (browserSetting && browserSetting !== 'auto') {
    const resolved = findOnPath(browserSetting);
    if (resolved) return resolved;
    throw new Error(`browser not found: ${browserSetting}`);
  }

  const tried = browserCandidates();
  for (const candidate of tried) {
    const resolved = findOnPath(candidate);
    if (resolved) return resolved;
  }
  throw new Error(`no Chrome/Chromium browser found; tried ${tried.join(', ')}`);
}

function isFirefoxBrowser(browser) {
  return /(^|[/\\])(firefox|librewolf)(\.exe)?$/i.test(browser);
}

function contentType(path) {
  const dot = path.lastIndexOf('.');
  return dot >= 0 ? mime.get(path.slice(dot).toLowerCase()) || 'application/octet-stream' : 'application/octet-stream';
}

function isInside(base, path) {
  const rel = normalize(path).startsWith(base.endsWith(sep) ? base : base + sep);
  return path === base || rel;
}

const server = createServer((req, res) => {
  const url = new URL(req.url || '/', 'http://127.0.0.1');
  const leaf = url.pathname === '/' ? '/index.html' : decodeURIComponent(url.pathname);
  const path = resolve(root, '.' + leaf);

  if (!isInside(root, path) || !existsSync(path)) {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('not found');
    return;
  }

  res.writeHead(200, {
    'content-type': contentType(path),
    'cache-control': 'no-store'
  });
  createReadStream(path).pipe(res);
});

function listen() {
  return new Promise((resolveListen, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolveListen(server.address().port));
  });
}

function delay(ms) {
  return new Promise(resolveDelay => setTimeout(resolveDelay, ms));
}

function formatChromeLaunchError(stderrLines) {
  const stderr = stderrLines.join('').trim();
  const suffix = stderr ? `; chrome stderr: ${stderr.slice(-4000)}` : '';
  return new Error(`Chrome exited before DevTools was ready${suffix}`);
}

function readDevtoolsPort() {
  const path = join(userDataDir, 'DevToolsActivePort');

  if (!existsSync(path))
    return 0;

  const port = Number(readFileSync(path, 'utf8').split('\n', 1)[0]);
  return Number.isFinite(port) && port > 0 ? port : 0;
}

async function waitForDevtools(chrome, stderrLines) {
  const start = Date.now();
  let exited = false;
  const onExit = () => {
    exited = true;
  };
  chrome.once('exit', onExit);

  try {
    while (Date.now() - start < timeoutMs) {
      if (exited)
        throw formatChromeLaunchError(stderrLines);

      const port = readDevtoolsPort();
      if (port > 0) {
        try {
          const response = await fetch(`http://127.0.0.1:${port}/json/version`);
          if (response.ok)
            return port;
        } catch {}
      }

      await delay(50);
    }
  } finally {
    chrome.off('exit', onExit);
  }

  const stderr = stderrLines.join('').trim();
  const suffix = stderr ? `; chrome stderr: ${stderr.slice(-4000)}` : '';
  throw new Error(`timed out waiting for Chrome DevToolsActivePort${suffix}`);
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok)
    throw new Error(`${options.method || 'GET'} ${url} failed: ${response.status}`);
  return response.json();
}

function connect(wsUrl) {
  return new Promise((resolveConnect, reject) => {
    const ws = new WebSocket(wsUrl);
    const pending = new Map();
    const events = [];
    let nextId = 1;

    ws.addEventListener('open', () => {
      resolveConnect({
        events,
        send(method, params = {}) {
          const id = nextId++;
          ws.send(JSON.stringify({ id, method, params }));
          return new Promise((resolveSend, rejectSend) => {
            pending.set(id, { resolve: resolveSend, reject: rejectSend, method });
          });
        },
        close() {
          ws.close();
        }
      });
    });
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id && pending.has(message.id)) {
        const item = pending.get(message.id);
        pending.delete(message.id);
        if (message.error)
          item.reject(new Error(`${item.method}: ${message.error.message}`));
        else
          item.resolve(message.result || {});
      } else if (message.method) {
        events.push(message);
      }
    });
    ws.addEventListener('error', reject);
  });
}

function connectBidi(wsUrl) {
  return new Promise((resolveConnect, reject) => {
    const ws = new WebSocket(wsUrl);
    const pending = new Map();
    const events = [];
    let nextId = 1;

    ws.addEventListener('open', () => {
      resolveConnect({
        events,
        send(method, params = {}) {
          const id = nextId++;
          ws.send(JSON.stringify({ id, method, params }));
          return new Promise((resolveSend, rejectSend) => {
            pending.set(id, { resolve: resolveSend, reject: rejectSend, method });
          });
        },
        close() {
          ws.close();
        }
      });
    });
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id && pending.has(message.id)) {
        const item = pending.get(message.id);
        pending.delete(message.id);
        if (message.error)
          item.reject(new Error(`${item.method}: ${message.message || message.error || JSON.stringify(message)}`));
        else
          item.resolve(message.result || {});
      } else if (message.method) {
        events.push(message);
      }
    });
    ws.addEventListener('error', event => reject(new Error(event.message || `WebSocket error for ${wsUrl}`)));
  });
}

function eventText(event) {
  if (event.method === 'Runtime.consoleAPICalled') {
    return (event.params.args || []).map(arg => arg.value ?? arg.description ?? '').join(' ');
  }
  if (event.method === 'Log.entryAdded')
    return event.params.entry?.text || '';
  if (event.method === 'Runtime.exceptionThrown')
    return [
      event.params.exceptionDetails?.text || event.params.exceptionDetails?.exception?.description || 'exception thrown',
      ...((event.params.exceptionDetails?.stackTrace?.callFrames || []).map(frame => {
        const name = frame.functionName || '(anonymous)';
        return `${name}@${frame.url}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`;
      }))
    ].join(' ');
  if (event.method === 'Page.javascriptDialogOpening')
    return event.params.message || 'javascript dialog opened';
  return '';
}

function isBenignAsyncifyUnwind(text) {
  return /\b(callUserCallback|doRewind|MainLoop_runner)\b/.test(text) &&
    !/\b(RuntimeError|Aborted|memory access|unreachable)\b/i.test(text);
}

function fatalEvent(event) {
  const text = eventText(event);
  if (event.method === 'Runtime.exceptionThrown' && text.includes('transaction.oncomplete'))
    return '';
  if (event.method === 'Runtime.exceptionThrown' && isBenignAsyncifyUnwind(text))
    return '';
  if (event.method === 'Runtime.exceptionThrown' || event.method === 'Page.javascriptDialogOpening')
    return text;
  if (event.method === 'Runtime.consoleAPICalled' && event.params.type === 'error' &&
      /Aborted|RuntimeError|unreachable|exception thrown/i.test(text))
    return text;
  if (event.method === 'Log.entryAdded' && event.params.entry?.level === 'error' &&
      /Aborted|RuntimeError|unreachable/i.test(text))
    return text;
  return '';
}

function fatalBidiEvent(event) {
  if (event.method !== 'log.entryAdded')
    return '';

  const params = event.params || {};
  const text = params.text || params.args?.map(arg => arg.value ?? arg.text ?? '').join(' ') || '';
  if (text === 'unwind' || text === 'uncaught exception: unwind')
    return '';
  if (params.type === 'javascript' && params.level === 'error')
    return text || 'javascript error';
  if (params.level === 'error' && /Aborted|RuntimeError|unreachable|exception thrown/i.test(text))
    return text;
  return '';
}

function isTransientTargetNavigationError(error) {
  return /Inspected target navigated or closed|Execution context was destroyed|Cannot find context with specified id/.test(error?.message || '');
}

async function waitForHealthyPage(client) {
  const start = Date.now();
  let sawApp = false;
  let lastState = null;
  let healthySince = 0;

  while (Date.now() - start < timeoutMs) {
    for (const event of client.events) {
      const fatal = fatalEvent(event);
      if (fatal) {
        const recent = client.events.slice(-16).map(eventText).filter(Boolean).join(' | ');
        throw new Error(`${fatal}; recent=${recent}`);
      }
      if (/PLATFORM: WEB: Initialized successfully|INBE: Global app pointer set/.test(eventText(event)))
        sawApp = true;
    }

    let result;
    try {
      result = await client.send('Runtime.evaluate', {
        expression: `(() => {
        const renderer = ${JSON.stringify(renderer)};
        const canvas = document.querySelector('canvas');
        const status = document.querySelector('#status')?.textContent || '';
        if (/WebGL is disabled/.test(status)) return { ok: ${allowWebglDisabled ? 'true' : 'false'}, disabledWebgl: true, status };
        if (!canvas) return { ok: false, reason: 'missing canvas', status };
        const M = globalThis.Module;
        const asyncifyState = M && M.Asyncify && typeof M.Asyncify.state === 'number' ? M.Asyncify.state : 0;
        if (renderer === 'canvas') {
          const ctx = canvas.getContext('2d');
          const width = canvas.width || canvas.clientWidth;
          const height = canvas.height || canvas.clientHeight;
          return {
            ok: width > 0 && height > 0 && !!ctx && asyncifyState === 0,
            renderer,
            width,
            height,
            asyncifyState,
            loadingClass: document.querySelector('#loading-screen')?.className || '',
            moduleLoaded: !!M,
            appReady: !!(M && M.__inbeAppReady),
            runtimeReady: !!(M && M.__inbeRuntimeReady),
            moduleRenderer: M && M.__inbeRenderer,
            moduleStatus: (M && M.setStatus && M.setStatus.last && M.setStatus.last.text) || '',
            mainStarted: !!(M && M.__inbeAppReady) || /Global app pointer set/.test((M && M.__inbeLastLog) || ''),
            runDependencies: M && (typeof M.monitorRunDependencies === 'function') ? M.totalDependencies : undefined
          };
        }
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return { ok: false, reason: 'missing webgl', status };
        const width = gl.drawingBufferWidth;
        const height = gl.drawingBufferHeight;
        return {
          ok: width > 0 && height > 0 && asyncifyState === 0,
          renderer,
          width,
          height,
          asyncifyState,
          loadingClass: document.querySelector('#loading-screen')?.className || '',
          moduleLoaded: !!M,
          appReady: !!(M && M.__inbeAppReady),
          runtimeReady: !!(M && M.__inbeRuntimeReady),
          moduleStatus: (M && M.setStatus && M.setStatus.last && M.setStatus.last.text) || '',
          mainStarted: !!(M && M.__inbeAppReady) || !!(typeof Module !== 'undefined' && Module._main) || /Global app pointer set/.test((M && M.__inbeLastLog) || ''),
          runDependencies: M && (typeof M.monitorRunDependencies === 'function') ? M.totalDependencies : undefined
        };
      })()`,
        returnByValue: true
      });
    } catch (error) {
      if (!isTransientTargetNavigationError(error))
        throw error;
      lastState = { ok: false, reason: error.message };
      healthySince = 0;
      await delay(100);
      continue;
    }
    const value = result.result?.value;
    lastState = value;
    if ((sawApp || value?.appReady || value?.mainStarted) && value?.ok && value?.runtimeReady) {
      if (!healthySince)
        healthySince = Date.now();
      if (Date.now() - healthySince >= 1500)
      return value;
    } else {
      healthySince = 0;
    }
    await new Promise(resolveDelay => setTimeout(resolveDelay, 250));
  }

  const recent = client.events.slice(-12).map(eventText).filter(Boolean).join(' | ');
  const allExceptions = client.events
    .filter(e => e.method === 'Runtime.exceptionThrown')
    .map(eventText)
    .filter(Boolean)
    .join(' | ');
  throw new Error(`web app did not become healthy within ${timeoutMs}ms; state=${JSON.stringify(lastState)}; recent=${recent || '(none)'}; exceptions=${allExceptions || '(none)'}`);
}

async function waitForHealthyBidiPage(client, context) {
  const start = Date.now();
  let lastState = null;
  let healthySince = 0;

  while (Date.now() - start < timeoutMs) {
    for (const event of client.events) {
      const fatal = fatalBidiEvent(event);
      if (fatal)
        throw new Error(fatal);
    }

    const result = await client.send('script.evaluate', {
      target: { context },
      awaitPromise: false,
      resultOwnership: 'none',
      expression: `JSON.stringify((() => {
        const canvas = document.querySelector('canvas');
        const status = document.querySelector('#status')?.textContent || '';
        if (/WebGL is disabled/.test(status)) return { ok: ${allowWebglDisabled ? 'true' : 'false'}, disabledWebgl: true, status };
        if (!canvas) return { ok: false, reason: 'missing canvas', status };
        const boot = Array.from(document.querySelectorAll('script')).some(script => /index\\.js/.test(script.src || ''));
        const M = globalThis.Module;
        const asyncifyState = M && M.Asyncify && typeof M.Asyncify.state === 'number' ? M.Asyncify.state : 0;
        if (${JSON.stringify(renderer)} === 'canvas') {
          const ctx = canvas.getContext('2d');
          const width = canvas.width || canvas.clientWidth;
          const height = canvas.height || canvas.clientHeight;
          return {
            ok: width > 0 && height > 0 && !!ctx && boot && !!(M && M.__inbeRuntimeReady) && asyncifyState === 0,
            renderer: 'canvas',
            width,
            height,
            asyncifyState,
            boot,
            runtimeReady: !!(M && M.__inbeRuntimeReady),
            moduleRenderer: M && M.__inbeRenderer,
            hasOnboardingHook: !!(M && M._app_web_test_onboarding_state)
          };
        }
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return { ok: false, reason: 'missing webgl', status };
        const width = gl.drawingBufferWidth;
        const height = gl.drawingBufferHeight;
        return {
          ok: width > 0 && height > 0 && boot && !!(M && M.__inbeRuntimeReady) && asyncifyState === 0,
          renderer: 'raylib',
          width,
          height,
          asyncifyState,
          boot,
          runtimeReady: !!(M && M.__inbeRuntimeReady),
          hasOnboardingHook: !!(M && M._app_web_test_onboarding_state)
        };
      })())`
    });
    try {
      lastState = JSON.parse(result.result?.value || '{}');
    } catch {
      lastState = null;
    }
    if (lastState?.ok) {
      if (!healthySince)
        healthySince = Date.now();
      if (Date.now() - healthySince >= 1500)
        return lastState;
    } else {
      healthySince = 0;
    }
    await delay(250);
  }

  throw new Error(`Firefox web app did not become healthy within ${timeoutMs}ms; state=${JSON.stringify(lastState)}`);
}

async function waitForFirefoxBidi(browser, stderrLines) {
  const start = Date.now();
  let exited = false;
  const onExit = () => {
    exited = true;
  };
  browser.once('exit', onExit);

  try {
    while (Date.now() - start < timeoutMs) {
      if (exited) {
        const stderr = stderrLines.join('').trim();
        throw new Error(`Firefox exited before BiDi was ready${stderr ? `; firefox stderr: ${stderr.slice(-4000)}` : ''}`);
      }

      const stderr = stderrLines.join('');
      const match = stderr.match(/WebDriver BiDi listening on (ws:\/\/[^\s]+)/);
      if (match)
        return match[1].replace(/\/?$/, '/session');

      await delay(50);
    }
  } finally {
    browser.off('exit', onExit);
  }

  const stderr = stderrLines.join('').trim();
  throw new Error(`timed out waiting for Firefox BiDi${stderr ? `; firefox stderr: ${stderr.slice(-4000)}` : ''}`);
}

function writeFirefoxPrefs() {
  writeFileSync(join(userDataDir, 'user.js'), [
    'user_pref("browser.shell.checkDefaultBrowser", false);',
    'user_pref("browser.tabs.warnOnClose", false);',
    'user_pref("browser.warnOnQuit", false);',
    'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
    'user_pref("dom.webgpu.enabled", false);',
    'user_pref("gfx.webrender.software", true);',
    'user_pref("media.autoplay.default", 0);',
    'user_pref("privacy.fingerprintingProtection", false);',
    'user_pref("privacy.resistFingerprinting", false);',
    'user_pref("webgl.disabled", false);',
    'user_pref("webgl.disable-fail-if-major-performance-caveat", false);',
    'user_pref("webgl.enable-webgl2", true);',
    'user_pref("webgl.force-enabled", true);',
    ''
  ].join('\n'));
}

async function waitForStorageIdle(client) {
  const start = Date.now();
  let lastState = null;

  while (Date.now() - start < timeoutMs) {
    const result = await client.send('Runtime.evaluate', {
      expression: `(() => ({
        syncing: !!Module.__inbeStorageSyncing,
        pending: !!Module.__inbeStorageSyncPending,
        timer: !!Module.__inbeStorageSyncTimer
      }))()`,
      returnByValue: true
    });
    lastState = result.result?.value;
    if (lastState && !lastState.syncing && !lastState.pending && !lastState.timer)
      return;
    await new Promise(resolveDelay => setTimeout(resolveDelay, 50));
  }

  throw new Error(`IDBFS sync did not finish within ${timeoutMs}ms; state=${JSON.stringify(lastState)}`);
}

async function waitForStorageIdleBidi(client, context) {
  const start = Date.now();
  let lastState = null;

  while (Date.now() - start < timeoutMs) {
    const result = await client.send('script.evaluate', {
      target: { context },
      awaitPromise: false,
      resultOwnership: 'none',
      expression: "JSON.stringify((() => ({ syncing: !!Module.__inbeStorageSyncing, pending: !!Module.__inbeStorageSyncPending, timer: !!Module.__inbeStorageSyncTimer }))())"
    });
    try {
      lastState = JSON.parse(result.result?.value || '{}');
    } catch {
      lastState = null;
    }
    if (lastState && !lastState.syncing && !lastState.pending && !lastState.timer)
      return;
    await delay(50);
  }

  throw new Error('Firefox IDBFS sync did not finish within ' + timeoutMs + 'ms; state=' + JSON.stringify(lastState));
}

function bidiResultValue(result, label) {
  if (result.type === 'exception') {
    const exception = result.exceptionDetails?.text ||
      result.exceptionDetails?.exception?.value ||
      result.exceptionDetails?.exception?.description ||
      JSON.stringify(result.exceptionDetails || result);
    throw new Error(`${label} threw in Firefox: ${exception}`);
  }
  if (!result.result || !Object.hasOwn(result.result, 'value'))
    throw new Error(`${label} did not return a value in Firefox: ${JSON.stringify(result).slice(0, 1000)}`);
  return result.result.value;
}

function bidiJsonResult(result, label) {
  const value = bidiResultValue(result, label);
  try {
    return JSON.parse(value || '{}');
  } catch (error) {
    throw new Error(`${label} returned invalid JSON in Firefox: ${JSON.stringify(value)}; ${error.message}`);
  }
}

function wasmHookEvalHelper() {
  return `
    async function callWasmHook(name, args = []) {
      const M = globalThis.Module;
      const fn = M && M['_' + name];
      async function waitForAsyncifyIdle(phase) {
        const idleDeadline = Date.now() + 5000;
        while (true) {
          const state = M.Asyncify ? M.Asyncify.state : 0;
          // A suspended call can have normal state while its saved stack remains live.
          if (state === 0 && !M.Asyncify?.currData)
            return;
          if (Date.now() > idleDeadline)
            throw new Error(name + ' Asyncify ' + phase + ' wait timed out; state=' + state);
          await new Promise(resolve => setTimeout(resolve, 5));
        }
      }
      if (typeof fn !== 'function')
        throw new Error('missing ' + name + ' hook');
      await waitForAsyncifyIdle('idle');
      let result = fn.apply(M, args);
      if (M.Asyncify?.currData && typeof M.Asyncify.whenDone === 'function') {
        const done = M.Asyncify.whenDone();
        const timeout = new Promise((_, reject) =>
          setTimeout(() => reject(new Error(name + ' Asyncify wait timed out')), 5000));
        result = await Promise.race([done, timeout]);
      }
      await waitForAsyncifyIdle('settle');
      return result;
    }
  `;
}

async function verifyReloadPersistence(client) {
  await waitForStorageIdle(client);
  const marker = `web-smoke-${Date.now()}`;
  const flush = await client.send('Runtime.evaluate', {
    expression: `(async () => {
      try { FS.mkdir('/home/inbe'); } catch (e) {}
      FS.writeFile('/home/inbe/web-smoke-persist.txt', ${JSON.stringify(marker)});
      if (typeof Module.__inbeFlushStorageSync !== 'function')
        throw new Error('missing immediate storage flush helper');
      return await Module.__inbeFlushStorageSync(true);
    })()`,
    awaitPromise: true,
    returnByValue: true
  });
  if (!flush.result?.value)
    throw new Error('IDBFS flush failed before reload persistence check');
  await waitForStorageIdle(client);
  await client.send('Page.reload', { ignoreCache: true });
  await waitForHealthyPage(client);

  const result = await client.send('Runtime.evaluate', {
    expression: `(() => {
      try {
        return FS.readFile('/home/inbe/web-smoke-persist.txt', { encoding: 'utf8' });
      } catch (e) {
        return '';
      }
    })()`,
    returnByValue: true
  });
  if (result.result?.value !== marker)
    throw new Error(`IDBFS reload persistence failed; got=${JSON.stringify(result.result?.value)}`);
}

async function verifyAppSettingsReloadPersistence(client) {
  await waitForStorageIdle(client);
  let ok = await pageJson(client, `(async () => { ${wasmHookEvalHelper()} await callWasmHook('app_web_test_save_onboarding_state'); await Module.__inbeFlushStorageSync(true); return true; })()`, true);
  if (!ok)
    throw new Error('failed to invoke app settings save test hook');
  await waitForStorageIdle(client);
  await client.send('Page.reload', { ignoreCache: true });
  await waitForHealthyPage(client);

  ok = await pageJson(client, "(() => typeof Module._app_web_test_onboarding_state === 'function' && Module._app_web_test_onboarding_state() === 1)()");
  if (!ok)
    throw new Error('app settings did not persist across reload');
}

async function verifyLanguageRouteDoesNotOverrideSavedOnboarding(client, port) {
  await waitForStorageIdle(client);
  await client.send('Page.navigate', { url: `http://127.0.0.1:${port}/index.html#/language` });
  await waitForHealthyPage(client);
  await waitForStorageIdle(client);

  const result = await client.send('Runtime.evaluate', {
    expression: `(() => ({
      hash: location.hash || '',
      onboarding: typeof Module._app_web_test_onboarding_state === 'function'
        ? Module._app_web_test_onboarding_state()
        : -1
    }))()`,
    returnByValue: true
  });
  const value = result.result?.value || {};
  if (value.onboarding !== 1)
    throw new Error(`saved onboarding state missing before language route check; state=${JSON.stringify(value)}`);
  if (value.hash === '#/language')
    throw new Error('saved onboarding state was overridden by stale #/language route');
}

async function verifySyncKeyImport(client) {
  await waitForStorageIdle(client);
  let state = await pageJson(client, `(async () => JSON.stringify(await (async () => {
      if (typeof Module._app_web_test_import_sync_key !== 'function')
        return { ok: false, code: -99 };
      if (typeof Module._app_web_test_sync_key_state !== 'function')
        return { ok: false, code: -98 };
      ${wasmHookEvalHelper()}
      await callWasmHook('app_web_test_import_sync_key');
      const deadline = Date.now() + ${timeoutMs};
      let code = 0;
      while (Date.now() < deadline) {
        code = Module._app_web_test_sync_key_state();
        if (code !== 0)
          return { ok: code === 1, code };
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      return { ok: false, code };
    })()))()`, true);
  if (!state.ok)
    throw new Error(`web sync key import hook failed; code=${state.code}`);
  const flush = await client.send('Runtime.evaluate', {
    expression: "(async () => await Module.__inbeFlushStorageSync(true))()",
    awaitPromise: true,
    returnByValue: true
  });
  if (!flush.result?.value)
    throw new Error('IDBFS flush failed after web sync key import hook');
  await waitForStorageIdle(client);
  state = await pageJson(client, "(() => JSON.stringify({ code: typeof Module._app_web_test_sync_key_state === 'function' ? Module._app_web_test_sync_key_state() : -99 }))()");
  if (state.code !== 1)
    throw new Error(`web sync key import did not save account settings; code=${state.code}`);
}

async function verifyAppSettingsReloadPersistenceBidi(client, context) {
  await waitForStorageIdleBidi(client, context);
  let result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: true,
    resultOwnership: 'none',
    expression: `(async () => JSON.stringify(await (async () => { ${wasmHookEvalHelper()} try { await callWasmHook('app_web_test_save_onboarding_state'); } catch (error) { return { ok: false, reason: String(error && error.message || error) }; } await Module.__inbeFlushStorageSync(true); return { ok: Module._app_web_test_onboarding_state && Module._app_web_test_onboarding_state() === 1 }; })()))()`
  });
  const state = JSON.parse(result.result?.value || '{}');
  if (!state.ok)
    throw new Error(state.reason || 'failed to invoke Firefox app settings save test hook or immediate readback failed');
  await waitForStorageIdleBidi(client, context);
  await client.send('browsingContext.reload', { context, wait: 'complete' });
  await waitForHealthyBidiPage(client, context);

  result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: false,
    resultOwnership: 'none',
    expression: "JSON.stringify((() => ({ ok: typeof Module._app_web_test_onboarding_state === 'function' && Module._app_web_test_onboarding_state() === 1 }))())"
  });
  state = JSON.parse(result.result?.value || '{}');
  if (!state.ok)
    throw new Error('Firefox app settings did not persist across reload');
}

async function verifyAppSettingsImmediateBidi(client, context) {
  await waitForStorageIdleBidi(client, context);
  const result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: true,
    resultOwnership: 'none',
    expression: `(async () => JSON.stringify(await (async () => { ${wasmHookEvalHelper()} try { await callWasmHook('app_web_test_save_onboarding_state'); } catch (error) { return { ok: false, reason: String(error && error.message || error) }; } await Module.__inbeFlushStorageSync(true); return { ok: Module._app_web_test_onboarding_state && Module._app_web_test_onboarding_state() === 1 }; })()))()`
  });
  let state = JSON.parse(result.result?.value || '{}');
  if (!state.ok)
    throw new Error(state.reason || 'Firefox app settings immediate save/readback failed');
  await waitForStorageIdleBidi(client, context);
}

async function verifySyncKeyImportBidi(client, context) {
  await waitForStorageIdleBidi(client, context);
  let result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: true,
    resultOwnership: 'none',
    expression: `(async () => JSON.stringify(await (async () => {
        if (typeof Module._app_web_test_import_sync_key !== 'function')
          return { ok: false, code: -99 };
        if (typeof Module._app_web_test_sync_key_state !== 'function')
          return { ok: false, code: -98 };
        try {
          ${wasmHookEvalHelper()}
          await callWasmHook('app_web_test_import_sync_key');
        } catch (error) {
          return { ok: false, code: -95, phase: 'import', error: String(error && error.stack || error) };
        }
        const deadline = Date.now() + ${timeoutMs};
        let code = 0;
        while (Date.now() < deadline) {
          try {
            code = Module._app_web_test_sync_key_state();
          } catch (error) {
            return { ok: false, code: -94, phase: 'state', error: String(error && error.stack || error) };
          }
          if (code !== 0)
            break;
          await new Promise(resolve => setTimeout(resolve, 50));
        }
        if (code !== 1)
          return { ok: false, code };
        if (typeof Module.__inbeFlushStorageSync !== 'function')
          return { ok: false, code: -97 };
        if (!await Module.__inbeFlushStorageSync(true))
          return { ok: false, code: -96 };
        try {
          code = Module._app_web_test_sync_key_state();
        } catch (error) {
          return { ok: false, code: -93, phase: 'readback', error: String(error && error.stack || error) };
        }
        return { ok: code === 1, code };
      })()))()`
  });
  let state = bidiJsonResult(result, 'sync key hook availability check');
  if (!state.ok)
    throw new Error(`Firefox web sync key import hook failed; code=${state.code}; phase=${state.phase || 'unknown'}; error=${state.error || ''}`);
  await waitForStorageIdleBidi(client, context);
  result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: false,
    resultOwnership: 'none',
    expression: "JSON.stringify((() => { const code = typeof Module._app_web_test_sync_key_state === 'function' ? Module._app_web_test_sync_key_state() : -99; return { ok: code === 1, code }; })())"
  });
  state = bidiJsonResult(result, 'sync key settings readback');
  if (!state.ok)
    throw new Error(`Firefox web sync key import did not save account settings; code=${state.code}`);
}

async function pageJson(client, expression, awaitPromise = false) {
  const result = await client.send('Runtime.evaluate', {
    expression,
    awaitPromise,
    returnByValue: true
  });
  if (result.exceptionDetails) {
    const text = result.exceptionDetails.exception?.description ||
      result.exceptionDetails.text || 'unknown page evaluation error';
    throw new Error(`page evaluation failed: ${text}`);
  }
  const value = result.result?.value;
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {}
  }
  return value;
}

// A route change fades over a fraction of a second and ignores input
// meanwhile, so a click must wait for the fade to finish. The app reports
// whether one is running.
async function waitRouteTransition(client) {
  await waitAnimationFrames(client, 2);
  for (let attempt = 0; attempt < 150; attempt++) {
    const active = await pageJson(client, `(() => JSON.stringify(
      typeof Module._app_web_test_route_transition_active === 'function' ?
        Module._app_web_test_route_transition_active() : 0))()`);
    if (!active)
      return;
    await delay(20);
  }
  throw new Error('route transition did not finish');
}

async function waitAnimationFrames(client, frameCount = 3) {
  const result = await pageJson(client, `(async () => JSON.stringify(await new Promise(resolve => {
    let frames = 0;
    function tick() {
      frames++;
      if (frames >= ${frameCount}) resolve({ ok: true, frames });
      else requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    setTimeout(() => resolve({ ok: false, reason: 'timeout', frames }), 5000);
  })))()`, true);
  if (!result?.ok)
    throw new Error(`animation frames stalled: ${JSON.stringify(result)}`);
}

async function dispatchCanvasClick(client, x, y) {
  await waitRouteTransition(client);
  await client.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x,
    y
  });
  await client.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x,
    y,
    button: 'left',
    clickCount: 1
  });
  await delay(50);
  await client.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x,
    y,
    button: 'left',
    clickCount: 1
  });
}

async function firstRunGuideButtonTarget(client, kind) {
  const suffix = kind === 'close' ? 'close' : 'next';
  const target = await pageJson(client, `(() => JSON.stringify((() => {
    const canvas = Module.canvas || document.querySelector('canvas');
    if (!canvas)
      return { ok: false, reason: 'missing canvas' };
    const xFn = Module._app_web_test_first_run_guide_${suffix}_x;
    const yFn = Module._app_web_test_first_run_guide_${suffix}_y;
    if (typeof xFn !== 'function' || typeof yFn !== 'function')
      return { ok: false, reason: 'missing guide ${suffix} hook' };
    const rawX = xFn();
    const rawY = yFn();
    const rect = canvas.getBoundingClientRect();
    const logicalW = window.__kryCanvas && window.__kryCanvas.w ? window.__kryCanvas.w : rect.width;
    const logicalH = window.__kryCanvas && window.__kryCanvas.h ? window.__kryCanvas.h : rect.height;
    const x = rect.left + rawX * rect.width / Math.max(1, logicalW);
    const y = rect.top + rawY * rect.height / Math.max(1, logicalH);
    return {
      ok: rawX >= 0 && rawY >= 0 && x >= rect.left && y >= rect.top &&
          x <= rect.right && y <= rect.bottom,
      reason: 'invalid guide ${suffix} target',
      x,
      y,
      rawX,
      rawY,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
      logical: { width: logicalW, height: logicalH },
      canvas: { width: canvas.width, height: canvas.height }
    };
  })()))()`);
  if (!target?.ok)
    throw new Error(`${target?.reason || 'failed to compute guide click target'}; state=${JSON.stringify(target)}`);
  return target;
}

async function firstRunGuideState(client, requireDebug = true, requireActive = false) {
  const start = Date.now();
  let state = null;

  while (Date.now() - start < timeoutMs) {
    state = await pageJson(client, `(() => ({
      active: Module._app_web_test_first_run_guide_active(),
      step: Module._app_web_test_first_run_guide_step(),
      clipped: Module._app_web_test_first_run_guide_text_clipped()
    }))()`);
    if ((!requireActive || (state?.active === 1 && state?.step === 0)) &&
        (!requireDebug || state?.clipped !== -1))
      return state;
    await waitAnimationFrames(client, 1);
  }

  return state;
}

async function firstRunGuideActionAnchor(client) {
  return pageJson(client, `(() => {
    const canvas = Module.canvas || document.querySelector('canvas');
    const rect = canvas ? canvas.getBoundingClientRect() : { width: 0, height: 0 };
    const logicalW = window.__kryCanvas && window.__kryCanvas.w ? window.__kryCanvas.w : rect.width;
    const logicalH = window.__kryCanvas && window.__kryCanvas.h ? window.__kryCanvas.h : rect.height;
    return {
      x: Module._app_web_test_first_run_guide_anchor_x(),
      y: Module._app_web_test_first_run_guide_anchor_y(),
      width: Module._app_web_test_first_run_guide_anchor_w(),
      height: Module._app_web_test_first_run_guide_anchor_h(),
      logical: { width: logicalW, height: logicalH }
    };
  })()`);
}

async function verifyFirstRunGuideCanvasFlow(client) {
  if (renderer !== 'canvas')
    return;

  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 450, height: 800, deviceScaleFactor: 1, mobile: false
  });
  await waitAnimationFrames(client, 4);

  let state = await pageJson(client, `(async () => JSON.stringify(await (async () => {
    if (typeof Module._app_web_test_show_first_run_guide !== 'function')
      return { ok: false, reason: 'missing first-run guide show hook' };
    if (typeof Module._app_web_test_first_run_guide_active !== 'function' ||
        typeof Module._app_web_test_first_run_guide_step !== 'function' ||
        typeof Module._app_web_test_first_run_guide_text_clipped !== 'function' ||
        typeof Module._app_web_test_save_onboarding_state !== 'function')
      return { ok: false, reason: 'missing first-run guide state hooks' };
    ${wasmHookEvalHelper()}
    await callWasmHook('app_web_test_show_first_run_guide');
    await Module.__inbeFlushStorageSync(true);
    return { ok: true };
  })()))()`, true);
  if (state?.ok) {
    await waitAnimationFrames(client, 2);
    state = { ok: true, ...(await firstRunGuideState(client, true, true)) };
  }
  if (!state?.ok || state.active !== 1 || state.step !== 0)
    throw new Error(`failed to show Spanish first-run guide: ${JSON.stringify(state)}`);
  if (state.clipped === -1)
    state = { ok: true, ...(await firstRunGuideState(client)) };
  if (state.clipped !== 0)
    throw new Error(`Spanish first-run guide text is clipped: ${JSON.stringify(state)}`);

  let previousTarget = null;
  for (let expected = 1; expected < 3; expected++) {
    let target;
    for (let attempt = 0; attempt < 30; attempt++) {
      target = await firstRunGuideButtonTarget(client, 'next');
      if (!previousTarget || target.rawY !== previousTarget.rawY)
        break;
      await waitAnimationFrames(client, 2);
    }
    if (previousTarget && target.rawY === previousTarget.rawY)
      throw new Error(`guide Next layout did not advance at 1:1 scale: ${JSON.stringify({ expected, target })}`);
    if (target.rect.width !== 450 || target.rect.height !== 800 ||
        target.canvas.width !== 450 || target.canvas.height !== 800)
      throw new Error(`guide canvas is not 1:1 at 450x800: ${JSON.stringify(target)}`);
    await dispatchCanvasClick(client, target.x, target.y);
    await waitRouteTransition(client);
    state = await firstRunGuideState(client, false);
    if (state.active !== 1 || state.step !== expected || state.clipped !== 0)
      throw new Error(`guide Next missed or clipped at 1:1 scale: ${JSON.stringify({ expected, state, target })}`);
    previousTarget = target;
  }

  state = await pageJson(client, `(async () => JSON.stringify(await (async () => {
    ${wasmHookEvalHelper()}
    await callWasmHook('app_web_test_save_onboarding_state');
    await Module.__inbeFlushStorageSync(true);
    return {
      active: Module._app_web_test_first_run_guide_active(),
      step: Module._app_web_test_first_run_guide_step(),
      onboarding: Module._app_web_test_onboarding_state && Module._app_web_test_onboarding_state()
    };
  })()))()`, true);
  if (state.onboarding !== 1)
    throw new Error(`guide dismissed state did not persist before reload: ${JSON.stringify(state)}`);

  await waitForStorageIdle(client);
  await client.send('Page.reload', { ignoreCache: true });
  await waitForHealthyPage(client);
  await waitAnimationFrames(client, 3);
  state = await pageJson(client, `(() => ({
    active: Module._app_web_test_first_run_guide_active(),
    step: Module._app_web_test_first_run_guide_step(),
    onboarding: Module._app_web_test_onboarding_state && Module._app_web_test_onboarding_state()
  }))()`);
  if (state.active !== 0 || state.onboarding !== 1)
    throw new Error(`guide reopened after reload: ${JSON.stringify(state)}`);
  await client.send('Emulation.clearDeviceMetricsOverride');
  await waitAnimationFrames(client, 4);
}

function installHabitsLifecycleWatchExpression() {
  return `(() => {
    window.__inbeSmokeLifecycle = { beforeunload: 0, pagehide: 0, visibilityHidden: 0 };
    if (!window.__inbeSmokeLifecycleInstalled) {
      window.__inbeSmokeLifecycleInstalled = true;
      window.addEventListener('beforeunload', () => { window.__inbeSmokeLifecycle.beforeunload++; });
      window.addEventListener('pagehide', () => { window.__inbeSmokeLifecycle.pagehide++; });
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden')
          window.__inbeSmokeLifecycle.visibilityHidden++;
      });
    }
    return true;
  })()`;
}

function startHabitsFrameProbeExpression(frameCount) {
  return `(() => {
    const canvas = document.querySelector('canvas');
    const frames = ${frameCount};
    window.__inbeSmokeFrameProbe = new Promise(resolve => {
      const samples = [];
      let frame = 0;
      function sample() {
        const result = { frame, ok: false, bright: 0, total: 0, reason: '' };
        try {
          if (!canvas) {
            result.reason = 'missing canvas';
          } else if (canvas.clientWidth <= 0 || canvas.clientHeight <= 0) {
            result.reason = 'zero-size canvas';
          } else {
            const w = 32;
            const h = 32;
            const copy = document.createElement('canvas');
            copy.width = w;
            copy.height = h;
            const ctx = copy.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(canvas, 0, 0, w, h);
            const data = ctx.getImageData(0, 0, w, h).data;
            let bright = 0;
            let alpha = 0;
            for (let i = 0; i < data.length; i += 4) {
              if (data[i + 3] > 0)
                alpha++;
              if (data[i + 3] > 0 && data[i] + data[i + 1] + data[i + 2] > 18)
                bright++;
            }
            result.bright = bright;
            result.alpha = alpha;
            result.total = w * h;
            result.ok = bright > result.total * 0.05;
            if (!result.ok)
              result.reason = 'blank or black canvas frame';
          }
        } catch (error) {
          result.reason = error && error.message ? error.message : String(error);
        }
        samples.push(result);
        frame++;
        if (frame >= frames) {
          const bad = samples.find(sample => !sample.ok);
          resolve({ ok: !bad, bad, samples: samples.slice(0, 3).concat(samples.slice(-3)) });
        } else {
          requestAnimationFrame(sample);
        }
      }
      requestAnimationFrame(sample);
    });
    return true;
  })()`;
}

async function openHabitsOverview(client) {
  const state = await pageJson(client, `(async () => JSON.stringify(await (async () => {
    ${wasmHookEvalHelper()}
    if (typeof Module._app_web_test_save_onboarding_state === 'function') {
      await callWasmHook('app_web_test_save_onboarding_state');
    }
    if (typeof Module._app_web_extension_open_habits !== 'function')
      return { ok: false, reason: 'missing habits launch hook' };
    await callWasmHook('app_web_extension_open_habits');
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return {
      ok: typeof Module._app_web_test_habits_click_x === 'function' &&
          typeof Module._app_web_test_habits_click_y === 'function',
      reason: 'missing habits click hook'
    };
  })()))()`, true);
  if (!state?.ok)
    throw new Error(state?.reason || 'failed to open habits overview');
}

async function habitsClickTarget(client) {
  const target = await pageJson(client, `(() => JSON.stringify((() => {
    const canvas = Module.canvas || document.querySelector('canvas');
    if (!canvas)
      return { ok: false, reason: 'missing canvas' };
    const rect = canvas.getBoundingClientRect();
    const rawX = Module._app_web_test_habits_click_x();
    const rawY = Module._app_web_test_habits_click_y();
    const basisW = canvas.width || rect.width || 1;
    const basisH = canvas.height || rect.height || 1;
    const x = rect.left + rawX * rect.width / basisW;
    const y = rect.top + rawY * rect.height / basisH;
    return {
      ok: rawX >= 0 && rawY >= 0 && x >= rect.left && y >= rect.top &&
          x <= rect.right && y <= rect.bottom,
      reason: 'invalid habits click target',
      x,
      y,
      rawX,
      rawY,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
      canvas: { width: canvas.width, height: canvas.height }
    };
  })()))()`);
  if (!target?.ok)
    throw new Error(`${target?.reason || 'failed to compute habits click target'}; state=${JSON.stringify(target)}`);
  return target;
}

async function openPracticeHome(client) {
  const state = await pageJson(client, `(async () => JSON.stringify(await (async () => {
    if (typeof Module._app_web_test_show_practice_home !== 'function')
      return { ok: false, reason: 'missing practice home hook' };
    if (typeof Module._app_web_test_screen !== 'function' ||
        typeof Module._app_web_test_practice_start_click_x !== 'function' ||
        typeof Module._app_web_test_practice_start_click_y !== 'function')
      return { ok: false, reason: 'missing practice start hooks' };
    ${wasmHookEvalHelper()}
    await callWasmHook('app_web_test_show_practice_home');
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return { ok: true, screen: Module._app_web_test_screen() };
  })()))()`, true);
  if (!state?.ok)
    throw new Error(state?.reason || 'failed to open practice home');
}

async function practiceStartClickTarget(client) {
  const target = await pageJson(client, `(() => JSON.stringify((() => {
    const canvas = Module.canvas || document.querySelector('canvas');
    if (!canvas)
      return { ok: false, reason: 'missing canvas' };
    const rect = canvas.getBoundingClientRect();
    const rawX = Module._app_web_test_practice_start_click_x();
    const rawY = Module._app_web_test_practice_start_click_y();
    const basisW = canvas.width || rect.width || 1;
    const basisH = canvas.height || rect.height || 1;
    const x = rect.left + rawX * rect.width / basisW;
    const y = rect.top + rawY * rect.height / basisH;
    return {
      ok: rawX >= 0 && rawY >= 0 && x >= rect.left && y >= rect.top &&
          x <= rect.right && y <= rect.bottom,
      reason: 'invalid practice start click target',
      x,
      y,
      rawX,
      rawY,
      rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
      canvas: { width: canvas.width, height: canvas.height }
    };
  })()))()`);
  if (!target?.ok)
    throw new Error(`${target?.reason || 'failed to compute practice start target'}; state=${JSON.stringify(target)}`);
  return target;
}

async function verifyPracticeCarouselSwipe(client) {
  await openPracticeHome(client);
  const target = await practiceStartClickTarget(client);
  const selected = () => pageJson(client, 'Module._app_web_test_practice_selected()');
  const initial = await selected();
  async function waitForSelectionChange(previous) {
    const deadline = Date.now() + 500;
    let current = await selected();
    while (current === previous && Date.now() < deadline) {
      await delay(50);
      current = await selected();
    }
    return current;
  }
  const x = target.rect.left + target.rect.width / 2;
  const y = target.rect.top + (target.y - target.rect.top) * 0.4;
  const distance = target.rect.width * 0.4;
  async function drag(dx, dy) {
    const startX = x - dx / 2;
    const startY = y - dy / 2;
    await client.send('Input.dispatchMouseEvent', {
      type: 'mousePressed', x: startX, y: startY, button: 'left', clickCount: 1
    });
    await waitAnimationFrames(client, 2);
    for (let step = 1; step <= 6; step++) {
      await client.send('Input.dispatchMouseEvent', {
        type: 'mouseMoved', x: startX + dx * step / 6, y: startY + dy * step / 6,
        button: 'left', buttons: 1
      });
      await waitAnimationFrames(client, 1);
    }
    await client.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased', x: startX + dx, y: startY + dy, button: 'left', clickCount: 1
    });
    await waitAnimationFrames(client, 3);
  }
  async function swipeToNext(dx, previous, label) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      await drag(dx, 0);
      const current = await waitForSelectionChange(previous);
      if (current !== previous) return current;
    }
    throw new Error(`${label} did not change practice after three gestures (selected=${previous})`);
  }
  const first = await swipeToNext(-distance, initial, 'left swipe');
  if (await swipeToNext(distance, first, 'right swipe') !== initial)
    throw new Error('right swipe did not return to practice');
  await drag(0, distance / 2);
  if (await selected() !== initial) throw new Error('vertical drag changed practice');
  await dispatchCanvasClick(client, x, y);
  await waitAnimationFrames(client, 3);
  if (await selected() !== initial) throw new Error('artwork tap changed practice');
  const visited = new Set([initial]);
  let previous = initial;
  for (let i = 0; i < 4; i++) {
    const current = await swipeToNext(-distance, previous, `carousel swipe ${i + 1}`);
    if (i < 3 && visited.has(current))
      throw new Error(`carousel repeated practice early on swipe ${i + 1}: ${current}`);
    if (i === 3 && current !== initial)
      throw new Error(`carousel did not wrap after four swipes (selected=${current}, initial=${initial})`);
    visited.add(current);
    previous = current;
  }
}

async function verifyPracticeStartClick(client) {
  await openPracticeHome(client);
  const target = await practiceStartClickTarget(client);
  await dispatchCanvasClick(client, target.x, target.y);
  await waitAnimationFrames(client, 3);
  const state = await pageJson(client, `(() => ({
    screen: Module._app_web_test_screen && Module._app_web_test_screen(),
    ready: !!Module.__inbeRuntimeReady,
    loadingClass: document.querySelector('#loading-screen')?.className || ''
  }))()`);
  if (state.screen === 0 || state.screen === -1 || !state.ready)
    throw new Error(`practice start click did not start a session: ${JSON.stringify(state)}`);
  if (!/is-hidden/.test(state.loadingClass))
    throw new Error(`practice start click showed loading overlay: ${JSON.stringify(state.loadingClass)}`);
}

async function verifyPracticeCompletionPersistence(client) {
  await waitForStorageIdle(client);
  const result = await pageJson(client, `(async () => {
    ${wasmHookEvalHelper()}
    await callWasmHook('app_web_test_complete_practice');
    const persisted = !!Module._app_web_test_completed_practice_persisted();
    const flushed = await Module.__inbeFlushStorageSync(true);
    return { persisted, flushed, stage: Module._app_web_test_completion_stage(),
      storageError: Module.__inbeStorageSyncLastError };
  })()`, true);
  if (!result.persisted || !result.flushed)
    throw new Error('practice pause/resume/completion failed: ' + JSON.stringify(result));
  await waitForStorageIdle(client);
  await client.send('Page.reload', { ignoreCache: true });
  await waitForHealthyPage(client);
  const persisted = await pageJson(client,
    'Module._app_web_test_completed_practice_persisted() === 1');
  if (!persisted) throw new Error('completed practice mood did not survive reload');
}

function readPngBrightness(base64) {
  const png = Buffer.from(base64, 'base64');
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (png.length < signature.length || !png.subarray(0, signature.length).equals(signature))
    throw new Error('screenshot is not a PNG');

  let offset = signature.length;
  let width = 0;
  let height = 0;
  let colorType = -1;
  const idat = [];
  while (offset + 8 <= png.length) {
    const length = png.readUInt32BE(offset);
    const type = png.toString('ascii', offset + 4, offset + 8);
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    if (dataEnd + 4 > png.length)
      throw new Error('truncated PNG chunk');
    if (type === 'IHDR') {
      width = png.readUInt32BE(dataStart);
      height = png.readUInt32BE(dataStart + 4);
      const bitDepth = png[dataStart + 8];
      colorType = png[dataStart + 9];
      if (bitDepth !== 8 || (colorType !== 2 && colorType !== 6))
        throw new Error(`unsupported PNG format bitDepth=${bitDepth} colorType=${colorType}`);
    } else if (type === 'IDAT') {
      idat.push(png.subarray(dataStart, dataEnd));
    } else if (type === 'IEND') {
      break;
    }
    offset = dataEnd + 4;
  }
  if (width <= 0 || height <= 0 || !idat.length)
    throw new Error('PNG is missing IHDR/IDAT data');

  const bpp = colorType === 6 ? 4 : 3;
  const stride = width * bpp;
  const inflated = inflateSync(Buffer.concat(idat));
  let input = 0;
  let bright = 0;
  const total = width * height;
  let previous = Buffer.alloc(stride);
  let current = Buffer.alloc(stride);

  for (let y = 0; y < height; y++) {
    const filter = inflated[input++];
    for (let x = 0; x < stride; x++) {
      const raw = inflated[input++];
      const left = x >= bpp ? current[x - bpp] : 0;
      const up = previous[x] || 0;
      const upLeft = x >= bpp ? previous[x - bpp] : 0;
      let value = raw;
      if (filter === 1) {
        value += left;
      } else if (filter === 2) {
        value += up;
      } else if (filter === 3) {
        value += Math.floor((left + up) / 2);
      } else if (filter === 4) {
        const p = left + up - upLeft;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - upLeft);
        value += pa <= pb && pa <= pc ? left : (pb <= pc ? up : upLeft);
      } else if (filter !== 0) {
        throw new Error(`unsupported PNG filter ${filter}`);
      }
      current[x] = value & 255;
    }
    for (let x = 0; x < width; x++) {
      const pixel = x * bpp;
      if (current[pixel] + current[pixel + 1] + current[pixel + 2] > 18)
        bright++;
    }
    const swap = previous;
    previous = current;
    current = swap;
  }

  return { bright, total, width, height, ok: bright > total * 0.05 };
}

async function captureScreenshotProbe(client, samples) {
  const frames = [];
  for (let frame = 0; frame < samples; frame++) {
    const screenshot = await client.send('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true
    });
    const state = readPngBrightness(screenshot.data);
    frames.push({ frame, ...state });
    if (!state.ok)
      return { ok: false, bad: frames[frames.length - 1], samples: frames.slice(0, 3).concat(frames.slice(-3)) };
    await delay(25);
  }
  return { ok: true, samples: frames.slice(0, 3).concat(frames.slice(-3)) };
}

async function verifyHabitsClickDoesNotReload(client) {
  await waitForStorageIdle(client);
  await openHabitsOverview(client);
  await verifyRenderingLive(client);
  await client.send('Page.setLifecycleEventsEnabled', { enabled: true }).catch(() => {});
  await pageJson(client, installHabitsLifecycleWatchExpression());
  const target = await habitsClickTarget(client);
  const marker = `habits-click-${Date.now()}`;
  const before = await pageJson(client, `(() => {
    window.__inbeSmokeModule = Module;
    Module.__inbeSmokeMarker = ${JSON.stringify(marker)};
    return {
      href: location.href,
      ready: !!Module.__inbeRuntimeReady,
      loadingClass: document.querySelector('#loading-screen')?.className || '',
      lifecycle: window.__inbeSmokeLifecycle
    };
  })()`);
  const firstEvent = client.events.length;
  if (renderer === 'canvas')
    await pageJson(client, startHabitsFrameProbeExpression(30));

  await client.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: target.x,
    y: target.y
  });
  await client.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: target.x,
    y: target.y,
    button: 'left',
    clickCount: 1
  });
  await delay(50);
  await client.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: target.x,
    y: target.y,
    button: 'left',
    clickCount: 1
  });

  const probe = renderer === 'canvas'
    ? await pageJson(client, 'window.__inbeSmokeFrameProbe.then(value => JSON.stringify(value))', true)
    : await captureScreenshotProbe(client, 12);
  await delay(250);
  const after = await pageJson(client, `(() => ({
    href: location.href,
    ready: !!Module.__inbeRuntimeReady,
    sameModule: window.__inbeSmokeModule === Module,
    sameMarker: Module.__inbeSmokeMarker === ${JSON.stringify(marker)},
    loadingClass: document.querySelector('#loading-screen')?.className || '',
    lifecycle: window.__inbeSmokeLifecycle
  }))()`);
  const events = client.events.slice(firstEvent);
  const navigationEvents = events
    .filter(event => event.method === 'Page.frameNavigated' ||
      event.method === 'Page.frameStartedNavigating' ||
      event.method === 'Page.domContentEventFired' ||
      event.method === 'Page.loadEventFired' ||
      (event.method === 'Page.lifecycleEvent' && event.params?.name === 'init'))
    .map(event => event.method + (event.params?.name ? `:${event.params.name}` : ''));

  if (navigationEvents.length)
    throw new Error(`habits click triggered page navigation/reload events: ${navigationEvents.join(', ')}`);
  if (before.href !== after.href)
    throw new Error(`habits click changed location: before=${before.href} after=${after.href}`);
  if (!after.ready || !after.sameModule || !after.sameMarker)
    throw new Error(`habits click replaced or reset the app runtime: ${JSON.stringify(after)}`);
  if ((after.lifecycle?.beforeunload || 0) > 0 || (after.lifecycle?.pagehide || 0) > 0)
    throw new Error(`habits click fired unload lifecycle handlers: ${JSON.stringify(after.lifecycle)}`);
  if (!/is-hidden/.test(after.loadingClass))
    throw new Error(`habits click showed loading overlay: ${JSON.stringify(after.loadingClass)}`);
  if (!probe?.ok)
    throw new Error(`habits click produced a blank canvas frame: ${JSON.stringify(probe?.bad || probe)}`);
}

let chrome;
let client;
let failure;

/* Proves the page is actually rendering: a canvas with nonzero size, a live
 * WebGL context, and a cycling requestAnimationFrame loop. Catches "boots to
 * a black screen" that console-error checks cannot see. Runs in the page, so
 * the same expression serves both the CDP and the Firefox BiDi paths. */
function renderLiveExpression(rendererKind) {
  return `(async () => JSON.stringify(await (async () => {
  const canvas = document.querySelector('canvas');
  if (!canvas)
    return { ok: false, reason: 'no canvas element' };
  if (canvas.clientWidth === 0 || canvas.clientHeight === 0)
    return { ok: false, reason: 'canvas has zero display size' };
  const renderer = ${JSON.stringify(rendererKind)};
  let ctx = null;
  if (renderer === 'canvas') {
    ctx = canvas.getContext('2d');
    if (!ctx)
      return { ok: false, reason: 'no Canvas2D context' };
  } else {
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl)
      return { ok: false, reason: 'no WebGL context' };
    if (!gl.getParameter(gl.VERSION))
      return { ok: false, reason: 'WebGL context unresponsive' };
  }
  let frames = 0;
  await new Promise(resolve => {
    const tick = () => {
      frames++;
      if (frames >= 3)
        resolve();
      else
        requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    setTimeout(resolve, 5000);
  });
  if (frames < 3)
    return { ok: false, reason: 'render loop not cycling (rAF frames=' + frames + ')' };
  if (renderer === 'canvas') {
    const w = Math.max(1, Math.min(64, canvas.width || canvas.clientWidth || 1));
    const h = Math.max(1, Math.min(64, canvas.height || canvas.clientHeight || 1));
    const data = ctx.getImageData(0, 0, w, h).data;
    let nonzero = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] || data[i + 1] || data[i + 2] || data[i + 3]) nonzero++;
    }
    if (!nonzero)
      return { ok: false, reason: 'Canvas2D pixels are blank' };
    return { ok: true, renderer, frames, nonzero };
  }
  return { ok: true, renderer, frames };
})()))()`;
}

async function verifyRenderingLive(client) {
  const result = await client.send('Runtime.evaluate', {
    expression: renderLiveExpression(renderer),
    awaitPromise: true,
    returnByValue: true
  });
  const state = JSON.parse(result.result?.value || '{}');
  if (!state.ok)
    throw new Error(`page is not rendering: ${state.reason}`);
}

async function verifyRenderingLiveBidi(client, context) {
  const result = await client.send('script.evaluate', {
    target: { context },
    awaitPromise: true,
    resultOwnership: 'none',
    expression: renderLiveExpression(renderer)
  });
  const state = JSON.parse(result.result?.value || '{}');
  if (!state.ok)
    throw new Error(`page is not rendering: ${state.reason}`);
}

try {
  const port = await listen();
  const browser = resolveBrowser();
  if (isFirefoxBrowser(browser)) {
    writeFirefoxPrefs();
    const args = [
      '--headless',
      '--new-instance',
      '--profile',
      userDataDir,
      '--remote-debugging-port',
      '0',
      '--remote-allow-hosts',
      '127.0.0.1',
      '--remote-allow-origins',
      '*',
      ...browserArgs,
      'about:blank'
    ];
    const firefoxStderr = [];
    chrome = spawn(browser, args, { stdio: ['ignore', 'ignore', 'pipe'], detached: true });
    chrome.stderr.setEncoding('utf8');
    chrome.stderr.on('data', chunk => {
      firefoxStderr.push(chunk);
      while (firefoxStderr.join('').length > 8000)
        firefoxStderr.shift();
    });
    chrome.once('error', error => {
      if (!failure)
        failure = error;
    });

    const bidiUrl = await waitForFirefoxBidi(chrome, firefoxStderr);
    client = await connectBidi(bidiUrl);
    await client.send('session.new', { capabilities: {} });
    await client.send('session.subscribe', { events: ['log.entryAdded'] });
    const created = await client.send('browsingContext.create', { type: 'tab' });
    const context = created.context;
    await client.send('browsingContext.navigate', {
      context,
      url: `http://127.0.0.1:${port}/index.html`,
      wait: 'complete'
    });
    await waitForHealthyBidiPage(client, context);
    await verifyRenderingLiveBidi(client, context);
    await verifyAppSettingsImmediateBidi(client, context);
    await verifySyncKeyImportBidi(client, context);
  } else {
    const args = [
      '--headless=new',
      '--remote-debugging-port=0',
      '--remote-debugging-address=127.0.0.1',
      `--user-data-dir=${userDataDir}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-background-networking',
      '--disable-dev-shm-usage',
      '--enable-unsafe-swiftshader',
      '--ignore-gpu-blocklist',
      '--enable-webgl',
      '--use-gl=angle',
      '--use-angle=swiftshader',
      ...browserArgs,
      'about:blank'
    ];
    if (useNoSandbox)
      args.splice(1, 0, '--no-sandbox');

    const chromeStderr = [];
    chrome = spawn(browser, args, { stdio: ['ignore', 'ignore', 'pipe'], detached: true });
    chrome.stderr.setEncoding('utf8');
    chrome.stderr.on('data', chunk => {
      chromeStderr.push(chunk);
      while (chromeStderr.join('').length > 8000)
        chromeStderr.shift();
    });
    chrome.once('error', error => {
      if (!failure)
        failure = error;
    });

    const devtoolsPort = await waitForDevtools(chrome, chromeStderr);
    const pages = await jsonRequest(`http://127.0.0.1:${devtoolsPort}/json/new?about:blank`, {
      method: 'PUT'
    });
    client = await connect(pages.webSocketDebuggerUrl);
    await client.send('Runtime.enable');
    await client.send('Log.enable');
    await client.send('Page.enable');
    await client.send('Page.navigate', { url: `http://127.0.0.1:${port}/index.html` });
    await waitForHealthyPage(client);
    await verifyRenderingLive(client);
    await verifyReloadPersistence(client);
    await verifyAppSettingsReloadPersistence(client);
    await verifyLanguageRouteDoesNotOverrideSavedOnboarding(client, port);
    await verifyFirstRunGuideCanvasFlow(client);
    await verifySyncKeyImport(client);
    // Check an empty habit day before completion links a session to it.
    await verifyHabitsClickDoesNotReload(client);
    await verifyPracticeCarouselSwipe(client);
    await verifyPracticeStartClick(client);
    await verifyPracticeCompletionPersistence(client);
  }
  console.log(`web smoke: PASS (${renderer})`);
} catch (error) {
  failure = error;
} finally {
  if (client)
    client.close();
  if (chrome) {
    const exited = new Promise(resolveExit => chrome.once('exit', resolveExit));
    try {
      process.kill(-chrome.pid, 'SIGTERM');
    } catch {}
    const stopped = await Promise.race([
      exited.then(() => true),
      new Promise(resolveDelay => setTimeout(() => resolveDelay(false), 2000))
    ]);
    if (!stopped) {
      try {
        process.kill(-chrome.pid, 'SIGKILL');
      } catch {}
      await Promise.race([exited, new Promise(resolveDelay => setTimeout(resolveDelay, 1000))]);
    }
  }
  server.close();
  for (let attempt = 0; attempt < 10; attempt++) {
    try {
      rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
      break;
    } catch (error) {
      if (attempt === 9 || !['ENOTEMPTY', 'EBUSY', 'EPERM'].includes(error.code))
        throw error;
      await delay(250);
    }
  }
}

if (failure) {
  console.error(`web smoke: FAIL: ${failure.message}`);
  process.exit(1);
}
