// Lesson 5: High Pat on Horse, Kick with Right Heel, Strike the Opponent's
// Ears with Both Fists, Turn and Kick with Left Heel. It starts from Single
// Whip facing 90, kicks to the right-front, strikes facing 60, then turns
// round to the left to kick facing 270.

import { SINK, STEP, TRACK } from './hands.js'
import { singleWhipPose } from './boundaries.js'

// Standing a little taller on one leg for the kicks.
const KICK_SINK = 0.06

// Wrists crossed in front of the chest, `outer` hand on the outside, both
// palms facing the body.
function crossHands(k, outer) {
    const inner = outer === 'L' ? 'R' : 'L'
    k.hand(outer, { at: [-0.03, -0.1, 0.31], palm: 'back+mid', fingers: 'up+mid', shape: 'palm', elbow: [0.7, -1, -0.2] })
    k.hand(inner, { at: [-0.02, -0.13, 0.25], palm: 'back+mid', fingers: 'up+mid', shape: 'palm', elbow: [0.7, -1, -0.2] })
}

// Both arms opened out at shoulder height, elbows soft, palms facing out;
// the `kick` side arm reaches over the kicking leg.
function spreadArms(k, kick) {
    const back = kick === 'L' ? 'R' : 'L'
    k.hand(kick, { at: [0.42, 0.02, 0.36], palm: 'out+fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, -0.2] })
    k.hand(back, { at: [0.56, 0.02, 0.02], palm: 'out', fingers: 'up', shape: 'palm', elbow: [0.3, -1, -0.3] })
}

// Arms circling out and down at the sides, palms turned down and out.
function circleDown(k) {
    k.hands({ at: [0.42, -0.22, 0.3], palm: 'down+out', fingers: 'fwd+out', shape: 'palm', elbow: [0.5, -1, -0.3] })
}

// 12. High Pat on Horse.
export function highPat(f) {
    f.key(2.0, (k) => {
        k.load('L')
        k.sink(0.12)
        k.place('R', { from: 'L', fwd: -0.3, out: 0.15, turn: 45 })
    }, 'Bring the right foot a half step forward')
    f.key(2.2, (k) => {
        k.load('R')
        k.sink(SINK)
        k.pitch('L', -14)
        k.waist(-22)
        k.hand('R', { at: [0.42, 0.02, 0.3], palm: 'up', fingers: 'out+fwd', shape: 'palm', elbow: [0.3, -1, -0.3] })
        k.hand('L', { at: [0.1, -0.06, 0.46], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, 0] })
        k.look({ yaw: 15 })
    }, 'Sit back onto the right leg; open the hook and turn both palms up')
    f.key(3.0, (k) => {
        k.place('L', { from: 'R', fwd: 0.33, out: 0.12, pitch: -18 })
        k.waist(0)
        k.hand('R', { at: [0.03, 0.1, 0.46], palm: 'fwd+down', fingers: 'up+mid+fwd', shape: 'palm', elbow: [0.5, -1, -0.2] })
        k.hand('L', { at: [0.16, -0.5, 0.14], palm: 'up', fingers: 'fwd+mid', shape: 'palm', elbow: [0.5, -1, -0.4] })
        k.look('R')
    }, 'Turn back to the front: the right palm pats forward past the ear, the left draws to the waist')
}

// 13. Kick with Right Heel.
export function rightHeelKick(f) {
    f.key(2.0, (k) => {
        k.hand('L', { at: [0.0, 0.04, 0.42], palm: 'up+mid', fingers: 'fwd+mid', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [0.02, 0.07, 0.47], palm: 'down+fwd', fingers: 'fwd+mid', shape: 'palm', elbow: [0.5, -1, -0.2] })
        k.look('fwd')
    }, 'Reach the left hand forward under the right wrist; the hands cross')
    f.key(2.4, (k) => {
        k.place('L', { from: 'R', fwd: 0.48, out: 0.24, turn: 20, pitch: 18 })
        k.waist(10)
        k.hands({ at: [0.4, 0.0, 0.38], palm: [0.7, -0.5, 0.2], fingers: [0.55, 0.35, 0.75], shape: 'palm', elbow: [0.5, -1, -0.2] })
    }, 'Separate the hands; step the left heel out to the left-front')
    f.key(2.2, (k) => {
        k.ground('L')
        k.load('L', 0.75)
        k.sink(SINK)
        k.waist(0)
        circleDown(k)
    }, 'Shift forward into a left bow stance as the hands circle down')
    f.key(2.4, (k) => {
        k.load('L')
        k.place('R', { from: 'L', fwd: 0.0, out: 0.16, turn: 30, pitch: -24 })
        crossHands(k, 'R')
        k.look({ yaw: -30 })
    }, 'Draw the right foot in, toes touching; cross the wrists at the chest, right hand outside')
    f.key(2.2, (k) => {
        k.sink(KICK_SINK)
        k.place('R', { from: 'L', fwd: 0.16, out: 0.2, turn: 30, pitch: -20, lift: 0.34 })
    }, 'Stand up on the left leg and lift the right knee')
    f.key(3.2, (k) => {
        k.place('R', { from: 'L', fwd: 0.66, out: 0.48, turn: 30, pitch: 22, lift: 0.6 })
        k.chest(-18)
        k.hips(-8)
        spreadArms(k, 'R')
        k.look('R')
    }, 'Open both arms and press the right heel out slowly to the right-front')
    f.hold(1.2, 'Hold the kick: arms level, right arm over the right leg')
}

// 14. Strike the Opponent's Ears with Both Fists.
export function strikeEars(f) {
    f.key(2.4, (k) => {
        k.place('R', { from: 'L', fwd: 0.24, out: 0.24, turn: 30, pitch: -20, lift: 0.34 })
        k.chest(-25)
        k.hips(-15)
        k.lean(8)
        k.hand('R', { at: [0.22, -0.36, 0.38], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.hand('L', { at: [0.0, -0.36, 0.36], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.6, -1, -0.3] })
        k.look('fwd')
    }, 'Draw the right leg back, knee up; both palms turn up and come down beside the knee')
    f.key(2.2, (k) => {
        k.turn(-30)
        k.lean(0)
        k.sink(SINK)
        k.place('R', { from: 'L', fwd: STEP, out: TRACK, pitch: 18 })
        k.waist(0)
        k.hands({ at: [0.28, -0.46, 0.18], palm: 'up+mid', fingers: 'fwd', shape: [0.6, 0.4, 0], elbow: [0.5, -1, -0.4] })
    }, 'Step the right heel down to the right-front; the hands drop to the sides')
    f.key(3.2, (k) => {
        k.ground('R')
        k.load('R', 0.7)
        k.hands({ at: [0.09, 0.12, 0.42], palm: 'out+down', fingers: 'fwd+mid+up', shape: 'fist', elbow: [0.7, -1, -0.1] })
        k.look('fwd')
    }, 'Bow stance: the fists circle up and in to ear height, like pincers')
}

// 15. Turn and Kick with Left Heel. The body turns round to the left to
// face 240; the left heel kicks 30° further left, along 270, where the
// form continues.
export function turnLeftHeelKick(f) {
    f.key(2.2, (k) => {
        k.load('L', 0.8)
        k.pitch('R', 22)
        k.waist(15)
        k.hands({ at: [0.3, 0.06, 0.4], palm: 'fwd', fingers: 'up+out', shape: 'palm', elbow: [0.5, -1, -0.2] })
    }, 'Sit back onto the left leg and raise the right toes; the fists open')
    f.key(2.8, (k) => {
        k.pivot('R', -120, 'heel')
        k.turn(150)
        k.waist(0)
        k.hands({ at: [0.55, 0.0, 0.2], palm: 'fwd+out', fingers: 'up+out', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.look('L')
    }, 'Hook the right toes in and turn to the left; the arms open to the sides')
    f.key(1.4, (k) => {
        k.ground('R')
        k.load('R', 0.6)
        k.waist(-10)
    }, 'Set the right foot down and shift toward it')
    f.key(2.6, (k) => {
        k.turn(30)
        k.load('R')
        k.waist(0)
        k.place('L', { from: 'R', fwd: 0.02, out: 0.2, pitch: -24 })
        crossHands(k, 'L')
        k.look({ yaw: 30 })
    }, 'Weight onto the right leg; draw the left foot in and cross the wrists, left hand outside')
    f.key(2.2, (k) => {
        k.sink(KICK_SINK)
        k.place('L', { from: 'R', fwd: 0.16, out: 0.22, turn: 30, pitch: -20, lift: 0.34 })
    }, 'Stand up on the right leg and lift the left knee')
    f.key(3.2, (k) => {
        k.turn(30)
        k.place('L', { from: 'R', fwd: 0.8, out: 0.2, turn: 0, pitch: 22, lift: 0.6 })
        k.chest(-12)
        k.hips(-22)
        spreadArms(k, 'L')
        k.look('L')
    }, 'Open both arms and press the left heel out slowly to the left-front')
    f.hold(1.2, 'Hold the kick: arms level, left arm over the left leg')
}

export const MOVES = [
    { id: 'high-pat', number: 12, lesson: 5, title: 'High Pat on Horse', build: highPat, endFacing: 90 },
    { id: 'right-heel-kick', number: 13, lesson: 5, title: 'Kick with Right Heel', build: rightHeelKick, endFacing: 90 },
    { id: 'strike-ears', number: 14, lesson: 5, title: 'Strike the Ears with Both Fists', build: strikeEars, endFacing: 60 },
    { id: 'turn-left-heel-kick', number: 15, lesson: 5, title: 'Turn and Kick with Left Heel', build: turnLeftHeelKick, endFacing: 270 },
]

export function startPose() {
    return singleWhipPose()
}
