import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const workerSource = fs.readFileSync("packaging/chrome-web-store/service_worker.js", "utf8");
const appSource = fs.readFileSync("packaging/chrome-web-store/extension_app.js", "utf8");

function appPage() {
  const status = { textContent: "Downloading..." };
  const document = Object.assign(new EventTarget(), {
    hidden: true,
    hasFocus: () => state.focused,
    querySelector: () => status,
  });
  const state = { focused: false, busy: false, breaksEnabled: false, selected: true, loads: 0, reloads: 0, saves: 0, discards: 0 };
  let now = 0;
  let timer;
  let finishSave;
  const window = Object.assign(new EventTarget(), {
    __inbeLoadApp: path => {
      assert.equal(path, "index.js");
      state.loads++;
    },
  });
  const Module = {
    __inbeRuntimeReady: true,
    __inbeStorageMounted: true,
    __inbeStorageLastOk: true,
    Asyncify: { state: 0 },
    __inbeFlushStorageSync: () => {
      state.saves++;
      return new Promise(resolve => { finishSave = resolve; });
    },
  };
  vm.runInNewContext(appSource, {
    document, window, Module, console,
    chrome: { tabs: {
      getCurrent: async () => ({ id: 4, active: state.selected }),
      discard: async id => {
        assert.equal(id, 4);
        state.discards++;
        return { id, discarded: true };
      },
    } },
    extensionCallExport: name => Number(name === "app_web_extension_breaks_enabled" ? state.breaksEnabled : !state.busy),
    location: { reload: () => state.reloads++ },
    performance: { now: () => now },
    setTimeout: (callback, delay) => { timer = { callback, at: now + delay }; },
    clearTimeout: () => { timer = undefined; },
  });
  return {
    state, Module, status,
    focus(focused, hidden = !focused) {
      state.focused = focused;
      document.hidden = hidden;
      document.dispatchEvent(new Event("visibilitychange"));
      window.dispatchEvent(new Event(focused ? "focus" : "blur"));
    },
    advance(ms) {
      now += ms;
      if (!timer || timer.at > now) return;
      const { callback } = timer;
      timer = undefined;
      return callback();
    },
    retry: window.__inbeTrySuspendExtension,
    finishSave: ok => finishSave(ok),
  };
}

{
  const page = appPage();
  assert.equal(page.state.loads, 0, "a restored background tab stays lightweight");
  assert.equal(page.status.textContent, "");
  page.focus(true);
  assert.equal(page.state.loads, 1, "focus starts the runtime once");
  assert.equal(page.status.textContent, "Downloading...");

  page.state.busy = true;
  page.focus(false);
  page.advance(19_999);
  assert.equal(page.state.saves, 0);
  await page.advance(1);
  assert.equal(page.state.saves, 0, "a busy runtime stays running");
  page.state.busy = false;
  const interrupted = page.retry();
  assert.equal(page.state.saves, 1);
  assert.equal(page.state.reloads, 0, "storage must finish first");
  page.focus(true);
  page.focus(false);
  page.finishSave(true);
  await interrupted;
  assert.equal(page.state.reloads, 0, "returning to the app cancels the old reload");

  const failed = page.advance(20_000);
  page.finishSave(false);
  await failed;
  await page.retry();
  assert.equal(page.state.saves, 2, "an unsuccessful save keeps the runtime awake");
  assert.equal(page.state.reloads, 0);

  page.focus(true);
  page.state.breaksEnabled = true;
  page.focus(false, false);
  await page.advance(20_000);
  assert.equal(page.state.saves, 2, "a visible break timer stays running while the window is blurred");
  page.focus(false);
  page.Module.__inbeStorageLastOk = false;
  await page.retry();
  assert.equal(page.state.saves, 2, "failed initial storage load holds the runtime open");
  page.Module.__inbeStorageLastOk = true;
  page.Module.Asyncify.state = 2;
  await page.retry();
  assert.equal(page.state.saves, 2, "an asynchronous WebAssembly call keeps the runtime awake");
  page.Module.Asyncify.state = 0;
  const saved = page.retry();
  page.finishSave(true);
  await saved;
  assert.equal(page.state.reloads, 1, "a selected tab reloads into the lightweight page after saving");
  assert.equal(page.state.loads, 1, "focus changes do not duplicate the active runtime");
}

