import * as T from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { createExercise } from './scenes.js'

const items = await fetch('./src/sessions.json').then(response => response.json())
const canvas = document.querySelector('canvas')
const renderer = new T.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true })
renderer.setPixelRatio(1)
const composer = new EffectComposer(renderer)
const renderPass = new RenderPass(new T.Scene(), new T.Camera())
composer.addPass(renderPass)
composer.addPass(new UnrealBloomPass(new T.Vector2(640, 360), 0.48, 0.45, 0.95))
composer.addPass(new OutputPass())
const scenes = items.map(createExercise)
const picker = document.querySelector('#exercise')
const seek = document.querySelector('#seek')
const play = document.querySelector('#play')
let selected = 0
let time = 0
let playing = false
let last = performance.now()
let state
const clock = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
items.forEach((item, index) => picker.add(new Option(item.title, index)))

function draw() {
    const view = scenes[selected]
    state = view.update(time)
    renderPass.scene = view.scene
    renderPass.camera = view.camera
    composer.render()
    seek.value = time
    document.querySelector('#clock').textContent = `${clock(time)} / ${clock(items[selected].duration)}`
    document.querySelector('#phase').textContent = time === items[selected].duration ? 'Complete · recall and write' : state.phase
    document.querySelector('#cue-number').textContent = `CUE ${state.index + 1} / ${items[selected].cues.length} · ${clock(state.cue.second)}`
    document.querySelector('#caption').textContent = state.cue.text
    document.querySelectorAll('#markers button').forEach((button, index) => button.setAttribute('aria-current', String(index === state.index)))
}

function setPlaying(value) {
    playing = value
    play.textContent = playing ? 'Pause' : 'Play'
    last = performance.now()
}

function choose(index) {
    selected = index
    picker.value = index
    time = 0
    seek.max = items[index].duration
    setPlaying(false)
    const markers = document.querySelector('#markers')
    markers.replaceChildren(...items[index].cues.map((cue, i) => {
        const button = document.createElement('button')
        button.textContent = clock(cue.second)
        button.title = cue.text
        button.setAttribute('aria-label', `Cue ${i + 1}: ${clock(cue.second)}`)
        button.onclick = () => {
            time = cue.second
            draw()
        }
        return button
    }))
    draw()
}

function resize() {
    // One capped-resolution render, shared materials and low-poly figures.
    const width = Math.min(960, canvas.clientWidth)
    const height = Math.round(width * canvas.clientHeight / canvas.clientWidth)
    renderer.setSize(width, height, false)
    composer.setSize(width, height)
    scenes.forEach(view => {
        view.camera.aspect = width / height
        view.camera.updateProjectionMatrix()
    })
    draw()
}
picker.onchange = () => choose(Number(picker.value))
play.onclick = () => {
    if (time >= items[selected].duration) time = 0
    setPlaying(!playing)
}
document.querySelector('#restart').onclick = () => {
    time = 0
    setPlaying(false)
    draw()
}
seek.oninput = () => {
    time = Number(seek.value)
    draw()
}
window.addEventListener('resize', resize)
choose(0)
resize()
const params = new URLSearchParams(location.search)
const initial = items.findIndex(item => item.id === params.get('exercise'))
if (initial >= 0) choose(initial)
if (params.has('t')) {
    time = Math.max(0, Math.min(items[selected].duration, Number(params.get('t')) || 0))
    draw()
}

// Deterministic review API used by the private-display tests.
window.astral = {
    items,
    select: choose,
    seek(value) {
        time = Math.max(0, Math.min(items[selected].duration, value))
        draw()
        return this.state()
    },
    state() { return { id: items[selected].id, time, playing, cue: state.cue.key, caption: state.cue.text, index: state.index, phase: state.phase } },
    pixels() {
        const gl = renderer.getContext()
        const bytes = new Uint8Array(canvas.width * canvas.height * 4)
        gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, bytes)
        let bright = 0
        for (let i = 0; i < bytes.length; i += 4) if (Math.max(bytes[i], bytes[i + 1], bytes[i + 2]) > 80) bright += 1
        return { bright, total: canvas.width * canvas.height, calls: renderer.info.render.calls }
    },
}
function frame(now) {
    if (playing) {
        time = Math.min(items[selected].duration, time + Math.min(1, (now - last) / 1000) * Number(document.querySelector('#speed').value))
        if (time >= items[selected].duration) setPlaying(false)
        draw()
    }
    last = now
    requestAnimationFrame(frame)
}
requestAnimationFrame(frame)
