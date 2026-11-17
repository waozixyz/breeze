import * as T from 'three'
import { bodyMaterial } from '../../../promo-film/three/src/character-shaders.js'
import { sample } from './timeline.js'

const smooth = x => T.MathUtils.smoothstep(x, 0, 1)
const pulse = t => (Math.sin(t * 2.4) + 1) / 2

function figure(material) {
    const root = new T.Group()
    const sphere = new T.SphereGeometry(1, 16, 12)
    const part = (position, scale) => {
        const mesh = new T.Mesh(sphere, material)
        mesh.position.set(...position)
        mesh.scale.set(...scale)
        root.add(mesh)
        return mesh
    }
    part([0, 0.55, 0], [0.29, 0.47, 0.17])
    part([0, 1.18, 0], [0.20, 0.24, 0.19])
    part([0, 0.04, 0], [0.27, 0.23, 0.17])
    // Nose and closed eyes give the otherwise simple body an unmistakable face.
    part([0, 1.17, 0.19], [0.045, 0.055, 0.06])
    for (const x of [-0.075, 0.075]) {
        const eye = new T.Mesh(sphere, new T.MeshBasicMaterial({ color: '#493f43' }))
        eye.position.set(x, 1.23, 0.177)
        eye.scale.set(0.045, 0.012, 0.016)
        root.add(eye)
    }
    const arms = []
    for (const side of [-1, 1]) {
        part([side * 0.14, -0.53, 0], [0.12, 0.52, 0.12])
        part([side * 0.14, -1.03, 0.07], [0.12, 0.10, 0.21])
        const arm = new T.Group()
        arm.position.set(side * 0.35, 0.84, 0)
        const limb = new T.Mesh(sphere, material)
        limb.position.y = -0.36
        limb.scale.set(0.09, 0.42, 0.09)
        arm.add(limb)
        root.add(arm)
        arms.push(arm)
    }
    root.rotation.x = -Math.PI / 2
    root.position.y = 0.4
    return { root, arms }
}

