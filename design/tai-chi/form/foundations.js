// Foundations: posture, warm-ups, standing, stances, stepping and hand shapes.
//
// Every drill starts standing with the feet together and ends standing, so
// it can loop. Drills done on both sides are written for the left and run
// again with the form mirrored.

import { SINK, STEP, TRACK, handsDown, pressByHip, pushPalm } from './hands.js'

// Shoulder width between the feet, measured centre to centre.
const SHOULDER_WIDTH = 0.3

// Hands resting on the hips, fingers forward.
function handsOnHips(k) {
    k.hands({ at: [0.19, -0.5, 0.02], palm: 'mid', fingers: 'fwd+down', shape: 'palm', elbow: [1, -0.4, -0.5] })
}

// Arms relaxed at the sides, a little away from the body.
function armsHanging(k) {
    k.hands({ at: [0.21, -0.57, 0.05], palm: 'mid', fingers: 'down', shape: 'palm', elbow: [0.35, -1, -0.25] })
}

// Both palms side by side in front of the belly.
function palmsAtBelly(k, palm = 'up', { up = -0.42, fwd = 0.2 } = {}) {
    k.hands({ at: [0.12, up, fwd], palm, fingers: 'mid+fwd', shape: 'palm', elbow: [0.6, -1, -0.3] })
}

// Bends the knees a little before the weight moves: straight legs cannot
// shift the weight smoothly.
function softenKnees(f, depth = 0.04) {
    f.key(1.2, (k) => {
        k.sink(depth)
    }, 'Soften the knees')
}

// Steps the left foot out to `width` from feet together, toes first.
function stepOut(f, width = SHOULDER_WIDTH, cue = 'Step out to shoulder width, toes first') {
    softenKnees(f, 0.03)
    f.key(1.3, (k) => {
        k.load('R')
    }, 'Settle the weight onto the right foot')
    f.key(0.9, (k) => {
        k.lift('L', 0.03, -12)
    }, 'Lift the left heel, then the foot')
    f.key(1.1, (k) => {
        k.place('L', { from: 'other', out: width, pitch: -10 })
    }, cue)
    f.key(1.3, (k) => {
        k.ground('L')
        k.load(0.5)
    }, 'Lower the heel and centre the weight')
}

// Brings the left foot back beside the right and stands up.
function stepIn(f, cue = 'Bring the left foot back beside the right') {
    f.key(1.3, (k) => {
        k.load('R')
        armsHanging(k)
        k.look('fwd')
    }, 'Shift the weight onto the right foot')
    f.key(1.2, (k) => {
        k.place('L', { from: 'other', out: 0.1, pitch: -10 })
    }, cue)
    f.key(1.3, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0)
        k.waist(0)
        handsDown(k)
    }, 'Centre the weight and stand tall')
}

// ── 1. Posture and breathing ───────────────────────────────────────────

function standingPosture(f) {
    f.hold(2.0, 'Stand with the feet together, arms relaxed, eyes level')
    stepOut(f)
    f.key(3.0, (k) => {
        k.sink(0.04)
        armsHanging(k)
    }, 'Soften the knees; let the shoulders drop and the arms hang')
    f.hold(3.5, 'Lift the crown of the head, tuck the chin in slightly')
    f.key(3.0, (k) => {
        k.sink(0.05)
    }, 'Relax the lower back; feel the weight sink into the feet')
    f.hold(3.5, 'Breathe naturally through the nose')
    stepIn(f)
}

function breathing(f) {
    stepOut(f)
    f.key(2.5, (k) => {
        k.sink(0.05)
        palmsAtBelly(k, 'up')
    }, 'Bring the hands in front of the belly, palms up')
    for (let round = 0; round < 3; round += 1) {
        f.key(4.0, (k) => {
            k.sink(0.03)
            palmsAtBelly(k, 'up', { up: -0.2, fwd: 0.26 })
        }, 'Breathe in: the palms float up to the chest')
        f.key(1.2, (k) => {
            palmsAtBelly(k, 'down', { up: -0.18, fwd: 0.27 })
        }, 'Turn the palms down')
        f.key(4.0, (k) => {
            k.sink(0.07)
            palmsAtBelly(k, 'down', { up: -0.44, fwd: 0.21 })
        }, 'Breathe out: the palms sink, the knees soften')
        f.key(1.2, (k) => {
            palmsAtBelly(k, 'up', { up: -0.42, fwd: 0.2 })
        }, 'Turn the palms up')
    }
    stepIn(f, 'Lower the arms and bring the left foot back')
}

