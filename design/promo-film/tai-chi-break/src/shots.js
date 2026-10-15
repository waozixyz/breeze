// The shots of "a Tai Chi break": a late-night desk where six agents work,
// a pause above the clouds, Tai Chi in the monastery courtyard, the finished
// work, and the end card. Each shot draws any moment of film time t.
import { Color, Mesh, PlaneGeometry, Scene, ShaderMaterial, AdditiveBlending } from 'three'
import { createLumi, createTrail } from '/design/promo-film/three/src/lumi.js'
import { createPuppet } from './puppets.js'
import {
    distanceFactor, ease, filmCamera, glow, lerp, mist, motes, plate, texture, track, worldAt, worldPerPixel,
} from '/design/promo-film/three/src/world.js'
import { createTerminal } from './terminal.js'

const THREE_PLATES = '../../three/plates/'
// The empty monitor screen in plates/studio.jpg, in plate pixels.
const SCREEN = [510, 152, 1406, 609]

// Film times. The cuts follow the score: its swells peak at 13.1 and 38.9 s.
export const LENGTH = 53.0
export const CUTS = {
    ledge: 13.1, courtyard: 18.6, pair: 28.6, back: 38.9, card: 46.0,
}

function stage() {
    const scene = new Scene()
    scene.background = new Color(0x000000)
    return { scene, camera: filmCamera() }
}