// Every exercise gets its own scene and deterministic time sampler. No
// accumulated transforms: a scrub produces the same pose as uninterrupted play.
export function createExercise(item) {
    const scene = new T.Scene()
    scene.background = new T.Color('#0b1424')
    scene.fog = new T.Fog('#0b1424', 10, 25)
    const camera = new T.PerspectiveCamera(42, 2, 0.1, 40)
    camera.position.set(4.3, 5.4, 6.3)
    camera.lookAt(0, 0.6, 0)
    const physicalMaterial = bodyMaterial()
    const energyMaterial = bodyMaterial({ astral: true })
    const physical = figure(physicalMaterial)
    const energy = figure(energyMaterial)
    scene.add(physical.root, energy.root)
    const bed = new T.Mesh(new T.BoxGeometry(1.6, 0.16, 3.3), new T.MeshBasicMaterial({ color: '#243349' }))
    bed.position.y = 0.1
    scene.add(bed)
    const grid = new T.GridHelper(18, 24, '#29455c', '#15283c')
    grid.position.y = -0.1
    scene.add(grid)
    const haloMaterial = new T.MeshBasicMaterial({ color: '#84efff', toneMapped: false })
    const point = new T.Mesh(new T.SphereGeometry(0.065, 12, 8), haloMaterial)
    scene.add(point)
    const ring = new T.Mesh(new T.TorusGeometry(0.14, 0.014, 6, 32), haloMaterial)
    ring.rotation.x = -Math.PI / 2
    scene.add(ring)
    const shaft = new T.Group()
    for (let i = 0; i < 9; i += 1) {
        const floor = new T.Mesh(new T.BoxGeometry(3.5, 0.025, 3.5), new T.MeshBasicMaterial({ color: '#29445a', wireframe: true, transparent: true, opacity: 0.35 }))
        shaft.add(floor)
    }
    scene.add(shaft)
    const rope = new T.Mesh(new T.CylinderGeometry(0.025, 0.025, 4, 8), new T.MeshBasicMaterial({ color: '#dac9a3' }))
    rope.position.set(0, 2.5, -0.3)
    scene.add(rope)
    const cordGeometry = new T.BufferGeometry().setFromPoints(Array.from({ length: 25 }, () => new T.Vector3()))
    const cord = new T.Line(cordGeometry, new T.LineBasicMaterial({ color: '#c4f4ff', toneMapped: false }))
    scene.add(cord)
    const current = new T.Group()
    for (let i = 0; i < 14; i += 1) {
        const bead = new T.Mesh(new T.SphereGeometry(0.025, 6, 4), haloMaterial)
        current.add(bead)
    }
    scene.add(current)

    function update(seconds) {
        const state = sample(item, seconds)
        const { time: t, index: i, progress: u } = state
        const id = item.id
        energyMaterial.uniforms.time.value = t
        physicalMaterial.uniforms.time.value = t
        energy.root.position.set(0, 0.43, 0)
        energy.root.rotation.set(-Math.PI / 2, 0, 0)
        energy.arms.forEach(arm => arm.rotation.set(0, 0, 0))
        const isReturn = i >= item.cues.length - (id.includes('current') || id.includes('elevator') ? 2 : 1)
        const fade = isReturn ? 1 - smooth(u) : 1
        energy.root.visible = !id.includes('spin') && !id.includes('elevator') && fade > 0.001
        point.visible = false
        ring.visible = false
        rope.visible = id.includes('rope') && i >= 11 && i < 19
        shaft.visible = id.includes('elevator') && i >= 6 && i < 13
        current.visible = false
        if (shaft.visible) {
            // The shaft rises around the resting observer: felt downward travel.
            const descend = i <= 8 || i === 11
            const offset = descend ? (t % 24) / 24 : 0.5
            shaft.children.forEach((floor, n) => { floor.position.y = (n - 4 + offset) * 0.7 })
        }
        if (id.includes('foundation') && i >= 1 && i < 9) {
            point.visible = true
            ring.visible = true
            if (i < 4) {
                point.position.set(0.39 + 0.055 * Math.cos(t * 8), 0.56, -0.12 + 0.055 * Math.sin(t * 8))
            } else if (i === 4) {
                point.position.set(0.38, 0.55, -0.22 + pulse(t) * 0.45)
            } else {
                point.position.set(i === 5 ? -0.14 : 0.14, 0.54, 1.05 - (t % 3) / 3 * 1.05)
            }
            ring.position.copy(point.position)
            if (i >= 7) {
                current.visible = true
                current.children.forEach((bead, n) => bead.position.set(n % 2 ? -0.14 : 0.14, 0.52, 1.05 - ((t / 3 + n / 14) % 1) * 1.05))
            }
        }
        const circuit = id.includes('current') && i >= 1 && i < 11 || id.includes('rope') && (i === 7 || i === 8) || id.includes('roll') && i === 4
        if (circuit) {
            current.visible = true
            current.children.forEach((bead, n) => {
                const cycle = (t / (i < 4 ? 1.5 : 6) + n / 14) % 1
                const side = n % 2 ? -1 : 1
                let z = 1.05 - cycle * 2.35
                let x = side * 0.14
                if (id.includes('current') && i <= 2) {
                    z = 1.05 - pulse(t + n * 0.12)
                    x = i === 1 ? 0.14 : side * 0.14
                } else if (id.includes('current') && (i === 3 || i === 5)) {
                    x = side * 0.38
                    z = 0.15 - pulse(t + n * 0.12)
                } else if (id.includes('current') && i === 4) {
                    z = 1.05 - cycle * 1.05
                } else if (cycle > 0.5) {
                    z = -1.3 + (cycle - 0.5) * 2.6
                }
                bead.position.set(x, cycle < 0.5 ? 0.40 : 0.65, z)
            })
        }
        if (id.includes('spin') && i >= 4 && i < 14 || id.includes('rope') && i === 9) {
            point.visible = true
            const angle = i < 6 ? 0 : -(t * Math.PI)
            const radius = i < 6 ? 0.5 + pulse(t) * 1.6 : 2.15
            const returning = id.includes('spin') && i === 13 ? 1 - smooth(u) : 1
            point.position.set(Math.sin(angle) * radius * returning, 0.7 + Math.cos(angle) * 0.5, -Math.cos(angle) * radius * returning)
        }
        if (id.includes('rope') && i >= 11) {
            const returning = i === 18 ? 1 - smooth(u) : i >= 19 ? 0 : 1
            const lift = Math.min(1.65, (t - 1320) / 450) * returning
            energy.root.position.y += Math.max(0, lift)
            energy.arms.forEach((arm, n) => {
                arm.rotation.x = -1.5 + Math.sin(t * (i >= 13 ? 7 : 4) + n * Math.PI) * 0.55 * returning
            })
        }
        if (id.includes('roll') && i >= 6) {
            const side = i === 8 ? 1 : -1
            const returning = i === 13 ? 1 - smooth(u) : i >= 14 ? 0 : 1
            const amplitude = i === 6 ? 0.2 : i < 10 ? 0.9 : 1.5
            const roll = (0.5 - 0.5 * Math.cos((t % 8) / 8 * Math.PI * 2)) * returning
            energy.root.position.x = side * roll * amplitude
            energy.root.position.y += roll * 0.35
            energy.root.rotation.y = side * roll * 1.7
        }
        // Keep the silver cord anchored in world space as the double moves.
        cord.visible = energy.root.visible && energy.root.position.distanceTo(physical.root.position) > 0.15
        const from = new T.Vector3(0, 0.57, 0)
        const to = energy.root.position.clone().add(new T.Vector3(0, 0.12, 0))
        const positions = cordGeometry.attributes.position
        for (let n = 0; n < 25; n += 1) {
            const v = n / 24
            const p = from.clone().lerp(to, v)
            p.y -= Math.sin(v * Math.PI) * 0.15
            positions.setXYZ(n, p.x, p.y, p.z)
        }
        positions.needsUpdate = true
        cordGeometry.computeBoundingSphere()
        // In quiet preparation phases a breathing focus marks the body area
        // addressed by the cue, rather than inventing muscular movement.
        if (!point.visible && !current.visible && !rope.visible && !shaft.visible && !isReturn) {
            ring.visible = true
            const z = /Face|face/.test(state.phase) ? -1.18 : /Arms|arms/.test(state.phase) ? -0.45 : /Legs|legs/.test(state.phase) ? 0.65 : -0.45
            ring.position.set(0, 0.66, z)
            ring.scale.setScalar(0.8 + 0.2 * Math.sin(t * Math.PI / 3))
        } else {
            ring.scale.setScalar(1)
        }
        if (isReturn) {
            energy.root.visible = false
            current.visible = false
            point.visible = false
            ring.visible = false
        }
        return state
    }
    return { scene, camera, update }
}
