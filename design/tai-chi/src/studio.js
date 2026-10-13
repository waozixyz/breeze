// The review studio: course outline, 3D view, timeline, cues and checks.

import {
    BufferGeometry, DoubleSide, Float32BufferAttribute, Group, Line, LineBasicMaterial, LineLoop, Mesh,
    MeshBasicMaterial, Shape, ShapeGeometry, Vector3,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { buildCourse, timelineFor } from './course.js'
import { checkTimeline } from './checks.js'
import { makeRig } from './rig.js'
import { solvePose } from './solve.js'
import { createFigure, styleNames } from './view/figure.js'
import './view/characters.js'
import { THEMES, VIEWS, createCameraRig, createStage } from './view/stage.js'
import { createPaintedFigure, loadCharacter } from './painted/figure.js'

const params = new URLSearchParams(location.search)
const renderMode = params.has('render')
if (renderMode) {
    document.body.classList.add('render')
}

const FIGURE_LABELS = { mannequin: 'Mannequin', sageBun: 'Sage Bun', sageMale: 'Sage Male', monk: 'Monk', tibetanWoman: 'Tibetan Woman' }
// Painted 2D characters: cut-out paintings over the same solved body.
const PAINTED = {
    monk: 'characters/monk/character.json',
    tibetanWoman: 'characters/tibetan-woman/character.json',
}
const DEG = Math.PI / 180
const course = buildCourse()

const state = {
    item: null,
    data: null,
    time: 0,
    playing: !renderMode,
    speed: 1,
    loop: true,
    view: 'behind',
    mirror: false,
    figure: params.get('figure') ?? 'monk',
    theme: params.get('theme') ?? 'light',
    footprints: true,
    weight: true,
    ghost: false,
    checks: false,
    checkResult: null,
}

const canvas = document.getElementById('view')
const viewport = document.getElementById('viewport')
const stage = createStage(canvas, { preserveDrawingBuffer: renderMode })
const cameraRig = createCameraRig(stage.camera)
const orbit = new OrbitControls(stage.camera, canvas)
orbit.enabled = false
orbit.enableDamping = true
orbit.target.set(0, 0.9, 0)

let rig = makeRig(state.figure)
let figure = null
let ghost = null
let painted = null
const characters = new Map()

function figureNames() {
    return [...Object.keys(PAINTED), ...styleNames()]
}

async function setFigure(name) {
    if (!figureNames().includes(name)) {
        name = 'mannequin'
    }
    state.figure = name
    rig = makeRig(name)
    for (const old of [figure, ghost]) {
        if (old) {
            stage.scene.remove(old.root)
            old.dispose()
        }
    }
    figure = null
    ghost = null
    painted?.dispose()
    painted = null
    if (PAINTED[name]) {
        if (!characters.has(name)) {
            characters.set(name, loadCharacter(PAINTED[name]))
        }
        const character = await characters.get(name)
        if (state.figure !== name) {
            return
        }
        painted = createPaintedFigure(character, rig)
        painted.setBackground(THEMES[state.theme]?.background ?? THEMES.light.background)
    } else {
        figure = createFigure(rig, name, { theme: state.theme })
        stage.scene.add(figure.root)
        ghost = createFigure(rig, name, { theme: state.theme })
        ghost.setGhost(0.22)
        ghost.root.visible = state.ghost
        stage.scene.add(ghost.root)
    }
    footprintGeometry = null
    rebuildFootprints()
    renderToolbar()
}

// Footprints: the planted feet, and an outline where each foot goes next.
let footprintGeometry = null
let footprintOutline = null
const footprints = new Group()
stage.overlay.add(footprints)
const prints = {}

function footShape() {
    const heel = rig.heelBack + 0.012 * rig.height
    const toe = rig.toeTip + 0.008 * rig.height
    const width = rig.footHalfWidth * 1.15
    const shape = new Shape()
    shape.moveTo(0, -heel)
    shape.bezierCurveTo(width * 0.95, -heel, width * 0.95, -heel * 0.3, width * 0.9, rig.ball * 0.4)
    shape.bezierCurveTo(width * 1.15, rig.ball, width, toe, 0, toe)
    shape.bezierCurveTo(-width * 1.05, toe, -width * 1.2, rig.ball, -width * 0.95, rig.ball * 0.5)
    shape.bezierCurveTo(-width * 0.8, -heel * 0.3, -width * 0.95, -heel, 0, -heel)
    return shape
}

function flatten(geometry) {
    const positions = geometry.getAttribute('position')
    for (let index = 0; index < positions.count; index += 1) {
        const x = positions.getX(index)
        const y = positions.getY(index)
        positions.setXYZ(index, x, 0, y)
    }
    positions.needsUpdate = true
    return geometry
}

function rebuildFootprints() {
    footprints.clear()
    const shape = footShape()
    footprintGeometry = flatten(new ShapeGeometry(shape, 12))
    const outlinePoints = shape.getPoints(24).map((point) => new Vector3(point.x, 0, point.y))
    footprintOutline = new BufferGeometry().setFromPoints(outlinePoints)
    const colors = getComputedStyle(document.documentElement)
    for (const side of ['L', 'R']) {
        const color = colors.getPropertyValue(side === 'L' ? '--left' : '--right').trim() || (side === 'L' ? '#3b8f87' : '#d0714f')
        const fill = new Mesh(footprintGeometry, new MeshBasicMaterial({ color, transparent: true, opacity: 0.35, depthWrite: false, side: DoubleSide }))
        fill.renderOrder = 1
        const next = new LineLoop(footprintOutline, new LineBasicMaterial({ color, transparent: true, opacity: 0.85 }))
        const nextLine = new Line(new BufferGeometry().setFromPoints([new Vector3(), new Vector3()]),
            new LineBasicMaterial({ color, transparent: true, opacity: 0.35 }))
        footprints.add(fill, next, nextLine)
        prints[side] = { fill, next, nextLine }
    }
}

function placePrint(object, x, z, yaw) {
    object.position.set(x * rig.scale, 0.003, z * rig.scale)
    object.rotation.set(0, yaw, 0)
}

// The next placement of each foot after the current key, within the item.
function nextPlacement(side, index) {
    const keys = state.data.keys
    const current = keys[index].pose.feet[side]
    for (let next = index + 1; next < keys.length; next += 1) {
        const foot = keys[next].pose.feet[side]
        const moved = Math.hypot(foot.x - current.x, foot.z - current.z) > 0.03 || Math.abs(foot.yaw - current.yaw) > 0.1
        if (moved && foot.lift < 0.002) {
            return foot
        }
    }
    return null
}

function updateFootprints(sample, solved) {
    footprints.visible = state.footprints
    if (!state.footprints) {
        return
    }
    for (const side of ['L', 'R']) {
        const foot = sample.pose.feet[side]
        const print = prints[side]
        const share = side === 'L' ? solved.load : 1 - solved.load
        const planted = foot.lift < 0.004
        print.fill.visible = planted
        print.fill.material.opacity = 0.12 + 0.45 * share
        placePrint(print.fill, foot.x, foot.z, foot.yaw)
        const next = nextPlacement(side, sample.index)
        print.next.visible = Boolean(next)
        print.nextLine.visible = Boolean(next)
        if (next) {
            placePrint(print.next, next.x, next.z, next.yaw)
            const positions = print.nextLine.geometry.getAttribute('position')
            positions.setXYZ(0, foot.x * rig.scale, 0.004, foot.z * rig.scale)
            positions.setXYZ(1, next.x * rig.scale, 0.004, next.z * rig.scale)
            positions.needsUpdate = true
        }
    }
}

// Outline of lessons and versions.
function renderOutline() {
    const nav = document.getElementById('outline')
    nav.innerHTML = ''
    for (const module of course.modules) {
        const section = document.createElement('div')
        section.className = 'module'
        section.innerHTML = `<h2>${module.title}</h2>`
        for (const lesson of module.lessons) {
            const details = document.createElement('details')
            details.className = 'lesson'
            details.dataset.lesson = lesson.id
            const summary = document.createElement('summary')
            summary.innerHTML = `<span class="name">${lesson.title}</span>${lesson.subtitle ? `<span class="sub">${lesson.subtitle}</span>` : ''}`
            details.append(summary)
            const entries = document.createElement('div')
            entries.className = 'entries'
            // Group versions of the same movement on one row.
            const rows = new Map()
            for (const item of lesson.items) {
                const rowKey = item.version && item.kind !== 'full' ? item.title : item.id
                if (!rows.has(rowKey)) {
                    rows.set(rowKey, [])
                }
                rows.get(rowKey).push(item)
            }
            if (lesson.items.length === 0) {
                entries.innerHTML = '<div class="entry"><span class="title" style="color:var(--muted)">Not yet animated</span></div>'
            }
            for (const [, items] of rows) {
                const row = document.createElement('div')
                row.className = 'entry'
                row.dataset.items = items.map((item) => item.id).join(' ')
                const title = document.createElement('span')
                title.className = 'title'
                title.textContent = items[0].title
                title.addEventListener('click', () => selectItem(items[0].id))
                row.append(title)
                if (items.length > 1 || items[0].version) {
                    const versions = document.createElement('div')
                    versions.className = 'versions'
                    for (const item of items) {
                        const chip = document.createElement('button')
                        chip.className = 'chip'
                        chip.dataset.item = item.id
                        chip.textContent = item.version ?? 'Play'
                        chip.addEventListener('click', () => selectItem(item.id))
                        versions.append(chip)
                    }
                    row.append(versions)
                }
                entries.append(row)
            }
            details.append(entries)
            section.append(details)
        }
        nav.append(section)
    }
}

function highlightOutline() {
    for (const chip of document.querySelectorAll('.chip')) {
        chip.classList.toggle('active', chip.dataset.item === state.item.id)
    }
    for (const row of document.querySelectorAll('.entry')) {
        row.classList.toggle('active-row', (row.dataset.items ?? '').split(' ').includes(state.item.id))
    }
    const lessonId = [...course.modules].flatMap((module) => module.lessons).find((lesson) => lesson.items.includes(state.item))?.id
    for (const details of document.querySelectorAll('details.lesson')) {
        if (details.dataset.lesson === lessonId) {
            details.open = true
        }
    }
}

function renderToolbar() {
    const views = document.getElementById('views')
    views.innerHTML = ''
    for (const [name, view] of [...Object.entries(VIEWS), ['free', { label: 'Free' }]]) {
        const button = document.createElement('button')
        button.textContent = view.label
        button.className = state.view === name ? 'on' : ''
        button.title = name === 'free' ? 'Drag to orbit, scroll to zoom' : `${view.label} view`
        button.addEventListener('click', () => setView(name))
        views.append(button)
    }
    const figures = document.getElementById('figures')
    figures.innerHTML = ''
    for (const name of figureNames()) {
        const button = document.createElement('button')
        button.textContent = FIGURE_LABELS[name] ?? name
        button.className = state.figure === name ? 'on' : ''
        button.addEventListener('click', () => setFigure(name))
        figures.append(button)
    }
    const toggles = document.getElementById('toggles')
    toggles.innerHTML = ''
    const toggle = (label, key, after, title) => {
        const button = document.createElement('button')
        button.textContent = label
        button.title = title ?? label
        button.className = state[key] ? 'on' : ''
        button.addEventListener('click', () => {
            state[key] = !state[key]
            after?.()
            renderToolbar()
        })
        toggles.append(button)
    }
    toggle('Mirror', 'mirror', () => canvas.classList.toggle('mirrored', state.mirror), 'Flip the picture left to right, like a mirror')
    // Footprints and the next-pose ghost are drawn in the 3D scene only.
    if (!PAINTED[state.figure]) {
        toggle('Footprints', 'footprints')
    }
    toggle('Weight', 'weight', () => { document.getElementById('weight').style.display = state.weight ? '' : 'none' })
    if (!PAINTED[state.figure]) {
        toggle('Next pose', 'ghost', () => { ghost.root.visible = state.ghost }, 'Show the next key pose as a ghost')
    }
    toggle('Checks', 'checks', () => { if (state.checks) { runChecks() } else { document.getElementById('checks').classList.add('hidden') } }, 'Run the motion checks for this item')
    const theme = document.createElement('button')
    theme.textContent = state.theme === 'light' ? 'Dark' : 'Light'
    theme.title = 'Switch theme'
    theme.addEventListener('click', () => setTheme(state.theme === 'light' ? 'dark' : 'light'))
    toggles.append(theme)
}

function setTheme(name) {
    state.theme = name
    document.documentElement.dataset.theme = name
    stage.setTheme(name)
    return setFigure(state.figure)
}

function setView(name) {
    state.view = name
    if (name === 'free') {
        orbit.enabled = true
        orbit.target.set(cameraRig.center.x, 0.9, cameraRig.center.z)
    } else {
        orbit.enabled = false
        cameraRig.view = name
        cameraRig.initialized = false
    }
    renderToolbar()
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60)
    const rest = seconds - minutes * 60
    return `${minutes}:${rest.toFixed(1).padStart(4, '0')}`
}

