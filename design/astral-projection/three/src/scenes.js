import * as T from 'three'
import { bodyMaterial } from '../../../promo-film/three/src/character-shaders.js'
import { sample } from './timeline.js'
import { createFigure } from './figure.js'
import { createRoom, palette } from './room.js'
import { aura, filament } from './energy.js'

const smooth = x => T.MathUtils.smoothstep(x, 0, 1)
const cycle = (t, period) => (t % period) / period
const wave = (t, period = 6) => 0.5 - 0.5 * Math.cos(t * Math.PI * 2 / period)
const types = ['foundation', 'current', 'elevator', 'spin', 'rope', 'roll']
const bodyHeight = 0.62

function cameraFrame(kind, index) {
    if (kind === 'foundation' && index >= 1 && index <= 4) return { position: [1.05, 1.42, 1.0], target: [0.35, 0.57, -0.07], name: 'HAND STUDY' }
    if (kind === 'foundation' && index >= 5 && index <= 8) return { position: [2.5, 2.75, 3.3], target: [0, 0.60, 0.45], name: 'UPWARD AWARENESS' }
    if (kind === 'rope' && index >= 11 && index <= 18) return { position: [3.2, 3.3, 5.3], target: [0, 1.7, -0.1], name: 'THE ASCENT' }
    if (kind === 'roll' && index >= 6 && index <= 13) return { position: [0.1, 3.6, 5.5], target: [-0.5, 0.9, 0], name: 'WHOLE BODY ROLL' }
    if (kind === 'spin' && index >= 4 && index <= 13) return { position: [4.0, 4.8, 5.5], target: [0, 0.9, 0], name: 'EXTERIOR AWARENESS' }
    if (kind === 'elevator' && index >= 6 && index <= 12) return { position: [3.7, 2.8, 5.1], target: [0, 0.8, 0], name: 'THE DESCENT' }
    return { position: [3.4, 2.8, 4.3], target: [0, 0.75, 0], name: 'RESTING BODY' }
}

