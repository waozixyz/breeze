// Samples a list of keyed poses into a continuous motion.
//
// Body channels use monotone cubic curves, so weight, sinking and turning
// never overshoot and come to rest where the movement reverses. Hands use
// Catmull-Rom curves, so they travel in smooth arcs through their keys.
// Feet that stay on the floor never slide: a foot that keeps its heel, ball
// or ankle point pivots about it exactly, and a foot that moves lifts off.

import { REFERENCE_FOOT, groundPoint } from './pose.js'

const SIDES = ['L', 'R']
const SAME_POINT = 0.002
const PIVOT_RAISE = 12 * Math.PI / 180
const STEP_PEEL = 0.12

function monotoneTangents(times, values) {
    const count = values.length
    const tangents = new Array(count).fill(0)
    for (let index = 1; index < count - 1; index += 1) {
        const before = times[index] - times[index - 1]
        const after = times[index + 1] - times[index]
        const slopeBefore = (values[index] - values[index - 1]) / before
        const slopeAfter = (values[index + 1] - values[index]) / after
        if (slopeBefore * slopeAfter <= 0) {
            continue
        }
        tangents[index] = 3 * (before + after) /
            ((2 * after + before) / slopeBefore + (after + 2 * before) / slopeAfter)
    }
    return tangents
}

function catmullTangents(times, values) {
    const count = values.length
    const tangents = new Array(count).fill(0)
    for (let index = 1; index < count - 1; index += 1) {
        const held = Math.abs(values[index] - values[index - 1]) < 1e-9 ||
            Math.abs(values[index + 1] - values[index]) < 1e-9
        if (held) {
            continue
        }
        tangents[index] = (values[index + 1] - values[index - 1]) / (times[index + 1] - times[index - 1])
    }
    return tangents
}

function hermite(y0, y1, m0, m1, span, u) {
    const u2 = u * u
    const u3 = u2 * u
    return (2 * u3 - 3 * u2 + 1) * y0 + (u3 - 2 * u2 + u) * span * m0 +
        (-2 * u3 + 3 * u2) * y1 + (u3 - u2) * span * m1
}

export function smoothstep(u) {
    return u * u * (3 - 2 * u)
}

// Flat numeric channels of a pose, read and written by name.
const BODY_CHANNELS = [
    ['facing', (p) => p.facing, (p, v) => { p.facing = v }],
    ['load', (p) => p.load, (p, v) => { p.load = v }],
    ['sink', (p) => p.sink, (p, v) => { p.sink = v }],
    ['hips', (p) => p.hips, (p, v) => { p.hips = v }],
    ['chest', (p) => p.chest, (p, v) => { p.chest = v }],
    ['lean', (p) => p.lean, (p, v) => { p.lean = v }],
    ['bend', (p) => p.bend, (p, v) => { p.bend = v }],
    ['shiftF', (p) => p.shift[0], (p, v) => { p.shift[0] = v }],
    ['shiftS', (p) => p.shift[1], (p, v) => { p.shift[1] = v }],
]
for (const side of SIDES) {
    for (const field of ['yaw', 'pitch', 'lift', 'x', 'z']) {
        BODY_CHANNELS.push([`foot${side}.${field}`, (p) => p.feet[side][field], (p, v) => { p.feet[side][field] = v }])
    }
    for (let index = 0; index < 3; index += 1) {
        BODY_CHANNELS.push([`shape${side}${index}`, (p) => p.hands[side].shape[index], (p, v) => { p.hands[side].shape[index] = v }])
    }
}

const HAND_CHANNELS = []
for (const side of SIDES) {
    for (const field of ['at', 'palm', 'fingers', 'elbow']) {
        for (let index = 0; index < 3; index += 1) {
            HAND_CHANNELS.push([`${side}.${field}${index}`,
                (p) => p.hands[side][field][index],
                (p, v) => { p.hands[side][field][index] = v }])
        }
    }
}

function clonePose(pose) {
    return structuredClone(pose)
}

function sameFootPoint(a, b) {
    return Math.hypot(a.x - b.x, a.z - b.z) < SAME_POINT
}

// How a foot gets from one key to the next: 'still', a pivot about its
// 'heel', 'ball' or 'ankle', or a 'step'.
export function footMotion(a, b) {
    if (sameFootPoint(a, b) && Math.abs(a.yaw - b.yaw) < 1e-6) {
        return 'still'
    }
    if (sameFootPoint(groundPoint(a, 'heel'), groundPoint(b, 'heel'))) {
        return 'heel'
    }
    if (sameFootPoint(groundPoint(a, 'ball'), groundPoint(b, 'ball'))) {
        return 'ball'
    }
    if (sameFootPoint(a, b)) {
        return 'ankle'
    }
    return 'step'
}

