// Lesson 7: Fair Lady Works at Shuttles, Needle at Sea Bottom, Fan Through
// the Back. The lesson starts on the right leg after Golden Rooster, facing
// 270, and travels along that line: the shuttles go out to the two front
// diagonals (225 and 315) and the needle and fan face 270 again.

import { goldenRoosterRightPose } from './boundaries.js'
import { SINK, STEP, TRACK, holdBall, other, pressByHip } from './hands.js'

const SIDE_NAME = { L: 'left', R: 'right' }

// The hand that blocks above the forehead, palm turned out and up, the
// forearm across the brow.
function blockAboveForehead(k, side) {
    k.hand(side, { at: [0.14, 0.26, 0.3], palm: 'up+fwd+out', fingers: 'mid', shape: 'palm', elbow: [0.9, -0.5, 0.1] })
}

// The other hand pushes forward at nose height.
function pushAtNose(k, side) {
    k.hand(side, { at: [0.06, 0.1, 0.48], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
}

// One shuttle to the `side` front diagonal, from the ball held on the other
// side with the `side` foot drawn in. `turn` is the change of facing and
// `backPivot` turns the back foot in behind the new line.
function shuttle(f, side, { turn, backPivot }) {
    const back = other(side)
    f.key(2.0, (k) => {
        k.turn(turn)
        k.place(side, { from: back, fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(side === 'L' ? -30 : 30)
        k.hand(side, { at: [0.02, 0.0, 0.3], palm: 'back+mid', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, 0] })
        k.hand(back, { at: [-0.02, -0.3, 0.3], palm: 'down+fwd', fingers: 'mid+fwd', shape: 'palm' })
        k.look(side)
    }, `Turn and step the ${SIDE_NAME[side]} heel out to the front corner`)
    f.key(2.4, (k) => {
        k.ground(side)
        k.load(side, 0.7)
        k.sink(SINK)
        k.waist(0)
        k.hand(side, { at: [0.1, 0.14, 0.3], palm: 'fwd+up', fingers: 'mid+up', shape: 'palm', elbow: [0.9, -0.6, 0.1] })
        k.hand(back, { at: [0.04, 0.02, 0.4], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.look(back)
    }, 'Shift forward into the bow stance as the hands rise')
    f.key(1.6, (k) => {
        k.pivot(back, backPivot, 'ball')
        k.load(side, 0.75)
        blockAboveForehead(k, side)
        pushAtNose(k, back)
    }, `Turn the back heel out: the ${SIDE_NAME[side]} hand blocks above the forehead, the other palm pushes`)
}

// 18. Fair Lady Works at Shuttles, right and left.
export function shuttles(f) {
    f.key(2.6, (k) => {
        k.place('L', { from: 'R', fwd: 0.32, out: 0.12, turn: 30, pitch: 12 })
        k.sink(SINK)
        k.waist(15)
        k.hand('L', { at: [0.12, -0.08, 0.3], palm: 'down+mid', fingers: 'mid+fwd', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.hand('R', { at: [0.1, -0.38, 0.26], palm: 'up', fingers: 'mid+fwd', shape: 'palm' })
        k.look('L')
    }, 'Lower the left foot to the front, toes turned out')
    f.key(2.6, (k) => {
        k.ground('L')
        k.load('L', 0.85)
        k.waist(30)
        holdBall(k, 'L')
        k.look('L')
    }, 'Sit into both knees and hold the ball on the left')
    f.key(2.2, (k) => {
        k.load('L')
        k.place('R', { from: 'L', out: 0.22, fwd: -0.06, pitch: -24 })
    }, 'Draw the right foot in, toes touching')
    shuttle(f, 'R', { turn: -45, backPivot: -30 })
    f.key(2.0, (k) => {
        k.load('R', 0.3)
        k.pitch('R', 18)
        k.waist(-8)
        k.hand('R', { at: [0.16, 0.1, 0.32], palm: 'fwd+out', fingers: 'mid+up', shape: 'palm', elbow: [0.8, -1, 0] })
        k.hand('L', { at: [0.08, -0.06, 0.42], palm: 'fwd+down', fingers: 'up+fwd', shape: 'palm' })
    }, 'Sit back a little and raise the right toes')
    f.key(1.2, (k) => {
        k.pivot('R', 20, 'heel')
    }, 'Turn the right toes out a little')
    f.key(2.4, (k) => {
        k.ground('R')
        k.load('R', 0.85)
        k.pitch('L', -25)
        k.waist(-30)
        holdBall(k, 'R')
        k.look('R')
    }, 'Shift forward and hold the ball on the right')
    f.key(2.2, (k) => {
        k.load('R')
        k.place('L', { from: 'R', out: 0.2, fwd: -0.06, pitch: -24 })
    }, 'Draw the left foot in, toes touching')
    shuttle(f, 'L', { turn: 90, backPivot: -65 })
}

// 19. Needle at Sea Bottom.
export function needle(f) {
    f.key(1.6, (k) => {
        k.load('L', 0.95)
        k.shift(-0.05)
        k.pitch('R', -40)
        k.waist(10)
        k.hand('R', { at: [0.1, -0.1, 0.45], palm: 'fwd+mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.5, -1, -0.1] })
        k.hand('L', { at: [0.12, -0.05, 0.42], palm: 'down+fwd', fingers: 'mid+fwd', shape: 'palm', elbow: [0.6, -1, 0] })
    }, 'Shift the weight onto the left foot; the right heel lifts')
    f.key(2.0, (k) => {
        k.turn(-45)
        k.load('L')
        k.place('R', { from: 'L', fwd: -0.3, out: 0.12, turn: 45, pitch: -12 })
        k.waist(0)
        k.hand('R', { at: [0.18, -0.25, 0.3], palm: 'mid+down', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.hand('L', { at: [0.1, -0.2, 0.4], palm: 'down', fingers: 'fwd+mid', shape: 'palm' })
        k.look('fwd')
    }, 'Bring the right foot a half step in behind')
    f.key(2.4, (k) => {
        k.ground('R')
        k.load('R')
        k.shift(0)
        k.waist(-25)
        k.hand('R', { at: [0.16, 0.06, 0.3], palm: 'mid', fingers: [0, 0.3, 1], shape: 'palm', elbow: [0.3, -1, 0] })
        k.hand('L', { at: [0.12, -0.36, 0.34], palm: 'down', fingers: 'fwd+mid', shape: 'palm' })
        k.look('R')
    }, 'Sit back onto the right leg; draw the right hand up by the ear')
    f.key(1.6, (k) => {
        k.place('L', { from: 'R', fwd: 0.38, out: 0.12, pitch: -16 })
        k.waist(-10)
        k.look('fwd')
    }, 'Ease the left foot forward, toes touching')
    f.key(3.2, (k) => {
        k.waist(0)
        k.lean(32)
        k.sink(SINK + 0.02)
        k.hand('R', { at: [0.02, -0.34, 0.44], palm: 'mid', fingers: 'fwd+down', shape: 'palm', elbow: [0.3, -1, -0.3] })
        pressByHip(k, 'L', { fwd: 0.22 })
        k.look({ pitch: 18 })
    }, 'Lean forward and thrust the right fingers down in front')
}

// 20. Fan Through the Back.
export function fanThroughBack(f) {
    f.key(2.4, (k) => {
        k.lean(0)
        k.sink(SINK)
        k.waist(-15)
        k.place('L', { from: 'R', fwd: STEP, out: TRACK, pitch: 18 })
        k.hand('R', { at: [0.06, -0.04, 0.38], palm: 'mid', fingers: 'fwd+up', shape: 'palm', elbow: [0.4, -1, -0.2] })
        k.hand('L', { at: [-0.02, -0.06, 0.28], palm: 'mid+fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.look('fwd')
    }, 'Rise, lift both hands and step the left heel forward')
    f.key(3.0, (k) => {
        k.ground('L')
        k.load('L', 0.7)
        k.waist(-10)
        k.hand('R', { at: [0.2, 0.24, 0.24], palm: 'out+up', fingers: 'mid+fwd', shape: 'palm', elbow: [0.8, -1, 0] })
        k.hand('L', { at: [0.06, -0.02, 0.5], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.look('L')
    }, 'Bow stance: the right hand opens above the temple, the left palm pushes')
}

export const MOVES = [
    { id: 'shuttles', number: 18, lesson: 7, title: 'Fair Lady Works at Shuttles', build: shuttles, endFacing: 315 },
    { id: 'needle', number: 19, lesson: 7, title: 'Needle at Sea Bottom', build: needle, endFacing: 270 },
    { id: 'fan-through-back', number: 20, lesson: 7, title: 'Fan Through the Back', build: fanThroughBack, endFacing: 270 },
]

// The lesson starts on the right leg after Golden Rooster.
export function startPose() {
    return goldenRoosterRightPose()
}
