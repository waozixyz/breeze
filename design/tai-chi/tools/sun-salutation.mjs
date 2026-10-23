// Renders stills of the Sun Salutation body lab (sun-salutation.html) with
// headless Chromium, the way tools/render.mjs renders the course.
//
//   python3 scripts/render-sun-salutation-live.py --motion design/tai-chi/lab/sun-salutation-motion.json
//   node tools/sun-salutation.mjs --stills 11.5,28.5,52.4 [--camera app|side|back|front] [--name lab]
//
// Stills go to build/tai-chi/sun-salutation/ as NAME-tSECONDS.png.

import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { STUDIO_ROOT, startServer } from './serve.mjs'
import { launchBrowser } from './render.mjs'

const options = { camera: 'app', name: 'lab', width: '1280', height: '900' }
const argv = process.argv.slice(2)
for (let index = 0; index < argv.length; index += 2) {
    options[argv[index].replace(/^--/, '')] = argv[index + 1]
}
if (!options.stills) {
    console.error('Give --stills T1,T2,...')
    process.exit(1)
}
const out = resolve(STUDIO_ROOT, '..', '..', 'build', 'tai-chi', 'sun-salutation')
mkdirSync(out, { recursive: true })
const server = await startServer()
const job = `lab${process.pid}`
const times = options.stills.split(',')
const written = []
const finished = new Promise((done, fail) => {
    server.jobs.set(job, {
        async frame(index, png) {
            const path = join(out, `${options.name}-t${Number(times[index]).toFixed(2).replace('.', '_')}.png`)
            writeFileSync(path, png)
            written.push(path)
        },
        done,
        error: (text) => fail(new Error(text)),
    })
})
const query = new URLSearchParams({ render: job, stills: options.stills, camera: options.camera, figure: options.figure ?? 'sunWoman',
    width: options.width, height: options.height })
const browser = launchBrowser(`${server.url}sun-salutation.html?${query}`, Number(options.width), Number(options.height))
try {
    await Promise.race([
        finished,
        new Promise((_, fail) => setTimeout(() => fail(new Error(`Timed out\n${browser.log()}`)), 300000)),
    ])
    console.log(written.join('\n'))
} finally {
    browser.close()
    server.server.close()
}
