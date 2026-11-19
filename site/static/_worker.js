function assetRequest(url, request, method = 'GET') {
  const headers = new Headers(request.headers);
  for (const name of ['range', 'if-range', 'if-none-match', 'if-modified-since']) {
    headers.delete(name);
  }
  return new Request(url, { method, headers });
}

function preferZstd(request) {
  const accepted = request.cf?.clientAcceptEncoding ?? request.headers.get('Accept-Encoding') ?? '';
  const quality = new Map();
  for (const item of accepted.toLowerCase().split(',')) {
    const [coding, parameter] = item.trim().split(';');
    if (parameter === undefined) {
      quality.set(coding, 1);
    } else {
      const match = /^\s*q\s*=\s*(0(?:\.\d{0,3})?|1(?:\.0{0,3})?)\s*$/.exec(parameter);
      if (match) quality.set(coding.trim(), Number(match[1]));
    }
  }
  const zstd = quality.get('zstd') ?? 0;
  return zstd > 0 && zstd >= (quality.get('gzip') ?? quality.get('*') ?? 0);
}

function varyWasm(headers) {
  headers.append('Vary', 'Accept-Encoding');
  headers.append('Cache-Control', 'no-transform');
}

async function multipartAsset(url, request, env, manifestResponse, coding) {
  const manifest = await manifestResponse.json().catch(() => null);
  const basename = url.pathname.slice(url.pathname.lastIndexOf('/') + 1);
  const extension = coding === 'zstd' ? 'zstd' : 'gz';
  if (!manifest || !Array.isArray(manifest.parts) || manifest.parts.length === 0 ||
      !manifest.parts.every(part => typeof part === 'string' &&
        part.startsWith(basename + '.' + extension + '.') && !/[\\/]/.test(part)) ||
      !/^[a-f0-9]{64}$/.test(manifest.sha256) ||
      (coding === 'zstd' && (!Number.isSafeInteger(manifest.size) || manifest.size <= 0))) {
    return new Response('Invalid asset manifest', { status: 502 });
  }
  const headers = new Headers(manifestResponse.headers);
  headers.delete('Content-Length');
  headers.delete('Content-Range');
  headers.delete('Accept-Ranges');
  headers.set('Content-Encoding', coding);
  if (basename.endsWith('.wasm')) varyWasm(headers);
  headers.set('Content-Type', basename.endsWith('.wasm')
    ? 'application/wasm' : 'application/octet-stream');
  const etag = '"' + manifest.sha256 + '"';
  headers.set('ETag', etag);
  const matches = (request.headers.get('If-None-Match') || '').split(',');
  if (matches.some(value => value.trim() === etag || value.trim() === '*')) {
    return new Response(null, { status: 304, headers });
  }
  if (request.method === 'HEAD') {
    return new Response(null, { headers });
  }
  if (coding === 'zstd') headers.set('Content-Length', String(manifest.size));
  // Fixed length avoids HTTP/1.1 chunked Zstd issues in WebKit.
  const { readable, writable } = coding === 'zstd' && typeof FixedLengthStream === 'function'
    ? new FixedLengthStream(manifest.size) : new TransformStream();
  async function pump() {
    for (const part of manifest.parts) {
      const partUrl = new URL(url);
      partUrl.pathname = url.pathname.slice(0, url.pathname.lastIndexOf('/') + 1) + part;
      const response = await env.ASSETS.fetch(assetRequest(partUrl, request));
      if (!response.ok || !response.body ||
          response.headers.get('Content-Type')?.includes('text/html')) {
        throw new Error('Missing browser asset part');
      }
      await response.body.pipeTo(writable, { preventClose: true });
    }
    await writable.getWriter().close();
  }
  pump().catch(error => writable.abort(error).catch(() => {}));
  return new Response(readable, { headers, encodeBody: 'manual' });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (['GET', 'HEAD'].includes(request.method) &&
        /^\/build\/(web|telegram)\/index\.(data|wasm)$/.test(url.pathname)) {
      const wasm = url.pathname.endsWith('.wasm');
      const manifestUrl = new URL(url);
      if (wasm && preferZstd(request)) {
        manifestUrl.pathname = url.pathname + '.zstd.parts.json';
        const manifest = await env.ASSETS.fetch(assetRequest(manifestUrl, request));
        if (manifest.ok && manifest.headers.get('Content-Type')?.includes('application/json')) {
          const response = await multipartAsset(url, request, env, manifest, 'zstd');
          if (response.status !== 502) return response;
        }
      }
      manifestUrl.pathname = url.pathname + '.parts.json';
      const manifest = await env.ASSETS.fetch(assetRequest(manifestUrl, request));
      if (manifest.ok && manifest.headers.get('Content-Type')?.includes('application/json')) {
        return multipartAsset(url, request, env, manifest, 'gzip');
      }
      const compressed = new URL(url);
      compressed.pathname += '.gz';
      const response = await env.ASSETS.fetch(assetRequest(compressed, request, request.method));
      if (response.ok && !response.headers.get('Content-Type')?.includes('text/html')) {
        const headers = new Headers(response.headers);
        headers.set('Content-Encoding', 'gzip');
        if (wasm) varyWasm(headers);
        headers.set('Content-Type', url.pathname.endsWith('.wasm')
          ? 'application/wasm' : 'application/octet-stream');
        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers,
          encodeBody: 'manual',
        });
      }
    }
    return env.ASSETS.fetch(request);
  },
};
