// "A Tai Chi break": while your agents build, find your calm. Draws any
// moment of the film from timeline time; ?render=JOB streams frames to
// tools/render.mjs, otherwise the page plays a preview (?t= to start later).
import {
    HalfFloatType, LinearSRGBColorSpace, Mesh, NoToneMapping, OrthographicCamera, PlaneGeometry, Scene,
    ShaderMaterial, SRGBColorSpace, Vector2, WebGLRenderTarget, WebGLRenderer,
} from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { FRAME_HEIGHT, FRAME_WIDTH, PORTRAIT } from './aspect.js'
import { createOverlay } from './overlay.js'
import { CUTS, LENGTH, buildShots } from './shots.js'

const params = new URLSearchParams(location.search)
const job = params.get('render')
const width = Number(params.get('width') ?? FRAME_WIDTH)
const height = Number(params.get('height') ?? FRAME_HEIGHT)
const fps = Number(params.get('fps') ?? 30)
// Cross-dissolves at the cuts: [time, seconds, light]. A light dissolve
// passes through a warm glow, the screen's light opening into dawn.
const DISSOLVES = [
    [CUTS.ledge, 1.2, 1], [CUTS.courtyard, 1.0, 0], [CUTS.pair, 0.9, 0], [CUTS.back, 1.2, 1], [CUTS.card, 1.1, 0],
]

// Words on screen, in film time. A portrait frame keeps them inside the
// area that TikTok, Shorts and Reels leave clear: below the top 220 px,
// above the bottom 420 px and away from the buttons on the right.
function portraitTitles(overlay, t) {
    overlay.begin()
    overlay.line('your agents are building.', t, 1.3, 5.6, { y: 1350, size: 64, x: 520 })
    overlay.line('you don’t have to\nwatch every line.', t, 6.5, 11.2, { y: 1330, size: 64, x: 520 })
    overlay.line('step away for a moment.', t, CUTS.ledge + 0.9, CUTS.courtyard - 0.3, { y: 520, size: 62, x: 520 })
    overlay.line('find your calm', t, CUTS.courtyard + 0.8, CUTS.courtyard + 5.0, { x: 80, align: 'left', y: 470, size: 76 })
    overlay.line('while they work.', t, CUTS.courtyard + 1.3, CUTS.courtyard + 5.0, { x: 80, align: 'left', y: 562, size: 76 })
    overlay.title('Tai Chi in Inner Breeze', 'a guided course with spoken lessons', t, CUTS.courtyard + 5.6, CUTS.pair - 0.2, { x: 80, y: 470, size: 68, sublineSize: 34 })
    overlay.movement('Wave Hands Like Clouds', 'movement 10 of 24', t, CUTS.courtyard + 1.2, CUTS.pair - 0.4, { x: 80, y: 290 })
    overlay.fact('the full 24-form, in 8 lessons', t, CUTS.pair + 0.7, CUTS.pair + 3.5, { x: 80, y: 520, size: 46 })
    overlay.fact('spoken guidance in 12 languages', t, CUTS.pair + 3.8, CUTS.pair + 6.6, { x: 80, y: 520, size: 46 })
    overlay.fact('a female or male voice', t, CUTS.pair + 6.9, CUTS.back - 0.4, { x: 80, y: 520, size: 46 })
    overlay.movement('Part the Wild Horse’s Mane', 'movement 2 of 24', t, CUTS.pair + 0.9, CUTS.back - 0.5, { x: 80, y: 290 })
    overlay.line('back to your project,\nwith a clear head.', t, CUTS.back + 2.8, CUTS.card - 0.2, { y: 1330, size: 62, x: 520 })
    overlay.card(t, CUTS.card + 0.8, LENGTH + 1, { y: 1010 })
    overlay.end()
}

