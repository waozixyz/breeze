// Motion checks: things a teacher would correct and things that betray an
// animation. Each check samples the timeline and reports the time ranges
// where it fails.

import { Vector3 } from 'three'
import { solvePose } from './solve.js'

const SIDES = ['L', 'R']
const DEG = Math.PI / 180

// Limits, in metres, seconds and degrees for the figure being checked.
export const LIMITS = {
    footSlide: 0.008,
    footFloat: 0.006,
    kneeTrackAngle: 25,
    kneePastToes: 0.04,
    kneeFlexion: 128,
    kneeFlexionDeep: 150,
    wristBend: 85,
    wristBendHook: 115,
    handInBody: 0.0,
    balanceMargin: 0.03,
    handSpeed: 2.2,
    footSpeed: 1.6,
    pelvisSpeed: 0.75,
    headSpeed: 1.0,
    jumpSpeed: 3.5,
    feetApart: 0.05,
    kneesApart: 0.07,
    facingTolerance: 12,
}

const SPEED_LIMITS = {
    palmL: LIMITS.handSpeed,
    palmR: LIMITS.handSpeed,
    pelvis: LIMITS.pelvisSpeed,
    headTop: LIMITS.headSpeed,
    ankleL: LIMITS.footSpeed,
    ankleR: LIMITS.footSpeed,
}

function angleBetween(a, b) {
    const dot = a.clone().normalize().dot(b.clone().normalize())
    return Math.acos(Math.min(1, Math.max(-1, dot))) / DEG
}

// Distance from point p to segment ab.
function segmentDistance(p, a, b) {
    const ab = b.clone().sub(a)
    const t = Math.min(1, Math.max(0, p.clone().sub(a).dot(ab) / Math.max(ab.lengthSq(), 1e-9)))
    return p.distanceTo(a.clone().addScaledVector(ab, t))
}

function segmentSegmentDistance(a0, a1, b0, b1) {
    let best = Infinity
    for (let index = 0; index <= 8; index += 1) {
        const point = a0.clone().lerp(a1, index / 8)
        best = Math.min(best, segmentDistance(point, b0, b1))
    }
    return best
}

// Convex hull of floor points (x, z), counter-clockwise.
function hull(points) {
    const sorted = [...points].sort((a, b) => a.x - b.x || a.z - b.z)
    if (sorted.length < 3) {
        return sorted
    }
    const cross = (o, a, b) => (a.x - o.x) * (b.z - o.z) - (a.z - o.z) * (b.x - o.x)
    const lower = []
    for (const point of sorted) {
        while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
            lower.pop()
        }
        lower.push(point)
    }
    const upper = []
    for (let index = sorted.length - 1; index >= 0; index -= 1) {
        const point = sorted[index]
        while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) {
            upper.pop()
        }
        upper.push(point)
    }
    upper.pop()
    lower.pop()
    return lower.concat(upper)
}

// How far a point lies outside a convex polygon (0 inside).
function outsideDistance(point, polygon) {
    if (polygon.length === 0) {
        return Infinity
    }
    if (polygon.length < 3) {
        let best = Infinity
        for (let index = 0; index < polygon.length; index += 1) {
            const a = polygon[index]
            const b = polygon[(index + 1) % polygon.length]
            best = Math.min(best, segmentDistance(new Vector3(point.x, 0, point.z), new Vector3(a.x, 0, a.z), new Vector3(b.x, 0, b.z)))
        }
        return best
    }
    let inside = true
    let best = Infinity
    for (let index = 0; index < polygon.length; index += 1) {
        const a = polygon[index]
        const b = polygon[(index + 1) % polygon.length]
        const crossValue = (b.x - a.x) * (point.z - a.z) - (b.z - a.z) * (point.x - a.x)
        if (crossValue < 0) {
            inside = false
        }
        best = Math.min(best, segmentDistance(new Vector3(point.x, 0, point.z), new Vector3(a.x, 0, a.z), new Vector3(b.x, 0, b.z)))
    }
    return inside ? 0 : best
}

// The floor outline a planted foot covers, given its solved points.
function footprintPoints(solved, side, rig) {
    const heel = solved.joints[`heel${side}`]
    const toe = solved.joints[`toe${side}`]
    const ball = solved.joints[`ball${side}`]
    const along = toe.clone().sub(heel).setY(0).normalize()
    const across = new Vector3(-along.z, 0, along.x).multiplyScalar(rig.footHalfWidth)
    const points = []
    const onFloor = (point) => point.y < 0.012
    for (const point of [heel, ball, toe]) {
        if (onFloor(point)) {
            points.push({ x: point.x + across.x, z: point.z + across.z })
            points.push({ x: point.x - across.x, z: point.z - across.z })
        }
    }
    if (points.length === 0 && ball.y < 0.02) {
        points.push({ x: ball.x, z: ball.z })
    }
    return points
}

class IssueLog {
    constructor(step) {
        this.step = step
        this.open = new Map()
        this.issues = []
    }

