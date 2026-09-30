var statusElement = document.querySelector('#status');
var progressElement = document.querySelector('#progress');
var loadingScreen = document.querySelector('#loading-screen');

function storageOriginLooksPersistent() {
  var protocol = window.location && window.location.protocol;

  return protocol === 'http:' || protocol === 'https:';
}

function reportStorageOriginProblem() {
  if (storageOriginLooksPersistent()) return;
  console.error(
    'APP: persistent storage needs an http://localhost or https:// origin. ' +
    'Opening the web build directly as a file can prevent Firefox IndexedDB/IDBFS saves.'
  );
}

function selectedRenderer() {
  return 'canvas';
}

window.__inbeLoadApp = function(src) {
  var script;
  var renderer = selectedRenderer();

  Module.__inbeRenderer = renderer;

  script = document.createElement('script');
  script.async = true;
  script.src = src;
  document.body.appendChild(script);
};

function routineRuntimeLog(text) {
  return /^(AUDIO: Loaded sound asset|AUDIO: Cannot play sound because sound is not loaded|DATA: root directory|APP: app init|APP: DPI scale|APP: Global app pointer set|APP: Loaded play_in_background setting|APP_EMBED: geometry|SYNC: queued local changes|SYNC: starting background sync|SYNC: payload|SYNC: dispatched|SYNC: background sync complete|SYNC: refreshing social cache|SYNC: social cache refreshed|SYNC: websocket event listener started)/.test(text || '');
}

function mirrorRuntimeLog(text, isErrorStream) {
  if (routineRuntimeLog(text)) {
    if (Module.__inbeVerboseLogs)
      console.debug(text);
    return;
  }
  if (isErrorStream || /\b(error|failed|invalid|missing|aborted|exception)\b/i.test(text || ''))
    console.error(text);
  else
    console.log(text);
}

function hideLoadingScreen() {
  if (!loadingScreen) return;
  window.requestAnimationFrame(function() {
    loadingScreen.classList.add('is-hidden');
  });
}

var extensionBridgeStarted = false;
var extensionBridgeLastConfig = '';
var extensionBridgePort = null;
var extensionPageSuspended = false;

function extensionRuntime() {
  var isExtensionPage = window.__inbeExtension ||
    (window.location && window.location.protocol === 'chrome-extension:');
  if (!isExtensionPage) return null;
  if (typeof chrome === 'undefined' || !chrome.runtime || !chrome.runtime.sendMessage) return null;
  return chrome.runtime;
}

function extensionCallExport(name, args) {
  if (!Module || !Module.__inbeRuntimeReady) return 0;
  var fn = Module && Module['_' + name];
  if (typeof fn !== 'function') return 0;
  try {
    return fn.apply(null, args || []);
  } catch (e) {
    console.error('Extension bridge callback failed:', name, e);
    return 0;
  }
}

function extensionTimerConfig(type) {
  return {
    enabled: !!extensionCallExport('app_web_extension_break_timer_enabled', [type]),
    limitS: extensionCallExport('app_web_extension_break_timer_limit_s', [type]) | 0,
    durationS: extensionCallExport('app_web_extension_break_timer_duration_s', [type]) | 0,
    postponeS: extensionCallExport('app_web_extension_break_timer_postpone_s', [type]) | 0,
    maxPrompts: extensionCallExport('app_web_extension_break_timer_max_prompts', [type]) | 0,
    showSkip: !!extensionCallExport('app_web_extension_break_timer_show_skip', [type]),
    showPostpone: !!extensionCallExport('app_web_extension_break_timer_show_postpone', [type])
  };
}

function extensionBreakConfig() {
  return {
    enabled: !!extensionCallExport('app_web_extension_breaks_enabled'),
    timers: [extensionTimerConfig(0), extensionTimerConfig(1), extensionTimerConfig(2)]
  };
}

