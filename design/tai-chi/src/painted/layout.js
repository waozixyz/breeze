// Where the painted pieces go: the flat placement of a painted figure,
// without textures or meshes, so the studio and exports share it.
//
// Every joint is projected onto the picture plane of a camera that looks
// along a view yaw with a slight downward tilt. Arms and legs are painted
// straight and bend along their projected bones; the torso follows the
// projected spine; the head, hands and shoes are rigid drawings picked by
// how each part is turned toward the viewer. Turned views are painted facing
// the image's right and mirrored for the other side.
//
// `layout` returns one description per piece and the order to draw them,
// back to front. `pieceVertices` turns a description into the corner points
// of a grid over its image. Units are metres; screen y points up.

import { Vector3 } from 'three'

const DEG = Math.PI / 180
const VIEWS = ['front', 'threeQuarter', 'side', 'threeQuarterBack', 'back']
export const SIDES = ['L', 'R']
// Degrees past a view boundary before the drawing changes, so a part that
// hovers on a boundary does not flicker between two drawings.
const VIEW_HYSTERESIS = 5

function sideSign(side) {
    return side === 'L' ? 1 : -1
}

function axis(quat, x, y, z) {
    return new Vector3(x, y, z).applyQuaternion(quat)
}

// --- Flat view -------------------------------------------------------------

// The picture plane: `right` and `up` span the screen, `toward` points at
// the viewer. Screen points are metres from `center` (on the floor).
export class FlatView {
    constructor() {
        this.center = new Vector3()
        this.set(0, 6 * DEG, this.center)
    }

    set(yaw, tilt, center) {
        this.yaw = yaw
        this.tilt = tilt
        this.center.copy(center).setY(0)
        this.toward = new Vector3(Math.sin(yaw) * Math.cos(tilt), Math.sin(tilt), Math.cos(yaw) * Math.cos(tilt))
        this.flatToward = new Vector3(Math.sin(yaw), 0, Math.cos(yaw))
        this.right = new Vector3(Math.cos(yaw), 0, -Math.sin(yaw))
        this.up = new Vector3().crossVectors(this.toward, this.right)
    }

    point(p) {
        const dx = p.x - this.center.x
        const dy = p.y - this.center.y
        const dz = p.z - this.center.z
        return {
            x: dx * this.right.x + dy * this.right.y + dz * this.right.z,
            y: dx * this.up.x + dy * this.up.y + dz * this.up.z,
        }
    }

    vector(v) {
        return { x: v.dot(this.right), y: v.dot(this.up) }
    }

    depth(p) {
        return p.clone().sub(this.center).dot(this.toward)
    }

    // Where a horizontal direction points: 0 at the viewer, +90° to the
    // screen's right, ±180° away.
    facing(direction) {
        return Math.atan2(direction.dot(this.right), direction.dot(this.flatToward))
    }
}

// --- 2D helpers ------------------------------------------------------------

export const v2 = (x, y) => ({ x, y })
export const add = (a, b) => v2(a.x + b.x, a.y + b.y)
export const sub = (a, b) => v2(a.x - b.x, a.y - b.y)
export const scale = (a, k) => v2(a.x * k, a.y * k)
const dot = (a, b) => a.x * b.x + a.y * b.y
export const length = (a) => Math.hypot(a.x, a.y)
export const lerp2 = (a, b, u) => v2(a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u)
// The direction rotated a quarter turn clockwise: up becomes right.
export const clockwise = (a) => v2(a.y, -a.x)

export function unit(a, fallback) {
    const size = length(a)
    return size > 1e-6 ? scale(a, 1 / size) : fallback
}

// --- View choice -----------------------------------------------------------

// The drawing for a part facing `angle` (see FlatView.facing), with
// hysteresis kept in `memory[key]`. Front and back drawings keep their
// last mirroring so they do not flip while facing straight on.
function pickView(angle, memory, key) {
    const degrees = Math.abs(angle) / DEG
    let index = Math.min(4, Math.round(degrees / 45))
    const previous = memory[key]
    if (previous && Math.abs(degrees - previous.index * 45) < 22.5 + VIEW_HYSTERESIS) {
        index = previous.index
    }
    let mirror = angle < 0
    if ((index === 0 || index === 4) && previous && (previous.index === index)) {
        mirror = previous.mirror
    }
    memory[key] = { index, mirror }
    return { name: VIEWS[index], index, mirror }
}