// ── 2. Warm-up ─────────────────────────────────────────────────────────

function neck(f) {
    stepOut(f)
    f.key(3.0, (k) => {
        k.look({ yaw: 60 })
    }, 'Turn the head slowly to the left')
    f.key(2.5, (k) => {
        k.look('fwd')
    }, 'Back to the centre')
    f.key(3.0, (k) => {
        k.look({ yaw: -60 })
    }, 'Turn the head slowly to the right')
    f.key(2.5, (k) => {
        k.look('fwd')
    }, 'Back to the centre')
    f.key(3.0, (k) => {
        k.look({ pitch: 35 })
    }, 'Nod the chin gently toward the chest')
    f.key(3.0, (k) => {
        k.look({ pitch: -20 })
    }, 'Lift the gaze gently, without dropping the head back')
    f.key(2.5, (k) => {
        k.look('fwd')
    }, 'Eyes level again')
    stepIn(f)
}

function armCircles(f) {
    stepOut(f)
    const front = { at: [0.18, -0.04, 0.5], palm: 'down', fingers: 'fwd', elbow: [0.3, -1, -0.3] }
    const overhead = { at: [0.15, 0.54, 0.08], palm: 'mid', fingers: 'up', elbow: [0.6, -0.2, -0.4] }
    const side = { at: [0.7, 0.0, 0.05], palm: 'down', fingers: 'out', elbow: [0, -1, -0.4] }
    const low = { at: [0.2, -0.56, 0.08], palm: 'mid', fingers: 'down', elbow: [0.35, -1, -0.25] }
    for (let round = 0; round < 2; round += 1) {
        f.key(2.2, (k) => k.hands(front), round === 0 ? 'Shoulder circles: raise both arms forward' : null)
        f.key(2.0, (k) => k.hands(overhead), round === 0 ? 'Continue up overhead' : null)
        f.key(2.2, (k) => k.hands(side), round === 0 ? 'Open the arms out to the sides' : null)
        f.key(2.0, (k) => k.hands(low), round === 0 ? 'Lower them and let the shoulders roll down' : null)
    }
    for (let round = 0; round < 2; round += 1) {
        f.key(2.2, (k) => k.hands(side), round === 0 ? 'Now the other way: raise the arms out to the sides' : null)
        f.key(2.0, (k) => k.hands(overhead), round === 0 ? 'Up overhead' : null)
        f.key(2.2, (k) => k.hands(front), round === 0 ? 'Down in front' : null)
        f.key(2.0, (k) => k.hands(low), round === 0 ? 'Relax the arms down' : null)
    }
    stepIn(f)
}

// One loose waist turn toward `side`: the arms swing round with the body.
function swing(k, side) {
    const sign = side === 'L' ? 1 : -1
    const other = side === 'L' ? 'R' : 'L'
    k.chest(55 * sign)
    k.hips(25 * sign)
    k.load(side, 0.6)
    k.hand(other, { at: [-0.1, -0.16, 0.3], palm: 'back', fingers: 'mid', shape: 'palm', elbow: [0.6, -1, 0] })
    k.hand(side, { at: [0.22, -0.5, -0.12], palm: 'mid+fwd', fingers: 'down+back', shape: 'palm', elbow: [0.5, -1, -0.5] })
    k.look({ yaw: 25 * sign })
}

// Passing through the centre between two swings, arms hanging wide.
function swingThrough(k) {
    k.waist(0)
    k.load(0.5)
    k.hands({ at: [0.25, -0.52, 0.06], palm: 'mid', fingers: 'down', shape: 'palm', elbow: [0.35, -1, -0.25] })
    k.look('fwd')
}

