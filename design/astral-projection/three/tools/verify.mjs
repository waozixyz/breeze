// Integration test: launch ONLY an owned private X server and browser.
import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync, existsSync, rmSync, mkdtempSync } from 'node:fs'
import { resolve, join } from 'node:path'
import assert from 'node:assert/strict'
import { startServer, INBE_ROOT } from '../../../promo-film/three/tools/serve.mjs'
import { sample, phases } from '../src/timeline.js'

const root = INBE_ROOT
const out = join(root, 'build/astral-threejs')
mkdirSync(out, { recursive: true })
const temp = join(root, 'build/atmp')
mkdirSync(temp, { recursive: true })
const env = { ...process.env, TMPDIR: temp, HARMONY_DESKTOP_RECOVERY: '0' }
for (const key of ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER']) delete env[key]
const items = JSON.parse(readFileSync(join(root, 'design/astral-projection/three/src/sessions.json')))
const source = resolve(root, '../../modules/practices/astral_projection')
const text = Object.fromEntries([...readFileSync(join(source, 'text/en.txt'), 'utf8').matchAll(/\[([^\]]+)\]\n(.*?)\n---/gs)].map(m => [m[1], m[2]]))
const catalogue = JSON.parse(readFileSync(join(source, 'catalogue.json'))).practices
assert.equal(JSON.parse(readFileSync(join(root, 'design/promo-film/three/node_modules/three/package.json'))).version, '0.169.0')
assert.equal(items.length, 6)
for (const [n, item] of items.entries()) {
    assert.equal(item.id, catalogue[n].id)
    const session = JSON.parse(readFileSync(join(source, 'sessions', `${item.id}.json`)))
    assert.equal(item.duration, session.duration)
    assert.equal(phases[item.id].length, session.cues.length)
    assert.deepEqual(item.cues.map(({ second, key }) => ({ second, key })), session.cues)
    for (const [i, cue] of item.cues.entries()) {
        assert.equal(cue.text, text[cue.key])
        assert.equal(sample(item, cue.second).index, i)
        if (i) assert.equal(sample(item, cue.second - 0.001).index, i - 1)
    }
    assert.equal(sample(item, item.duration + 1).time, item.duration)
}
const { server } = await startServer()
const port = server.address().port
const profile = mkdtempSync(join(temp, 'c-'))
const browser = spawn('xvfb-run', ['-a', 'chromium', '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--remote-allow-origins=*', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--window-size=1100,1000', 'about:blank'], { env, stdio: ['ignore', 'ignore', 'pipe'] })
let diagnostics = ''
browser.stderr.on('data', bytes => { diagnostics = (diagnostics + bytes).slice(-6000) })
const delay = ms => new Promise(done => setTimeout(done, ms))
const report = { source: 'canonical practices working tree', cueBoundaries: 0, frames: [], errors: [] }
let socket
let id = 0
const pending = new Map()
async function cdp(method, params = {}) {
    const seq = ++id
    const result = new Promise((done, fail) => pending.set(seq, { done, fail }))
    socket.send(JSON.stringify({ id: seq, method, params }))
    return result
}
async function evaluate(expression) {
    const value = await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (value.exceptionDetails) throw new Error(JSON.stringify(value.exceptionDetails))
    return value.result.value
}
async function until(expression) {
    for (let n = 0; n < 100; n += 1) {
        if (await evaluate(expression)) return
        await delay(150)
    }
    throw new Error(`Timed out: ${expression}`)
}
async function frame(name) {
    const { data } = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
    const path = join(out, `${name}.png`)
    writeFileSync(path, Buffer.from(data, 'base64'))
    report.frames.push(path.replace(root + '/', ''))
}
try {
    const active = join(profile, 'DevToolsActivePort')
    for (let n = 0; n < 150 && !existsSync(active); n += 1) await delay(100)
    assert(existsSync(active), diagnostics)
    const debugPort = readFileSync(active, 'utf8').split('\n')[0]
    const tabs = await fetch(`http://127.0.0.1:${debugPort}/json`).then(r => r.json())
    socket = new WebSocket(tabs[0].webSocketDebuggerUrl)
    await new Promise(done => socket.addEventListener('open', done, { once: true }))
    socket.addEventListener('message', event => {
        const msg = JSON.parse(event.data)
        if (msg.id) {
            const task = pending.get(msg.id)
            pending.delete(msg.id)
            if (msg.error) task.fail(new Error(JSON.stringify(msg.error)))
            else task.done(msg.result)
        } else if (msg.method === 'Runtime.exceptionThrown') report.errors.push(msg.params.exceptionDetails.exception?.description ?? JSON.stringify(msg.params.exceptionDetails))
        else if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') report.errors.push(msg.params.args.map(arg => arg.value ?? arg.description).join(' '))
        else if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') report.errors.push(msg.params.entry.text + ' ' + msg.params.entry.url)
    })
    await cdp('Runtime.enable')
    await cdp('Log.enable')
    await cdp('Page.enable')
    await cdp('Page.navigate', { url: `http://127.0.0.1:${port}/design/astral-projection/three/index.html` })
    await until('Boolean(window.astral)')
    for (const [n, item] of items.entries()) {
        await evaluate(`document.querySelector('#exercise').value = ${n}; document.querySelector('#exercise').dispatchEvent(new Event('change'))`)
        for (const [i, cue] of item.cues.entries()) {
            const state = await evaluate(`window.astral.seek(${cue.second})`)
            assert.equal(state.cue, cue.key)
            assert.equal(state.caption, text[cue.key])
            assert.equal(await evaluate('document.querySelector("#caption").textContent'), text[cue.key])
            if (i) assert.equal((await evaluate(`window.astral.seek(${cue.second - 0.01})`)).index, i - 1)
            report.cueBoundaries += 1
        }
        for (const i of [0, Math.floor(item.cues.length / 2), item.cues.length - 3, item.cues.length - 1]) {
            const t = item.cues[i].second + 30
            await evaluate(`window.astral.seek(${t})`)
            const pixels = await evaluate('window.astral.pixels()')
            assert(pixels.bright > 300, `Blank ${item.id} at ${t}: ${JSON.stringify(pixels)}`)
            await frame(`${item.id}-${t}`)
        }
        await evaluate(`document.querySelector('#seek').value = ${item.duration}; document.querySelector('#seek').dispatchEvent(new Event('input')); document.querySelector('#play').click()`)
        await delay(150)
        assert((await evaluate('window.astral.state()')).time < 2, 'Play restarts completed session')
        await evaluate('document.querySelector("#play").click()')
        const paused = await evaluate('window.astral.state().time')
        await delay(80)
        assert.equal(await evaluate('window.astral.state().time'), paused)
        await evaluate('document.querySelector("#restart").click()')
        assert.equal(await evaluate('window.astral.state().time'), 0)
    }
    await cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true })
    await evaluate('window.dispatchEvent(new Event("resize")); window.astral.select(4); window.astral.seek(1500)')
    await frame('portrait-rope-1500')
    assert(await evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Portrait overflow')
    await cdp('Emulation.clearDeviceMetricsOverride')
    // The real promo loads Lumi, the monk and Tibetan woman; shader compile
    // errors are collected from the WebGL console rather than inferred from source.
    await cdp('Page.navigate', { url: `http://127.0.0.1:${port}/design/promo-film/three/index.html?t=38&width=960&height=540` })
    await until('Boolean(document.querySelector("#hud")?.textContent)')
    await frame('promo-shader-review')
    const errors = report.errors.filter(message => !message.includes('favicon.ico'))
    assert.deepEqual(errors, [], 'Browser/GLSL errors')
    report.result = 'PASS'
    writeFileSync(join(out, 'verification.json'), JSON.stringify(report, null, 2) + '\n')
    console.log(`PASS: ${report.cueBoundaries} cue boundaries; ${report.frames.length} frames; controls, portrait and promo shaders. Report: build/astral-threejs/verification.json`)
} catch (error) {
    console.error(JSON.stringify(report.errors), diagnostics.slice(-1500))
    throw error
} finally {
    if (socket) {
        try { await cdp('Browser.close') } catch {}
        socket.close()
    }
    browser.kill('SIGTERM')
    server.close()
    await delay(600)
    rmSync(profile, { recursive: true, force: true })
}
