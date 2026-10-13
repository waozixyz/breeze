// A painted figure: cut-out paintings placed over the solved 3D body and
// seen flat from one side, like a paper puppet.
//
// Every joint is projected onto the picture plane of a camera that looks
// along a view yaw with a slight downward tilt. Arms and legs are painted
// straight and bend along their projected bones; the torso follows the
// projected spine; the head, hands and shoes are rigid drawings picked by
// how each part is turned toward the viewer. Turned views are painted facing
// the image's right and mirrored for the other side.
//
// The pieces are textured meshes in an orthographic scene, drawn back to
// front: back arms, legs, head, torso, front arms. Units are metres.

import {
    BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, LinearMipmapLinearFilter, Mesh, MeshBasicMaterial,
    OrthographicCamera, Scene, SRGBColorSpace, TextureLoader, Vector3,
} from 'three'

const DEG = Math.PI / 180
const VIEWS = ['front', 'threeQuarter', 'side', 'threeQuarterBack', 'back']
const SIDES = ['L', 'R']
// Degrees past a view boundary before the drawing changes, so a part that
// hovers on a boundary does not flicker between two drawings.
const VIEW_HYSTERESIS = 5
const STRIP_ROWS = 32
const SHOE_COLUMNS = 14
const UP = new Vector3(0, 1, 0)

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

const v2 = (x, y) => ({ x, y })
const add = (a, b) => v2(a.x + b.x, a.y + b.y)
const sub = (a, b) => v2(a.x - b.x, a.y - b.y)
const scale = (a, k) => v2(a.x * k, a.y * k)
const dot = (a, b) => a.x * b.x + a.y * b.y
const length = (a) => Math.hypot(a.x, a.y)
const lerp2 = (a, b, u) => v2(a.x + (b.x - a.x) * u, a.y + (b.y - a.y) * u)
// The direction rotated a quarter turn clockwise: up becomes right.
const clockwise = (a) => v2(a.y, -a.x)

function unit(a, fallback) {
    const size = length(a)
    return size > 1e-6 ? scale(a, 1 / size) : fallback
}

// --- Drawing pieces --------------------------------------------------------

// A textured mesh of `columns` × `rows` vertices whose positions are set
// every frame. UVs cover the whole image.
class Piece {
    constructor(scene, columns, rows) {
        this.columns = columns
        this.rows = rows
        const count = columns * rows
        this.positions = new Float32Array(count * 3)
        const uvs = new Float32Array(count * 2)
        const indices = []
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                const index = row * columns + column
                uvs[index * 2] = column / (columns - 1)
                uvs[index * 2 + 1] = 1 - row / (rows - 1)
                if (row < rows - 1 && column < columns - 1) {
                    const below = index + columns
                    indices.push(index, below, index + 1, index + 1, below, below + 1)
                }
            }
        }
        const geometry = new BufferGeometry()
        geometry.setAttribute('position', new BufferAttribute(this.positions, 3))
        geometry.setAttribute('uv', new BufferAttribute(uvs, 2))
        geometry.setIndex(indices)
        // Mirrored pieces reverse their winding, so both faces are drawn.
        this.material = new MeshBasicMaterial({ transparent: true, depthTest: false, depthWrite: false, side: DoubleSide })
        this.mesh = new Mesh(geometry, this.material)
        this.mesh.frustumCulled = false
        scene.add(this.mesh)
    }

    use(texture) {
        if (this.material.map !== texture) {
            this.material.map = texture
            this.material.needsUpdate = true
        }
    }

    set(column, row, point) {
        const index = (row * this.columns + column) * 3
        this.positions[index] = point.x
        this.positions[index + 1] = point.y
        this.positions[index + 2] = 0
    }

    // Places the image rigidly: the image point `anchor` (pixels) lands on
    // `at`; one pixel right in the image moves by `xAxis`, one pixel down
    // by `yAxis` (both screen vectors).
    affine(image, anchor, at, xAxis, yAxis) {
        for (let row = 0; row < this.rows; row += 1) {
            for (let column = 0; column < this.columns; column += 1) {
                const px = (column / (this.columns - 1)) * image.width - anchor.x
                const py = (row / (this.rows - 1)) * image.height - anchor.y
                this.set(column, row, add(at, add(scale(xAxis, px), scale(yAxis, py))))
            }
        }
    }

    commit(order, visible = true) {
        this.mesh.renderOrder = order
        this.mesh.visible = visible
        this.mesh.geometry.attributes.position.needsUpdate = true
    }

    dispose() {
        this.mesh.geometry.dispose()
        this.material.dispose()
    }
}