function waistTurns(f) {
    stepOut(f, 0.4, 'Step out a little wider than the shoulders')
    f.key(2.0, (k) => {
        k.sink(0.06)
    }, 'Soften the knees; keep the knees still as the waist turns')
    for (let round = 0; round < 3; round += 1) {
        f.key(2.0, (k) => swing(k, 'L'), round === 0 ? 'Turn the waist left; the arms swing loosely with it' : null)
        f.key(1.3, swingThrough, round === 0 ? 'Through the centre, arms hanging' : null)
        f.key(2.0, (k) => swing(k, 'R'), round === 0 ? 'Turn the waist right; the arms follow' : null)
        f.key(1.3, swingThrough)
    }
    f.key(2.4, (k) => {
        k.waist(0)
        k.load(0.5)
        armsHanging(k)
        k.look('fwd')
    }, 'Come back to the centre')
    f.key(1.3, (k) => {
        k.load('R')
        k.sink(0.03)
    }, 'Shift the weight onto the right foot')
    f.key(1.3, (k) => {
        k.place('L', { from: 'other', out: 0.1, pitch: -10 })
    }, 'Bring the left foot back beside the right')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre the weight and stand tall')
}

function kneeCircles(f) {
    softenKnees(f, 0.03)
    f.key(1.3, (k) => {
        k.load('R')
    }, 'Settle onto the right foot')
    f.key(1.2, (k) => {
        k.place('L', { from: 'other', out: 0.2, pitch: -10 })
    }, 'Step out to hip width')
    f.key(1.5, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0.07)
        handsOnHips(k)
    }, 'Hands on the hips, knees soft')
    const ring = [[0.045, 0], [0, 0.045], [-0.03, 0], [0, -0.045]]
    for (let round = 0; round < 3; round += 1) {
        ring.forEach(([fwd, side], index) => {
            f.key(1.1, (k) => {
                k.shift(fwd, side)
                k.sink(0.07 + (fwd > 0 ? 0.02 : 0))
            }, round === 0 && index === 0 ? 'Circle the knees: forward, left, back, right' : null)
        })
    }
    for (let round = 0; round < 3; round += 1) {
        [...ring].reverse().forEach(([fwd, side], index) => {
            f.key(1.1, (k) => {
                k.shift(fwd, side)
                k.sink(0.07 + (fwd > 0 ? 0.02 : 0))
            }, round === 0 && index === 0 ? 'And the other way round' : null)
        })
    }
    f.key(1.5, (k) => {
        k.shift(0, 0)
        k.sink(0.02)
        k.load('R')
        armsHanging(k)
    }, 'Settle and shift onto the right foot')
    f.key(1.2, (k) => {
        k.place('L', { from: 'other', out: 0.1, pitch: -10 })
    }, 'Bring the left foot back')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Stand tall')
}

// ── 3. Standing meditation ─────────────────────────────────────────────

function hugTheTree(f) {
    const arms = (k, fwd, up = -0.15) => {
        k.hands({ at: [0.15, up, fwd], palm: 'back+mid', fingers: 'mid', shape: 'palm', elbow: [0.9, -0.55, -0.1] })
    }
    stepOut(f)
    f.key(2.5, (k) => {
        k.sink(0.1)
        palmsAtBelly(k, 'back', { up: -0.4, fwd: 0.22 })
    }, 'Sink a little; bring the hands in front of the belly')
    f.key(3.0, (k) => {
        arms(k, 0.38)
    }, 'Raise the arms into a circle at chest height, as if hugging a tree')
    f.hold(2.0, 'Elbows soft and a little lower than the wrists; shoulders down')
    for (let round = 0; round < 4; round += 1) {
        f.key(4.0, (k) => {
            k.sink(0.09)
            arms(k, 0.41, -0.14)
        }, round === 0 ? 'Breathe in: the circle of the arms swells slightly' : null)
        f.key(4.0, (k) => {
            k.sink(0.11)
            arms(k, 0.37, -0.16)
        }, round === 0 ? 'Breathe out: sink into the legs, let the arms settle' : null)
    }
    f.key(3.0, (k) => {
        palmsAtBelly(k, 'down', { up: -0.42, fwd: 0.2 })
        k.sink(0.06)
    }, 'Lower the hands slowly to the belly')
    stepIn(f)
}

// ── 4. Stances ─────────────────────────────────────────────────────────

