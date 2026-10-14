// The nine shots of "A Day with Lumi", timed to film.json's clips. Each
// shot builds its own scene and draws any moment of global film time t.
import { Color, Scene } from 'three'
import { createLumi, createTrail } from './lumi.js'
import { createPuppet } from './puppets.js'
import {
    cutout, distanceFactor, ease, filmCamera, glow, lerp, mist, motes, plate, ring, track, worldAt, worldPerPixel,
} from './world.js'

const TAU = Math.PI * 2

function stage() {
    const scene = new Scene()
    scene.background = new Color(0x000000)
    const camera = filmCamera()
    return { scene, camera }
}

// Camera drift: from one offset to another (world units, FAR = 10) over the shot.
function drift(camera, t, start, end, from, to) {
    const k = ease((t - start) / (end - start)) * 0.85 + ((t - start) / (end - start)) * 0.15
    camera.position.set(lerp(from[0], to[0], k), lerp(from[1], to[1], k), lerp(from[2], to[2], k))
}

function setTime(t, ...things) {
    for (const thing of things) {
        const uniforms = thing.uniforms ?? thing.material?.uniforms
        if (uniforms?.time) {
            uniforms.time.value = t
        }
    }
}

// A Lumi that follows a keyed path; returns her state too, for trails.
function flight(keys) {
    const path = track(keys)
    return (t) => {
        const p = path(t)
        const q = path(t + 0.05)
        return { ...p, vx: (q.x - p.x) / 0.05 }
    }
}

// Light in the painting (sun, lamp, phone) sits behind the characters.
function backLight(color) {
    const mesh = glow(color, 1)
    mesh.renderOrder = 2
    return mesh
}

// A point `reach` pixels beyond a puppet's joint, away from its pelvis.
function outside(puppet, joint, t, reach, lift) {
    const hand = puppet.jointPixel(joint, t)
    const hip = puppet.jointPixel('pelvis', t)
    const dx = hand.x - hip.x
    const dy = hand.y - hip.y
    const length = Math.hypot(dx, dy) || 1
    return { x: hand.x + (dx / length) * reach, y: hand.y + (dy / length) * reach * 0.5 + lift, f: puppet.layout.f * 0.97 }
}

function placeGlow(mesh, x, y, f, sizePx, intensity) {
    mesh.position.copy(worldAt(x, y, f))
    mesh.scale.setScalar(sizePx * worldPerPixel(f))
    mesh.material.uniforms.intensity.value = intensity
}

