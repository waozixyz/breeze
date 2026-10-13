// Lesson 1: Commencing, Part the Wild Horse's Mane, White Crane Spreads
// Its Wings. The form starts facing the audience; the first movements
// travel to the practitioner's left.

import { SINK, STEP, TRACK, holdBall, other, pressByHip, raiseToEyes } from './hands.js'

// 1. Commencing.
export function commencing(f) {
    f.hold(2.0, 'Stand naturally: feet together, arms relaxed, eyes level')
    f.key(1.3, (k) => {
        k.load('R')
    }, 'Settle the weight onto the right foot')
    f.key(0.9, (k) => {
        k.lift('L', 0.03, -12)
    }, 'Lift the left heel, then the foot')
    f.key(1.1, (k) => {
        k.place('L', { from: 'R', out: 0.3, pitch: -10 })
    }, 'Step out to shoulder width, toes first')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load(0.5)
    }, 'Lower the heel and centre the weight')
    f.key(3.2, (k) => {
        k.hands({ at: [0.18, -0.02, 0.48], palm: 'down', fingers: 'fwd', elbow: [0.3, -1, -0.3] })
    }, 'Float both arms up to shoulder height, palms down')
    f.key(3.2, (k) => {
        k.sink(0.1)
        k.hands({ at: [0.17, -0.44, 0.25], palm: 'down', fingers: 'fwd', elbow: [0.45, -1, -0.45] })
    }, 'Bend the knees and press the palms down to the belly')
}

// One Part the Wild Horse's Mane to `side`, starting from the ball held on
// the other side with the `side` foot drawn in.
function partMane(f, side, { turn = 0, backPivot = 0 } = {}) {
    const back = other(side)
    f.key(1.2, (k) => {
        k.turn(turn)
        k.place(side, { from: back, fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(side === 'L' ? -20 : 20)
    }, `Step the ${side === 'L' ? 'left' : 'right'} heel out to the front`)
    f.key(2.0, (k) => {
        k.ground(side)
        if (backPivot) {
            k.pivot(back, backPivot, 'ball')
        }
        k.load(side, 0.7)
        k.sink(SINK)
        k.waist(0)
        raiseToEyes(k, side)
        pressByHip(k, back)
        k.look(side)
    }, 'Bow stance: the front hand opens to eye level, the back hand presses down')
}

// Sits back, turns the front toes out and gathers the ball on that side.
function gatherBall(f, side) {
    const back = other(side)
    f.key(1.2, (k) => {
        k.load(back, 0.75)
        k.pitch(side, 20)
        k.waist(side === 'L' ? 8 : -8)
    }, 'Sit back and raise the front toes')
    f.key(0.8, (k) => {
        k.pivot(side, 45, 'heel')
    }, 'Turn the front toes out')
    f.key(1.3, (k) => {
        k.ground(side)
        k.load(side, 0.8)
        k.waist(side === 'L' ? 30 : -30)
        holdBall(k, side)
        k.look(side)
    }, `Shift forward and hold the ball on the ${side === 'L' ? 'left' : 'right'}`)
    f.key(1.7, (k) => {
        k.load(side)
        k.place(back, { from: side, out: 0.12, fwd: 0, pitch: -24 })
    }, 'Draw the back foot in, toes touching')
}

// 2. Part the Wild Horse's Mane, left, right, left.
export function wildHorse(f) {
    f.key(1.4, (k) => {
        k.load('R')
        k.sink(SINK)
        k.waist(-30)
        holdBall(k, 'R')
        k.look('R')
    }, 'Turn slightly right and hold the ball on the right')
    f.key(1.0, (k) => {
        k.place('L', { from: 'R', out: 0.12, pitch: -24 })
    }, 'Draw the left foot in, toes touching')
    // Turn to the left: the right heel pushes out behind the new direction.
    partMane(f, 'L', { turn: 90, backPivot: -45 })
    gatherBall(f, 'L')
    partMane(f, 'R')
    gatherBall(f, 'R')
    partMane(f, 'L')
}

// 3. White Crane Spreads Its Wings.
export function whiteCrane(f) {
    f.key(1.3, (k) => {
        k.load('L', 0.95)
        k.waist(20)
        holdBall(k, 'L')
        k.look('L')
    }, 'Turn slightly left and hold the ball on the left')
    f.key(1.0, (k) => {
        k.load('L')
        k.place('R', { from: 'L', fwd: -0.34, out: 0.12, turn: 45, pitch: -15 })
    }, 'Bring the right foot a half step in behind')
    f.key(1.2, (k) => {
        k.ground('R')
        k.load('R')
        k.waist(-25)
        k.hand('R', { at: [0.18, 0.08, 0.3], palm: 'mid+back', fingers: 'up+mid', elbow: [0.6, -1, 0] })
        k.hand('L', { at: [0.15, -0.35, 0.28], palm: 'down', fingers: 'fwd+mid' })
        k.look('R')
    }, 'Sit back onto the right leg and turn slightly right')
    f.key(1.8, (k) => {
        k.place('L', { from: 'R', fwd: 0.3, out: 0.12, pitch: -16 })
        k.waist(0)
        k.hand('R', { at: [0.2, 0.22, 0.28], palm: 'mid+back', fingers: 'up+mid', elbow: [0.6, -1, 0] })
        k.hand('L', { at: [0.2, -0.5, 0.18], palm: 'down', fingers: 'fwd' })
        k.look('fwd')
    }, 'Empty stance: right hand rises by the temple, left hand presses by the hip')
}

export const MOVES = [
    { id: 'commencing', number: 1, lesson: 1, title: 'Commencing', build: commencing, endFacing: 0 },
    { id: 'wild-horse', number: 2, lesson: 1, title: 'Part the Wild Horse\'s Mane', build: wildHorse, endFacing: 90 },
    { id: 'white-crane', number: 3, lesson: 1, title: 'White Crane Spreads Its Wings', build: whiteCrane, endFacing: 90 },
]