function renderTrack() {
    const track = document.getElementById('track')
    track.innerHTML = '<div class="lane"></div><div class="fill" id="fill"></div>'
    const duration = state.data.timeline.duration
    for (const mark of state.data.marks) {
        const segment = document.createElement('div')
        segment.className = 'seg'
        segment.style.left = `${(mark.start / duration) * 100}%`
        segment.style.width = `${((mark.end - mark.start) / duration) * 100}%`
        segment.textContent = mark.number ? `${mark.number}. ${mark.title}` : mark.title
        segment.title = segment.textContent
        track.append(segment)
    }
    for (const key of state.data.keys) {
        if (!key.cue) {
            continue
        }
        const tick = document.createElement('div')
        tick.className = 'tick'
        tick.style.left = `${((key.t - state.data.keys[0].t) / duration) * 100}%`
        track.append(tick)
    }
    const head = document.createElement('div')
    head.className = 'head'
    head.id = 'head'
    track.append(head)
}

function updateTrack() {
    const duration = state.data.timeline.duration
    const share = duration > 0 ? state.time / duration : 0
    document.getElementById('head').style.left = `${share * 100}%`
    document.getElementById('fill').style.width = `${share * 100}%`
    document.getElementById('time').textContent = `${formatTime(state.time)} / ${formatTime(duration)}`
    document.getElementById('play').textContent = state.playing ? '❚❚' : '▶'
}

