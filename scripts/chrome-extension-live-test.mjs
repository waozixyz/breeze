#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { accessSync, constants, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

if (typeof WebSocket === "undefined") {
  console.error("chrome extension live test needs Node with global WebSocket support");
  process.exit(1);
}

const extensionRoot = resolve(process.argv[2] || "build/dist/chrome-web-store");
const timeoutMs = Number(process.env.INBE_EXTENSION_TEST_TIMEOUT_MS || 120000);
const userDataDir = mkdtempSync(join(tmpdir(), "inbe-chrome-extension-"));

function canExecute(path) {
  try {
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function findOnPath(command) {
  if (command.includes("/"))
    return canExecute(command) ? command : "";
  for (const dir of (process.env.PATH || "").split(":")) {
    if (!dir) continue;
    const path = join(dir, command);
    if (canExecute(path)) return path;
  }
  return "";
}

function resolveChromium() {
  const candidates = [
    process.env.CHROME || "",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
  ].filter(Boolean);

  for (const candidate of candidates) {
    const browser = findOnPath(candidate);
    if (browser) return browser;
  }
  throw new Error(`Chrome/Chromium not found; tried ${candidates.join(", ")}`);
}

function delay(ms) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, ms));
}

function readDevtoolsPort() {
  const path = join(userDataDir, "DevToolsActivePort");
  if (!existsSync(path)) return 0;
  const port = Number(readFileSync(path, "utf8").split("\n", 1)[0]);
  return Number.isFinite(port) && port > 0 ? port : 0;
}

async function waitForDevtools(chrome, stderrLines) {
  const start = Date.now();
  let exited = false;

  chrome.once("exit", () => {
    exited = true;
  });
  while (Date.now() - start < timeoutMs) {
    if (exited) {
      const stderr = stderrLines.join("").trim();
      throw new Error(`Chromium exited before DevTools was ready${stderr ? `: ${stderr.slice(-3000)}` : ""}`);
    }
    const port = readDevtoolsPort();
    if (port) return port;
    await delay(100);
  }
  throw new Error("timed out waiting for Chromium DevTools port");
}

class Cdp {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
    this.ready = new Promise((resolveReady, rejectReady) => {
      this.ws.addEventListener("open", resolveReady, { once: true });
      this.ws.addEventListener("error", rejectReady, { once: true });
    });
    this.ws.addEventListener("message", (event) => this.onMessage(event));
  }

  onMessage(event) {
    const message = JSON.parse(event.data);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(`${message.error.message || "CDP error"} ${JSON.stringify(message.error)}`));
      else resolve(message.result || {});
      return;
    }
    this.events.push(message);
  }

  async send(method, params = {}, sessionId = undefined) {
    await this.ready;
    const id = this.nextId++;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    this.ws.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    this.ws.close();
  }
}

async function waitForTarget(cdp, predicate, label) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const { targetInfos } = await cdp.send("Target.getTargets");
    const match = targetInfos.find(predicate);
    if (match) return match;
    await delay(250);
  }
  throw new Error(`timed out waiting for target: ${label}`);
}

async function attach(cdp, targetId) {
  const { sessionId } = await cdp.send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  await cdp.send("Runtime.enable", {}, sessionId);
  return sessionId;
}

async function evaluate(cdp, sessionId, expression, awaitPromise = false) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise,
    returnByValue: true,
  }, sessionId);
  if (result.exceptionDetails) {
    throw new Error(`evaluation failed: ${JSON.stringify(result.exceptionDetails)}`);
  }
  return result.result.value;
}

async function waitForPageReady(cdp, sessionId) {
  const start = Date.now();
  let lastState = {};
  while (Date.now() - start < timeoutMs) {
    const value = await evaluate(cdp, sessionId, `JSON.stringify({
      extension: !!window.__inbeExtension,
      runtimeReady: !!(window.Module && Module.__inbeRuntimeReady),
      href: location.href
    })`);
    const state = JSON.parse(value);
    lastState = state;
    if (state.runtimeReady) return state;
    await delay(500);
  }
  assert.equal(lastState.extension, true, `extension flag missing at ${lastState.href || "unknown page"}`);
  throw new Error(`extension app page did not become runtime-ready: ${JSON.stringify(lastState)}`);
}

async function waitForWorkerBreakConfig(cdp, worker, predicate, label) {
  const start = Date.now();
  let lastConfig = null;
  while (Date.now() - start < timeoutMs) {
    lastConfig = JSON.parse(await evaluate(cdp, worker, `chrome.storage.local.get('inbeBreakConfig').then((data) => JSON.stringify(data.inbeBreakConfig || null))`, true));
    if (predicate(lastConfig)) return lastConfig;
    await delay(500);
  }
  throw new Error(`timed out waiting for worker break config ${label}: ${JSON.stringify(lastConfig)}`);
}