// A sign that keeps its last value while `value` is close to zero.
function stickySign(value, memory, key, dead = 0.08) {
    if (Math.abs(value) > dead || memory[key] === undefined) {
        memory[key] = value >= 0 ? 1 : -1
    }
    return memory[key]
}

// --- Images ----------------------------------------------------------------

// An image description from character.json: its size in pixels and its
// named points converted from fractions to pixels.
export function imageFromSpec(spec, width, height) {
    const image = { width, height }
    for (const [key, value] of Object.entries(spec)) {
        if (Array.isArray(value) && value.length === 2 && typeof value[0] === 'number') {
            image[key] = v2(value[0] * width, value[1] * height)
        } else if (key === 'shoulders') {
            image.shoulders = value.map(([x, y]) => v2(x * width, y * height))
        } else {
            image[key] = value
        }
    }
    return image
}

// The shadow is a soft round gradient drawn on a square image.
export const SHADOW_IMAGE = { width: 128, height: 128 }

// --- Piece vertices ----------------------------------------------------------

// Rigid placement: the image point `anchor` lands on `at`; one pixel right
// in the image moves by `xAxis`, one pixel down by `yAxis`.
function affinePoint(piece, px, py) {
    return add(piece.at, add(scale(piece.xAxis, px - piece.anchor.x), scale(piece.yAxis, py - piece.anchor.y)))
}

// A straight painted limb bent along root → joint → end: the centre of the
// strip at image row `y` and the direction along the limb there.
function limbCenter(piece, image, y) {
    const { root, joint, end } = piece
    const rootY = image.root.y
    const endY = image.end.y
    const jointY = rootY + (endY - rootY) * piece.upperShare
    const halfWidth = image.width * 0.5
    const upper = sub(joint, root)
    const lower = sub(end, joint)
    const upperDir = unit(upper, unit(lower, v2(0, -1)))
    const lowerDir = unit(lower, upperDir)
    // Round the joint over about a limb's half width, less on short
    // (foreshortened) bones.
    const round = Math.min(halfWidth * 0.9, 0.45 * (jointY - rootY), 0.45 * (endY - jointY))
    if (y <= jointY - round) {
        return { point: add(root, scale(upper, (y - rootY) / (jointY - rootY))), tangent: upperDir }
    }
    if (y >= jointY + round) {
        return { point: add(joint, scale(lower, (y - jointY) / (endY - jointY))), tangent: lowerDir }
    }
    const before = add(root, scale(upper, (jointY - round - rootY) / (jointY - rootY)))
    const after = add(joint, scale(lower, round / (endY - jointY)))
    const u = (y - (jointY - round)) / (2 * round)
    const point = add(add(scale(before, (1 - u) * (1 - u)), scale(joint, 2 * u * (1 - u))), scale(after, u * u))
    const tangent = add(scale(sub(joint, before), 2 * (1 - u)), scale(sub(after, joint), 2 * u))
    return { point, tangent: unit(tangent, upperDir) }
}

// The torso's spine path at a share of its real length (below 0 above the
// neck, beyond 1 below the hips).
function spineAt(piece, share) {
    const { points, lengths } = piece
    const total = lengths[lengths.length - 1]
    const target = share * total
    let index = 1
    while (index < lengths.length - 1 && lengths[index] < target) {
        index += 1
    }
    const span = lengths[index] - lengths[index - 1] || 1
    const u = (target - lengths[index - 1]) / span
    return lerp2(points[index - 1], points[index], u)
}