function currentMark() {
    return state.data.marks.find((mark) => state.time >= mark.start - 1e-6 && state.time <= mark.end + 1e-6) ?? state.data.marks[0]
}

function updateHud(sample) {
    const mark = currentMark()
    const lesson = course.modules.flatMap((module) => module.lessons).find((candidate) => candidate.items.includes(state.item))
    const title = document.getElementById('hud-title')
    const lessonName = lesson ? `${lesson.title}${lesson.subtitle ? ` · ${lesson.subtitle}` : ''}` : ''
    const moveName = mark ? (mark.number ? `${mark.number}. ${mark.title}` : mark.title) : state.item.title
    const html = `<div class="lesson-name">${lessonName}</div><div class="move-name">${moveName}</div>${state.item.version ? `<div class="version">${state.item.version}</div>` : ''}`
    if (title.innerHTML !== html) {
        title.innerHTML = html
    }
    const cue = document.getElementById('cue')
    let text = sample.to.cue ?? ''
    if (!text && sample.from.held) {
        text = state.data.keys.slice(0, sample.index + 1).reverse().find((key) => key.cue)?.cue ?? ''
    }
    const cueHtml = text ? text : ''
    if (cue.innerHTML !== cueHtml) {
        cue.innerHTML = cueHtml
    }
}

