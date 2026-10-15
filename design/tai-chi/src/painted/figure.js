// A painted figure: cut-out paintings placed over the solved 3D body and
// seen flat from one side, like a paper puppet. Where each painting goes is
// worked out in layout.js; this module draws the pieces as textured meshes
// in an orthographic scene, back to front. Units are metres.

import {
    BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, LinearMipmapLinearFilter, Mesh, MeshBasicMaterial,
    OrthographicCamera, Scene, SRGBColorSpace, TextureLoader,
} from 'three'
import { SHADOW_IMAGE, createPaintedLayout, imageFromSpec, pieceImage, pieceVertices } from './layout.js'

const STRIP_ROWS = 32
const SHOE_COLUMNS = 14

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

    setPoints(points) {
        for (let index = 0; index < points.length; index += 1) {
            this.positions[index * 3] = points[index].x
            this.positions[index * 3 + 1] = points[index].y
            this.positions[index * 3 + 2] = 0
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

// An image with its size, its named points in pixels and its texture.
async function loadImage(loader, base, spec) {
    const texture = await loadTexture(loader, new URL(spec.file, base).href)
    const { file, ...points } = spec
    return { ...imageFromSpec(points, texture.image.width, texture.image.height), texture }
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

// --- Figure ----------------------------------------------------------------

// Grid sizes of the meshes: strips bend along their length, shoes along
// the foot.
const GRIDS = {
    shadowL: [2, 2],
    shadowR: [2, 2],
    shadowBody: [2, 2],
    head: [2, 2],
    torso: [2, STRIP_ROWS],
    armL: [2, STRIP_ROWS],
    armR: [2, STRIP_ROWS],
    handL: [2, 2],
    handR: [2, 2],
    legL: [2, STRIP_ROWS],
    legR: [2, STRIP_ROWS],
    shoeL: [SHOE_COLUMNS, 2],
    shoeR: [SHOE_COLUMNS, 2],
}

export function createPaintedFigure(character, rig) {
    const scene = new Scene()
    const camera = new OrthographicCamera(-1, 1, 1, -1, -10, 10)
    const shadow = shadowTexture()
    const images = { ...character, shadow }
    const placement = createPaintedLayout(character, rig, { torsoRowCount: STRIP_ROWS })
    const pieces = {}
    for (const [name, [columns, rows]] of Object.entries(GRIDS)) {
        pieces[name] = new Piece(scene, columns, rows)
    }

    function update(solved, { yaw, tilt, center, viewHeight, viewCenter, aspect }) {
        const halfHeight = viewHeight / 2
        camera.left = -halfHeight * aspect
        camera.right = halfHeight * aspect
        camera.top = viewCenter + halfHeight
        camera.bottom = viewCenter - halfHeight
        camera.updateProjectionMatrix()

        const frame = placement.layout(solved, { yaw, tilt, center })
        frame.order.forEach((name, index) => {
            const description = frame.pieces[name]
            const piece = pieces[name]
            const image = pieceImage(images, description.image)
            piece.use(image.texture)
            piece.setPoints(pieceVertices(description, image, piece.columns, piece.rows))
            if (description.opacity !== undefined) {
                piece.material.opacity = description.opacity
            }
            piece.commit(index + 1)
        })
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
