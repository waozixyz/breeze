// Renders review stills and videos with headless Chromium. Nothing opens a
// window: the browser runs without a display, and the inherited display and
// session variables are removed from its environment.
//
//   node tools/render.mjs --item lesson-1/wild-horse/demo --stills 3,6.5,9
//   node tools/render.mjs --item full/normal --video
//   node tools/render.mjs --lessons            (every lesson, demo video each)
//
// Options: --view behind|front|side|threeQuarter|top, --figure monk|
// tibetanWoman|sageBun|sageMale|mannequin, --theme light|dark, --width,
// --height, --fps,
// --label (draw title, cue and time), --out DIR, --name NAME.

import { spawn } from 'node:child_process'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { STUDIO_ROOT, startServer } from './serve.mjs'

const INBE_ROOT = resolve(STUDIO_ROOT, '..', '..')
const DEFAULT_OUT = join(INBE_ROOT, 'build', 'tai-chi')

function parseArgs(argv) {
    const options = { label: false, video: false, lessons: false }
    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index]
        if (!arg.startsWith('--')) {
            continue
        }
        const name = arg.slice(2)
        if (['label', 'video', 'lessons', 'full', 'keep'].includes(name)) {
            options[name] = true
        } else {
            options[name] = argv[index + 1]
            index += 1
        }
    }
    return options
}

function chromiumBinary() {
    return process.env.CHROMIUM ?? 'chromium'
}

function privateEnvironment() {
    const environment = { ...process.env }
    for (const name of ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS']) {
        delete environment[name]
    }
    return environment
}

function launchBrowser(url, width, height) {
    const profile = mkdtempSync(join(tmpdir(), 'tai-chi-render-'))
    const browser = spawn(chromiumBinary(), [
        '--headless=new',
        '--use-angle=swiftshader',
        '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        `--user-data-dir=${profile}`,
        `--window-size=${width},${height}`,
        url,
    ], { env: privateEnvironment(), stdio: ['ignore', 'ignore', 'pipe'] })
    let log = ''
    browser.stderr.on('data', (chunk) => {
        log += chunk
        if (log.length > 20000) {
            log = log.slice(-20000)
        }
    })
    return {
        browser,
        log: () => log,
        close() {
            browser.kill('SIGTERM')
            setTimeout(() => rmSync(profile, { recursive: true, force: true }), 500)
        },
    }
}

function encoder(path, fps) {
    const ffmpeg = spawn('ffmpeg', [
        '-y', '-loglevel', 'error',
        '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', path,
    ], { stdio: ['pipe', 'inherit', 'inherit'] })
    return {
        write(png) {
            return new Promise((resolveWrite) => {
                if (!ffmpeg.stdin.write(png)) {
                    ffmpeg.stdin.once('drain', resolveWrite)
                } else {
                    resolveWrite()
                }
            })
        },
        finish() {
            return new Promise((resolveFinish, reject) => {
                ffmpeg.on('close', (code) => (code === 0 ? resolveFinish() : reject(new Error(`ffmpeg exited ${code}`))))
                ffmpeg.stdin.end()
            })
        },
    }
}

let jobCounter = 0

// Renders one item to stills or a video. Resolves with the written paths.
export async function renderItem(server, options) {
    const job = `job${process.pid}-${jobCounter += 1}`
    const width = Number(options.width ?? 1280)
    const height = Number(options.height ?? 720)
    const fps = Number(options.fps ?? 30)
    const out = resolve(options.out ?? DEFAULT_OUT)
    mkdirSync(out, { recursive: true })
    const name = options.name ?? options.item.replaceAll('/', '_')
    const query = new URLSearchParams({ render: job, item: options.item, width, height, fps })
    for (const key of ['view', 'figure', 'theme', 'from', 'to', 'mirror']) {
        if (options[key] !== undefined) {
            query.set(key, options[key])
        }
    }
    if (options.label) {
        query.set('label', '1')
    }
    if (options.stills) {
        query.set('stills', options.stills)
    }
    const written = []
    const video = options.stills ? null : encoder(join(out, `${name}.mp4`), fps)
    const stillTimes = options.stills ? String(options.stills).split(',') : []
    const finished = new Promise((resolveJob, reject) => {
        server.jobs.set(job, {
            async frame(index, png) {
                if (video) {
                    await video.write(png)
                } else {
                    const time = Number(stillTimes[index]).toFixed(2).replace('.', '_')
                    const path = join(out, `${name}-t${time}.png`)
                    writeFileSync(path, png)
                    written.push(path)
                }
                if (video && index % 300 === 0) {
                    process.stdout.write(`  ${name}: frame ${index}\n`)
                }
            },
            done: resolveJob,
            error: (text) => reject(new Error(text)),
        })
    })
    const browser = launchBrowser(`${server.url}index.html?${query}`, width, height)
    const timeout = Number(options.timeout ?? 3600) * 1000
    let timer = null
    try {
        await Promise.race([
            finished,
            new Promise((_, reject) => {
                timer = setTimeout(() => reject(new Error(`Render timed out\n${browser.log()}`)), timeout)
            }),
            new Promise((_, reject) => browser.browser.on('exit', (code) => reject(new Error(`Chromium exited ${code}\n${browser.log()}`)))),
        ])
    } finally {
        clearTimeout(timer)
        browser.browser.removeAllListeners('exit')
        browser.close()
        server.jobs.delete(job)
    }
    if (video) {
        await video.finish()
        written.push(join(out, `${name}.mp4`))
    }
    return written
}

async function main() {
    const options = parseArgs(process.argv.slice(2))
    const server = await startServer()
    try {
        if (options.lessons || options.full) {
            const { buildCourse } = await import('../src/course.js')
            const course = buildCourse()
            const ids = []
            if (options.lessons) {
                for (const lesson of course.modules.find((module) => module.id === 'lessons').lessons) {
                    if (lesson.items.length > 0) {
                        ids.push(`${lesson.id}/all`)
                    }
                }
            }
            if (options.full) {
                ids.push('full/normal')
            }
            for (const id of ids) {
                const paths = await renderItem(server, { ...options, item: id, name: undefined })
                console.log(paths.join('\n'))
            }
        } else {
            if (!options.item) {
                throw new Error('Give --item ID, --lessons or --full')
            }
            const paths = await renderItem(server, options)
            console.log(paths.join('\n'))
        }
    } finally {
        server.server.close()
    }
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(new URL(import.meta.url).pathname)) {
    main().catch((error) => {
        console.error(error.message)
        process.exit(1)
    })
}
