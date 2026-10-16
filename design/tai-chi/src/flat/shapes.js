// The shapes of a flat figure: the solved body drawn as flat 2D shapes,
// like a flat vector illustration and like Inbe's flat Sun Salutation
// characters (scripts/render-sun-salutation-flat.py). The solved skeleton is
// projected flat along the view as for the painted figures (FlatView), and
// `paint` returns the frame as paint operations, back to front: filled
// convex polygons and stroked lines, in metres with screen y up. The studio
// draws them with Canvas 2D (figure.js); Inbe draws the same operations
// with Kryon (src/practices/tai_chi/tai_chi_flat.zi).
//
// - Arms and legs are hulls of circles at their joints and of rings at
//   their cuffs, so they read from any side. Parts of one colour overlap
//   and join without seams.
// - The jacket is a loft of rings along the spine: the hull of each pair of
//   neighbouring rings, so it turns and bends from any side. A darker hem,
//   collar and wrap line sit on it.
// - The head is a few ellipsoids in its own frame. Its outline is drawn in
//   the hair colour, then the face: the part of the hair shell below the
//   hairline that the viewer sees, cut exactly where the hairline and the
//   outline meet. Jaw, nose and ears go behind or in front by depth, then
//   the fringe, the bun and its tie, closed eyes, brows, blush and mouth.
// - The far arm and leg take a darker tone, and an arm in front casts a
//   crisp shade on the jacket.
//
// Only what Inbe's solver keeps is read: joints, the pelvis, chest, head,
// hand, foot and toes orientations, and the spine points.

import { Quaternion, Vector3 } from 'three'

const SIDES = ['L', 'R']
export const FLAT_RING_POINTS = 24
export const FLAT_OUTLINE_POINTS = 32
export const FLAT_TORSO_STATIONS = 20
export const FLAT_CLIP_STATIONS = 8
// Height of the hip joints at rest, as a share of standing height (rig.js).
const HIP_SHARE = 0.524

// --- Looks -----------------------------------------------------------------

// Jacket rows as in the 3D characters (view/characters.js): height share at
// rest, half width, half depth and forward offset, all × height.
function jacketProfile(shape) {
    return [
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
        [0.834, 0.05, 0.044, 0.0],
    ]
}

// Legs and arms, × height: thigh radii at hip, middle and knee; shin radii
// at knee and calf; where the trousers end (height above the ankle,
// radius); their band (top height above the ankle, top and bottom radii).
const LOOSE_LEGS = { thigh: [0.052, 0.049, 0.04], shin: [0.039, 0.0375], end: [0.035, 0.034], band: [0.075, 0.0335, 0.0345] }
// Baggy trousers gathered at the ankle.
const GATHERED_LEGS = { thigh: [0.057, 0.056, 0.048], shin: [0.047, 0.05], end: [0.03, 0.028], band: [0.066, 0.031, 0.029] }

// A look with the defaults filled in. Colours: `sleeve` (the top's when
// absent), `cuff`, `wrap` and `collar` (the top's shade), `band` (the
// trousers' shade), `shoes` (bare feet when absent), `scalp` (a shaved
// head's tone). `sash` bands are [from, to, colour] in height shares;
// `jacketFrom` is where the top ends below. Hair is 'bun', 'crop', 'shaved'
// or 'crown' (braids wound round the head, with yarn and beads).
function makeLook(look) {
    return {
        male: false,
        sleeves: 'long',
        legs: LOOSE_LEGS,
        sash: [],
        jacketFrom: look.jacket[0][0],
        collarWidth: 0.006,
        limbs: 1,
        ...look,
        head: { fringe: null, crown: null, ears: false, ...look.head },
    }
}

