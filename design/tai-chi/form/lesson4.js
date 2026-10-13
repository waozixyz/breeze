// Lesson 4: Single Whip, Wave Hands Like Clouds, Single Whip. Single Whip
// turns back to 90; Cloud Hands face the front (0) and step sideways
// toward 90.

import { STEP, TRACK } from './hands.js'
import { graspLeft, graspRight, startPose as lessonThreeStart } from './lesson3.js'
import { Form } from '../src/form.js'

// The right hand gathers into a hook out to the right; the left hand
// arrives in front of the right shoulder; the left foot comes in.
function hookAndGather(f, { turnToStep }) {
    f.key(1.2, (k) => {
        k.load('R', 0.85)
        k.waist(-30)
        k.hand('R', { at: [0.55, -0.02, 0.24], palm: 'out+fwd', fingers: 'up+out', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('L', { at: [-0.02, -0.3, 0.28], palm: 'back+up', fingers: 'mid', shape: 'palm', elbow: [0.5, -1, -0.3] })
        k.look('R')
    }, 'Turn right: the right hand sweeps out to the right, the left hand passes the belly')
    f.key(1.0, (k) => {
        k.load('R')
        k.waist(-35)
        k.hand('R', { at: [0.66, -0.02, 0.2], palm: 'back+mid', fingers: 'down', shape: 'hook', elbow: [0.3, -1, 0] })
        k.hand('L', { at: [-0.12, -0.11, 0.28], palm: 'back', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.look('L')
    }, 'The right hand gathers into a hook; the left hand comes to the right shoulder')
    f.key(1.0, (k) => {
        k.turn(turnToStep)
        k.waist(-35 - turnToStep)
        k.place('L', { from: 'R', out: 0.14, pitch: -24 })
    }, 'Draw the left foot in, toes touching')
}

// Steps out into Single Whip toward the facing direction.
function openWhip(f, { backPivot = 0 } = {}) {
    f.key(1.2, (k) => {
        k.place('L', { from: 'R', fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(-35)
        k.look('L')
    }, 'Turn left and step the left heel out to the front')
    f.key(2.2, (k) => {
        k.ground('L')
        if (backPivot) {
            k.pivot('R', backPivot, 'ball')
        }
        k.load('L', 0.7)
        k.hips(-10)
        k.chest(-15)
        k.hand('L', { at: [0.1, -0.03, 0.48], palm: 'fwd+out', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [0.66, -0.02, 0.2], palm: 'back+mid', fingers: 'down', shape: 'hook', elbow: [0.3, -1, 0] })
    }, 'Bow stance: the left palm turns and pushes forward, the hook stays out to the right')
}

// 9. Single Whip, from Grasp the Bird's Tail on the right.
export function singleWhip(f) {
    f.key(1.3, (k) => {
        k.load('L', 0.85)
        k.pitch('R', 16)
        k.waist(25)
        k.hand('L', { at: [0.2, -0.06, 0.42], palm: 'fwd+out', fingers: 'up', elbow: [0.5, -1, 0] })
        k.hand('R', { at: [0.12, -0.16, 0.42], palm: 'down+mid', fingers: 'fwd', elbow: [0.5, -1, 0] })
        k.look('L')
    }, 'Sit back onto the left leg, raise the right toes and turn left')
    f.key(1.5, (k) => {
        k.turn(90)
        k.pivot('R', -135, 'heel')
        k.waist(35)
        k.hand('L', { at: [0.45, -0.03, 0.24], palm: 'out+fwd', fingers: 'up+out', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [-0.1, -0.36, 0.22], palm: 'up+back', fingers: 'mid', elbow: [0.5, -1, -0.3] })
    }, 'Turn the right toes in; the left hand sweeps left, the right hand passes the belly')
    f.key(1.0, (k) => {
        k.ground('R')
        k.load('R', 0.6)
        k.waist(0)
        k.hand('R', { at: [0.24, -0.2, 0.32], palm: 'back+out', fingers: 'up+mid' })
        k.hand('L', { at: [0.12, -0.3, 0.3], palm: 'back', fingers: 'mid+up' })
        k.look('R')
    }, 'Shift the weight back toward the right leg')
    hookAndGather(f, { turnToStep: 90 })
    openWhip(f)
}

// One Cloud Hands turn to `side`: that hand passes in front of the face and
// turns out, the other hand passes the belly and rises to the shoulder.
function cloudTurn(f, side) {
    const sign = side === 'L' ? 1 : -1
    const lower = side === 'L' ? 'R' : 'L'
    f.key(1.3, (k) => {
        k.ground('L')
        k.ground('R')
        k.load(0.5)
        k.waist(0)
        k.hand(side, { at: [0.03, 0.05, 0.32], palm: 'back', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.hand(lower, { at: [0.02, -0.42, 0.26], palm: 'back+up', fingers: 'mid+down', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.look(side)
    }, `Turn ${side === 'L' ? 'left' : 'right'}: the upper hand passes in front of the face, the lower hand past the belly`)
    f.key(1.3, (k) => {
        k.load(side)
        k.waist(40 * sign)
        k.hand(side, { at: [0.25, -0.02, 0.32], palm: 'out+fwd', fingers: 'up+mid' })
        k.hand(lower, { at: [-0.12, -0.12, 0.3], palm: 'back', fingers: 'up+mid' })
    }, 'Weight across; the upper palm turns out, the lower hand rises to the shoulder')
}

// 10. Wave Hands Like Clouds, three times.
export function cloudHands(f) {
    f.key(1.3, (k) => {
        k.load('R', 0.8)
        k.pitch('L', 16)
        k.waist(-25)
        k.hand('R', { at: [0.6, -0.02, 0.22], palm: 'out+fwd', fingers: 'up+out', shape: 'palm', elbow: [0.4, -1, 0] })
    }, 'Shift the weight right, raise the left toes and open the hook')
    f.key(1.4, (k) => {
        k.turn(-90)
        k.toes('L', 0)
        k.waist(-35)
        k.hand('L', { at: [-0.12, -0.12, 0.3], palm: 'back', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.hand('R', { at: [0.25, -0.02, 0.32], palm: 'out+fwd', fingers: 'up+mid', shape: 'palm', elbow: [0.5, -1, -0.1] })
        k.look('R')
    }, 'Turn the left toes in to face the front; the hook opens, the left hand rises to the right shoulder')
    for (let round = 0; round < 3; round += 1) {
        cloudTurn(f, 'L')
        f.key(1.5, (k) => {
            k.place('R', { from: 'L', out: 0.17, pitch: -12 })
        }, 'Bring the right foot in beside the left, toes first')
        if (round < 2) {
            cloudTurn(f, 'R')
            f.key(1.5, (k) => {
                k.place('L', { from: 'R', out: 0.42, pitch: -12 })
            }, 'Step the left foot out to the side, toes first')
        }
    }
    f.key(0.9, (k) => {
        k.ground('R')
        k.load(0.5)
    }, 'Set the right foot down')
}

// 11. Single Whip, from Cloud Hands.
export function singleWhipAgain(f) {
    f.key(1.3, (k) => {
        k.load('R', 0.7)
        k.waist(-10)
        k.hand('R', { at: [0.1, 0.03, 0.32], palm: 'back', fingers: 'up+mid', elbow: [0.6, -1, -0.2] })
        k.hand('L', { at: [0.04, -0.4, 0.26], palm: 'back+up', fingers: 'mid+down', elbow: [0.4, -1, -0.3] })
        k.look('R')
    }, 'Turn right; the right hand passes in front of the face')
    hookAndGather(f, { turnToStep: 90 })
    openWhip(f, { backPivot: -45 })
}

export const MOVES = [
    { id: 'single-whip', number: 9, lesson: 4, title: 'Single Whip', build: singleWhip, endFacing: 90 },
    { id: 'cloud-hands', number: 10, lesson: 4, title: 'Wave Hands Like Clouds', build: cloudHands, endFacing: 0 },
    { id: 'single-whip-again', number: 11, lesson: 4, title: 'Single Whip', build: singleWhipAgain, endFacing: 90 },
]

// The end of lesson 3.
export function startPose() {
    const form = new Form(lessonThreeStart())
    graspLeft(form)
    graspRight(form)
    return form.pose
}