function syncExtensionPagePresence() {
  var runtime = extensionRuntime();
  if (!runtime || window.location.protocol !== 'chrome-extension:') return;
  if (document.hidden || extensionPageSuspended) {
    if (extensionBridgePort) extensionBridgePort.disconnect();
    extensionBridgePort = null;
    return;
  }
  if (extensionBridgePort) return;
  try {
    var port = runtime.connect({ name: 'inbe-visible-page' });
    extensionBridgePort = port;
    port.onDisconnect.addListener(function() {
      if (extensionBridgePort === port) extensionBridgePort = null;
    });
  } catch (error) {
    console.warn('Inner Breeze extension presence failed:', error);
  }
}

function publishExtensionBreakConfig(force) {
  var runtime = extensionRuntime();
  var config;
  var text;

  if (!runtime || !Module.__inbeRuntimeReady) return;
  config = extensionBreakConfig();
  text = JSON.stringify(config);
  if (!force && text === extensionBridgeLastConfig) return;
  extensionBridgeLastConfig = text;
  runtime.sendMessage({ type: 'inbe.breakConfig', config: config }, function() {
    var lastError = chrome.runtime && chrome.runtime.lastError;
    if (lastError) console.warn('Inner Breeze extension break sync failed:', lastError.message);
  });
}

window.__inbeExtensionBreakNow = function(breakType) {
  var runtime = extensionRuntime();
  publishExtensionBreakConfig(true);
  if (!runtime) return;
  runtime.sendMessage({ type: 'inbe.breakNow', breakType: breakType | 0 }, function() {
    var lastError = chrome.runtime && chrome.runtime.lastError;
    if (lastError) console.warn('Inner Breeze extension rest-now failed:', lastError.message);
  });
};

function startExtensionBridge() {
  if (extensionBridgeStarted || !extensionRuntime()) return;
  extensionBridgeStarted = true;
  syncExtensionPagePresence();
  document.addEventListener('visibilitychange', syncExtensionPagePresence, false);
  window.addEventListener('pagehide', function() {
    extensionPageSuspended = true;
    syncExtensionPagePresence();
  }, false);
  window.addEventListener('pageshow', function() {
    extensionPageSuspended = false;
    syncExtensionPagePresence();
  }, false);
  publishExtensionBreakConfig(true);
  setInterval(function() {
    syncExtensionPagePresence();
    publishExtensionBreakConfig(false);
  }, 2000);
}

function markRuntimeReady() {
  if (!Module.__inbeAppReady) return;
  if (Module.__inbeRuntimeReady) return;
  if (Module.Asyncify && Module.Asyncify.state !== 0) {
    if (!Module.__inbeRuntimeReadyPending) {
      Module.__inbeRuntimeReadyPending = true;
      setTimeout(function() {
        Module.__inbeRuntimeReadyPending = false;
        markRuntimeReady();
      }, 16);
    }
    return;
  }
  Module.__inbeRuntimeReady = true;
  hideLoadingScreen();
  runLaunchCommand();
  startExtensionBridge();
}

function noteAppReadyFromLog(text) {
  if (!/APP: Global app pointer set(?:$| to 0x[0-9a-fA-F]+)/.test(text)) return;
  Module.__inbeAppReady = true;
  markRuntimeReady();
}