export function createExercise(item, exerciseIndex = 0) {
    const kind = types[exerciseIndex]
    const scene = new T.Scene()
    const camera = new T.PerspectiveCamera(39, 2, 0.08, 65)
    const room = createRoom(scene, exerciseIndex)
    const accent = palette(exerciseIndex)
    const physicalMaterial = bodyMaterial({ accent })
    const energyMaterial = bodyMaterial({ astral: true, accent: new T.Color('#8fcfff').lerp(accent, 0.20) })
    const physical = createFigure(physicalMaterial)
    const energy = createFigure(energyMaterial, { astral: true })
    energy.root.scale.setScalar(1.025)
    scene.add(physical.root, energy.root)
    const focus = aura(accent)
    focus.rotation.x = -Math.PI / 2
    scene.add(focus)
    const chestAura = aura(accent)
    chestAura.rotation.x = -Math.PI / 2
    chestAura.scale.set(1.7, 3.5, 1)
    chestAura.position.set(0, 0.44, 0)
    scene.add(chestAura)
    const point = new T.Mesh(new T.IcosahedronGeometry(0.052, 1), new T.MeshBasicMaterial({ color: accent.clone().multiplyScalar(3), toneMapped: false }))
    scene.add(point)
    const trail = filament(accent, { width: 0.024, segments: 90 })
    scene.add(trail.mesh)
    const pathways = Array.from({ length: 6 }, () => filament(accent, { width: 0.018, segments: 48, opacity: 0.75 }))
    pathways.forEach(path => scene.add(path.mesh))
    const cord = filament(new T.Color('#d4e7ff'), { width: 0.018, segments: 50 })
    scene.add(cord.mesh)
    const elevator = new T.Group()
    const levels = []
    const metal = new T.MeshStandardMaterial({ color: '#29384e', metalness: 0.7, roughness: 0.4 })
    const glow = new T.MeshBasicMaterial({ color: accent.clone().multiplyScalar(1.5), toneMapped: false })
    for (let i = 0; i < 9; i += 1) {
        const level = new T.Group()
        const ring = new T.Mesh(new T.TorusGeometry(2, 0.035, 5, 64), metal)
        ring.rotation.x = Math.PI / 2
        level.add(ring)
        for (const x of [-2, 2]) {
            const marker = new T.Mesh(new T.BoxGeometry(0.07, 0.12, 1.8), glow)
            marker.position.x = x
            level.add(marker)
        }
        elevator.add(level)
        levels.push(level)
    }
    for (const x of [-2.05, 2.05]) {
        const rail = new T.Mesh(new T.BoxGeometry(0.05, 9, 0.05), metal)
        rail.position.set(x, 2, 0)
        elevator.add(rail)
    }
    scene.add(elevator)
    const rope = new T.Group()
    const ropeSurface = new T.MeshStandardMaterial({ color: '#d2c3a6', metalness: 0.25, roughness: 0.70 })
    for (let strand = 0; strand < 3; strand += 1) {
        const points = []
        for (let n = 0; n <= 100; n += 1) {
            const y = n / 100 * 4.2
            const angle = y * 22 + strand / 3 * Math.PI * 2
            points.push(new T.Vector3(Math.cos(angle) * 0.019, y, Math.sin(angle) * 0.019))
        }
        rope.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points), 100, 0.015, 5, false), ropeSurface))
    }
    rope.position.set(0, 0.8, -0.28)
    scene.add(rope)
    const anchor = new T.Mesh(new T.TorusGeometry(0.14, 0.026, 8, 32), new T.MeshStandardMaterial({ color: '#caac70', metalness: 0.9, roughness: 0.3 }))
    anchor.position.set(0, 4.8, -0.28)
    scene.add(anchor)
    const coils = Array.from({ length: 3 }, () => filament(accent, { width: 0.009, opacity: 0.45, segments: 80 }))
    coils.forEach(coil => scene.add(coil.mesh))
    const position = new T.Vector3()
    const look = new T.Vector3()
    let viewName = ''
    let motion = ''

    function update(seconds, { directed = true } = {}) {
        const state = sample(item, seconds)
        const { time: t, index: i, progress: u } = state
        const elapsed = t - state.cue.second
        const last = item.cues.length - 1
        const grounded = i === last || kind === 'current' && i >= 11 || kind === 'elevator' && i >= 13
        const activity = grounded ? 1 - smooth(elapsed / 8) : 1
        room.update(t)
        physical.breathe(t)
        physicalMaterial.uniforms.time.value = t
        energyMaterial.uniforms.time.value = t
        energyMaterial.uniforms.opacity.value = grounded ? 0 : 0.6
        energy.root.position.set(0, 0.54, 0)
        energy.root.rotation.set(-Math.PI / 2, 0, 0)
        energy.root.visible = !grounded && (kind === 'rope' && i >= 11 || kind === 'roll' && i >= 6)
        energy.arms.forEach(arm => arm.rotation.set(0, 0, 0))
        energy.elbows.forEach(elbow => elbow.rotation.set(0, 0, 0))
        energy.hands.forEach(hand => hand.rotation.set(0, 0, 0))
        energy.grips.forEach(({ open, closed }) => {
            open.visible = true
            closed.visible = false
        })
        pathways.forEach(path => { path.mesh.visible = false })
        coils.forEach(coil => { coil.mesh.visible = false })
        point.visible = false
        point.scale.setScalar(kind === 'foundation' ? 0.30 : 1)
        trail.mesh.visible = false
        rope.visible = kind === 'rope' && i >= 11 && i < last
        anchor.visible = rope.visible
        elevator.visible = kind === 'elevator' && i >= 6 && i < 13
        focus.visible = !grounded
        focus.material.uniforms.time.value = t
        focus.material.uniforms.opacity.value = 0.7 * activity
        chestAura.material.uniforms.time.value = t
        chestAura.material.uniforms.opacity.value = (0.12 + wave(t) * 0.10) * activity
        focus.scale.setScalar(0.8 + wave(t, 4) * 0.2)
        focus.position.set(0, bodyHeight + 0.15, /face/i.test(state.phase) ? -1.24 : /legs/i.test(state.phase) ? 0.65 : -0.5)
        motion = grounded ? 'Feel support · breathe · return' : 'Relax the body. Let awareness do the moving.'
        function showPath(n, path, alpha = 1) {
            pathways[n].mesh.visible = true
            pathways[n].update(path, t, alpha * activity)
        }
        function limbStroke(n, side, arm = false, bothDirections = false) {
            showPath(n, (v, p) => {
                const progress = bothDirections ? (1 - Math.cos(v * Math.PI * 2)) / 2 : v
                const drift = 0.018 * Math.sin(v * 28 - t * 3)
                p.set(side * (arm ? 0.39 : 0.15) + drift, bodyHeight + 0.06 + Math.sin(v * Math.PI) * 0.07,
                    arm ? 0.08 - progress * 0.85 : 1.12 - progress * 1.18)
            })
        }
        function fullCircuit() {
            for (let side = 0; side < 2; side += 1) {
                showPath(side, (v, p) => {
                    if (v < 0.5) {
                        const q = v * 2
                        p.set((side ? 1 : -1) * 0.15 * (1 - q * 0.7), bodyHeight + 0.03, 1.12 - q * 2.6)
                    } else {
                        const q = (v - 0.5) * 2
                        p.set((side ? 1 : -1) * 0.055, bodyHeight + 0.28 + Math.sin(q * Math.PI) * 0.08, -1.48 + q * 1.56)
                    }
                })
            }
        }
        if (kind === 'foundation' && i >= 1 && i < last) {
            point.visible = true
            focus.scale.setScalar(i <= 4 ? 0.16 : 0.8)
            focus.material.uniforms.opacity.value = i <= 4 ? 0.25 : 0.55
            if (i < 4) {
                const angle = t * Math.PI * 2 * 1.2
                const path = (v, p) => {
                    const a = angle - v * Math.PI * 1.6
                    p.set(0.438 + Math.cos(a) * 0.025, bodyHeight + 0.025, -0.065 + Math.sin(a) * 0.025)
                }
                path(0, point.position)
                trail.mesh.visible = true
                trail.update(path, t)
                motion = i === 1 ? 'Touch the thumb joint. Follow the remembered sensation.' : 'Small clockwise circles · awareness alone'
            } else if (i === 4) {
                point.position.set(0.438, bodyHeight + 0.025, -0.18 + wave(t, 3) * 0.3)
                limbStroke(0, 1, true, true)
                motion = 'Brush the thumb, then widen toward the wrist.'
            } else {
                const side = i === 5 ? -1 : 1
                point.position.set(side * 0.15, bodyHeight + 0.08, 1.12 - cycle(t, 3) * 1.18)
                limbStroke(0, side)
                if (i >= 7) limbStroke(1, -side)
                motion = 'Toes → ankle → knee → hip. Release and begin again.'
            }
            focus.position.copy(point.position)
        }
        if (kind === 'current' && i >= 1 && i < 11) {
            focus.visible = false
            if (i <= 2) {
                limbStroke(0, 1, false, true)
                if (i === 2) limbStroke(1, -1, false, true)
                motion = 'Foot ↔ hip. Find a comfortable bouncing rhythm.'
            } else if (i === 3 || i === 5) {
                limbStroke(0, 1, true, i === 3)
                limbStroke(1, -1, true, i === 3)
                if (i === 5) {
                    showPath(2, (v, p) => p.set(0.20 * Math.sin(v * Math.PI), bodyHeight + 0.18, -0.75 + v * 0.85))
                    showPath(3, (v, p) => p.set(-0.20 * Math.sin(v * Math.PI), bodyHeight + 0.18, -0.75 + v * 0.85))
                }
                motion = i === 3 ? 'Fingertips ↔ shoulders. The physical arms stay soft.' : 'Through the arms and chest → lower belly'
            } else if (i === 4) {
                limbStroke(0, 1)
                limbStroke(1, -1)
                motion = 'Draw the whole pathway upward into the lower belly.'
            } else {
                fullCircuit()
                motion = cycle(t, 6) < 0.5 ? 'INHALE · feet, legs, spine, crown' : 'EXHALE · crown, face, chest, lower belly'
                focus.visible = true
                focus.position.set(0, bodyHeight + 0.18, cycle(t, 6) < 0.5 ? 1.12 - cycle(t, 6) * 5.2 : -1.48 + (cycle(t, 6) - 0.5) * 3.12)
                focus.scale.setScalar(0.7)
            }
        }
        if (elevator.visible) {
            const moving = i <= 8 || i === 11
            const descent = Math.min(Math.max(t - 720, 0), 360) + Math.max(0, Math.min(t - 1320, 120))
            levels.forEach((level, n) => { level.position.y = ((n * 1.2 + descent * 0.045 + 6) % 10.8) - 3 })
            motion = moving ? 'The walls rise past you. Feel yourself gently descending.' : 'Let the elevator pause. Keep one thread of breath.'
            focus.visible = false
        }
        if (kind === 'spin' && i >= 4 && i < last || kind === 'rope' && i === 9) {
            point.visible = true
            trail.mesh.visible = true
            focus.visible = false
            const returning = kind === 'spin' && i === 13 ? 1 - smooth(u) : 1
            const orbit = i >= 6 || kind === 'rope'
            const path = (v, p) => {
                const angle = -(t - v * 1.7) * Math.PI * 0.8
                if (orbit) p.set(Math.sin(angle) * 2.5 * returning, 1.05 + Math.cos(angle) * 0.8, Math.cos(angle) * 2.5 * returning)
                else p.set(0, 0.8 + wave(t - v, 4) * 1.9, -1.1)
            }
            path(0, point.position)
            trail.update(path, t, returning)
            motion = orbit ? 'Front → right → behind → left. Follow the changing perspective.' : 'A point of awareness touches the surface, then returns.'
        }
        if (kind === 'rope') {
            if (i === 7) {
                limbStroke(0, -1)
                limbStroke(1, 1)
                limbStroke(2, -1, true)
                limbStroke(3, 1, true)
            }
            if (i === 8) fullCircuit()
            if (i >= 11 && i < last) {
                const returning = i === 18 ? 1 - smooth(u) : 1
                const lift = smooth((t - 1320) / 360) * 1.9 * returning
                energy.root.position.y += lift
                // The torso peels out before the legs, then floats level.
                energy.root.rotation.x += Math.sin(smooth((t - 1320) / 360) * Math.PI) * 0.16 * returning
                energyMaterial.uniforms.opacity.value = 0.95
                energy.arms.forEach((arm, n) => {
                    const side = n ? 1 : -1
                    const period = i >= 13 ? 1 : 2
                    const reach = wave(t + n * period / 2, period)
                    const gripping = reach < 0.65 && (i !== 18 || u < 0.8)
                    energy.grips[n].closed.visible = gripping
                    energy.grips[n].open.visible = !gripping
                    const target = new T.Vector3(side * 0.025, 0.28, 0.35 + reach * 0.14)
                    const delta = target.clone().sub(arm.position)
                    const upper = energy.elbows[n].position.length()
                    const lowerRest = new T.Vector3(side * 0.025, -0.38, 0.02)
                    const lower = lowerRest.length()
                    const distance = Math.min(delta.length(), upper + lower - 0.002)
                    const direction = delta.normalize()
                    const bend = new T.Vector3(side, 0, 0)
                    bend.addScaledVector(direction, -bend.dot(direction)).normalize()
                    const cosine = T.MathUtils.clamp((upper * upper + distance * distance - lower * lower) / (2 * upper * distance), -1, 1)
                    const upperDirection = direction.clone().multiplyScalar(cosine).addScaledVector(bend, Math.sqrt(1 - cosine * cosine))
                    arm.quaternion.setFromUnitVectors(energy.elbows[n].position.clone().normalize(), upperDirection)
                    const elbowPoint = arm.position.clone().addScaledVector(upperDirection, upper)
                    const lowerDirection = target.sub(elbowPoint).applyQuaternion(arm.quaternion.clone().invert()).normalize()
                    energy.elbows[n].quaternion.setFromUnitVectors(lowerRest.normalize(), lowerDirection)
                    if (i === 18) {
                        arm.quaternion.slerp(new T.Quaternion(), smooth(u))
                        energy.elbows[n].quaternion.slerp(new T.Quaternion(), smooth(u))
                    }
                })
                motion = i === 18 ? 'Choose to return. Let the double settle back into the body.' : 'Reach. Grip. Pull. Alternate the awareness hands; rise without muscle effort.'
            }
        }
        if (kind === 'roll') {
            if (i === 4) fullCircuit()
            if (i >= 6 && i < last) {
                const side = i === 8 ? 1 : -1
                const returning = i === 13 ? 1 - smooth(u) : 1
                const amplitude = i === 6 ? 0.12 : i < 10 ? 0.85 : 1.65
                const roll = wave(t, 7) * returning
                energy.root.position.x = side * roll * amplitude
                energy.root.position.y += roll * 0.65
                energy.root.rotation.y = side * roll * 2.4
                energyMaterial.uniforms.opacity.value = 0.95
                motion = i === 13 ? 'Return directly. Let the whole body reunite.' : `Roll ${side < 0 ? 'left' : 'right'} as one shape. Head, chest, hips and feet travel together.`
            }
        }
        const separated = energy.root.position.distanceTo(physical.root.position) > 0.2
        cord.mesh.visible = energy.root.visible && separated
        if (cord.mesh.visible) {
            const from = new T.Vector3(0, bodyHeight, 0)
            const to = new T.Vector3(0, 0, 0.12).applyEuler(energy.root.rotation).add(energy.root.position)
            const distance = from.distanceTo(to)
            const slack = 0.22 / (1 + distance)
            cord.update((v, p) => {
                p.copy(from).lerp(to, v)
                p.y -= Math.sin(v * Math.PI) * slack
                p.z += Math.sin(v * Math.PI) * Math.sin(t * 0.8 + v * 9) * 0.045
            }, t)
            coils.forEach((coil, n) => {
                coil.mesh.visible = true
                coil.update((v, p) => {
                    const angle = v * Math.PI * 4 + t * 0.6 + n * 2.1
                    p.set(energy.root.position.x + Math.cos(angle) * 0.48,
                        energy.root.position.y + Math.sin(angle) * 0.33, 1.35 - v * 2.8)
                }, t, 0.6)
            })
        }
        const now = cameraFrame(kind, i)
        const before = cameraFrame(kind, Math.max(0, i - 1))
        const transition = smooth(elapsed / 7)
        position.set(...before.position).lerp(new T.Vector3(...now.position), transition)
        look.set(...before.target).lerp(new T.Vector3(...now.target), transition)
        if (directed) {
            const angle = Math.sin(t * 0.025) * (now.name === 'HAND STUDY' ? 0.08 : 0.15)
            const x = position.x
            position.x = x * Math.cos(angle) + position.z * Math.sin(angle)
            position.z = position.z * Math.cos(angle) - x * Math.sin(angle)
            position.y += Math.sin(t * 0.07) * 0.04
        }
        position.sub(look).multiplyScalar(Math.max(1, 1.25 / camera.aspect)).add(look)
        camera.position.copy(position)
        camera.lookAt(look)
        viewName = now.name
        return { ...state, viewName, motion }
    }
    return {
        scene, camera, update,
        diagnostics() {
            return {
                physicalPosition: physical.root.position.toArray(), astralPosition: energy.root.position.toArray(),
                astralRotation: energy.root.rotation.toArray().slice(0, 3), cordVisible: cord.mesh.visible,
                pointVisible: point.visible, ropeVisible: rope.visible, elevatorVisible: elevator.visible, viewName,
                handGrips: energy.grips.map(grip => grip.closed.visible),
            }
        },
    }
}