// --- Loading ---------------------------------------------------------------

function loadTexture(loader, url) {
    return new Promise((resolve, reject) => {
        loader.load(url, (texture) => {
            texture.colorSpace = SRGBColorSpace
            texture.minFilter = LinearMipmapLinearFilter
            texture.anisotropy = 4
            resolve(texture)
        }, undefined, () => reject(new Error(`Could not load ${url}`)))
    })
}

// An image with its size and its named points in pixels.
async function loadImage(loader, base, spec) {
    const texture = await loadTexture(loader, new URL(spec.file, base).href)
    const width = texture.image.width
    const height = texture.image.height
    const image = { texture, width, height }
    for (const [key, value] of Object.entries(spec)) {
        if (Array.isArray(value) && value.length === 2 && typeof value[0] === 'number') {
            image[key] = v2(value[0] * width, value[1] * height)
        } else if (key === 'shoulders') {
            image.shoulders = value.map(([x, y]) => v2(x * width, y * height))
        } else if (key !== 'file') {
            image[key] = value
        }
    }
    return image
}

async function loadGroup(loader, base, specs) {
    const group = {}
    for (const [name, spec] of Object.entries(specs)) {
        if (spec && typeof spec === 'object' && spec.file) {
            group[name] = await loadImage(loader, base, spec)
        }
    }
    return group
}

export async function loadCharacter(url) {
    const base = new URL(url, globalThis.location?.href)
    const definition = await (await fetch(base)).json()
    const loader = new TextureLoader()
    return {
        id: definition.id,
        name: definition.name,
        figure: definition.figure,
        head: await loadGroup(loader, base, definition.head.views),
        torso: await loadGroup(loader, base, definition.torso.views),
        arm: await loadImage(loader, base, definition.arm),
        leg: await loadImage(loader, base, definition.leg),
        hands: await loadGroup(loader, base, definition.hands),
        shoes: await loadGroup(loader, base, definition.shoes),
    }
}