function drift(camera, t, start, end, from, to) {
    const x = (t - start) / (end - start)
    const k = ease(x) * 0.8 + Math.min(1, Math.max(0, x)) * 0.2
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

function backLight(color) {
    const mesh = glow(color, 1)
    mesh.renderOrder = 2
    return mesh
}

function placeGlow(mesh, x, y, f, sizePx, intensity) {
    mesh.position.copy(worldAt(x, y, f))
    mesh.scale.setScalar(sizePx * worldPerPixel(f))
    mesh.material.uniforms.intensity.value = intensity
}

function flight(keys) {
    const path = track(keys)
    return (t) => {
        const p = path(t)
        const q = path(t + 0.05)
        return { ...p, vx: (q.x - p.x) / 0.05 }
    }
}

// The terminal on the monitor: a quad over the painted screen, at the
// screen's own depth so it stays in place when the camera moves.
function screen(terminal, f) {
    const [x0, y0, x1, y1] = SCREEN
    const unit = worldPerPixel(f)
    const material = new ShaderMaterial({
        uniforms: { map: { value: terminal.map }, power: { value: 1 }, flare: { value: 0 }, time: { value: 0 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform float power; uniform float flare; uniform float time; varying vec2 vUv;
void main() {
    vec3 c = texture2D(map, vUv).rgb;
    // A little glass: a soft diagonal sheen and darker corners.
    float sheen = smoothstep(0.0, 1.0, 1.0 - abs(vUv.x * 0.8 + vUv.y * 0.6 - 0.95) * 2.2) * 0.035;
    vec2 d = vUv - 0.5;
    float corners = 1.0 - smoothstep(0.18, 0.5, dot(d, d)) * 0.35;
    c = c * corners * power + sheen;
    // The break: the screen's light swells into a warm white.
    c = mix(c, vec3(1.0, 0.93, 0.82) * 1.6, flare);
    gl_FragColor = vec4(c, 1.0);
    #include <colorspace_fragment>
}`,
        depthTest: false, depthWrite: false,
    })
    const mesh = new Mesh(new PlaneGeometry((x1 - x0) * unit, (y1 - y0) * unit), material)
    mesh.position.copy(worldAt((x0 + x1) / 2, (y0 + y1) / 2, f))
    mesh.renderOrder = 3
    mesh.frustumCulled = false
    return mesh
}

// Steam curling up from the tea cup: thin wisps of drifting noise.
function steam(x, y, f, widthPx, heightPx) {
    const unit = worldPerPixel(f)
    const material = new ShaderMaterial({
        uniforms: { time: { value: 0 }, amount: { value: 0.32 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform float time; uniform float amount; varying vec2 vUv;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
void main() {
    vec2 p = vUv;
    float rise = time * 0.22;
    float bend = (noise(vec2(p.y * 3.0 - rise * 2.0, 1.7)) - 0.5) * 0.5 * p.y;
    float x = (p.x - 0.5 - bend) * 2.0;
    float strand = exp(-x * x * 9.0);
    float wisps = noise(vec2(x * 3.0, p.y * 5.0 - rise * 4.0)) * noise(vec2(x * 7.0 + 3.0, p.y * 9.0 - rise * 6.0));
    float fade = smoothstep(0.0, 0.15, p.y) * (1.0 - smoothstep(0.45, 1.0, p.y));
    float a = strand * smoothstep(0.08, 0.45, wisps) * fade * amount;
    gl_FragColor = vec4(vec3(1.0, 0.95, 0.88) * a, 1.0);
}`,
        blending: AdditiveBlending, transparent: true, depthTest: false, depthWrite: false,
    })
    const mesh = new Mesh(new PlaneGeometry(widthPx * unit, heightPx * unit), material)
    mesh.position.copy(worldAt(x, y - heightPx / 2, f))
    mesh.renderOrder = 7
    mesh.frustumCulled = false
    return mesh
}

// A camera path through keyed rows { t, x, y, z }.
function path(keys) {
    const along = track(keys)
    return (t) => {
        const p = along(t)
        return [p.x, p.y, p.z]
    }
}

async function studio({ start, end, camera: cameraAt, terminalState, light }) {
    const { scene, camera } = stage()
    const room = await plate('studio', {
        rainRect: [300, 0, 1920, 560], rainAmount: 0.45,
        waterRect: [1420, 440, 1700, 560], waterAmount: 0.6, waterMaxDepth: 0.2,
        starRect: [1400, 0, 1920, 140], starAmount: 0.4,
    })
    const f = distanceFactor(room.depth(958, 380))
    const terminal = createTerminal(2048, Math.round(2048 * (SCREEN[3] - SCREEN[1]) / (SCREEN[2] - SCREEN[0])))
    const monitor = screen(terminal, f)
    const spill = backLight('#6f8dff')
    const lantern = backLight('#ffc978')
    const flare = glow('#fff1d6', 1)
    const cup = steam(368, 655, distanceFactor(room.depth(368, 690)) * 0.99, 90, 230)
    scene.add(room.mesh, spill, lantern, monitor, cup, flare)
    return {
        start, end, scene, camera,
        update(t) {
            setTime(t, room, cup)
            monitor.material.uniforms.time.value = t
            camera.position.set(...cameraAt(t))
            const state = terminalState(t)
            terminal.draw({ t, ...state })
            const swell = light(t)
            monitor.material.uniforms.flare.value = swell * 0.7
            monitor.material.uniforms.power.value = 1.05 + swell * 0.6
            placeGlow(spill, 958, 400, f * 1.02, 1500, 0.2 + swell * 0.5)
            placeGlow(lantern, 1702, 560, distanceFactor(room.depth(1702, 560)), 420, 0.42 + Math.sin(t * 1.7) * 0.03 + Math.sin(t * 4.3) * 0.015)
            placeGlow(flare, 958, 380, f * 0.98, 900 + swell * 2000, swell * 0.5)
        },
    }
}

export async function buildShots() {
    const shots = []

    // 1. Late night. Six agents work on the monitor; the camera eases in.
    shots.push(await studio({
        start: 0, end: CUTS.ledge,
        // A slow push towards the monitor, then through its light.
        camera: path([
            { t: -0.5, x: 0.22, y: -0.06, z: 0.25 },
            { t: 5.5, x: 0.1, y: 0.0, z: -0.75 },
            { t: 10.6, x: -0.02, y: 0.1, z: -1.65 },
            // The screen fills the frame from about 12.6 s (its centre is
            // at y 0.78, and it fills the view from 3.3 units away).
            { t: 12.1, x: 0.0, y: 0.55, z: -3.2 },
            { t: 13.1, x: 0.0, y: 0.78, z: -4.35 },
            { t: 14.0, x: 0.0, y: 0.8, z: -4.7 },
        ]),
        terminalState: (t) => ({ crawl: Math.min(1, t / CUTS.ledge), elapsed: 754 + t * 1.6 }),
        // The screen's light swells into the cut to the clouds.
        light: (t) => Math.pow(ease((t - 11.2) / 1.8), 1.6),
    }))

    // 2. Above the clouds at dawn: step away for a moment.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const ledge = await plate(`${THREE_PLATES}ledge-empty`, { flowRect: [640, 200, 1920, 1000], flowAmount: 1, flowMaxDepth: 0.32 })
        const fog = mist({ box: [560, 560, 1920, 920], f: 0.9, color: '#fff1da', amount: 0.26 })
        const haze = mist({ box: [0, 380, 1300, 760], f: 0.95, color: '#ffe9cc', amount: 0.2, speed: 0.02 })
        const sun = backLight('#ffd28a')
        const flies = motes({ count: 34, box: [200, 200, 1800, 900], f: [0.55, 0.95], color: '#ffe3a6', size: [3, 7], drift: 30, blink: 0.6, seed: 7, speed: 0.7 })
        const lumi = await createLumi()
        const trail = createTrail({ width: 22, intensity: 1.0, samples: 160 })
        scene.add(ledge.mesh, sun, haze, fog, flies, trail.mesh, lumi.group)
        const s = CUTS.ledge
        const path = flight([
            { t: s - 0.4, x: 330, y: 980, f: 0.62, s: 120 },
            { t: s + 1.2, x: 560, y: 720, f: 0.66, s: 112 },
            { t: s + 2.8, x: 820, y: 560, f: 0.72, s: 104 },
            { t: s + 4.2, x: 1120, y: 470, f: 0.78, s: 96 },
            { t: s + 5.4, x: 1420, y: 360, f: 0.84, s: 88 },
            { t: s + 6.6, x: 1640, y: 250, f: 0.9, s: 80 },
        ])
        return {
            start: CUTS.ledge, end: CUTS.courtyard, scene, camera,
            update(t) {
                setTime(t, ledge, fog, haze, flies)
                drift(camera, t, s - 0.6, CUTS.courtyard + 0.5, [-0.18, -0.12, 0.1], [0.14, 0.12, -0.5])
                placeGlow(sun, 1725, 122, 1, 560, 0.6 + Math.sin(t * 0.9) * 0.05)
                const p = path(t)
                const appear = ease((t - s + 0.2) / 0.8)
                lumi.update({ x: p.x, y: p.y + Math.sin(t * 2.1) * 6, f: p.f, size: p.s, t, vx: p.vx, light: 1.1, opacity: appear, spark: appear })
                trail.update((time) => path(time), t, 1.6, { start: s - 0.3 })
            },
        }
    })())

    // 3. The courtyard: Wave Hands Like Clouds, the monk alone.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const courtyard = await plate(`${THREE_PLATES}courtyard`, { flagRect: [0, 0, 1920, 560], flagAmount: 1, flowRect: [480, 240, 1920, 640], flowAmount: 0.7, flowMaxDepth: 0.22 })
        const sun = backLight('#ffd690')
        const monk = await createPuppet('monk', 'lesson-4/cloud-hands/demo', { from: 2.0, yaw: 0 })
        monk.plane.material.uniforms.tint.value = new Color(1.0, 0.94, 0.86)
        monk.place(1360, 985, 640, distanceFactor(courtyard.depth(1360, 985)))
        const sparkles = motes({ count: 34, box: [300, 260, 1700, 900], f: [0.55, 0.9], color: '#ffe0a0', size: [3, 7], drift: 35, blink: 0.7, seed: 17 })
        const fog = mist({ box: [0, 520, 1920, 820], f: 0.97, color: '#fff0d8', amount: 0.14, speed: 0.02 })
        scene.add(courtyard.mesh, sun, fog, monk.plane, sparkles)
        const s = CUTS.courtyard
        return {
            start: CUTS.courtyard, end: CUTS.pair, scene, camera,
            update(t, renderer) {
                setTime(t, courtyard, sparkles, fog)
                drift(camera, t, s - 0.5, CUTS.pair + 0.5, [0.2, 0.0, 0.05], [0.02, 0.05, -0.55])
                placeGlow(sun, 1850, 70, 1, 760, 0.66)
                monk.draw(renderer, t - s)
            },
        }
    })())

    // 4. Part the Wild Horse's Mane, the monk and the Tibetan teacher together.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const courtyard = await plate(`${THREE_PLATES}courtyard`, { flagRect: [0, 0, 1920, 560], flagAmount: 1, flowRect: [480, 240, 1920, 640], flowAmount: 0.7, flowMaxDepth: 0.22 })
        const sun = backLight('#ffd690')
        const yaw = 0.4
        const dolma = await createPuppet('tibetanWoman', 'lesson-1/wild-horse/demo', { from: 1.0, yaw })
        const monk = await createPuppet('monk', 'lesson-1/wild-horse/demo', { from: 1.0, yaw })
        for (const puppet of [dolma, monk]) {
            puppet.plane.material.uniforms.tint.value = new Color(1.0, 0.94, 0.86)
        }
        dolma.place(1610, 925, 530, distanceFactor(courtyard.depth(1610, 925)))
        monk.place(1130, 1010, 630, distanceFactor(courtyard.depth(1130, 1010)))
        const sparkles = motes({ count: 30, box: [300, 260, 1700, 900], f: [0.55, 0.9], color: '#ffe0a0', size: [3, 7], drift: 35, blink: 0.7, seed: 23 })
        scene.add(courtyard.mesh, sun, dolma.plane, monk.plane, sparkles)
        const s = CUTS.pair
        return {
            start: CUTS.pair, end: CUTS.back, scene, camera,
            update(t, renderer) {
                setTime(t, courtyard, sparkles)
                drift(camera, t, s - 0.5, CUTS.back + 0.5, [-0.26, 0.04, 0.0], [0.16, 0.06, -0.3])
                placeGlow(sun, 1850, 70, 1, 760, 0.66)
                dolma.draw(renderer, t - s)
                monk.draw(renderer, t - s)
            },
        }
    })())

    // 5. Back at the desk: the last lanes finish, and the work is ready.
    shots.push(await studio({
        start: CUTS.back, end: CUTS.card,
        // Out of the light, back from the monitor, and a slow settle.
        camera: path([
            { t: CUTS.back - 0.9, x: 0.0, y: 0.8, z: -4.7 },
            { t: CUTS.back, x: 0.0, y: 0.78, z: -4.35 },
            { t: CUTS.back + 1.2, x: 0.0, y: 0.5, z: -3.0 },
            { t: CUTS.back + 3.4, x: -0.06, y: 0.08, z: -1.45 },
            { t: CUTS.card + 0.6, x: -0.2, y: -0.02, z: -0.6 },
        ]),
        terminalState: (t) => ({ crawl: 1, done: ease((t - CUTS.back - 0.4) / 2.2), elapsed: 1960 + (t - CUTS.back) * 1.6 }),
        // The light settles back into the screen after the cut.
        light: (t) => Math.pow(1 - ease((t - CUTS.back + 0.1) / 1.9), 1.6),
    }))

    // 6. The end card under the night sky, Lumi drawing her trail.
    shots.push(await (async () => {
        const { scene, camera } = stage()
        const night = await plate(`${THREE_PLATES}night`, {
            starRect: [0, 0, 1920, 760], starAmount: 1,
            waterRect: [0, 830, 1920, 1080], waterAmount: 1, waterMaxDepth: 0.6,
        })
        const flies = motes({ count: 60, box: [0, 760, 1920, 900], f: [0.7, 0.98], color: '#ffd27a', size: [4, 9], drift: 30, seed: 29 })
        const iconMap = await texture('/assets/app/source-icon.png')
        const icon = new Mesh(new PlaneGeometry(1, 1), new ShaderMaterial({
            uniforms: { map: { value: iconMap }, opacity: { value: 0 } },
            vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
            fragmentShader: /* glsl */ `
uniform sampler2D map; uniform float opacity; varying vec2 vUv;
void main() { vec4 c = texture2D(map, vUv); gl_FragColor = vec4(c.rgb, c.a * opacity);
    #include <colorspace_fragment>
}`,
            transparent: true, depthTest: false, depthWrite: false,
        }))
        icon.renderOrder = 30
        icon.frustumCulled = false
        const halo = glow('#cfd8ff', 1)
        halo.renderOrder = 29
        const lumi = await createLumi()
        const trail = createTrail({ width: 34, intensity: 1.3, samples: 220 })
        scene.add(night.mesh, flies, trail.mesh, halo, icon, lumi.group)
        const s = CUTS.card
        const path = flight([
            { t: s - 0.4, x: 100, y: 990, f: 0.5, s: 130 },
            { t: s + 1.0, x: 470, y: 860, f: 0.56, s: 120 },
            { t: s + 2.3, x: 860, y: 930, f: 0.62, s: 110 },
            { t: s + 3.6, x: 1240, y: 830, f: 0.68, s: 100 },
            { t: s + 4.8, x: 1500, y: 640, f: 0.74, s: 92 },
            { t: s + 6.0, x: 1680, y: 470, f: 0.8, s: 86 },
            { t: s + 7.6, x: 1820, y: 300, f: 0.84, s: 80 },
        ])
        const iconF = 0.5
        return {
            start: CUTS.card, end: LENGTH, scene, camera,
            update(t) {
                setTime(t, night, flies)
                drift(camera, t, s - 0.6, LENGTH, [0, -0.12, 0], [0.04, 0.2, -0.25])
                const appear = ease((t - s - 0.6) / 1.2)
                const sizePx = 230
                icon.position.copy(worldAt(960, 300, iconF))
                icon.scale.setScalar(sizePx * worldPerPixel(iconF))
                icon.material.uniforms.opacity.value = appear
                placeGlow(halo, 960, 300, iconF * 1.01, 640, 0.3 * appear)
                const p = path(t)
                lumi.update({ x: p.x, y: p.y, f: p.f, size: p.s, t, vx: p.vx, light: 1.2 })
                trail.update((time) => path(time), t, 6.5, { start: s - 0.3 })
            },
        }
    })())

    return shots
}