// Jade woman and Indigo man match the flat Sun Salutation characters Jade
// bun and Indigo crop (docs/sun-salutation-flat.json in Inbe); the Tibetan
// woman and monk follow the studio's painted pair (characters/*/source).
// Sizes are × height. The hair zone of the head is where u · axis > edge
// on the hair shell's unit sphere; `fringe` is an extra cap of hair.
export const FLAT_LOOKS = {
    jadeWoman: makeLook({
        name: 'Jade Woman',
        colors: {
            skin: '#f1c7a6', hair: '#2a2238', top: '#3f8f7a', pants: '#2e3d63', cuff: '#2e3d63',
            accent: '#f2a65e', features: '#2a2238', mouth: '#c9806f', blush: '#ec9f8f',
        },
        jacket: jacketProfile({
            hem: 0.134, hip: 0.12, waist: 0.104, chest: 0.105, shoulder: 0.103,
            hemDepth: 0.095, waistDepth: 0.073, chestDepth: 0.079, bust: 0.004,
        }),
        neck: 0.025,
        head: {
            scale: 1.08, blush: 0.5, lashes: true, brow: 0.0016, hair: 'bun',
            hairAxis: [0, 0.814, -0.581], hairEdge: -0.094,
            fringe: { axis: [0.3, 0.62, 0.72], edge: 0.866 },
        },
    }),
    indigoMan: makeLook({
        name: 'Indigo Man',
        male: true,
        colors: {
            skin: '#e6aa7c', hair: '#7a4a2e', top: '#4f5c94', pants: '#c4ab78', cuff: '#424e80',
            accent: '#f2a65e', features: '#3a2a26', mouth: '#a8705c', blush: '#d98f7a',
        },
        jacket: jacketProfile({
            hem: 0.126, hip: 0.116, waist: 0.105, chest: 0.111, shoulder: 0.114,
            hemDepth: 0.09, waistDepth: 0.073, chestDepth: 0.08, bust: 0,
        }),
        limbs: 1.06,
        neck: 0.029,
        head: {
            scale: 1.06, blush: 0, lashes: false, brow: 0.0024, ears: true, hair: 'crop',
            hairAxis: [0, 0.9, -0.435], hairEdge: 0,
        },
    }),
    tibetanWoman: makeLook({
        name: 'Tibetan Woman',
        colors: {
            skin: '#c98d64', hair: '#2a2025', top: '#2f6f7a', sleeve: '#efe6d6', cuff: '#ddd2bf',
            pants: '#2c3558', band: '#222a46', wrap: '#235a63', collar: '#efe6d6', shoes: '#8a2a2a',
            accent: '#b03a2e', features: '#2a2025', mouth: '#a8604f', blush: '#d98a78',
        },
        jacket: jacketProfile({
            hem: 0.122, hip: 0.116, waist: 0.1, chest: 0.103, shoulder: 0.098,
            hemDepth: 0.088, waistDepth: 0.07, chestDepth: 0.078, bust: 0.004,
        }),
        jacketFrom: 0.5,
        collarWidth: 0.01,
        legs: GATHERED_LEGS,
        sash: [
            [0.59, 0.6025, '#b8433a'], [0.6025, 0.615, '#e0913a'], [0.615, 0.6275, '#e8c547'],
            [0.6275, 0.64, '#4f9a6a'], [0.64, 0.6525, '#3b6fa6'], [0.6525, 0.665, '#6e4c8a'],
        ],
        neck: 0.025,
        head: {
            scale: 1.08, blush: 0.45, lashes: true, brow: 0.0017, ears: true, hair: 'crown',
            hairAxis: [0, 0.814, -0.581], hairEdge: -0.094,
            crown: { axis: [0, 0.92, -0.39], edge: 0.38, width: 0.017, yarn: '#b03a2e', beads: ['#3aa6a0', '#e07a5f'] },
        },
    }),
    monk: makeLook({
        name: 'Tibetan Monk',
        male: true,
        sleeves: 'bare',
        colors: {
            skin: '#c98a5e', hair: '#3a2a26', scalp: '#b97a50', top: '#e9a92e', cuff: '#e9a92e',
            pants: '#7a2629', band: '#5e1c1f', wrap: '#2f4f9e', collar: '#2f4f9e', shoes: '#26262b',
            accent: '#f2a65e', features: '#3a2a26', mouth: '#9a5a48', blush: '#c47a5c',
        },
        jacket: jacketProfile({
            hem: 0.122, hip: 0.115, waist: 0.104, chest: 0.112, shoulder: 0.112,
            hemDepth: 0.088, waistDepth: 0.074, chestDepth: 0.082, bust: 0,
        }),
        jacketFrom: 0.5,
        legs: GATHERED_LEGS,
        sash: [[0.585, 0.655, '#6b1c22']],
        limbs: 1.04,
        neck: 0.029,
        head: {
            scale: 1.06, blush: 0, lashes: false, brow: 0.0022, ears: true, hair: 'shaved',
            hairAxis: [0, 0.9, -0.435], hairEdge: 0.08,
        },
    }),
}

// --- Colours ---------------------------------------------------------------

function channels(hex) {
    const value = parseInt(hex.slice(1), 16)
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function toHex(values) {
    return `#${values.map((value) => Math.round(Math.min(255, Math.max(0, value))).toString(16).padStart(2, '0')).join('')}`
}

// Darkened by `amount`, or lightened by a negative amount.
export function shadeColor(hex, amount) {
    return toHex(channels(hex).map((value) => (amount >= 0 ? value * (1 - amount) : value + (255 - value) * -amount)))
}

export function mixColor(a, b, share) {
    const from = channels(a)
    const to = channels(b)
    return toHex(from.map((value, index) => value + (to[index] - value) * share))
}

export function flatPalette(colors) {
    const sleeve = colors.sleeve ?? colors.top
    const topShade = shadeColor(colors.top, 0.14)
    return {
        ...colors,
        sleeve,
        sleeveFar: shadeColor(sleeve, 0.2),
        topShade,
        wrap: colors.wrap ?? topShade,
        collar: colors.collar ?? topShade,
        pantsFar: shadeColor(colors.pants, 0.22),
        band: colors.band ?? shadeColor(colors.pants, 0.16),
        cuffFar: shadeColor(colors.cuff, 0.2),
        cuffInside: shadeColor(colors.cuff, 0.35),
        skinFar: shadeColor(colors.skin, 0.1),
        feet: colors.shoes ?? colors.skin,
        feetFar: colors.shoes ? shadeColor(colors.shoes, 0.2) : shadeColor(colors.skin, 0.1),
        scalp: colors.scalp ?? colors.skin,
        shadow: '#3c2d1e',
    }
}

// --- Geometry helpers ------------------------------------------------------

const clamp01 = (value) => Math.min(1, Math.max(0, value))
const lerp = (a, b, share) => a + (b - a) * share

function smooth(edge0, edge1, value) {
    const share = clamp01((value - edge0) / (edge1 - edge0))
    return share * share * (3 - 2 * share)
}

function axis(quat, x, y, z) {
    return new Vector3(x, y, z).applyQuaternion(quat)
}

function circle2(center, radius, count = 20) {
    const points = []
    for (let index = 0; index < count; index += 1) {
        const angle = (index / count) * Math.PI * 2
        points.push({ x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius })
    }
    return points
}

// Convex hull, counter-clockwise with y up.
export function hull(points) {
    const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y)
    if (sorted.length < 3) {
        return sorted
    }
    const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
    const lower = []
    for (const point of sorted) {
        while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 1e-12) {
            lower.pop()
        }
        lower.push(point)
    }
    const upper = []
    for (let index = sorted.length - 1; index >= 0; index -= 1) {
        const point = sorted[index]
        while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 1e-12) {
            upper.pop()
        }
        upper.push(point)
    }
    return lower.slice(0, -1).concat(upper.slice(0, -1))
}

