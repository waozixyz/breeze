// The monitor's terminal: six AI agents working in parallel, drawn into a
// canvas from film time alone, so any frame renders on its own. `progress`
// runs from 0 (the film opens) to 1 (every agent finished).
import { CanvasTexture, LinearFilter, SRGBColorSpace } from 'three'

const SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
const MONO = '"Noto Sans Mono", "DejaVu Sans Mono", monospace'

// Each lane: its colour, its current task and where its bar stands at the
// opening (`from`) and before the break (`to`).
const AGENTS = [
    { name: 'planner', color: '#c9a7ff', task: 'splitting the feature into tasks', from: 0.62, to: 0.71 },
    { name: 'api', color: '#7cc7ff', task: 'adding the sync endpoint', from: 0.41, to: 0.49 },
    { name: 'ui', color: '#7fe0c3', task: 'building the settings screen', from: 0.33, to: 0.42 },
    { name: 'tests', color: '#ffd27a', task: 'writing integration tests', from: 0.27, to: 0.35 },
    { name: 'docs', color: '#ffb38a', task: 'updating the guide', from: 0.48, to: 0.55 },
    { name: 'review', color: '#ff9fbf', task: 'reading every diff', from: 0.12, to: 0.19 },
]

const LOG = [
    ['ui', 'laid out the settings panel'],
    ['tests', 'sync_roundtrip ... ok'],
    ['api', 'compiling server (2 of 5)'],
    ['planner', 'task 7 assigned to ui'],
    ['docs', 'rewrote "getting started"'],
    ['review', 'api: suggested a smaller diff'],
    ['tests', 'offline_queue ... ok'],
    ['api', 'migration 0042 applied'],
    ['ui', 'dark theme contrast checked'],
    ['tests', 'conflict_merge ... ok'],
    ['planner', 'waiting on api for task 9'],
    ['docs', 'screenshots regenerated'],
    ['review', 'ui: approved 3 files'],
    ['api', 'endpoint answers in 38 ms'],
    ['tests', '128 passed, 0 failed'],
    ['ui', 'animations eased'],
]

function roundRect(context, x, y, w, h, r) {
    context.beginPath()
    context.moveTo(x + r, y)
    context.arcTo(x + w, y, x + w, y + h, r)
    context.arcTo(x + w, y + h, x, y + h, r)
    context.arcTo(x, y + h, x, y, r)
    context.arcTo(x, y, x + w, y, r)
    context.closePath()
}

