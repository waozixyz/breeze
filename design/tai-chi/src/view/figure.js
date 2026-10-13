// A figure made of rigid parts, one group per solved segment.
//
// Each style fills the segment groups with meshes built in the segment's
// local frame (see solve.js); `update` copies the solved world transforms.

import {
    BoxGeometry, Group, Mesh, MeshStandardMaterial, SphereGeometry,
} from 'three'
import { ellipsoid, taperedCapsule } from './parts.js'

export const SEGMENTS = [
    'pelvis', 'spine0', 'spine1', 'chest', 'neck', 'head',
    'clavicleL', 'upperArmL', 'foreArmL', 'handL',
    'clavicleR', 'upperArmR', 'foreArmR', 'handR',
    'thighL', 'shinL', 'footL', 'toesL',
    'thighR', 'shinR', 'footR', 'toesR',
]

const STYLES = {}

// Registers a figure style: `build(figure, rig, options)` fills
// figure.groups and may set figure.updateHand(side, group, shape).
export function registerStyle(name, build) {
    STYLES[name] = build
}

export function styleNames() {
    return Object.keys(STYLES)
}

export function createFigure(rig, style = 'mannequin', options = {}) {
    const root = new Group()
    root.name = `figure-${style}`
    const groups = {}
    for (const name of SEGMENTS) {
        const group = new Group()
        group.name = name
        group.matrixAutoUpdate = true
        root.add(group)
        groups[name] = group
    }
    const figure = {
        root,
        groups,
        rig,
        style,
        materials: [],
        hands: {},
        updateHand: null,
        update(solved) {
            for (const name of SEGMENTS) {
                const segment = solved.segments[name]
                if (!segment) {
                    continue
                }
                groups[name].position.copy(segment.pos)
                groups[name].quaternion.copy(segment.quat)
            }
            if (figure.updateHand) {
                figure.updateHand('L', solved.hands.L.shape)
                figure.updateHand('R', solved.hands.R.shape)
            }
            if (figure.afterUpdate) {
                figure.afterUpdate(solved)
            }
        },
        setGhost(opacity) {
            for (const material of figure.materials) {
                material.transparent = true
                material.opacity = opacity
                material.depthWrite = false
            }
            root.traverse((node) => {
                node.castShadow = false
                node.renderOrder = 2
            })
        },
        dispose() {
            root.traverse((node) => {
                if (node.geometry) {
                    node.geometry.dispose()
                }
            })
            for (const material of figure.materials) {
                material.dispose()
            }
        },
    }
    const build = STYLES[style] ?? STYLES.mannequin
    build(figure, rig, options)
    root.traverse((node) => {
        if (node.isMesh) {
            node.castShadow = true
            node.receiveShadow = false
        }
    })
    return figure
}

export function material(figure, color, extra = {}) {
    const made = new MeshStandardMaterial({ color, roughness: 0.75, metalness: 0, ...extra })
    figure.materials.push(made)
    return made
}

export function addMesh(group, geometry, mat, position = [0, 0, 0], rotation = null) {
    const mesh = new Mesh(geometry, mat)
    mesh.position.set(position[0], position[1], position[2])
    if (rotation) {
        mesh.rotation.set(rotation[0], rotation[1], rotation[2])
    }
    group.add(mesh)
    return mesh
}

// A simple hand: palm, a block of fingers that curls at the knuckles, and a
// thumb. Fingers point along -Y, the palm faces +Z.
export function buildHand(figure, side, group, rig, skin, size = 1) {
    const H = rig.height * size
    const thumbSide = side === 'L' ? 1 : -1
    const palm = addMesh(group, new BoxGeometry(0.048 * H, 0.056 * H, 0.016 * H), skin, [0, -0.03 * H, 0])
    palm.geometry.translate(0, 0, 0)
    const knuckles = new Group()
    knuckles.position.set(0, -0.056 * H, 0)
    group.add(knuckles)
    const fingers = new Group()
    knuckles.add(fingers)
    const fingerGeometry = taperedCapsule(0.0075 * H, 0.0065 * H, 0.04 * H, 10)
    for (let index = 0; index < 4; index += 1) {
        const x = (-0.018 + index * 0.012) * H
        const length = [0.86, 1.0, 0.95, 0.75][thumbSide > 0 ? 3 - index : index]
        const finger = addMesh(fingers, fingerGeometry, skin, [x, 0, 0])
        finger.scale.set(1, length, 1)
    }
    const thumbRoot = new Group()
    thumbRoot.position.set(thumbSide * 0.022 * H, -0.012 * H, 0.006 * H)
    group.add(thumbRoot)
    addMesh(thumbRoot, taperedCapsule(0.009 * H, 0.0075 * H, 0.038 * H, 10), skin)
    thumbRoot.rotation.z = thumbSide * 0.55
    figure.hands[side] = { group, knuckles, thumbRoot, palm, thumbSide }
}

