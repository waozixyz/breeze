// Lesson 2: Brush Knee and Push, Play the Lute, Repulse the Monkey. The
// form keeps travelling toward 90; the monkey walks back along the same line.

import { STEP, TRACK, other, pressByHip, pushPalm } from './hands.js'
import { commencing, whiteCrane, wildHorse } from './lesson1.js'
import { Form } from '../src/form.js'
import { standingPose } from '../src/pose.js'

const TURN = { L: 1, R: -1 }

// A hand circled back to ear height beside the body, palm up.
function handBack(k, side) {
    k.hand(side, { at: [0.38, 0.03, 0.0], palm: 'up+out', fingers: 'out+fwd', shape: 'palm', elbow: [0.4, -1, -0.5] })
}

// A hand bent by the ear, about to push.
function handByEar(k, side) {
    k.hand(side, { at: [0.2, 0.08, 0.14], palm: 'fwd+mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.5, -1, -0.2] })
}

// Gathers for a Brush Knee to `side`: the other hand circles back to the
// ear, this hand crosses in front of the other shoulder, the foot comes in.
function gatherBrush(f, side) {
    const back = other(side)
    f.key(1.2, (k) => {
        k.load(back, 0.75)
        k.pitch(side, 20)
        k.waist(-8 * TURN[side])
    }, 'Sit back and raise the front toes')
    f.key(0.8, (k) => {
        k.pivot(side, 45, 'heel')
    }, 'Turn the front toes out')
    f.key(1.3, (k) => {
        k.ground(side)
        k.load(side, 0.8)
        k.waist(35 * TURN[side])
        handBack(k, side)
        k.hand(back, { at: [-0.06, -0.12, 0.28], palm: 'down', fingers: 'mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.look(side)
    }, 'Shift forward; one hand circles back to the ear, the other crosses in front')
    f.key(1.6, (k) => {
        k.load(side)
        k.place(back, { from: side, out: 0.12, pitch: -24 })
    }, 'Draw the back foot in, toes touching')
}

// One Brush Knee and Push leading with the `side` foot: the `side` hand
// brushes past the knee, the other hand pushes from the ear.
function brushKnee(f, side) {
    const pusher = other(side)
    f.key(1.2, (k) => {
        k.place(side, { from: pusher, fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(20 * TURN[pusher])
        handByEar(k, pusher)
        k.hand(side, { at: [0.04, -0.34, 0.3], palm: 'down', fingers: 'mid+fwd', shape: 'palm', elbow: [0.5, -1, -0.3] })
    }, `Step the ${side === 'L' ? 'left' : 'right'} heel forward; the hand by the ear bends`)
    f.key(2.0, (k) => {
        k.ground(side)
        k.load(side, 0.7)
        k.waist(0)
        pushPalm(k, pusher)
        pressByHip(k, side)
        k.look('fwd')
    }, 'Bow stance: push forward and brush past the knee to the hip')
}

// 4. Brush Knee and Push, left, right, left.
export function brushKneePush(f) {
    f.key(1.2, (k) => {
        k.waist(15)
        k.hand('R', { at: [0.08, -0.12, 0.32], palm: 'down+mid', fingers: 'fwd+mid', elbow: [0.5, -1, -0.2] })
        k.hand('L', { at: [0.26, -0.24, 0.24], palm: 'down+out', fingers: 'fwd', elbow: [0.5, -1, -0.2] })
    }, 'Turn slightly left; the right hand starts to fall')
    f.key(1.6, (k) => {
        k.waist(-38)
        handBack(k, 'R')
        k.hand('L', { at: [-0.06, -0.12, 0.28], palm: 'down', fingers: 'mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.place('L', { from: 'R', out: 0.12, pitch: -24 })
        k.look('R')
    }, 'Turn right: right hand circles back to the ear, left hand comes in front, left foot in')
    brushKnee(f, 'L')
    gatherBrush(f, 'L')
    brushKnee(f, 'R')
    gatherBrush(f, 'R')
    brushKnee(f, 'L')
}

// 5. Play the Lute.
export function playLute(f) {
    f.key(1.3, (k) => {
        k.load('L')
        k.place('R', { from: 'L', fwd: -0.34, out: 0.12, turn: 45, pitch: -15 })
        k.hand('R', { at: [0.06, -0.06, 0.46], palm: 'fwd+down', fingers: 'up+fwd' })
    }, 'The right foot follows a half step, toes first')
    f.key(1.1, (k) => {
        k.ground('R')
        k.load('R')
        k.waist(-20)
        k.hand('L', { at: [0.18, -0.24, 0.32], palm: 'mid+up', fingers: 'fwd+up+out' })
        k.hand('R', { at: [0.06, -0.08, 0.32], palm: 'mid+down', fingers: 'fwd+up' })
    }, 'Sit back onto the right leg and turn slightly right')
    f.key(1.8, (k) => {
        k.place('L', { from: 'R', fwd: 0.32, out: 0.12, pitch: 18 })
        k.waist(0)
        k.hand('L', { at: [0.04, 0.1, 0.4], palm: 'mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.3, -1, -0.2] })
        k.hand('R', { at: [-0.02, -0.13, 0.22], palm: 'mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.look('L')
    }, 'Left heel forward: the hands hold the lute, left in front at nose height')
}

// One Repulse the Monkey: `side` steps back, the other hand pushes.
function repulse(f, side, first) {
    const pusher = other(side)
    f.key(1.0, (k) => {
        k.waist(35 * TURN[pusher])
        k.hand(pusher, { at: [0.26, -0.36, 0.14], palm: 'up', fingers: 'fwd+out', shape: 'palm', elbow: [0.4, -1, -0.4] })
        k.hand(side, { at: [0.08, -0.04, 0.42], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, -0.2] })
    }, first ? 'Turn the palms up; the right hand drops past the hip' : 'Turn the palms up; the back hand drops past the hip')
    f.key(1.1, (k) => {
        k.waist(40 * TURN[pusher])
        handBack(k, pusher)
        k.look(pusher)
    }, 'Circle it back and up to shoulder height, eyes following')
    f.key(1.1, (k) => {
        k.place(side, { from: pusher, out: 0.14, pitch: -15, lift: 0.05 })
        k.waist(20 * TURN[pusher])
        handByEar(k, pusher)
        k.hand(side, { at: [0.12, -0.16, 0.34], palm: 'up', fingers: 'fwd', elbow: [0.3, -1, -0.3] })
        k.look('fwd')
    }, `Lift the ${side === 'L' ? 'left' : 'right'} foot past the standing foot`)
    f.key(1.1, (k) => {
        k.place(side, { from: pusher, fwd: -0.42, out: 0.18, turn: 40, pitch: -15 })
        k.hand(side, { at: [0.18, -0.32, 0.22], palm: 'up', fingers: 'fwd', elbow: [0.3, -1, -0.4] })
    }, 'Step back, landing on the ball of the foot')
    f.key(1.9, (k) => {
        k.ground(side)
        k.load(side)
        k.toes(pusher, 0, 'ball')
        k.pitch(pusher, -10)
        k.waist(0)
        pushPalm(k, pusher)
        k.hand(side, { at: [0.22, -0.42, 0.1], palm: 'up', fingers: 'fwd', elbow: [0.4, -1, -0.5] })
    }, 'Sit back and straighten the front foot; push forward, draw the other hand to the hip')
}

// 6. Repulse the Monkey, four times.
export function repulseMonkey(f) {
    repulse(f, 'L', true)
    repulse(f, 'R', false)
    repulse(f, 'L', false)
    repulse(f, 'R', false)
}

export const MOVES = [
    { id: 'brush-knee', number: 4, lesson: 2, title: 'Brush Knee and Push', build: brushKneePush, endFacing: 90 },
    { id: 'play-lute', number: 5, lesson: 2, title: 'Play the Lute', build: playLute, endFacing: 90 },
    { id: 'repulse-monkey', number: 6, lesson: 2, title: 'Repulse the Monkey', build: repulseMonkey, endFacing: 90 },
]

// The end of lesson 1.
export function startPose() {
    const form = new Form(standingPose())
    commencing(form)
    wildHorse(form)
    whiteCrane(form)
    return form.pose
}