function shadowTexture() {
    const size = 128
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
    gradient.addColorStop(0, 'rgba(60, 45, 30, 0.42)')
    gradient.addColorStop(0.55, 'rgba(60, 45, 30, 0.2)')
    gradient.addColorStop(1, 'rgba(60, 45, 30, 0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, size, size)
    const texture = new CanvasTexture(canvas)
    texture.colorSpace = SRGBColorSpace
    return { texture, width: size, height: size }
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

// --- Figure ----------------------------------------------------------------

export function createPaintedFigure(character, rig) {
    const scene = new Scene()
    const camera = new OrthographicCamera(-1, 1, 1, -1, -10, 10)
    const view = new FlatView()
    const memory = {}
    const shadow = shadowTexture()

    const pieces = {
        shadowL: new Piece(scene, 2, 2),
        shadowR: new Piece(scene, 2, 2),
        shadowBody: new Piece(scene, 2, 2),
        head: new Piece(scene, 2, 2),
        torso: new Piece(scene, 2, STRIP_ROWS),
    }
    for (const side of SIDES) {
        pieces[`arm${side}`] = new Piece(scene, 2, STRIP_ROWS)
        pieces[`hand${side}`] = new Piece(scene, 2, 2)
        pieces[`leg${side}`] = new Piece(scene, 2, STRIP_ROWS)
        pieces[`shoe${side}`] = new Piece(scene, SHOE_COLUMNS, 2)
    }
    for (const name of ['shadowL', 'shadowR', 'shadowBody']) {
        pieces[name].use(shadow.texture)
    }

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

    function project(point) {
        return view.point(point)
    }

    // --- Shadows ---
    function placeShadow(piece, center, width, depth, strength) {
        const image = shadow
        const at = project(center)
        const xAxis = v2(width / image.width, 0)
        const yAxis = v2(0, -(depth * Math.sin(Math.max(view.tilt, 4 * DEG)) + 0.012) / image.height)
        piece.affine(image, v2(image.width / 2, image.height / 2), at, xAxis, yAxis)
        piece.material.opacity = strength
    }

    // --- Torso ---
    // The spine from the neck base down to the middle of the hip joints.
    function spinePath(solved) {
        const s = solved.segments
        const hipCenter = s.pelvis.pos.clone().add(new Vector3(0, -rig.hipDrop, 0).applyQuaternion(s.pelvis.quat))
        const points3 = [solved.joints.neckBase, s.chest.pos, s.spine1.pos, s.pelvis.pos, hipCenter]
        const points = points3.map(project)
        const lengths = [0]
        for (let index = 1; index < points3.length; index += 1) {
            lengths.push(lengths[index - 1] + points3[index].distanceTo(points3[index - 1]))
        }
        return { points, lengths, total: lengths[lengths.length - 1] }
    }

    // A point along the projected spine at a share of its real length
    // (below 0 above the neck, beyond 1 below the hips).
    function spineAt(path, share) {
        const { points, lengths, total } = path
        const target = share * total
        let index = 1
        while (index < lengths.length - 1 && lengths[index] < target) {
            index += 1
        }
        const span = lengths[index] - lengths[index - 1] || 1
        const u = (target - lengths[index - 1]) / span
        return lerp2(points[index - 1], points[index], u)
    }

    function placeTorso(solved) {
        const chestForward = axis(solved.segments.chest.quat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(chestForward), memory, 'torso')
        const image = character.torso[choice.name]
        const mirror = choice.mirror ? -1 : 1
        const piece = pieces.torso
        piece.use(image.texture)
        const path = spinePath(solved)
        const span = image.hip.y - image.neck.y
        const centers = []
        for (let row = 0; row < STRIP_ROWS; row += 1) {
            const y = (row / (STRIP_ROWS - 1)) * image.height
            centers.push(spineAt(path, (y - image.neck.y) / span))
        }
        const mapping = []
        for (let row = 0; row < STRIP_ROWS; row += 1) {
            const before = centers[Math.max(0, row - 1)]
            const after = centers[Math.min(STRIP_ROWS - 1, row + 1)]
            // Down the spine; its clockwise normal is the image's right.
            const down = unit(sub(after, before), v2(0, -1))
            const across = scale(clockwise(scale(down, -1)), mirror)
            const y = (row / (STRIP_ROWS - 1)) * image.height
            const share = Math.min(1, Math.max(0, (y - image.neck.y) / span))
            const axisX = image.neck.x + (image.hip.x - image.neck.x) * share
            mapping.push({ center: centers[row], across, axisX })
            piece.set(0, row, add(centers[row], scale(across, (0 - axisX) * torsoScale)))
            piece.set(1, row, add(centers[row], scale(across, (image.width - axisX) * torsoScale)))
        }
        // Image points on the placed torso (for the neck and shoulders).
        const toScreen = (point) => {
            const rowFloat = (point.y / image.height) * (STRIP_ROWS - 1)
            const row = Math.min(STRIP_ROWS - 2, Math.max(0, Math.floor(rowFloat)))
            const u = rowFloat - row
            const a = mapping[row]
            const b = mapping[row + 1]
            const center = lerp2(a.center, b.center, u)
            const across = lerp2(a.across, b.across, u)
            const axisX = a.axisX + (b.axisX - a.axisX) * u
            return add(center, scale(across, (point.x - axisX) * torsoScale))
        }
        return {
            neck: toScreen(image.neck),
            shoulders: image.shoulders.map(toScreen),
        }
    }

    // --- Head ---
    function placeHead(solved, neckAt) {
        const headQuat = solved.segments.head.quat
        const forward = axis(headQuat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(forward), memory, 'head')
        const image = character.head[choice.name]
        const piece = pieces.head
        piece.use(image.texture)
        const up = unit(view.vector(axis(headQuat, 0, 1, 0)), v2(0, 1))
        const right = scale(clockwise(up), choice.mirror ? -1 : 1)
        piece.affine(image, image.neck, neckAt, scale(right, headScale), scale(up, -headScale))
    }

    // --- Limbs ---
    // A straight painted limb bent along root → joint → end on screen.
    // `anterior` is the screen direction the limb's front faces.
    function placeLimb(piece, image, root, joint, end, upperLength, lowerLength, anterior, key) {
        piece.use(image.texture)
        const rootY = image.root.y
        const endY = image.end.y
        const jointY = rootY + (endY - rootY) * (upperLength / (upperLength + lowerLength))
        const pixel = (upperLength + lowerLength) / (endY - rootY)
        const widthScale = pixel * (image.thickness ?? 1)
        const halfWidth = image.texture.image.width * 0.5
        const upper = sub(joint, root)
        const lower = sub(end, joint)
        const upperDir = unit(upper, unit(lower, v2(0, -1)))
        const lowerDir = unit(lower, upperDir)
        // Round the joint over about a limb's half width, less on short
        // (foreshortened) bones.
        const round = Math.min(halfWidth * 0.9, 0.45 * (jointY - rootY), 0.45 * (endY - jointY))
        const before = add(root, scale(upper, (jointY - round - rootY) / (jointY - rootY)))
        const after = add(joint, scale(lower, round / (endY - jointY)))
        const centerAt = (y) => {
            if (y <= jointY - round) {
                return { point: add(root, scale(upper, (y - rootY) / (jointY - rootY))), tangent: upperDir }
            }
            if (y >= jointY + round) {
                return { point: add(joint, scale(lower, (y - jointY) / (endY - jointY))), tangent: lowerDir }
            }
            const u = (y - (jointY - round)) / (2 * round)
            const point = add(add(scale(before, (1 - u) * (1 - u)), scale(joint, 2 * u * (1 - u))), scale(after, u * u))
            const tangent = add(scale(sub(joint, before), 2 * (1 - u)), scale(sub(after, joint), 2 * u))
            return { point, tangent: unit(tangent, upperDir) }
        }
        // The painting's +x is the limb's front when image.anterior is 1.
        const jointNormal = clockwise(scale(unit(add(upperDir, lowerDir), upperDir), -1))
        const flip = stickySign(dot(jointNormal, anterior), memory, key) * (image.anterior ?? 1)
        const axisX = image.root.x
        for (let row = 0; row < STRIP_ROWS; row += 1) {
            const y = (row / (STRIP_ROWS - 1)) * image.height
            const { point, tangent } = centerAt(y)
            const across = scale(clockwise(scale(tangent, -1)), flip)
            piece.set(0, row, add(point, scale(across, (0 - axisX) * widthScale)))
            piece.set(1, row, add(point, scale(across, (image.texture.image.width - axisX) * widthScale)))
        }
    }

    // --- Hands ---
    function placeHand(side, solved) {
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
        const piece = pieces[`hand${side}`]
        piece.use(image.texture)
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
        piece.affine(image, image.wrist, wrist, xStep, yStep)
    }

    // --- Shoes ---
    function placeShoe(side, solved) {
        const footQuat = solved.segments[`foot${side}`].quat
        const toesQuat = solved.segments[`toes${side}`].quat
        const forward = axis(footQuat, 0, 0, 1).setY(0)
        const choice = pickView(view.facing(forward), memory, `shoe${side}`)
        const piece = pieces[`shoe${side}`]
        const mirror = choice.mirror ? -1 : 1
        if (choice.name === 'side') {
            const outward = axis(footQuat, 1, 0, 0).multiplyScalar(sideSign(side))
            const image = outward.dot(view.toward) >= 0 ? character.shoes.outer : character.shoes.inner
            piece.use(image.texture)
            const heel = project(solved.joints[`heel${side}`])
            const ball = project(solved.joints[`ball${side}`])
            const toe = project(solved.joints[`toe${side}`])
            const ballShare = (rig.heelBack + rig.ball) / (rig.heelBack + rig.toeTip)
            const ballX = image.heel.x + (image.toe.x - image.heel.x) * ballShare
            const footUp = view.vector(axis(footQuat, 0, 1, 0))
            const toesUp = view.vector(axis(toesQuat, 0, 1, 0))
            for (let column = 0; column < SHOE_COLUMNS; column += 1) {
                const x = (column / (SHOE_COLUMNS - 1)) * image.texture.image.width
                let base
                let up
                if (x <= ballX) {
                    base = lerp2(heel, ball, (x - image.heel.x) / (ballX - image.heel.x))
                    up = footUp
                } else {
                    base = lerp2(ball, toe, (x - ballX) / (image.toe.x - ballX))
                    up = lerp2(footUp, toesUp, Math.min(1, (x - ballX) / ((image.toe.x - ballX) * 0.5)))
                }
                for (let row = 0; row < 2; row += 1) {
                    const y = row * image.texture.image.height
                    piece.set(column, row, add(base, scale(up, (image.heel.y - y) * shoeScale)))
                }
            }
            return
        }
        const image = character.shoes[choice.name]
        piece.use(image.texture)
        const up = unit(view.vector(axis(footQuat, 0, 1, 0)), v2(0, 1))
        const right = scale(clockwise(up), mirror)
        const ankle = project(solved.joints[`ankle${side}`])
        // Rigid views keep their columns but must line up a shoe grid.
        const columns = SHOE_COLUMNS
        for (let column = 0; column < columns; column += 1) {
            for (let row = 0; row < 2; row += 1) {
                const px = (column / (columns - 1)) * image.width - image.ankle.x
                const py = row * image.height - image.ankle.y
                piece.set(column, row, add(ankle, add(scale(right, px * shoeScale), scale(up, -py * shoeScale))))
            }
        }
    }

    // --- Frame ---
    function update(solved, { yaw, tilt, center, viewHeight, viewCenter, aspect }) {
        view.set(yaw, tilt, center)
        const halfHeight = viewHeight / 2
        camera.left = -halfHeight * aspect
        camera.right = halfHeight * aspect
        camera.top = viewCenter + halfHeight
        camera.bottom = viewCenter - halfHeight
        camera.updateProjectionMatrix()

        const joints = solved.joints
        const depthOf = (names) => names.reduce((sum, name) => sum + view.depth(joints[name]), 0) / names.length
        let order = 0
        const next = () => (order += 1)

        // Shadows on the floor.
        for (const side of SIDES) {
            const ankle = joints[`ankle${side}`]
            const lift = Math.max(0, ankle.y - rig.ankleHeight)
            const strength = Math.max(0, 1 - lift / 0.25) * 0.8
            placeShadow(pieces[`shadow${side}`], new Vector3(ankle.x, 0, ankle.z), 0.32, 0.18, strength)
            pieces[`shadow${side}`].commit(next())
        }
        const pelvis = joints.pelvis
        placeShadow(pieces.shadowBody, new Vector3(pelvis.x, 0, pelvis.z), 0.7, 0.4, 0.55)
        pieces.shadowBody.commit(next())

        const torso = placeTorso(solved)
        const chestDepth = view.depth(joints.shoulderCenter)

        // Arms start at the painted armholes nearest their real shoulders.
        const realShoulders = SIDES.map((side) => project(joints[`shoulder${side}`]))
        const straight = length(sub(realShoulders[0], torso.shoulders[0])) + length(sub(realShoulders[1], torso.shoulders[1]))
        const crossed = length(sub(realShoulders[0], torso.shoulders[1])) + length(sub(realShoulders[1], torso.shoulders[0]))
        const armRoots = straight <= crossed ? torso.shoulders : [torso.shoulders[1], torso.shoulders[0]]

        const arms = SIDES.map((side, index) => {
            const shoulder = joints[`shoulder${side}`]
            const elbow = joints[`elbow${side}`]
            const wrist = joints[`wrist${side}`]
            const middle = shoulder.clone().add(wrist).multiplyScalar(0.5)
            const inside = middle.sub(elbow)
            const chestForward = axis(solved.segments.chest.quat, 0, 0, 1)
            const anterior3 = inside.length() > 0.02 ? inside.normalize() : chestForward
            placeLimb(pieces[`arm${side}`], character.arm, armRoots[index], project(elbow), project(wrist),
                rig.upperArm, rig.foreArm, view.vector(anterior3), `arm${side}`)
            placeHand(side, solved)
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
            placeLimb(pieces[`leg${side}`], character.leg, project(hip), project(knee), project(ankle),
                rig.thigh, rig.shin, view.vector(anterior3), `leg${side}`)
            placeShoe(side, solved)
            return { side, depth: depthOf([`hip${side}`, `knee${side}`, `ankle${side}`]) }
        })

        placeHead(solved, torso.neck)

        for (const arm of arms.filter((candidate) => !candidate.front)) {
            pieces[`arm${arm.side}`].commit(next())
            pieces[`hand${arm.side}`].commit(next())
        }
        for (const leg of [...legs].sort((a, b) => a.depth - b.depth)) {
            pieces[`shoe${leg.side}`].commit(next())
            pieces[`leg${leg.side}`].commit(next())
        }
        pieces.head.commit(next())
        pieces.torso.commit(next())
        const frontArms = arms.filter((candidate) => candidate.front)
            .sort((a, b) => depthOf([`elbow${a.side}`]) - depthOf([`elbow${b.side}`]))
        for (const arm of frontArms) {
            pieces[`arm${arm.side}`].commit(next())
            pieces[`hand${arm.side}`].commit(next())
        }
    }

    return {
        scene,
        camera,
        character,
        update,
        setBackground(color) {
            scene.background = new Color(color)
        },
        render(renderer) {
            renderer.render(scene, camera)
        },
        dispose() {
            for (const piece of Object.values(pieces)) {
                piece?.dispose()
            }
        },
    }
}
