// Exercise the built browser host with real signed accounts and a local node.
// CDP replaces transport only; the page and signed client keep their canonical
// origins. Every other network destination is blocked in this private browser.
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {readFile, writeFile, mkdir, mkdtemp, rm, cp} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve, join, extname, sep} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
// Attach the same dormant production UI driver before the runtime starts.
const driverSetup = `let testModule;
Object.defineProperty(globalThis, 'Module', {configurable:true,
 get(){return testModule;}, set(value){testModule=value;
 if(!value || value.privateDriverPrepared)return; value.privateDriverPrepared=true;
 const previous=value.preRun||[];
 value.preRun=[function(){ENV.KRYON_TEST_DRIVER='/tmp/test-driver';
 value.FS.mkdirTree('/tmp/test-driver');},...(Array.isArray(previous)?previous:[previous])];
}});`;

const project = resolve(new URL('..', import.meta.url).pathname);
const projects = resolve(project, '../../..');
const output = join(project, 'work/referral-host/web-ui');
assert.equal(spawnSync('git', ['check-ignore', '-q', output], {cwd: project}).status, 0);
await mkdir(output, {recursive: true});
const privateRoot = await mkdtemp(join(output, 'run-'));
const webRoot = resolve(process.env.WEB_TEST_ROOT || join(project, 'build/dist/web'));
const pageOrigin = 'https://inbe.waozi.xyz';
const nodeOrigin = 'https://api.waozi.xyz';
const environment = {...process.env, YUE_DESKTOP_RECOVERY: '0'};
for (const key of ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
  'SESSION_MANAGER', 'GDK_DISPLAY', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy'])
  delete environment[key];
environment.NO_PROXY = '*';
const fixture = spawn(join(projects, 'kryonlabs/daochi/work/referral-fixture.test'),
  ['-test.run', '^TestReferralBrowserFixture$', '-test.v', '-test.timeout=30m'], {
    cwd: join(projects, 'kryonlabs/daochi'),
    env: {...environment, DAOCHI_REFERRAL_FIXTURE_REPORT: join(privateRoot, 'fixture.json')},
    stdio: ['ignore', 'pipe', 'pipe']
  });
let fixtureErrors = '';
fixture.stderr.on('data', bytes => fixtureErrors = (fixtureErrors + bytes).slice(-2000));
fixture.stdout.on('data', bytes => fixtureErrors = (fixtureErrors + bytes).slice(-2000));
const browsers = new Set();
const mime = {'.js': 'text/javascript', '.wasm': 'application/wasm', '.html': 'text/html',
  '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png',
  '.css': 'text/css', '.svg': 'image/svg+xml'};
const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://localhost');
    const path = resolve(webRoot, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
    assert(path.startsWith(webRoot + sep));
    const bytes = await readFile(path);
    response.setHeader('Content-Type', mime[extname(path)] || 'application/octet-stream');
    response.end(bytes);
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise(done => server.listen(0, '127.0.0.1', done));
const staticOrigin = `http://127.0.0.1:${server.address().port}`;

async function until(predicate, label, timeout = 60000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const value = await predicate();
    if (value) return value;
    await delay(80);
  }
  throw Error(label);
}

async function stop(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise(done => child.once('exit', done));
  const signal = value => {
    try { if (child.spawnargs.includes('--headless')) process.kill(-child.pid, value); else child.kill(value); }
    catch (error) { if (error.code !== 'ESRCH') throw error; }
  };
  signal('SIGTERM');
  const timer = setTimeout(() => signal('SIGKILL'), 5000);
  await exited;
  clearTimeout(timer);
}

try {
  const metadata = await until(async () => {
    assert.equal(fixture.exitCode, null, 'Fixture stopped: ' + fixtureErrors);
    try { return JSON.parse(await readFile(join(privateRoot, 'fixture.json'), 'utf8')); }
    catch { return null; }
  }, 'Fixture did not start');
  assert(metadata.synthetic && metadata.real_mldsa && metadata.authority === nodeOrigin);
  assert(metadata.url.startsWith('http://127.0.0.1:'));

  async function control(path, body = {}) {
    const response = await fetch(metadata.url + '/fixture/' + path, {method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Fixture-Key': metadata.control_key},
      body: JSON.stringify(body)});
    assert(response.ok, 'Fixture control failed: ' + path + ' ' + response.status);
    return response.json();
  }

  async function application(name, action) {
    const profile = join(privateRoot, name);
    await mkdir(profile, {recursive: true});
    // Each prior private browser is stopped before reopening or copying its
    // profile. Discard its process locks and endpoint, which are not account
    // data and cannot identify the newly launched browser.
    for (const file of ['DevToolsActivePort', 'SingletonLock', 'SingletonSocket', 'SingletonCookie'])
      await rm(join(profile, file), {force:true});
    const browser = spawn(process.env.CHROMIUM || 'chromium', ['--headless', '--no-sandbox',
      '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
      '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'],
      {detached: true, env: environment, stdio: ['ignore', 'ignore', 'pipe']});
    browsers.add(browser);
    let errors = '';
    let stage = 'starting actual host';
    browser.stderr.on('data', bytes => errors = (errors + bytes).slice(-2000));
    let socket;
    try {
      const port = await until(async () => {
        assert.equal(browser.exitCode, null, 'Private Chromium stopped: ' + errors);
        try { return (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; }
        catch { return null; }
      }, 'Private Chromium did not start');
      const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      socket = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
      await new Promise(done => socket.addEventListener('open', done, {once: true}));
      let serial = 0;
      const pending = new Map(), transportErrors = [];
      socket.addEventListener('message', event => {
        const message = JSON.parse(event.data);
        if (pending.has(message.id)) { pending.get(message.id)(message); pending.delete(message.id); }
        if (message.method === 'Fetch.requestPaused')
          transport(message.params).catch(error => transportErrors.push(String(error)));
      });
      async function call(method, params = {}) {
        const id = ++serial;
        const answer = new Promise((done, reject) => {
          pending.set(id, done);
          setTimeout(() => {
            if (pending.delete(id)) reject(Error('CDP request timed out: ' + method + ' while ' + stage));
          }, 90000).unref();
        });
        socket.send(JSON.stringify({id, method, params}));
        const result = await answer;
        assert(!result.error, method + ': ' + result.error?.message);
        return result.result;
      }
      async function transport({requestId, request}) {
        const url = new URL(request.url);
        let target;
        if (url.origin === pageOrigin) target = staticOrigin + url.pathname + url.search;
        else if (url.origin === nodeOrigin) target = metadata.url + url.pathname + url.search;
        else { await call('Fetch.failRequest', {requestId, errorReason: 'BlockedByClient'}); return; }
        try {
          const headers = {...request.headers};
          for (const key of Object.keys(headers))
            if (['host', 'connection', 'content-length', 'accept-encoding'].includes(key.toLowerCase())) delete headers[key];
          const response = await fetch(target, {method: request.method, headers,
            body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.postData});
          const responseHeaders = [...response.headers].filter(([key]) =>
            !['content-length', 'content-encoding', 'transfer-encoding', 'connection'].includes(key));
          await call('Fetch.fulfillRequest', {requestId, responseCode: response.status,
            responseHeaders: responseHeaders.map(([name, value]) => ({name, value})),
            body: Buffer.from(await response.arrayBuffer()).toString('base64')});
        } catch (error) {
          await call('Fetch.failRequest', {requestId, errorReason: 'Failed'});
          throw error;
        }
      }
      async function evaluate(expression, awaitPromise = false) {
        const result = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise});
        assert(!result.exceptionDetails, 'Browser evaluation failed');
        return result.result.value;
      }
      await call('Runtime.enable');
      await call('Page.enable');
      await call('Page.addScriptToEvaluateOnNewDocument', {source: driverSetup});
      await call('Fetch.enable', {patterns: [{urlPattern: '*'}]});
      await call('Emulation.setDeviceMetricsOverride', {width: 900, height: 1500, deviceScaleFactor: 1, mobile: false});
      console.log(name + ': loading the actual browser host');
      await call('Page.navigate', {url: pageOrigin + '/'});
      await until(() => evaluate('Boolean(globalThis.Module?.__inbeRuntimeReady && Module.FS && Module.__inbeStorageLastOk)'), 'Actual Profile provider not ready');
      stage = 'driving ' + name + ' signup and referrals';
      console.log(name + ': actual host ready');
      let driverSerial = 0;
      async function send(verb, fields = {}) {
        const escape = value => String(value).replaceAll('\\', '\\\\').replaceAll('\t', '\\t').replaceAll('\n', '\\n');
        const text = [++driverSerial, verb, ...Object.entries(fields).map(([key, value]) => key + '=' + escape(value))].join('\t') + '\n';
        await evaluate(`(() => { const fs=Module.FS; if(fs.analyzePath('/tmp/test-driver/reply').exists)fs.unlink('/tmp/test-driver/reply'); fs.writeFile('/tmp/test-driver/command',${JSON.stringify(text)}); })()`);
        await until(() => evaluate("Module.FS.analyzePath('/tmp/test-driver/reply').exists"), 'No committed UI driver reply');
        const reply = JSON.parse(await evaluate("Module.FS.readFile('/tmp/test-driver/reply',{encoding:'utf8'})"));
        assert(reply.ok, 'UI command failed: ' + verb);
        return reply;
      }
      const tree = async () => (await send('tree')).nodes;
      const key = async value => (await tree()).find(node => node.key === value);
      async function press(selector) {
        for (let attempt = 0; attempt < 20; attempt++) {
          const nodes = await tree();
          const found = nodes.find(node => node.visible && Object.entries(selector).every(([name, value]) =>
            name === 'role' ? node.role === value || node.kind === value : node[name] === value));
          if (found) {
            await send('pointer', {real:1});
            const root=nodes[0];
            assert(root?.width>0 && root?.height>0, 'Committed UI root has no viewport');
            const point=await evaluate(`(() => {
              const canvas=document.querySelector('canvas'), r=canvas.getBoundingClientRect();
              return {x:r.left+${found.visible_x + found.visible_width / 2 - root.x}*r.width/${root.width},
                y:r.top+${found.visible_y + found.visible_height / 2 - root.y}*r.height/${root.height}};
            })()`);
            await call('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
            await call('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',buttons:1,clickCount:1,...point});
            await delay(100);
            await call('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',buttons:0,clickCount:1,...point});
            await delay(150);
            if (found.kind === 'text_field' && !(await key(found.key))?.focused) {
              await delay(350);
              continue;
            }
            return;
          }
          // The default browser can have a narrow viewport. Scroll inside
          // the committed content instead of outside it at desktop coordinates.
          const scroll = nodes.find(node => node.kind === 'scroll' && node.visible) || nodes[0];
          await send('pointer', {x: scroll.visible_x + scroll.visible_width / 2,
            y: scroll.visible_y + scroll.visible_height / 2, wheel: -6});
          await delay(450);
        }
        const nodes = await tree();
        await writeFile(join(output, name + '-missing-control.json'), JSON.stringify(nodes));
        const capture = await call('Page.captureScreenshot', {format:'png'});
        await writeFile(join(output, name + '-missing-control.png'), Buffer.from(capture.data, 'base64'));
        throw Error('Missing visible UI control: ' + JSON.stringify(selector) + '; visible=' +
          JSON.stringify(nodes.filter(node => node.visible && node.label).map(node =>
            ({key:node.key,label:node.label,kind:node.kind}))));
      }
      async function referrals() {
        if ((await tree()).some(node => node.label === 'Not now' && node.visible))
          await press({label: 'Not now', role: 'button'});
        await press({label: 'Apps', role: 'button'});
        if (await key(83110)) await press({key:83110});
        if ((await tree()).some(node => node.label === "Don't allow" && node.visible)) {
          await press({label: "Don't allow", role: 'button'});
          await until(async () => !(await tree()).some(node => node.label === 'App updates'),
            'App update consent did not close');
        }
        await press({focus_id: 6792, role: 'button'});
        await until(() => key(78030), 'Shared Profile did not open');
        await press({key: 78030});
        await until(() => key(78003), 'Referrals did not open');
      }
      async function currentAccount() {
        // Read only the public identifier from this browser's own synthetic DB.
        // Private key bytes never enter a log or test result.
        const bytes = await evaluate(`(() => {
          const fs=Module.FS, found=[];
          const walk=path=>{for(const name of fs.readdir(path)){
            if(name==='.'||name==='..')continue;
            const child=path+'/'+name;
            if(fs.isDir(fs.stat(child).mode))walk(child);
            else if(name==='inbe.db')found.push(child);
          }};
          walk('/home');
          return found.length===1 ? Array.from(fs.readFile(found[0])) : null;
        })()`);
        if (!bytes) return '';
        const database=join(privateRoot,name+'-account.db');
        await writeFile(database,Buffer.from(bytes));
        const query=spawnSync('python3',['-c',
          "import sqlite3,sys; db=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); rows=db.execute(\"SELECT value FROM settings WHERE key='sync_public_id' AND length(value)=64\").fetchall(); print(rows[0][0] if len(rows)==1 else '')",database],
          {env:environment,encoding:'utf8'});
        assert.equal(query.status,0,'Could not read the synthetic account public ID');
        return query.stdout.trim();
      }
      async function create() {
        await referrals();
        await press({key: 78005});
        await press({key:820});
        const account=await until(currentAccount,'Current web host did not save its public account ID');
        assert.match(account,/^[0-9a-f]{64}$/);
        await until(async () => {
          if (await key(78003)) return true;
          const nodes=await tree();
          if(nodes.some(node=>node.key===78030 && node.visible))await press({key:78030});
          else if(nodes.some(node=>node.label==='Not now' && node.visible))await press({label:'Not now',role:'button'});
          else if(nodes.some(node=>node.label==='Back' && node.visible))await press({label:'Back',role:'button'});
          return false;
        },'Signup did not return to referral review');
        await until(()=>key(78010),'Signed referral summary did not confirm the current account');
        return account;
      }
      async function type(text) {
        // Use the same sampled character input as the native UI driver after
        // the browser's physical pointer has given the committed field focus.
        await writeFile(join(output, name + '-text-focus.json'), JSON.stringify({
          field: await key(107),
          editor: await evaluate(`({tag:document.activeElement?.tagName,
            type:document.activeElement?.getAttribute('type')})`)
        }));
        await send('type', {text});
      }
      await action({create, referrals, press, key, tree, send, type});
      assert(await evaluate(`(async () => {
        if (Module.__inbeFlushStorageSync) return await Module.__inbeFlushStorageSync(true);
        return await new Promise(done => Module.FS.syncfs(false,error => done(!error)));
      })()`, true), 'The actual browser store did not persist its account');
      assert.deepEqual(transportErrors, [], 'Local test transport failed');
    } finally {
      socket?.close();
      await stop(browser);
      browsers.delete(browser);
    }
  }

  let inviter, friend, invitation;
  await application('inviter', async driver => {
    inviter = await driver.create();
    invitation = (await control('seed', {account_id: inviter, count: 1})).code;
  });
  await application('friend', async driver => {
    friend = await driver.create();
    assert.notEqual(friend, inviter);
    assert(!await driver.key(78006), 'New account inherited a welcome receipt');
    assert(!await driver.key(78018), 'New account inherited a referrer');
    await driver.press({key: 107});
    await driver.type(invitation);
    await until(async () => (await driver.key(107))?.value === invitation,
      'Browser invite field did not receive the typed code');
    await driver.press({key: 78024});
    assert(!await driver.key(78006), 'Review accepted without confirmation');
    await driver.press({key: 78022});
    const gift = await until(() => driver.key(78006), 'No immediate no-purchase welcome confirmation');
    assert(/\b20\b/.test(gift.label || ''), 'The immediate welcome confirmation did not show 20 Dew');
    assert(!await driver.key(78024), 'Successful claim still offered');
  });
  await cp(join(privateRoot, 'friend'), join(privateRoot, 'friend-device'), {recursive: true});
  await application('friend-device', async driver => {
    await driver.referrals();
    await until(() => driver.key(78018), 'Global referrer missing from another private browser');
    assert(!await driver.key(78024), 'Another private browser offered a duplicate claim');
  });
  await application('inviter', async driver => {
    await driver.referrals();
    const person = await until(async () => (await driver.tree()).find(node => node.label?.includes(friend)),
      'Accepted nonpurchaser absent from inviter list');
    const date = await driver.key(person.key + 1);
    assert(/\d{4}-\d{2}-\d{2}/.test(date?.label || ''), 'Acceptance date missing');
  });
  await control('stop');
  await writeFile(join(output, 'result.json'), JSON.stringify({app: 'breeze', canonical_origins: true,
    real_signed_provider: true, no_purchase_welcome: true, accepted_nonpurchaser_date: true,
    explicit_confirmation: true, second_browser_binding: true}) + '\n');
  console.log('Breeze actual browser: signed signup, explicit no-purchase gift, accepted friend/date and persistent global binding passed');
} finally {
  for (const browser of browsers) await stop(browser);
  await stop(fixture);
  await new Promise(done => server.close(done));
  await rm(privateRoot, {recursive: true, force: true});
}