// The part of the convex polygon `subject` inside the convex polygon `clip`
// (both counter-clockwise).
export function clipConvex(subject, clip) {
    let output = subject
    for (let index = 0; index < clip.length && output.length > 0; index += 1) {
        const a = clip[index]
        const b = clip[(index + 1) % clip.length]
        const inside = (p) => (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x) >= 0
        const cut = (p, q) => {
            const dx = q.x - p.x
            const dy = q.y - p.y
            const ex = b.x - a.x
            const ey = b.y - a.y
            const denominator = dx * ey - dy * ex
            const t = denominator === 0 ? 0 : ((a.x - p.x) * ey - (a.y - p.y) * ex) / denominator
            return { x: p.x + dx * t, y: p.y + dy * t }
        }
        const input = output
        output = []
        for (let at = 0; at < input.length; at += 1) {
            const current = input[at]
            const previous = input[(at + input.length - 1) % input.length]
            if (inside(current)) {
                if (!inside(previous)) {
                    output.push(cut(previous, current))
                }
                output.push(current)
            } else if (inside(previous)) {
                output.push(cut(previous, current))
            }
        }
    }
    return output
}

// Two unit vectors perpendicular to the unit vector `direction`.
function perpendiculars(direction) {
    const helper = Math.abs(direction.y) < 0.9 ? new Vector3(0, 1, 0) : new Vector3(1, 0, 0)
    const first = new Vector3().crossVectors(direction, helper).normalize()
    const second = new Vector3().crossVectors(direction, first).normalize()
    return [first, second]
}

// --- Shapes ----------------------------------------------------------------