function runStorageSync(retryDelay) {
  if (Module.__inbeStorageSyncing) return Module.__inbeStorageSyncPromise || Promise.resolve(false);

  Module.__inbeStorageSyncing = true;
  Module.__inbeStorageSyncPending = false;
  var shouldLog = !!Module.__inbeStorageSyncLogSuccess;
  Module.__inbeStorageSyncLogSuccess = false;
  if (!Module.__inbeStorageSyncPromise) {
    Module.__inbeStorageSyncPromise = new Promise(function(resolve) {
      Module.__inbeStorageSyncResolve = resolve;
    });
  }
  var promise = Module.__inbeStorageSyncPromise;

  function finishStorageSync(ok) {
    var resolve = Module.__inbeStorageSyncResolve;

    Module.__inbeStorageSyncLastOk = !!ok;
    if (ok) {
      Module.__inbeStorageSyncLastError = '';
      Module.__inbeStorageSyncLastSuccessMs = Date.now();
    }
    Module.__inbeStorageSyncResolve = null;
    Module.__inbeStorageSyncPromise = null;
    if (resolve) resolve(ok);
  }

  function drainPendingStorageSync() {
    if (!Module.__inbeStorageSyncPending) {
      finishStorageSync(true);
      return;
    }
    if (Module.__inbeStorageSyncTimer) clearTimeout(Module.__inbeStorageSyncTimer);
    Module.__inbeStorageSyncTimer = setTimeout(function() {
      Module.__inbeStorageSyncTimer = 0;
      runStorageSync(retryDelay);
    }, retryDelay);
  }

  try {
    FS.syncfs(false, function(err) {
      Module.__inbeStorageSyncing = false;
      if (err) {
        Module.__inbeStorageSyncLastError = err && err.message ? err.message : String(err);
        console.error('IDBFS save failed:', err);
        finishStorageSync(false);
      } else {
        if (shouldLog) console.log('IDBFS synced');
        drainPendingStorageSync();
      }
    });
  } catch (e) {
    Module.__inbeStorageSyncing = false;
    console.error('IDBFS sync error:', e);
    finishStorageSync(false);
  }

  return promise;
}

function scheduleStorageSync(delay, logSuccess) {
  if (typeof FS === 'undefined' || typeof FS.syncfs !== 'function') return;
  Module.__inbeStorageSyncPending = true;
  Module.__inbeStorageSyncLogSuccess = Module.__inbeStorageSyncLogSuccess || !!logSuccess;
  if (Module.__inbeStorageSyncTimer) clearTimeout(Module.__inbeStorageSyncTimer);

  Module.__inbeStorageSyncTimer = setTimeout(function() {
    Module.__inbeStorageSyncTimer = 0;
    runStorageSync(delay);
  }, delay);
}

function flushStorageSync(logSuccess) {
  if (typeof FS === 'undefined' || typeof FS.syncfs !== 'function') return Promise.resolve(false);
  Module.__inbeStorageSyncPending = true;
  Module.__inbeStorageSyncLogSuccess = Module.__inbeStorageSyncLogSuccess || !!logSuccess;
  if (Module.__inbeStorageSyncTimer) {
    clearTimeout(Module.__inbeStorageSyncTimer);
    Module.__inbeStorageSyncTimer = 0;
  }
  return runStorageSync(0);
}

function flushStorageBeforePageSuspends() {
  flushStorageSync(false);
}

window.addEventListener('pagehide', flushStorageBeforePageSuspends);
window.addEventListener('beforeunload', flushStorageBeforePageSuspends);
document.addEventListener('visibilitychange', function() {
  if (document.visibilityState === 'hidden') flushStorageBeforePageSuspends();
});

