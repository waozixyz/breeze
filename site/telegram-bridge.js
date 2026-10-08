/* Telegram host facilities only. Ziran verifies identity, grants and keys. */
(function (global) {
  'use strict';

  const storageKey = 'inbe_delegate_v1';
  // Instances using one SDK share a mutation barrier, including late writes.
  const storageStates = new WeakMap();
  const capsuleFields = ['format', 'signing_private', 'encryption_public',
    'encryption_private', 'owner_public_key', 'grant'];
  const grantFields = ['version', 'account_id', 'grant_id', 'request_id', 'app_id',
    'client_id', 'node_id', 'audience', 'signing_key', 'encryption_key', 'issued_at',
    'not_before', 'expires_at', 'nonce', 'bot_id', 'telegram_id', 'scopes', 'signature'];
  const scopeFields = ['collection', 'visibility', 'read', 'write', 'key_id', 'key_envelope'];

  function exactFields(value, names) {
    return value !== null && typeof value === 'object' && !Array.isArray(value) &&
      Object.keys(value).length === names.length &&
      names.every(function (name) { return Object.hasOwn(value, name); });
  }

  function hex(value, length) {
    return typeof value === 'string' && value.length === length && /^[0-9a-f]+$/.test(value);
  }

  // JSON.parse alone accepts duplicate fields. Scan the complete JSON first,
  // including decoded escaped keys; the built-in parser then checks grammar.
  function canonicalJSON(text) {
    let at = 0;
    function space() {
      while (at < text.length && /[\t\n\r ]/.test(text[at])) at += 1;
    }
    function string() {
      if (text[at] !== '"') throw new Error('invalid delegate capsule');
      const start = at;
      at += 1;
      while (at < text.length) {
        if (text[at] === '\\') {
          at += 2;
        } else if (text[at] === '"') {
          at += 1;
          return JSON.parse(text.slice(start, at));
        } else {
          at += 1;
        }
      }
      throw new Error('invalid delegate capsule');
    }
    function value(depth) {
      space();
      if (depth > 24 || at >= text.length) throw new Error('invalid delegate capsule');
      if (text[at] === '"') {
        string();
      } else if (text[at] === '{' || text[at] === '[') {
        const object = text[at] === '{';
        const end = object ? '}' : ']';
        const keys = new Set();
        at += 1;
        space();
        if (text[at] === end) { at += 1; return; }
        while (at < text.length) {
          if (object) {
            const key = string();
            if (!/^[a-z0-9_]+$/.test(key) || keys.has(key)) {
              throw new Error('invalid delegate capsule');
            }
            keys.add(key);
            space();
            if (text[at] !== ':') throw new Error('invalid delegate capsule');
            at += 1;
          }
          value(depth + 1);
          space();
          if (text[at] === end) { at += 1; return; }
          if (text[at] !== ',') throw new Error('invalid delegate capsule');
          at += 1;
          space();
        }
        throw new Error('invalid delegate capsule');
      } else {
        const start = at;
        while (at < text.length && !/[\t\n\r ,}\]]/.test(text[at])) at += 1;
        if (at === start) throw new Error('invalid delegate capsule');
      }
    }
    value(0);
    space();
    if (at !== text.length) throw new Error('invalid delegate capsule');
    return JSON.parse(text);
  }

  function capsuleValid(text) {
    if (typeof text !== 'string' || text.length === 0 || text.length > 65536) return false;
    try {
      const capsule = canonicalJSON(text);
      if (!exactFields(capsule, capsuleFields) || capsule.format !== 'inbe-delegate-v1' ||
          !hex(capsule.signing_private, 128) || !hex(capsule.encryption_public, 2368) ||
          !hex(capsule.encryption_private, 4800) || !hex(capsule.owner_public_key, 2624)) return false;
      const grant = capsule.grant;
      if (!exactFields(grant, grantFields) || grant.version !== 1 || grant.app_id !== 'inbe' ||
          !hex(grant.account_id, 64) || !hex(grant.grant_id, 32) || !hex(grant.request_id, 32) ||
          !hex(grant.client_id, 64) || !hex(grant.node_id, 64) || !hex(grant.signing_key, 64) ||
          !hex(grant.encryption_key, 2368) || !hex(grant.nonce, 32) || !hex(grant.signature, 4840) ||
          grant.encryption_key !== capsule.encryption_public ||
          !Number.isSafeInteger(grant.bot_id) || grant.bot_id <= 0 ||
          !Number.isSafeInteger(grant.telegram_id) || grant.telegram_id <= 0 ||
          grant.telegram_id > 4503599627370495 ||
          !Number.isSafeInteger(grant.issued_at) || !Number.isSafeInteger(grant.not_before) ||
          !Number.isSafeInteger(grant.expires_at) || grant.issued_at <= 0 ||
          grant.not_before < grant.issued_at || grant.expires_at <= grant.not_before ||
          grant.expires_at - grant.issued_at > 2592000 ||
          !Array.isArray(grant.scopes) || grant.scopes.length !== 1) return false;
      const audience = new URL(grant.audience);
      if (audience.protocol !== 'https:' || audience.username || audience.password ||
          audience.search || audience.hash) return false;
      const scope = grant.scopes[0];
      return exactFields(scope, scopeFields) && scope.collection === 'private.inbe.v2.lumi' &&
        scope.visibility === 'private' && scope.key_id === 'inbe-lumi-1' &&
        typeof scope.read === 'boolean' && typeof scope.write === 'boolean' &&
        (scope.read || scope.write) && typeof scope.key_envelope === 'string' &&
        scope.key_envelope.length > 0 && scope.key_envelope.length <= 16384;
    } catch (_) {
      return false;
    }
  }

  function createInbeTelegramBridge(options) {
    const telegram = options && options.telegram;
    const webApp = telegram && telegram.WebApp;
    const initData = webApp && typeof webApp.initData === 'string' ? webApp.initData : '';
    let entryId = '';
    let valid = false;
    try {
      const target = new URL(options.href);
      const query = target.search;
      valid = target.protocol === 'https:' && !target.username && !target.password &&
        /^\?r=[0-9a-f]{32}$/.test(query) && initData.length > 0 && initData.length <= 16384;
      if (valid) entryId = query.slice(3);
    } catch (_) {
      valid = false;
    }
    const context = Object.freeze({entryId: entryId, initData: initData, valid: valid});
    const secure = webApp && webApp.SecureStorage;
    const available = secure && ['getItem', 'setItem', 'removeItem'].every(function (method) {
      return typeof secure[method] === 'function';
    });
    let memory = null;
    let storageEnabled = Boolean(available);
    let generation = 0;
    let memoryGeneration = 0;
    let state = {generation: 0, readable: true, mutation: Promise.resolve()};
    if (available) {
      if (!storageStates.has(secure)) storageStates.set(secure, state);
      state = storageStates.get(secure);
    }

    // Mutation settlement is independent of the caller deadline. An SDK write
    // that times out may still take effect later; keep newer mutations queued
    // until its actual callback, and disable restores in the meantime.
    function storageMutation(method, args) {
      return new Promise(function (resolve) {
        let settled = false;
        function finish(error, value) {
          if (settled) return;
          settled = true;
          resolve({error: Boolean(error), value: value});
        }
        try {
          secure[method].apply(secure, args.concat(finish));
        } catch (_) {
          finish(true, null);
        }
      });
    }

    function callerDeadline(operation, fallback) {
      return new Promise(function (resolve) {
        let settled = false;
        let timer;
        function finish(value) {
          if (settled) return;
          settled = true;
          if (timer !== undefined) global.clearTimeout(timer);
          resolve(value);
        }
        if (typeof global.setTimeout === 'function') {
          timer = global.setTimeout(function () { finish(fallback); }, 3000);
        }
        operation.then(finish, function () { finish(fallback); });
      });
    }

    function storageCall(method, args) {
      return new Promise(function (resolve) {
        let settled = false;
        let timer;
        function finish(error, value) {
          if (settled) return;
          settled = true;
          if (timer !== undefined) global.clearTimeout(timer);
          resolve({error: Boolean(error), value: value});
        }
        if (typeof global.setTimeout === 'function') {
          timer = global.setTimeout(function () { finish(true, null); }, 3000);
        }
        try {
          secure[method].apply(secure, args.concat(finish));
        } catch (_) {
          finish(true, null);
        }
      });
    }

    const bridge = {
      context: context,
      contextCurrent: function () {
        return valid && webApp && webApp.initData === context.initData;
      },
      saveDelegate: async function (capsule) {
        if (!capsuleValid(capsule)) throw new Error('invalid delegate capsule');
        const current = ++generation;
        const storageGeneration = ++state.generation;
        memory = capsule;
        memoryGeneration = storageGeneration;
        storageEnabled = false;
        state.readable = false;
        const operation = state.mutation.then(async function () {
          if (!available || storageGeneration !== state.generation) return {persistent: false};
          const removed = await storageMutation('removeItem', [storageKey]);
          if (removed.error || removed.value !== true || storageGeneration !== state.generation) {
            return {persistent: false};
          }
          const result = await storageMutation('setItem', [storageKey, capsule]);
          if (storageGeneration !== state.generation || current !== generation) return {persistent: false};
          storageEnabled = !result.error && result.value === true;
          state.readable = storageEnabled;
          return {persistent: storageEnabled};
        });
        state.mutation = operation.then(function () {});
        return callerDeadline(operation, {persistent: false});
      },
      loadDelegate: async function () {
        if (available && memoryGeneration !== state.generation) {
          memory = null;
          memoryGeneration = state.generation;
        }
        if (memory !== null) return memory;
        if (!storageEnabled || !state.readable) return null;
        const current = generation;
        const storageGeneration = state.generation;
        const result = await storageCall('getItem', [storageKey]);
        if (current !== generation || storageGeneration !== state.generation ||
            !storageEnabled || !state.readable) return memory;
        if (result.error) {
          storageEnabled = false;
          return null;
        }
        if (result.value === null || result.value === undefined) return null;
        if (!capsuleValid(result.value)) {
          await bridge.clearDelegate();
          return memory;
        }
        memory = result.value;
        memoryGeneration = storageGeneration;
        return memory;
      },
      clearDelegate: async function () {
        ++generation;
        const storageGeneration = ++state.generation;
        memory = null;
        memoryGeneration = storageGeneration;
        storageEnabled = false;
        state.readable = false;
        const operation = state.mutation.then(async function () {
          if (!available || storageGeneration !== state.generation) return;
          await storageMutation('removeItem', [storageKey]);
        });
        state.mutation = operation.then(function () {});
        await callerDeadline(operation, undefined);
      }
    };
    return Object.freeze(bridge);
  }

  global.createInbeTelegramBridge = createInbeTelegramBridge;
  global.InbeTelegramBridge = createInbeTelegramBridge({
    telegram: global.Telegram,
    href: global.location ? global.location.href : ''
  });
}(globalThis));
