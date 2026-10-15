// Pose solver: turns a pose description into world transforms for every
// body segment.
//
// World axes: +Y up, the figure starts facing +Z, its left is +X. A yaw of
// θ faces (sin θ, 0, cos θ), so a positive yaw turns the figure left.
//
// Segment frames: limbs hang along their local -Y from the proximal joint,
// torso pieces rise along +Y, the head and feet look along +Z, hands point
// their fingers along -Y with the palm facing +Z.

import { Matrix4, Quaternion, Vector3 } from 'three'

const UP = new Vector3(0, 1, 0)
const DEG = Math.PI / 180
const KNEE_GIVE = 0.03
// How far a loaded front knee may pass the toes, in metres.
const KNEE_PAST_TOES = 0.025

export const SIDES = ['L', 'R']

// +1 for the left side (+X), -1 for the right.
export function sideSign(side) {
    return side === 'L' ? 1 : -1
}

export function forwardOf(yaw) {
    return new Vector3(Math.sin(yaw), 0, Math.cos(yaw))
}

export function leftOf(yaw) {
    return new Vector3(Math.cos(yaw), 0, -Math.sin(yaw))
}

function yawQuat(yaw) {
    return new Quaternion().setFromAxisAngle(UP, yaw)
}

// Yaw, then forward lean about the local left axis, then side bend about the
// local forward axis (positive bends toward the left).
function bodyQuat(yaw, lean, bend) {
    const q = yawQuat(yaw)
    q.multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), lean))
    q.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), -bend))
    return q
}

// A frame whose +Y is `yAxis` and whose +Z is as close to `zHint` as possible.
export function frameQuat(yAxis, zHint, fallbackZ) {
    const y = yAxis.clone().normalize()
    let z = zHint.clone().sub(y.clone().multiplyScalar(zHint.dot(y)))
    if (z.lengthSq() < 1e-8 && fallbackZ) {
        z = fallbackZ.clone().sub(y.clone().multiplyScalar(fallbackZ.dot(y)))
    }
    if (z.lengthSq() < 1e-8) {
        z = Math.abs(y.x) < 0.9 ? new Vector3(1, 0, 0) : new Vector3(0, 0, 1)
        z.sub(y.clone().multiplyScalar(z.dot(y)))
    }
    z.normalize()
    const x = new Vector3().crossVectors(y, z).normalize()
    return new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(x, y, z))
}

// Converts a side-relative vector [out, up, fwd] to a frame's local axes.
function chestLocal(side, v) {
    return new Vector3(v[0] * sideSign(side), v[1], v[2])
}

// Two-bone inverse kinematics. Returns the middle joint and the clamped end.
export function solveTwoBone(root, target, upper, lower, pole) {
    const toTarget = target.clone().sub(root)
    let distance = toTarget.length()
    const direction = distance > 1e-6 ? toTarget.clone().divideScalar(distance) : new Vector3(0, -1, 0)
    const reach = upper + lower
    const stretched = distance > reach * 0.9999
    distance = Math.min(Math.max(distance, Math.abs(upper - lower) + 1e-4), reach * 0.9999)
    const cosine = (upper * upper + distance * distance - lower * lower) / (2 * upper * distance)
    const along = upper * cosine
    const across = upper * Math.sqrt(Math.max(0, 1 - cosine * cosine))
    let bend = pole.clone().sub(direction.clone().multiplyScalar(pole.dot(direction)))
    if (bend.lengthSq() < 1e-8) {
        bend = new Vector3(0, 0, 1).sub(direction.clone().multiplyScalar(direction.z))
    }
    bend.normalize()
    const middle = root.clone().add(direction.clone().multiplyScalar(along)).add(bend.multiplyScalar(across))
    const end = root.clone().add(direction.clone().multiplyScalar(distance))
    return { middle, end, stretched }
}