    // Records a failing sample; consecutive samples merge into one issue.
    fail(time, check, part, message, value, severity = 'error') {
        const id = `${check}:${part}`
        const current = this.open.get(id)
        if (current && time - current.end <= this.step * 1.5) {
            current.end = time
            if (Math.abs(value) > Math.abs(current.worst)) {
                current.worst = value
                current.message = message
                current.at = time
            }
            return
        }
        const issue = { check, part, message, start: time, end: time, at: time, worst: value, severity }
        this.open.set(id, issue)
        this.issues.push(issue)
    }
}

export function checkTimeline(timeline, rig, { fps = 30, moves = [], expectDuration = null } = {}) {
    const step = 1 / fps
    const log = new IssueLog(step)
    const anchors = { L: null, R: null }
    let previous = null
    const frames = Math.floor(timeline.duration * fps) + 1
    for (let frame = 0; frame < frames; frame += 1) {
        const time = Math.min(frame * step, timeline.duration)
        const sample = timeline.sample(timeline.start + time)
        const pose = sample.pose
        const solved = solvePose(pose, rig)
        const joints = solved.joints

        for (const side of SIDES) {
            const foot = pose.feet[side]
            const leg = solved.legs[side]
            const share = side === 'L' ? solved.load : 1 - solved.load
            const planted = (foot.lift ?? 0) < 0.0015
            // Feet on the floor reach it and do not slide.
            if (planted && leg.reachError > LIMITS.footFloat) {
                log.fail(time, 'foot-reach', side, `${side} foot hangs ${(leg.reachError * 100).toFixed(1)} cm short of the floor`, leg.reachError)
            }
            const heel = joints[`heel${side}`]
            const ball = joints[`ball${side}`]
            const heelDown = heel.y < 0.004
            const ballDown = ball.y < 0.004
            if (planted && (heelDown || ballDown)) {
                const anchor = anchors[side]
                if (anchor) {
                    if (heelDown && anchor.heel) {
                        const moved = heel.distanceTo(anchor.heel)
                        if (moved > LIMITS.footSlide) {
                            log.fail(time, 'foot-slide', side, `${side} heel slides ${(moved * 100).toFixed(1)} cm while planted`, moved)
                            anchor.heel = heel.clone()
                        }
                    }
                    if (ballDown && anchor.ball) {
                        const moved = ball.distanceTo(anchor.ball)
                        if (moved > LIMITS.footSlide) {
                            log.fail(time, 'foot-slide', side, `${side} ball slides ${(moved * 100).toFixed(1)} cm while planted`, moved)
                            anchor.ball = ball.clone()
                        }
                    }
                    anchor.heel = heelDown ? anchor.heel ?? heel.clone() : null
                    anchor.ball = ballDown ? anchor.ball ?? ball.clone() : null
                } else {
                    anchors[side] = { heel: heelDown ? heel.clone() : null, ball: ballDown ? ball.clone() : null }
                }
            } else {
                anchors[side] = null
            }

            // Knees bend the way the toes point, and a front knee stays
            // behind its toes.
            const knee = joints[`knee${side}`]
            const ankle = joints[`ankle${side}`]
            const hip = joints[`hip${side}`]
            const toward = joints[`toe${side}`].clone().sub(heel).setY(0).normalize()
            const axis = ankle.clone().sub(hip).normalize()
            const onAxis = hip.clone().addScaledVector(axis, knee.clone().sub(hip).dot(axis))
            const bendDirection = knee.clone().sub(onAxis)
            const toesAcross = toward.clone().addScaledVector(axis, -toward.dot(axis))
            if (planted && share > 0.4 && bendDirection.length() > 0.04 && toesAcross.length() > 0.2) {
                const offTrack = angleBetween(bendDirection, toesAcross)
                if (offTrack > LIMITS.kneeTrackAngle) {
                    log.fail(time, 'knee-track', side, `${side} knee bends ${offTrack.toFixed(0)}° away from the toes`, offTrack, 'warn')
                }
            }
            const otherHeel = joints[`heel${side === 'L' ? 'R' : 'L'}`]
            const facingVector = new Vector3(Math.sin(pose.facing), 0, Math.cos(pose.facing))
            const inFront = heel.clone().sub(otherHeel).dot(facingVector) > 0.25
            const otherPlanted = (pose.feet[side === 'L' ? 'R' : 'L'].lift ?? 0) < 0.0015
            if (planted && otherPlanted && inFront && share > 0.5) {
                const pastToes = knee.clone().sub(ankle).setY(0).dot(toward) - rig.toeTip
                if (pastToes > LIMITS.kneePastToes) {
                    log.fail(time, 'knee-past-toes', side, `${side} front knee is ${(pastToes * 100).toFixed(0)} cm past the toes`, pastToes, 'warn')
                }
            }
            const flexion = 180 - angleBetween(hip.clone().sub(knee), ankle.clone().sub(knee))
            const deepAllowed = (sample.from.pose.deep || sample.to.pose.deep)
            const flexionLimit = deepAllowed ? LIMITS.kneeFlexionDeep : LIMITS.kneeFlexion
            if (flexion > flexionLimit) {
                log.fail(time, 'knee-flexion', side, `${side} knee bends ${flexion.toFixed(0)}°`, flexion)
            }

            // Wrists stay within comfortable bends; arms do not overreach.
            const elbow = joints[`elbow${side}`]
            const wrist = joints[`wrist${side}`]
            const fingertip = joints[`fingertip${side}`]
            const hand = solved.hands[side]
            const wristBend = angleBetween(wrist.clone().sub(elbow), fingertip.clone().sub(wrist))
            const wristLimit = (hand.shape[2] ?? 0) > 0.5 ? LIMITS.wristBendHook : LIMITS.wristBend
            if (wristBend > wristLimit) {
                log.fail(time, 'wrist-bend', side, `${side} wrist bends ${wristBend.toFixed(0)}°`, wristBend, 'warn')
            }
            if (hand.stretched) {
                log.fail(time, 'arm-reach', side, `${side} hand target is out of reach; the arm locks straight`, 1, 'warn')
            }
            // Hands stay outside the torso.
            const palm = joints[`palm${side}`]
            const torsoRadius = 0.085 * rig.height
            const inside = torsoRadius - segmentDistance(palm, joints.pelvis.clone().add(new Vector3(0, 0.03 * rig.height, 0)), joints.neckBase.clone().add(new Vector3(0, -0.06 * rig.height, 0)))
            if (inside > 0.015) {
                log.fail(time, 'hand-in-body', side, `${side} hand sinks ${(inside * 100).toFixed(0)} cm into the body`, inside)
            }
            if (palm.y < 0.06) {
                log.fail(time, 'hand-floor', side, `${side} hand touches the floor`, palm.y)
            }
        }

        // Feet and knees do not collide.
        const footGap = segmentSegmentDistance(joints.heelL, joints.toeL, joints.heelR, joints.toeR) - 2 * rig.footHalfWidth
        if (footGap < -0.005) {
            log.fail(time, 'feet-overlap', 'feet', `The feet overlap by ${(-footGap * 100).toFixed(1)} cm`, -footGap)
        }
        const kneeGap = joints.kneeL.distanceTo(joints.kneeR)
        if (kneeGap < LIMITS.kneesApart) {
            log.fail(time, 'knees-collide', 'knees', `The knees come within ${(kneeGap * 100).toFixed(0)} cm`, kneeGap, 'warn')
        }

        // Balance: the centre of mass stays over the feet.
        const support = []
        for (const side of SIDES) {
            if ((pose.feet[side].lift ?? 0) < 0.0015) {
                support.push(...footprintPoints(solved, side, rig))
            }
        }
        const outside = outsideDistance({ x: joints.com.x, z: joints.com.z }, hull(support))
        if (outside > LIMITS.balanceMargin) {
            log.fail(time, 'balance', 'body', `Centre of mass is ${(outside * 100).toFixed(0)} cm outside the feet`, outside)
        }

        // Smooth: no jumps, no rushing.
        const tracked = { palmL: joints.palmL, palmR: joints.palmR, pelvis: joints.pelvis, headTop: joints.headTop, ankleL: joints.ankleL, ankleR: joints.ankleR }
        if (previous) {
            for (const [name, point] of Object.entries(tracked)) {
                const speed = point.distanceTo(previous[name]) / step
                if (speed > LIMITS.jumpSpeed) {
                    log.fail(time, 'jump', name, `${name} jumps (${speed.toFixed(1)} m/s)`, speed)
                    continue
                }
                const limit = SPEED_LIMITS[name]
                if (speed > limit) {
                    log.fail(time, 'speed', name, `${name} moves at ${speed.toFixed(2)} m/s`, speed, 'warn')
                }
            }
        }
        previous = Object.fromEntries(Object.entries(tracked).map(([name, point]) => [name, point.clone()]))
    }

    // Facing at the end of each movement.
    for (const move of moves) {
        if (move.endFacing === undefined || move.end === undefined) {
            continue
        }
        const pose = timeline.sample(timeline.start + move.end).pose
        let difference = pose.facing / DEG - move.endFacing
        difference = ((difference % 360) + 540) % 360 - 180
        if (Math.abs(difference) > LIMITS.facingTolerance) {
            log.fail(move.end, 'facing', move.id, `${move.title} ends facing ${(pose.facing / DEG).toFixed(0)}°, expected ${move.endFacing}°`, difference)
        }
    }
    if (expectDuration) {
        const [low, high] = expectDuration
        if (timeline.duration < low || timeline.duration > high) {
            log.fail(0, 'duration', 'form', `Lasts ${(timeline.duration / 60).toFixed(2)} min, expected ${(low / 60).toFixed(1)}–${(high / 60).toFixed(1)} min`, timeline.duration)
        }
    }
    const issues = log.issues.sort((a, b) => a.start - b.start)
    return {
        issues,
        errors: issues.filter((issue) => issue.severity === 'error').length,
        warnings: issues.filter((issue) => issue.severity === 'warn').length,
        frames,
    }
}
