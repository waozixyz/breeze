// Lesson 8: Turn, Deflect, Parry and Punch, Apparent Close Up, Cross Hands,
// Closing Form. The lesson starts in the left bow stance of Fan Through the
// Back, facing 270, turns right to face 90 for the punch and the push, and
// turns right again to finish facing the starting direction (0).
//
// A foot that carries weight never pivots straight from flat: its toes
// rise in one key, it turns in the next, and it lowers after, so the weight
// moves onto the heel gradually.

import { fanThroughBackPose } from './boundaries.js'
import { SINK, STEP, handsDown, pressByHip } from './hands.js'

// 21. Turn, Deflect, Parry and Punch.
export function deflectParryPunch(f) {
    f.key(2.2, (k) => {
        k.load('R', 0.85)
        k.pitch('L', 20)
        k.waist(-30)
        k.hand('R', { at: [0.42, 0.04, 0.26], palm: 'fwd+out', fingers: 'up+out', shape: 'palm', elbow: [0.7, -1, 0] })
        k.hand('L', { at: [0.14, 0.12, 0.36], palm: 'fwd+up', fingers: 'up+mid', shape: 'palm', elbow: [0.5, -1, 0] })
        k.look('R')
    }, 'Sit back onto the right leg and raise the left toes')
    f.key(1.8, (k) => {
        k.turn(-120)
        k.pivot('L', -135, 'heel')
        k.waist(0)
        k.hand('R', { at: [0.3, -0.32, 0.26], palm: 'back+down', fingers: 'fwd+down', shape: 'fist', elbow: [0.5, -1, -0.3] })
        k.hand('L', { at: [0.12, 0.18, 0.3], palm: 'up+fwd', fingers: 'mid+fwd', shape: 'palm', elbow: [0.6, -1, 0] })
        k.look('fwd')
    }, 'Turn the left toes in and turn right; the right hand sinks into a fist')
    f.key(2.0, (k) => {
        k.turn(-60)
        k.ground('L')
        k.load('L', 0.9)
        k.waist(10)
        k.hand('R', { at: [-0.06, -0.36, 0.24], palm: 'down', fingers: 'mid+fwd', shape: 'fist', elbow: [0.6, -1, -0.2] })
        k.hand('L', { at: [0.1, 0.18, 0.3], palm: 'up+fwd', fingers: 'mid', shape: 'palm', elbow: [0.6, -1, 0] })
    }, 'Shift onto the left leg; the right fist circles to the left ribs')
    f.key(1.2, (k) => {
        k.load('L')
        k.place('R', { from: 'L', fwd: 0.1, out: 0.12, turn: 30, lift: 0.04, pitch: -10 })
        k.hand('R', { at: [0.0, -0.2, 0.26], palm: 'back+down', fingers: 'up+mid', shape: 'fist', elbow: [0.5, -1, -0.2] })
    }, 'Draw the right foot back without stopping')
    f.key(1.6, (k) => {
        k.place('R', { from: 'L', fwd: 0.4, out: 0.12, turn: 45, pitch: 15 })
        k.waist(-20)
        k.hand('R', { at: [0.06, -0.1, 0.42], palm: 'up', fingers: 'fwd', shape: 'fist', elbow: [0.4, -1, -0.2] })
        pressByHip(k, 'L')
        k.look('R')
    }, 'Step it forward, toes out, as the right fist rolls over the top')
    f.key(1.8, (k) => {
        k.ground('R')
        k.load('R')
        k.waist(-30)
        k.hand('R', { at: [0.14, -0.2, 0.36], palm: 'up', fingers: 'fwd+out', shape: 'fist', elbow: [0.4, -1, -0.3] })
        k.hand('L', { at: [0.3, -0.3, 0.2], palm: 'down+mid', fingers: 'fwd+out', shape: 'palm', elbow: [0.5, -1, -0.2] })
    }, 'Shift onto the right leg')
    f.key(1.9, (k) => {
        k.place('L', { from: 'R', fwd: STEP, out: 0.22, pitch: 18 })
        k.waist(0)
        k.hand('L', { at: [0.06, -0.04, 0.44], palm: 'mid+fwd', fingers: 'up+fwd', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [0.18, -0.46, 0.08], palm: 'up', fingers: 'fwd', shape: 'fist', elbow: [0.4, -1, -0.6] })
        k.look('L')
    }, 'Step the left heel forward; the left hand parries, the right fist draws back')
    f.key(2.6, (k) => {
        k.ground('L')
        k.load('L', 0.7)
        k.sink(SINK)
        k.hand('R', { at: [0.02, -0.12, 0.5], palm: 'mid', fingers: 'fwd', shape: 'fist', elbow: [0.3, -1, -0.2] })
        k.hand('L', { at: [-0.02, -0.08, 0.32], palm: 'mid', fingers: 'up', shape: 'palm', elbow: [0.5, -1, 0] })
        k.look('R')
    }, 'Left bow stance: punch with the right fist, the left palm beside the forearm')
}

