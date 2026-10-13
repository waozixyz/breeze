// Poses where one lesson hands over to the next. A lesson that ends here
// should finish in this pose (positions may differ; stance, facing, weight
// and hands should match), and the next lesson's standalone preview starts
// from it.

import { Form } from '../src/form.js'
import { standingPose } from '../src/pose.js'
import { SINK, STEP, TRACK, pressByHip } from './hands.js'

// Built with the same choreography calls as the form, from standing.
function build(edit) {
    const form = new Form(standingPose())
    form.key(1, edit)
    return form.pose
}

// End of Single Whip (lessons 4 → 5): left bow stance facing 90, left palm
// pushing forward, right hand a hook out to the right.
export function singleWhipPose() {
    return build((k) => {
        k.turn(90)
        k.toes('R', 45, 'ball')
        k.place('L', { from: 'R', fwd: STEP, out: TRACK })
        k.load('L', 0.7)
        k.sink(SINK)
        k.hips(-10)
        k.chest(-15)
        k.hand('L', { at: [0.1, -0.03, 0.48], palm: 'fwd+out', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.hand('R', { at: [0.66, -0.02, 0.2], palm: 'back+mid', fingers: 'down', shape: 'hook', elbow: [0.3, -1, 0] })
        k.look('L')
    })
}

// End of Golden Rooster on the right leg (lessons 6 → 7): facing 270,
// standing on the right leg, left knee lifted, left hand up over the knee,
// right hand pressing by the right hip.
export function goldenRoosterRightPose() {
    return build((k) => {
        k.turn(270)
        k.toes('R', 0, 'ball')
        k.load('R')
        k.sink(0.06)
        k.place('L', { from: 'R', fwd: 0.16, out: 0.1, pitch: -25, lift: 0.36 })
        k.hand('L', { at: [0.12, 0.08, 0.32], palm: 'mid', fingers: 'up', shape: 'palm', elbow: [0.1, -1, 0.3] })
        pressByHip(k, 'R')
        k.look('fwd')
    })
}

// End of Fan Through the Back (lessons 7 → 8): left bow stance facing 270,
// right hand held above the right temple palm out, left palm pushing.
export function fanThroughBackPose() {
    return build((k) => {
        k.turn(270)
        k.toes('R', 45, 'ball')
        k.place('L', { from: 'R', fwd: STEP, out: TRACK })
        k.load('L', 0.7)
        k.sink(SINK)
        k.waist(-10)
        k.hand('R', { at: [0.2, 0.18, 0.18], palm: 'out+up', fingers: 'mid+fwd', shape: 'palm', elbow: [0.8, -1, 0] })
        k.hand('L', { at: [0.06, -0.02, 0.5], palm: 'fwd', fingers: 'up', shape: 'palm', elbow: [0.4, -1, 0] })
        k.look('fwd')
    })
}
