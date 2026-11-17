import * as T from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { createExercise } from './scenes.js'

// The existing film server has no CSS MIME entry. Install the stylesheet from
// text so this static page works there without changing its shared server.
const style = document.createElement('style')
style.textContent = await fetch(new URL('../style.css', import.meta.url)).then(response => response.text())
document.head.append(style)
const items = await fetch('./src/sessions.json').then(response => response.json())
const colors = ['#79e0d8', '#8facff', '#b79aff', '#75dcc7', '#e4bd75', '#c4a2ff']
const names = ['Foundation', 'Full-body current', 'Elevator descent', 'Room spin', 'Rope exit', 'Roll-out exit']
const symbols = ['◎', '≋', '⇣', '◌', '⤒', '↶']
const techniques = [1, 6, 6, 6, 11, 7]
const highlights = [[1, 2, 4, 5, 7, 9], [1, 3, 4, 6, 8, 11], [6, 7, 8, 9, 11, 13], [4, 6, 8, 10, 13, 14], [7, 8, 11, 12, 15, 18], [4, 7, 8, 10, 12, 13]]
const canvas = document.querySelector('canvas')
const renderer = new T.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' })
renderer.setPixelRatio(1)
renderer.info.autoReset = false
const composer = new EffectComposer(renderer)
const renderPass = new RenderPass(new T.Scene(), new T.Camera())
composer.addPass(renderPass)
composer.addPass(new UnrealBloomPass(new T.Vector2(640, 360), 0.65, 0.6, 0.9))
composer.addPass(new OutputPass())
const scenes = items.map((item, index) => createExercise(item, index))
const picker = document.querySelector('#exercise')
const seek = document.querySelector('#seek')
const play = document.querySelector('#play')
const highlightButton = document.querySelector('#highlights')
const cards = document.querySelector('#exercise-cards')
let selected = 0
let time = 0
let playing = false
let montage = false
let montageIndex = 0
let montageAge = 0
let last = performance.now()
let state
let previousCue = ''
const clock = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
items.forEach((item, index) => {
    picker.add(new Option(item.title, index))
    const button = document.createElement('button')
    button.className = 'exercise-card'
    button.style.setProperty('--card-accent', colors[index])
    button.setAttribute('aria-pressed', 'false')
    const icon = document.createElement('span')
    icon.className = 'card-icon'
    icon.textContent = symbols[index]
    const label = document.createElement('span')
    label.className = 'card-label'
    const number = document.createElement('small')
    number.textContent = `0${index + 1} / ${item.duration / 60} MIN`
    label.append(number, document.createTextNode(names[index]))
    button.append(icon, label)
    button.onclick = () => {
        choose(index)
        jumpToTechnique()
    }
    cards.append(button)
})
function draw() {
    const view = scenes[selected]
    state = view.update(time, { directed: document.querySelector('#camera').value === 'directed' })
    renderPass.scene = view.scene
    renderPass.camera = view.camera
    renderer.info.reset()
    composer.render()
    seek.value = time
    document.querySelector('#clock').textContent = `${clock(time)} / ${clock(items[selected].duration)}`
    document.querySelector('#phase').textContent = time === items[selected].duration ? 'Complete · recall and write' : state.phase
    document.querySelector('#motion').textContent = state.motion
    document.querySelector('#camera-name').textContent = state.viewName
    document.querySelector('#phase-index').textContent = `${montage ? 'HIGHLIGHTS · ' : ''}CHAPTER ${String(state.index + 1).padStart(2, '0')}`
    document.querySelector('#breath-symbol').style.transform = `scale(${0.75 + 0.25 * Math.sin(time * Math.PI / 3)})`
    if (previousCue !== state.cue.key) {
        document.querySelector('#cue-number').textContent = `CUE ${state.index + 1} / ${items[selected].cues.length} · ${clock(state.cue.second)}`
        document.querySelector('#caption').textContent = state.cue.text
        document.querySelectorAll('#markers button').forEach((button, index) => button.setAttribute('aria-current', String(index === state.index)))
        previousCue = state.cue.key
    }
}
function setPlaying(value) {
    playing = value
    play.textContent = playing ? 'Pause' : 'Play'
    play.setAttribute('aria-label', playing ? 'Pause animation' : 'Play animation')
    document.querySelector('#status').textContent = playing ? montage ? 'HIGHLIGHTS PLAYING' : 'PLAYING' : 'PAUSED'
    last = performance.now()
}
function exitMontage() {
    montage = false
    highlightButton.textContent = 'Watch highlights'
    highlightButton.setAttribute('aria-pressed', 'false')
    document.querySelector('#status').textContent = playing ? 'PLAYING' : 'PAUSED'
}
function choose(index) {
    selected = index
    picker.value = index
    time = 0
    previousCue = ''
    seek.max = items[index].duration
    exitMontage()
    setPlaying(false)
    document.documentElement.style.setProperty('--accent', colors[index])
    document.querySelector('#scene-title').textContent = items[index].title
    document.querySelector('#scene-index').textContent = `STUDY 0${index + 1} / 06`
    Array.from(cards.children).forEach((card, n) => card.setAttribute('aria-pressed', String(n === index)))
    document.querySelector('#markers').replaceChildren(...items[index].cues.map((cue, i) => {
        const button = document.createElement('button')
        button.textContent = clock(cue.second)
        button.title = cue.text
        button.setAttribute('aria-label', `Cue ${i + 1}: ${clock(cue.second)}`)
        button.onclick = () => {
            exitMontage()
            time = cue.second
            draw()
        }
        return button
    }))
    draw()
}
function jumpToTechnique() {
    exitMontage()
    time = items[selected].cues[techniques[selected]].second + 9
    setPlaying(true)
    draw()
}
function resize() {
    const cap = document.querySelector('#quality').value === 'phone' ? 720 : 1280
    const width = Math.min(cap, canvas.clientWidth)
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
    draw()
}
highlightButton.onclick = () => {
    if (montage) exitMontage()
    else {
        montage = true
        montageIndex = 0
        montageAge = 0
        time = items[selected].cues[highlights[selected][0]].second + 9
        highlightButton.textContent = 'Full session'
        highlightButton.setAttribute('aria-pressed', 'true')
    }
    setPlaying(true)
    draw()
}
document.querySelector('#technique').onclick = jumpToTechnique
document.querySelector('#restart').onclick = () => {
    time = 0
    exitMontage()
    setPlaying(false)
    draw()
}
seek.oninput = () => {
    exitMontage()
    time = Number(seek.value)
    draw()
}
document.querySelector('#camera').onchange = draw
document.querySelector('#quality').onchange = resize
window.addEventListener('resize', resize)
choose(0)
resize()
const params = new URLSearchParams(location.search)
const initial = items.findIndex(item => item.id === params.get('exercise'))
if (initial >= 0) choose(initial)
if (params.has('t')) {
    time = Math.max(0, Math.min(items[selected].duration, Number(params.get('t')) || 0))
    draw()
} else if (!matchMedia('(prefers-reduced-motion: reduce)').matches) jumpToTechnique()

