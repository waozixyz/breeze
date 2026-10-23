// Sun Salutation on the studio's skinned 3D woman, to design her body in
// real 3D before the app's flat painter draws it.
//
// The motion is the app's own: every frame of the solved skeleton exported
// by `scripts/render-sun-salutation-live.py --motion` from the Ziran pose
// solver. This page turns those joints into the studio's segment frames and
// plays them on a skinned studio character (the app's woman by default), in
// the app's camera or an orbit.
//
// Query: ?t=SECONDS to start there, ?camera=app|side|back|front|orbit,
// ?figure=sunWoman|sageBun|sageMale,
// ?render=JOB&stills=T1,T2 to post stills to tools/sun-salutation.mjs.

import { Quaternion, Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { makeRig } from './rig.js'
import { frameQuat } from './solve.js'
import { createStage } from './view/stage.js'
import { createFigure } from './view/figure.js'
import './view/characters.js'

const params = new URLSearchParams(location.search)
const SIDES = ['L', 'R']
const TILT = 7 * Math.PI / 180

const vector = (a) => new Vector3(a[0], a[1], a[2])
const quaternion = (a) => new Quaternion(a[0], a[1], a[2], a[3])
const axis = (quat, x, y, z) => new Vector3(x, y, z).applyQuaternion(quat)

// The studio's segment frames from one exported frame of the app's solver.
function segmentsOf(frame, rig) {
    const H = rig.height
    const segments = {}
    const pelvisQuat = quaternion(frame.pelvis_quat)
    const chestQuat = quaternion(frame.chest_quat)
    const headQuat = quaternion(frame.head_quat)
    const pelvis = vector(frame.pelvis)
    const spine1 = vector(frame.spine1)
    const chest = vector(frame.chest)
    const neckBase = vector(frame.neck_base)
    const pelvisZ = axis(pelvisQuat, 0, 0, 1)
    const chestZ = axis(chestQuat, 0, 0, 1)
    segments.pelvis = { pos: pelvis, quat: pelvisQuat }
    segments.spine0 = { pos: pelvis.clone(), quat: frameQuat(spine1.clone().sub(pelvis), pelvisZ.clone().lerp(chestZ, 0.4)) }
    segments.spine1 = { pos: spine1, quat: frameQuat(chest.clone().sub(spine1), pelvisZ.clone().lerp(chestZ, 0.8)) }
    segments.chest = { pos: chest, quat: chestQuat }
    segments.neck = { pos: neckBase, quat: chestQuat.clone().slerp(headQuat, 0.5) }
    const headPivot = vector(frame.head_center).sub(new Vector3(0, 0.065 * H, 0.012 * H).applyQuaternion(headQuat))
    segments.head = { pos: headPivot, quat: headQuat }
    const hands = {}
    SIDES.forEach((side, index) => {
        const sign = index === 0 ? 1 : -1
        const shoulder = vector(frame.shoulders[index])
        const elbow = vector(frame.elbows[index])
        const wrist = vector(frame.wrists[index])
        const handQuat = quaternion(frame.hand_quats[index])
        const clavicleRoot = neckBase.clone().add(new Vector3(sign * 0.012 * H, -0.008 * H, 0.012 * H).applyQuaternion(chestQuat))
        const upperDir = elbow.clone().sub(shoulder)
        const foreDir = wrist.clone().sub(elbow)
        const palmNormal = axis(handQuat, 0, 0, 1)
        segments[`clavicle${side}`] = { pos: clavicleRoot, quat: frameQuat(clavicleRoot.clone().sub(shoulder), chestZ) }
        segments[`upperArm${side}`] = { pos: shoulder, quat: frameQuat(upperDir.clone().negate(), foreDir, chestZ) }
        segments[`foreArm${side}`] = { pos: elbow, quat: frameQuat(foreDir.clone().negate(), palmNormal, foreDir.clone().negate().cross(upperDir)) }
        segments[`hand${side}`] = { pos: wrist, quat: handQuat }
        hands[side] = { shape: frame.hand_shapes[index] }
        const hip = vector(frame.hips[index])
        const knee = vector(frame.knees[index])
        const ankle = vector(frame.ankles[index])
        const footQuat = quaternion(frame.foot_quats[index])
        // The knee bends toward where it sits off the hip-ankle line; a
        // straight leg keeps the foot's forward.
        const line = ankle.clone().sub(hip)
        const share = knee.clone().sub(hip).dot(line) / Math.max(line.lengthSq(), 1e-9)
        let pole = knee.clone().sub(hip.clone().addScaledVector(line, share))
        if (pole.length() < 0.004 * H) {
            pole = axis(footQuat, 0, 0, 1)
        }
        segments[`thigh${side}`] = { pos: hip, quat: frameQuat(knee.clone().sub(hip).negate(), pole) }
        segments[`shin${side}`] = { pos: knee, quat: frameQuat(ankle.clone().sub(knee).negate(), pole) }
        segments[`foot${side}`] = { pos: ankle, quat: footQuat }
        segments[`toes${side}`] = { pos: vector(frame.balls[index]), quat: quaternion(frame.toes_quats[index]) }
    })
    return { segments, hands }
}

const motion = await (await fetch('lab/sun-salutation-motion.json')).json()
const rig = makeRig('jadeWoman')
const canvas = document.getElementById('view')
const stage = createStage(canvas, { preserveDrawingBuffer: params.has('render') })
const figure = createFigure(rig, params.get('figure') ?? 'sunWoman')
stage.scene.add(figure.root)
const controls = new OrbitControls(stage.camera, canvas)
controls.enabled = false

const duration = motion.frames.length / motion.fps
let time = Number(params.get('t') ?? 0)
let playing = !params.has('render') && !params.has('t')
let cameraMode = params.get('camera') ?? 'app'

// The app's camera: its turn and tilt, centred on the figure; or a fixed side,
// back or front view; or a free orbit.
function placeCamera(frame) {
    const pelvis = vector(frame.pelvis)
    const center = new Vector3(pelvis.x, 0, pelvis.z)
    stage.follow(center)
    if (cameraMode === 'orbit') {
        controls.enabled = true
        controls.target.set(pelvis.x, Math.max(0.4, pelvis.y), pelvis.z)
        controls.update()
        return
    }
    controls.enabled = false
    const turns = { side: -90, back: -150, front: 0 }
    const yaw = (turns[cameraMode] ?? frame.yaw) * Math.PI / 180
    const distance = 4.4
    const direction = new Vector3(Math.sin(yaw), 0, Math.cos(yaw))
    const target = new Vector3(center.x, 0.62, center.z)
    stage.camera.position.copy(target).addScaledVector(direction, distance * Math.cos(TILT))
    stage.camera.position.y += distance * Math.sin(TILT)
    stage.camera.lookAt(target)
}

function show(second) {
    const index = Math.max(0, Math.min(motion.frames.length - 1, Math.round(second * motion.fps)))
    const frame = motion.frames[index]
    figure.update(segmentsOf(frame, rig))
    placeCamera(frame)
    stage.render()
    const label = document.getElementById('time')
    if (label) {
        label.textContent = `${second.toFixed(2)} s`
    }
    const slider = document.getElementById('scrub')
    if (slider) {
        slider.value = String(second)
    }
}

function resize() {
    const width = Number(params.get('width') ?? canvas.clientWidth)
    const height = Number(params.get('height') ?? canvas.clientHeight)
    stage.resize(width, height)
}

async function renderStills() {
    const job = params.get('render')
    const stills = (params.get('stills') ?? '0').split(',').map(Number)
    resize()
    for (let index = 0; index < stills.length; index += 1) {
        show(stills[index])
        const blob = await new Promise((done) => canvas.toBlob(done, 'image/png'))
        await fetch(`/render/${job}/frame/${index}`, { method: 'POST', body: blob })
    }
    await fetch(`/render/${job}/done`, { method: 'POST', body: JSON.stringify({ frames: stills.length }) })
}

if (params.has('render')) {
    renderStills().catch((error) => fetch(`/render/${params.get('render')}/error`, { method: 'POST', body: String(error?.stack ?? error) }))
} else {
    const slider = document.getElementById('scrub')
    slider.max = String(duration)
    slider.addEventListener('input', () => {
        playing = false
        time = Number(slider.value)
        show(time)
    })
    document.getElementById('play').addEventListener('click', () => {
        playing = !playing
    })
    for (const button of document.querySelectorAll('[data-camera]')) {
        button.addEventListener('click', () => {
            cameraMode = button.dataset.camera
            show(time)
        })
    }
    addEventListener('resize', () => {
        resize()
        show(time)
    })
    resize()
    let last = performance.now()
    const tick = (now) => {
        if (playing) {
            time = (time + (now - last) / 1000) % duration
        }
        last = now
        show(time)
        requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
}
