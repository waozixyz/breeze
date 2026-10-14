// Serves the Inbe tree read-only (the film imports Tai Chi puppets, app
// frames and Lumi sprites from it) and receives frames from the render page.
//
//   node tools/serve.mjs [--port 8772]   then open /design/promo-film/three/

import { createReadStream, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const FILM_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)))
export const INBE_ROOT = resolve(FILM_ROOT, '..', '..', '..')

const TYPES = {
    '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp',
}

function readBody(request) {
    return new Promise((resolveBody, reject) => {
        const chunks = []
        request.on('data', (chunk) => chunks.push(chunk))
        request.on('end', () => resolveBody(Buffer.concat(chunks)))
        request.on('error', reject)
    })
}

// `jobs` maps a render job name to { frame(index, bytes), done(info), error(text) }.
export function startServer({ port = 0, host = '127.0.0.1', jobs = new Map() } = {}) {
    const server = createServer(async (request, response) => {
        const url = new URL(request.url, 'http://localhost')
        const render = url.pathname.match(/^\/render\/([\w-]+)\/(frame|done|error|log)(?:\/(\d+))?$/)
        if (render && request.method === 'POST') {
            const job = jobs.get(render[1])
            const body = await readBody(request)
            if (!job) {
                response.writeHead(404).end()
                return
            }
            if (render[2] === 'frame') {
                try {
                    await job.frame(Number(render[3]), body)
                } catch (error) {
                    console.error(`frame ${render[3]}: ${error}`)
                    response.writeHead(500).end()
                    return
                }
            } else if (render[2] === 'done') {
                job.done(JSON.parse(body.toString() || '{}'))
            } else if (render[2] === 'log') {
                process.stdout.write(`  page: ${body.toString()}\n`)
            } else {
                job.error(body.toString())
            }
            response.writeHead(204).end()
            return
        }
        const path = normalize(join(INBE_ROOT, decodeURIComponent(url.pathname)))
        if (!path.startsWith(INBE_ROOT) || path.includes(`${INBE_ROOT}/.`)) {
            response.writeHead(403).end()
            return
        }
        try {
            const stats = statSync(path)
            if (!stats.isFile()) {
                throw new Error('not a file')
            }
            response.writeHead(200, { 'Content-Type': TYPES[extname(path)] ?? 'application/octet-stream', 'Cache-Control': 'no-store' })
            createReadStream(path).pipe(response)
        } catch {
            response.writeHead(404).end()
        }
    })
    return new Promise((resolveServer) => {
        server.listen(port, host, () => {
            const address = server.address()
            resolveServer({ server, jobs, url: `http://${host}:${address.port}/design/promo-film/three/`, close: () => server.close() })
        })
    })
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    const at = process.argv.indexOf('--port')
    const port = at >= 0 ? Number(process.argv[at + 1]) : 8772
    startServer({ port }).then(({ url }) => console.log(`Film at ${url}`))
}
