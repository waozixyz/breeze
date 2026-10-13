// Pose descriptions for the reference 1.70 m figure.
//
// A pose holds: facing (the direction the form is heading), the two feet
// (ground point under the ankle, yaw, pitch, lift), the share of weight on
// the left foot, sinking, hip and chest turn relative to facing, lean, side
// bend, a pelvis shift, both hands in side-relative chest axes
// [out, up, fwd] measured from the point between the shoulders, and gaze.
// Angles are radians.

import { makeRig } from './rig.js'

const REFERENCE = makeRig('mannequin')

export const REFERENCE_FOOT = {
    heelBack: REFERENCE.heelBack,
    ball: REFERENCE.ball,
}

// The floor point under the heel, ball or ankle of a foot placement.
export function groundPoint(foot, which) {
    const offset = which === 'heel' ? -REFERENCE.heelBack : which === 'ball' ? REFERENCE.ball : 0
    return { x: foot.x + Math.sin(foot.yaw) * offset, z: foot.z + Math.cos(foot.yaw) * offset }
}

export const SHAPES = {
    palm: [1, 0, 0],
    fist: [0, 1, 0],
    hook: [0, 0, 1],
}

export function hangingHand() {
    return {
        at: [0.2, -0.58, 0.03],
        palm: [-1, 0, 0],
        fingers: [0, -1, 0],
        shape: [1, 0, 0],
        elbow: [0.35, -1, -0.25],
    }
}

export function standingPose() {
    return {
        facing: 0,
        feet: {
            L: { x: 0.05, z: 0, yaw: 0, pitch: 0, lift: 0 },
            R: { x: -0.05, z: 0, yaw: 0, pitch: 0, lift: 0 },
        },
        load: 0.5,
        sink: 0,
        hips: 0,
        chest: 0,
        lean: 0,
        bend: 0,
        shift: [0, 0],
        hands: { L: hangingHand(), R: hangingHand() },
        look: 'fwd',
    }
}

export function clonePose(pose) {
    return structuredClone(pose)
}

function swapSides(record) {
    return { L: record.R, R: record.L }
}

function mirrorLook(look) {
    if (look === 'L' || look === 'R') {
        return look === 'L' ? 'R' : 'L'
    }
    if (look && typeof look === 'object') {
        const mirrored = { ...look }
        if (look.hand) {
            mirrored.hand = look.hand === 'L' ? 'R' : 'L'
        }
        if (look.yaw) {
            mirrored.yaw = -look.yaw
        }
        return mirrored
    }
    return look
}

// The pose reflected across the vertical plane through `pivot` that runs
// along `axisYaw`. Left and right swap.
export function mirrorPose(pose, pivot, axisYaw) {
    const forward = { x: Math.sin(axisYaw), z: Math.cos(axisYaw) }
    const reflectPoint = (point) => {
        const dx = point.x - pivot.x
        const dz = point.z - pivot.z
        const along = dx * forward.x + dz * forward.z
        const acrossX = dx - along * forward.x
        const acrossZ = dz - along * forward.z
        return { x: pivot.x + along * forward.x - acrossX, z: pivot.z + along * forward.z - acrossZ }
    }
    const reflectFoot = (foot) => {
        const point = reflectPoint(foot)
        return { ...foot, x: point.x, z: point.z, yaw: 2 * axisYaw - foot.yaw }
    }
    const mirrored = clonePose(pose)
    mirrored.facing = 2 * axisYaw - pose.facing
    mirrored.feet = swapSides({ L: reflectFoot(pose.feet.L), R: reflectFoot(pose.feet.R) })
    mirrored.load = 1 - pose.load
    mirrored.hips = -pose.hips
    mirrored.chest = -pose.chest
    mirrored.bend = -pose.bend
    mirrored.shift = [pose.shift[0], -pose.shift[1]]
    mirrored.hands = swapSides(clonePose(pose.hands))
    mirrored.look = mirrorLook(pose.look)
    return mirrored
}

// The pose moved by (dx, dz) on the floor.
export function translatePose(pose, dx, dz) {
    const moved = clonePose(pose)
    for (const side of ['L', 'R']) {
        moved.feet[side].x += dx
        moved.feet[side].z += dz
    }
    return moved
}

// The pose turned by `angle` (radians, positive to the left) about `pivot`
// on the floor.
export function rotatePose(pose, pivot, angle) {
    const turned = clonePose(pose)
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    for (const side of ['L', 'R']) {
        const foot = turned.feet[side]
        const dx = foot.x - pivot.x
        const dz = foot.z - pivot.z
        foot.x = pivot.x + dx * cos + dz * sin
        foot.z = pivot.z - dx * sin + dz * cos
        foot.yaw += angle
    }
    turned.facing += angle
    return turned
}

export function stanceCenter(pose) {
    return {
        x: (pose.feet.L.x + pose.feet.R.x) / 2,
        z: (pose.feet.L.z + pose.feet.R.z) / 2,
    }
}