var Module = {
  __inbeAppReady: false,
  __inbeRuntimeReady: false,
  __inbeRenderer: selectedRenderer(),
  __inbeStorageMounted: false,
  __inbeStorageLastOk: false,
  __inbeStorageLastError: '',
  __inbeStorageLastSuccessMs: 0,
  __inbeStorageSyncPromise: null,
  __inbeStorageSyncResolve: null,
  __inbeScheduleStorageSync: scheduleStorageSync,
  __inbeFlushStorageSync: flushStorageSync,
  preRun: [function() {
    reportStorageOriginProblem();

    if (typeof FS === 'undefined' || typeof IDBFS === 'undefined') {
      Module.__inbeStorageLastError = 'idbfs unavailable';
      console.error('IDBFS unavailable');
      return;
    }

    try {
      FS.mkdir('/home');
    } catch (e) {}

    try {
      FS.mount(IDBFS, { root: '/' }, '/home');
    } catch (e) {
      if (e.errno !== 10 && String(e).indexOf('already mounted') === -1) {
        Module.__inbeStorageLastError = e && e.message ? e.message : String(e);
        console.error('IDBFS mount failed:', e);
        return;
      }
    }
    Module.__inbeStorageMounted = true;

    addRunDependency('breathing-idbfs');
    FS.syncfs(true, function(err) {
      if (err) {
        Module.__inbeStorageLastError = err && err.message ? err.message : String(err);
        console.error('IDBFS init sync failed:', err);
      } else {
        Module.__inbeStorageLastOk = true;
        Module.__inbeStorageLastError = '';
        Module.__inbeStorageLastSuccessMs = Date.now();
        console.log('IDBFS initialized');
      }
      removeRunDependency('breathing-idbfs');
    });
  }],
  postRun: [function() {
    markRuntimeReady();
  }],
  locateFile: function(path, prefix) {
    if (path === 'index.wasm' || path === 'index.data') {
      return prefix + path + '?v=WEB_CACHE_BUSTER';
    }
    return prefix + path;
  },
  print: function(text) {
    if (arguments.length > 1) text = Array.prototype.slice.call(arguments).join(' ');
    Module.__inbeLastLog = text;
    noteAppReadyFromLog(text);
    mirrorRuntimeLog(text, false);
  },
  printErr: function(text) {
    if (arguments.length > 1) text = Array.prototype.slice.call(arguments).join(' ');
    Module.__inbeLastLog = text;
    noteAppReadyFromLog(text);
    mirrorRuntimeLog(text, true);
  },
  canvas: (function() {
    var canvas = document.getElementById('canvas') || document.querySelector('canvas.emscripten');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'emscripten';
      canvas.id = 'canvas';
      canvas.width = 320;
      canvas.height = 560;
      canvas.tabIndex = -1;
      var frame = document.getElementById('canvas-frame') || document.body;
      frame.appendChild(canvas);
    }
    canvas.addEventListener('contextmenu', function(e) {
      var rect = canvas.getBoundingClientRect();
      var width = canvas.width || rect.width || 1;
      var height = canvas.height || rect.height || 1;

      e.preventDefault();
      Module.__kryonContextClick = {
        x: Math.round((e.clientX - rect.left) * width / Math.max(1, rect.width)),
        y: Math.round((e.clientY - rect.top) * height / Math.max(1, rect.height)),
        time: Date.now()
      };
    }, false);
    return canvas;
  })(),
  setStatus: function(text) {
    if (!Module.setStatus.last) Module.setStatus.last = { time: Date.now(), text: '' };
    if (text === Module.setStatus.last.text) return;

    var match = text.match(/([^(]+)\((\d+(\.\d+)?)\/(\d+)\)/);
    var now = Date.now();
    if (match && now - Module.setStatus.last.time < 30) return;

    Module.setStatus.last.time = now;
    Module.setStatus.last.text = text;

    if (match) {
      statusElement.textContent = match[1];
      progressElement.value = parseInt(match[2], 10) * 100;
      progressElement.max = parseInt(match[4], 10) * 100;
      progressElement.hidden = false;
    } else {
      statusElement.textContent = text;
      progressElement.hidden = true;
      if (!text) hideLoadingScreen();
    }
  },
  totalDependencies: 0,
  monitorRunDependencies: function(left) {
    this.totalDependencies = Math.max(this.totalDependencies, left);
    Module.setStatus(left ? 'Preparing... (' + (this.totalDependencies - left) + '/' + this.totalDependencies + ')' : 'All downloads complete.');
  }
};
globalThis.Module = Module;

function launchPracticeId(value) {
  switch (value) {
    case 'whm':
      return 0;
    case 'meditation':
      return 1;
    case 'sun_salutation':
      return 2;
    default:
      return -1;
  }
}