export function createFlatShapes(look, rig) {
    const H = rig.height
    const colors = flatPalette(look.colors)
    let view = null
    const project = (point) => view.point(point)
    const depth = (point) => view.depth(point)

    // --- Torso ---

    // The spine from the hip centre to the neck base. `frameAt(s)` and
    // `pointAt(s)` give the frame and point s metres above the hip centre;
    // the frame turns from the pelvis's to the chest's.
    function spine(solved) {
        const segments = solved.segments
        const pelvisQuat = segments.pelvis.quat
        const chestQuat = segments.chest.quat
        const hipCenter = segments.pelvis.pos.clone().add(axis(pelvisQuat, 0, -rig.hipDrop, 0))
        const points = [hipCenter, segments.pelvis.pos, segments.spine1.pos, segments.chest.pos, solved.joints.neckBase]
        const starts = [0]
        for (let index = 1; index < points.length; index += 1) {
            starts.push(starts[index - 1] + points[index].distanceTo(points[index - 1]))
        }
        const total = starts[starts.length - 1]
        const turnFrom = (starts[1] + starts[2]) / 2
        const turnTo = (starts[3] + starts[4]) / 2

        function frameAt(s) {
            const quat = new Quaternion().slerpQuaternions(pelvisQuat, chestQuat, smooth(turnFrom, turnTo, s))
            return { x: axis(quat, 1, 0, 0), up: axis(quat, 0, 1, 0), z: axis(quat, 0, 0, 1) }
        }

        function pointAt(s) {
            if (s <= 0) {
                return hipCenter.clone().addScaledVector(axis(pelvisQuat, 0, 1, 0), s)
            }
            if (s >= total) {
                return points[points.length - 1].clone().addScaledVector(axis(chestQuat, 0, 1, 0), s - total)
            }
            let index = 0
            while (s > starts[index + 1]) {
                index += 1
            }
            const share = (s - starts[index]) / (starts[index + 1] - starts[index])
            return points[index].clone().lerp(points[index + 1], share)
        }

        return { hipCenter, frameAt, pointAt }
    }

    // Profile values at a height share, interpolated between rows.
    function profileAt(share) {
        const rows = look.jacket
        if (share <= rows[0][0]) {
            return rows[0].slice(1)
        }
        for (let index = 1; index < rows.length; index += 1) {
            if (share <= rows[index][0]) {
                const a = rows[index - 1]
                const b = rows[index]
                const u = (share - a[0]) / (b[0] - a[0])
                return a.slice(1).map((value, column) => lerp(value, b[column + 1], u))
            }
        }
        return rows[rows.length - 1].slice(1)
    }

    // A ring of the jacket at a height share: its centre, frame and radii.
    function jacketRing(path, share) {
        const [half, halfDepth, forward] = profileAt(share)
        const s = (share - HIP_SHARE) * H
        const frame = path.frameAt(s)
        const center = path.pointAt(s).addScaledVector(frame.z, forward * H)
        return { center, frame, a: half * H, b: halfDepth * H }
    }

    function ringPoint(ring, angle) {
        return ring.center.clone()
            .addScaledVector(ring.frame.x, Math.cos(angle) * ring.a)
            .addScaledVector(ring.frame.z, Math.sin(angle) * ring.b)
    }

    // The hulls of neighbouring rings between two height shares.
    function loft(path, from, to, stations) {
        const rings = []
        for (let station = 0; station <= stations; station += 1) {
            const ring = jacketRing(path, lerp(from, to, station / stations))
            const points = []
            for (let index = 0; index < FLAT_RING_POINTS; index += 1) {
                points.push(project(ringPoint(ring, (index / FLAT_RING_POINTS) * Math.PI * 2)))
            }
            rings.push(points)
        }
        const shapes = []
        for (let index = 0; index < rings.length - 1; index += 1) {
            shapes.push(hull([...rings[index], ...rings[index + 1]]))
        }
        return shapes
    }

    // A point on the jacket's surface: `across` from -1 (her right) to 1
    // (her left) of the half width at a height share, on the front, with
    // how much the surface there faces the viewer.
    function jacketSurface(path, share, across) {
        const ring = jacketRing(path, share)
        const x = across * ring.a
        const z = ring.b * Math.sqrt(Math.max(0, 1 - across * across))
        const point = ring.center.clone().addScaledVector(ring.frame.x, x).addScaledVector(ring.frame.z, z)
        const normal = ring.frame.x.clone().multiplyScalar(x / (ring.a * ring.a))
            .addScaledVector(ring.frame.z, z / (ring.b * ring.b)).normalize()
        return { point: project(point), facing: normal.dot(view.toward) }
    }

    function torso(solved) {
        const path = spine(solved)
        const rows = look.jacket
        const bottom = look.jacketFrom
        const top = rows[rows.length - 1][0]
        // The collar: the top ring all round, with how much each point faces
        // the viewer.
        const ring = jacketRing(path, top)
        const collar = []
        for (let index = 0; index <= FLAT_RING_POINTS; index += 1) {
            const angle = (index / FLAT_RING_POINTS) * Math.PI * 2
            const normal = ring.frame.x.clone().multiplyScalar(Math.cos(angle) / ring.a)
                .addScaledVector(ring.frame.z, Math.sin(angle) / ring.b).normalize()
            collar.push({ point: project(ringPoint(ring, angle)), facing: normal.dot(view.toward) })
        }
        // The wrap line runs from the collar across her chest to her right
        // side at the waist.
        const wrap = []
        for (let step = 0; step <= 16; step += 1) {
            const share = lerp(0.826, 0.6, step / 16)
            wrap.push(jacketSurface(path, share, lerp(0.22, -0.78, smooth(0, 1, step / 16))))
        }
        return {
            body: loft(path, bottom, top, FLAT_TORSO_STATIONS),
            clip: loft(path, bottom, top, FLAT_CLIP_STATIONS),
            hem: loft(path, bottom, bottom + 0.022, 2),
            sash: look.sash.map(([from, to, color]) => ({ shapes: loft(path, from, to, 2), color })),
            collar,
            wrap,
            hipCenter: path.hipCenter,
        }
    }

    // --- Limbs ---

    // The hull of circles round 3D points (projected spheres).
    function spheres(list) {
        const points = []
        for (const [center, radius] of list) {
            points.push(...circle2(project(center), radius))
        }
        return hull(points)
    }

    // A ring of `radius` round the axis `direction` at `center`, projected.
    function ring2(center, direction, radius) {
        const [first, second] = perpendiculars(direction)
        const points = []
        for (let index = 0; index < FLAT_RING_POINTS; index += 1) {
            const angle = (index / FLAT_RING_POINTS) * Math.PI * 2
            points.push(project(center.clone().addScaledVector(first, Math.cos(angle) * radius)
                .addScaledVector(second, Math.sin(angle) * radius)))
        }
        return points
    }

    function leg(side, solved) {
        const joints = solved.joints
        const hip = joints[`hip${side}`]
        const knee = joints[`knee${side}`]
        const ankle = joints[`ankle${side}`]
        const up = knee.clone().sub(ankle).normalize()
        const k = look.limbs * H
        const legs = look.legs
        const thigh = spheres([[hip, legs.thigh[0] * k], [hip.clone().lerp(knee, 0.45), legs.thigh[1] * k],
            [knee, legs.thigh[2] * k]])
        const end = ankle.clone().addScaledVector(up, legs.end[0] * H)
        const calf = knee.clone().lerp(ankle, 0.35)
        const shin = hull([...circle2(project(knee), legs.shin[0] * k), ...circle2(project(calf), legs.shin[1] * k),
            ...ring2(end, up, legs.end[1] * k)])
        const band = hull([...ring2(ankle.clone().addScaledVector(up, legs.band[0] * H), up, legs.band[1] * k),
            ...ring2(end, up, legs.band[2] * k)])
        const ankleSkin = spheres([[ankle, 0.0185 * H], [ankle.clone().addScaledVector(up, 0.045 * H), 0.0175 * H]])
        // The bare foot: heel, ball and toes sit on the sole.
        const footUp = axis(solved.segments[`foot${side}`].quat, 0, 1, 0)
        const toesUp = axis(solved.segments[`toes${side}`].quat, 0, 1, 0)
        const lifted = (point, radius, normal) => [point.clone().addScaledVector(normal, radius), radius]
        const foot = spheres([
            [ankle, 0.02 * H],
            lifted(joints[`heel${side}`], 0.019 * H, footUp),
            lifted(joints[`ball${side}`], 0.021 * H, footUp),
            lifted(joints[`toe${side}`], 0.013 * H, toesUp),
        ])
        return {
            side,
            depth: (depth(hip) + depth(knee) + depth(ankle)) / 3,
            pants: [thigh, shin],
            band,
            skin: [foot, ankleSkin],
        }
    }

    function hand(side, solved) {
        const joints = solved.joints
        const quat = solved.segments[`hand${side}`].quat
        const sign = side === 'L' ? 1 : -1
        const fingers = axis(quat, 0, -1, 0)
        const palmNormal = axis(quat, 0, 0, 1)
        const thumb = view.vector(axis(quat, 1, 0, 0).multiplyScalar(sign))
        const shape = solved.hands[side].shape ?? [1, 0, 0]
        const fist = shape[1] ?? 0
        const hook = shape[2] ?? 0
        const wristPoint = joints[`wrist${side}`]
        const wrist = project(wristPoint)
        const tip = project(wristPoint.clone().addScaledVector(fingers, rig.handLength))
        const reach = 1 - 0.42 * fist - 0.25 * hook
        const along = { x: (tip.x - wrist.x) * reach, y: (tip.y - wrist.y) * reach }
        const at = (share) => ({ x: wrist.x + along.x * share, y: wrist.y + along.y * share })
        const open = Math.abs(palmNormal.dot(view.toward))
        const half = lerp(0.0125, 0.023, open) * H * look.limbs
        const shapes = [hull([
            ...circle2(wrist, half * 0.8),
            ...circle2(at(0.38), half),
            ...circle2(at(0.66), half * 0.95),
            ...circle2(at(0.94), half * (0.68 + 0.25 * fist)),
        ])]
        const thumbSize = Math.hypot(thumb.x, thumb.y)
        if (thumbSize > 0.25 && fist < 0.6) {
            const out = { x: thumb.x / thumbSize, y: thumb.y / thumbSize }
            const base = at(0.32)
            const thumbTip = { x: base.x + out.x * half * 1.15 + along.x * 0.18, y: base.y + out.y * half * 1.15 + along.y * 0.18 }
            shapes.push(hull([...circle2(base, half * 0.5), ...circle2(thumbTip, half * 0.38)]))
        }
        return shapes
    }

    function arm(side, solved) {
        const joints = solved.joints
        const shoulder = joints[`shoulder${side}`]
        const elbow = joints[`elbow${side}`]
        const wrist = joints[`wrist${side}`]
        const toward = wrist.clone().sub(elbow).normalize()
        const k = look.limbs * H
        // The hand points at the viewer when the sleeve opening faces them.
        const out = toward.dot(view.toward)
        const placed = {
            side,
            depth: (depth(shoulder) + depth(elbow) + depth(wrist)) / 3,
            shoulderDepth: depth(shoulder),
            elbowDepth: depth(elbow),
            handFirst: out <= 0,
            hand: hand(side, solved),
        }
        if (look.sleeves === 'bare') {
            const upper = spheres([[shoulder.clone().lerp(elbow, 0.12), 0.024 * k], [shoulder.clone().lerp(elbow, 0.45), 0.022 * k],
                [elbow, 0.019 * k]])
            const forearm = spheres([[elbow, 0.0185 * k], [elbow.clone().lerp(wrist, 0.4), 0.019 * k], [wrist, 0.0165 * k]])
            return { ...placed, bare: true, sleeve: [upper, forearm], cuff: null, opening: null, handFirst: false }
        }
        const upper = spheres([[shoulder.clone().lerp(elbow, 0.12), 0.029 * k], [shoulder.clone().lerp(elbow, 0.45), 0.029 * k],
            [elbow, 0.027 * k]])
        const end = wrist.clone().addScaledVector(toward, -0.014 * H)
        const opening = ring2(end, toward, 0.03 * k)
        const forearm = hull([...circle2(project(elbow), 0.0265 * k), ...opening])
        const cuff = hull([...ring2(wrist.clone().addScaledVector(toward, -0.03 * H), toward, 0.0295 * k), ...opening])
        return { ...placed, bare: false, sleeve: [upper, forearm], cuff, opening: out > 0.3 ? hull(opening) : null }
    }

    // --- Head ---

    // Ellipsoids in the head's frame, metres from the head pivot.
    const headScale = H * look.head.scale
    const part = (center, radii) => ({
        center: new Vector3(center[0] * headScale, center[1] * headScale, center[2] * headScale),
        radii: new Vector3(radii[0] * headScale, radii[1] * headScale, radii[2] * headScale),
    })
    const SKULL = part([0, 0.068, 0.012], [0.058, 0.071, 0.063])
    const SHELL = part([0, 0.068, 0.012], [0.0625, 0.0765, 0.0675])
    const JAW = part([0, 0.043, 0.022], [0.041, 0.034, 0.043])
    const NOSE = part([0, 0.051, 0.0715], [0.0068, 0.009, 0.0068])
    const EARS = [part([0.056, 0.06, 0], [0.0085, 0.014, 0.01]), part([-0.056, 0.06, 0], [0.0085, 0.014, 0.01])]
    const BUN = part([0, 0.135, -0.044], [0.031, 0.028, 0.03])
    const CROP = [
        part([0.004, 0.123, 0.012], [0.054, 0.026, 0.06]),
        part([0.012, 0.121, 0.054], [0.034, 0.014, 0.022]),
        part([0.056, 0.074, 0.012], [0.006, 0.016, 0.012]),
        part([-0.056, 0.074, 0.012], [0.006, 0.016, 0.012]),
    ]
    // The head pivot from the head centre (solve.js places the centre
    // 0.065 up and 0.012 forward of the pivot, × height).
    const CENTER_FROM_PIVOT = new Vector3(0, 0.065 * H, 0.012 * H)

    function headFrame(solved) {
        const quat = solved.segments.head.quat
        const pivot = solved.joints.headCenter.clone().sub(CENTER_FROM_PIVOT.clone().applyQuaternion(quat))
        return { quat, inverse: quat.clone().invert(), pivot }
    }

    // A point of an ellipsoid at unit-sphere direction `u`, in the world.
    function ellipsoidPoint(head, item, u) {
        return new Vector3(item.center.x + item.radii.x * u.x, item.center.y + item.radii.y * u.y,
            item.center.z + item.radii.z * u.z).applyQuaternion(head.quat).add(head.pivot)
    }

    // How much the surface at unit-sphere direction `u` faces the viewer.
    function ellipsoidFacing(head, item, u) {
        return new Vector3(u.x / item.radii.x, u.y / item.radii.y, u.z / item.radii.z)
            .applyQuaternion(head.quat).normalize().dot(view.toward)
    }

    // Unit-sphere directions of the ellipsoid's outline as seen: the great
    // circle whose surface normals are square to the view.
    function outlineDirections(head, item) {
        const toward = view.toward.clone().applyQuaternion(head.inverse)
        const w = new Vector3(toward.x / item.radii.x, toward.y / item.radii.y, toward.z / item.radii.z).normalize()
        const [first, second] = perpendiculars(w)
        const directions = []
        for (let index = 0; index < FLAT_OUTLINE_POINTS; index += 1) {
            const angle = (index / FLAT_OUTLINE_POINTS) * Math.PI * 2
            directions.push(first.clone().multiplyScalar(Math.cos(angle)).addScaledVector(second, Math.sin(angle)))
        }
        return directions
    }

    function outline(head, item) {
        return hull(outlineDirections(head, item).map((u) => project(ellipsoidPoint(head, item, u))))
    }

    // The part of the cap u · capAxis > edge of an ellipsoid that the viewer
    // sees: its outline inside the cap and the visible part of the cap's
    // rim. Null when none of it shows.
    function capRegion(head, item, capAxis, edge) {
        const points = []
        for (const u of outlineDirections(head, item)) {
            if (u.dot(capAxis) > edge) {
                points.push(project(ellipsoidPoint(head, item, u)))
            }
        }
        const [first, second] = perpendiculars(capAxis)
        const across = Math.sqrt(Math.max(0, 1 - edge * edge))
        for (let index = 0; index < FLAT_OUTLINE_POINTS; index += 1) {
            const angle = (index / FLAT_OUTLINE_POINTS) * Math.PI * 2
            const u = capAxis.clone().multiplyScalar(edge).addScaledVector(first, Math.cos(angle) * across)
                .addScaledVector(second, Math.sin(angle) * across)
            if (ellipsoidFacing(head, item, u) >= 0) {
                points.push(project(ellipsoidPoint(head, item, u)))
            }
        }
        return points.length >= 3 ? hull(points) : null
    }

    // The visible runs of a circle on an ellipsoid, round `ringAxis` at
    // `edge`, as lines.
    function capRim(head, item, ringAxis, edge) {
        const [first, second] = perpendiculars(ringAxis)
        const across = Math.sqrt(Math.max(0, 1 - edge * edge))
        const runs = []
        let run = []
        for (let index = 0; index <= FLAT_OUTLINE_POINTS; index += 1) {
            const angle = (index / FLAT_OUTLINE_POINTS) * Math.PI * 2
            const u = ringAxis.clone().multiplyScalar(edge).addScaledVector(first, Math.cos(angle) * across)
                .addScaledVector(second, Math.sin(angle) * across)
            if (ellipsoidFacing(head, item, u) > 0.05) {
                run.push(project(ellipsoidPoint(head, item, u)))
            } else {
                if (run.length > 1) {
                    runs.push(run)
                }
                run = []
            }
        }
        if (run.length > 1) {
            runs.push(run)
        }
        return runs
    }

    function centreDepth(head, item) {
        return depth(item.center.clone().applyQuaternion(head.quat).add(head.pivot))
    }

    // A point on the front of an ellipsoid at head-frame x, y (× height),
    // and how much it faces the viewer.
    function onFace(head, x, y, item = SKULL) {
        const local = new Vector3(x * headScale, y * headScale, 0)
        const dx = (local.x - item.center.x) / item.radii.x
        const dy = (local.y - item.center.y) / item.radii.y
        const dz = Math.sqrt(Math.max(0, 1 - dx * dx - dy * dy))
        const u = new Vector3(dx, dy, dz)
        return { world: ellipsoidPoint(head, item, u), facing: ellipsoidFacing(head, item, u) }
    }

    function head(solved, ops) {
        const frame = headFrame(solved)
        const hair = look.head.hair
        const hairAxis = new Vector3(...look.head.hairAxis).normalize()
        const skullDepth = centreDepth(frame, SKULL)
        const inFront = (item) => centreDepth(frame, item) - skullDepth > 0.004 * headScale
        const behind = []
        const front = []
        for (const item of [JAW, NOSE, ...(look.head.ears ? EARS : [])]) {
            ;(inFront(item) ? front : behind).push(outline(frame, item))
        }
        const hasBun = hair === 'bun'
        const bunBehind = hasBun && !inFront(BUN)
        const bun = () => {
            ops.push(fillOp(outline(frame, BUN), colors.hair))
            // The tie round the bun where it meets the head.
            const base = SKULL.center.clone().sub(BUN.center).divide(BUN.radii).normalize()
            for (const run of capRim(frame, BUN, base, 0.58)) {
                ops.push(lineOp(run, colors.accent, 0.0095 * headScale))
            }
        }
        if (bunBehind) {
            bun()
        }
        for (const shape of behind) {
            ops.push(fillOp(shape, colors.skin))
        }
        if (hair === 'shaved') {
            // The bare head, its shaved crown a shade darker.
            ops.push(fillOp(outline(frame, SKULL), colors.skin))
            const scalp = capRegion(frame, SKULL, hairAxis, look.head.hairEdge)
            if (scalp) {
                ops.push(fillOp(scalp, colors.scalp))
            }
        } else {
            ops.push(fillOp(outline(frame, SHELL), colors.hair))
            const face = capRegion(frame, SHELL, hairAxis.clone().negate(), -look.head.hairEdge)
            if (face) {
                ops.push(fillOp(face, colors.skin))
            }
        }
        for (const shape of front) {
            ops.push(fillOp(shape, colors.skin))
        }
        if (look.head.fringe) {
            const fringe = capRegion(frame, SHELL, new Vector3(...look.head.fringe.axis).normalize(), look.head.fringe.edge)
            if (fringe) {
                ops.push(fillOp(fringe, colors.hair))
            }
        }
        if (hair === 'crop') {
            for (const item of CROP) {
                ops.push(fillOp(outline(frame, item), colors.hair))
            }
        }
        if (hair === 'crown') {
            crown(frame, ops)
        }
        if (hasBun && !bunBehind) {
            bun()
        }
        features(frame, ops)
    }

    // Braids wound round the head, red yarn through them, and beads.
    function crown(frame, ops) {
        const spec = look.head.crown
        const ringAxis = new Vector3(...spec.axis).normalize()
        for (const run of capRim(frame, SHELL, ringAxis, spec.edge)) {
            ops.push(lineOp(run, colors.hair, spec.width * headScale))
            ops.push(lineOp(run, spec.yarn, spec.width * 0.3 * headScale))
        }
        const [first, second] = perpendiculars(ringAxis)
        const across = Math.sqrt(Math.max(0, 1 - spec.edge * spec.edge))
        for (let index = 0; index < 10; index += 1) {
            const angle = (index / 10) * Math.PI * 2
            const u = ringAxis.clone().multiplyScalar(spec.edge).addScaledVector(first, Math.cos(angle) * across)
                .addScaledVector(second, Math.sin(angle) * across)
            if (ellipsoidFacing(frame, SHELL, u) > 0.2) {
                const bead = circle2(project(ellipsoidPoint(frame, SHELL, u)), 0.0042 * headScale, 12)
                ops.push(fillOp(hull(bead), spec.beads[index % spec.beads.length]))
            }
        }
    }

    function features(frame, ops) {
        const xAxis = axis(frame.quat, 1, 0, 0)
        const yAxis = axis(frame.quat, 0, 1, 0)
        // An arc on the face, `width` across, bowing by `bow` (down for
        // closed eyes and the mouth, up for brows).
        const arc = (anchor, width, bow) => {
            const points = []
            for (let step = 0; step <= 10; step += 1) {
                const t = step / 5 - 1
                points.push(project(anchor.world.clone().addScaledVector(xAxis, t * width * headScale)
                    .addScaledVector(yAxis, bow * headScale * (1 - t * t))))
            }
            return points
        }
        for (const sign of [1, -1]) {
            const eye = onFace(frame, sign * 0.021, 0.064)
            const alpha = smooth(0.12, 0.35, eye.facing)
            if (alpha <= 0) {
                continue
            }
            if (look.head.blush) {
                const cheek = onFace(frame, sign * 0.03, 0.049)
                const points = []
                for (let step = 0; step < 20; step += 1) {
                    const angle = (step / 20) * Math.PI * 2
                    points.push(project(cheek.world.clone()
                        .addScaledVector(xAxis, Math.cos(angle) * 0.0095 * headScale)
                        .addScaledVector(yAxis, Math.sin(angle) * 0.0065 * headScale)))
                }
                ops.push(fillOp(hull(points), colors.blush, look.head.blush * smooth(0.15, 0.4, cheek.facing)))
            }
            ops.push(lineOp(arc(eye, 0.0095, -0.0034), colors.features, 0.0026 * headScale, alpha))
            if (look.head.lashes) {
                const corner = project(eye.world.clone().addScaledVector(xAxis, sign * 0.0098 * headScale))
                const lash = project(eye.world.clone().addScaledVector(xAxis, sign * 0.0135 * headScale)
                    .addScaledVector(yAxis, -0.0028 * headScale))
                ops.push(lineOp([corner, lash], colors.features, 0.002 * headScale, alpha))
            }
            const brow = onFace(frame, sign * 0.022, 0.085)
            ops.push(lineOp(arc(brow, 0.0105, 0.0022), colors.hair, look.head.brow * headScale, alpha))
        }
        const mouth = onFace(frame, 0, 0.0385, JAW)
        const mouthAlpha = smooth(0.2, 0.45, mouth.facing)
        if (mouthAlpha > 0) {
            ops.push(lineOp(arc(mouth, 0.0068, -0.0018), colors.mouth, 0.0022 * headScale, mouthAlpha))
        }
        const nose = onFace(frame, 0, 0.0455)
        const noseAlpha = smooth(0.3, 0.6, nose.facing) * 0.7
        if (noseAlpha > 0) {
            ops.push(lineOp(arc(nose, 0.0042, -0.0012), colors.mouth, 0.0019 * headScale, noseAlpha))
        }
    }

    function neck(solved) {
        const frame = headFrame(solved)
        const top = frame.pivot.clone().addScaledVector(axis(frame.quat, 0, 1, 0), 0.02 * H)
        return spheres([[solved.joints.neckBase, look.neck * H], [top, look.neck * H * 0.96]])
    }

    function shadow(solved) {
        const joints = solved.joints
        const points3 = [joints.ankleL, joints.ankleR, joints.pelvis]
        const xs = points3.map((point) => point.x)
        const zs = points3.map((point) => point.z)
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2
        const cz = (Math.min(...zs) + Math.max(...zs)) / 2
        const rx = (Math.max(...xs) - Math.min(...xs)) / 2 + 0.24
        const rz = (Math.max(...zs) - Math.min(...zs)) / 2 + 0.2
        const points = []
        for (let step = 0; step < FLAT_OUTLINE_POINTS; step += 1) {
            const angle = (step / FLAT_OUTLINE_POINTS) * Math.PI * 2
            points.push(project(new Vector3(cx + Math.cos(angle) * rx, 0, cz + Math.sin(angle) * rz)))
        }
        return hull(points)
    }

    // --- Operations ---

    function fillOp(points, color, alpha = 1) {
        return { kind: 'fill', points, color, alpha }
    }

    function lineOp(points, color, width, alpha = 1) {
        return { kind: 'line', points, color, width, alpha }
    }

    // The runs of a line whose points face the viewer.
    function facingRuns(points, color, width, ops) {
        let run = []
        for (const point of points) {
            if (point.facing > 0.05) {
                run.push(point.point)
            } else {
                if (run.length > 1) {
                    ops.push(lineOp(run, color, width))
                }
                run = []
            }
        }
        if (run.length > 1) {
            ops.push(lineOp(run, color, width))
        }
    }

    function legOps(item, ops) {
        ops.push(fillOp(item.skin[0], mixColor(colors.feet, colors.feetFar, item.far)))
        ops.push(fillOp(item.skin[1], mixColor(colors.skin, colors.skinFar, item.far)))
        for (const shape of item.pants) {
            ops.push(fillOp(shape, mixColor(colors.pants, colors.pantsFar, item.far)))
        }
        ops.push(fillOp(item.band, mixColor(colors.band, colors.pantsFar, item.far)))
    }

    function armOps(item, ops, torsoClip = null) {
        const skin = mixColor(colors.skin, colors.skinFar, item.far)
        const handOps = () => {
            for (const shape of item.hand) {
                ops.push(fillOp(shape, skin))
            }
        }
        if (item.handFirst) {
            handOps()
        }
        if (torsoClip) {
            // The arm casts a crisp shade on the jacket where it crosses it.
            for (const shape of item.sleeve) {
                const moved = shape.map((point) => ({ x: point.x - 0.0075 * H, y: point.y - 0.01 * H }))
                for (const piece of torsoClip) {
                    const shade = clipConvex(moved, piece)
                    if (shade.length >= 3) {
                        ops.push(fillOp(shade, colors.topShade))
                    }
                }
            }
        }
        for (const shape of item.sleeve) {
            ops.push(fillOp(shape, item.bare ? skin : mixColor(colors.sleeve, colors.sleeveFar, item.far)))
        }
        if (item.cuff) {
            ops.push(fillOp(item.cuff, mixColor(colors.cuff, colors.cuffFar, item.far)))
        }
        if (item.opening) {
            ops.push(fillOp(item.opening, colors.cuffInside))
        }
        if (!item.handFirst) {
            handOps()
        }
    }

    // The frame's paint operations, back to front, for a FlatView.
    function paint(solved, flatView) {
        view = flatView
        const ops = []
        const chestDepth = depth(solved.joints.shoulderCenter)
        const arms = SIDES.map((side) => arm(side, solved))
        const legs = SIDES.map((side) => leg(side, solved))
        // The farther arm and leg take the darker tone, blended as they pass.
        const farShare = (a, b) => smooth(0, 0.07, b - a)
        arms[0].far = farShare(arms[0].shoulderDepth, arms[1].shoulderDepth)
        arms[1].far = farShare(arms[1].shoulderDepth, arms[0].shoulderDepth)
        legs[0].far = farShare(legs[0].depth, legs[1].depth)
        legs[1].far = farShare(legs[1].depth, legs[0].depth)
        const body = torso(solved)
        const pelvisUp = axis(solved.segments.pelvis.quat, 0, 1, 0)
        const seat = spheres([
            [solved.joints.hipL, 0.05 * H * look.limbs],
            [solved.joints.hipR, 0.05 * H * look.limbs],
            [body.hipCenter.clone().addScaledVector(pelvisUp, -0.03 * H), 0.04 * H * look.limbs],
        ])

        ops.push(fillOp(shadow(solved), colors.shadow, 0.13))
        for (const item of arms.filter((candidate) => candidate.depth <= chestDepth - 0.05)) {
            armOps(item, ops)
        }
        ops.push(fillOp(seat, colors.pants))
        for (const item of [...legs].sort((a, b) => a.depth - b.depth)) {
            legOps(item, ops)
        }
        ops.push(fillOp(neck(solved), colors.skin))
        for (const shape of body.body) {
            ops.push(fillOp(shape, colors.top))
        }
        for (const shape of body.hem) {
            ops.push(fillOp(shape, colors.topShade))
        }
        for (const band of body.sash) {
            for (const shape of band.shapes) {
                ops.push(fillOp(shape, band.color))
            }
        }
        facingRuns(body.wrap, colors.wrap, 0.0045 * H, ops)
        facingRuns(body.collar, colors.collar, look.collarWidth * H, ops)
        head(solved, ops)
        const frontArms = arms.filter((candidate) => candidate.depth > chestDepth - 0.05)
            .sort((a, b) => a.elbowDepth - b.elbowDepth)
        for (const item of frontArms) {
            armOps(item, ops, body.clip)
        }
        // A shape whose points all fall in a line has nothing to fill.
        return ops.filter((op) => op.kind !== 'fill' || op.points.length >= 3)
    }

    return { paint, colors }
}
