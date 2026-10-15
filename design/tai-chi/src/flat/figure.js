// A flat figure: the solved body drawn as flat 2D shapes, like a flat
// vector illustration and like Inbe's flat Sun Salutation characters
// (scripts/render-sun-salutation-flat.py). The solved skeleton is projected
// flat along the view as for the painted figures (FlatView in
// ../painted/layout.js), and every part is drawn on it with Canvas 2D:
//
// - Arms and legs are hulls of circles at their joints and of rings at
//   their cuffs, so they read from any side. Parts of one colour are filled
//   as one path, so they join without seams.
// - The jacket is a loft of rings along the spine. The hulls of
//   neighbouring rings, filled together, give its outline from any side as
//   it turns and bends; a darker hem, collar and wrap line sit on it.
// - The head is ray cast against a few ellipsoids in its own frame (skull,
//   hair, jaw, nose, ears, bun) and coloured flat by zone, so the hairline
//   and bun turn with it. Closed eyes, brows, blush and mouth are strokes
//   placed on its surface.
// - The far arm and leg take a darker tone, and an arm in front casts a
//   crisp shade on the jacket.
//
// Units are metres and screen y points up. The drawing goes to a canvas
// shown on a full-screen quad, so the studio renders and captures it like
// the painted figures.

import {
    CanvasTexture, Color, Mesh, MeshBasicMaterial, OrthographicCamera, PlaneGeometry, Quaternion, Scene,
    SRGBColorSpace, Vector2, Vector3,
} from 'three'
import { FlatView } from '../painted/layout.js'

const SIDES = ['L', 'R']
const RING_POINTS = 24
// Samples per pixel along each axis when the head is ray cast.
const HEAD_SAMPLES = 3
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