function titles(overlay, t) {
    if (PORTRAIT) {
        portraitTitles(overlay, t)
        return
    }
    overlay.begin()
    overlay.line('your agents are building.', t, 1.3, 5.6)
    overlay.line('you don’t have to watch every line.', t, 6.5, 11.2)
    overlay.line('step away for a moment.', t, CUTS.ledge + 0.9, CUTS.courtyard - 0.3)
    overlay.line('find your calm', t, CUTS.courtyard + 0.8, CUTS.courtyard + 5.0, { x: 150, align: 'left', y: 800, size: 72 })
    overlay.line('while they work.', t, CUTS.courtyard + 1.3, CUTS.courtyard + 5.0, { x: 150, align: 'left', y: 890, size: 72 })
    overlay.title('Tai Chi in Inner Breeze', 'a guided course with spoken lessons', t, CUTS.courtyard + 5.6, CUTS.pair - 0.2, { x: 150, y: 760 })
    overlay.movement('Wave Hands Like Clouds', 'movement 10 of 24', t, CUTS.courtyard + 1.2, CUTS.pair - 0.4)
    overlay.fact('the full 24-form, in 8 lessons', t, CUTS.pair + 0.7, CUTS.pair + 3.5)
    overlay.fact('spoken guidance in 12 languages', t, CUTS.pair + 3.8, CUTS.pair + 6.6)
    overlay.fact('a female or male voice', t, CUTS.pair + 6.9, CUTS.back - 0.4)
    overlay.movement('Part the Wild Horse’s Mane', 'movement 2 of 24', t, CUTS.pair + 0.9, CUTS.back - 0.5)
    overlay.line('back to your project, with a clear head.', t, CUTS.back + 2.8, CUTS.card - 0.2)
    overlay.card(t, CUTS.card + 0.8, LENGTH + 1)
    overlay.end()
}

function report(text) {
    if (job) {
        fetch(`/render/${job}/log`, { method: 'POST', body: text })
    }
    console.log(text)
}

