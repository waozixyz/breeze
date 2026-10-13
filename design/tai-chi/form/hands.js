// Hand shapes and positions that recur through the form.
//
// Positions are [out, up, fwd] metres from the point between the shoulders
// in the chest frame; `out` is toward the hand's own side, so a negative
// value crosses the midline.

export function other(side) {
    return side === 'L' ? 'R' : 'L'
}

// Arms relaxed at the sides.
export function handsDown(k) {
    k.hands({ at: [0.2, -0.58, 0.04], palm: 'mid', fingers: 'down', shape: 'palm', elbow: [0.35, -1, -0.25] })
}

// Holding a ball in front of the `side` chest: that hand on top palm down,
// the other hand underneath palm up.
export function holdBall(k, side, { size = 1, fwd = 0.27 } = {}) {
    const top = side
    const bottom = other(side)
    k.hand(top, { at: [0.1, -0.13, fwd], palm: 'down', fingers: 'mid+fwd', shape: 'palm', elbow: [0.6, -1, -0.2] })
    k.hand(bottom, { at: [-0.06, -0.13 - 0.3 * size, fwd - 0.02], palm: 'up', fingers: 'mid+fwd', shape: 'palm', elbow: [0.4, -1, -0.3] })
}

// A hand pressing down beside the hip, fingers forward.
export function pressByHip(k, side, { fwd = 0.14 } = {}) {
    k.hand(side, { at: [0.22, -0.52, fwd], palm: 'down', fingers: 'fwd', shape: 'palm', elbow: [0.5, -1, -0.4] })
}

// A hand raised in front at eye level, palm obliquely up and in.
export function raiseToEyes(k, side, { out = 0.08, up = 0.1, fwd = 0.42 } = {}) {
    k.hand(side, { at: [out, up, fwd], palm: [-0.55, 0.75, -0.3], fingers: 'fwd+up+out', shape: 'palm', elbow: [0.3, -1, 0] })
}

// A standing palm pushing forward, fingers up.
export function pushPalm(k, side, { out = 0.06, up = -0.04, fwd = 0.5 } = {}) {
    k.hand(side, { at: [out, up, fwd], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
}

// Height and stance sizes for the reference figure. The form stays at one
// height once it has sunk: no bobbing up and down between movements.
export const SINK = 0.14
export const STEP = 0.48
export const TRACK = 0.2