// Where a foot sits: ankle, frame, and contact points. `foot` holds the flat
// placement (x, z of the ground point under the ankle), yaw, pitch (positive
// raises the toes about the heel, negative raises the heel about the ball)
// and lift (extra ankle height in the air), all for the reference figure.
function raisedHeel(placed, footPose, rig) {
    return Math.abs(placed.ankle.y - placeFoot(footPose, rig).ankle.y) > 1e-4
}

export function placeFoot(foot, rig) {
    const scale = rig.scale
    const yaw = foot.yaw
    const forward = forwardOf(yaw)
    const left = leftOf(yaw)
    const ground = new Vector3(foot.x * scale, 0, foot.z * scale)
    const pitch = foot.pitch ?? 0
    const lift = (foot.lift ?? 0) * scale
    const tilt = new Quaternion().setFromAxisAngle(left, -pitch)
    let contact
    let fromContact
    if (pitch >= 0) {
        contact = ground.clone().addScaledVector(forward, -rig.heelBack)
        fromContact = forward.clone().multiplyScalar(rig.heelBack).addScaledVector(UP, rig.ankleHeight)
    } else {
        contact = ground.clone().addScaledVector(forward, rig.ball)
        fromContact = forward.clone().multiplyScalar(-rig.ball).addScaledVector(UP, rig.ankleHeight)
    }
    const ankle = contact.clone().add(fromContact.applyQuaternion(tilt)).addScaledVector(UP, lift)
    const quat = tilt.clone().multiply(yawQuat(yaw))
    const heel = ankle.clone().add(new Vector3(0, -rig.ankleHeight, -rig.heelBack).applyQuaternion(quat))
    const ball = ankle.clone().add(new Vector3(0, -rig.ankleHeight, rig.ball).applyQuaternion(quat))
    // Toes stay on the floor while the heel is up, and follow the foot once it lifts.
    let toesQuat = quat.clone()
    let toesOrigin = ball.clone()
    if (pitch < 0) {
        const flat = yawQuat(yaw)
        const follow = Math.min(1, lift / (0.04 * scale))
        toesQuat = flat.slerp(quat, follow)
    }
    const toeTip = toesOrigin.clone().add(new Vector3(0, 0, rig.toeTip - rig.ball).applyQuaternion(toesQuat))
    const grounded = lift < 0.002 * scale
    return { ankle, quat, heel, ball, toeTip, toesQuat, toesOrigin, grounded, forward, yaw, pitch }
}

// Named or numeric directions in side-relative chest axes [out, up, fwd].
const NAMED = {
    up: [0, 1, 0],
    down: [0, -1, 0],
    fwd: [0, 0, 1],
    back: [0, 0, -1],
    out: [1, 0, 0],
    mid: [-1, 0, 0],
}

export function directionVector(spec) {
    if (Array.isArray(spec)) {
        return spec
    }
    const sum = [0, 0, 0]
    for (const part of String(spec).split('+')) {
        const named = NAMED[part.trim()]
        if (!named) {
            throw new Error(`Unknown direction "${part}"`)
        }
        sum[0] += named[0]
        sum[1] += named[1]
        sum[2] += named[2]
    }
    const length = Math.hypot(sum[0], sum[1], sum[2]) || 1
    return [sum[0] / length, sum[1] / length, sum[2] / length]
}