export class Timeline {
    constructor(keys) {
        if (keys.length < 2) {
            throw new Error('A timeline needs at least two keys')
        }
        this.keys = keys
        this.times = keys.map((key) => key.t)
        this.duration = this.times[this.times.length - 1] - this.times[0]
        this.start = this.times[0]
        const poses = keys.map((key) => key.pose)
        this.body = BODY_CHANNELS.map(([name, read, write]) => {
            const values = poses.map(read)
            return { name, write, values, tangents: monotoneTangents(this.times, values) }
        })
        this.handChannels = HAND_CHANNELS.map(([name, read, write]) => {
            const values = poses.map(read)
            return { name, write, values, tangents: catmullTangents(this.times, values) }
        })
        this.footChannels = SIDES.map((side) => ({
            x: this.body.find((channel) => channel.name === `foot${side}.x`),
            z: this.body.find((channel) => channel.name === `foot${side}.z`),
            yaw: this.body.find((channel) => channel.name === `foot${side}.yaw`),
        }))
        this.footMotions = SIDES.map((side) => poses.slice(1).map((pose, index) => footMotion(poses[index].feet[side], pose.feet[side])))
    }

    segmentAt(time) {
        const times = this.times
        if (time <= times[0]) {
            return { index: 0, u: 0 }
        }
        if (time >= times[times.length - 1]) {
            return { index: times.length - 2, u: 1 }
        }
        let low = 0
        let high = times.length - 1
        while (high - low > 1) {
            const middle = (low + high) >> 1
            if (times[middle] <= time) {
                low = middle
            } else {
                high = middle
            }
        }
        const span = times[low + 1] - times[low]
        return { index: low, u: span > 0 ? (time - times[low]) / span : 1 }
    }

    // The pose at `time` plus the key segment it falls in.
    sample(time) {
        const { index, u } = this.segmentAt(time)
        const from = this.keys[index]
        const to = this.keys[index + 1]
        const span = to.t - from.t
        const pose = clonePose(from.pose)
        for (const channel of this.body) {
            channel.write(pose, hermite(channel.values[index], channel.values[index + 1],
                channel.tangents[index], channel.tangents[index + 1], span, u))
        }
        for (const channel of this.handChannels) {
            channel.write(pose, hermite(channel.values[index], channel.values[index + 1],
                channel.tangents[index], channel.tangents[index + 1], span, u))
        }
        for (let sideIndex = 0; sideIndex < 2; sideIndex += 1) {
            const side = SIDES[sideIndex]
            const motion = this.footMotions[sideIndex][index]
            const a = from.pose.feet[side]
            const b = to.pose.feet[side]
            const foot = pose.feet[side]
            if (motion === 'still' || motion === 'ankle') {
                foot.x = a.x
                foot.z = a.z
            } else if (motion === 'heel' || motion === 'ball') {
                const pivot = groundPoint(a, motion)
                const offset = motion === 'heel' ? REFERENCE_FOOT.heelBack : -REFERENCE_FOOT.ball
                foot.x = pivot.x + Math.sin(foot.yaw) * offset
                foot.z = pivot.z + Math.cos(foot.yaw) * offset
                // A flat foot turning on its heel lifts its toes a little,
                // and one turning on its ball lifts its heel.
                const raise = PIVOT_RAISE * Math.sin(Math.PI * u) ** 2
                if (motion === 'heel') {
                    foot.pitch = Math.max(foot.pitch, raise)
                } else {
                    foot.pitch = Math.min(foot.pitch, -raise)
                }
            } else {
                // A step: a foot leaving the floor peels off before it
                // travels, and a landing foot finishes turning and moving
                // before it touches down.
                const fromFloor = a.lift < 1e-4
                const toFloor = b.lift < 1e-4
                const begin = fromFloor ? STEP_PEEL : 0
                const finish = toFloor ? STEP_PEEL : 0
                let travel = Math.min(1, Math.max(0, (u - begin) / (1 - begin - finish)))
                if (fromFloor && toFloor) {
                    const distance = Math.hypot(a.x - b.x, a.z - b.z)
                    const arc = Math.min(0.05, 0.15 * distance)
                    foot.lift += arc * Math.sin(Math.PI * smoothstep(u))
                    travel = smoothstep(travel)
                }
                const channels = this.footChannels[sideIndex]
                for (const field of ['x', 'z', 'yaw']) {
                    const channel = channels[field]
                    foot[field] = hermite(channel.values[index], channel.values[index + 1],
                        channel.tangents[index], channel.tangents[index + 1], span, travel)
                }
            }
        }
        for (const side of SIDES) {
            const shape = pose.hands[side].shape
            const total = shape.reduce((sum, value) => sum + Math.max(0, value), 0) || 1
            for (let index = 0; index < 3; index += 1) {
                shape[index] = Math.max(0, shape[index]) / total
            }
            pose.feet[side].lift = Math.max(0, pose.feet[side].lift)
        }
        pose.load = Math.min(1, Math.max(0, pose.load))
        pose.look = { from: from.pose.look, to: to.pose.look, u: smoothstep(u) }
        return { pose, index, u, from, to }
    }
}