async function main() {
    await Promise.all(['bold 40px Quicksand', '40px "Quicksand Medium"', '40px "Quicksand Light"', '40px "Noto Sans Mono"', '600 40px "Noto Sans Mono"']
        .map((font) => document.fonts.load(font).catch(() => null)))
    const canvas = document.getElementById('film')
    const renderer = new WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: Boolean(job), alpha: false })
    renderer.setPixelRatio(1)
    renderer.setSize(width, height, false)
    renderer.toneMapping = NoToneMapping
    renderer.outputColorSpace = SRGBColorSpace

    const shots = await buildShots()
    const overlay = createOverlay(width, height)
    report(`built ${shots.length} shots`)

    const targets = [0, 1].map(() => new WebGLRenderTarget(width, height, { type: HalfFloatType, colorSpace: LinearSRGBColorSpace, samples: 4 }))
    const mixMaterial = new ShaderMaterial({
        uniforms: {
            a: { value: targets[0].texture }, b: { value: targets[1].texture }, k: { value: 0 }, light: { value: 0 }, debug: { value: params.has('debug') ? 1 : 0 },
            shape: { value: PORTRAIT ? new Vector2(1.0, 1.78) : new Vector2(1.6, 1.0) },
        },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D a; uniform sampler2D b; uniform float k; uniform float light; uniform float debug; uniform vec2 shape;
varying vec2 vUv;
void main() {
    vec4 c = mix(texture2D(a, vUv), texture2D(b, vUv), k);
    // A light dissolve blooms through warm white at its middle.
    float swell = sin(3.14159265 * k);
    swell *= swell * light;
    vec2 d = (vUv - vec2(0.5, 0.62)) * shape;
    float centre = exp(-dot(d, d) * 3.0);
    c.rgb = mix(c.rgb, vec3(1.0, 0.91, 0.78) * (0.8 + centre * 0.4), swell * (0.28 + centre * 0.26));
    bool bad = any(isnan(c)) || any(isinf(c)) || max(c.r, max(c.g, c.b)) > 60.0;
    if (bad) c = debug > 0.5 ? vec4(1.0, 0.0, 1.0, 1.0) : vec4(0.0, 0.0, 0.0, 1.0);
    gl_FragColor = c;
}`,
        depthTest: false, depthWrite: false,
    })
    const mixScene = new Scene()
    mixScene.add(new Mesh(new PlaneGeometry(2, 2), mixMaterial))
    const mixCamera = new OrthographicCamera(-1, 1, 1, -1, 0, 1)

    const composer = new EffectComposer(renderer, new WebGLRenderTarget(width, height, { type: HalfFloatType }))
    composer.setPixelRatio(1)
    composer.setSize(width, height)
    composer.addPass(new RenderPass(mixScene, mixCamera))
    composer.addPass(new UnrealBloomPass(new Vector2(width, height), 0.42, 0.6, 0.86))
    const grade = new ShaderPass({
        uniforms: { tDiffuse: { value: null }, frame: { value: 0 }, fade: { value: 1 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D tDiffuse; uniform float frame; uniform float fade; varying vec2 vUv;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + frame * 0.618) * 43758.5453); }
void main() {
    vec4 c = texture2D(tDiffuse, vUv);
    vec2 d = vUv - 0.5;
    c.rgb *= 1.0 - dot(d, d) * 0.6;
    c.rgb += (hash(vUv * 1000.0) - 0.5) * 0.012;
    gl_FragColor = vec4(max(c.rgb, 0.0) * fade, 1.0);
}`,
    })
    composer.addPass(grade)
    composer.addPass(new OutputPass())
    // Titles go over the finished, display-encoded picture.
    const titlesPass = new ShaderPass({
        uniforms: { tDiffuse: { value: null }, words: { value: overlay.map }, fade: { value: 1 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D tDiffuse; uniform sampler2D words; uniform float fade; varying vec2 vUv;
void main() {
    vec4 c = texture2D(tDiffuse, vUv);
    vec4 w = texture2D(words, vUv) * fade;
    gl_FragColor = vec4(c.rgb * (1.0 - w.a) + w.rgb, 1.0);
}`,
    })
    // ShaderPass clones its uniforms; the canvas texture itself must be the
    // one sampled, or its updates never upload.
    titlesPass.uniforms.words.value = overlay.map
    composer.addPass(titlesPass)

    function windowOf(index) {
        const shot = shots[index]
        const before = DISSOLVES.find(([time]) => Math.abs(time - shot.start) < 1e-6)
        const after = DISSOLVES.find(([time]) => Math.abs(time - shot.end) < 1e-6)
        return [shot.start - (before ? before[1] / 2 : 0), shot.end + (after ? after[1] / 2 : 0)]
    }

    function drawShot(shot, t, target) {
        shot.update(t, renderer)
        renderer.setRenderTarget(target)
        renderer.setClearColor(0x000000, 1)
        renderer.clear()
        renderer.render(shot.scene, shot.camera)
        renderer.setRenderTarget(null)
    }

    function draw(t, frame) {
        const active = shots.map((_, index) => index).filter((index) => {
            const [from, to] = windowOf(index)
            return t >= from && t < to
        })
        if (active.length === 0) {
            active.push(t < 1 ? 0 : shots.length - 1)
        }
        drawShot(shots[active[0]], t, targets[0])
        let k = 0
        let light = 0
        if (active.length > 1) {
            drawShot(shots[active[1]], t, targets[1])
            const [time, length, glowing] = DISSOLVES.find(([time]) => Math.abs(time - shots[active[1]].start) < 1e-6)
            const x = (t - (time - length / 2)) / length
            k = x * x * (3 - 2 * x)
            light = glowing
        }
        mixMaterial.uniforms.k.value = k
        mixMaterial.uniforms.light.value = light
        grade.uniforms.frame.value = frame
        const fade = Math.min(1, t / 0.8, (LENGTH - t) / 0.6)
        grade.uniforms.fade.value = fade
        titlesPass.uniforms.fade.value = Math.min(1, (LENGTH - t) / 0.6)
        titles(overlay, t)
        composer.render()
    }

    if (job) {
        const from = Number(params.get('from') ?? 0)
        const to = Number(params.get('to') ?? LENGTH)
        const stills = params.get('stills') ? params.get('stills').split(',').map(Number) : null
        const times = stills ?? Array.from({ length: Math.round((to - from) * fps) }, (_, index) => from + index / fps)
        for (let index = 0; index < times.length; index += 1) {
            draw(times[index], Math.round(times[index] * fps))
            let body
            if (stills) {
                body = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
            } else {
                const gl = renderer.getContext()
                body = new Uint8Array(width * height * 4)
                gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, body)
            }
            for (let attempt = 0; ; attempt += 1) {
                try {
                    const response = await fetch(`/render/${job}/frame/${index}`, { method: 'POST', body })
                    if (response.ok) {
                        break
                    }
                } catch (error) {
                    if (attempt >= 6) {
                        throw error
                    }
                }
                await new Promise((resolve) => setTimeout(resolve, 300 * (attempt + 1)))
            }
        }
        await fetch(`/render/${job}/done`, { method: 'POST', body: JSON.stringify({ frames: times.length }) })
        return
    }

    const hud = document.getElementById('hud')
    let start = performance.now() / 1000 - Number(params.get('t') ?? 0)
    function tick() {
        let t = performance.now() / 1000 - start
        if (t > LENGTH) {
            start += LENGTH
            t -= LENGTH
        }
        draw(t, Math.round(t * fps))
        hud.textContent = t.toFixed(2)
        requestAnimationFrame(tick)
    }
    tick()
}

main().catch((error) => {
    report(`ERROR ${error?.stack ?? error}`)
    if (job) {
        fetch(`/render/${job}/error`, { method: 'POST', body: String(error?.stack ?? error) })
    }
})