// Yaw and pitch of a gaze description, given the solved body so far.
function gazeAngles(look, chestYaw, headBase, palms) {
    if (!look || look === 'fwd') {
        return { yaw: chestYaw, pitch: 0 }
    }
    if (typeof look === 'string') {
        look = { hand: look }
    }
    if (look.hand) {
        const toHand = palms[look.hand].clone().sub(headBase)
        const horizontal = Math.hypot(toHand.x, toHand.z)
        let yaw = Math.atan2(toHand.x, toHand.z)
        while (yaw - chestYaw > Math.PI) yaw -= 2 * Math.PI
        while (yaw - chestYaw < -Math.PI) yaw += 2 * Math.PI
        // Eyes follow the hand; the head turns most of the way and does not
        // drop all the way to a low hand.
        const relative = Math.max(-65 * DEG, Math.min(65 * DEG, (yaw - chestYaw) * 0.85))
        const pitch = Math.atan2(-toHand.y, Math.max(horizontal, 0.05)) * 0.6 + (look.pitch ?? 0) * DEG
        return { yaw: chestYaw + relative + (look.yaw ?? 0) * DEG, pitch: Math.max(-25 * DEG, Math.min(45 * DEG, pitch)) }
    }
    return { yaw: chestYaw + (look.yaw ?? 0) * DEG, pitch: (look.pitch ?? 0) * DEG }
}

// How firmly a foot is on the floor: 1 on the floor, 0 from 3 cm up.
function groundedness(foot) {
    return Math.min(1, Math.max(0, 1 - (foot.lift ?? 0) / 0.03))
}

function hipJoint(side, pelvisXZ, height, pelvisQuat, rig) {
    const offset = new Vector3(sideSign(side) * rig.hipHalfWidth, -rig.hipDrop, 0).applyQuaternion(pelvisQuat)
    return new Vector3(pelvisXZ.x, height, pelvisXZ.z).add(offset)
}

// A lightly loaded foot that cannot reach the floor from the hip rolls up
// onto its ball, as a back foot does when the weight moves forward.
function raiseHeelToReach(side, footPose, share, pelvisXZ, height, pelvisQuat, facing, rig) {
    const room = Math.min(1, Math.max(0, (0.45 - share) / 0.3))
    const pitch = footPose.pitch ?? 0
    if (room <= 0 || pitch > 0.01) {
        return null
    }
    // Small shortfalls are taken up by bending the knees a little lower
    // (reachablePelvisHeight); the heel rises only for the rest, and only
    // on a foot that trails behind the hip.
    const hip = hipJoint(side, pelvisXZ, height - KNEE_GIVE * rig.scale, pelvisQuat, rig)
    const ahead = (footPose.x * rig.scale - hip.x) * Math.sin(facing) + (footPose.z * rig.scale - hip.z) * Math.cos(facing)
    // Fades in as the foot falls behind the hip, so the heel never pops up.
    const trailing = 1 - smoothRamp(ahead, -0.02 * rig.scale, 0.06 * rig.scale)
    if (trailing <= 0) {
        return null
    }
    const legReach = rig.legLength * 0.995
    const reachWith = (extra) => placeFoot({ ...footPose, pitch: pitch - extra }, rig).ankle.distanceTo(hip)
    if (reachWith(0) <= legReach) {
        return null
    }
    const most = 60 * DEG * room * trailing
    if (reachWith(most) > legReach) {
        return placeFoot({ ...footPose, pitch: pitch - most }, rig)
    }
    let low = 0
    let high = most
    for (let step = 0; step < 18; step += 1) {
        const middle = (low + high) / 2
        if (reachWith(middle) > legReach) {
            low = middle
        } else {
            high = middle
        }
    }
    return placeFoot({ ...footPose, pitch: pitch - high }, rig)
}

// The pelvis height that keeps every foot on the floor reachable; a foot
// that is lifting constrains it less the higher it is.
function reachablePelvisHeight(target, pelvisXZ, pelvisQuat, feet, footPoses, rig) {
    let height = target
    const legReach = rig.legLength * 0.995
    for (const side of SIDES) {
        const foot = feet[side]
        const weight = groundedness(footPoses[side])
        if (weight <= 0) {
            continue
        }
        const hipOffset = new Vector3(sideSign(side) * rig.hipHalfWidth, -rig.hipDrop, 0).applyQuaternion(pelvisQuat)
        const dx = pelvisXZ.x + hipOffset.x - foot.ankle.x
        const dz = pelvisXZ.z + hipOffset.z - foot.ankle.z
        const horizontal = Math.hypot(dx, dz)
        const vertical = Math.sqrt(Math.max(legReach * legReach - horizontal * horizontal, 0))
        const allowed = foot.ankle.y + vertical - hipOffset.y
        if (allowed < target) {
            height = Math.min(height, target + (allowed - target) * weight)
        }
    }
    return height
}

