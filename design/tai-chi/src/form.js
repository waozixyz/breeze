// Choreography builder.
//
// A Form keeps the current pose and appends keys. Each key edits a draft of
// the previous pose, so a movement is written as a sequence of changes:
// shift the weight, place a foot, turn the waist, move the hands. Distances
// are metres for the reference 1.70 m figure; angles are degrees.
//
// Everything is written relative to sides and to the facing direction, so
// the same movement code runs mirrored: with `mirrored` set, left and right
// swap and every turn changes direction.

import { REFERENCE_FOOT, SHAPES, clonePose, groundPoint, standingPose } from './pose.js'
import { directionVector } from './solve.js'
import { Timeline, footMotion } from './timeline.js'

const DEG = Math.PI / 180
const PIVOT_SHARE = 0.35
// How low the figure sits while it steps between the two sides of a
// follow-along.
const RESET_SINK = 0.06

function other(side) {
    return side === 'L' ? 'R' : 'L'
}

function sideSign(side) {
    return side === 'L' ? 1 : -1
}

function lerp(a, b, u) {
    return a + (b - a) * u
}

function lerpArray(a, b, u) {
    return a.map((value, index) => lerp(value, b[index], u))
}

class Draft {
    constructor(form, pose) {
        this.form = form
        this.pose = pose
    }

    side(side) {
        if (side !== 'L' && side !== 'R') {
            throw new Error(`Unknown side "${side}"`)
        }
        return this.form.mirrored ? other(side) : side
    }

    angle(degrees) {
        return (this.form.mirrored ? -degrees : degrees) * DEG
    }

    forward() {
        return { x: Math.sin(this.pose.facing), z: Math.cos(this.pose.facing) }
    }

    left() {
        return { x: Math.cos(this.pose.facing), z: -Math.sin(this.pose.facing) }
    }

    // Weight: load('L') puts it all on the left, load('L', 0.7) seventy
    // percent, load(0.5) or load('both') centres it.
    load(side, share = 1) {
        if (side === 'both' || typeof side === 'number') {
            const centred = typeof side === 'number' ? side : 0.5
            this.pose.load = this.form.mirrored ? 1 - centred : centred
            return this
        }
        const actual = this.side(side)
        this.pose.load = actual === 'L' ? share : 1 - share
        return this
    }

    // Places a foot relative to a foot: `from` is 'self', 'other' (default)
    // or a side name ('L', 'R', swapped when mirrored); `fwd` along the
    // facing direction, `out` toward this foot's side, `turn` toes outward
    // from the facing direction.
    place(side, { from = 'other', fwd = 0, out = 0, turn = 0, pitch = 0, lift = 0 } = {}) {
        const actual = this.side(side)
        let reference = other(actual)
        if (from === 'self') {
            reference = actual
        } else if (from === 'L' || from === 'R') {
            reference = this.side(from)
        } else if (from !== 'other') {
            throw new Error(`Unknown foot reference "${from}"`)
        }
        const base = this.pose.feet[reference]
        const forward = this.forward()
        const left = this.left()
        const outward = sideSign(actual)
        this.pose.feet[actual] = {
            x: base.x + forward.x * fwd + left.x * out * outward,
            z: base.z + forward.z * fwd + left.z * out * outward,
            yaw: this.pose.facing + outward * turn * DEG,
            pitch: pitch * DEG,
            lift,
        }
        return this
    }

    // Turns a planted foot about its heel or ball; positive turns the toes out.
    pivot(side, degrees, on = 'heel') {
        const actual = this.side(side)
        const foot = this.pose.feet[actual]
        const point = groundPoint(foot, on)
        const offset = on === 'heel' ? REFERENCE_FOOT.heelBack : -REFERENCE_FOOT.ball
        foot.yaw += sideSign(actual) * degrees * DEG
        foot.x = point.x + Math.sin(foot.yaw) * offset
        foot.z = point.z + Math.cos(foot.yaw) * offset
        return this
    }

    // Toes outward from the facing direction, about the heel.
    toes(side, degrees, on = 'heel') {
        const actual = this.side(side)
        const foot = this.pose.feet[actual]
        const target = this.pose.facing + sideSign(actual) * degrees * DEG
        return this.pivot(side, (target - foot.yaw) / DEG * sideSign(actual), on)
    }

