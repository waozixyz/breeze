// The course characters: Sage Bun and Sage Male in loose Tai Chi clothes,
// and the flat Jade Woman and Lake Man, drawn in two tones like a flat
// illustration (calm closed eyes, dark sleeve cuffs; see flatMaterial).
//
// Cloth is skinned so it bends smoothly: the jacket follows the pelvis and
// the three spine pieces (its hem gives a little to the thighs), sleeves
// follow the upper arm and forearm, trousers the thigh and shin. Head,
// hands and slippers are rigid parts on their segment groups. The skinned
// meshes are built around the standing pose, which is their bind pose.

import {
    Bone, BufferGeometry, CylinderGeometry, DoubleSide, Float32BufferAttribute, Matrix4,
    Quaternion, Skeleton, SkinnedMesh, SphereGeometry, TorusGeometry, Uint16BufferAttribute, Vector3,
} from 'three'
import { standingPose } from '../pose.js'
import { solvePose } from '../solve.js'
import { FLAT_SHADE, addMesh, buildHand, curlHand, flatMaterial, material, registerStyle } from './figure.js'
import { ellipsoid, taperedCapsule } from './parts.js'

const SIDES = ['L', 'R']
const DOWN = new Vector3(0, -1, 0)

const LOOKS = {
    sageBun: {
        skin: 0xf0c4a2,
        skinShade: 0xe2a98a,
        lips: 0xc06a62,
        eyes: 0x2b211d,
        brows: 0x5a3020,
        hair: 0x8c4a2b,
        hairTie: 0x6f8f63,
        jacket: 0xf1e8d6,
        buttons: 0x8a6a4a,
        trousers: 0x748f68,
        trousersInside: 0x55704b,
        slipper: 0x2b2b30,
        sole: 0xeee8dc,
        style: 'bun',
        jacketShape: {
            hem: 0.126, hip: 0.116, waist: 0.099, chest: 0.103, shoulder: 0.103,
            hemDepth: 0.09, waistDepth: 0.07, chestDepth: 0.078, bust: 0.005,
        },
        neckRadius: 0.025,
        handSize: 0.95,
    },
    sageMale: {
        skin: 0xe9b691,
        skinShade: 0xd59c78,
        lips: 0xae6458,
        eyes: 0x2a2220,
        brows: 0x4a2a18,
        hair: 0x6e3f22,
        hairTie: 0x6e3f22,
        jacket: 0x3f5089,
        buttons: 0xe8dfca,
        trousers: 0xc9b17f,
        trousersInside: 0xa58f60,
        slipper: 0x26262b,
        sole: 0xeee8dc,
        style: 'short',
        jacketShape: {
            hem: 0.122, hip: 0.114, waist: 0.103, chest: 0.11, shoulder: 0.114,
            hemDepth: 0.088, waistDepth: 0.072, chestDepth: 0.08, bust: 0,
        },
        neckRadius: 0.029,
        handSize: 1.0,
    },
    jadeWoman: {
        flat: true,
        face: 'calm',
        skin: 0xf1c7a6,
        skinShade: 0xe0ad8c,
        blush: 0xec9f8f,
        lips: 0xc9806f,
        eyes: 0x2a2238,
        brows: 0x2a2238,
        hair: 0x2a2238,
        hairTie: 0xf2a65e,
        jacket: 0x3f8f7a,
        buttons: 0x2f705f,
        cuff: 0x2e3d63,
        trousers: 0x2e3d63,
        trousersInside: 0x232f4d,
        legCuff: 0x232f4d,
        slipper: 0x2a2238,
        sole: 0xeee8dc,
        style: 'bun',
        jacketShape: {
            hem: 0.134, hip: 0.12, waist: 0.104, chest: 0.105, shoulder: 0.103,
            hemDepth: 0.095, waistDepth: 0.073, chestDepth: 0.079, bust: 0.004,
        },
        neckRadius: 0.025,
        handSize: 0.95,
    },
    lakeMan: {
        flat: true,
        face: 'calm',
        skin: 0xd9a07c,
        skinShade: 0xc68c69,
        blush: null,
        lips: 0xa8705c,
        eyes: 0x2a2238,
        brows: 0x2a2238,
        hair: 0x2a2238,
        hairTie: 0x2a2238,
        jacket: 0x3f6f8f,
        buttons: 0x2f5470,
        cuff: 0x6e4c36,
        trousers: 0x6e4c36,
        trousersInside: 0x553a29,
        legCuff: 0x553a29,
        slipper: 0x2a2238,
        sole: 0xeee8dc,
        style: 'short',
        jacketShape: {
            hem: 0.126, hip: 0.116, waist: 0.105, chest: 0.111, shoulder: 0.114,
            hemDepth: 0.09, waistDepth: 0.073, chestDepth: 0.08, bust: 0,
        },
        neckRadius: 0.029,
        handSize: 1.0,
    },
}

