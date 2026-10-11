// Browser effects imported by the Ziran app through Emscripten.
addToLibrary({
  browser_storage_schedule: (delay_ms, log_success) => {
    if (typeof Module.__inbeScheduleStorageSync === 'function') {
      Module.__inbeScheduleStorageSync(delay_ms, !!log_success);
    }
  },

  browser_storage_busy: () => Module.__inbeStorageSyncing ||
    Module.__inbeStorageSyncPending ? 1 : 0,

  browser_storage_wait__deps: ['$Asyncify'],
  browser_storage_wait__async: true,
  browser_storage_wait: (timeout_ms, log_success) => Asyncify.handleAsync(async () => {
    const module = Module || {};
    const timeout = timeout_ms > 0 ? timeout_ms : 5000;
    let flush = typeof module.__inbeFlushStorageSync === 'function'
      ? module.__inbeFlushStorageSync : null;
    if (!flush && typeof module.__inbeScheduleStorageSync === 'function') {
      module.__inbeScheduleStorageSync(0, !!log_success);
      flush = typeof module.__inbeFlushStorageSync === 'function'
        ? module.__inbeFlushStorageSync : null;
    }
    if (!flush) {
      return 0;
    }
    let timer;
    try {
      const promise = flush(!!log_success);
      if (!promise || typeof promise.then !== 'function') {
        return module.__inbeStorageSyncLastOk === false ? 0 : 1;
      }
      let timedOut = false;
      const result = await Promise.race([
        promise,
        new Promise(resolve => {
          timer = setTimeout(() => {
            timedOut = true;
            resolve(false);
          }, timeout);
        })
      ]);
      if (timedOut) {
        module.__inbeStorageSyncLastOk = false;
        module.__inbeStorageSyncLastError = 'timeout';
        return 0;
      }
      return result ? 1 : 0;
    } catch (error) {
      module.__inbeStorageSyncLastOk = false;
      module.__inbeStorageSyncLastError =
        error && error.message ? error.message : String(error);
      return 0;
    } finally {
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    }
  }),

  browser_storage_flush: log_success => {
    if (typeof Module.__inbeFlushStorageSync === 'function') {
      Module.__inbeFlushStorageSync(!!log_success);
    } else if (typeof Module.__inbeScheduleStorageSync === 'function') {
      Module.__inbeScheduleStorageSync(0, !!log_success);
    }
  },

  web_extension_host_js: () => {
    if (typeof window === 'undefined') {
      return 0;
    }
    if (window.__inbeExtension) {
      return 1;
    }
    return window.location && window.location.protocol === 'chrome-extension:' &&
      typeof chrome !== 'undefined' && chrome.runtime ? 1 : 0;
  },

  web_extension_break_now_js: break_type => {
    if (typeof window !== 'undefined' &&
        typeof window.__inbeExtensionBreakNow === 'function') {
      window.__inbeExtensionBreakNow(break_type);
    }
  },

  web_context_click_in_bounds: (x0, y0, x1, y1) => {
    const click = Module.__kryonContextClick;
    if (!click) {
      return 0;
    }
    if (Date.now() - click.time > 750) {
      Module.__kryonContextClick = null;
      return 0;
    }
    if (click.x >= x0 && click.x <= x1 && click.y >= y0 && click.y <= y1) {
      Module.__kryonContextClick = null;
      return 1;
    }
    return 0;
  }
});
