(() => {
  const idleDelayMs = 20_000;
  const status = document.querySelector("#status");
  const loadingText = status.textContent;
  let started = false;
  let idlePeriod = null;
  let idleTimer;
  let saving = false;

  function focused() {
    return !document.hidden && document.hasFocus();
  }

  function canSuspend() {
    if (!Module.__inbeRuntimeReady || !Module.__inbeStorageMounted || !Module.__inbeStorageLastOk ||
        Module.Asyncify?.state !== 0) return false;
    // Reloading a visible page would disconnect its break timer from the worker.
    if (!document.hidden && extensionCallExport("app_web_extension_breaks_enabled")) return false;
    return extensionCallExport("app_web_extension_can_suspend") === 1;
  }

  async function trySuspend() {
    const period = idlePeriod;
    if (!period || saving || focused() || period.suspendFailed ||
        performance.now() < period.deadline || !canSuspend()) return;

    saving = true;
    try {
      if (!await Module.__inbeFlushStorageSync(false)) {
        period.suspendFailed = true;
        return;
      }
      if (idlePeriod !== period || focused() || !canSuspend()) return;
      if (document.hidden) {
        const tab = await chrome.tabs.getCurrent();
        if (idlePeriod !== period || focused() || !canSuspend()) return;
        if (tab && !tab.active && (await chrome.tabs.discard(tab.id))?.discarded) return;
      }
      // Chrome only discards an unselected tab. Reload a blurred selected tab
      // into this lightweight page without replacing its tab or history.
      if (idlePeriod === period && !focused() && canSuspend()) location.reload();
    } catch (error) {
      period.suspendFailed = true;
      console.warn("Inner Breeze could not go idle", error);
    } finally {
      saving = false;
    }
  }

  function updateFocus() {
    if (focused()) {
      clearTimeout(idleTimer);
      idlePeriod = null;
      if (!started) {
        started = true;
        status.textContent = loadingText;
        window.__inbeLoadApp("index.js");
      }
    } else if (started && !idlePeriod) {
      idlePeriod = { deadline: performance.now() + idleDelayMs, suspendFailed: false };
      idleTimer = setTimeout(trySuspend, idleDelayMs);
    }
  }

  // The already-running extension bridge retries when a practice or save ends.
  window.__inbeTrySuspendExtension = trySuspend;
  window.addEventListener("focus", updateFocus);
  window.addEventListener("blur", updateFocus);
  document.addEventListener("visibilitychange", updateFocus);
  status.textContent = "";
  updateFocus();
})();