function updateWeight(solved) {
    const left = Math.round(solved.load * 100)
    document.getElementById('weight-l').style.width = `${left}%`
    document.getElementById('weight-r').style.width = `${100 - left}%`
    document.getElementById('weight-ln').textContent = `${left}%`
    document.getElementById('weight-rn').textContent = `${100 - left}%`
}

function selectItem(id, { time = 0, keepView = false } = {}) {
    const item = course.items.get(id) ?? course.items.values().next().value
    state.item = item
    state.data = timelineFor(item)
    state.time = Math.min(time, state.data.timeline.duration)
    state.checkResult = null
    if (!keepView) {
        setView(item.view ?? 'behind')
        state.mirror = Boolean(item.mirror)
        canvas.classList.toggle('mirrored', state.mirror)
    }
    cameraRig.initialized = false
    renderTrack()
    highlightOutline()
    renderToolbar()
    if (state.checks) {
        runChecks()
    }
    if (!renderMode) {
        const url = new URL(location.href)
        url.searchParams.set('item', item.id)
        history.replaceState(null, '', url)
    }
}

function runChecks() {
    const panel = document.getElementById('checks')
    panel.classList.remove('hidden')
    panel.innerHTML = '<h3>Motion checks</h3><div>Running…</div>'
    setTimeout(() => {
        const moves = state.data.marks.map((mark) => ({ ...mark, endFacing: course.form.moves.find((move) => move.id === mark.id)?.endFacing, end: mark.end }))
        const result = checkTimeline(state.data.timeline, rig, { fps: 20, moves: state.item.kind === 'full' ? moves : [] })
        state.checkResult = result
        const status = result.errors === 0 && result.warnings === 0
            ? '<span class="ok">All clear</span>'
            : `<span class="bad">${result.errors} errors · ${result.warnings} warnings</span>`
        panel.innerHTML = `<h3>Motion checks ${status}</h3>`
        const list = document.createElement('ul')
        for (const issue of result.issues.slice(0, 200)) {
            const entry = document.createElement('li')
            entry.innerHTML = `<span class="time">${formatTime(issue.at)}</span>${issue.message}`
            entry.addEventListener('click', () => {
                state.time = issue.at
                state.playing = false
            })
            list.append(entry)
        }
        panel.append(list)
    }, 20)
}

