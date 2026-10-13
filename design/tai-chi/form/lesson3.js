// Lesson 3: Grasp the Bird's Tail, left (facing 90) and right (turning
// round to -90): ward off, roll back, press and push.

import { STEP, TRACK, holdBall, other, pressByHip } from './hands.js'
import { brushKneePush, playLute, repulseMonkey, startPose as lessonTwoStart } from './lesson2.js'
import { Form } from '../src/form.js'

const TURN = { L: 1, R: -1 }

// Ward off, roll back, press and push with the `side` foot and forearm
// leading, starting with the `side` heel stepping out from the ball held
// on the other side.
function graspTail(f, side) {
    const back = other(side)
    const turn = TURN[side]
    f.key(1.2, (k) => {
        k.place(side, { from: back, fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(-15 * turn)
    }, `Step the ${side === 'L' ? 'left' : 'right'} heel out to the front`)
    f.key(2.0, (k) => {
        k.ground(side)
        k.load(side, 0.7)
        k.waist(0)
        k.hand(side, { at: [-0.02, -0.07, 0.42], palm: 'back', fingers: 'mid', shape: 'palm', elbow: [1, -0.45, 0] })
        pressByHip(k, back)
        k.look(side)
    }, 'Ward off: the forearm rounds forward at shoulder height, the other hand presses down')

    // Roll back.
    f.key(1.1, (k) => {
        k.waist(12 * turn)
        k.hand(side, { at: [0.07, -0.03, 0.5], palm: 'down+mid', fingers: 'fwd', elbow: [0.6, -1, 0] })
        k.hand(back, { at: [-0.03, -0.14, 0.38], palm: 'up+mid', fingers: 'fwd+mid', shape: 'palm', elbow: [0.4, -1, -0.2] })
        k.look('fwd')
    }, 'Reach forward: front palm turns down, the other palm turns up beneath the forearm')
    f.key(1.1, (k) => {
        k.load(back, 0.6)
        k.waist(-20 * turn)
        k.hand(side, { at: [0.05, -0.3, 0.32], palm: 'back+down', fingers: 'mid+fwd', elbow: [0.6, -1, -0.2] })
        k.hand(back, { at: [0.12, -0.38, 0.24], palm: 'up', fingers: 'fwd+mid', elbow: [0.4, -1, -0.3] })
        k.look(back)
    }, 'Roll back: sit back and draw both hands down past the belly')
    f.key(1.2, (k) => {
        k.load(back, 0.85)
        k.waist(-45 * turn)
        k.hand(side, { at: [0.0, -0.13, 0.27], palm: 'back', fingers: 'mid', elbow: [0.9, -0.6, 0] })
        k.hand(back, { at: [0.37, 0.0, 0.0], palm: 'up+out', fingers: 'out+fwd', elbow: [0.4, -1, -0.5] })
    }, 'The back hand circles up behind to shoulder height; the front forearm comes across the chest')

    // Press.
    f.key(1.2, (k) => {
        k.waist(0)
        k.hand(side, { at: [0.02, -0.12, 0.3], palm: 'back', fingers: 'mid', elbow: [0.9, -0.6, 0] })
        k.hand(back, { at: [0.0, -0.1, 0.24], palm: 'fwd', fingers: 'up+mid', elbow: [0.5, -1, -0.3] })
        k.look('fwd')
    }, 'Turn to the front; the back palm comes to the inside of the front wrist')
    f.key(1.8, (k) => {
        k.load(side, 0.7)
        k.hand(side, { at: [0.02, -0.1, 0.47] })
        k.hand(back, { at: [0.0, -0.08, 0.41] })
    }, 'Press: shift forward and press both hands out together')

    // Push.
    f.key(1.0, (k) => {
        k.hand(side, { at: [0.14, -0.07, 0.46], palm: 'down', fingers: 'fwd', elbow: [0.5, -1, -0.1] })
        k.hand(back, { at: [0.14, -0.07, 0.46], palm: 'down', fingers: 'fwd', elbow: [0.5, -1, -0.1] })
    }, 'Turn both palms down and separate them to shoulder width')
    f.key(1.6, (k) => {
        k.load(back, 0.8)
        k.pitch(side, 16)
        k.hands({ at: [0.15, -0.33, 0.24], palm: 'fwd+down', fingers: 'up+fwd', elbow: [0.5, -1, -0.4] })
    }, 'Sit back, front toes up, and draw the hands back to the belly')
    f.key(2.0, (k) => {
        k.ground(side)
        k.load(side, 0.7)
        k.hands({ at: [0.15, -0.04, 0.48], palm: 'fwd', fingers: 'up', elbow: [0.45, -1, -0.1] })
    }, 'Push: shift forward and push both palms out at shoulder height')
}

// 7. Grasp the Bird's Tail, left.
export function graspLeft(f) {
    f.key(1.3, (k) => {
        k.waist(-40)
        k.hand('R', { at: [0.37, 0.02, 0.0], palm: 'up+out', fingers: 'out+fwd', shape: 'palm', elbow: [0.4, -1, -0.5] })
        k.hand('L', { at: [0.1, -0.08, 0.4], palm: 'down', fingers: 'fwd+mid', shape: 'palm' })
        k.look('R')
    }, 'Turn right: the right hand circles back and up, palm up')
    f.key(1.5, (k) => {
        k.waist(-30)
        holdBall(k, 'R')
        k.load('R')
        k.place('L', { from: 'R', out: 0.12, pitch: -24 })
    }, 'Hold the ball on the right and draw the left foot in')
    graspTail(f, 'L')
}

// 8. Grasp the Bird's Tail, right: turn round to the right first.
export function graspRight(f) {
    f.key(1.3, (k) => {
        k.load('R', 0.85)
        k.pitch('L', 16)
        k.waist(-40)
        k.hand('R', { at: [0.3, -0.04, 0.4], palm: 'out+fwd', fingers: 'up+out', elbow: [0.5, -1, 0] })
        k.hand('L', { at: [0.18, -0.08, 0.42], palm: 'fwd+out', fingers: 'up', elbow: [0.5, -1, 0] })
        k.look('R')
    }, 'Sit back, raise the left toes and turn right')
    f.key(1.4, (k) => {
        k.turn(-90)
        k.pivot('L', -135, 'heel')
        k.waist(-40)
        k.hand('R', { at: [0.45, -0.02, 0.22], palm: 'out+fwd', fingers: 'up+out', elbow: [0.5, -1, 0] })
    }, 'Turn the left toes in; the right hand sweeps out to the right')
    f.key(1.4, (k) => {
        k.ground('L')
        k.load('L', 0.9)
        k.turn(-90)
        k.waist(45)
        holdBall(k, 'L')
        k.look('L')
    }, 'Shift onto the left leg and hold the ball on the left')
    f.key(1.6, (k) => {
        k.load('L')
        k.place('R', { from: 'L', out: 0.12, pitch: -24 })
    }, 'Draw the right foot in, toes touching')
    graspTail(f, 'R')
}

export const MOVES = [
    { id: 'grasp-left', number: 7, lesson: 3, title: 'Grasp the Bird\'s Tail, Left', build: graspLeft, endFacing: 90 },
    { id: 'grasp-right', number: 8, lesson: 3, title: 'Grasp the Bird\'s Tail, Right', build: graspRight, endFacing: -90 },
]

// The end of lesson 2.
export function startPose() {
    const form = new Form(lessonTwoStart())
    brushKneePush(form)
    playLute(form)
    repulseMonkey(form)
    return form.pose
}