{
  const page = appPage();
  page.focus(true);
  page.state.selected = false;
  page.focus(false);
  const saved = page.advance(20_000);
  page.finishSave(true);
  await saved;
  assert.equal(page.state.discards, 1, "Chromium unloads a saved background tab");
  assert.equal(page.state.reloads, 0, "the browser reloads the discarded tab on activation");
}

const storage = {};
const events = {};
const notifications = [];
const tabs = [];
const alarms = [];
let idleState = "active";
let nextTabId = 1;

function event(name) {
  events[name] = [];
  return {
    addListener(listener) {
      events[name].push(listener);
    },
  };
}

const chrome = {
  runtime: {
    getURL(path) {
      return `chrome-extension://inbe/${path}`;
    },
    onInstalled: event("runtime.onInstalled"),
    onStartup: event("runtime.onStartup"),
    onConnect: event("runtime.onConnect"),
    onMessage: event("runtime.onMessage"),
  },
  storage: {
    local: {
      async get(keys) {
        const out = {};
        for (const key of keys)
          out[key] = storage[key];
        return out;
      },
      async set(values) {
        Object.assign(storage, values);
      },
    },
  },
  alarms: {
    async create(name, spec) {
      alarms.push({ name, spec });
    },
    async clear(name) {
      alarms.push({ name, clear: true });
    },
    onAlarm: event("alarms.onAlarm"),
  },
  idle: {
    async queryState() {
      return idleState;
    },
  },
  notifications: {
    async create(id, options) {
      notifications.push({ id, options });
      return id;
    },
    async clear(id) {
      notifications.push({ id, clear: true });
      return true;
    },
    onClicked: event("notifications.onClicked"),
    onButtonClicked: event("notifications.onButtonClicked"),
  },
  action: {
    onClicked: event("action.onClicked"),
    async setBadgeText(value) {
      chrome.action.badgeText = value.text;
    },
    async setBadgeBackgroundColor(value) {
      chrome.action.badgeColor = value.color;
    },
  },
  contextMenus: {
    create(item) {
      chrome.contextMenus.items.push(item);
    },
    removeAll(callback) {
      chrome.contextMenus.items = [];
      if (callback) callback();
    },
    items: [],
    onClicked: event("contextMenus.onClicked"),
  },
  tabs: {
    async query({ currentWindow }) {
      assert.equal(currentWindow, true);
      return tabs.slice();
    },
    async create({ url }) {
      const tab = { id: nextTabId++, pendingUrl: url, active: true };
      tabs.push(tab);
      return tab;
    },
    async update(id, changes) {
      const tab = tabs.find((candidate) => candidate.id === id);
      assert.ok(tab, "cannot update a missing tab");
      Object.assign(tab, changes);
      return tab;
    },
  },
};

const context = {
  chrome,
  console,
  Date,
  globalThis: {},
  setTimeout,
  clearTimeout,
};
context.globalThis = context;

vm.runInNewContext(workerSource, context, {
  filename: "packaging/chrome-web-store/service_worker.js",
});

const api = context.__inbeExtensionBreaks;
assert.ok(api, "service worker exposes test API");

const normalized = api.normalizeConfig({
  enabled: true,
  timers: [{ limitS: 10.4, durationS: 2, showSkip: false }],
});
assert.equal(normalized.enabled, true);
assert.equal(normalized.timers[0].limitS, 10);
assert.equal(normalized.timers[0].showSkip, false);
assert.equal(normalized.timers[1].limitS, 2700);