// 22. Apparent Close Up.
export function apparentClose(f) {
    f.key(1.8, (k) => {
        k.hand('L', { at: [-0.02, -0.2, 0.44], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.5, -1, -0.1] })
        k.hand('R', { at: [0.02, -0.12, 0.46], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, -0.2] })
        k.look('fwd')
    }, 'Thread the left hand forward under the right wrist; open the fist')
    f.key(1.6, (k) => {
        k.hands({ at: [0.15, -0.12, 0.44], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.2] })
    }, 'Turn both palms up and separate them')
    f.key(2.4, (k) => {
        k.load('R', 0.85)
        k.pitch('L', 18)
        k.hands({ at: [0.15, -0.14, 0.26], palm: 'mid+up+back', fingers: 'fwd+up', elbow: [0.5, -1, -0.4] })
    }, 'Sit back, raise the left toes and draw the palms to the chest')
    f.key(1.4, (k) => {
        k.hands({ at: [0.15, -0.36, 0.28], palm: 'down+fwd', fingers: 'fwd', elbow: [0.5, -1, -0.4] })
    }, 'Turn the palms down past the belly')
    f.key(2.6, (k) => {
        k.ground('L')
        k.load('L', 0.7)
        k.hands({ at: [0.15, -0.04, 0.48], palm: 'fwd', fingers: 'up', elbow: [0.4, -1, 0] })
    }, 'Bow stance: push both palms forward at shoulder height')
}

// 23. Cross Hands.
export function crossHands(f) {
    f.key(2.0, (k) => {
        k.load('R', 0.8)
        k.pitch('L', 18)
        k.waist(-30)
        k.hands({ at: [0.24, 0.08, 0.38], palm: 'fwd', fingers: 'up', elbow: [0.5, -1, 0] })
        k.look('R')
    }, 'Sit back onto the right leg and raise the left toes')
    f.key(2.0, (k) => {
        k.turn(-90)
        k.pivot('L', -90, 'heel')
        k.waist(-20)
        k.hands({ at: [0.56, 0.03, 0.22], palm: 'fwd', fingers: 'out+fwd', elbow: [0.4, -1, -0.2] })
    }, 'Turn the left toes in and face the front; the arms sweep open')
    f.key(1.8, (k) => {
        k.ground('L')
        k.load('L', 0.7)
        k.pitch('R', 15)
        k.waist(-10)
    }, 'Ease the weight to the left and raise the right toes')
    f.key(1.2, (k) => {
        k.pivot('R', 65, 'heel')
    }, 'Turn the right toes out')
    f.key(2.0, (k) => {
        k.ground('R')
        k.load('R', 0.7)
        k.waist(-20)
        k.hands({ at: [0.62, 0.02, 0.16], palm: 'fwd', fingers: 'out', elbow: [0.4, -1, -0.2] })
    }, 'Side bow stance to the right: the arms open wide at shoulder height')
    f.key(2.2, (k) => {
        k.load('L', 0.85)
        k.pitch('R', 15)
        k.waist(0)
        k.hands({ at: [0.45, -0.4, 0.26], palm: 'mid+fwd', fingers: 'out+down', elbow: [0.4, -1, -0.2] })
        k.look('fwd')
    }, 'Shift onto the left leg; the arms circle down; raise the right toes')
    f.key(1.4, (k) => {
        k.pivot('R', -20, 'heel')
        k.hands({ at: [0.28, -0.52, 0.26], palm: 'mid+up', fingers: 'down+fwd', elbow: [0.4, -1, -0.3] })
    }, 'Turn the right toes in')
    f.key(2.0, (k) => {
        k.load('L')
        k.place('R', { from: 'L', out: 0.3 })
        k.hands({ at: [0.08, -0.3, 0.34], palm: 'back+up', fingers: 'up+mid+fwd', elbow: [0.5, -1, -0.2] })
    }, 'Draw the right foot in to shoulder width as the hands scoop up')
    f.key(2.4, (k) => {
        k.load(0.5)
        k.sink(0.05)
        k.hand('R', { at: [-0.04, -0.1, 0.36], palm: 'back', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, 0] })
        k.hand('L', { at: [-0.04, -0.12, 0.3], palm: 'back', fingers: 'up+mid', shape: 'palm', elbow: [0.6, -1, 0] })
    }, 'Rise a little and cross the wrists at the chest, right hand outside')
}

// 24. Closing Form.
export function closing(f) {
    f.key(2.0, (k) => {
        k.hands({ at: [0.16, -0.08, 0.4], palm: 'down', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
    }, 'Turn the palms down and separate them to shoulder width')
    f.key(3.2, (k) => {
        k.sink(0.03)
        handsDown(k)
    }, 'Lower the arms slowly to the sides and stand up')
    f.key(1.6, (k) => {
        k.load('R')
    }, 'Settle the weight onto the right foot')
    f.key(1.4, (k) => {
        k.place('L', { from: 'R', out: 0.1 })
    }, 'Bring the left foot in beside the right')
    f.key(1.6, (k) => {
        k.load(0.5)
        k.sink(0)
    }, 'Centre the weight and straighten up')
    f.hold(2.0, 'Stand quietly and breathe naturally')
}

export const MOVES = [
    { id: 'deflect-parry-punch', number: 21, lesson: 8, title: 'Turn, Deflect, Parry and Punch', build: deflectParryPunch, endFacing: 90 },
    { id: 'apparent-close', number: 22, lesson: 8, title: 'Apparent Close Up', build: apparentClose, endFacing: 90 },
    { id: 'cross-hands', number: 23, lesson: 8, title: 'Cross Hands', build: crossHands, endFacing: 0 },
    { id: 'closing', number: 24, lesson: 8, title: 'Closing Form', build: closing, endFacing: 0 },
]

// The lesson starts in the bow stance of Fan Through the Back.
export function startPose() {
    return fanThroughBackPose()
}