// A launch command runs once. Route changes keep the page query, so remove the
// command from the address; reloading must not start the practice again.
function clearLaunchCommand(params) {
  var query;
  params.delete('launch');
  params.delete('practice');
  query = params.toString();
  window.history.replaceState(window.history.state, '',
    window.location.pathname + (query ? '?' + query : '') + window.location.hash);
}

function runLaunchCommand() {
  var params = new URLSearchParams(window.location.search || '');
  var launch = params.get('launch');
  var practice = params.get('practice');
  var practiceId;

  if (launch) clearLaunchCommand(params);
  if (launch === 'break-settings') {
    extensionCallExport('app_web_extension_open_break_settings');
    return;
  }
  if (launch === 'habits') {
    extensionCallExport('app_web_extension_open_habits');
    return;
  }
  if (launch !== 'start-practice') return;
  practiceId = launchPracticeId(practice);
  if (practiceId < 0 || typeof Module._app_web_launch_practice !== 'function') return;
  Module._app_web_launch_practice(practiceId);
}

Module.setStatus('Downloading...');
window.onerror = function() {
  Module.setStatus('Exception thrown, see JavaScript console');
  Module.setStatus = function(text) {
    if (text) Module.printErr('[post-exception status] ' + text);
  };
};

(function() {
  var backgroundTimer = 0;
  var lastBackgroundTick = 0;

  function callExport(name, args) {
    if (!Module || !Module.__inbeRuntimeReady) return 0;
    var fn = Module && Module['_' + name];
    if (typeof fn !== 'function') return 0;
    try {
      return fn.apply(null, args || []);
    } catch (e) {
      console.error('Web background callback failed:', name, e);
      return 0;
    }
  }

  function playInBackgroundEnabled() {
    return callExport('app_web_get_play_in_background') ? true : false;
  }

  function resumeWebAudio() {
    var miniaudio = window.miniaudio;
    if (!miniaudio || !miniaudio.devices) return;
    miniaudio.devices.forEach(function(device) {
      if (!device || !device.webaudio || device.state !== miniaudio.device_state.started) return;
      if (device.webaudio.state !== 'running') {
        device.webaudio.resume().catch(function(error) {
          console.error('Failed to resume web audio:', error);
        });
      }
    });
  }

  function runBackgroundTick() {
    var now = performance.now();
    var elapsed = lastBackgroundTick ? now - lastBackgroundTick : 0;
    lastBackgroundTick = now;
    resumeWebAudio();
    if (elapsed > 0) callExport('app_web_background_tick', [Math.max(1, Math.round(elapsed))]);
  }

  function stopBackgroundTimer() {
    if (backgroundTimer) {
      clearInterval(backgroundTimer);
      backgroundTimer = 0;
    }
    lastBackgroundTick = 0;
  }

  function startBackgroundTimer() {
    if (backgroundTimer || !playInBackgroundEnabled()) return;
    lastBackgroundTick = performance.now();
    runBackgroundTick();
    backgroundTimer = setInterval(runBackgroundTick, 250);
  }

  function applyVisibilityState() {
    var hidden = document.hidden;
    if (hidden) {
      callExport('app_web_set_backgrounded', [1]);
      startBackgroundTimer();
    } else {
      runBackgroundTick();
      stopBackgroundTimer();
      callExport('app_web_set_backgrounded', [0]);
      resumeWebAudio();
    }
  }

  document.addEventListener('visibilitychange', applyVisibilityState, false);
  window.addEventListener('pagehide', function() {
    callExport('app_web_set_backgrounded', [1]);
    runBackgroundTick();
  }, false);
  window.addEventListener('pageshow', applyVisibilityState, false);
  window.addEventListener('blur', function() {
    if (document.hidden) applyVisibilityState();
  }, false);
  window.addEventListener('focus', applyVisibilityState, false);
})();