await events["runtime.onInstalled"][0]({ reason: "install" });
assert.ok(chrome.contextMenus.items.some((item) => item.id === "break-rest-now"));
assert.equal(tabs.length, 0, "install does not load the app runtime");

const open = events["action.onClicked"][0];
await Promise.all([open(), open()]);
assert.equal(tabs.length, 1, "concurrent opens share one app tab");
const appTab = tabs[0];
assert.equal(appTab.pendingUrl, "chrome-extension://inbe/index.html");
appTab.active = false;
await open();
assert.equal(tabs.length, 1, "a pending navigation already owns the app tab");
assert.equal(appTab.active, true);
appTab.url = appTab.pendingUrl;
delete appTab.pendingUrl;
appTab.active = false;
await open();
assert.equal(tabs.length, 1, "a loaded app tab is reused");
assert.equal(appTab.active, true);
tabs.length = 0;
await open();
assert.equal(tabs.length, 1, "a closed tab can be opened again");

await api.requestBreakNow(1);
assert.equal(storage.inbeBreakConfig.enabled, true);
assert.ok(notifications.some((entry) => entry.id === "inbe-break-1" && entry.options));
assert.equal(chrome.action.badgeText, "", "manual break does not start a hidden alarm");

let disconnectVisiblePage;
events["runtime.onConnect"][0]({
  name: "inbe-visible-page",
  onDisconnect: {
    addListener(listener) {
      disconnectVisiblePage = listener;
    },
  },
});
await new Promise((resolve) => setImmediate(resolve));
assert.equal(chrome.action.badgeText, "BR", "visible page enables automatic breaks");

storage.inbeBreakConfig = api.normalizeConfig({
  enabled: true,
  timers: [
    { enabled: true, limitS: 60, durationS: 30, postponeS: 120, maxPrompts: 3, showSkip: true, showPostpone: true },
    { enabled: false },
    { enabled: false },
  ],
});
storage.inbeBreakState = api.normalizeState({ lastTickMs: 1000 });
idleState = "active";
await api.tickBreaks(61000);
assert.ok(notifications.some((entry) =>
  entry.id === "inbe-break-0" && entry.options && entry.options.buttons.length === 2));

await api.applyNotificationAction("inbe-break-0", 0);
assert.ok(storage.inbeBreakState.timers[0].snoozeUntilMs > Date.now(), "postpone stores snooze deadline");

disconnectVisiblePage();
await new Promise((resolve) => setImmediate(resolve));
assert.equal(chrome.action.badgeText, "", "closing the page stops the indicator");
assert.ok(alarms.some((entry) => entry.name === "inbe-break-tick" && entry.clear));
const notificationCount = notifications.filter((entry) => entry.options).length;
await api.tickBreaks(122000);
assert.equal(notifications.filter((entry) => entry.options).length, notificationCount,
  "closed page cannot receive automatic reminders");
assert.equal(storage.inbeBreakState.lastTickMs, 0, "closed page resets the timer");

events["runtime.onConnect"][0]({
  name: "inbe-visible-page",
  onDisconnect: { addListener() {} },
});
await new Promise((resolve) => setImmediate(resolve));

storage.inbeBreakState = api.normalizeState({
  lastTickMs: 1000,
  timers: [{ activeS: 80, idleS: 0 }],
});
idleState = "idle";
await api.tickBreaks(61000);
assert.equal(storage.inbeBreakState.timers[0].activeS, 0, "natural idle break resets timer");

events["notifications.onClicked"][0]("inbe-break-1");
await new Promise((resolve) => setImmediate(resolve));
assert.ok(tabs.some((tab) => tab.pendingUrl?.endsWith("?inbe_launch=break-settings")));

events["contextMenus.onClicked"][0]({ menuItemId: "habits" });
await new Promise((resolve) => setImmediate(resolve));
assert.ok(tabs.some((tab) => tab.pendingUrl?.endsWith("?inbe_launch=habits")));

console.log("Chrome extension break service worker tests passed");
