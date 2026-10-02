function assetRequest(url, request, method = 'GET') {
  const headers = new Headers(request.headers);
  for (const name of ['range', 'if-range', 'if-none-match', 'if-modified-since']) {
    headers.delete(name);
  }
  return new Request(url, { method, headers });
}

async function multipartAsset(url, request, env, manifestResponse) {
  const manifest = await manifestResponse.json();
  const basename = url.pathname.slice(url.pathname.lastIndexOf('/') + 1);
  if (!Array.isArray(manifest.parts) || manifest.parts.length === 0 ||
      !manifest.parts.every(part => typeof part === 'string' &&
        part.startsWith(basename + '.gz.') && !/[\\/]/.test(part)) ||
      !/^[a-f0-9]{64}$/.test(manifest.sha256)) {
    return new Response('Invalid asset manifest', { status: 502 });
  }
  const headers = new Headers(manifestResponse.headers);
  headers.delete('Content-Length');
  headers.delete('Content-Range');
  headers.delete('Accept-Ranges');
  headers.set('Content-Encoding', 'gzip');
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
  const { readable, writable } = new TransformStream();
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
      const manifestUrl = new URL(url);
      manifestUrl.pathname += '.parts.json';
      const manifest = await env.ASSETS.fetch(assetRequest(manifestUrl, request));
      if (manifest.ok && manifest.headers.get('Content-Type')?.includes('application/json')) {
        return multipartAsset(url, request, env, manifest);
      }
      const compressed = new URL(url);
      compressed.pathname += '.gz';
      const response = await env.ASSETS.fetch(assetRequest(compressed, request, request.method));
      if (response.ok && !response.headers.get('Content-Type')?.includes('text/html')) {
        const headers = new Headers(response.headers);
        headers.set('Content-Encoding', 'gzip');
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