export function curlHand(figure, side, shape) {
    const hand = figure.hands[side]
    if (!hand) {
        return
    }
    const fist = shape[1] ?? 0
    const hook = shape[2] ?? 0
    // Open palm: fingers gently curved. Fist: rolled into the palm. Hook:
    // fingertips gathered and pointing down from a bent wrist.
    hand.knuckles.rotation.x = -(0.12 + fist * 1.9 + hook * 0.9)
    hand.knuckles.scale.set(1, 1 - fist * 0.15, 1)
    hand.thumbRoot.rotation.x = -(0.15 + fist * 1.1 + hook * 0.8)
    hand.thumbRoot.rotation.z = hand.thumbSide * (0.55 - fist * 0.35 - hook * 0.45)
    hand.palm.rotation.x = -hook * 0.25
}

// The artist's mannequin: smooth wooden pieces with ball joints.
function buildMannequin(figure, rig) {
    const H = rig.height
    const wood = material(figure, 0xd9b48a, { roughness: 0.6 })
    const joint = material(figure, 0xc29a70, { roughness: 0.55 })
    const face = material(figure, 0xb98c62, { roughness: 0.6 })
    const g = figure.groups

    addMesh(g.pelvis, ellipsoid(0.098 * H, 0.06 * H, 0.068 * H), wood, [0, -0.02 * H, 0])
    addMesh(g.spine0, ellipsoid(0.08 * H, 0.05 * H, 0.058 * H), wood, [0, 0.035 * H, 0])
    addMesh(g.spine1, ellipsoid(0.088 * H, 0.068 * H, 0.062 * H), wood, [0, 0.05 * H, 0.002 * H])
    addMesh(g.chest, ellipsoid(0.104 * H, 0.072 * H, 0.068 * H), wood, [0, 0.055 * H, 0.004 * H])
    addMesh(g.neck, taperedCapsule(0.024 * H, 0.028 * H, 0.05 * H), joint, [0, 0.045 * H, 0])
    addMesh(g.head, ellipsoid(0.055 * H, 0.07 * H, 0.062 * H), wood, [0, 0.07 * H, 0.012 * H])
    addMesh(g.head, new SphereGeometry(0.012 * H, 12, 8), face, [0, 0.062 * H, 0.072 * H])

    for (const side of ['L', 'R']) {
        addMesh(g[`upperArm${side}`], taperedCapsule(0.027 * H, 0.021 * H, rig.upperArm), wood)
        addMesh(g[`upperArm${side}`], new SphereGeometry(0.03 * H, 16, 12), joint)
        addMesh(g[`foreArm${side}`], taperedCapsule(0.021 * H, 0.016 * H, rig.foreArm), wood)
        addMesh(g[`foreArm${side}`], new SphereGeometry(0.022 * H, 16, 12), joint)
        buildHand(figure, side, g[`hand${side}`], rig, wood)
        addMesh(g[`thigh${side}`], taperedCapsule(0.048 * H, 0.032 * H, rig.thigh), wood)
        addMesh(g[`thigh${side}`], new SphereGeometry(0.046 * H, 16, 12), joint)
        addMesh(g[`shin${side}`], taperedCapsule(0.032 * H, 0.021 * H, rig.shin), wood)
        addMesh(g[`shin${side}`], new SphereGeometry(0.033 * H, 16, 12), joint)
        const foot = addMesh(g[`foot${side}`], ellipsoid(0.026 * H, 0.022 * H, 0.065 * H), wood,
            [0, -rig.ankleHeight * 0.55, (rig.ball - rig.heelBack) * 0.45])
        foot.scale.y = 1
        addMesh(g[`foot${side}`], new SphereGeometry(0.022 * H, 12, 10), joint)
        addMesh(g[`toes${side}`], ellipsoid(0.024 * H, 0.012 * H, 0.03 * H), wood,
            [0, 0.012 * H, (rig.toeTip - rig.ball) * 0.4])
    }
    figure.updateHand = (side, shape) => curlHand(figure, side, shape)
}

registerStyle('mannequin', buildMannequin)