// The colours match the flat Sun Salutation characters Jade bun and Indigo
// crop (docs/sun-salutation-flat.json in Inbe). Sizes are × height.
export const FLAT_LOOKS = {
    jadeWoman: {
        name: 'Jade Woman',
        colors: {
            skin: '#f1c7a6', hair: '#2a2238', top: '#3f8f7a', pants: '#2e3d63', cuff: '#2e3d63',
            accent: '#f2a65e', features: '#2a2238', mouth: '#c9806f', blush: '#ec9f8f',
        },
        jacket: jacketProfile({
            hem: 0.134, hip: 0.12, waist: 0.104, chest: 0.105, shoulder: 0.103,
            hemDepth: 0.095, waistDepth: 0.073, chestDepth: 0.079, bust: 0.004,
        }),
        limbs: 1,
        neck: 0.025,
        head: { scale: 1.08, hair: 'bun', blush: 0.5, lashes: true, brow: 0.0016 },
    },
    indigoMan: {
        name: 'Indigo Man',
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
        head: { scale: 1.06, hair: 'crop', blush: 0, lashes: false, brow: 0.0024 },
    },
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
function shade(hex, amount) {
    return toHex(channels(hex).map((value) => (amount >= 0 ? value * (1 - amount) : value + (255 - value) * -amount)))
}

function mixColor(a, b, share) {
    const from = channels(a)
    const to = channels(b)
    return toHex(from.map((value, index) => value + (to[index] - value) * share))
}

function palette(colors) {
    return {
        ...colors,
        topFar: shade(colors.top, 0.2),
        topShade: shade(colors.top, 0.14),
        pantsFar: shade(colors.pants, 0.22),
        pantsShade: shade(colors.pants, 0.16),
        cuffFar: shade(colors.cuff, 0.2),
        cuffInside: shade(colors.cuff, 0.35),
        skinFar: shade(colors.skin, 0.1),
        hairLight: shade(colors.hair, -0.2),
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

function circle2(center, radius, count = 28) {
    const points = []
    for (let index = 0; index < count; index += 1) {
        const angle = (index / count) * Math.PI * 2
        points.push({ x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius })
    }
    return points
}

// Convex hull, counter-clockwise with y up.
function hull(points) {
    const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y)
    if (sorted.length < 3) {
        return sorted
    }
    const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
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
    return lower.slice(0, -1).concat(upper.slice(0, -1))
}

function signedArea(points) {
    let area = 0
    for (let index = 0; index < points.length; index += 1) {
        const a = points[index]
        const b = points[(index + 1) % points.length]
        area += a.x * b.y - b.x * a.y
    }
    return area / 2
}

// Every outline runs the same way, so overlapping parts fill as one.
function oriented(points) {
    return signedArea(points) >= 0 ? points : [...points].reverse()
}

// Two vectors perpendicular to `direction` (a unit Vector3).
function perpendiculars(direction) {
    const helper = Math.abs(direction.y) < 0.9 ? new Vector3(0, 1, 0) : new Vector3(1, 0, 0)
    const first = new Vector3().crossVectors(direction, helper).normalize()
    const second = new Vector3().crossVectors(direction, first).normalize()
    return [first, second]
}

// --- Figure ----------------------------------------------------------------

export function createFlatFigure(look, rig) {
    const H = rig.height
    const colors = palette(look.colors)
    const view = new FlatView()
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    const headCanvas = document.createElement('canvas')
    const headContext = headCanvas.getContext('2d')
    const scene = new Scene()
    const camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1)
    let texture = null
    const material = new MeshBasicMaterial({ depthTest: false, depthWrite: false, toneMapped: false })
    const quad = new Mesh(new PlaneGeometry(2, 2), material)
    quad.frustumCulled = false
    scene.add(quad)
    let background = '#f1ece0'
    let frame = null

    const project = (point) => view.point(point)
    const depth = (point) => view.depth(point)

    // --- Torso ---

    // The spine from the hip centre up to the neck base, with the frame of
    // each piece; `at(s)` gives the point and frame s metres above the hip
    // centre (below it or above the neck the line runs straight on).
    function spine(solved) {
        const segments = solved.segments
        const hipCenter = segments.pelvis.pos.clone().add(axis(segments.pelvis.quat, 0, -rig.hipDrop, 0))
        const points = [hipCenter, segments.pelvis.pos, segments.spine1.pos, segments.chest.pos, solved.joints.neckBase]
        const quats = [segments.pelvis.quat, segments.spine0.quat, segments.spine1.quat, segments.chest.quat]
        const starts = [0]
        for (let index = 1; index < points.length; index += 1) {
            starts.push(starts[index - 1] + points[index].distanceTo(points[index - 1]))
        }
        const middles = quats.map((_, index) => (starts[index] + starts[index + 1]) / 2)
        const total = starts[starts.length - 1]

        function frameAt(s) {
            let quat
            if (s <= middles[0]) {
                quat = quats[0]
            } else if (s >= middles[middles.length - 1]) {
                quat = quats[quats.length - 1]
            } else {
                let index = 0
                while (s > middles[index + 1]) {
                    index += 1
                }
                const share = smooth(middles[index], middles[index + 1], s)
                quat = new Quaternion().slerpQuaternions(quats[index], quats[index + 1], share)
            }
            return { x: axis(quat, 1, 0, 0), up: axis(quat, 0, 1, 0), z: axis(quat, 0, 0, 1) }
        }

        function pointAt(s) {
            if (s <= 0) {
                return hipCenter.clone().addScaledVector(axis(quats[0], 0, 1, 0), s)
            }
            if (s >= total) {
                return points[points.length - 1].clone().addScaledVector(axis(quats[quats.length - 1], 0, 1, 0), s - total)
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
        const frame3 = path.frameAt(s)
        const center = path.pointAt(s).addScaledVector(frame3.z, forward * H)
        return { center, frame: frame3, a: half * H, b: halfDepth * H }
    }

    function ringPoints(ring) {
        const points = []
        for (let index = 0; index < RING_POINTS; index += 1) {
            const angle = (index / RING_POINTS) * Math.PI * 2
            points.push(ring.center.clone()
                .addScaledVector(ring.frame.x, Math.cos(angle) * ring.a)
                .addScaledVector(ring.frame.z, Math.sin(angle) * ring.b))
        }
        return points
    }

    // The union of the hulls of neighbouring rings between two shares.
    function loft(path, from, to, stations) {
        const rings = []
        for (let station = 0; station <= stations; station += 1) {
            rings.push(ringPoints(jacketRing(path, lerp(from, to, station / stations))).map(project))
        }
        const shapes = []
        for (let index = 0; index < rings.length - 1; index += 1) {
            shapes.push(hull([...rings[index], ...rings[index + 1]]))
        }
        return shapes
    }

    // Points on the front of the jacket: `across` from -1 (her right) to 1
    // (her left) of the half width, at a height share, with how much the
    // surface there faces the viewer.
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
        const bottom = rows[0][0]
        const top = rows[rows.length - 1][0]
        const body = loft(path, bottom, top, 30)
        const hem = loft(path, bottom, bottom + 0.022, 2)
        // The collar: the top ring's half that faces the viewer.
        const collar = []
        const ring = jacketRing(path, top)
        for (let index = 0; index <= RING_POINTS; index += 1) {
            const angle = (index / RING_POINTS) * Math.PI * 2
            const normal = ring.frame.x.clone().multiplyScalar(Math.cos(angle) / ring.a)
                .addScaledVector(ring.frame.z, Math.sin(angle) / ring.b).normalize()
            const point = ring.center.clone().addScaledVector(ring.frame.x, Math.cos(angle) * ring.a)
                .addScaledVector(ring.frame.z, Math.sin(angle) * ring.b)
            collar.push({ point: project(point), facing: normal.dot(view.toward) })
        }
        // The wrap line runs from the collar across her chest to her right
        // side at the waist.
        const wrap = []
        for (let step = 0; step <= 16; step += 1) {
            const share = lerp(0.826, 0.6, step / 16)
            wrap.push(jacketSurface(path, share, lerp(0.22, -0.78, smooth(0, 1, step / 16))))
        }
        return { body, hem, collar, wrap, hipCenter: path.hipCenter, path }
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
        for (let index = 0; index < RING_POINTS; index += 1) {
            const angle = (index / RING_POINTS) * Math.PI * 2
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
        const thigh = spheres([[hip, 0.052 * k], [hip.clone().lerp(knee, 0.45), 0.049 * k], [knee, 0.04 * k]])
        const end = ankle.clone().addScaledVector(up, 0.035 * H)
        const calf = knee.clone().lerp(ankle, 0.35)
        const shin = hull([...circle2(project(knee), 0.039 * k), ...circle2(project(calf), 0.0375 * k),
            ...ring2(end, up, 0.034 * k)])
        const band = hull([...ring2(ankle.clone().addScaledVector(up, 0.075 * H), up, 0.0335 * k),
            ...ring2(end, up, 0.0345 * k)])
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
        const palmNormal = axis(quat, 0, 0, 1)
        const thumb = view.vector(axis(quat, 1, 0, 0).multiplyScalar(sign))
        const shape = solved.hands[side].shape ?? [1, 0, 0]
        const fist = shape[1] ?? 0
        const hook = shape[2] ?? 0
        const wrist = project(joints[`wrist${side}`])
        const tip = project(joints[`fingertip${side}`])
        const reach = 1 - 0.42 * fist - 0.25 * hook
        const along = { x: (tip.x - wrist.x) * reach, y: (tip.y - wrist.y) * reach }
        const at = (share) => ({ x: wrist.x + along.x * share, y: wrist.y + along.y * share })
        const open = Math.abs(palmNormal.dot(view.toward))
        const half = lerp(0.0125, 0.023, open) * H * look.limbs
        const points = [
            ...circle2(wrist, half * 0.8),
            ...circle2(at(0.38), half),
            ...circle2(at(0.66), half * 0.95),
            ...circle2(at(0.94), half * (0.68 + 0.25 * fist)),
        ]
        const shapes = [hull(points)]
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
        const upper = spheres([[shoulder.clone().lerp(elbow, 0.12), 0.029 * k], [shoulder.clone().lerp(elbow, 0.45), 0.029 * k],
            [elbow, 0.027 * k]])
        const end = wrist.clone().addScaledVector(toward, -0.014 * H)
        const opening = ring2(end, toward, 0.03 * k)
        const forearm = hull([...circle2(project(elbow), 0.0265 * k), ...opening])
        const cuff = hull([...ring2(wrist.clone().addScaledVector(toward, -0.03 * H), toward, 0.0295 * k), ...opening])
        // The hand points at the viewer when the sleeve opening faces them.
        const out = toward.dot(view.toward)
        return {
            side,
            depth: (depth(shoulder) + depth(elbow) + depth(wrist)) / 3,
            shoulderDepth: depth(shoulder),
            elbowDepth: depth(elbow),
            sleeve: [upper, forearm],
            cuff,
            opening: out > 0.3 ? opening : null,
            handFirst: out <= 0,
            hand: hand(side, solved),
        }
    }

    // --- Head ---

    // Ellipsoids in the head's frame, metres from the head pivot.
    function headParts() {
        const k = H * look.head.scale
        const part = (name, center, radii) => ({
            name,
            center: new Vector3(center[0] * k, center[1] * k, center[2] * k),
            radii: new Vector3(radii[0] * k, radii[1] * k, radii[2] * k),
        })
        const parts = [
            part('skull', [0, 0.068, 0.012], [0.058, 0.071, 0.063]),
            part('hair', [0, 0.068, 0.012], [0.0625, 0.0765, 0.0675]),
            part('jaw', [0, 0.043, 0.022], [0.041, 0.034, 0.043]),
            part('nose', [0, 0.051, 0.0715], [0.0068, 0.009, 0.0068]),
        ]
        if (look.head.hair === 'bun') {
            parts.push(part('bun', [0, 0.135, -0.044], [0.031, 0.028, 0.03]))
        } else {
            parts.push(part('ear', [0.056, 0.06, 0], [0.0085, 0.014, 0.01]))
            parts.push(part('ear', [-0.056, 0.06, 0], [0.0085, 0.014, 0.01]))
            parts.push(part('hairTop', [0.004, 0.123, 0.012], [0.054, 0.026, 0.06]))
            parts.push(part('hairTop', [0.012, 0.121, 0.054], [0.034, 0.014, 0.022]))
            parts.push(part('hairTop', [0.056, 0.074, 0.012], [0.006, 0.016, 0.012]))
            parts.push(part('hairTop', [-0.056, 0.074, 0.012], [0.006, 0.016, 0.012]))
        }
        return parts
    }
    const HEAD = headParts()
    const skull = HEAD[0]
    const bun = HEAD.find((part) => part.name === 'bun')

    // Whether a point on the hair shell (in its unit coordinates) is hair.
    function isHair(u) {
        if (look.head.hair === 'bun') {
            // Pulled back to the bun, with a fringe swept across.
            const cap = u.y * 0.814 - u.z * 0.581 > -0.094
            const fringe = u.z > 0.3 && u.y > 0.36 - 0.2 * u.x
            return cap || fringe
        }
        return u.y * 0.9 - u.z * 0.435 > 0
    }

    // The colour where a ray hits the head, or null.
    function headColor(origin, direction) {
        let nearest = Infinity
        let color = null
        for (const part of HEAD) {
            const q = origin.clone().sub(part.center).divide(part.radii)
            const e = direction.clone().divide(part.radii)
            const a = e.dot(e)
            const b = q.dot(e)
            const c = q.dot(q) - 1
            const disc = b * b - a * c
            if (disc <= 0) {
                continue
            }
            const root = Math.sqrt(disc)
            const hits = part.name === 'hair' ? [(-b - root) / a, (-b + root) / a] : [(-b - root) / a]
            for (const t of hits) {
                if (t <= 0 || t >= nearest) {
                    continue
                }
                const point = origin.clone().addScaledVector(direction, t)
                let hit = null
                if (part.name === 'hair') {
                    const u = point.clone().sub(part.center).divide(part.radii)
                    hit = isHair(u) ? colors.hair : null
                } else if (part.name === 'bun') {
                    const u = point.clone().sub(part.center).divide(part.radii).normalize()
                    const base = skull.center.clone().sub(part.center).divide(part.radii).normalize()
                    const toward = u.dot(base)
                    hit = toward > 0.42 && toward < 0.74 ? colors.accent : colors.hair
                } else if (part.name === 'hairTop') {
                    hit = colors.hair
                } else {
                    hit = colors.skin
                }
                if (hit) {
                    nearest = t
                    color = hit
                    break
                }
            }
        }
        return color
    }

    // A point on the skull's (or jaw's) front surface at head x, y, and how
    // much its surface faces the viewer.
    function onFace(quat, pivot, x, y, part = skull) {
        const k = H * look.head.scale
        const local = new Vector3(x * k, y * k, 0)
        const dx = (local.x - part.center.x) / part.radii.x
        const dy = (local.y - part.center.y) / part.radii.y
        local.z = part.center.z + part.radii.z * Math.sqrt(Math.max(0, 1 - dx * dx - dy * dy))
        const normal = local.clone().sub(part.center).divide(part.radii).divide(part.radii).normalize()
        return {
            local,
            world: local.clone().applyQuaternion(quat).add(pivot),
            facing: normal.applyQuaternion(quat).dot(view.toward),
        }
    }

    function headFeatures(solved) {
        const quat = solved.segments.head.quat
        const pivot = solved.segments.head.pos
        const k = H * look.head.scale
        const xAxis = axis(quat, 1, 0, 0)
        const yAxis = axis(quat, 0, 1, 0)
        const strokes = []
        const fills = []
        // An arc on the face: `width` across, bowing by `bow` (down for
        // closed eyes and the mouth, up for brows).
        const arc = (anchor, width, bow) => {
            const points = []
            for (let step = 0; step <= 10; step += 1) {
                const t = step / 5 - 1
                points.push(project(anchor.world.clone().addScaledVector(xAxis, t * width * k)
                    .addScaledVector(yAxis, bow * k * (1 - t * t))))
            }
            return points
        }
        for (const sign of [1, -1]) {
            const eye = onFace(quat, pivot, sign * 0.021, 0.064)
            const alpha = smooth(0.12, 0.35, eye.facing)
            if (alpha > 0) {
                strokes.push({ points: arc(eye, 0.0095, -0.0034), width: 0.0026 * k, color: colors.features, alpha })
                if (look.head.lashes) {
                    const corner = project(eye.world.clone().addScaledVector(xAxis, sign * 0.0098 * k))
                    const lash = project(eye.world.clone().addScaledVector(xAxis, sign * 0.0135 * k)
                        .addScaledVector(yAxis, -0.0028 * k))
                    strokes.push({ points: [corner, lash], width: 0.002 * k, color: colors.features, alpha })
                }
                const brow = onFace(quat, pivot, sign * 0.022, 0.085)
                strokes.push({ points: arc(brow, 0.0105, 0.0022), width: look.head.brow * k, color: colors.hair, alpha })
                if (look.head.blush) {
                    const cheek = onFace(quat, pivot, sign * 0.03, 0.049)
                    const points = []
                    for (let step = 0; step < 20; step += 1) {
                        const angle = (step / 20) * Math.PI * 2
                        points.push(project(cheek.world.clone()
                            .addScaledVector(xAxis, Math.cos(angle) * 0.0095 * k)
                            .addScaledVector(yAxis, Math.sin(angle) * 0.0065 * k)))
                    }
                    fills.push({ points, color: colors.blush, alpha: look.head.blush * smooth(0.15, 0.4, cheek.facing) })
                }
            }
        }
        const jaw = HEAD.find((part) => part.name === 'jaw')
        const mouth = onFace(quat, pivot, 0, 0.0385, jaw)
        const mouthAlpha = smooth(0.2, 0.45, mouth.facing)
        if (mouthAlpha > 0) {
            strokes.push({ points: arc(mouth, 0.0068, -0.0018), width: 0.0022 * k, color: colors.mouth, alpha: mouthAlpha })
        }
        const nose = onFace(quat, pivot, 0, 0.0455)
        const noseAlpha = smooth(0.3, 0.6, nose.facing) * 0.7
        if (noseAlpha > 0) {
            strokes.push({ points: arc(nose, 0.0042, -0.0012), width: 0.0019 * k, color: colors.mouth, alpha: noseAlpha })
        }
        return { strokes, fills }
    }

    function neck(solved) {
        const base = solved.joints.neckBase
        const top = solved.segments.head.pos.clone().addScaledVector(axis(solved.segments.head.quat, 0, 1, 0), 0.02 * H)
        return spheres([[base, look.neck * H], [top, look.neck * H * 0.96]])
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
        for (let step = 0; step < 40; step += 1) {
            const angle = (step / 40) * Math.PI * 2
            points.push(project(new Vector3(cx + Math.cos(angle) * rx, 0, cz + Math.sin(angle) * rz)))
        }
        return points
    }

    // --- Frame ---

    function layout(solved, { yaw, tilt, center }) {
        view.set(yaw, tilt, center)
        const chestDepth = depth(solved.joints.shoulderCenter)
        const arms = SIDES.map((side) => arm(side, solved))
        const legs = SIDES.map((side) => leg(side, solved))
        // The farther arm and leg take the darker tone, blended as they pass.
        const farShare = (a, b) => smooth(0, 0.07, b - a)
        for (const [list, key] of [[arms, 'shoulderDepth'], [legs, 'depth']]) {
            list[0].far = farShare(list[0][key], list[1][key])
            list[1].far = farShare(list[1][key], list[0][key])
        }
        const hipCenter = spine(solved).hipCenter
        const pelvisUp = axis(solved.segments.pelvis.quat, 0, 1, 0)
        const seat = spheres([
            [solved.joints.hipL, 0.05 * H * look.limbs],
            [solved.joints.hipR, 0.05 * H * look.limbs],
            [hipCenter.clone().addScaledVector(pelvisUp, -0.03 * H), 0.04 * H * look.limbs],
        ])
        return {
            solved,
            shadow: shadow(solved),
            backArms: arms.filter((candidate) => candidate.depth <= chestDepth - 0.05),
            frontArms: arms.filter((candidate) => candidate.depth > chestDepth - 0.05)
                .sort((a, b) => a.elbowDepth - b.elbowDepth),
            legs: [...legs].sort((a, b) => a.depth - b.depth),
            seat,
            neck: neck(solved),
            torso: torso(solved),
            features: headFeatures(solved),
        }
    }

    // --- Drawing ---

    function path(shapes) {
        context.beginPath()
        for (const shape of shapes) {
            if (shape.length < 3) {
                continue
            }
            const points = oriented(shape)
            context.moveTo(points[0].x, points[0].y)
            for (let index = 1; index < points.length; index += 1) {
                context.lineTo(points[index].x, points[index].y)
            }
            context.closePath()
        }
    }

    function fill(shapes, color, alpha = 1) {
        path(shapes)
        context.globalAlpha = alpha
        context.fillStyle = color
        context.fill('nonzero')
        context.globalAlpha = 1
    }

    function stroke(points, color, width, alpha = 1) {
        context.beginPath()
        context.moveTo(points[0].x, points[0].y)
        for (let index = 1; index < points.length; index += 1) {
            context.lineTo(points[index].x, points[index].y)
        }
        context.globalAlpha = alpha
        context.strokeStyle = color
        context.lineWidth = width
        context.lineCap = 'round'
        context.lineJoin = 'round'
        context.stroke()
        context.globalAlpha = 1
    }

    // Strokes the runs of a line whose points face the viewer.
    function strokeFacing(points, color, width) {
        let run = []
        for (const point of points) {
            if (point.facing > 0.05) {
                run.push(point.point)
            } else {
                if (run.length > 1) {
                    stroke(run, color, width)
                }
                run = []
            }
        }
        if (run.length > 1) {
            stroke(run, color, width)
        }
    }

    function drawLeg(item) {
        fill(item.skin, mixColor(colors.skin, colors.skinFar, item.far))
        fill(item.pants, mixColor(colors.pants, colors.pantsFar, item.far))
        fill([item.band], mixColor(colors.pantsShade, colors.pantsFar, item.far))
    }

    function drawArm(item, torsoShapes = null) {
        const skin = mixColor(colors.skin, colors.skinFar, item.far)
        if (item.handFirst) {
            fill(item.hand, skin)
        }
        if (torsoShapes) {
            // The arm casts a crisp shade on the jacket where it crosses it.
            context.save()
            path(torsoShapes)
            context.clip('nonzero')
            const offset = (shape) => shape.map((point) => ({ x: point.x - 0.012, y: point.y - 0.016 }))
            fill(item.sleeve.map(offset), colors.topShade)
            context.restore()
        }
        fill(item.sleeve, mixColor(colors.top, colors.topFar, item.far))
        fill([item.cuff], mixColor(colors.cuff, colors.cuffFar, item.far))
        if (item.opening) {
            fill([item.opening], colors.cuffInside)
        }
        if (!item.handFirst) {
            fill(item.hand, skin)
        }
    }

    function drawTorso(torso) {
        fill(torso.body, colors.top)
        context.save()
        path(torso.body)
        context.clip('nonzero')
        fill(torso.hem, colors.topShade)
        strokeFacing(torso.wrap, colors.topShade, 0.0045 * H)
        strokeFacing(torso.collar, colors.topShade, 0.006 * H)
        context.restore()
    }

    // Ray casts the head into the pixels it covers, `HEAD_SAMPLES`² rays
    // a pixel, and draws it flat onto the frame.
    function drawHead(solved, toPixel, pixelsPerMetre) {
        const quat = solved.segments.head.quat
        const pivot = solved.segments.head.pos
        const inverse = quat.clone().invert()
        const centre = project(solved.joints.headCenter)
        const reach = 0.13 * H * look.head.scale
        const [cx, cy] = toPixel(centre.x, centre.y)
        const radius = reach * pixelsPerMetre
        const left = Math.max(0, Math.floor(cx - radius))
        const top = Math.max(0, Math.floor(cy - radius))
        const right = Math.min(canvas.width, Math.ceil(cx + radius))
        const bottom = Math.min(canvas.height, Math.ceil(cy + radius))
        const width = right - left
        const height = bottom - top
        if (width <= 0 || height <= 0) {
            return
        }
        // Ray origins in the head frame: a point on the picture plane in
        // front of the figure, stepped across the screen.
        const ahead = view.center.clone().addScaledVector(view.toward, 4).sub(pivot).applyQuaternion(inverse)
        const rightStep = view.right.clone().applyQuaternion(inverse)
        const upStep = view.up.clone().applyQuaternion(inverse)
        const direction = view.toward.clone().negate().applyQuaternion(inverse)
        const image = new ImageData(width, height)
        const data = image.data
        const origin = new Vector3()
        const cache = new Map()
        for (let row = 0; row < height; row += 1) {
            for (let column = 0; column < width; column += 1) {
                let red = 0
                let green = 0
                let blue = 0
                let covered = 0
                for (let sy = 0; sy < HEAD_SAMPLES; sy += 1) {
                    for (let sx = 0; sx < HEAD_SAMPLES; sx += 1) {
                        const px = left + column + (sx + 0.5) / HEAD_SAMPLES
                        const py = top + row + (sy + 0.5) / HEAD_SAMPLES
                        const screenX = frame.left + px / pixelsPerMetre
                        const screenY = frame.top - py / pixelsPerMetre
                        origin.copy(ahead).addScaledVector(rightStep, screenX).addScaledVector(upStep, screenY)
                        const color = headColor(origin, direction)
                        if (color) {
                            if (!cache.has(color)) {
                                cache.set(color, channels(color))
                            }
                            const [r, g, b] = cache.get(color)
                            red += r
                            green += g
                            blue += b
                            covered += 1
                        }
                    }
                }
                if (covered > 0) {
                    const index = (row * width + column) * 4
                    data[index] = red / covered
                    data[index + 1] = green / covered
                    data[index + 2] = blue / covered
                    data[index + 3] = (255 * covered) / (HEAD_SAMPLES * HEAD_SAMPLES)
                }
            }
        }
        headCanvas.width = width
        headCanvas.height = height
        headContext.putImageData(image, 0, 0)
        context.save()
        context.setTransform(1, 0, 0, 1, 0, 0)
        context.drawImage(headCanvas, left, top)
        context.restore()
    }

    function draw() {
        const { width, height } = canvas
        context.setTransform(1, 0, 0, 1, 0, 0)
        context.fillStyle = background
        context.fillRect(0, 0, width, height)
        if (!frame) {
            return
        }
        const pixelsPerMetre = height / (frame.top - frame.bottom)
        context.setTransform(pixelsPerMetre, 0, 0, -pixelsPerMetre, -frame.left * pixelsPerMetre, frame.top * pixelsPerMetre)
        const toPixel = (x, y) => [(x - frame.left) * pixelsPerMetre, (frame.top - y) * pixelsPerMetre]
        const item = frame.layout
        fill([item.shadow], 'rgb(60, 45, 30)', 0.13)
        for (const back of item.backArms) {
            drawArm(back)
        }
        fill([item.seat], colors.pants)
        for (const legItem of item.legs) {
            drawLeg(legItem)
        }
        fill([item.neck], colors.skin)
        drawTorso(item.torso)
        drawHead(item.solved, toPixel, pixelsPerMetre)
        for (const shape of item.features.fills) {
            fill([shape.points], shape.color, shape.alpha)
        }
        for (const line of item.features.strokes) {
            stroke(line.points, line.color, line.width, line.alpha)
        }
        for (const front of item.frontArms) {
            drawArm(front, item.torso.body)
        }
    }

    return {
        scene,
        camera,
        character: look,
        update(solved, { yaw, tilt, center, viewHeight, viewCenter, aspect }) {
            const halfHeight = viewHeight / 2
            frame = {
                left: -halfHeight * aspect,
                right: halfHeight * aspect,
                top: viewCenter + halfHeight,
                bottom: viewCenter - halfHeight,
                layout: layout(solved, { yaw, tilt, center }),
            }
        },
        setBackground(color) {
            background = new Color(color).getStyle()
        },
        render(renderer) {
            const size = renderer.getDrawingBufferSize(new Vector2())
            if (canvas.width !== size.x || canvas.height !== size.y || !texture) {
                canvas.width = size.x
                canvas.height = size.y
                texture?.dispose()
                texture = new CanvasTexture(canvas)
                texture.colorSpace = SRGBColorSpace
                material.map = texture
                material.needsUpdate = true
            }
            draw()
            texture.needsUpdate = true
            renderer.render(scene, camera)
        },
        dispose() {
            texture?.dispose()
            material.dispose()
            quad.geometry.dispose()
        },
    }
}