function clamp01(value) {
    return Math.min(1, Math.max(0, value))
}

function smooth(edge0, edge1, value) {
    const u = clamp01((value - edge0) / (edge1 - edge0))
    return u * u * (3 - 2 * u)
}

function lerp(a, b, u) {
    return a + (b - a) * u
}

// Piecewise-linear lookup in rows of [key, ...values].
function profileAt(rows, key) {
    if (key <= rows[0][0]) {
        return rows[0].slice(1)
    }
    for (let index = 1; index < rows.length; index += 1) {
        if (key <= rows[index][0]) {
            const a = rows[index - 1]
            const b = rows[index]
            const u = (key - a[0]) / (b[0] - a[0])
            return a.slice(1).map((value, column) => lerp(value, b[column + 1], u))
        }
    }
    return rows[rows.length - 1].slice(1)
}

// The forearm bone used for skinning: the solved forearm direction with the
// upper arm's roll, so the sleeve never twists like a sweet wrapper at the
// elbow however the palm turns.
function forearmSkinQuat(upperQuat, foreQuat) {
    const upperDown = DOWN.clone().applyQuaternion(upperQuat)
    const foreDown = DOWN.clone().applyQuaternion(foreQuat)
    return new Quaternion().setFromUnitVectors(upperDown, foreDown).multiply(upperQuat)
}

const BONES = ['pelvis', 'spine0', 'spine1', 'chest', 'thighL', 'thighR', 'shinL', 'shinR', 'upperArmL', 'upperArmR', 'foreArmL', 'foreArmR']

function boneTransforms(solved) {
    const transforms = {}
    for (const name of BONES) {
        const segment = solved.segments[name]
        transforms[name] = { pos: segment.pos.clone(), quat: segment.quat.clone() }
    }
    for (const side of SIDES) {
        transforms[`foreArm${side}`].quat = forearmSkinQuat(solved.segments[`upperArm${side}`].quat, solved.segments[`foreArm${side}`].quat)
    }
    return transforms
}