    // Foot pitch in degrees: positive raises the toes, negative the heel.
    pitch(side, degrees) {
        this.pose.feet[this.side(side)].pitch = degrees * DEG
        return this
    }

    lift(side, height, pitch = 0) {
        const foot = this.pose.feet[this.side(side)]
        foot.lift = height
        foot.pitch = pitch * DEG
        return this
    }

    // Moves a lifted foot relative to where it is, in the facing frame.
    reach(side, { fwd = 0, out = 0, up = null, pitch = null, turn = null } = {}) {
        const actual = this.side(side)
        const foot = this.pose.feet[actual]
        const forward = this.forward()
        const left = this.left()
        foot.x += forward.x * fwd + left.x * out * sideSign(actual)
        foot.z += forward.z * fwd + left.z * out * sideSign(actual)
        if (up !== null) {
            foot.lift = up
        }
        if (pitch !== null) {
            foot.pitch = pitch * DEG
        }
        if (turn !== null) {
            foot.yaw = this.pose.facing + sideSign(actual) * turn * DEG
        }
        return this
    }

    ground(side) {
        const foot = this.pose.feet[this.side(side)]
        foot.lift = 0
        foot.pitch = 0
        return this
    }

    // Turns the facing direction (positive is to the left).
    turn(degrees) {
        this.pose.facing += this.angle(degrees)
        return this
    }

    hips(degrees) {
        this.pose.hips = this.angle(degrees)
        return this
    }

    chest(degrees) {
        this.pose.chest = this.angle(degrees)
        return this
    }

    // The waist turn: the chest turns fully, the hips a little over half.
    waist(degrees) {
        this.pose.chest = this.angle(degrees)
        this.pose.hips = this.angle(degrees * 0.6)
        return this
    }

    sink(metres) {
        this.pose.sink = metres
        return this
    }

    lean(degrees) {
        this.pose.lean = degrees * DEG
        return this
    }

    bend(degrees) {
        this.pose.bend = this.angle(degrees)
        return this
    }

    shift(fwd, side = 0) {
        this.pose.shift = [fwd, this.form.mirrored ? -side : side]
        return this
    }

    // A hand in side-relative chest axes: `at` is [out, up, fwd] in metres
    // from the point between the shoulders; palm, fingers and elbow are
    // directions such as 'down', 'fwd+mid' or [out, up, fwd].
    hand(side, spec) {
        const hand = this.pose.hands[this.side(side)]
        if (spec.at) {
            hand.at = [...spec.at]
        }
        if (spec.palm) {
            hand.palm = [...directionVector(spec.palm)]
        }
        if (spec.fingers) {
            hand.fingers = [...directionVector(spec.fingers)]
        }
        if (spec.elbow) {
            hand.elbow = [...directionVector(spec.elbow)]
        }
        if (spec.shape) {
            hand.shape = Array.isArray(spec.shape) ? [...spec.shape] : [...SHAPES[spec.shape]]
        }
        return this
    }

    hands(spec) {
        this.hand('L', spec)
        this.hand('R', spec)
        return this
    }

    // Gaze: 'fwd', a hand ('L' or 'R'), or { hand, yaw, pitch } / { yaw, pitch }.
    look(spec) {
        if (spec === 'L' || spec === 'R') {
            this.pose.look = this.side(spec)
            return this
        }
        if (spec && typeof spec === 'object') {
            const look = { ...spec }
            if (look.hand) {
                look.hand = this.side(look.hand)
            }
            if (look.yaw) {
                look.yaw = this.form.mirrored ? -look.yaw : look.yaw
            }
            this.pose.look = look
            return this
        }
        this.pose.look = 'fwd'
        return this
    }

    // Marks a deliberately deep posture (Snake Creeps Down), which the
    // checks allow to bend the knee further.
    deep(flag = true) {
        this.pose.deep = flag
        return this
    }

    // Raw access for helpers that copy a whole pose.
    set(pose) {
        this.pose = clonePose(pose)
        return this
    }
}

export class Form {
    constructor(start = standingPose(), { mirrored = false, time = 0 } = {}) {
        this.pose = clonePose(start)
        this.t = time
        this.mirrored = mirrored
        this.keys = [{ t: time, pose: clonePose(start), cue: null, move: null }]
        this.moves = []
        this.currentMove = null
    }

