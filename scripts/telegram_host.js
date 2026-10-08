// Bounded host memory and SDK callbacks; identity/protocol policy stays in Ziran.
addToLibrary({
  $TelegramHost: {
    next: 1,
    pending: null,
    pinnedBridge: null,
    pinnedContext: null,
    pinnedInitData: null,
    pinnedEntryId: null,
    initialize() { if (!this.pending) this.pending = new Map(); },
    bridge() { this.initialize(); return globalThis.InbeTelegramBridge; },
    pin() {
      const bridge = this.bridge();
      if (!this.pinnedBridge && bridge && bridge.context &&
          typeof bridge.context.initData === 'string' && bridge.context.initData.length > 0) {
        this.pinnedBridge = bridge;
        this.pinnedContext = bridge.context;
        this.pinnedInitData = bridge.context.initData;
        this.pinnedEntryId = bridge.context.entryId;
      }
    },
    write(text, pointer, capacity) {
      if (!Number.isInteger(pointer) || !Number.isInteger(capacity) || pointer < 0 ||
          capacity < 1 || pointer + capacity > HEAPU8.length) return false;
      HEAPU8.fill(0, pointer, pointer + capacity);
      const bytes = new TextEncoder().encode(text);
      if (bytes.length >= capacity) return false;
      HEAPU8.set(bytes, pointer);
      return true;
    },
    current(expected) {
      const bridge = this.bridge();
      try {
        return Boolean(bridge && (!expected || bridge === expected) &&
          (!this.pinnedBridge || (bridge === this.pinnedBridge &&
            bridge.context === this.pinnedContext &&
            bridge.context.initData === this.pinnedInitData &&
            bridge.context.entryId === this.pinnedEntryId)) &&
          bridge.context && bridge.context.valid && bridge.contextCurrent());
      } catch (_) {
        return false;
      }
    }
  },
  telegram_context__deps: ['$TelegramHost'],
  telegram_context: function (kind, output, capacity) {
    TelegramHost.pin();
    const bridge = TelegramHost.bridge();
    if (!TelegramHost.write('', output, capacity) || !TelegramHost.current(bridge)) return 0;
    const value = kind === 1 ? bridge.context.entryId : kind === 2 ? bridge.context.initData : '';
    return value && TelegramHost.write(value, output, capacity) ? value.length : 0;
  },
  telegram_hosted__deps: ['$TelegramHost'],
  telegram_hosted: function () {
    TelegramHost.pin();
    const bridge = TelegramHost.bridge();
    return bridge && bridge.context && typeof bridge.context.initData === 'string' &&
      bridge.context.initData.length > 0 ? 1 : 0;
  },
  telegram_current__deps: ['$TelegramHost'],
  telegram_current: function () {
    TelegramHost.pin();
    return TelegramHost.current() ? 1 : 0;
  },
  telegram_storage_start__deps: ['$TelegramHost'],
  telegram_storage_start: function (action, input, length, output, capacity) {
    const bridge = TelegramHost.bridge();
    if (!TelegramHost.write('', output, capacity) || !bridge ||
        (action !== 3 && !TelegramHost.current(bridge)) ||
        ![1, 2, 3].includes(action) || !Number.isInteger(length) || length < 0 ||
        length > 65536 || !Number.isInteger(input) || input < 0 ||
        input + length > HEAPU8.length) return 0;
    if (TelegramHost.next >= 2147483647) TelegramHost.next = 1;
    while (TelegramHost.pending.has(TelegramHost.next)) TelegramHost.next += 1;
    const id = TelegramHost.next++;
    const entry = {action, bridge, output, capacity, done: false, error: false, persistent: false};
    TelegramHost.pending.set(id, entry);
    let operation;
    try {
      if (action === 1) {
        const text = new TextDecoder('utf-8', {fatal: true}).decode(HEAPU8.subarray(input, input + length));
        operation = bridge.saveDelegate(text);
      } else if (action === 2) {
        operation = bridge.loadDelegate();
      } else {
        operation = bridge.clearDelegate();
      }
    } catch (_) {
      entry.done = true;
      entry.error = true;
      return id;
    }
    Promise.resolve(operation).then(function (value) {
      if (TelegramHost.pending.get(id) !== entry) return;
      if (action !== 3 && !TelegramHost.current(entry.bridge)) {
        entry.error = true;
      } else if (action === 2 && value !== null) {
        entry.error = typeof value !== 'string' || !TelegramHost.write(value, output, capacity);
      } else if (action === 1) {
        entry.persistent = Boolean(value && value.persistent === true);
      }
      entry.done = true;
    }, function () {
      if (TelegramHost.pending.get(id) !== entry) return;
      entry.done = true;
      entry.error = true;
    });
    return id;
  },
  telegram_recovery_start__deps: ['$TelegramHost'],
  telegram_recovery_start: function (output, capacity) {
    if (!TelegramHost.current() || capacity < 17664 ||
        !TelegramHost.write('', output, capacity)) return 0;
    if (TelegramHost.next >= 2147483647) TelegramHost.next = 1;
    while (TelegramHost.pending.has(TelegramHost.next)) TelegramHost.next += 1;
    const id = TelegramHost.next++;
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = '.key,application/octet-stream';
    const entry = {action: 4, bridge: TelegramHost.bridge(), output, capacity, done: false, error: false, persistent: false,
      cancel: function () { picker.remove(); }};
    TelegramHost.pending.set(id, entry);
    picker.oncancel = function () {
      picker.remove();
      if (TelegramHost.pending.get(id) === entry) {
        entry.done = true;
        entry.error = true;
      }
    };
    picker.onchange = async function () {
      const file = picker.files && picker.files[0];
      picker.remove();
      if (TelegramHost.pending.get(id) !== entry) return;
      if (!file || file.size === 0 || file.size >= capacity) {
        entry.done = true;
        entry.error = true;
        return;
      }
      try {
        const text = await file.text();
        if (TelegramHost.pending.get(id) !== entry) return;
        entry.error = !TelegramHost.current(entry.bridge) || !TelegramHost.write(text, output, capacity);
      } catch (_) {
        entry.error = true;
      }
      entry.done = true;
    };
    picker.click();
    return id;
  },
  telegram_recovery_download__deps: ['$TelegramHost'],
  telegram_recovery_download: function (input, length) {
    if (!TelegramHost.current() || length <= 0 || length >= 17664 ||
        input < 0 || input + length > HEAPU8.length) return 0;
    const blob = new Blob([HEAPU8.slice(input, input + length)], {type: 'application/octet-stream'});
    const address = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = address;
    link.download = 'inbe-recovery.key';
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(address); }, 1000);
    return 1;
  },
  telegram_storage_poll__deps: ['$TelegramHost'],
  telegram_storage_poll: function (id, persistent) {
    TelegramHost.initialize();
    const entry = TelegramHost.pending.get(id);
    if (!entry) return -1;
    if (!Number.isInteger(persistent) || persistent < 0 || persistent % 4 !== 0 ||
        persistent + 4 > HEAPU8.length ||
        (entry.action !== 3 && !TelegramHost.current(entry.bridge))) {
      TelegramHost.pending.delete(id);
      if (entry.cancel) entry.cancel();
      TelegramHost.write('', entry.output, entry.capacity);
      return -1;
    }
    if (!entry.done) return 0;
    TelegramHost.pending.delete(id);
    HEAP32[persistent >> 2] = entry.persistent ? 1 : 0;
    if (entry.error) {
      TelegramHost.write('', entry.output, entry.capacity);
      return -1;
    }
    return 1;
  },
  telegram_storage_cancel__deps: ['$TelegramHost'],
  telegram_storage_cancel: function (id) {
    TelegramHost.initialize();
    const entry = TelegramHost.pending.get(id);
    if (!entry) return;
    TelegramHost.pending.delete(id);
    if (entry.cancel) entry.cancel();
    TelegramHost.write('', entry.output, entry.capacity);
    if (entry.action === 1) {
      try {
        Promise.resolve(entry.bridge.clearDelegate()).catch(function () {});
      } catch (_) {}
    }
  }
});