function clock(seconds) {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// A portrait frame sees only the middle of the monitor, so the portrait
// layout stacks each lane (name, task, bar) inside this share of its width.
const COLUMN = [0.265, 0.735]

export function createTerminal(width = 2048, height = 1152, { portrait = false } = {}) {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    const map = new CanvasTexture(canvas)
    map.colorSpace = SRGBColorSpace
    map.minFilter = LinearFilter
    map.generateMipmaps = false
    map.anisotropy = 8

    function lane(agent, index, crawl, done) {
        // On return the lanes finish one after another, review last.
        const finish = Math.min(1, Math.max(0, done * 1.25 - index * 0.05))
        const value = agent.from + (agent.to - agent.from) * crawl
        const shown = finish > 0 ? value + (1 - value) * finish : value
        return { shown, complete: shown >= 0.999 }
    }

    function bar(c, x, y, w, h, shown, complete, color) {
        c.fillStyle = '#18213d'
        roundRect(c, x, y, w, h, h / 2)
        c.fill()
        const fill = c.createLinearGradient(x, 0, x + w, 0)
        fill.addColorStop(0, complete ? '#5fcf8c' : color)
        fill.addColorStop(1, complete ? '#9df0b9' : '#ffffff')
        c.fillStyle = fill
        c.globalAlpha = complete ? 0.95 : 0.88
        roundRect(c, x, y, Math.max(h, w * shown), h, h / 2)
        c.fill()
        c.globalAlpha = 1
    }

    function drawPortrait({ t, crawl = 0, done = 0, elapsed = 0 }) {
        const u = height / 1044
        const c = context
        c.save()
        const background = c.createLinearGradient(0, 0, 0, height)
        background.addColorStop(0, '#0e1529')
        background.addColorStop(1, '#090d1b')
        c.fillStyle = background
        c.fillRect(0, 0, width, height)
        c.fillStyle = '#131b35'
        c.fillRect(0, 0, width, 64 * u)
        c.font = `500 ${28 * u}px ${MONO}`
        c.fillStyle = '#7d89ad'
        c.textAlign = 'center'
        c.textBaseline = 'middle'
        c.fillText('agents  —  ~/projects/app', width / 2, 33 * u)
        c.textAlign = 'left'
        c.textBaseline = 'alphabetic'

        const finished = done >= 0.999
        const left = width * COLUMN[0]
        const right = width * COLUMN[1]
        c.font = `600 ${58 * u}px ${MONO}`
        c.fillStyle = finished ? '#86e3a8' : '#eef3ff'
        c.fillText(finished ? '✓ all 6 agents finished' : `${SPINNER[Math.floor(t * 12) % SPINNER.length]} orchestrating 6 agents`, left, 152 * u)
        c.font = `500 ${30 * u}px ${MONO}`
        c.fillStyle = '#8e9abd'
        const eta = Math.max(1, Math.round(19 - crawl * 3))
        c.fillText(finished ? `elapsed ${clock(elapsed)}  ·  ready for review` : `elapsed ${clock(elapsed)}  ·  eta ~${eta} min`, left, 204 * u)
        c.fillStyle = '#212b4a'
        c.fillRect(left, 232 * u, right - left, 2 * u)

        AGENTS.forEach((agent, index) => {
            const y = (296 + index * 98) * u
            const { shown, complete } = lane(agent, index, crawl, done)
            c.font = `600 ${40 * u}px ${MONO}`
            c.fillStyle = complete ? '#86e3a8' : agent.color
            c.fillText(complete ? '✓' : SPINNER[(Math.floor(t * 12) + index * 3) % SPINNER.length], left, y)
            c.fillText(agent.name, left + 58 * u, y)
            c.font = `500 ${32 * u}px ${MONO}`
            c.fillStyle = '#a3aed0'
            c.textAlign = 'right'
            c.fillText(`${Math.round(shown * 100)}%`, right, y)
            c.textAlign = 'left'
            c.font = `500 ${29 * u}px ${MONO}`
            c.fillStyle = complete ? '#7f8bab' : '#cdd5ec'
            c.fillText(complete ? 'done' : agent.task, left + 58 * u, y + 38 * u)
            bar(c, left, y + 52 * u, right - left, 14 * u, shown, complete, agent.color)
        })

        // Three log lines stream up beneath the lanes.
        const paneTop = 884 * u
        const paneBottom = 994 * u
        c.fillStyle = '#0b1022'
        roundRect(c, left - 18 * u, paneTop, right - left + 36 * u, paneBottom - paneTop, 12 * u)
        c.fill()
        c.save()
        c.beginPath()
        c.rect(left - 18 * u, paneTop, right - left + 36 * u, paneBottom - paneTop)
        c.clip()
        const position = finished ? 30 : 8 + t * 1.4
        const first = Math.floor(position)
        const scroll = finished ? 1 : position - first
        const lineHeight = 34 * u
        const rows = 3
        for (let row = 0; row <= rows; row += 1) {
            const n = first - rows + row
            const [agent, text] = finished && row === rows ? ['review', 'all diffs approved'] : LOG[n % LOG.length]
            const color = AGENTS.find((entry) => entry.name === agent).color
            const y = paneTop + 38 * u + (row - scroll) * lineHeight
            const age = rows - row + scroll
            const edge = Math.min(1, Math.max(0, (y - paneTop - 12 * u) / (22 * u)), Math.max(0, (paneBottom - y - 4 * u) / (22 * u)))
            c.globalAlpha = Math.max(0.3, Math.min(1, 1.15 - age * 0.18)) * edge
            c.font = `500 ${27 * u}px ${MONO}`
            c.fillStyle = color
            c.fillText(agent, left, y)
            c.fillStyle = '#bfc8e2'
            c.fillText(text, left + 150 * u, y)
        }
        c.restore()
        c.globalAlpha = 1

        c.font = `500 ${29 * u}px ${MONO}`
        c.fillStyle = finished ? '#86e3a8' : '#8692b6'
        const tests = finished ? 412 : 128 + Math.floor(crawl * 40)
        c.fillText(finished ? `6 finished  ·  0 failed  ·  ${tests} tests` : `6 running  ·  0 failed  ·  ${tests} tests`, left, 1030 * u)
        if (Math.floor(t * 2) % 2 === 0) {
            c.fillStyle = '#c5cee6'
            c.fillRect(right - 14 * u, 1004 * u, 14 * u, 30 * u)
        }
        c.restore()
        map.needsUpdate = true
    }

    // state: { t (film seconds), crawl (0..1 before the break), done (0..1
    // lanes finishing on return), elapsed (seconds shown) }
    function draw({ t, crawl = 0, done = 0, elapsed = 0 }) {
        if (portrait) {
            drawPortrait({ t, crawl, done, elapsed })
            return
        }
        const u = height / 1044
        const c = context
        c.save()
        const background = c.createLinearGradient(0, 0, 0, height)
        background.addColorStop(0, '#0e1529')
        background.addColorStop(1, '#090d1b')
        c.fillStyle = background
        c.fillRect(0, 0, width, height)

        // Window bar.
        c.fillStyle = '#131b35'
        c.fillRect(0, 0, width, 64 * u)
        ;['#ff7a7a', '#ffc96b', '#76d99a'].forEach((color, index) => {
            c.fillStyle = color
            c.globalAlpha = 0.8
            c.beginPath()
            c.arc((42 + index * 36) * u, 32 * u, 11 * u, 0, Math.PI * 2)
            c.fill()
        })
        c.globalAlpha = 1
        c.font = `500 ${28 * u}px ${MONO}`
        c.fillStyle = '#7d89ad'
        c.textAlign = 'center'
        c.textBaseline = 'middle'
        c.fillText('agents  —  ~/projects/app', width / 2, 33 * u)
        c.textAlign = 'left'

        const finished = done >= 0.999
        const left = 72 * u
        const right = width - 72 * u
        // Header.
        c.textBaseline = 'alphabetic'
        c.font = `600 ${64 * u}px ${MONO}`
        if (finished) {
            c.fillStyle = '#86e3a8'
            c.fillText('✓ all 6 agents finished', left, 158 * u)
        } else {
            c.fillStyle = '#eef3ff'
            c.fillText(`${SPINNER[Math.floor(t * 12) % SPINNER.length]} orchestrating 6 agents`, left, 158 * u)
        }
        c.font = `500 ${32 * u}px ${MONO}`
        c.fillStyle = '#8e9abd'
        c.textAlign = 'right'
        const eta = Math.max(1, Math.round(19 - crawl * 3))
        c.fillText(finished ? `elapsed ${clock(elapsed)}  ·  ready for review` : `elapsed ${clock(elapsed)}  ·  eta ~${eta} min`, right, 154 * u)
        c.textAlign = 'left'
        c.fillStyle = '#212b4a'
        c.fillRect(left, 192 * u, right - left, 2 * u)

        // Lanes.
        AGENTS.forEach((agent, index) => {
            const y = (262 + index * 80) * u
            // On return the lanes finish one after another, review last.
            const finish = Math.min(1, Math.max(0, done * 1.25 - index * 0.05))
            const value = agent.from + (agent.to - agent.from) * crawl
            const shown = finish > 0 ? value + (1 - value) * finish : value
            const complete = shown >= 0.999
            c.font = `600 ${42 * u}px ${MONO}`
            c.fillStyle = complete ? '#86e3a8' : agent.color
            c.fillText(complete ? '✓' : SPINNER[(Math.floor(t * 12) + index * 3) % SPINNER.length], left, y)
            c.fillText(agent.name, left + 62 * u, y)
            c.font = `500 ${38 * u}px ${MONO}`
            c.fillStyle = complete ? '#7f8bab' : '#cdd5ec'
            c.fillText(complete ? 'done' : agent.task, left + 330 * u, y)
            const barX = width * 0.64
            const barW = right - barX - 120 * u
            c.fillStyle = '#18213d'
            roundRect(c, barX, y - 26 * u, barW, 22 * u, 11 * u)
            c.fill()
            const fill = c.createLinearGradient(barX, 0, barX + barW, 0)
            fill.addColorStop(0, complete ? '#5fcf8c' : agent.color)
            fill.addColorStop(1, complete ? '#9df0b9' : '#ffffff')
            c.fillStyle = fill
            c.globalAlpha = complete ? 0.95 : 0.88
            roundRect(c, barX, y - 26 * u, Math.max(22 * u, barW * shown), 22 * u, 11 * u)
            c.fill()
            c.globalAlpha = 1
            c.font = `500 ${34 * u}px ${MONO}`
            c.fillStyle = '#a3aed0'
            c.textAlign = 'right'
            c.fillText(`${Math.round(shown * 100)}%`, right, y - 2 * u)
            c.textAlign = 'left'
        })

        // Log pane: lines stream up smoothly, and stop once all is done.
        const top = 760 * u
        const paneTop = top - 44 * u
        const paneBottom = height - 66 * u
        c.fillStyle = '#0b1022'
        roundRect(c, left - 18 * u, paneTop, right - left + 36 * u, paneBottom - paneTop, 14 * u)
        c.fill()
        c.save()
        c.beginPath()
        c.rect(left - 18 * u, paneTop, right - left + 36 * u, paneBottom - paneTop)
        c.clip()
        const position = finished ? 30 : 8 + t * 1.4
        const first = Math.floor(position)
        // Finished, the log rests with its last line fully in view.
        const scroll = finished ? 1 : position - first
        const lineHeight = 44 * u
        const rows = 5
        for (let row = 0; row <= rows; row += 1) {
            const n = first - rows + row
            const [agent, text] = finished && row === rows ? ['review', 'all diffs approved, ready for you'] : LOG[n % LOG.length]
            const color = AGENTS.find((entry) => entry.name === agent).color
            const y = top + (row - scroll) * lineHeight
            const age = rows - row + scroll
            // Older lines dim; lines fade at the pane's edges as they scroll.
            const edge = Math.min(1, Math.max(0, (y - paneTop - 18 * u) / (26 * u)), Math.max(0, (paneBottom - y - 4 * u) / (26 * u)))
            c.globalAlpha = Math.max(0.3, Math.min(1, 1.15 - age * 0.13)) * edge
            c.font = `500 ${33 * u}px ${MONO}`
            c.fillStyle = '#5a6690'
            c.fillText(`23:${String(Math.floor((elapsed / 60 - age * 0.4 + 600) % 60)).padStart(2, '0')}`, left, y)
            c.fillStyle = color
            c.fillText(agent, left + 140 * u, y)
            c.fillStyle = '#bfc8e2'
            c.fillText(text, left + 330 * u, y)
        }
        c.restore()
        c.globalAlpha = 1

        // Status line.
        c.font = `500 ${32 * u}px ${MONO}`
        c.fillStyle = finished ? '#86e3a8' : '#8692b6'
        const tests = finished ? 412 : 128 + Math.floor(crawl * 40)
        c.fillText(finished ? `6 finished  ·  0 failed  ·  ${tests} tests passed` : `6 running  ·  0 failed  ·  ${tests} tests passed`, left, height - 20 * u)
        if (Math.floor(t * 2) % 2 === 0) {
            c.fillStyle = '#c5cee6'
            c.fillRect(right - 18 * u, height - 50 * u, 16 * u, 34 * u)
        }
        c.restore()
        map.needsUpdate = true
    }
    return { map, draw, canvas }
}
