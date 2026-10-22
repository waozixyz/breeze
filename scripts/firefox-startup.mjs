// Distribution launchers may send the BiDi announcement to either stream.
// Read it as output arrives, before a large diagnostic chunk can discard it.
export function waitForFirefoxBidi(browser, timeoutMs) {
  return new Promise((resolve, reject) => {
    let tail = '';
    const diagnostic = () => tail.trim() ? `; firefox output: ${tail.trim()}` : '';
    const finish = (error, endpoint) => {
      clearTimeout(timer);
      browser.off('exit', onExit);
      browser.off('error', onError);
      for (const stream of [browser.stdout, browser.stderr]) {
        stream.off('data', onData);
        stream.resume();
      }
      if (error) reject(error);
      else resolve(endpoint.replace(/\/?$/, '/session'));
    };
    const onData = chunk => {
      const output = tail + chunk;
      const match = output.match(/WebDriver BiDi listening on (ws:\/\/[^\s]+)\s/);
      tail = output.slice(-4000);
      if (match) finish(null, match[1]);
    };
    const onExit = () => finish(new Error(`Firefox exited before BiDi was ready${diagnostic()}`));
    const onError = error => finish(error);
    const timer = setTimeout(() => finish(new Error(`timed out waiting for Firefox BiDi${diagnostic()}`)), timeoutMs);
    browser.once('exit', onExit);
    browser.once('error', onError);
    for (const stream of [browser.stdout, browser.stderr]) {
      stream.setEncoding('utf8');
      stream.on('data', onData);
    }
    if (browser.exitCode !== null) onExit();
  });
}