function smoothRamp(value, from, to) {
    const u = Math.min(1, Math.max(0, (value - from) / (to - from)))
    return u * u * (3 - 2 * u)
}

// A loaded front knee stays over the foot, not past the toes: where it
// would pass them the pelvis rises just enough to keep it there, as a
// teacher corrects a stance by sinking less. The correction fades in with
// the weight and with how far the foot is in front, so it never jumps.
function kneeSafePelvisHeight(height, pelvisXZ, pelvisQuat, feet, pose, rig) {
    let raise = 0
    const facing = forwardOf(pose.facing)
    for (const side of SIDES) {
        const foot = feet[side]
        const footPose = pose.feet[side]
        const share = side === 'L' ? pose.load : 1 - pose.load
        const otherFoot = feet[side === 'L' ? 'R' : 'L']
        const ahead = foot.heel.clone().sub(otherFoot.heel).dot(facing)
        const weight = smoothRamp(share, 0.4, 0.6) * smoothRamp(ahead, 0.18 * rig.scale, 0.28 * rig.scale) *
            (1 - smoothRamp(footPose.lift ?? 0, 0.0015, 0.02))
        if (weight <= 0) {
            continue
        }
        const toward = foot.toeTip.clone().sub(foot.heel).setY(0)
        if (toward.lengthSq() < 1e-8) {
            continue
        }
        toward.normalize()
        const sign = sideSign(side)
        const footSide = leftOf(foot.yaw).multiplyScalar(sign)
        const pole = foot.forward.clone().add(footSide.multiplyScalar(0.1)).add(new Vector3(0, 0.05, 0))
        const pastToes = (lift) => {
            const hip = hipJoint(side, pelvisXZ, height + lift, pelvisQuat, rig)
            const knee = solveTwoBone(hip, foot.ankle, rig.thigh, rig.shin, pole).middle
            return knee.clone().sub(foot.ankle).setY(0).dot(toward) - rig.toeTip
        }
        const allowed = KNEE_PAST_TOES * rig.scale
        if (pastToes(0) <= allowed) {
            continue
        }
        let low = 0
        let high = 0.12 * rig.scale
        if (pastToes(high) > allowed) {
            raise = Math.max(raise, high * weight)
            continue
        }
        for (let step = 0; step < 14; step += 1) {
            const middle = (low + high) / 2
            if (pastToes(middle) > allowed) {
                low = middle
            } else {
                high = middle
            }
        }
        raise = Math.max(raise, high * weight)
    }
    return height + raise
}

// Solves a sampled pose. Angles in the pose are radians. The pelvis is
// placed so that the centre of mass, not just the pelvis, sits over the
// weighted point between the feet.
export function solvePose(pose, rig) {
    const first = solveBody(pose, rig, new Vector3())
    const correction = first.balanceTarget.clone().sub(first.joints.com).setY(0)
    if (correction.length() < 1e-4) {
        return first
    }
    return solveBody(pose, rig, correction)
}