function horseStance(f) {
    softenKnees(f, 0.06)
    f.key(1.4, (k) => {
        k.load('R')
        k.sink(0.12)
        handsOnHips(k)
    }, 'Shift onto the right leg and sink a little')
    f.key(0.9, (k) => {
        k.lift('L', 0.04, -12)
    }, 'Lift the left foot')
    f.key(1.6, (k) => {
        k.place('L', { from: 'other', out: 0.46, turn: 8, pitch: -10 })
    }, 'Step wide to the side, toes first')
    f.key(2.2, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0.19)
        k.hands({ at: [0.12, -0.18, 0.36], palm: 'back+mid', fingers: 'mid', shape: 'palm', elbow: [0.9, -0.6, -0.1] })
    }, 'Horse stance: weight even, knees over the toes, back upright')
    f.hold(4.0, 'Hold: knees press gently outward, tailbone drops')
    f.key(2.2, (k) => {
        k.load('R')
        k.sink(0.13)
        handsOnHips(k)
    }, 'Shift onto the right leg')
    f.key(1.6, (k) => {
        k.place('L', { from: 'other', out: 0.1, pitch: -10 })
    }, 'Bring the left foot back')
    f.key(1.5, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Stand tall')
}

// A bow stance with the left foot in front, from feet together and back.
function bowLeft(f) {
    softenKnees(f)
    f.key(1.3, (k) => {
        k.load('L')
        handsOnHips(k)
    }, 'Shift onto the left foot')
    f.key(1.0, (k) => {
        k.toes('R', 45)
    }, 'Turn the right toes out on the heel')
    f.key(1.4, (k) => {
        k.load('R')
        k.sink(SINK)
    }, 'Sit onto the right leg')
    f.key(1.5, (k) => {
        k.place('L', { from: 'other', fwd: STEP, out: TRACK, pitch: 18 })
    }, 'Step the left heel forward, a little to the side')
    f.key(2.2, (k) => {
        k.ground('L')
        k.load('L', 0.7)
        pushPalm(k, 'L', { out: 0.16, up: -0.08, fwd: 0.46 })
        pushPalm(k, 'R', { out: 0.16, up: -0.08, fwd: 0.46 })
    }, 'Bow stance: 70% forward, front knee over the foot, back leg long')
    f.hold(2.5, 'Hips and chest face forward; the back heel stays down')
    f.key(2.2, (k) => {
        k.load('R', 0.7)
        k.hands({ at: [0.15, -0.3, 0.22], palm: 'fwd+down', fingers: 'up+fwd', shape: 'palm', elbow: [0.5, -1, -0.4] })
    }, 'Sit back: 70% on the back leg')
    f.key(2.2, (k) => {
        k.load('L', 0.7)
        pushPalm(k, 'L', { out: 0.16, up: -0.08, fwd: 0.46 })
        pushPalm(k, 'R', { out: 0.16, up: -0.08, fwd: 0.46 })
    }, 'And shift forward again')
    f.key(2.0, (k) => {
        k.load('R')
        k.pitch('L', 15)
        handsOnHips(k)
    }, 'Sit all the way back; the front toes lift')
    f.key(2.0, (k) => {
        k.place('L', { from: 'other', out: 0.15, pitch: -10 })
    }, 'Draw the left foot back beside the right')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load('L')
    }, 'Shift onto the left foot')
    f.key(1.0, (k) => {
        k.toes('R', 0)
    }, 'Turn the right toes back in')
    f.key(1.4, (k) => {
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

// An empty stance with the left foot in front: toes first, then heel.
function emptyLeft(f) {
    softenKnees(f)
    f.key(1.3, (k) => {
        k.load('L')
    }, 'Shift onto the left foot')
    f.key(1.0, (k) => {
        k.toes('R', 45)
    }, 'Turn the right toes out on the heel')
    f.key(1.5, (k) => {
        k.load('R')
        k.sink(0.12)
    }, 'Sit onto the right leg')
    f.key(1.6, (k) => {
        k.place('L', { from: 'other', fwd: 0.3, out: 0.12, pitch: -16 })
        k.hand('L', { at: [0.06, -0.04, 0.42], palm: 'mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [-0.02, -0.24, 0.24], palm: 'mid', fingers: 'up+fwd', shape: 'palm', elbow: [0.4, -1, -0.2] })
        k.look('L')
    }, 'Empty stance: the left toes touch lightly, all the weight stays back')
    f.hold(3.0, 'The front foot carries no weight; it could lift at any moment')
    f.key(1.4, (k) => {
        k.lift('L', 0.03, -8)
    }, 'Lift the front foot')
    f.key(1.4, (k) => {
        k.place('L', { from: 'self', pitch: 18 })
    }, 'Set it down on the heel, toes raised')
    f.hold(3.0, 'Heel empty stance, as in Play the Lute')
    f.key(1.6, (k) => {
        k.place('L', { from: 'other', out: 0.15, pitch: -10 })
        k.look('fwd')
        armsHanging(k)
    }, 'Draw the left foot back')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load('L')
    }, 'Shift onto the left foot')
    f.key(1.0, (k) => {
        k.toes('R', 0)
    }, 'Turn the right toes back in')
    f.key(1.4, (k) => {
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

// Standing on the right leg with the left knee raised.
function singleLegLeft(f) {
    softenKnees(f, 0.05)
    f.key(1.5, (k) => {
        k.load('R')
        k.sink(0.06)
    }, 'Shift all the weight onto the right foot')
    f.key(1.3, (k) => {
        k.place('L', { from: 'other', fwd: 0.08, out: 0.1, pitch: -20, lift: 0.16 })
        k.hand('L', { at: [0.15, -0.34, 0.3], palm: 'mid', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, 0] })
        pressByHip(k, 'R')
    }, 'Raise the left knee; the left hand comes forward')
    f.key(1.5, (k) => {
        k.place('L', { from: 'other', fwd: 0.2, out: 0.1, pitch: -25, lift: 0.42 })
        k.hand('L', { at: [0.12, 0.08, 0.32], palm: 'mid', fingers: 'up', shape: 'palm', elbow: [0.1, -1, 0.3] })
    }, 'Knee at hip height; the left hand rises above it, fingers up')
    f.hold(3.5, 'Standing leg soft, toes of the raised foot relaxed down')
    f.key(1.4, (k) => {
        k.place('L', { from: 'other', fwd: 0.08, out: 0.1, pitch: -18, lift: 0.14 })
        k.hand('L', { at: [0.16, -0.34, 0.28], palm: 'mid', fingers: 'fwd', shape: 'palm', elbow: [0.3, -1, 0] })
    }, 'Lower the knee; the hand comes down in front')
    f.key(1.4, (k) => {
        k.place('L', { from: 'other', fwd: 0.02, out: 0.1, pitch: -12, lift: 0.04 })
        armsHanging(k)
    }, 'Lower the foot slowly')
    f.key(1.2, (k) => {
        k.place('L', { from: 'other', out: 0.1, pitch: -8 })
    }, 'Toes touch down beside the right foot')
    f.key(1.4, (k) => {
        k.ground('L')
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

// Runs `drill` for the left, then mirrored for the right.
function bothSides(drill) {
    return (f) => {
        drill(f)
        f.mirrored = true
        drill(f)
        f.mirrored = false
    }
}

// ── 5. Stepping ────────────────────────────────────────────────────────

// One forward step with `side`, from the ball held on the other foot: heel
// first, shift forward, then turn the toes out and draw the back foot in.
function stepForward(f, side, first) {
    const back = side === 'L' ? 'R' : 'L'
    f.key(1.6, (k) => {
        k.place(side, { from: 'other', fwd: STEP, out: TRACK, pitch: 18 })
    }, first ? 'Step forward, heel first, like a cat: no weight yet' : null)
    f.key(2.0, (k) => {
        k.ground(side)
        k.load(side, 0.7)
    }, first ? 'Roll onto the foot and shift forward into a bow stance' : null)
    f.key(1.2, (k) => {
        k.load(back, 0.75)
        k.pitch(side, 20)
    }, first ? 'Sit back a little and raise the front toes' : null)
    f.key(0.9, (k) => {
        k.pivot(side, 45, 'heel')
    }, first ? 'Turn the front toes out' : null)
    f.key(1.4, (k) => {
        k.ground(side)
        k.load(side, 0.85)
    }, first ? 'Shift forward onto the turned foot' : null)
    f.key(1.7, (k) => {
        k.load(side)
        k.place(back, { from: 'other', out: 0.12, pitch: -22 })
    }, first ? 'Draw the back foot in beside it, toes touching' : null)
}

function forwardStepping(f) {
    softenKnees(f, 0.06)
    f.key(1.5, (k) => {
        k.load('R')
        k.sink(SINK)
        handsOnHips(k)
    }, 'Hands on the hips; sit onto the right leg')
    f.key(1.0, (k) => {
        k.place('L', { from: 'other', out: 0.12, pitch: -22 })
    }, 'Left toes touch beside the right foot')
    stepForward(f, 'L', true)
    stepForward(f, 'R', false)
    stepForward(f, 'L', false)
    stepForward(f, 'R', false)
    f.key(1.4, (k) => {
        k.ground('L')
        k.load('L')
    }, 'Set the left heel down and shift onto it')
    f.key(1.0, (k) => {
        k.toes('R', 0)
    }, 'Turn the right toes back in')
    f.key(1.5, (k) => {
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

// One step backward with `side`: toes touch down behind, the heel lowers
// turning out, the weight sits back and the front foot straightens.
function stepBack(f, side, first) {
    const front = side === 'L' ? 'R' : 'L'
    f.key(1.0, (k) => {
        k.lift(side, 0.05, -10)
    }, first ? 'Lift the foot that carries no weight' : null)
    f.key(1.6, (k) => {
        k.place(side, { from: 'other', fwd: -0.42, out: 0.22, turn: 20, pitch: -20 })
    }, first ? 'Step back and a little to the side, toes first' : null)
    f.key(1.4, (k) => {
        k.pivot(side, 25, 'ball')
        k.pitch(side, 0)
    }, first ? 'Lower the heel as the toes turn out' : null)
    f.key(1.5, (k) => {
        k.load(side)
    }, first ? 'Sit back onto it' : null)
    f.key(1.0, (k) => {
        k.toes(front, 0, 'ball')
        k.pitch(front, -14)
    }, first ? 'The empty front foot straightens on its ball, heel light' : null)
}

function backwardStepping(f) {
    softenKnees(f, 0.06)
    f.key(1.5, (k) => {
        k.load('R')
        k.sink(SINK)
        handsOnHips(k)
    }, 'Hands on the hips; sit onto the right leg')
    stepBack(f, 'L', true)
    stepBack(f, 'R', false)
    stepBack(f, 'L', false)
    stepBack(f, 'R', false)
    f.key(1.4, (k) => {
        k.pitch('L', 0)
        k.place('L', { from: 'other', fwd: 0, out: 0.16, pitch: -10 })
    }, 'Draw the front foot back beside the other')
    f.key(1.3, (k) => {
        k.ground('L')
        k.load('L')
    }, 'Shift onto the left foot')
    f.key(1.0, (k) => {
        k.toes('R', 0)
    }, 'Turn the right toes back in')
    f.key(1.5, (k) => {
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

function sideStepping(f) {
    stepOut(f, SHOULDER_WIDTH)
    f.key(1.5, (k) => {
        k.sink(SINK)
        handsOnHips(k)
    }, 'Hands on the hips; sink into the legs')
    for (let round = 0; round < 3; round += 1) {
        const first = round === 0
        f.key(1.5, (k) => {
            k.load('R')
        }, first ? 'Shift onto the right leg' : null)
        f.key(1.6, (k) => {
            k.place('L', { from: 'other', out: 0.48, pitch: -10 })
        }, first ? 'Step the left foot out to the side, toes first' : null)
        f.key(1.5, (k) => {
            k.ground('L')
            k.load('L')
        }, first ? 'Lower the heel and shift onto the left leg' : null)
        f.key(1.6, (k) => {
            k.place('R', { from: 'other', out: 0.22, pitch: -10 })
        }, first ? 'Bring the right foot in, feet parallel' : null)
        f.key(1.2, (k) => {
            k.ground('R')
            k.load(0.5)
        }, first ? 'Lower the heel; the height stays level' : null)
    }
    f.key(1.5, (k) => {
        k.load('L')
        k.sink(0.04)
    }, 'Shift onto the left leg and rise a little')
    f.key(1.2, (k) => {
        k.place('R', { from: 'other', out: 0.1, pitch: -10 })
    }, 'Bring the right foot beside the left')
    f.key(1.4, (k) => {
        k.ground('R')
        k.load(0.5)
        k.sink(0)
        handsDown(k)
    }, 'Centre and stand tall')
}

// ── 6. Hand shapes ─────────────────────────────────────────────────────

// A hand drawn back to the waist, palm up.
function palmAtWaist(k, side) {
    k.hand(side, { at: [0.17, -0.46, 0.1], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.6] })
}

function fistAtWaist(k, side) {
    k.hand(side, { at: [0.17, -0.45, 0.06], palm: 'up', fingers: 'fwd', shape: 'fist', elbow: [0.3, -1, -0.7] })
}

function palmDrill(f) {
    stepOut(f)
    f.key(2.2, (k) => {
        k.sink(0.08)
        palmAtWaist(k, 'L')
        palmAtWaist(k, 'R')
    }, 'Draw both hands to the waist, palms up')
    f.key(2.2, (k) => {
        k.hands({ at: [0.14, -0.1, 0.34], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, -0.2] })
    }, 'Tai Chi palm: fingers relaxed and slightly apart, wrist settled')
    for (let round = 0; round < 2; round += 1) {
        for (const side of ['R', 'L']) {
            const other = side === 'L' ? 'R' : 'L'
            f.key(2.4, (k) => {
                k.waist(side === 'R' ? 15 : -15)
                k.hand(side, { at: [0.02, -0.06, 0.52], palm: [0, -0.35, 1], fingers: [0, 1, 0.35], shape: 'palm', elbow: [0.4, -1, 0] })
                palmAtWaist(k, other)
                k.look(side)
            }, round === 0 ? `Push the ${side === 'L' ? 'left' : 'right'} palm forward; the other returns to the waist` : null)
        }
    }
    f.key(2.2, (k) => {
        k.waist(0)
        palmAtWaist(k, 'L')
        palmAtWaist(k, 'R')
        k.look('fwd')
    }, 'Both hands back to the waist')
    stepIn(f)
}

function fistDrill(f) {
    stepOut(f)
    f.key(2.2, (k) => {
        k.sink(0.08)
        fistAtWaist(k, 'L')
        fistAtWaist(k, 'R')
    }, 'Close the hands into loose fists at the waist')
    for (let round = 0; round < 2; round += 1) {
        for (const side of ['R', 'L']) {
            const other = side === 'L' ? 'R' : 'L'
            f.key(2.2, (k) => {
                k.waist(side === 'R' ? 12 : -12)
                k.hand(side, { at: [0.03, -0.16, 0.5], palm: 'mid', fingers: 'fwd', shape: 'fist', elbow: [0.3, -1, -0.2] })
                fistAtWaist(k, other)
                k.look('fwd')
            }, round === 0 ? `Punch with the ${side === 'L' ? 'left' : 'right'}: the fist turns upright, never locked straight` : null)
        }
    }
    f.key(2.2, (k) => {
        k.waist(0)
        fistAtWaist(k, 'L')
        fistAtWaist(k, 'R')
    }, 'Both fists back to the waist')
    f.key(1.8, (k) => {
        palmAtWaist(k, 'L')
        palmAtWaist(k, 'R')
    }, 'Open the hands')
    stepIn(f)
}

function hookDrill(f) {
    stepOut(f)
    f.key(2.2, (k) => {
        k.sink(0.08)
        k.hand('R', { at: [0.1, -0.12, 0.36], palm: 'up', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.2] })
        palmAtWaist(k, 'L')
    }, 'Raise the right hand in front, palm up')
    f.key(2.2, (k) => {
        k.hand('R', { at: [0.22, -0.08, 0.4], palm: 'back+mid', fingers: 'down+fwd', shape: 'hook', elbow: [0.4, -1, -0.2] })
    }, 'Gather the fingertips together and let the wrist drop: the hook')
    f.key(2.6, (k) => {
        k.waist(-25)
        k.hand('R', { at: [0.6, 0.0, 0.16], palm: 'back+mid', fingers: 'down', shape: 'hook', elbow: [0, -0.3, -1] })
        k.look('R')
    }, 'Extend the hook out to the right at shoulder height')
    f.key(2.6, (k) => {
        k.waist(10)
        k.hand('L', { at: [0.1, -0.04, 0.46], palm: 'fwd+out', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.look('L')
    }, 'Turn left and push the left palm forward, as in Single Whip')
    f.hold(2.0, 'Hook and palm stretch gently apart; shoulders stay down')
    f.key(2.4, (k) => {
        k.waist(0)
        k.hand('R', { at: [0.2, -0.3, 0.3], palm: 'down', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.hand('L', { at: [0.2, -0.3, 0.3], palm: 'down', fingers: 'fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
        k.look('fwd')
    }, 'Open the hook and bring both hands in front')
    stepIn(f)
}

export const FOUNDATIONS = [
    {
        id: 'posture',
        title: 'Posture and breathing',
        summary: 'How to stand, and how the breath moves with the hands.',
        drills: [
            { id: 'standing-posture', title: 'Standing posture', summary: 'Feet shoulder width, knees soft, crown lifted, arms relaxed.', view: 'front', build: standingPosture },
            { id: 'breathing', title: 'Breathing with the hands', summary: 'Palms rise with the in-breath and sink with the out-breath.', view: 'front', build: breathing },
        ],
    },
    {
        id: 'warm-up',
        title: 'Warm-up',
        summary: 'Gentle loosening of the neck, shoulders, waist and knees.',
        drills: [
            { id: 'neck', title: 'Neck turns and nods', summary: 'Slow head turns and nods, never forced.', view: 'front', build: neck },
            { id: 'arm-circles', title: 'Arm and shoulder circles', summary: 'Large slow arm circles, forward and back.', view: 'threeQuarter', build: armCircles },
            { id: 'waist-turns', title: 'Waist turns', summary: 'The waist turns, the arms swing loosely, the knees stay still.', view: 'front', build: waistTurns },
            { id: 'knee-circles', title: 'Knee circles', summary: 'Hands on the hips, small circles of the knees both ways.', view: 'threeQuarter', build: kneeCircles },
        ],
    },
    {
        id: 'standing-meditation',
        title: 'Standing meditation',
        summary: 'Zhan zhuang: standing still with rounded arms and quiet breath.',
        drills: [
            { id: 'hug-the-tree', title: 'Hug the tree', summary: 'Arms rounded at chest height, knees soft, breathing slowly.', view: 'threeQuarter', build: hugTheTree },
        ],
    },
    {
        id: 'stances',
        title: 'Stances',
        summary: 'The stances every movement of the form is built from.',
        drills: [
            { id: 'horse-stance', title: 'Horse stance', summary: 'Wide stance, weight even, knees over the toes.', view: 'front', build: horseStance },
            { id: 'bow-stance', title: 'Bow stance', summary: '70% on the bent front leg, back leg long; left, then right.', view: 'side', build: bothSides(bowLeft) },
            { id: 'empty-stance', title: 'Empty stance', summary: 'All the weight on the back leg, the front foot light; left, then right.', view: 'side', build: bothSides(emptyLeft) },
            { id: 'single-leg-stance', title: 'Single-leg stance', summary: 'Standing on one leg with the other knee raised; left, then right.', view: 'front', build: bothSides(singleLegLeft) },
        ],
    },
    {
        id: 'stepping',
        title: 'Stepping',
        summary: 'Moving the weight completely before a foot moves.',
        drills: [
            { id: 'forward-stepping', title: 'Forward stepping', summary: 'Cat step: heel first, shift, toes out, draw in.', view: 'side', build: forwardStepping },
            { id: 'backward-stepping', title: 'Backward stepping', summary: 'Toes first behind, heel turns out, sit back, as in Repulse the Monkey.', view: 'side', build: backwardStepping },
            { id: 'side-stepping', title: 'Side stepping', summary: 'Stepping sideways at one height, as in Cloud Hands.', view: 'front', build: sideStepping },
        ],
    },
    {
        id: 'hand-shapes',
        title: 'Hand shapes',
        summary: 'The open palm, the fist and the hook.',
        drills: [
            { id: 'palm', title: 'Open palm', summary: 'Alternating palm pushes with a small waist turn.', view: 'threeQuarter', build: palmDrill },
            { id: 'fist', title: 'Fist', summary: 'A loose fist punching from the waist, turning upright.', view: 'threeQuarter', build: fistDrill },
            { id: 'hook', title: 'Hook', summary: 'Fingertips gathered, wrist dropped, as in Single Whip.', view: 'threeQuarter', build: hookDrill },
        ],
    },
]