export async function buildShots(context) {
    const { meta, voice } = context
    const shots = []

    // 1. Firefly at dawn — Lumi lights up among the reeds and says hello.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const lake = await plate('lake', {
            waterRect: [560, 560, 1920, 1080], waterAmount: 1, waterMaxDepth: 0.35,
            flowRect: [380, 230, 1920, 640], flowAmount: 0.7, flowMaxDepth: 0.2,
            windAmount: 1, windMinDepth: 0.4,
        })
        const fog = mist({ box: [300, 440, 1920, 660], f: 0.86, color: '#c9d2ff', amount: 0.3 })
        const flies = motes({ count: 46, box: [80, 260, 1840, 1000], f: [0.45, 0.95], color: '#ffd27a', size: [5, 12], drift: 40, seed: 3 })
        const lumi = await createLumi()
        const trail = createTrail({ width: 18, intensity: 0.9 })
        scene.add(lake.mesh, fog, flies, trail.mesh, lumi.group)
        const path = flight([
            { t: -0.5, x: 560, y: 770, f: 0.55, s: 60 },
            { t: 1.0, x: 572, y: 742, f: 0.55, s: 80 },
            { t: 2.0, x: 640, y: 520, f: 0.5, s: 290 },
            { t: 3.4, x: 662, y: 474, f: 0.5, s: 325 },
            { t: 5.0, x: 690, y: 458, f: 0.5, s: 335 },
            { t: 6.0, x: 820, y: 404, f: 0.55, s: 300 },
            { t: 7.6, x: 1560, y: 230, f: 0.72, s: 150 },
        ])
        return {
            start: 0, end: 7.0, scene, camera,
            update(t) {
                setTime(t, lake, fog, flies)
                drift(camera, t, 0, 7.4, [0, 0.05, 0], [0.12, 0.12, -0.55])
                const p = path(t)
                const bob = Math.sin(t * 2.3) * 8
                const appear = ease((t - 1.0) / 0.8)
                const blink = t < 1.4 ? 0.35 + 0.65 * Math.abs(Math.sin(t * 5.2)) : 1
                lumi.update({ x: p.x, y: p.y + bob * appear, f: p.f, size: p.s, t, vx: p.vx, opacity: appear,
                    spark: ease((t - 0.3) / 0.4), light: (t < 1.4 ? blink * 2.4 : 1) + voice(t) * 0.9, face: t < 5.6 ? 1 : undefined })
                trail.update((time) => { const q = path(time); return { x: q.x, y: q.y + 20, f: q.f } }, t, 0.7, { start: 1.2, alpha: t > 5.6 || t < 2.2 ? 1 : 0.25 })
            },
        }
    })())

    // 2. Sunrise welcome — Lumi flies in through the cabin window.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const room = await plate('cabin-empty', { raysOrigin: [240, 200, 0], raysAmount: 0.6 })
        const mia = await cutout('cabin', meta.cabin, { hipY: 0.28 })
        const dust = motes({ count: 80, box: [180, 80, 1150, 820], f: [0.5, 0.85], color: '#ffe2b0', size: [3, 7], drift: 22, blink: 0.25, seed: 5, speed: 0.6 })
        const lumi = await createLumi()
        const trail = createTrail({ width: 20, intensity: 0.8 })
        scene.add(room.mesh, mia.mesh, dust, trail.mesh, lumi.group)
        const path = flight([
            { t: 6.6, x: 230, y: 330, f: 0.85, s: 60 },
            { t: 7.4, x: 330, y: 318, f: 0.76, s: 110 },
            { t: 8.4, x: 520, y: 290, f: 0.64, s: 165 },
            { t: 9.4, x: 640, y: 236, f: 0.6, s: 185 },
            { t: 10.6, x: 560, y: 300, f: 0.6, s: 185 },
            { t: 11.8, x: 650, y: 268, f: 0.6, s: 190 },
            { t: 13.4, x: 820, y: 230, f: 0.62, s: 175 },
        ])
        return {
            start: 7.0, end: 13.0, scene, camera,
            update(t) {
                setTime(t, room, dust)
                drift(camera, t, 6.6, 13.4, [-0.15, 0, -0.1], [0.12, 0.03, -0.38])
                mia.uniforms.breath.value = Math.sin((TAU * (t - 7)) / 4.2)
                mia.uniforms.breathAmount.value = 0.006
                mia.uniforms.sway.value = [Math.sin(t * 0.8) * 0.004, 0]
                const p = path(t)
                lumi.update({ x: p.x, y: p.y + Math.sin(t * 2.1) * 7, f: p.f, size: p.s, t, vx: p.vx, light: 1 + voice(t) * 0.9 })
                trail.update((time) => path(time), t, 0.8, { start: 6.6 })
            },
        }
    })())

    // 3. Breath on the dock — Lumi's glow rises and falls with Mia's breath.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const dock = await plate('dock-empty', {
            waterRect: [460, 600, 1920, 1080], waterAmount: 1, waterMaxDepth: 0.55,
            flowRect: [300, 330, 1920, 700], flowAmount: 0.8, flowMaxDepth: 0.25,
        })
        const fog = mist({ box: [250, 470, 1920, 760], f: 0.86, color: '#ffd8c4', amount: 0.32 })
        const mia = await cutout('dock', meta.dock, { hipY: 0.19 })
        const puff = glow('#ffffff', 1)
        const lumi = await createLumi()
        const flies = motes({ count: 16, box: [600, 300, 1700, 800], f: [0.6, 0.95], color: '#ffd9a0', size: [4, 8], drift: 30, seed: 9 })
        scene.add(dock.mesh, fog, mia.mesh, puff, flies, lumi.group)
        const miaF = distanceFactor(meta.dock.depth)
        const breathPeriod = 4.6
        const inhale = (t) => 0.5 - 0.5 * Math.cos((TAU * (t - 13)) / breathPeriod)
        return {
            start: 13.0, end: 20.0, scene, camera,
            update(t) {
                setTime(t, dock, fog, flies)
                drift(camera, t, 12.6, 20.4, [0.08, 0, 0], [-0.08, 0.04, -0.45])
                const breath = inhale(t)
                mia.uniforms.breath.value = breath * 2 - 1
                mia.uniforms.breathAmount.value = 0.008
                const out = Math.max(0, -Math.sin((TAU * (t - 13)) / breathPeriod))
                placeGlow(puff, 712 + out * 30, 182 - out * 10, miaF * 0.98, 90 + out * 120, out * 0.16)
                const x = 870 + Math.sin(t * 0.7) * 26
                const y = 330 + Math.sin(t * 1.3) * 14
                lumi.update({ x, y, f: miaF * 1.02, size: 150, t, vx: Math.cos(t * 0.7) * 18, face: -1,
                    light: 0.45 + breath * 1.1 + voice(t) * 0.5 })
            },
        }
    })())

    // 4a. Stillness above the clouds — a brass bell rings.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const ledge = await plate('ledge-empty', { flowRect: [640, 200, 1920, 1000], flowAmount: 1, flowMaxDepth: 0.32 })
        const fog = mist({ box: [560, 560, 1920, 920], f: 0.9, color: '#fff1da', amount: 0.26 })
        const mia = await cutout('ledge', meta.ledge, { hipY: 0.17 })
        const sun = backLight('#ffd28a')
        const rings = [ring('#ffd27a', 1), ring('#ffe6a8', 1)]
        const flash = glow('#fff0c0', 1)
        const lumi = await createLumi()
        scene.add(ledge.mesh, sun, fog, mia.mesh, ...rings, flash, lumi.group)
        const bellF = distanceFactor(ledge.depth(1134, 850))
        const miaF = distanceFactor(meta.ledge.depth)
        const strikes = [21.55, 22.35]
        return {
            start: 20.0, end: 25.0, scene, camera,
            update(t) {
                setTime(t, ledge, fog)
                drift(camera, t, 19.6, 25.3, [0.12, 0, -0.1], [-0.12, 0.03, -0.36])
                mia.uniforms.breath.value = Math.sin((TAU * (t - 20)) / 4.8)
                mia.uniforms.breathAmount.value = 0.006
                placeGlow(sun, 1725, 122, 1, 520, 0.55 + Math.sin(t * 0.9) * 0.05)
                rings.forEach((mesh, index) => {
                    const age = (t - strikes[index]) / 1.8
                    const on = age > 0 && age < 1
                    mesh.visible = on
                    if (on) {
                        placeGlow(mesh, 1134, 846, bellF, 60 + age * 620, (1 - age) * 0.9)
                        mesh.scale.y *= 0.3
                    }
                })
                const ringAge = Math.min(...strikes.map((s) => (t > s ? t - s : 9)))
                placeGlow(flash, 1134, 836, bellF, 160, Math.max(0, 1 - ringAge / 0.5) * 0.9)
                lumi.update({ x: 1010, y: 470 + Math.sin(t * 1.4) * 4, f: miaF * 1.05, size: 125, t, face: -1,
                    light: 0.9 + voice(t) * 0.6 + Math.max(0, 1 - ringAge / 1.2) * 0.6 })
            },
        }
    })())

    // 4b. Sun Salutation — Mia reaches up as Lumi traces an arc over her hands.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const meadow = await plate('meadow', { windAmount: 0.8, windMinDepth: 0.45, flowRect: [0, 520, 1920, 800], flowAmount: 0.6, flowMaxDepth: 0.2 })
        const mia = await cutout('meadow', meta.meadow, { hipY: 0.46, scale: 0.88 })
        const sun = backLight('#ffd690')
        const lumi = await createLumi()
        const trail = createTrail({ width: 28, intensity: 1.3 })
        const sparkles = motes({ count: 40, box: [250, 0, 900, 420], f: [0.55, 0.62], color: '#ffe39a', size: [3, 8], drift: 20, blink: 0.8, seed: 13 })
        scene.add(meadow.mesh, sun, mia.mesh, sparkles, trail.mesh, lumi.group)
        const f = distanceFactor(meta.meadow.depth) * 0.98
        const path = flight([
            { t: 24.7, x: 200, y: 520, f, s: 100 },
            { t: 25.7, x: 320, y: 260, f, s: 110 },
            { t: 26.6, x: 510, y: 120, f, s: 115 },
            { t: 27.5, x: 720, y: 220, f, s: 115 },
            { t: 28.4, x: 830, y: 330, f, s: 115 },
            { t: 29.7, x: 900, y: 430, f, s: 110 },
        ])
        return {
            start: 25.0, end: 29.3, scene, camera,
            update(t) {
                setTime(t, meadow, sparkles)
                drift(camera, t, 24.7, 29.65, [0, -0.1, -0.12], [0.04, 0.06, -0.4])
                // She lengthens up into the salute, then breathes there.
                mia.uniforms.breath.value = ease((t - 24.9) / 1.4) + Math.sin((TAU * (t - 26.3)) / 4) * 0.15
                mia.uniforms.breathAmount.value = 0.018
                placeGlow(sun, 1800, 405, 1, 640, 0.6)
                sparkles.material.uniforms.opacity.value = ease((t - 25.6) / 1)
                const p = path(t)
                lumi.update({ x: p.x, y: p.y + Math.sin(t * 2) * 5, f: p.f, size: p.s, t, vx: p.vx, light: 1.1 + voice(t) * 0.7 })
                trail.update((time) => path(time), t, 2.4, { start: 24.9 })
            },
        }
    })())

    // 5. Tai Chi in the monastery — the monk's Wave Hands Like Clouds.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const effects = { flagRect: [0, 0, 1920, 560], flagAmount: 1, flowRect: [480, 240, 1920, 640], flowAmount: 0.7, flowMaxDepth: 0.22 }
        const courtyard = await plate('courtyard', effects)
        const sun = backLight('#ffd690')
        const monk = await createPuppet('monk', 'lesson-4/cloud-hands/demo', { from: 4.0, yaw: 0 })
        monk.plane.material.uniforms.tint.value = new Color(1.0, 0.93, 0.84)
        monk.place(760, 955, 590, distanceFactor(courtyard.depth(760, 955)))
        const lumi = await createLumi()
        const trail = createTrail({ width: 20, intensity: 0.9 })
        const sparkles = motes({ count: 30, box: [300, 300, 1500, 900], f: [0.55, 0.9], color: '#ffe0a0', size: [3, 7], drift: 35, blink: 0.7, seed: 17 })
        scene.add(courtyard.mesh, sun, monk.plane, sparkles, trail.mesh, lumi.group)
        // Lumi plays just outside the monk's moving hand, never over his face.
        const lumiAt = (t) => outside(monk, 'wristL', t - 29.3 - 0.35, 150, -50)
        return {
            start: 29.3, end: 36.8, scene, camera,
            update(t, renderer) {
                setTime(t, courtyard, sparkles)
                drift(camera, t, 28.9, 37.1, [0.15, 0, 0], [0.02, 0.03, -0.42])
                placeGlow(sun, 1850, 70, 1, 700, 0.65)
                monk.draw(renderer, t - 29.3)
                const p = lumiAt(t)
                const q = lumiAt(t + 0.05)
                lumi.update({ x: p.x, y: p.y + Math.sin(t * 2.2) * 6, f: p.f, size: 115, t, vx: (q.x - p.x) / 0.05, light: 1 + voice(t) * 0.7 })
                trail.update(lumiAt, t, 0.9, { start: 29.0 })
            },
        }
    })())

    // 6. Brush knee and push — Dolma and the monk in unison; Lumi draws a ribbon.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const courtyard = await plate('courtyard', { flagRect: [0, 0, 1920, 560], flagAmount: 1, flowRect: [480, 240, 1920, 640], flowAmount: 0.7, flowMaxDepth: 0.22 })
        const sun = backLight('#ffd690')
        const yaw = 0.85
        // From 12.8 s the step, brush and push play with both faces towards us.
        const dolma = await createPuppet('tibetanWoman', 'lesson-2/brush-knee/demo', { from: 12.8, yaw })
        const monk = await createPuppet('monk', 'lesson-2/brush-knee/demo', { from: 12.8, yaw })
        for (const puppet of [dolma, monk]) {
            puppet.plane.material.uniforms.tint.value = new Color(1.0, 0.93, 0.84)
        }
        dolma.place(1180, 905, 520, distanceFactor(courtyard.depth(1180, 905)))
        monk.place(640, 1010, 610, distanceFactor(courtyard.depth(640, 1010)))
        const lumi = await createLumi()
        const ribbon = createTrail({ width: 30, intensity: 1.4, samples: 160 })
        scene.add(courtyard.mesh, sun, dolma.plane, monk.plane, ribbon.mesh, lumi.group)
        const lumiAt = (t) => outside(monk, 'wristR', t - 36.8 - 0.2, 70, -30)
        return {
            start: 36.8, end: 42.8, scene, camera,
            update(t, renderer) {
                setTime(t, courtyard)
                drift(camera, t, 36.5, 43.2, [-0.2, 0.02, 0.05], [0.18, 0.05, -0.2])
                placeGlow(sun, 1850, 70, 1, 700, 0.65)
                dolma.draw(renderer, t - 36.8)
                monk.draw(renderer, t - 36.8)
                const p = lumiAt(t)
                const q = lumiAt(t + 0.05)
                lumi.update({ x: p.x, y: p.y, f: p.f, size: 105, t, vx: (q.x - p.x) / 0.05, light: 1.2 })
                ribbon.update(lumiAt, t, 1.8, { start: 36.6 })
            },
        }
    })())

    // 7. Habits and the evening diary — seven circles fill with gold.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const room = await plate('desk-empty', { rainRect: [0, 0, 1190, 470], rainAmount: 1 })
        const mia = await cutout('desk', meta.desk, { hipY: 0.1 })
        const lamp = backLight('#ffcf80')
        const circleXs = Array.from({ length: 7 }, (_, index) => 700 + index * 80)
        const circleY = 150
        const rings = circleXs.map(() => ring('#ffd27a', 1))
        const fills = circleXs.map(() => glow('#ffd27a', 1))
        const lumi = await createLumi()
        const trail = createTrail({ width: 18, intensity: 0.9 })
        scene.add(room.mesh, lamp, mia.mesh, ...rings, ...fills, trail.mesh, lumi.group)
        const circleF = 0.78
        const fillAt = circleXs.map((_, index) => 43.45 + index * 0.48)
        const keys = [{ t: 42.3, x: 420, y: 420, f: 0.75, s: 90 }, { t: 43.0, x: 560, y: 240, f: circleF, s: 95 }]
        circleXs.forEach((x, index) => keys.push({ t: fillAt[index], x, y: circleY - 30, f: circleF, s: 95 }))
        keys.push({ t: 47.0, x: 1040, y: 300, f: 0.72, s: 100 }, { t: 47.9, x: 965, y: 392, f: 0.7, s: 118 }, { t: 52.3, x: 968, y: 390, f: 0.7, s: 118 })
        const path = flight(keys)
        return {
            start: 42.8, end: 51.8, scene, camera,
            update(t) {
                setTime(t, room)
                drift(camera, t, 42.4, 52.2, [0.06, 0, 0], [-0.04, 0.02, -0.34])
                mia.uniforms.breath.value = Math.sin((TAU * (t - 42.8)) / 4.4)
                mia.uniforms.breathAmount.value = 0.005
                mia.uniforms.sway.value = [Math.sin(t * 1.9) * 0.003, 0]
                const flicker = 0.24 + Math.sin(t * 7.3) * 0.015 + Math.sin(t * 13.1) * 0.01
                placeGlow(lamp, 965, 470, 0.72, 520, flicker)
                circleXs.forEach((x, index) => {
                    const appear = ease((t - 43.0 - index * 0.06) / 0.5)
                    const filled = ease((t - fillAt[index]) / 0.35)
                    const pop = 1 + Math.max(0, 1 - Math.abs(t - fillAt[index] - 0.18) / 0.18) * 0.25
                    placeGlow(rings[index], x, circleY, circleF, 78 * pop, appear * 0.55)
                    placeGlow(fills[index], x, circleY, circleF, 70 * pop, filled * 0.9)
                    const fade = 1 - ease((t - 50.2) / 1.2)
                    rings[index].material.uniforms.intensity.value *= fade
                    fills[index].material.uniforms.intensity.value *= fade
                })
                const p = path(t)
                const resting = t > 47.9
                lumi.update({ x: p.x, y: p.y + Math.sin(t * (resting ? 1.2 : 2.2)) * (resting ? 3 : 6), f: p.f, size: p.s, t, vx: p.vx,
                    light: 1 + voice(t) * 0.8, face: resting ? -1 : undefined })
                trail.update((time) => path(time), t, 0.6, { start: 42.4, alpha: resting ? 0 : 1 })
            },
        }
    })())

    // 8. Just ask — Lumi rises out of the phone's glow.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const room = await plate('sofa-empty')
        const mia = await cutout('sofa', meta.sofa, { hipY: 0.35 })
        const screen = backLight('#cfe6ff')
        const burst = motes({ count: 40, box: [660, 470, 800, 620], f: [0.62, 0.66], color: '#ffe3a0', size: [3, 7], drift: 45, blink: 0.6, seed: 21, speed: 2 })
        const lumi = await createLumi()
        const trail = createTrail({ width: 16, intensity: 0.9 })
        scene.add(room.mesh, mia.mesh, screen, burst, trail.mesh, lumi.group)
        const miaF = distanceFactor(meta.sofa.depth)
        const path = flight([
            { t: 51.4, x: 720, y: 588, f: miaF, s: 10 },
            { t: 52.0, x: 722, y: 580, f: miaF, s: 22 },
            { t: 52.6, x: 740, y: 520, f: miaF * 0.98, s: 70 },
            { t: 53.3, x: 800, y: 410, f: miaF * 0.96, s: 130 },
            { t: 54.2, x: 845, y: 345, f: miaF * 0.95, s: 150 },
            { t: 56.5, x: 860, y: 330, f: miaF * 0.95, s: 152 },
            { t: 59.3, x: 900, y: 310, f: miaF * 0.95, s: 150 },
        ])
        return {
            start: 51.8, end: 58.8, scene, camera,
            update(t) {
                setTime(t, room, burst)
                drift(camera, t, 51.4, 59.3, [0, 0, 0], [0.04, 0.02, -0.4])
                mia.uniforms.breath.value = Math.sin((TAU * (t - 51.8)) / 4.6)
                mia.uniforms.breathAmount.value = 0.005
                const rise = Math.max(0, 1 - Math.abs(t - 52.3) / 0.8)
                placeGlow(screen, 720, 590, miaF * 0.97, 160 + rise * 220, 0.35 + rise * 1.1)
                burst.material.uniforms.opacity.value = Math.max(0, 1 - Math.abs(t - 52.5) / 0.9)
                const p = path(t)
                const appear = ease((t - 51.9) / 0.4)
                lumi.update({ x: p.x, y: p.y + Math.sin(t * 2) * 5 * appear, f: p.f, size: p.s, t, vx: p.vx, opacity: appear,
                    face: -1, light: 1 + voice(t) * 1.0 + rise * 0.8 })
                trail.update((time) => path(time), t, 0.7, { start: 51.95, alpha: t < 54.5 ? 1 : 0 })
            },
        }
    })())

    // 9. A breeze of light — a long golden trail curls across the night.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const night = await plate('night', {
            starRect: [0, 0, 1920, 760], starAmount: 1,
            waterRect: [0, 830, 1920, 1080], waterAmount: 1, waterMaxDepth: 0.6,
        })
        const flies = motes({ count: 60, box: [0, 760, 1920, 900], f: [0.7, 0.98], color: '#ffd27a', size: [4, 9], drift: 30, seed: 29 })
        const lumi = await createLumi()
        const trail = createTrail({ width: 36, intensity: 1.35, samples: 220 })
        scene.add(night.mesh, flies, trail.mesh, lumi.group)
        const path = flight([
            { t: 58.2, x: 120, y: 980, f: 0.5, s: 140 },
            { t: 59.4, x: 470, y: 820, f: 0.56, s: 128 },
            { t: 60.6, x: 840, y: 905, f: 0.62, s: 116 },
            { t: 61.8, x: 1190, y: 800, f: 0.68, s: 104 },
            { t: 62.9, x: 1420, y: 560, f: 0.74, s: 96 },
            { t: 64.0, x: 1590, y: 360, f: 0.8, s: 90 },
            { t: 65.5, x: 1730, y: 210, f: 0.84, s: 84 },
        ])
        return {
            start: 58.8, end: 65.0, scene, camera,
            update(t) {
                setTime(t, night, flies)
                drift(camera, t, 58.3, 65, [0, -0.15, 0], [0.05, 0.28, -0.3])
                const p = path(t)
                lumi.update({ x: p.x, y: p.y, f: p.f, size: p.s, t, vx: p.vx, light: 1.2 + voice(t) * 0.8 })
                trail.update((time) => path(time), t, 6.5, { start: 58.4 })
            },
        }
    })())

    return shots
}