    // Appends a key `duration` seconds after the last one. `edit` changes a
    // draft of the current pose; `cue` describes what happens on the way.
    key(duration, edit, cue = null) {
        if (!(duration > 0)) {
            throw new Error(`Key duration must be positive, got ${duration}`)
        }
        const draft = new Draft(this, clonePose(this.pose))
        if (edit) {
            edit(draft)
        }
        const next = draft.pose
        const lead = this.weightLeadsStep(this.pose, next, duration) ?? this.pivotWaitsForWeight(this.pose, next, duration)
        if (lead) {
            this.t += lead.duration
            this.keys.push({ t: this.t, pose: lead.pose, cue: null, move: this.currentMove?.id ?? null })
            duration -= lead.duration
        }
        this.pose = next
        this.t += duration
        this.keys.push({ t: this.t, pose: clonePose(this.pose), cue, move: this.currentMove?.id ?? null })
        return this
    }

    // A loaded foot cannot turn on its ball or heel. When a key turns a foot
    // while the weight moves off it, the turn waits until most of the
    // weight has gone.
    pivotWaitsForWeight(from, to, duration) {
        for (const side of ['L', 'R']) {
            const motion = footMotion(from.feet[side], to.feet[side])
            if (motion !== 'heel' && motion !== 'ball') {
                continue
            }
            const shareStart = side === 'L' ? from.load : 1 - from.load
            const shareEnd = side === 'L' ? to.load : 1 - to.load
            if (shareStart <= PIVOT_SHARE || shareEnd >= shareStart) {
                continue
            }
            const part = Math.min(0.7, Math.max(0.15, (shareStart - PIVOT_SHARE) / (shareStart - shareEnd)))
            const pose = new Timeline([{ t: 0, pose: from }, { t: 1, pose: to }]).sample(part).pose
            pose.look = to.look
            pose.feet[side] = { ...from.feet[side] }
            pose.load = side === 'L' ? PIVOT_SHARE : 1 - PIVOT_SHARE
            return { pose, duration: duration * part }
        }
        return null
    }

    // A foot that steps from the floor must first be free of weight. When a
    // key moves a foot that still carries weight, the weight finishes
    // moving off it during the first part of the key.
    weightLeadsStep(from, to, duration) {
        for (const side of ['L', 'R']) {
            const a = from.feet[side]
            const b = to.feet[side]
            const steps = a.lift < 1e-4 && b.lift < 1e-4 && footMotion(a, b) === 'step'
            const share = side === 'L' ? from.load : 1 - from.load
            if (!steps || share < 0.02) {
                continue
            }
            const share0 = Math.min(1, share / 0.3)
            const part = 0.2 + 0.2 * share0
            const pose = new Timeline([{ t: 0, pose: from }, { t: 1, pose: to }]).sample(part).pose
            pose.look = to.look
            pose.feet[side] = { ...a }
            pose.load = side === 'L' ? 0 : 1
            return { pose, duration: duration * part }
        }
        return null
    }

    hold(duration, cue = null) {
        return this.key(duration, null, cue)
    }

    // Records a named movement made of the keys `body` adds.
    move(id, title, body, info = {}) {
        const startIndex = this.keys.length - 1
        const startPose = clonePose(this.pose)
        const start = this.t
        this.currentMove = { id, title }
        body(this)
        this.moves.push({
            id,
            title,
            ...info,
            startIndex,
            endIndex: this.keys.length - 1,
            start,
            end: this.t,
            startPose,
            endPose: clonePose(this.pose),
        })
        this.currentMove = null
        return this
    }