// Playback.
function bindControls() {
    document.getElementById('play').addEventListener('click', () => {
        if (!state.playing && state.time >= state.data.timeline.duration) {
            state.time = 0
        }
        state.playing = !state.playing
    })
    document.getElementById('speed').addEventListener('change', (event) => {
        state.speed = Number(event.target.value)
    })
    const loop = document.getElementById('loop')
    loop.addEventListener('click', () => {
        state.loop = !state.loop
        loop.classList.toggle('on', state.loop)
    })
    const track = document.getElementById('track')
    const seek = (event) => {
        const box = track.getBoundingClientRect()
        const share = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
        state.time = share * state.data.timeline.duration
    }
    let dragging = false
    track.addEventListener('pointerdown', (event) => {
        dragging = true
        track.setPointerCapture(event.pointerId)
        seek(event)
    })
    track.addEventListener('pointermove', (event) => {
        if (dragging) {
            seek(event)
        }
    })
    track.addEventListener('pointerup', () => {
        dragging = false
    })
    canvas.addEventListener('pointerdown', () => {
        if (state.view !== 'free') {
            setView('free')
        }
    })
    window.addEventListener('keydown', (event) => {
        if (event.target.tagName === 'SELECT') {
            return
        }
        const keys = state.data.keys
        const origin = keys[0].t
        if (event.code === 'Space') {
            event.preventDefault()
            state.playing = !state.playing
        } else if (event.code === 'ArrowRight' || event.code === 'ArrowLeft') {
            const direction = event.code === 'ArrowRight' ? 1 : -1
            state.time += direction * (event.shiftKey ? 1 : 1 / 30)
            state.playing = false
        } else if (event.key === ']' || event.key === '[') {
            const times = keys.filter((key) => key.cue).map((key) => key.t - origin)
            const next = event.key === ']'
                ? times.find((time) => time > state.time + 1e-3)
                : [...times].reverse().find((time) => time < state.time - 1e-3)
            if (next !== undefined) {
                state.time = next
            }
            state.playing = false
        } else if (/^[1-6]$/.test(event.key)) {
            setView([...Object.keys(VIEWS), 'free'][Number(event.key) - 1])
        }
        state.time = Math.min(Math.max(state.time, 0), state.data.timeline.duration)
    })
}

