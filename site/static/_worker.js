export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (/^\/build\/(web|telegram)\/index\.data$/.test(url.pathname)) {
      const compressed = new URL(url);
      compressed.pathname += '.gz';
      const response = await env.ASSETS.fetch(new Request(compressed, request));
      if (response.ok && !response.headers.get('Content-Type')?.includes('text/html')) {
        const headers = new Headers(response.headers);
        headers.set('Content-Encoding', 'gzip');
        headers.set('Content-Type', 'application/octet-stream');
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
