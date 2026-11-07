// Finite browser-fixture operations. A deadline also aborts the owned transport.
export function withDeadline(operation, milliseconds, message, parentSignal) {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0)
    return Promise.reject(new Error('deadline must be a positive finite duration'));
  return new Promise((resolve, reject) => {
    const controller = new AbortController();
    let finished = false;
    const finish = (error, value) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      parentSignal?.removeEventListener('abort', parentAborted);
      if (error) reject(error); else resolve(value);
    };
    const abort = reason => {
      controller.abort(reason);
      finish(reason);
    };
    const parentAborted = () => abort(parentSignal.reason || new Error('fixture aborted'));
    const timer = setTimeout(() => abort(new Error(message)), milliseconds);
    if (parentSignal?.aborted) {
      parentAborted();
      return;
    }
    parentSignal?.addEventListener('abort', parentAborted, { once: true });
    Promise.resolve().then(() => operation(controller.signal)).then(
      value => finish(null, value), error => finish(error));
  });
}

export function fetchWithDeadline(url, options, milliseconds, signal, consume = response => response) {
  return withDeadline(async requestSignal => {
    const response = await fetch(url, { ...options, signal: requestSignal });
    return await consume(response);
  }, milliseconds, `HTTP request timed out after ${milliseconds}ms: ${url}`, signal);
}

export function connectProtocol(url, label, milliseconds, signal) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const pending = new Map();
    const events = [];
    let nextId = 1;
    let closed = '';
    const fail = error => {
      if (closed) return;
      closed = error.message;
      clearTimeout(connectTimer);
      signal?.removeEventListener('abort', aborted);
      reject(error);
      for (const item of pending.values()) {
        clearTimeout(item.timer);
        item.reject(new Error(`${item.method}: ${closed}`));
      }
      pending.clear();
      try { ws.close(); } catch {}
    };
    const aborted = () => fail(signal.reason || new Error('fixture aborted'));
    const connectTimer = setTimeout(() => fail(new Error(
      `${label} connection timed out after ${milliseconds}ms`)), milliseconds);
    if (signal?.aborted) {
      aborted();
      return;
    }
    signal?.addEventListener('abort', aborted, { once: true });
    ws.addEventListener('open', () => {
      clearTimeout(connectTimer);
      if (closed) return;
      resolve({
        events,
        send(method, params = {}) {
          if (closed) return Promise.reject(new Error(`${method}: ${closed}`));
          const id = nextId++;
          return new Promise((resolveSend, rejectSend) => {
            const timer = setTimeout(() => fail(new Error(
              `${label} ${method} timed out after ${milliseconds}ms`)), milliseconds);
            pending.set(id, { resolve: resolveSend, reject: rejectSend, method, timer });
            try { ws.send(JSON.stringify({ id, method, params })); }
            catch (error) { fail(error); }
          });
        },
        close() { fail(new Error(`${label} connection closed by fixture`)); }
      });
    });
    ws.addEventListener('message', event => {
      let message;
      try { message = JSON.parse(event.data); }
      catch { fail(new Error(`${label} returned invalid JSON`)); return; }
      const item = pending.get(message.id);
      if (item) {
        pending.delete(message.id);
        clearTimeout(item.timer);
        if (message.error)
          item.reject(new Error(`${item.method}: ${message.error.message || message.message || message.error}`));
        else item.resolve(message.result || {});
      } else if (message.method) events.push(message);
    });
    ws.addEventListener('error', event => fail(new Error(event.message || `${label} WebSocket error`)));
    ws.addEventListener('close', event => fail(new Error(`${label} connection closed (${event.code})`)));
  });
}


export function validateChromiumSocketPath(directory) {
  const socket = `${directory}/org.chromium.Chromium.XXXXXX/SingletonSocket`;
  if (Buffer.byteLength(socket) >= 108)
    throw new Error('WEB_SMOKE_PROFILE_ROOT is too long for Chromium Unix sockets; choose a shorter directory inside this project');
}
