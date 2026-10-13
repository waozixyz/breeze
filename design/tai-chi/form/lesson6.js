// Lesson 6: Push Down and Stand on One Leg (Snake Creeps Down and Golden
// Rooster), left and right. Both crouches stretch a leg out along 270,
// the line the form travels; the body faces across the line while low and
// turns into it as it rises.

import { Form } from '../src/form.js'
import { pressByHip } from './hands.js'
import { singleWhipPose } from './boundaries.js'
import { MOVES as LESSON_5 } from './lesson5.js'

const CROUCH_SINK = 0.44
const RISING_SINK = 0.26
const LONG_BOW_SINK = 0.24
const ROOSTER_SINK = 0.06

// A hook hand held out to the `side`, fingertips pointing down.
function hook(k, side, at = [0.68, -0.06, 0.18]) {
    k.hand(side, { at, palm: 'back+mid', fingers: 'down', shape: 'hook', elbow: [0.5, -0.7, -0.6] })
}

// One Snake Creeps Down and Golden Rooster. `low` is the leg that
// stretches out along the line; `stand` is the crouching leg. The body
// faces across the line, turned 80° toward the standing side's
// direction (`across`: -1 turns right, +1 turns left).
function snakeAndRooster(f, low, across) {
    const stand = low === 'L' ? 'R' : 'L'
    const lowName = low === 'L' ? 'left' : 'right'
    const standName = stand === 'L' ? 'left' : 'right'
    f.key(3.2, (k) => {
        k.deep(true)
        k.sink(CROUCH_SINK)
        k.load(stand)
        k.pitch(stand, 0)
        k.place(low, { from: stand, fwd: 0.76, out: 0.08, turn: -80 })
        k.lean(15)
        k.chest(across * 70)
        k.hips(across * 75)
        k.hand(low, { at: [0.05, -0.36, 0.3], palm: 'out', fingers: 'down+fwd', shape: 'palm', elbow: [0.4, -1, -0.2] })
        k.look(stand)
    }, `Crouch on the ${standName} leg and stretch the ${lowName} leg out along the line`)
    f.key(2.8, (k) => {
        k.load(stand, 0.82)
        k.lean(20)
        k.chest(across * 30)
        k.hips(across * 50)
        k.hand(low, { at: [0.08, -0.4, 0.4], palm: 'mid', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, 0] })
        hook(k, stand, [0.64, -0.02, -0.25])
        k.look(low)
    }, `Thread the ${lowName} hand forward along the inside of the ${lowName} leg`)
    f.key(0.9, (k) => {
        k.pitch(low, 18)
        k.load(low, 0.3)
        k.lean(16)
    }, `Raise the ${lowName} toes`)
    f.key(2.0, (k) => {
        k.pivot(low, 80, 'heel')
        k.pitch(stand, 10)
        k.load(low, 0.5)
        k.sink(RISING_SINK)
        k.lean(10)
        k.chest(across * 10)
        k.hips(across * 25)
        k.hand(low, { at: [0.08, -0.12, 0.5], palm: 'mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand(stand, { at: [0.28, -0.34, -0.22], palm: 'up+mid', fingers: 'back+up', shape: 'hook', elbow: [0.3, -1, -0.2] })
    }, `Turn the ${lowName} toes out and rise forward`)
    f.key(2.2, (k) => {
        k.deep(false)
        k.ground(low)
        k.pivot(stand, -45, 'heel')
        k.ground(stand)
        k.load(low, 0.75)
        k.sink(LONG_BOW_SINK)
        k.lean(0)
        k.waist(0)
        k.hand(low, { at: [0.08, -0.02, 0.48], palm: 'mid+fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand(stand, { at: [0.3, -0.3, -0.24], palm: 'up+mid', fingers: 'back+up', shape: 'hook', elbow: [0.3, -1, -0.2] })
        k.look(low)
    }, `Bow onto the ${lowName} leg and hook the ${standName} toes in`)
    f.key(0.9, (k) => {
        k.load(low)
        k.sink(0.2)
    }, `Settle all the weight onto the ${lowName} leg`)
    f.key(3.0, (k) => {
        k.sink(ROOSTER_SINK)
        k.place(stand, { from: low, fwd: 0.16, out: 0.1, pitch: -25, lift: 0.36 })
        k.hand(stand, { at: [0.12, 0.08, 0.32], palm: 'mid', fingers: 'up', shape: 'palm', elbow: [0.1, -1, 0.3] })
        pressByHip(k, low)
        k.look('fwd')
    }, `Golden Rooster: stand on the ${lowName} leg, ${standName} knee and hand rise together`)
    f.hold(1.0, 'Stand tall and still on one leg')
}

// 16. Push Down and Stand on One Leg, left.
export function snakeLeft(f) {
    f.key(2.4, (k) => {
        k.sink(0.12)
        k.place('L', { from: 'R', fwd: 0.1, out: 0.22, turn: -30, pitch: -20, lift: 0.3 })
        k.chest(-80)
        k.hips(-60)
        hook(k, 'R')
        k.hand('L', { at: [-0.12, -0.02, 0.24], palm: 'back+out', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.look('R')
    }, 'Draw the left leg back bent; turn right and form the right hook')
    snakeAndRooster(f, 'L', -1)
}

// 17. Push Down and Stand on One Leg, right.
export function snakeRight(f) {
    f.key(2.2, (k) => {
        k.sink(0.1)
        k.place('R', { from: 'L', fwd: 0.3, out: 0.25, pitch: -15 })
        k.pitch('L', -6)
        k.hand('R', { at: [0.2, -0.1, 0.3], palm: 'mid+down', fingers: 'fwd+up', shape: 'palm', elbow: [0.3, -1, -0.2] })
        k.hand('L', { at: [0.2, -0.45, 0.16], palm: 'down', fingers: 'fwd', shape: 'palm', elbow: [0.5, -1, -0.4] })
    }, 'Set the right foot down ahead of the left, on its ball')
    f.key(2.2, (k) => {
        k.pivot('L', 80, 'ball')
        k.chest(80)
        k.hips(60)
        hook(k, 'L')
        k.hand('R', { at: [-0.12, -0.02, 0.24], palm: 'back+out', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, -0.2] })
        k.look('L')
    }, 'Turn on the left ball to the left and form the left hook')
    snakeAndRooster(f, 'R', 1)
}

export const MOVES = [
    { id: 'snake-left', number: 16, lesson: 6, title: 'Push Down and Stand on One Leg, Left', build: snakeLeft, endFacing: 270 },
    { id: 'snake-right', number: 17, lesson: 6, title: 'Push Down and Stand on One Leg, Right', build: snakeRight, endFacing: 270 },
]

// Lesson 5 played from Single Whip ends where this lesson begins.
export function startPose() {
    const form = new Form(singleWhipPose())
    for (const move of LESSON_5) {
        move.build(form)
    }
    return form.pose
}