    // Steps into `target` from wherever the figure is, one foot at a time
    // with the weight on the other, while the body and hands travel to
    // their new place. A foot in the air lands first; a foot that ends in
    // the air lifts last, so the weight is always on a foot on the floor.
    resetTo(target, cue = 'Settle into the starting position') {
        const start = clonePose(this.pose)
        const lifted = (foot) => foot.lift > 0.001
        const samePlace = (a, b) => Math.hypot(a.x - b.x, a.z - b.z) <= 0.01 &&
            Math.abs(a.yaw - b.yaw) <= 2 * DEG && Math.abs(a.pitch - b.pitch) <= DEG && Math.abs(a.lift - b.lift) <= 0.002
        const share = (side) => (side === 'L' ? start.load : 1 - start.load)
        const current = { L: { ...start.feet.L }, R: { ...start.feet.R } }
        const moves = []
        // A lifted foot lands beside the standing foot, about hip width
        // apart, facing the way the figure faces.
        for (const side of ['L', 'R']) {
            if (lifted(current[side])) {
                const standing = current[other(side)]
                const outward = side === 'L' ? 1 : -1
                const landing = {
                    x: standing.x + Math.cos(start.facing) * 0.2 * outward,
                    z: standing.z - Math.sin(start.facing) * 0.2 * outward,
                    yaw: start.facing,
                    pitch: 0,
                    lift: 0,
                }
                moves.push({ side, to: landing, landing: true })
                current[side] = landing
            }
        }
        for (const side of ['L', 'R'].sort((a, b) => share(a) - share(b))) {
            const goal = target.feet[side]
            if (!lifted(goal) && !samePlace(current[side], goal)) {
                moves.push({ side, to: { ...goal } })
                current[side] = { ...goal }
            }
        }
        for (const side of ['L', 'R']) {
            const goal = target.feet[side]
            if (lifted(goal) && !samePlace(current[side], goal)) {
                moves.push({ side, to: { ...goal }, rising: true })
                current[side] = { ...goal }
            }
        }
        const stages = moves.reduce((total, move) => total + (move.landing || move.rising ? 2 : 3), 0) + 1
        let stage = 0
        const blend = (pose) => {
            stage += 1
            const u = stage / stages
            for (const side of ['L', 'R']) {
                const from = start.hands[side]
                const to = target.hands[side]
                pose.hands[side] = {
                    at: lerpArray(from.at, to.at, u),
                    palm: lerpArray(from.palm, to.palm, u),
                    fingers: lerpArray(from.fingers, to.fingers, u),
                    elbow: lerpArray(from.elbow, to.elbow, u),
                    shape: lerpArray(from.shape, to.shape, u),
                }
            }
            pose.facing = lerp(start.facing, target.facing, u)
            pose.hips = lerp(start.hips, target.hips, u)
            pose.chest = lerp(start.chest, target.chest, u)
            pose.lean = lerp(start.lean, target.lean, u)
            pose.bend = lerp(start.bend, target.bend, u)
            // Stand a little taller while stepping into place, so a
            // knee never drives past its toes on a long stance.
            const sink = lerp(start.sink, target.sink, u)
            pose.sink = sink + (Math.min(sink, RESET_SINK) - sink) * Math.sin(Math.PI * u)
            pose.shift = lerpArray(start.shift, target.shift, u)
            pose.deep = Boolean(start.deep || target.deep)
            pose.look = 'fwd'
        }
        const wasMirrored = this.mirrored
        this.mirrored = false
        let first = true
        for (const move of moves) {
            const { side } = move
            const support = other(side)
            // The weight crosses between the feet at no more than about
            // 0.3 m/s on average, so wide stances take longer to leave.
            const feetApart = Math.hypot(this.pose.feet.L.x - this.pose.feet.R.x, this.pose.feet.L.z - this.pose.feet.R.z)
            const shareMoving = support === 'L' ? 1 - this.pose.load : this.pose.load
            this.key(Math.min(3.2, Math.max(1.1, (feetApart * shareMoving) / 0.3)), (k) => {
                blend(k.pose)
                k.load(support)
            }, first ? cue : null)
            first = false
            if (!move.landing && !move.rising) {
                this.key(0.6, (k) => {
                    blend(k.pose)
                    const foot = k.pose.feet[side]
                    foot.lift = 0.05
                    foot.pitch = -10 * DEG
                })
            }
            const from = this.pose.feet[side]
            const distance = Math.hypot(from.x - move.to.x, from.z - move.to.z)
            this.key(Math.min(3.4, Math.max(1.2, 1.0 + distance * 2.4)), (k) => {
                blend(k.pose)
                k.pose.feet[side] = { ...move.to }
            })
        }
        this.key(1.3, (k) => {
            k.set(target)
        }, first ? cue : null)
        this.mirrored = wasMirrored
        return this
    }
}