function solveBody(pose, rig, correction) {
    const scale = rig.scale
    const segments = {}
    const joints = {}
    const feet = { L: placeFoot(pose.feet.L, rig), R: placeFoot(pose.feet.R, rig) }

    // Pelvis: over the weighted support point of the feet.
    // Each foot bears weight at its middle when flat, at the heel or ball
    // when it stands on one of them. A heel that rises by itself (to reach)
    // hands its weight to the ball over a wider pitch, so the pelvis
    // follows it smoothly.
    const support = (foot, ramp = 3.5 * DEG) => {
        const middle = foot.ankle.clone().setY(0).addScaledVector(foot.forward, 0.03 * scale)
        const pitch = foot.pitch
        const contact = (pitch >= 0 ? foot.heel : foot.ball).clone().setY(0)
        return middle.lerp(contact, Math.min(1, Math.abs(pitch) / ramp))
    }
    const loadLeft = Math.min(1, Math.max(0, pose.load))
    const pelvisXZ = support(feet.L).multiplyScalar(loadLeft).add(support(feet.R).multiplyScalar(1 - loadLeft))
    const shift = pose.shift ?? [0, 0]
    pelvisXZ.addScaledVector(forwardOf(pose.facing), shift[0] * scale)
    pelvisXZ.addScaledVector(leftOf(pose.facing), shift[1] * scale)
    const balanceTarget = pelvisXZ.clone()
    pelvisXZ.add(correction)
    const hipYaw = pose.facing + pose.hips
    const chestYaw = pose.facing + pose.chest
    const lean = pose.lean ?? 0
    const bend = pose.bend ?? 0
    const pelvisQuat = bodyQuat(hipYaw, lean * 0.4, bend * 0.3)
    const targetHeight = rig.pelvisHeight - (pose.sink ?? 0) * scale
    let raisedAny = false
    const raisedSide = { L: false, R: false }
    for (const side of SIDES) {
        const share = side === 'L' ? loadLeft : 1 - loadLeft
        const raised = raiseHeelToReach(side, pose.feet[side], share, pelvisXZ, targetHeight, pelvisQuat, pose.facing, rig)
        if (raised) {
            feet[side] = raised
            raisedAny = true
            raisedSide[side] = true
        }
    }
    if (raisedAny) {
        // A raised heel moves that foot's weight onto its ball.
        const supportOf = (side) => support(feet[side], raisedSide[side] ? 14 * DEG : 3.5 * DEG)
        const moved = supportOf('L').multiplyScalar(loadLeft).add(supportOf('R').multiplyScalar(1 - loadLeft))
        const offset = moved.sub(support(placeFoot(pose.feet.L, rig)).multiplyScalar(loadLeft)
            .add(support(placeFoot(pose.feet.R, rig)).multiplyScalar(1 - loadLeft)))
        pelvisXZ.add(offset)
        balanceTarget.add(offset)
    }
    const kneeSafeHeight = kneeSafePelvisHeight(targetHeight, pelvisXZ, pelvisQuat, feet, pose, rig)
    const pelvisHeight = reachablePelvisHeight(kneeSafeHeight, pelvisXZ, pelvisQuat, feet, pose.feet, rig)
    const pelvis = new Vector3(pelvisXZ.x, pelvisHeight, pelvisXZ.z)
    segments.pelvis = { pos: pelvis, quat: pelvisQuat }
    joints.pelvis = pelvis

    // Spine: twist and lean spread over three pieces.
    const twistShare = [0.3, 0.65, 1.0]
    const leanShare = [0.6, 0.85, 1.0]
    const bendShare = [0.5, 0.8, 1.0]
    let origin = pelvis.clone()
    const spineNames = ['spine0', 'spine1', 'chest']
    for (let index = 0; index < 3; index += 1) {
        const yaw = hipYaw + (chestYaw - hipYaw) * twistShare[index]
        const quat = bodyQuat(yaw, lean * leanShare[index], bend * bendShare[index])
        segments[spineNames[index]] = { pos: origin.clone(), quat }
        origin = origin.clone().add(new Vector3(0, rig.spine[index], 0).applyQuaternion(quat))
    }
    const chestQuat = segments.chest.quat
    const neckBase = origin
    joints.neckBase = neckBase
    const shoulderCenter = neckBase.clone().add(new Vector3(0, -rig.shoulderDrop, 0).applyQuaternion(chestQuat))
    joints.shoulderCenter = shoulderCenter

    // Arms.
    const palms = {}
    const handInfo = {}
    for (const side of SIDES) {
        const hand = pose.hands[side]
        const sign = sideSign(side)
        const toWorld = (v) => chestLocal(side, v).applyQuaternion(chestQuat)
        const palm = shoulderCenter.clone().add(toWorld(hand.at).multiplyScalar(scale))
        const fingers = toWorld(directionVector(hand.fingers)).normalize()
        const palmNormal = toWorld(directionVector(hand.palm)).normalize()
        const handQuat = frameQuat(fingers.clone().negate(), palmNormal, toWorld([0, 0, 1]))
        const handY = new Vector3(0, 1, 0).applyQuaternion(handQuat)
        const handZ = new Vector3(0, 0, 1).applyQuaternion(handQuat)
        const shape = hand.shape ?? [1, 0, 0]
        const hookShare = shape[2] ?? 0
        const palmOffset = rig.palmOffset * (1 - 0.45 * hookShare)
        const wristTarget = palm.clone().addScaledVector(handY, palmOffset).addScaledVector(handZ, -0.008 * rig.height)

        const clavicleRoot = neckBase.clone().add(new Vector3(sign * 0.012 * rig.height, -0.008 * rig.height, 0.012 * rig.height).applyQuaternion(chestQuat))
        const shoulderRest = shoulderCenter.clone().add(new Vector3(sign * rig.shoulderHalfWidth, 0, -0.004 * rig.height).applyQuaternion(chestQuat))
        // Long reaches draw the shoulder a little toward the hand.
        const reach = wristTarget.distanceTo(shoulderRest)
        const excess = Math.max(0, reach - rig.armLength * 0.92)
        const shoulder = shoulderRest.clone().addScaledVector(
            wristTarget.clone().sub(shoulderRest).normalize(), Math.min(excess * 0.4, 0.03 * rig.height))
        const pole = toWorld(directionVector(hand.elbow ?? [0.35, -1, -0.25]))
        const arm = solveTwoBone(shoulder, wristTarget, rig.upperArm, rig.foreArm, pole)
        const elbow = arm.middle
        const wrist = arm.end
        const upperDir = elbow.clone().sub(shoulder)
        const foreDir = wrist.clone().sub(elbow)
        segments[`clavicle${side}`] = { pos: clavicleRoot, quat: frameQuat(clavicleRoot.clone().sub(shoulder), new Vector3(0, 0, 1).applyQuaternion(chestQuat)) }
        segments[`upperArm${side}`] = { pos: shoulder, quat: frameQuat(upperDir.clone().negate(), foreDir, new Vector3(0, 0, 1).applyQuaternion(chestQuat)) }
        segments[`foreArm${side}`] = { pos: elbow, quat: frameQuat(foreDir.clone().negate(), palmNormal, foreDir.clone().negate().cross(upperDir)) }
        segments[`hand${side}`] = { pos: wrist, quat: handQuat }
        const realPalm = wrist.clone().addScaledVector(handY, -palmOffset).addScaledVector(handZ, 0.008 * rig.height)
        palms[side] = realPalm
        joints[`shoulder${side}`] = shoulder
        joints[`elbow${side}`] = elbow
        joints[`wrist${side}`] = wrist
        joints[`palm${side}`] = realPalm
        joints[`fingertip${side}`] = wrist.clone().addScaledVector(handY, -rig.handLength * (1 - 0.55 * hookShare))
        handInfo[side] = { shape, stretched: arm.stretched, wristTarget, palmNormal, fingers }
    }

    // Neck and head.
    const headBase = neckBase.clone().add(new Vector3(0, rig.neck + 0.06 * rig.height, 0.03 * rig.height).applyQuaternion(chestQuat))
    const lookFrom = gazeAngles(pose.look?.from ?? pose.look, chestYaw, headBase, palms)
    const lookTo = pose.look?.to ? gazeAngles(pose.look.to, chestYaw, headBase, palms) : lookFrom
    const blend = pose.look?.u ?? 0
    const headYaw = lookFrom.yaw + (lookTo.yaw - lookFrom.yaw) * blend
    // The head stays near level when the torso leans: it keeps a third of the lean.
    const headPitch = lookFrom.pitch + (lookTo.pitch - lookFrom.pitch) * blend + lean * 0.35
    const headQuat = bodyQuat(headYaw, headPitch, bend * 0.5)
    const neckQuat = chestQuat.clone().slerp(headQuat, 0.5)
    segments.neck = { pos: neckBase.clone(), quat: neckQuat }
    const headPivot = neckBase.clone().add(new Vector3(0, rig.neck, 0).applyQuaternion(neckQuat))
    segments.head = { pos: headPivot, quat: headQuat }
    joints.headPivot = headPivot
    joints.headCenter = headPivot.clone().add(new Vector3(0, 0.065 * rig.height, 0.012 * rig.height).applyQuaternion(headQuat))
    joints.headTop = headPivot.clone().add(new Vector3(0, rig.headHeight, 0).applyQuaternion(headQuat))

    // Legs: knees track over the toes.
    const legInfo = {}
    for (const side of SIDES) {
        const foot = feet[side]
        const sign = sideSign(side)
        const hip = pelvis.clone().add(new Vector3(sign * rig.hipHalfWidth, -rig.hipDrop, 0).applyQuaternion(pelvisQuat))
        const footSide = leftOf(foot.yaw).multiplyScalar(sign)
        const pole = foot.forward.clone().add(footSide.multiplyScalar(0.1)).add(new Vector3(0, 0.05, 0))
        const leg = solveTwoBone(hip, foot.ankle, rig.thigh, rig.shin, pole)
        const knee = leg.middle
        const ankle = leg.end
        const thighDir = knee.clone().sub(hip)
        const shinDir = ankle.clone().sub(knee)
        segments[`thigh${side}`] = { pos: hip, quat: frameQuat(thighDir.clone().negate(), pole) }
        segments[`shin${side}`] = { pos: knee, quat: frameQuat(shinDir.clone().negate(), pole) }
        // If the leg could not reach, the foot hangs from the real ankle.
        const offset = ankle.clone().sub(foot.ankle)
        segments[`foot${side}`] = { pos: ankle, quat: foot.quat }
        segments[`toes${side}`] = { pos: foot.toesOrigin.clone().add(offset), quat: foot.toesQuat }
        joints[`hip${side}`] = hip
        joints[`knee${side}`] = knee
        joints[`ankle${side}`] = ankle
        joints[`heel${side}`] = foot.heel.clone().add(offset)
        joints[`ball${side}`] = foot.ball.clone().add(offset)
        joints[`toe${side}`] = foot.toeTip.clone().add(offset)
        legInfo[side] = { stretched: leg.stretched, reachError: offset.length(), grounded: foot.grounded, pitch: pose.feet[side].pitch ?? 0, autoHeel: feet[side].quat !== undefined && raisedHeel(feet[side], pose.feet[side], rig) }
    }

    // A rough centre of mass: pelvis weighted with the trunk and head.
    const com = pelvis.clone().multiplyScalar(0.55)
        .add(shoulderCenter.clone().multiplyScalar(0.3))
        .add(joints.headCenter.clone().multiplyScalar(0.08))
        .add(joints.kneeL.clone().add(joints.kneeR).multiplyScalar(0.035))
    joints.com = com

    return {
        segments,
        joints,
        feet,
        hands: handInfo,
        legs: legInfo,
        pelvisHeight,
        targetPelvisHeight: targetHeight,
        balanceTarget,
        hipYaw,
        chestYaw,
        headYaw,
        load: loadLeft,
    }
}