// The torso strip: for each image row, its centre on the spine, the
// direction of the image's +x, and the image x of the spine there.
function torsoRows(piece, image, rows) {
    const span = image.hip.y - image.neck.y
    const centers = []
    for (let row = 0; row < rows; row += 1) {
        const y = (row / (rows - 1)) * image.height
        centers.push(spineAt(piece, (y - image.neck.y) / span))
    }
    const mapping = []
    for (let row = 0; row < rows; row += 1) {
        const before = centers[Math.max(0, row - 1)]
        const after = centers[Math.min(rows - 1, row + 1)]
        // Down the spine; its clockwise normal is the image's right.
        const down = unit(sub(after, before), v2(0, -1))
        const across = scale(clockwise(scale(down, -1)), piece.mirror ? -1 : 1)
        const y = (row / (rows - 1)) * image.height
        const share = Math.min(1, Math.max(0, (y - image.neck.y) / span))
        const axisX = image.neck.x + (image.hip.x - image.neck.x) * share
        mapping.push({ center: centers[row], across, axisX })
    }
    return mapping
}

// Grid points (columns × rows, row by row from the image's top) of a
// piece over its image.
export function pieceVertices(piece, image, columns, rows) {
    const points = []
    if (piece.kind === 'affine') {
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                points.push(affinePoint(piece, (column / (columns - 1)) * image.width, (row / (rows - 1)) * image.height))
            }
        }
        return points
    }
    if (piece.kind === 'limb') {
        const widthScale = piece.pixel * (image.thickness ?? 1)
        const axisX = image.root.x
        for (let row = 0; row < rows; row += 1) {
            const y = (row / (rows - 1)) * image.height
            const { point, tangent } = limbCenter(piece, image, y)
            const across = scale(clockwise(scale(tangent, -1)), piece.flip)
            for (let column = 0; column < columns; column += 1) {
                const x = (column / (columns - 1)) * image.width
                points.push(add(point, scale(across, (x - axisX) * widthScale)))
            }
        }
        return points
    }
    if (piece.kind === 'torso') {
        const mapping = torsoRows(piece, image, rows)
        for (let row = 0; row < rows; row += 1) {
            const { center, across, axisX } = mapping[row]
            for (let column = 0; column < columns; column += 1) {
                const x = (column / (columns - 1)) * image.width
                points.push(add(center, scale(across, (x - axisX) * piece.pixel)))
            }
        }
        return points
    }
    if (piece.kind === 'shoeSide') {
        const ballX = image.heel.x + (image.toe.x - image.heel.x) * piece.ballShare
        for (let row = 0; row < rows; row += 1) {
            const y = (row / (rows - 1)) * image.height
            for (let column = 0; column < columns; column += 1) {
                const x = (column / (columns - 1)) * image.width
                let base
                let up
                if (x <= ballX) {
                    base = lerp2(piece.heel, piece.ball, (x - image.heel.x) / (ballX - image.heel.x))
                    up = piece.footUp
                } else {
                    base = lerp2(piece.ball, piece.toe, (x - ballX) / (image.toe.x - ballX))
                    up = lerp2(piece.footUp, piece.toesUp, Math.min(1, (x - ballX) / ((image.toe.x - ballX) * 0.5)))
                }
                points.push(add(base, scale(up, (image.heel.y - y) * piece.pixel)))
            }
        }
        return points
    }
    throw new Error(`Unknown piece kind ${piece.kind}`)
}

// Image points on a placed torso (for the neck and shoulders).
function torsoPoint(piece, image, point, rows) {
    const mapping = torsoRows(piece, image, rows)
    const rowFloat = (point.y / image.height) * (rows - 1)
    const row = Math.min(rows - 2, Math.max(0, Math.floor(rowFloat)))
    const u = rowFloat - row
    const a = mapping[row]
    const b = mapping[row + 1]
    const center = lerp2(a.center, b.center, u)
    const across = lerp2(a.across, b.across, u)
    const axisX = a.axisX + (b.axisX - a.axisX) * u
    return add(center, scale(across, (point.x - axisX) * piece.pixel))
}

// --- Layout ----------------------------------------------------------------