function resize() {
    const box = viewport.getBoundingClientRect()
    stage.resize(Math.max(1, box.width), Math.max(1, box.height))
}

// Draws one frame at the current time.
function drawFrame(dt, snap = false) {
    const timeline = state.data.timeline
    const sample = timeline.sample(timeline.start + state.time)
    const solved = solvePose(sample.pose, rig)
    if (state.view === 'free') {
        orbit.update()
    } else {
        cameraRig.update(solved.joints.pelvis, sample.pose.facing, dt, snap)
    }
    if (painted) {
        drawPainted(solved)
    } else if (figure) {
        figure.update(solved)
        if (state.ghost) {
            ghost.update(solvePose({ ...sample.to.pose, look: sample.to.pose.look }, rig))
        }
        updateFootprints(sample, solved)
        stage.follow(solved.joints.pelvis)
        stage.render()
    }
    updateHud(sample)
    if (state.weight) {
        updateWeight(solved)
    }
    return { sample, solved }
}

// The painted figure is seen flat along the 3D camera's direction, framed
// like the 3D view but a little closer.
function drawPainted(solved) {
    const camera = stage.camera
    const target = state.view === 'free'
        ? orbit.target.clone()
        : cameraRig.center.clone().setY(VIEWS[state.view]?.target ?? 0.9)
    const offset = camera.position.clone().sub(target)
    const flat = Math.hypot(offset.x, offset.z)
    const yaw = Math.atan2(offset.x, offset.z)
    const tilt = Math.min(14 * DEG, Math.max(0, Math.atan2(offset.y, flat)))
    const distance = Math.max(2.5, state.view === 'top' ? 4.4 : offset.length())
    const viewHeight = 2 * distance * Math.tan((34 * DEG) / 2) * 0.8
    painted.update(solved, {
        yaw,
        tilt,
        center: state.view === 'free' ? target : cameraRig.center,
        viewHeight,
        viewCenter: Math.max(0.85, target.y),
        aspect: camera.aspect,
    })
    painted.render(stage.renderer)
}

let last = performance.now()
function animate(now) {
    const dt = Math.min(0.1, (now - last) / 1000)
    last = now
    if (state.playing) {
        state.time += dt * state.speed
        const duration = state.data.timeline.duration
        if (state.time > duration) {
            if (state.loop) {
                state.time = 0
                cameraRig.initialized = false
            } else {
                state.time = duration
                state.playing = false
            }
        }
    }
    drawFrame(dt)
    updateTrack()
    requestAnimationFrame(animate)
}

