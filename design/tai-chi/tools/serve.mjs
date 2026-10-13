// Serves the studio, and receives frames from the render page.
//
//   node tools/serve.mjs [--port 8765]

import { createReadStream, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const STUDIO_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)))

const TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
}

function readBody(request) {
    return new Promise((resolveBody, reject) => {
        const chunks = []
        request.on('data', (chunk) => chunks.push(chunk))
        request.on('end', () => resolveBody(Buffer.concat(chunks)))
        request.on('error', reject)
    })
}

// `jobs` maps a render job name to { frame(index, png), done(info), error(text) }.
export function startServer({ port = 0, host = '127.0.0.1', jobs = new Map() } = {}) {
    const server = createServer(async (request, response) => {
        const url = new URL(request.url, 'http://localhost')
        const render = url.pathname.match(/^\/render\/([\w-]+)\/(frame|done|error)(?:\/(\d+))?$/)
        if (render && request.method === 'POST') {
            const job = jobs.get(render[1])
            const body = await readBody(request)
            if (!job) {
                response.writeHead(404).end()
                return
            }
            if (render[2] === 'frame') {
                await job.frame(Number(render[3]), body)
            } else if (render[2] === 'done') {
                job.done(JSON.parse(body.toString() || '{}'))
            } else {
                job.error(body.toString())
            }
            response.writeHead(204).end()
            return
        }
        const path = normalize(join(STUDIO_ROOT, decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname)))
        if (!path.startsWith(STUDIO_ROOT)) {
            response.writeHead(403).end()
            return
        }
        try {
            const stats = statSync(path)
            if (!stats.isFile()) {
                throw new Error('not a file')
            }
            response.writeHead(200, { 'Content-Type': TYPES[extname(path)] ?? 'application/octet-stream', 'Cache-Control': 'no-cache' })
            createReadStream(path).pipe(response)
        } catch {
            response.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found')
        }
    })
    return new Promise((resolveServer) => {
        server.listen(port, host, () => resolveServer({ server, jobs, url: `http://${host}:${server.address().port}/` }))
    })
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const portIndex = process.argv.indexOf('--port')
    const port = portIndex > 0 ? Number(process.argv[portIndex + 1]) : 8765
    const { url } = await startServer({ port })
    console.log(`Tai Chi studio: ${url}`)
}