window.astral = {
    items, select: choose,
    seek(value) {
        exitMontage()
        time = Math.max(0, Math.min(items[selected].duration, value))
        draw()
        return this.state()
    },
    state() { return { id: items[selected].id, time, playing, montage, cue: state.cue.key, caption: state.cue.text, index: state.index, phase: state.phase, ...scenes[selected].diagnostics() } },
    pixels() {
        const gl = renderer.getContext()
        const bytes = new Uint8Array(canvas.width * canvas.height * 4)
        gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, bytes)
        let bright = 0
        let checksum = 0
        for (let i = 0; i < bytes.length; i += 4) {
            if (Math.max(bytes[i], bytes[i + 1], bytes[i + 2]) > 80) bright += 1
            checksum = (checksum + bytes[i] * (i % 97 + 1) + bytes[i + 1] * 31 + bytes[i + 2] * 17) >>> 0
        }
        return { bright, checksum, total: canvas.width * canvas.height, calls: renderer.info.render.calls }
    },
}
function frame(now) {
    if (playing) {
        const delta = Math.min(0.1, (now - last) / 1000)
        if (montage) {
            montageAge += delta
            if (montageAge >= 12) {
                montageAge = 0
                montageIndex += 1
                if (montageIndex >= highlights[selected].length) {
                    montageIndex = highlights[selected].length - 1
                    montageAge = 12
                    setPlaying(false)
                }
            }
            const cueIndex = highlights[selected][montageIndex]
            const returning = selected === 4 && cueIndex === 18 || selected === 5 && cueIndex === 13 || selected === 3 && cueIndex === 13
            time = items[selected].cues[cueIndex].second + 9 + montageAge * (returning ? 8.5 : 1)
        } else {
            time = Math.min(items[selected].duration, time + delta * Number(document.querySelector('#speed').value))
            if (time >= items[selected].duration) setPlaying(false)
        }
        draw()
    }
    last = now
    requestAnimationFrame(frame)
}
requestAnimationFrame(frame)