// `character` holds image descriptions (see imageFromSpec) grouped as in
// character.json: head and torso views, arm, leg, hands and shoes.
// `torsoRows` is how finely the torso strip is sampled when the neck and
// armholes are found on it.
export function createPaintedLayout(character, rig, { torsoRowCount = 32 } = {}) {
    const view = new FlatView()
    let memory = {}

    // Scales in metres per image pixel. The torso maps its neck-to-hip
    // span onto the spine; the head shares the torso's sheet but is drawn
    // to the rig's neck-to-crown height; hands and shoes share one scale
    // per sheet, set by the rig's hand and foot.
    const neckToHip = rig.spine.reduce((sum, part) => sum + part, 0) + rig.hipDrop
    const frontTorso = character.torso.front
    const torsoScale = neckToHip / (frontTorso.hip.y - frontTorso.neck.y)
    const frontHead = character.head.front
    const headScale = (rig.neck + rig.headHeight) / (frontHead.neck.y - (frontHead.crown?.y ?? 0.02 * frontHead.height))
    const palm = character.hands.palm
    const handScale = rig.handLength / length(sub(palm.tip, palm.wrist))
    const outer = character.shoes.outer
    const shoeScale = (rig.heelBack + rig.toeTip) / length(sub(outer.toe, outer.heel))

    const project = (point) => view.point(point)

    // --- Shadows ---
    function shadow(center, width, depth, strength) {
        const image = SHADOW_IMAGE
        return {
            kind: 'affine',
            image: 'shadow',
            at: project(center),
            anchor: v2(image.width / 2, image.height / 2),
            xAxis: v2(width / image.width, 0),
            yAxis: v2(0, -(depth * Math.sin(Math.max(view.tilt, 4 * DEG)) + 0.012) / image.height),
            opacity: strength,
        }
    }

    // --- Torso ---
    // The spine from the neck base down to the middle of the hip joints.
    function torso(solved) {
        const s = solved.segments
        const chestForward = axis(s.chest.quat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(chestForward), memory, 'torso')
        const hipCenter = s.pelvis.pos.clone().add(new Vector3(0, -rig.hipDrop, 0).applyQuaternion(s.pelvis.quat))
        const points3 = [solved.joints.neckBase, s.chest.pos, s.spine1.pos, s.pelvis.pos, hipCenter]
        const lengths = [0]
        for (let index = 1; index < points3.length; index += 1) {
            lengths.push(lengths[index - 1] + points3[index].distanceTo(points3[index - 1]))
        }
        return {
            kind: 'torso',
            image: `torso.${choice.name}`,
            mirror: choice.mirror,
            points: points3.map(project),
            lengths,
            pixel: torsoScale,
        }
    }

    // --- Head ---
    function head(solved, neckAt) {
        const headQuat = solved.segments.head.quat
        const forward = axis(headQuat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(forward), memory, 'head')
        const image = character.head[choice.name]
        const up = unit(view.vector(axis(headQuat, 0, 1, 0)), v2(0, 1))
        const right = scale(clockwise(up), choice.mirror ? -1 : 1)
        return { kind: 'affine', image: `head.${choice.name}`, at: neckAt, anchor: image.neck, xAxis: scale(right, headScale), yAxis: scale(up, -headScale) }
    }

    // --- Limbs ---
    // `anterior` is the screen direction the limb's front faces.
    function limb(imageName, image, root, joint, end, upperLength, lowerLength, anterior, key) {
        const upper = sub(joint, root)
        const lower = sub(end, joint)
        const upperDir = unit(upper, unit(lower, v2(0, -1)))
        const lowerDir = unit(lower, upperDir)
        // The painting's +x is the limb's front when image.anterior is 1.
        const jointNormal = clockwise(scale(unit(add(upperDir, lowerDir), upperDir), -1))
        const flip = stickySign(dot(jointNormal, anterior), memory, key) * (image.anterior ?? 1)
        return {
            kind: 'limb',
            image: imageName,
            root,
            joint,
            end,
            upperShare: upperLength / (upperLength + lowerLength),
            pixel: (upperLength + lowerLength) / (image.end.y - image.root.y),
            flip,
        }
    }

    // --- Hands ---
    function hand(side, solved) {
        const quat = solved.segments[`hand${side}`].quat
        const fingers = axis(quat, 0, -1, 0)
        const palmNormal = axis(quat, 0, 0, 1)
        const thumb = axis(quat, 1, 0, 0).multiplyScalar(sideSign(side))
        const shape = solved.hands[side].shape ?? [1, 0, 0]
        const facing = palmNormal.dot(view.toward)
        let name
        if ((shape[2] ?? 0) > 0.5) {
            name = 'hook'
        } else if ((shape[1] ?? 0) > 0.5) {
            name = Math.abs(facing) > 0.45 ? 'fistFront' : 'fistSide'
        } else {
            const previous = memory[`hand${side}`]
            const limit = (candidate) => (previous === candidate ? 0.27 : 0.35)
            if (facing > limit('palm')) {
                name = 'palm'
            } else if (facing < -limit('back')) {
                name = 'back'
            } else {
                name = 'edge'
            }
        }
        memory[`hand${side}`] = name
        const image = character.hands[name]
        const wrist = project(solved.joints[`wrist${side}`])
        let main = view.vector(fingers)
        const forearm = unit(sub(wrist, project(solved.joints[`elbow${side}`])), v2(0, -1))
        // Fingers pointing at the viewer: lean the drawing along the forearm.
        const reach = length(main)
        if (reach < 0.35) {
            main = lerp2(forearm, unit(main, forearm), reach / 0.35)
        }
        const along = unit(main, forearm)
        const shorten = Math.min(1, Math.max(0.6, reach))
        const target = view.vector(image.across === 'thumb' ? thumb : palmNormal)
        const flip = stickySign(dot(clockwise(along), target), memory, `handFlip${side}`, 0.05) * image.sign
        // Image axes: from the wrist to the tip is "main"; its clockwise
        // normal is "across".
        const imageMain = unit(v2(image.tip.x - image.wrist.x, -(image.tip.y - image.wrist.y)), v2(0, 1))
        const imageAcross = clockwise(imageMain)
        const screenAcross = scale(clockwise(along), flip)
        // Pixel steps in the image (x right, y down) in main/across terms.
        const xStep = add(scale(along, imageMain.x * handScale * shorten), scale(screenAcross, imageAcross.x * handScale))
        const yStep = add(scale(along, -imageMain.y * handScale * shorten), scale(screenAcross, -imageAcross.y * handScale))
        return { kind: 'affine', image: `hands.${name}`, at: wrist, anchor: image.wrist, xAxis: xStep, yAxis: yStep }
    }

    // --- Shoes ---
    function shoe(side, solved) {
        const footQuat = solved.segments[`foot${side}`].quat
        const toesQuat = solved.segments[`toes${side}`].quat
        const forward = axis(footQuat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(forward), memory, `shoe${side}`)
        if (choice.name === 'side') {
            const outward = axis(footQuat, 1, 0, 0).multiplyScalar(sideSign(side))
            const name = outward.dot(view.toward) >= 0 ? 'outer' : 'inner'
            return {
                kind: 'shoeSide',
                image: `shoes.${name}`,
                heel: project(solved.joints[`heel${side}`]),
                ball: project(solved.joints[`ball${side}`]),
                toe: project(solved.joints[`toe${side}`]),
                footUp: view.vector(axis(footQuat, 0, 1, 0)),
                toesUp: view.vector(axis(toesQuat, 0, 1, 0)),
                ballShare: (rig.heelBack + rig.ball) / (rig.heelBack + rig.toeTip),
                pixel: shoeScale,
            }
        }
        const image = character.shoes[choice.name]
        const up = unit(view.vector(axis(footQuat, 0, 1, 0)), v2(0, 1))
        const right = scale(clockwise(up), choice.mirror ? -1 : 1)
        return {
            kind: 'affine',
            image: `shoes.${choice.name}`,
            at: project(solved.joints[`ankle${side}`]),
            anchor: image.ankle,
            xAxis: scale(right, shoeScale),
            yAxis: scale(up, -shoeScale),
        }
    }

    // --- Frame ---
    // The pieces of one frame and the order to draw them, back to front.
    function layout(solved, { yaw, tilt, center }) {
        view.set(yaw, tilt, center)
        const joints = solved.joints
        const depthOf = (names) => names.reduce((sum, name) => sum + view.depth(joints[name]), 0) / names.length
        const pieces = {}
        const order = []

        // Shadows on the floor.
        for (const side of SIDES) {
            const ankle = joints[`ankle${side}`]
            const lift = Math.max(0, ankle.y - rig.ankleHeight)
            const strength = Math.max(0, 1 - lift / 0.25) * 0.8
            pieces[`shadow${side}`] = shadow(new Vector3(ankle.x, 0, ankle.z), 0.32, 0.18, strength)
            order.push(`shadow${side}`)
        }
        const pelvis = joints.pelvis
        pieces.shadowBody = shadow(new Vector3(pelvis.x, 0, pelvis.z), 0.7, 0.4, 0.55)
        order.push('shadowBody')

        pieces.torso = torso(solved)
        const torsoImage = character.torso[pieces.torso.image.slice('torso.'.length)]
        const neckAt = torsoPoint(pieces.torso, torsoImage, torsoImage.neck, torsoRowCount)
        const shoulders = torsoImage.shoulders.map((point) => torsoPoint(pieces.torso, torsoImage, point, torsoRowCount))
        const chestDepth = view.depth(joints.shoulderCenter)

        // Arms start at the painted armholes nearest their real shoulders.
        const realShoulders = SIDES.map((side) => project(joints[`shoulder${side}`]))
        const straight = length(sub(realShoulders[0], shoulders[0])) + length(sub(realShoulders[1], shoulders[1]))
        const crossed = length(sub(realShoulders[0], shoulders[1])) + length(sub(realShoulders[1], shoulders[0]))
        const armRoots = straight <= crossed ? shoulders : [shoulders[1], shoulders[0]]

        const arms = SIDES.map((side, index) => {
            const shoulder = joints[`shoulder${side}`]
            const elbow = joints[`elbow${side}`]
            const wrist = joints[`wrist${side}`]
            const middle = shoulder.clone().add(wrist).multiplyScalar(0.5)
            const inside = middle.sub(elbow)
            const chestForward = axis(solved.segments.chest.quat, 0, 0, 1)
            const anterior3 = inside.length() > 0.02 ? inside.normalize() : chestForward
            pieces[`arm${side}`] = limb('arm', character.arm, armRoots[index], project(elbow), project(wrist),
                rig.upperArm, rig.foreArm, view.vector(anterior3), `arm${side}`)
            pieces[`hand${side}`] = hand(side, solved)
            const depth = depthOf([`shoulder${side}`, `elbow${side}`, `wrist${side}`])
            return { side, front: depth > chestDepth - 0.05 }
        })

        const legs = SIDES.map((side) => {
            const hip = joints[`hip${side}`]
            const knee = joints[`knee${side}`]
            const ankle = joints[`ankle${side}`]
            const middle = hip.clone().add(ankle).multiplyScalar(0.5)
            const outward = knee.clone().sub(middle)
            const footForward = axis(solved.segments[`foot${side}`].quat, 0, 0, 1)
            const anterior3 = outward.length() > 0.02 ? outward.normalize() : footForward
            pieces[`leg${side}`] = limb('leg', character.leg, project(hip), project(knee), project(ankle),
                rig.thigh, rig.shin, view.vector(anterior3), `leg${side}`)
            pieces[`shoe${side}`] = shoe(side, solved)
            return { side, depth: depthOf([`hip${side}`, `knee${side}`, `ankle${side}`]) }
        })

        pieces.head = head(solved, neckAt)

        for (const arm of arms.filter((candidate) => !candidate.front)) {
            order.push(`arm${arm.side}`, `hand${arm.side}`)
        }
        for (const leg of [...legs].sort((a, b) => a.depth - b.depth)) {
            order.push(`shoe${leg.side}`, `leg${leg.side}`)
        }
        order.push('head', 'torso')
        const frontArms = arms.filter((candidate) => candidate.front)
            .sort((a, b) => depthOf([`elbow${a.side}`]) - depthOf([`elbow${b.side}`]))
        for (const arm of frontArms) {
            order.push(`arm${arm.side}`, `hand${arm.side}`)
        }
        return { pieces, order }
    }

    return {
        view,
        layout,
        // Forgets the drawing choices kept for hysteresis, as when playback
        // jumps to another time.
        reset() {
            memory = {}
        },
    }
}

// The image a piece names ('torso.front', 'hands.palm', 'arm', 'shadow').
export function pieceImage(character, name) {
    if (name === 'shadow') {
        return character.shadow ?? SHADOW_IMAGE
    }
    const [group, key] = name.split('.')
    return key ? character[group][key] : character[group]
}
