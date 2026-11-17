import * as T from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

const sphere = new T.SphereGeometry(1, 22, 16)
const bone = new T.CylinderGeometry(1, 1, 1, 12)
const up = new T.Vector3(0, 1, 0)

// Independent reclining character. No Tai Chi rig, teacher art or martial pose.
// Static sculpted pieces are merged; shoulders, elbows and palms stay articulated.
export function createFigure(material, { astral = false } = {}) {
    const root = new T.Group()
    const flesh = new T.Group()
    root.add(flesh)
    const details = new T.MeshStandardMaterial({ color: astral ? '#8ce4ff' : '#302b35', roughness: 0.8 })
    const cloth = new T.MeshStandardMaterial({ color: '#596279', roughness: 0.95 })
    function part(position, scale, surface = material, parent = flesh) {
        const mesh = new T.Mesh(sphere, surface)
        mesh.position.set(...position)
        mesh.scale.set(...scale)
        parent.add(mesh)
        return mesh
    }
    const profile = [[0.18, -0.15], [0.25, -0.05], [0.23, 0.10], [0.19, 0.27], [0.22, 0.42], [0.29, 0.62], [0.31, 0.75], [0.25, 0.87], [0.12, 0.92]]
    const torso = new T.Mesh(new T.LatheGeometry(profile.map(([x, y]) => new T.Vector2(x, y)), 32), material)
    torso.scale.z = 0.65
    flesh.add(torso)
    part([0, 0.98, 0], [0.085, 0.14, 0.09])
    part([0, 1.23, 0], [0.175, 0.235, 0.165])
    part([0, 1.12, 0.04], [0.13, 0.12, 0.13])
    part([0, 1.22, 0.155], [0.033, 0.066, 0.045])
    part([0, 1.105, 0.157], [0.045, 0.009, 0.009], details)
    for (const side of [-1, 1]) {
        part([side * 0.174, 1.22, 0], [0.025, 0.063, 0.037])
        part([side * 0.071, 1.27, 0.147], [0.045, 0.008, 0.014], details)
        part([side * 0.075, 1.31, 0.139], [0.05, 0.009, 0.014], details)
        part([side * 0.13, 0.80, 0.12], [0.14, 0.025, 0.035])
        part([side * 0.125, 0.63, 0.08], [0.13, 0.15, 0.075])
    }
    const hair = part([0, 1.335, -0.03], [0.179, 0.145, 0.151], details)
    hair.rotation.x = -0.23
    const arms = []
    const elbows = []
    const hands = []
    const grips = []
    function limb(a, b, radiusX, radiusZ, surface = material, parent = flesh) {
        const start = new T.Vector3(...a)
        const end = new T.Vector3(...b)
        const mesh = new T.Mesh(bone, surface)
        mesh.position.copy(start).add(end).multiplyScalar(0.5)
        mesh.quaternion.setFromUnitVectors(up, end.clone().sub(start).normalize())
        mesh.scale.set(radiusX, start.distanceTo(end), radiusZ)
        parent.add(mesh)
    }
    for (const side of [-1, 1]) {
        const pants = astral ? material : cloth
        part([side * 0.15, -0.17, 0], [0.14, 0.20, 0.14], pants)
        limb([side * 0.15, -0.12, 0], [side * 0.15, -0.65, 0], 0.12, 0.115, pants)
        part([side * 0.15, -0.64, 0.015], [0.10, 0.11, 0.105], pants)
        limb([side * 0.15, -0.65, 0], [side * 0.15, -1.14, 0], 0.076, 0.08, pants)
        part([side * 0.15, -1.12, 0.095], [0.085, 0.08, 0.17])
        for (let toe = 0; toe < 5; toe += 1) {
            part([side * (0.095 + toe * 0.028), -1.14, 0.235 - toe * 0.008], [0.022, 0.028, 0.04])
        }
        const arm = new T.Group()
        arm.position.set(side * 0.30, 0.78, 0)
        flesh.add(arm)
        part([0, 0, 0], [0.095, 0.12, 0.10], material, arm)
        limb([0, -0.04, 0], [side * 0.055, -0.36, 0], 0.073, 0.075, material, arm)
        part([side * 0.055, -0.36, 0], [0.064, 0.07, 0.066], material, arm)
        const elbow = new T.Group()
        elbow.position.set(side * 0.055, -0.36, 0)
        arm.add(elbow)
        limb([0, 0, 0], [side * 0.025, -0.30, 0.02], 0.051, 0.055, material, elbow)
        const hand = new T.Group()
        hand.position.set(side * 0.025, -0.32, 0.02)
        elbow.add(hand)
        part([0, -0.045, 0], [0.069, 0.09, 0.027], material, hand)
        const open = new T.Group()
        const closed = new T.Group()
        hand.add(open, closed)
        closed.visible = false
        for (let digit = 0; digit < 4; digit += 1) {
            const x = -0.045 + digit * 0.03
            const finger = part([x, -0.143, 0], [0.014, 0.054 - Math.abs(digit - 1.3) * 0.007, 0.014], material, open)
            finger.rotation.z = (digit - 1.5) * 0.065
            part([x, -0.112, 0.025], [0.016, 0.032, 0.021], material, closed)
            part([x, -0.122, 0.055], [0.016, 0.018, 0.030], material, closed)
        }
        const thumb = part([side * 0.068, -0.035, 0.006], [0.02, 0.065, 0.02], material, hand)
        thumb.rotation.z = side * 0.55
        arms.push(arm)
        elbows.push(elbow)
        hands.push(hand)
        grips.push({ open, closed })
    }
    if (!astral) part([0, -0.12, 0], [0.275, 0.22, 0.16], cloth)
    function mergePieces(group) {
        const batches = new Map()
        group.updateMatrixWorld(true)
        const inverse = group.matrixWorld.clone().invert()
        for (const child of [...group.children]) {
            if (!child.isMesh || child === torso) continue
            const geometry = child.geometry.clone().applyMatrix4(inverse.clone().multiply(child.matrixWorld))
            if (!batches.has(child.material)) batches.set(child.material, [])
            batches.get(child.material).push(geometry)
            child.removeFromParent()
        }
        for (const [surface, geometries] of batches) {
            group.add(new T.Mesh(mergeGeometries(geometries, false), surface))
            geometries.forEach(geometry => geometry.dispose())
        }
    }
    grips.forEach(({ open, closed }) => {
        mergePieces(open)
        mergePieces(closed)
    })
    hands.forEach(mergePieces)
    elbows.forEach(mergePieces)
    arms.forEach(mergePieces)
    mergePieces(flesh)
    root.rotation.x = -Math.PI / 2
    root.position.y = 0.53
    return { root, arms, elbows, hands, grips, breathe(t) { torso.scale.z = 0.65 + 0.012 * Math.sin(t * Math.PI / 3) } }
}