// A tube of rings. Each ring: { center, axisX, axisZ, a, b, power, weights(point) }
// where weights returns [[boneIndex, weight], ...]. Rings run along the
// tube; normals face out. Optional caps close either end.
function tubeGeometry(rings, segments, { capStart = false, capEnd = false } = {}) {
    const positions = []
    const skinIndex = []
    const skinWeight = []
    const index = []
    const pushVertex = (point, weights) => {
        positions.push(point.x, point.y, point.z)
        const sorted = [...weights].filter(([, weight]) => weight > 1e-4).sort((a, b) => b[1] - a[1]).slice(0, 4)
        const total = sorted.reduce((sum, [, weight]) => sum + weight, 0) || 1
        for (let slot = 0; slot < 4; slot += 1) {
            skinIndex.push(sorted[slot] ? sorted[slot][0] : 0)
            skinWeight.push(sorted[slot] ? sorted[slot][1] / total : 0)
        }
        return positions.length / 3 - 1
    }
    const ringStarts = []
    for (const ring of rings) {
        ringStarts.push(positions.length / 3)
        const power = ring.power ?? 2
        for (let step = 0; step < segments; step += 1) {
            const angle = (step / segments) * Math.PI * 2
            const cos = Math.cos(angle)
            const sin = Math.sin(angle)
            const x = Math.sign(cos) * Math.pow(Math.abs(cos), 2 / power)
            const z = Math.sign(sin) * Math.pow(Math.abs(sin), 2 / power)
            const point = ring.center.clone().addScaledVector(ring.axisX, x * ring.a).addScaledVector(ring.axisZ, z * ring.b)
            pushVertex(point, ring.weights(point))
        }
    }
    for (let ringIndex = 0; ringIndex < rings.length - 1; ringIndex += 1) {
        const lower = ringStarts[ringIndex]
        const upper = ringStarts[ringIndex + 1]
        for (let step = 0; step < segments; step += 1) {
            const next = (step + 1) % segments
            index.push(lower + step, upper + step, lower + next)
            index.push(lower + next, upper + step, upper + next)
        }
    }
    const cap = (ringIndex, flip) => {
        const ring = rings[ringIndex]
        const start = ringStarts[ringIndex]
        const center = pushVertex(ring.capCenter ?? ring.center, ring.weights(ring.capCenter ?? ring.center))
        for (let step = 0; step < segments; step += 1) {
            const next = (step + 1) % segments
            if (flip) {
                index.push(center, start + next, start + step)
            } else {
                index.push(center, start + step, start + next)
            }
        }
    }
    if (capStart) {
        cap(0, false)
    }
    if (capEnd) {
        cap(rings.length - 1, true)
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
    geometry.setAttribute('skinIndex', new Uint16BufferAttribute(skinIndex, 4))
    geometry.setAttribute('skinWeight', new Float32BufferAttribute(skinWeight, 4))
    geometry.setIndex(index)
    geometry.computeVertexNormals()
    return geometry
}

// Ring axes perpendicular to `tangent`, with axisZ = axisX × tangent so the
// faces point outwards.
function ringAxes(tangent, hint = new Vector3(1, 0, 0)) {
    const axisX = hint.clone().addScaledVector(tangent, -hint.dot(tangent)).normalize()
    const axisZ = new Vector3().crossVectors(axisX, tangent).normalize()
    return { axisX, axisZ }
}

// Points along a polyline by arc length.
function polylinePoint(points, distance) {
    let travelled = 0
    for (let index = 0; index < points.length - 1; index += 1) {
        const length = points[index].distanceTo(points[index + 1])
        if (distance <= travelled + length || index === points.length - 2) {
            const u = length > 0 ? clamp01((distance - travelled) / length) : 0
            return {
                point: points[index].clone().lerp(points[index + 1], u),
                tangent: points[index + 1].clone().sub(points[index]).normalize(),
            }
        }
        travelled += length
    }
    return { point: points[points.length - 1].clone(), tangent: points[points.length - 1].clone().sub(points[points.length - 2]).normalize() }
}

function polylineLength(points) {
    let total = 0
    for (let index = 0; index < points.length - 1; index += 1) {
        total += points[index].distanceTo(points[index + 1])
    }
    return total
}

// A limb tube through `points`, radius by arc length from `profile`
// ([distanceShare, radius] rows), weights from the bend at `joint`.
function limbTube(points, profile, jointDistance, blend, boneUpper, boneLower, H, segments = 18, options = {}) {
    const length = polylineLength(points)
    const rings = []
    const stations = options.stations ?? 26
    const startTangent = points[1].clone().sub(points[0]).normalize()
    const hint = options.hint ?? (Math.abs(startTangent.x) > 0.8 ? new Vector3(0, 0, 1) : new Vector3(1, 0, 0))
    for (let station = 0; station <= stations; station += 1) {
        const distance = (station / stations) * length
        const { point, tangent } = polylinePoint(points, distance)
        const [radius] = profileAt(profile, distance / length)
        const { axisX, axisZ } = ringAxes(tangent, hint)
        const lowerShare = smooth(jointDistance - blend, jointDistance + blend, distance)
        rings.push({
            center: point,
            axisX,
            axisZ,
            a: radius * H,
            b: radius * H,
            weights: () => [[boneUpper, 1 - lowerShare], [boneLower, lowerShare]],
        })
    }
    return tubeGeometry(rings, segments, options)
}

function buildCharacter(figure, rig, options, lookName) {
    const look = LOOKS[lookName]
    const H = rig.height
    const g = figure.groups
    figure.flat = Boolean(look.flat)
    // A little self-light keeps faces warm on the dark stage instead of
    // shading the chin like a beard.
    const glow = (color, share) => {
        const r = ((color >> 16) & 255) * share
        const g2 = ((color >> 8) & 255) * share
        const b = (color & 255) * share
        return (Math.round(r) << 16) | (Math.round(g2) << 8) | Math.round(b)
    }
    // Flat looks keep only which faces they show; lit looks have their
    // roughness and glow.
    const surface = (color, extra = {}, shade = FLAT_SHADE.cloth) => (look.flat
        ? flatMaterial(figure, color, extra.side ? { side: extra.side } : {}, shade)
        : material(figure, color, extra))
    const skin = surface(look.skin, { roughness: 0.62, emissive: glow(look.skin, 0.16) }, FLAT_SHADE.skin)
    const skinShade = surface(look.skinShade, { roughness: 0.65, emissive: glow(look.skinShade, 0.12) }, FLAT_SHADE.skin)
    // On the dark stage, cloth and hair carry a little light of their own so
    // the figure stays clear of the background.
    const lift = options.theme === 'dark' ? 0.12 : 0
    const cloth = (color, extra = {}) => surface(color, { roughness: 0.88, emissive: glow(color, lift), ...extra })
    const jacket = cloth(look.jacket, { side: DoubleSide })
    const sleeve = cloth(look.jacket)
    const trousers = cloth(look.trousers, { roughness: 0.9 })
    const trousersInside = cloth(look.trousersInside, { roughness: 0.92 })
    const hair = cloth(look.hair, { roughness: 0.7 })
    const hairTie = surface(look.hairTie, { roughness: 0.7 })
    const dark = surface(look.eyes, { roughness: 0.4 })
    const brows = surface(look.brows, { roughness: 0.8 })
    const lips = surface(look.lips, { roughness: 0.6 })
    const white = surface(0xffffff, { roughness: 0.3 })
    const buttons = surface(look.buttons, { roughness: 0.6 })
    const slipper = surface(look.slipper, { roughness: 0.85 })
    const sole = surface(look.sole, { roughness: 0.9 })
    const blush = look.blush ? surface(look.blush, {}, FLAT_SHADE.skin) : null
    const cuff = look.cuff !== undefined ? surface(look.cuff, { side: DoubleSide }) : null
    const legCuff = look.legCuff !== undefined ? surface(look.legCuff, { side: DoubleSide }) : null

    // Bind pose: the standing pose, solved for this figure.
    const rest = solvePose(standingPose(), rig)
    const restBones = boneTransforms(rest)
    const bones = BONES.map((name) => {
        const bone = new Bone()
        bone.name = `skin-${name}`
        bone.position.copy(restBones[name].pos)
        bone.quaternion.copy(restBones[name].quat)
        figure.root.add(bone)
        return bone
    })
    const inverses = BONES.map((name) => new Matrix4().compose(restBones[name].pos, restBones[name].quat, new Vector3(1, 1, 1)).invert())
    const skeleton = new Skeleton(bones, inverses)
    const boneIndex = Object.fromEntries(BONES.map((name, index) => [name, index]))
    const addSkinned = (geometry, mat) => {
        const mesh = new SkinnedMesh(geometry, mat)
        mesh.bind(skeleton, new Matrix4())
        mesh.frustumCulled = false
        figure.root.add(mesh)
        return mesh
    }

    // Jacket: a loose torso from the hem to the collar.
    const shape = look.jacketShape
    const pelvis = rest.joints.pelvis
    const neckBase = rest.joints.neckBase
    const hipY = rest.joints.hipL.y
    const profile = [
        // height share, half width, half depth, forward offset (all × H)
        [0.478, shape.hem, shape.hemDepth, -0.006],
        [0.495, shape.hem - 0.004, shape.hemDepth - 0.003, -0.005],
        [0.52, shape.hip, shape.hemDepth - 0.01, -0.004],
        [0.56, shape.hip - 0.005, shape.waistDepth + 0.004, -0.002],
        [0.6, shape.waist, shape.waistDepth, 0],
        [0.64, shape.waist, shape.waistDepth, 0.002],
        [0.68, (shape.waist + shape.chest) / 2, shape.chestDepth - 0.004, 0.005 + shape.bust * 0.5],
        [0.715, shape.chest, shape.chestDepth, 0.007 + shape.bust],
        [0.75, shape.chest + 0.005, shape.chestDepth - 0.003, 0.006 + shape.bust * 0.6],
        [0.775, shape.shoulder - 0.003, shape.chestDepth - 0.01, 0.002],
        [0.795, shape.shoulder, shape.chestDepth - 0.017, 0],
        [0.807, shape.shoulder - 0.012, shape.chestDepth - 0.022, -0.001],
        [0.817, shape.shoulder - 0.032, shape.chestDepth - 0.026, -0.002],
        [0.826, shape.shoulder * 0.55, 0.05, -0.002],
        [0.834, 0.052, 0.046, 0.0],
    ]
    const spineWeights = (point) => {
        const share = point.y / H
        const weights = { pelvis: 0, spine0: 0, spine1: 0, chest: 0 }
        if (share < 0.555) {
            weights.pelvis = 1
        } else if (share < 0.6) {
            const u = smooth(0.555, 0.6, share)
            weights.pelvis = 1 - u
            weights.spine0 = u
        } else if (share < 0.66) {
            const u = smooth(0.6, 0.66, share)
            weights.spine0 = 1 - u
            weights.spine1 = u
        } else if (share < 0.735) {
            const u = smooth(0.69, 0.735, share)
            weights.spine1 = 1 - u
            weights.chest = u
        } else {
            weights.chest = 1
        }
        // The front of the hem drapes over whichever thigh lifts under it;
        // the back hangs from the pelvis.
        const below = clamp01((hipY + 0.025 * H - point.y) / (0.06 * H))
        const front = smooth(-0.01 * H, 0.06 * H, point.z - pelvis.z)
        let result = Object.entries(weights).map(([name, weight]) => [boneIndex[name], weight])
        if (below > 0 && front > 0) {
            const give = 0.85 * below * front
            const leftShare = smooth(-0.05 * H, 0.05 * H, point.x - pelvis.x)
            result = result.map(([bone, weight]) => [bone, weight * (1 - give)])
            result.push([boneIndex.thighL, give * leftShare], [boneIndex.thighR, give * (1 - leftShare)])
        }
        return result
    }
    const jacketRings = []
    const bottom = profile[0][0]
    const top = profile[profile.length - 1][0]
    const torsoStations = 30
    for (let station = 0; station <= torsoStations; station += 1) {
        // Denser rows near the shoulders where the shape turns quickly.
        const u = station / torsoStations
        const share = bottom + (top - bottom) * (1 - Math.pow(1 - u, 1.35))
        const [half, depth, forward] = profileAt(profile, share)
        const center = new Vector3(pelvis.x, share * H, pelvis.z + forward * H)
        jacketRings.push({
            center,
            axisX: new Vector3(1, 0, 0),
            axisZ: new Vector3(0, 0, 1),
            a: half * H,
            b: depth * H,
            power: share > 0.77 ? 2.0 : 2.4,
            weights: spineWeights,
            capCenter: share >= top - 1e-6 ? neckBase.clone() : undefined,
        })
    }
    addSkinned(tubeGeometry(jacketRings, 40, { capEnd: true }), jacket)

    // Mandarin collar, frog buttons.
    const collar = new CylinderGeometry(0.046 * H, 0.05 * H, 0.024 * H, 28, 1, true, 0.42, Math.PI * 2 - 0.84)
    addMesh(g.chest, collar, jacket, [0, rig.spine[2] + 0.006 * H, 0.002 * H])
    const chestDepthAt = (share) => profileAt(profile, share)
    for (const share of [0.79, 0.75, 0.71]) {
        const [, depth, forward] = chestDepthAt(share)
        const local = share * H - (pelvis.y + rig.spine[0] + rig.spine[1])
        addMesh(g.chest, ellipsoid(0.008 * H, 0.0035 * H, 0.004 * H), buttons, [0, local, (depth + forward) * H - 0.001 * H])
    }
    for (const share of [0.665]) {
        const [, depth, forward] = chestDepthAt(share)
        const local = share * H - (pelvis.y + rig.spine[0])
        addMesh(g.spine1, ellipsoid(0.008 * H, 0.0035 * H, 0.004 * H), buttons, [0, local, (depth + forward) * H - 0.001 * H])
    }

    // Seat of the trousers under the hem.
    addMesh(g.pelvis, ellipsoid(0.098 * H, 0.06 * H, 0.074 * H), trousers, [0, -0.028 * H, -0.004 * H])

    // Sleeves and trousers.
    for (const side of SIDES) {
        const shoulder = rest.joints[`shoulder${side}`]
        const elbow = rest.joints[`elbow${side}`]
        const wrist = rest.joints[`wrist${side}`]
        const towardHand = wrist.clone().sub(elbow).normalize()
        const sleeveTop = shoulder.clone().add(new Vector3(0, 0.006 * H, 0))
        const cuff = wrist.clone().addScaledVector(towardHand, -0.012 * H)
        const armPoints = [sleeveTop, shoulder, elbow, cuff]
        const armLength = polylineLength(armPoints)
        const elbowDistance = sleeveTop.distanceTo(shoulder) + shoulder.distanceTo(elbow)
        const sleeveProfile = [
            [0, 0.022], [0.03, 0.031], [0.1, 0.035], [0.3, 0.036], [elbowDistance / armLength, 0.034],
            [0.82, 0.033], [0.97, 0.031], [1, 0.03],
        ]
        addSkinned(limbTube(armPoints, sleeveProfile, elbowDistance, 0.035 * H,
            boneIndex[`upperArm${side}`], boneIndex[`foreArm${side}`], H, 18, { capStart: true, capEnd: true }), sleeve)
        // The jacket's shoulder stays round whatever the arm does: a filler
        // on the chest over the shoulder joint, and a cap on the upper arm.
        const sign = side === 'L' ? 1 : -1
        addMesh(g.chest, ellipsoid(0.03 * H, 0.022 * H, 0.032 * H, 20, 14), sleeve,
            [sign * (rig.shoulderHalfWidth - 0.006 * H), rig.spine[2] - rig.shoulderDrop - 0.02 * H, -0.004 * H])
        // Shoulder cap and elbow filler, rigid.
        addMesh(g[`upperArm${side}`], new SphereGeometry(0.03 * H, 20, 14), sleeve, [0, -0.022 * H, 0])
        addMesh(g[`foreArm${side}`], new SphereGeometry(0.031 * H, 16, 12), sleeve)
        // A dark band at the end of the sleeve, like a lined wide cuff.
        if (cuff) {
            const band = 0.026 * H
            addMesh(g[`foreArm${side}`], new CylinderGeometry(0.0318 * H, 0.0322 * H, band, 28, 1, true), cuff,
                [0, -(rig.foreArm - 0.012 * H - band / 2), 0])
        }
        // Inside of the cuff and the wrist.
        addMesh(g[`hand${side}`], taperedCapsule(0.0165 * H, 0.0175 * H, 0.03 * H, 14), skin, [0, 0.028 * H, 0])
        buildHand(figure, side, g[`hand${side}`], rig, skin, look.handSize)

        const hip = rest.joints[`hip${side}`]
        const knee = rest.joints[`knee${side}`]
        const ankle = rest.joints[`ankle${side}`]
        const legTop = hip.clone().add(new Vector3(0, 0.022 * H, 0))
        const legEnd = ankle.clone().add(new Vector3(0, 0.006 * H, 0))
        const legPoints = [legTop, hip, knee, legEnd]
        const legLength = polylineLength(legPoints)
        const kneeDistance = legTop.distanceTo(hip) + hip.distanceTo(knee)
        const k = kneeDistance / legLength
        const trouserProfile = [
            [0, 0.036], [0.05, 0.044], [0.13, 0.053], [0.3, 0.055], [k - 0.06, 0.049], [k, 0.047], [k + 0.12, 0.045],
            [0.84, 0.041], [0.92, 0.034], [0.955, 0.028], [0.965, 0.031], [1, 0.03],
        ]
        addSkinned(limbTube(legPoints, trouserProfile, kneeDistance, 0.045 * H,
            boneIndex[`thigh${side}`], boneIndex[`shin${side}`], H, 20, { capEnd: true }), trousers)
        addMesh(g[`shin${side}`], new SphereGeometry(0.041 * H, 18, 12), trousers, [0, 0.002 * H, 0.002 * H])
        // Ankle under the cuff.
        addMesh(g[`shin${side}`], taperedCapsule(0.022 * H, 0.021 * H, 0.03 * H, 12), trousersInside, [0, -rig.shin + 0.03 * H, 0])
        if (legCuff) {
            const band = 0.03 * H
            addMesh(g[`shin${side}`], new CylinderGeometry(0.0335 * H, 0.0335 * H, band, 28, 1, true), legCuff,
                [0, -rig.shin + 0.006 * H + band / 2, 0])
        }

        // Slipper: cloth upper and pale sole; the toe box bends at the ball.
        const foot = g[`foot${side}`]
        const toes = g[`toes${side}`]
        const sole0 = -rig.ankleHeight
        const footLength = rig.ball + rig.heelBack
        addMesh(foot, ellipsoid(0.03 * H, 0.026 * H, footLength * 0.55), slipper, [0, sole0 + 0.022 * H, (rig.ball - rig.heelBack) * 0.5 - 0.002 * H])
        addMesh(foot, new CylinderGeometry(0.024 * H, 0.027 * H, 0.03 * H, 16), slipper, [0, sole0 + 0.035 * H, -0.004 * H])
        addMesh(foot, ellipsoid(0.031 * H, 0.0045 * H, footLength * 0.56), sole, [0, sole0 + 0.0045 * H, (rig.ball - rig.heelBack) * 0.5])
        const toeLength = rig.toeTip - rig.ball
        addMesh(toes, ellipsoid(0.029 * H, 0.019 * H, toeLength * 0.9), slipper, [0, 0.016 * H, toeLength * 0.25])
        addMesh(toes, ellipsoid(0.03 * H, 0.0045 * H, toeLength * 0.92), sole, [0, 0.0045 * H, toeLength * 0.25])
    }

    // Neck and head.
    addMesh(g.neck, taperedCapsule(look.neckRadius * H, look.neckRadius * H * 1.05, 0.05 * H, 16), skin, [0, 0.045 * H, 0.002 * H])
    buildHead(figure, rig, look, { skin, skinShade, hair, hairTie, dark, brows, lips, white, blush })

    figure.updateHand = (side, shapeWeights) => curlHand(figure, side, shapeWeights)
    figure.afterUpdate = (solved) => {
        const transforms = boneTransforms(solved)
        BONES.forEach((name, index) => {
            bones[index].position.copy(transforms[name].pos)
            bones[index].quaternion.copy(transforms[name].quat)
        })
    }
    const disposeParts = figure.dispose
    figure.dispose = () => {
        disposeParts()
        skeleton.dispose()
    }
}

// Head: rounded skull and jaw, simple friendly face, hair.
function buildHead(figure, rig, look, mats) {
    const H = rig.height
    const head = figure.groups.head
    const skull = { x: 0, y: 0.068 * H, z: 0.012 * H, rx: 0.058 * H, ry: 0.071 * H, rz: 0.063 * H }
    addMesh(head, ellipsoid(skull.rx, skull.ry, skull.rz, 32, 24), mats.skin, [skull.x, skull.y, skull.z])
    addMesh(head, ellipsoid(0.041 * H, 0.034 * H, 0.043 * H, 24, 16), mats.skin, [0, 0.043 * H, 0.022 * H])
    // Surface of the face at (x, y).
    const faceZ = (x, y) => {
        const share = 1 - Math.pow((x - skull.x) / skull.rx, 2) - Math.pow((y - skull.y) / skull.ry, 2)
        return skull.z + skull.rz * Math.sqrt(Math.max(share, 0))
    }
    const calm = look.face === 'calm'
    for (const sign of [1, -1]) {
        const x = sign * 0.021 * H
        const y = 0.066 * H
        if (calm) {
            // Closed, peaceful eyes: a thin arc curving down, and a blush.
            const eye = addMesh(head, new TorusGeometry(0.0078 * H, 0.0013 * H, 6, 18, Math.PI * 0.7), mats.dark,
                [x, y + 0.004 * H, faceZ(x, y) + 0.0002 * H])
            eye.rotation.set(0, sign * 0.32, Math.PI * 1.15)
            if (mats.blush) {
                const cheek = addMesh(head, ellipsoid(0.0085 * H, 0.0062 * H, 0.003 * H, 14, 10), mats.blush,
                    [sign * 0.031 * H, 0.049 * H, faceZ(sign * 0.031 * H, 0.049 * H) - 0.0012 * H])
                cheek.rotation.y = sign * 0.55
            }
        } else {
            const eye = addMesh(head, ellipsoid(0.0072 * H, 0.0098 * H, 0.004 * H, 16, 12), mats.dark, [x, y, faceZ(x, y) - 0.0016 * H])
            eye.rotation.y = sign * 0.32
            addMesh(head, new SphereGeometry(0.0022 * H, 8, 6), mats.white, [x + 0.0025 * H, y + 0.0035 * H, faceZ(x, y) + 0.0018 * H])
        }
        const browRadius = calm ? 0.0012 * H : 0.0019 * H
        const brow = addMesh(head, taperedCapsule(browRadius, browRadius * 0.85, 0.016 * H, 8), mats.brows,
            [x - sign * 0.008 * H, y + 0.0185 * H, faceZ(x, y + 0.018 * H) - 0.0006 * H])
        brow.rotation.set(0, sign * 0.3, sign * (Math.PI / 2 + 0.12))
        // Ears.
        addMesh(head, ellipsoid(0.0085 * H, 0.014 * H, 0.01 * H, 12, 10), mats.skinShade, [sign * 0.056 * H, 0.06 * H, 0.0])
    }
    addMesh(head, ellipsoid(0.0068 * H, 0.009 * H, 0.0068 * H, 12, 10), mats.skinShade, [0, 0.051 * H, faceZ(0, 0.051 * H) - 0.001 * H])
    const mouth = addMesh(head, new TorusGeometry(0.0085 * H, 0.0016 * H, 8, 18, Math.PI * 0.75), mats.lips,
        [0, 0.039 * H, faceZ(0, 0.04 * H) + 0.0012 * H])
    mouth.rotation.set(0.2, 0, Math.PI + Math.PI * 0.125)

    if (look.style === 'bun') {
        // Cap tilted back: hairline high at the front, low at the nape.
        const cap = addMesh(head, new SphereGeometry(1, 36, 22, 0, Math.PI * 2, 0, Math.PI * 0.53), mats.hair,
            [0, skull.y + 0.004 * H, skull.z - 0.004 * H])
        cap.scale.set(skull.rx + 0.0045 * H, skull.ry + 0.006 * H, skull.rz + 0.0045 * H)
        cap.rotation.x = -0.62
        // Side-swept fringe and the bun with its tie.
        const fringe = addMesh(head, ellipsoid(0.04 * H, 0.013 * H, 0.024 * H, 20, 12), mats.hair, [0.012 * H, 0.118 * H, 0.046 * H])
        fringe.rotation.set(0.5, 0, -0.3)
        addMesh(head, ellipsoid(0.031 * H, 0.028 * H, 0.03 * H, 22, 16), mats.hair, [0, 0.135 * H, -0.044 * H])
        const tie = addMesh(head, new TorusGeometry(0.019 * H, 0.0045 * H, 8, 20), mats.hairTie, [0, 0.122 * H, -0.035 * H])
        tie.rotation.x = -0.9
    } else {
        const cap = addMesh(head, new SphereGeometry(1, 36, 22, 0, Math.PI * 2, 0, Math.PI * 0.5), mats.hair,
            [0, skull.y + 0.003 * H, skull.z - 0.003 * H])
        cap.scale.set(skull.rx + 0.004 * H, skull.ry + 0.005 * H, skull.rz + 0.004 * H)
        cap.rotation.x = -0.45
        // Volume on top with a side part, and short sideburns.
        const top = addMesh(head, ellipsoid(0.054 * H, 0.026 * H, 0.06 * H, 24, 14), mats.hair, [0.004 * H, 0.123 * H, 0.012 * H])
        top.rotation.set(0.12, 0, -0.08)
        const quiff = addMesh(head, ellipsoid(0.034 * H, 0.014 * H, 0.022 * H, 18, 10), mats.hair, [0.012 * H, 0.121 * H, 0.054 * H])
        quiff.rotation.set(0.5, 0, -0.2)
        for (const sign of [1, -1]) {
            addMesh(head, ellipsoid(0.006 * H, 0.016 * H, 0.012 * H, 10, 8), mats.hair, [sign * 0.056 * H, 0.074 * H, 0.012 * H])
        }
    }
}

registerStyle('sageBun', (figure, rig, options) => buildCharacter(figure, rig, options, 'sageBun'))
registerStyle('sageMale', (figure, rig, options) => buildCharacter(figure, rig, options, 'sageMale'))
registerStyle('jadeWoman', (figure, rig, options) => buildCharacter(figure, rig, options, 'jadeWoman'))
registerStyle('lakeMan', (figure, rig, options) => buildCharacter(figure, rig, options, 'lakeMan'))
