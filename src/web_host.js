// Browser effects imported by the Ziran app through Emscripten.
addToLibrary({
  browser_storage_schedule: (delay_ms, log_success) => {
    if (typeof Module.__inbeScheduleStorageSync === 'function') {
      Module.__inbeScheduleStorageSync(delay_ms, !!log_success);
    }
  },

  browser_storage_busy: () => Module.__inbeStorageSyncing ||
    Module.__inbeStorageSyncPending ? 1 : 0,

  browser_viewport_size: (fallbackWidth, fallbackHeight, output) => {
    const doc = typeof document !== 'undefined' ? document : null;
    const viewport = typeof visualViewport !== 'undefined' ? visualViewport : null;
    let width = fallbackWidth;
    let height = fallbackHeight;
    if (viewport && viewport.width > 0 && viewport.height > 0) {
      width = viewport.width;
      height = viewport.height;
    } else if (typeof window !== 'undefined') {
      width = window.innerWidth ||
        (doc && doc.documentElement && doc.documentElement.clientWidth) || fallbackWidth;
      height = window.innerHeight ||
        (doc && doc.documentElement && doc.documentElement.clientHeight) || fallbackHeight;
    }
    const canvas = Module.canvas || (doc && doc.getElementById('canvas'));
    const candidates = [doc && doc.getElementById('canvas-frame'),
      canvas && canvas.parentElement, canvas];
    for (const element of candidates) {
      if (!element || !element.getBoundingClientRect) {
        continue;
      }
      const bounds = element.getBoundingClientRect();
      if (bounds.width > 0 && bounds.height > 0) {
        width = Math.min(width, bounds.width);
        height = Math.min(height, bounds.height);
        break;
      }
    }
    HEAP32[output >> 2] = Math.max(1, Math.round(width > 0 ? width : fallbackWidth));
    HEAP32[(output + 4) >> 2] = Math.max(1, Math.round(height > 0 ? height : fallbackHeight));
  },

  browser_open_uri__deps: ['$UTF8ToString'],
  browser_open_uri: pointer => {
    const uri = UTF8ToString(pointer);
    if (!/^https?:\/\//i.test(uri)) {
      return 0;
    }
    let anchor;
    try {
      anchor = document.createElement('a');
      anchor.href = uri;
      anchor.target = '_blank';
      anchor.rel = 'noopener';
      document.body.appendChild(anchor);
      anchor.click();
      return 1;
    } catch (error) {
      return 0;
    } finally {
      if (anchor) {
        anchor.remove();
      }
    }
  },

  app_pick_file_web__deps: ['$Asyncify', '$FS', '$UTF8ToString',
    '$lengthBytesUTF8', '$stringToUTF8'],
  app_pick_file_web__async: true,
  app_pick_file_web: (title, filter, suggested_name, save, output, capacity) =>
    Asyncify.handleAsync(async () => {
      const titleText = UTF8ToString(title);
      const filterText = UTF8ToString(filter);
      const path = '/tmp/inbe-file-' + Date.now() + '-' +
        Math.random().toString(36).slice(2);
      if (capacity < 2 || lengthBytesUTF8(path) + 1 > capacity) {
        return -1;
      }
      let input;
      try {
        if (save) {
          stringToUTF8(path, output, capacity);
          return 1;
        }
        input = document.createElement('input');
        input.type = 'file';
        input.setAttribute('aria-label', titleText);
        input.accept = (filterText.match(/[*][.][a-z0-9]+/gi) || [])
          .map(value => value.slice(1)).join(',');
        input.style.display = 'none';
        document.body.appendChild(input);
        const selected = await new Promise(resolve => {
          input.addEventListener('change', () =>
            resolve(input.files && input.files[0] || null), {once: true});
          input.addEventListener('cancel', () => resolve(null), {once: true});
          input.click();
        });
        if (!selected) {
          return 0;
        }
        const bytes = new Uint8Array(await selected.arrayBuffer());
        FS.writeFile(path, bytes);
        stringToUTF8(path, output, capacity);
        return 1;
      } catch (error) {
        console.error('Inbe file picker failed:', error);
        return -1;
      } finally {
        if (input) {
          input.remove();
        }
      }
    }),

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

  web_download_file__deps: ['$FS', '$UTF8ToString'],
  web_download_file: (path, filename, mime) => {
    try {
      const bytes = FS.readFile(UTF8ToString(path));
      const blob = new Blob([bytes], {
        type: UTF8ToString(mime) || 'application/octet-stream'
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = UTF8ToString(filename) || 'download';
      anchor.style.display = 'none';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return 1;
    } catch (error) {
      console.error('Inbe web download failed:', error);
      return 0;
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