async function main() {
  assert.ok(existsSync(join(extensionRoot, "manifest.json")), "missing built extension manifest");
  assert.ok(existsSync(join(extensionRoot, "service_worker.js")), "missing built extension worker");
  assert.ok(existsSync(join(extensionRoot, "index.html")), "missing built extension page");

  const chromium = resolveChromium();
  const syncServer = createServer((request, response) => {
    response.writeHead(200, {
      "Access-Control-Allow-Origin": "*",
      "Content-Type": "text/plain",
    });
    response.end(request.url === "/sync-probe" ? "custom sync server reachable" : "unexpected path");
  });
  await new Promise((resolveReady) => syncServer.listen(0, "127.0.0.1", resolveReady));
  const syncServerPort = syncServer.address().port;
  const stderrLines = [];
  const args = [
    "--headless=new",
    "--disable-gpu",
    "--disable-breakpad",
    "--disable-crash-reporter",
    "--disable-crashpad",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--remote-debugging-port=0",
    `--user-data-dir=${userDataDir}`,
    `--disable-extensions-except=${extensionRoot}`,
    `--load-extension=${extensionRoot}`,
    "about:blank",
  ];
  if (process.env.INBE_EXTENSION_NO_SANDBOX || (typeof process.getuid === "function" && process.getuid() === 0))
    args.splice(1, 0, "--no-sandbox");

  const chrome = spawn(chromium, args, { stdio: ["ignore", "ignore", "pipe"] });
  chrome.stderr.on("data", (data) => stderrLines.push(data.toString()));

  let cdp;
  try {
    const port = await waitForDevtools(chrome, stderrLines);
    const version = await fetch(`http://127.0.0.1:${port}/json/version`).then((res) => res.json());
    cdp = new Cdp(version.webSocketDebuggerUrl);
    await cdp.ready;
    await cdp.send("Target.setDiscoverTargets", { discover: true });

    const workerTarget = await waitForTarget(
      cdp,
      (target) => target.type === "service_worker" &&
        target.url.startsWith("chrome-extension://") &&
        target.url.endsWith("/service_worker.js"),
      "extension service worker",
    );
    const extensionId = new URL(workerTarget.url).host;
    const worker = await attach(cdp, workerTarget.targetId);

    const workerApi = await evaluate(cdp, worker, `JSON.stringify({
      hasBreakApi: !!globalThis.__inbeExtensionBreaks,
      hasChromeStorage: !!(chrome && chrome.storage && chrome.storage.local),
      hasNotifications: !!(chrome && chrome.notifications),
      hasAlarms: !!(chrome && chrome.alarms)
    })`);
    assert.deepEqual(JSON.parse(workerApi), {
      hasBreakApi: true,
      hasChromeStorage: true,
      hasNotifications: true,
      hasAlarms: true,
    });

    const appUrl = `chrome-extension://${extensionId}/index.html`;
    await waitForWorkerBreakConfig(cdp, worker, (config) => config !== null, "at installation");
    const installedTargets = await cdp.send("Target.getTargets");
    assert.ok(!installedTargets.targetInfos.some((target) => target.url.startsWith(appUrl)),
      "install leaves the app runtime unloaded");

    await evaluate(cdp, worker, `globalThis.__inbeExtensionBreaks.requestBreakNow(1).then(() => true)`, true);
    const workerState = JSON.parse(await evaluate(cdp, worker, `chrome.storage.local.get(['inbeBreakConfig', 'inbeBreakState']).then((data) => JSON.stringify({
      enabled: data.inbeBreakConfig && data.inbeBreakConfig.enabled,
      notificationId: data.inbeBreakState && data.inbeBreakState.timers && data.inbeBreakState.timers[1].notificationId
    }))`, true));
    assert.equal(workerState.enabled, true);
    assert.equal(workerState.notificationId, "inbe-break-1");

    const breakSettingsUrl = `${appUrl}?inbe_launch=break-settings`;
    const openSettings = `openApp(${JSON.stringify(breakSettingsUrl)})`;
    await evaluate(cdp, worker, `Promise.all([${openSettings}, ${openSettings}]).then(() => true)`, true);
    const settingsTarget = await waitForTarget(cdp,
      (target) => target.type === "page" && target.url === breakSettingsUrl, "break settings tab");
    await evaluate(cdp, worker, `${openSettings}.then(() => true)`, true);
    const openedTargets = await cdp.send("Target.getTargets");
    assert.deepEqual(openedTargets.targetInfos.filter((target) => target.url === breakSettingsUrl)
      .map((target) => target.targetId), [settingsTarget.targetId], "opening again reuses the existing tab");
    const page = await attach(cdp, settingsTarget.targetId);
    const readyState = await waitForPageReady(cdp, page);
    assert.ok(readyState.href.includes("chrome-extension://"));

    const customServerResponse = await evaluate(cdp, page,
      `fetch('http://127.0.0.1:${syncServerPort}/sync-probe').then((response) => response.text())`, true);
    assert.equal(customServerResponse, "custom sync server reachable");

    const pageExports = JSON.parse(await evaluate(cdp, page, `(() => {
      Module._app_web_test_enable_extension_breaks(60);
      return JSON.stringify({
        host: Module._app_web_extension_host(),
        enabled: Module._app_web_extension_breaks_enabled(),
        limitS: Module._app_web_extension_break_timer_limit_s(1),
        showPostpone: Module._app_web_extension_break_timer_show_postpone(1)
      });
    })()`));
    assert.deepEqual(pageExports, {
      host: 1,
      enabled: 1,
      limitS: 60,
      showPostpone: 1,
    });
    await evaluate(cdp, page, `window.__inbeExtensionBreakNow(1); true`);
    const configFromPage = await waitForWorkerBreakConfig(
      cdp,
      worker,
      (config) => !!config && config.enabled === true &&
        config.timers && config.timers[1] &&
        config.timers[1].limitS === 60 &&
        config.timers[1].showPostpone === true,
      "from app bridge",
    );

    await cdp.send("Target.createTarget", {
      url: `chrome-extension://${extensionId}/index.html?inbe_launch=habits`,
    });
    await waitForTarget(cdp, (target) => target.type === "page" && target.url.includes("inbe_launch=habits"), "habits launch page");

    console.log(`Chrome extension live test passed (${extensionId})`);
  } finally {
    if (cdp) cdp.close();
    chrome.kill("SIGTERM");
    await delay(250);
    await new Promise((resolveClosed) => syncServer.close(resolveClosed));
    rmSync(userDataDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(`Chrome extension live test failed: ${error.stack || error.message}`);
  process.exit(1);
});
