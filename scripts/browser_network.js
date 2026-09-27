// Raw, bounded browser network effects. Daochi protocol and app state stay in Zi.
addToLibrary({
  $BrowserNetwork: {
    next: 1,
    http: null,
    sockets: null,
    streams: null,
    decoder: null,
    encoder: null,
    initialize() {
      if (!this.http) {
        this.http = new Map();
        this.sockets = new Map();
        this.streams = new Map();
        this.decoder = new TextDecoder('utf-8', { fatal: true });
        this.encoder = new TextEncoder();
      }
    },
    bytes(pointer, length) {
      if (!Number.isInteger(pointer) || !Number.isInteger(length) ||
          pointer < 0 || length < 0 || pointer + length > HEAPU8.length) {
        throw new Error('invalid network buffer');
      }
      return HEAPU8.subarray(pointer, pointer + length);
    },
    text(pointer, length) {
      return this.decoder.decode(this.bytes(pointer, length));
    },
    id() {
      if (this.next >= 2147483647) {
        this.next = 1;
      }
      while (this.http.has(this.next) || this.sockets.has(this.next) || this.streams.has(this.next)) {
        this.next += 1;
      }
      return this.next++;
    },
    failStream(id, task) {
      if (this.streams.get(id) !== task) return;
      task.failed = true;
      task.chunk = null;
      clearTimeout(task.timer);
      task.controller.abort();
      if (task.reader) task.reader.cancel().catch(() => {});
    },
    readStream(id, task) {
      if (this.streams.get(id) !== task || task.reading || task.done || task.failed) return;
      task.reading = true;
      task.reader.read().then(chunk => {
        task.reading = false;
        if (this.streams.get(id) !== task || task.failed) return;
        if (chunk.done) {
          task.done = true;
          clearTimeout(task.timer);
          return;
        }
        if ((!ArrayBuffer.isView(chunk.value) || chunk.value.BYTES_PER_ELEMENT !== 1) || chunk.value.length > 1048576 ||
            chunk.value.length > task.maximum - task.received) {
          this.failStream(id, task);
          return;
        }
        if (chunk.value.length === 0) {
          this.readStream(id, task);
          return;
        }
        task.received += chunk.value.length;
        task.chunk = chunk.value;
        task.offset = 0;
      }).catch(() => this.failStream(id, task));
    },
    finish(id, task, success, status) {
      if (this.http.get(id) !== task) {
        return;
      }
      clearTimeout(task.timer);
      task.done = true;
      task.success = success;
      task.status = status;
      if (!success) {
        HEAPU8[task.output] = 0;
      }
    }
  },

  browser_http_create__deps: ['$BrowserNetwork'],
  browser_http_create: (methodPointer, methodLength, urlPointer, urlLength,
                        output, capacity, timeout) => {
    BrowserNetwork.initialize();
    try {
      if (methodLength < 1 || methodLength > 31 || urlLength < 1 ||
          urlLength >= 2048 || capacity < 1 || capacity > 16777216 ||
          timeout < 1 || timeout > 900000 || BrowserNetwork.http.size >= 8) {
        return 0;
      }
      const method = BrowserNetwork.text(methodPointer, methodLength);
      const url = new URL(BrowserNetwork.text(urlPointer, urlLength));
      if (!/^[A-Za-z-]+$/.test(method) ||
          !['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
        return 0;
      }
      BrowserNetwork.bytes(output, capacity);
      HEAPU8[output] = 0;
      const id = BrowserNetwork.id();
      BrowserNetwork.http.set(id, {
        method, url: url.href, output, capacity, timeout,
        headers: new Headers(), controller: new AbortController(),
        sent: false, done: false, success: false, status: 0, timer: null
      });
      return id;
    } catch (_) {
      return 0;
    }
  },

  browser_http_header__deps: ['$BrowserNetwork'],
  browser_http_header: (id, namePointer, nameLength, valuePointer, valueLength) => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.http.get(id);
    if (!task || task.sent || nameLength < 1 || nameLength > 128 || valueLength > 8192) {
      return 0;
    }
    try {
      task.headers.append(BrowserNetwork.text(namePointer, nameLength),
        BrowserNetwork.text(valuePointer, valueLength));
      return 1;
    } catch (_) {
      return 0;
    }
  },

  browser_http_send__deps: ['$BrowserNetwork'],
  browser_http_send: (id, bodyPointer, bodyLength) => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.http.get(id);
    if (!task || task.sent || bodyLength > 16777216) {
      return 0;
    }
    let body;
    try {
      if (bodyLength > 0) {
        body = BrowserNetwork.bytes(bodyPointer, bodyLength).slice();
      }
    } catch (_) {
      return 0;
    }
    task.sent = true;
    task.timer = setTimeout(() => {
      task.controller.abort();
      BrowserNetwork.finish(id, task, false, 0);
    }, task.timeout);
    (async () => {
      let reader;
      try {
        const response = await fetch(task.url, {
          method: task.method, headers: task.headers, body,
          redirect: 'error', credentials: 'omit', cache: 'no-store',
          signal: task.controller.signal
        });
        if (BrowserNetwork.http.get(id) !== task || task.done) {
          return;
        }
        const declaredLength = Number(response.headers.get('content-length'));
        if (declaredLength >= task.capacity) {
          throw new Error('response capacity exceeded');
        }
        let length = 0;
        if (response.body) {
          reader = response.body.getReader();
          for (;;) {
            const chunk = await reader.read();
            if (BrowserNetwork.http.get(id) !== task || task.done) {
              await reader.cancel();
              return;
            }
            if (chunk.done) {
              break;
            }
            if (chunk.value.length > task.capacity - length - 1) {
              throw new Error('response capacity exceeded');
            }
            HEAPU8.set(chunk.value, task.output + length);
            length += chunk.value.length;
          }
        }
        HEAPU8[task.output + length] = 0;
        BrowserNetwork.finish(id, task, true, response.status);
      } catch (_) {
        task.controller.abort();
        if (reader) {
          try {
            await reader.cancel();
          } catch (_) {
            // Cancellation has already invalidated the transfer.
          }
        }
        BrowserNetwork.finish(id, task, false, 0);
      }
    })();
    return 1;
  },

  browser_http_poll__deps: ['$BrowserNetwork'],
  browser_http_poll: (id, statusPointer) => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.http.get(id);
    if (!task || !task.sent) {
      return 0;
    }
    if (!task.done) {
      return -1;
    }
    BrowserNetwork.http.delete(id);
    HEAP32[statusPointer >> 2] = task.status;
    return task.success ? 1 : 0;
  },

  browser_http_cancel__deps: ['$BrowserNetwork'],
  browser_http_cancel: id => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.http.get(id);
    if (!task) {
      return;
    }
    BrowserNetwork.http.delete(id);
    clearTimeout(task.timer);
    task.controller.abort();
  },

  browser_stream_open__deps: ['$BrowserNetwork'],
  browser_stream_open: (urlPointer, urlLength, maximum, timeout) => {
    BrowserNetwork.initialize();
    try {
      if (urlLength < 1 || urlLength >= 4096 || maximum < 1 || maximum > 536870912 ||
          timeout < 1 || timeout > 900000 || BrowserNetwork.streams.size >= 4) return 0;
      const url = new URL(BrowserNetwork.text(urlPointer, urlLength));
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) return 0;
      const id = BrowserNetwork.id();
      const task = { controller: new AbortController(), maximum, received: 0, total: 0,
        status: 0, reader: null, chunk: null, offset: 0, reading: false, done: false,
        failed: false, timer: null };
      BrowserNetwork.streams.set(id, task);
      task.timer = setTimeout(() => BrowserNetwork.failStream(id, task), timeout);
      fetch(url.href, { method: 'GET', redirect: 'follow', credentials: 'omit',
        signal: task.controller.signal }).then(response => {
        if (BrowserNetwork.streams.get(id) !== task || task.failed) {
          response.body?.cancel().catch(() => {});
          return;
        }
        task.status = response.status;
        const declared = Number(response.headers.get('content-length'));
        if (Number.isSafeInteger(declared) && declared > maximum) {
          BrowserNetwork.failStream(id, task);
          response.body?.cancel().catch(() => {});
          return;
        }
        if (Number.isSafeInteger(declared) && declared > 0) task.total = declared;
        if (!response.body) {
          task.done = true;
          clearTimeout(task.timer);
          return;
        }
        task.reader = response.body.getReader();
        BrowserNetwork.readStream(id, task);
      }).catch(() => BrowserNetwork.failStream(id, task));
      return id;
    } catch (_) {
      return 0;
    }
  },

  browser_stream_poll__deps: ['$BrowserNetwork'],
  browser_stream_poll: (id, output, capacity, countPointer, statusPointer, totalPointer) => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.streams.get(id);
    if (!task || capacity < 1 || capacity > 1048576) return 0;
    BrowserNetwork.bytes(output, capacity);
    HEAP32[countPointer >> 2] = 0;
    HEAP32[statusPointer >> 2] = task.status;
    HEAP32[totalPointer >> 2] = task.total;
    if (task.failed) return 0;
    if (task.chunk) {
      const length = Math.min(capacity, task.chunk.length - task.offset);
      HEAPU8.set(task.chunk.subarray(task.offset, task.offset + length), output);
      HEAP32[countPointer >> 2] = length;
      task.offset += length;
      if (task.offset === task.chunk.length) {
        task.chunk = null;
        task.offset = 0;
        BrowserNetwork.readStream(id, task);
      }
      return 1;
    }
    return task.done ? 2 : -1;
  },

  browser_stream_close__deps: ['$BrowserNetwork'],
  browser_stream_close: id => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.streams.get(id);
    if (!task) return;
    BrowserNetwork.streams.delete(id);
    clearTimeout(task.timer);
    task.controller.abort();
    if (task.reader) task.reader.cancel().catch(() => {});
    task.chunk = null;
  },

  browser_ws_open__deps: ['$BrowserNetwork'],
  browser_ws_open: (urlPointer, urlLength, protocolPointer, protocolLength,
                    authPointer, authLength, capacity) => {
    BrowserNetwork.initialize();
    try {
      if (urlLength < 1 || urlLength >= 2048 || protocolLength > 128 ||
          authLength > 8192 || capacity < 2 || capacity > 65536 ||
          BrowserNetwork.sockets.size >= 4) {
        return 0;
      }
      const url = new URL(BrowserNetwork.text(urlPointer, urlLength));
      if (!['ws:', 'wss:'].includes(url.protocol) || url.username || url.password) {
        return 0;
      }
      const protocols = [];
      if (protocolLength) {
        protocols.push(BrowserNetwork.text(protocolPointer, protocolLength));
      }
      if (authLength) {
        protocols.push(BrowserNetwork.text(authPointer, authLength));
      }
      const socket = new WebSocket(url.href, protocols);
      const id = BrowserNetwork.id();
      const task = { socket, queue: [], closed: false, capacity, timer: null };
      BrowserNetwork.sockets.set(id, task);
      const fail = code => {
        task.closed = true;
        clearTimeout(task.timer);
        socket.close(code);
      };
      task.timer = setTimeout(() => fail(1000), 10000);
      socket.onopen = () => clearTimeout(task.timer);
      socket.onerror = () => fail(1000);
      socket.onclose = () => {
        clearTimeout(task.timer);
        task.closed = true;
      };
      socket.onmessage = event => {
        if (BrowserNetwork.sockets.get(id) !== task || task.closed) {
          return;
        }
        if (typeof event.data !== 'string') {
          fail(1003);
          return;
        }
        const bytes = BrowserNetwork.encoder.encode(event.data);
        if (bytes.length >= capacity || task.queue.length >= 16) {
          fail(1009);
          return;
        }
        task.queue.push(bytes);
      };
      return id;
    } catch (_) {
      return 0;
    }
  },

  browser_ws_poll__deps: ['$BrowserNetwork'],
  browser_ws_poll: (id, output, capacity) => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.sockets.get(id);
    if (!task) {
      return 0;
    }
    if (task.closed) {
      BrowserNetwork.sockets.delete(id);
      return 0;
    }
    if (!task.queue.length) {
      return -1;
    }
    const bytes = task.queue.shift();
    if (bytes.length >= capacity) {
      task.socket.close(1009);
      BrowserNetwork.sockets.delete(id);
      return 0;
    }
    BrowserNetwork.bytes(output, capacity);
    HEAPU8.set(bytes, output);
    HEAPU8[output + bytes.length] = 0;
    return bytes.length;
  },

  browser_ws_close__deps: ['$BrowserNetwork'],
  browser_ws_close: id => {
    BrowserNetwork.initialize();
    const task = BrowserNetwork.sockets.get(id);
    if (task) {
      BrowserNetwork.sockets.delete(id);
      clearTimeout(task.timer);
      task.socket.close(1000);
    }
  }
});
