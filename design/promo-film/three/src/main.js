// Inner Breeze – A Day with Lumi, the Three.js edition. Draws any moment of
// the 65-second film from timeline time; ?render=JOB streams frames to
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
import { buildShots } from './shots.js'
import { HEIGHT, WIDTH } from './world.js'

const params = new URLSearchParams(location.search)
const job = params.get('render')
const width = Number(params.get('width') ?? WIDTH)
const height = Number(params.get('height') ?? HEIGHT)
const fps = Number(params.get('fps') ?? 24)
const LENGTH = 65
// Cross-dissolves at the clip boundaries: [time, seconds].
const DISSOLVES = [[7.0, 0.7], [13.0, 0.7], [20.0, 0.8], [25.0, 0.6], [29.3, 0.7], [36.8, 0.2], [42.8, 0.8], [51.8, 0.7], [58.8, 1.0]]

function report(text) {
    if (job) {
        fetch(`/render/${job}/log`, { method: 'POST', body: text })
    }
    console.log(text)
}

async function main() {
    const canvas = document.getElementById('film')
    const renderer = new WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: Boolean(job), alpha: false })
    renderer.setPixelRatio(1)
    renderer.setSize(width, height, false)
    renderer.toneMapping = NoToneMapping
    renderer.outputColorSpace = SRGBColorSpace

    const [meta, voiceData] = await Promise.all([
        fetch('plates/meta.json').then((r) => r.json()),
        fetch('voice.json').then((r) => r.json()),
    ])
    const voice = (t) => {
        const index = Math.round(t * voiceData.fps)
        return voiceData.level[Math.min(voiceData.level.length - 1, Math.max(0, index))] ?? 0
    }
    const shots = await buildShots({ meta, voice, renderer })
    report(`built ${shots.length} shots`)

    const targets = [0, 1].map(() => new WebGLRenderTarget(width, height, { type: HalfFloatType, colorSpace: LinearSRGBColorSpace, samples: 4 }))
    const mixMaterial = new ShaderMaterial({
        uniforms: { a: { value: targets[0].texture }, b: { value: targets[1].texture }, k: { value: 0 }, debug: { value: params.has('debug') ? 1 : 0 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D a; uniform sampler2D b; uniform float k; varying vec2 vUv;
uniform float debug;
void main() {
    vec4 c = mix(texture2D(a, vUv), texture2D(b, vUv), k);
    bool bad = any(isnan(c)) || any(isinf(c)) || max(c.r, max(c.g, c.b)) > 60.0;
    // A stray NaN would spread through the bloom into black blocks.
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
    float vignette = 1.0 - dot(d, d) * 0.55;
    c.rgb *= vignette;
    c.rgb += (hash(vUv * 1000.0) - 0.5) * 0.012;
    gl_FragColor = vec4(c.rgb * fade, 1.0);
}`,
    })
    composer.addPass(grade)
    composer.addPass(new OutputPass())

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
        if (active.length > 1) {
            drawShot(shots[active[1]], t, targets[1])
            const [time, length] = DISSOLVES.find(([time]) => Math.abs(time - shots[active[1]].start) < 1e-6)
            const x = (t - (time - length / 2)) / length
            k = x * x * (3 - 2 * x)
        }
        mixMaterial.uniforms.k.value = k
        grade.uniforms.frame.value = frame
        grade.uniforms.fade.value = Math.min(1, t / 0.6, (LENGTH - t) / 0.5)
        composer.render()
    }

    if (job) {
        const from = Number(params.get('from') ?? 0)
        const to = Number(params.get('to') ?? LENGTH)
        const stills = params.get('stills') ? params.get('stills').split(',').map(Number) : null
        const times = stills ?? Array.from({ length: Math.round((to - from) * fps) }, (_, index) => from + index / fps)
        for (let index = 0; index < times.length; index += 1) {
            draw(times[index], Math.round(times[index] * fps))
            // Stills come back as JPEG; video frames as raw RGBA rows read
            // straight from the canvas (bottom row first), which avoids
            // piling up hundreds of megabytes of PNG blobs in the browser.
            let body
            if (stills) {
                body = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92))
            } else {
                const gl = renderer.getContext()
                body = new Uint8Array(width * height * 4)
                gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, body)
            }
            // A dropped upload is retried; frames are written by index.
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
