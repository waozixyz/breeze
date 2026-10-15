// Renders the film frame by frame with headless Chromium on the GPU (no
// display: the inherited display and session variables are removed). Every
// frame is drawn from timeline time. Reuses the trailer's file server.
//
//   node tools/render.mjs [--from 0] [--to 53] [--fps 30] [--out build/promo-video/tai-chi-break/film.mp4]
//                         [--stills 3,20.5] [--gl swiftshader]

import { spawn } from 'node:child_process'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { INBE_ROOT, startServer } from '../../three/tools/serve.mjs'

const OUTPUT = 'build/promo-video/tai-chi-break'

function parseArgs(argv) {
    const options = {}
    for (let index = 2; index < argv.length; index += 2) {
        options[argv[index].replace(/^--/, '')] = argv[index + 1]
    }
    return options
}

function privateEnvironment() {
    const environment = { ...process.env }
    for (const name of ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS']) {
        delete environment[name]
    }
    return environment
}

function launchBrowser(url, width, height, gl) {
    mkdirSync(join(INBE_ROOT, OUTPUT, 'profiles'), { recursive: true })
    const profile = mkdtempSync(join(INBE_ROOT, OUTPUT, 'profiles', 'render-'))
    const angle = gl === 'swiftshader' ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : ['--use-angle=gl-egl']
    const browser = spawn(process.env.CHROMIUM ?? 'chromium', [
        '--headless=new', ...angle, '--ignore-gpu-blocklist', '--enable-gpu-rasterization',
        '--enable-logging=stderr', '--no-first-run', '--no-default-browser-check', '--disable-extensions',
        '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
        `--user-data-dir=${profile}`, `--window-size=${width},${height}`, url,
    ], { env: privateEnvironment(), stdio: ['ignore', 'ignore', 'pipe'] })
    let log = ''
    browser.stderr.on('data', (chunk) => { log = (log + chunk).slice(-20000) })
    return { browser, log: () => log, close() { browser.kill('SIGTERM'); setTimeout(() => rmSync(profile, { recursive: true, force: true }), 500) } }
}

// Raw RGBA frames (bottom row first) go straight into the encoder.
function encoder(path, fps, width, height) {
    mkdirSync(dirname(path), { recursive: true })
    const ffmpeg = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${width}x${height}`,
        '-framerate', String(fps), '-i', '-', '-vf', 'vflip', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path], { stdio: ['pipe', 'inherit', 'inherit'] })
    return {
        write: (bytes) => new Promise((done) => (ffmpeg.stdin.write(bytes) ? done() : ffmpeg.stdin.once('drain', done))),
        finish: () => new Promise((done, fail) => { ffmpeg.on('close', (code) => (code === 0 ? done() : fail(new Error(`ffmpeg ${code}`)))); ffmpeg.stdin.end() }),
    }
}

const options = parseArgs(process.argv)
const width = Number(options.width ?? 1920)
const height = Number(options.height ?? 1080)
const fps = Number(options.fps ?? 30)
const out = resolve(INBE_ROOT, options.out ?? `${OUTPUT}/film.mp4`)
const stills = options.stills ? options.stills.split(',') : null
const server = await startServer()
const job = `break${process.pid}`
const video = stills ? null : encoder(out, fps, width, height)
let last = Date.now()
const finished = new Promise((done, fail) => {
    server.jobs.set(job, {
        async frame(index, bytes) {
            if (video) {
                if (bytes.length !== width * height * 4) {
                    throw new Error(`frame ${index} has ${bytes.length} bytes`)
                }
                await video.write(bytes)
                if (index % 60 === 0) {
                    const now = Date.now()
                    process.stdout.write(`  frame ${index} (${((now - last) / 60).toFixed(0)} ms/frame)\n`)
                    last = now
                }
            } else {
                const path = join(dirname(out), `still-${Number(stills[index]).toFixed(2)}.png`)
                mkdirSync(dirname(path), { recursive: true })
                writeFileSync(path, bytes)
                console.log(path)
            }
        },
        done,
        error: (text) => fail(new Error(text)),
    })
})
const query = new URLSearchParams({ render: job, width, height, fps, from: options.from ?? 0, to: options.to ?? 53 })
if (stills) {
    query.set('stills', stills.join(','))
}
if (options.debug) {
    query.set('debug', '1')
}
const page = server.url.replace(/three\/$/, 'tai-chi-break/')
const browser = launchBrowser(`${page}index.html?${query}`, width, height, options.gl)
const timer = setTimeout(() => { console.error(browser.log()); process.exit(2) }, Number(options.timeout ?? 7200) * 1000)
try {
    await Promise.race([finished, new Promise((_, fail) => browser.browser.on('exit', (code) => fail(new Error(`Chromium exited ${code}\n${browser.log()}`))))])
} finally {
    clearTimeout(timer)
    browser.browser.removeAllListeners('exit')
    browser.close()
    server.close()
}
if (video) {
    await video.finish()
    console.log(out)
}