// Render mode: the page steps through frames itself and posts each one to
// the local render server, which encodes them.
async function renderFrames() {
    const job = params.get('render')
    const fps = Number(params.get('fps') ?? 30)
    const width = Number(params.get('width') ?? 1280)
    const height = Number(params.get('height') ?? 720)
    const from = Number(params.get('from') ?? 0)
    const duration = state.data.timeline.duration
    const to = Math.min(Number(params.get('to') ?? duration), duration)
    const stills = params.get('stills') ? params.get('stills').split(',').map(Number) : null
    viewport.style.width = `${width}px`
    viewport.style.height = `${height}px`
    stage.renderer.setPixelRatio(1)
    stage.resize(width, height)
    const label = params.get('label') === '1'
    const composite = document.createElement('canvas')
    composite.width = width
    composite.height = height
    const context = composite.getContext('2d')
    const times = stills ?? Array.from({ length: Math.floor((to - from) * fps) + 1 }, (_, index) => from + index / fps)
    let frame = 0
    for (const time of times) {
        state.time = Math.min(time, duration)
        const { sample } = drawFrame(1 / fps, frame === 0 || Boolean(stills))
        context.save()
        if (state.mirror) {
            context.translate(width, 0)
            context.scale(-1, 1)
        }
        context.drawImage(canvas, 0, 0, width, height)
        context.restore()
        if (label) {
            drawLabel(context, sample, width, height)
        }
        const blob = await new Promise((resolve) => composite.toBlob(resolve, 'image/png'))
        await fetch(`/render/${job}/frame/${frame}`, { method: 'POST', body: blob })
        frame += 1
    }
    await fetch(`/render/${job}/done`, { method: 'POST', body: JSON.stringify({ frames: frame }) })
}

function drawLabel(context, sample, width, height) {
    const mark = currentMark()
    const name = mark ? (mark.number ? `${mark.number}. ${mark.title}` : mark.title) : state.item.title
    const version = state.item.version ? ` · ${state.item.version}` : ''
    const cue = sample.to.cue ?? ''
    const dark = state.theme === 'dark'
    context.fillStyle = dark ? 'rgba(20, 28, 34, 0.82)' : 'rgba(250, 247, 240, 0.85)'
    context.fillRect(0, 0, width, 46)
    context.fillStyle = dark ? '#e6ece8' : '#2e3a33'
    context.textBaseline = 'middle'
    context.font = '500 18px system-ui, sans-serif'
    const stamp = `${formatTime(state.time)}  ·  frame ${Math.round(state.time * 30)}`
    const stampWidth = context.measureText(stamp).width
    context.fillText(stamp, width - stampWidth - 16, 23)
    let size = 20
    context.font = `600 ${size}px system-ui, sans-serif`
    while (context.measureText(`${name}${version}`).width > width - stampWidth - 48 && size > 11) {
        size -= 1
        context.font = `600 ${size}px system-ui, sans-serif`
    }
    context.fillText(`${name}${version}`, 16, 23)
    if (cue) {
        let size = 19
        context.font = `500 ${size}px system-ui, sans-serif`
        while (context.measureText(cue).width > width - 60 && size > 11) {
            size -= 1
            context.font = `500 ${size}px system-ui, sans-serif`
        }
        const textWidth = context.measureText(cue).width
        context.fillStyle = dark ? 'rgba(20, 28, 34, 0.82)' : 'rgba(250, 247, 240, 0.85)'
        context.fillRect((width - textWidth) / 2 - 14, height - 52, textWidth + 28, 36)
        context.fillStyle = dark ? '#e6ece8' : '#2e3a33'
        context.fillText(cue, (width - textWidth) / 2, height - 34)
    }
}

async function start() {
    renderOutline()
    document.documentElement.dataset.theme = state.theme
    stage.setTheme(state.theme)
    await setFigure(state.figure)
    const firstItem = params.get('item') ?? 'full/normal'
    selectItem(firstItem, { time: Number(params.get('t') ?? 0) })
    if (params.get('view')) {
        setView(params.get('view'))
    }
    if (params.has('mirror')) {
        state.mirror = params.get('mirror') === '1'
        canvas.classList.toggle('mirrored', state.mirror)
    }
    document.getElementById('loading').remove()
    if (renderMode) {
        renderFrames().catch((error) => {
            fetch(`/render/${params.get('render')}/error`, { method: 'POST', body: String(error?.stack ?? error) })
        })
        return
    }
    bindControls()
    resize()
    new ResizeObserver(resize).observe(viewport)
    requestAnimationFrame(animate)
}

start()
