// The 2.5D world every shot shares: a painted plate pushed into depth by
// its depth map, cutout characters on their own planes, and the light
// effects drawn over them. Positions are given in plate pixels (1920x1080)
// and a distance factor `f` (1 = the plate's far plane, smaller = nearer).
import {
    AdditiveBlending, BufferAttribute, BufferGeometry, CanvasTexture, Color, CustomBlending, DoubleSide,
    LinearFilter, Mesh, OneFactor, OneMinusSrcAlphaFactor, PerspectiveCamera, PlaneGeometry, Points,
    SRGBColorSpace, ShaderMaterial, TextureLoader, Vector3,
} from 'three'

export const WIDTH = 1920
export const HEIGHT = 1080
export const ASPECT = WIDTH / HEIGHT
export const FAR = 10
// The plate fills a 40-degree frustum; shots film it at 37 degrees, which
// leaves a margin so the camera can move without showing an edge.
export const PLATE_FOV = 40
export const FILM_FOV = 37
const HALF_H = Math.tan((PLATE_FOV * Math.PI) / 360)
const HALF_W = HALF_H * ASPECT
// How far the nearest depth (1) sits towards the camera, as a share of FAR.
export const DEPTH_REACH = 0.62

const loader = new TextureLoader()
const cache = new Map()

export function texture(url, { srgb = true } = {}) {
    if (!cache.has(url)) {
        cache.set(url, loader.loadAsync(url).then((map) => {
            if (srgb) {
                map.colorSpace = SRGBColorSpace
            }
            map.minFilter = LinearFilter
            map.generateMipmaps = false
            return map
        }))
    }
    return cache.get(url)
}

// Reads a depth map back so shots can place things "on" the painting.
export async function depthSampler(url) {
    const map = await texture(url, { srgb: false })
    const image = map.image
    const canvas = document.createElement('canvas')
    canvas.width = image.width
    canvas.height = image.height
    const context = canvas.getContext('2d', { willReadFrequently: true })
    context.drawImage(image, 0, 0)
    const data = context.getImageData(0, 0, image.width, image.height).data
    return (px, py) => {
        const x = Math.min(image.width - 1, Math.max(0, Math.round((px / WIDTH) * image.width)))
        const y = Math.min(image.height - 1, Math.max(0, Math.round((py / HEIGHT) * image.height)))
        return data[(y * image.width + x) * 4] / 255
    }
}

export function distanceFactor(depth) {
    return 1 - DEPTH_REACH * depth
}

// The world point that the starting camera sees at plate pixel (px, py),
// at distance factor f.
export function worldAt(px, py, f = 1, out = new Vector3()) {
    const nx = (px / WIDTH) * 2 - 1
    const ny = 1 - (py / HEIGHT) * 2
    return out.set(nx * HALF_W * FAR * f, ny * HALF_H * FAR * f, -FAR * f)
}

// World units per plate pixel at distance factor f.
export function worldPerPixel(f = 1) {
    return (2 * HALF_H * FAR * f) / HEIGHT
}

export function filmCamera() {
    const camera = new PerspectiveCamera(FILM_FOV, ASPECT, 0.05, 100)
    camera.position.set(0, 0, 0)
    return camera
}

// --- Shader helpers ------------------------------------------------------

const NOISE = /* glsl */ `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.03 + 17.0; a *= 0.5; }
    return v;
}
`

// Effects a plate can switch on. Rects are plate-pixel boxes [x0, y0, x1, y1].
const PLATE_EFFECTS = /* glsl */ `
uniform float time;
uniform vec4 waterRect; uniform float waterAmount; uniform float waterMaxDepth;
uniform vec4 flowRect; uniform float flowAmount; uniform float flowMaxDepth;
uniform float windAmount; uniform float windMinDepth;
uniform vec4 rainRect; uniform float rainAmount;
uniform vec4 starRect; uniform float starAmount;
uniform vec4 flagRect; uniform float flagAmount;
uniform vec3 raysOrigin; uniform float raysAmount;
uniform vec3 tint; uniform float exposure;

float inRect(vec2 px, vec4 r, float soft) {
    vec2 a = smoothstep(r.xy - soft, r.xy + soft, px);
    vec2 b = 1.0 - smoothstep(r.zw - soft, r.zw + soft, px);
    return a.x * a.y * b.x * b.y;
}
`

const plateVertex = /* glsl */ `
uniform sampler2D depthMap;
uniform float reach;
uniform float far;
uniform vec2 halfSize;
uniform vec4 region; // the plate part this mesh shows, in uv (x0, y0, x1, y1), y up
uniform float flatDepth; // >= 0: one depth for the whole mesh
uniform float breath; uniform float breathAmount; uniform float hipY; uniform vec2 sway;
varying vec2 vUv;
varying float vDepth;
void main() {
    vUv = uv;
    vec2 plateUv = mix(region.xy, region.zw, uv);
    float d = flatDepth >= 0.0 ? flatDepth : texture2D(depthMap, plateUv).r;
    vDepth = d;
    float f = 1.0 - reach * d;
    vec2 ndc = plateUv * 2.0 - 1.0;
    // Characters breathe: everything above the hips lifts with the chest.
    float above = max(0.0, uv.y - hipY);
    ndc.y += above * breathAmount * breath * (region.w - region.y) * 2.0;
    // and sway a little around the hips.
    ndc.x += above * sway.x * (region.w - region.y) * 2.0;
    vec3 p = vec3(ndc.x * halfSize.x * far, ndc.y * halfSize.y * far, -far) * f;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}
`

const plateFragment = /* glsl */ `
uniform sampler2D map;
uniform vec4 region;
uniform float opacity;
varying vec2 vUv;
varying float vDepth;
${NOISE}
${PLATE_EFFECTS}
void main() {
    vec2 uv = mix(region.xy, region.zw, vUv);
    vec2 px = vec2(uv.x * ${WIDTH}.0, (1.0 - uv.y) * ${HEIGHT}.0);
    vec2 offset = vec2(0.0);
    // Water: rippled reflections.
    float water = waterAmount * inRect(px, waterRect, 12.0) * (1.0 - smoothstep(waterMaxDepth - 0.05, waterMaxDepth + 0.05, vDepth));
    offset.x += water * (sin(px.y * 0.55 + time * 2.1) * 0.6 + sin(px.y * 1.3 - time * 3.3) * 0.4) * 0.0016;
    offset.y += water * sin(px.x * 0.05 + time * 1.4) * 0.0004;
    // Clouds and mist boil slowly.
    float flow = flowAmount * inRect(px, flowRect, 40.0) * (1.0 - smoothstep(flowMaxDepth - 0.05, flowMaxDepth + 0.05, vDepth));
    offset += flow * vec2(fbm(uv * 4.0 + vec2(time * 0.05, 0.0)) - 0.5, fbm(uv * 5.0 - vec2(0.0, time * 0.04)) - 0.5) * 0.010;
    // Reeds and leaves in the wind: near things sway, more towards the tips.
    float wind = windAmount * smoothstep(windMinDepth, windMinDepth + 0.15, vDepth);
    offset.x += wind * (sin(time * 1.3 + uv.x * 9.0) * 0.6 + sin(time * 2.7 + uv.y * 13.0) * 0.4) * 0.0035 * uv.y;
    // Prayer flags flutter.
    vec4 flagColor = texture2D(map, uv);
    float flagSat = max(flagColor.r, max(flagColor.g, flagColor.b)) - min(flagColor.r, min(flagColor.g, flagColor.b));
    float flag = flagAmount * inRect(px, flagRect, 20.0) * smoothstep(0.30, 0.45, flagSat);
    offset.y += flag * sin(px.x * 0.09 + time * 6.0) * 0.0018;
    offset.x += flag * sin(px.y * 0.07 + time * 4.0) * 0.0008;

    vec4 color = texture2D(map, uv + offset);
    float lum = dot(color.rgb, vec3(0.299, 0.587, 0.114));
    // Glints on the water.
    color.rgb *= 1.0 + water * 0.12 * smoothstep(0.35, 0.9, lum) * sin(px.y * 0.9 - time * 4.0 + noise(px * 0.05) * 6.0);
    // Rain down the window glass.
    float glass = rainAmount * inRect(px, rainRect, 10.0) * step(color.r + 0.03, color.b) * (1.0 - smoothstep(0.25, 0.45, lum));
    float column = floor(px.x / 5.0);
    float fall = fract(px.y / 260.0 - time * (0.9 + hash(vec2(column, 3.0)) * 0.8) + hash(vec2(column, 7.0)));
    float drop = smoothstep(0.0, 0.03, fall) * (1.0 - smoothstep(0.03, 0.22, fall)) * step(0.72, hash(vec2(column, 11.0)));
    color.rgb += glass * drop * vec3(0.35, 0.42, 0.55);
    // Stars twinkle.
    float star = starAmount * inRect(px, starRect, 30.0) * smoothstep(0.42, 0.75, lum);
    color.rgb *= 1.0 + star * (sin(time * (2.0 + hash(floor(px / 3.0)) * 4.0) + hash(floor(px / 3.0) + 9.0) * 6.28) * 0.45);
    // Light shafts breathe.
    vec2 toPx = px - raysOrigin.xy;
    float angle = atan(toPx.y, toPx.x);
    float shaft = pow(0.5 + 0.5 * sin(angle * 38.0 + time * 0.35 + sin(angle * 11.0 - time * 0.2) * 2.0), 3.0);
    color.rgb += raysAmount * shaft * smoothstep(0.45, 0.85, lum) * vec3(1.0, 0.72, 0.42) * 0.22;
    color.rgb *= tint * exposure;
    gl_FragColor = vec4(color.rgb, color.a * opacity);
    #include <colorspace_fragment>
}
`

function plateUniforms(map, depthMap) {
    return {
        map: { value: map },
        depthMap: { value: depthMap },
        reach: { value: DEPTH_REACH },
        far: { value: FAR },
        halfSize: { value: [HALF_W, HALF_H] },
        region: { value: [0, 0, 1, 1] },
        flatDepth: { value: -1 },
        opacity: { value: 1 },
        breath: { value: 0 },
        breathAmount: { value: 0 },
        hipY: { value: 0.4 },
        sway: { value: [0, 0] },
        time: { value: 0 },
        waterRect: { value: [0, 0, 0, 0] }, waterAmount: { value: 0 }, waterMaxDepth: { value: 1 },
        flowRect: { value: [0, 0, 0, 0] }, flowAmount: { value: 0 }, flowMaxDepth: { value: 1 },
        windAmount: { value: 0 }, windMinDepth: { value: 0.6 },
        rainRect: { value: [0, 0, 0, 0] }, rainAmount: { value: 0 },
        starRect: { value: [0, 0, 0, 0] }, starAmount: { value: 0 },
        flagRect: { value: [0, 0, 0, 0] }, flagAmount: { value: 0 },
        raysOrigin: { value: [0, 0, 0] }, raysAmount: { value: 0 },
        tint: { value: new Color(1, 1, 1) },
        exposure: { value: 1 },
    }
}

// The painted background, pushed into depth.
export async function plate(name, effects = {}) {
    const [map, depthMap] = await Promise.all([texture(`plates/${name}.jpg`), texture(`plates/${name}-depth.png`, { srgb: false })])
    const uniforms = plateUniforms(map, depthMap)
    for (const [key, value] of Object.entries(effects)) {
        if (uniforms[key]) {
            uniforms[key].value = value
        }
    }
    const material = new ShaderMaterial({ uniforms, vertexShader: plateVertex, fragmentShader: plateFragment })
    const mesh = new Mesh(new PlaneGeometry(1, 1, 320, 180), material)
    mesh.frustumCulled = false
    mesh.renderOrder = 0
    return { mesh, uniforms, depth: await depthSampler(`plates/${name}-depth.png`) }
}

// A cutout character from plates/NAME-mia.png, standing at one depth over
// its box of the plate. It breathes and sways around its hips.
export async function cutout(name, meta, { hipY = 0.42, depth, scale = 1 } = {}) {
    const map = await texture(`plates/${name}-mia.webp`)
    const uniforms = plateUniforms(map, map)
    // `scale` shrinks the figure around the middle of its feet.
    const [bx0, by0, bx1, by1] = meta.box
    const footX = (bx0 + bx1) / 2
    const [x0, y0, x1, y1] = [footX + (bx0 - footX) * scale, by1 - (by1 - by0) * scale, footX + (bx1 - footX) * scale, by1]
    uniforms.region.value = [x0 / WIDTH, 1 - y1 / HEIGHT, x1 / WIDTH, 1 - y0 / HEIGHT]
    uniforms.flatDepth.value = depth ?? meta.depth
    uniforms.hipY.value = hipY
    const material = new ShaderMaterial({
        uniforms, vertexShader: plateVertex,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform float opacity; uniform vec3 tint; uniform float exposure;
varying vec2 vUv;
void main() {
    vec4 color = texture2D(map, vUv);
    gl_FragColor = vec4(color.rgb * tint * exposure, color.a * opacity);
    #include <colorspace_fragment>
}`,
        transparent: true, depthWrite: false,
    })
    const mesh = new Mesh(new PlaneGeometry(1, 1, 48, 64), material)
    mesh.frustumCulled = false
    mesh.renderOrder = 5
    return { mesh, uniforms }
}

// --- Light -----------------------------------------------------------------

function canvasTexture(size, draw) {
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    draw(canvas.getContext('2d'), size)
    const map = new CanvasTexture(canvas)
    map.colorSpace = SRGBColorSpace
    return map
}

export const glowTexture = canvasTexture(256, (c, s) => {
    const g = c.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2)
    g.addColorStop(0, 'rgba(255,255,255,1)')
    g.addColorStop(0.18, 'rgba(255,255,255,0.55)')
    g.addColorStop(0.45, 'rgba(255,255,255,0.14)')
    g.addColorStop(1, 'rgba(255,255,255,0)')
    c.fillStyle = g
    c.fillRect(0, 0, s, s)
})

export const ringTexture = canvasTexture(512, (c, s) => {
    const g = c.createRadialGradient(s / 2, s / 2, s * 0.36, s / 2, s / 2, s / 2)
    g.addColorStop(0, 'rgba(255,255,255,0)')
    g.addColorStop(0.45, 'rgba(255,255,255,0.9)')
    g.addColorStop(0.62, 'rgba(255,255,255,0.35)')
    g.addColorStop(1, 'rgba(255,255,255,0)')
    c.fillStyle = g
    c.fillRect(0, 0, s, s)
})

// A soft additive sprite that always faces the camera's axis.
export function glow(color, size = 1) {
    const material = new ShaderMaterial({
        uniforms: { map: { value: glowTexture }, color: { value: new Color(color) }, intensity: { value: 1 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform vec3 color; uniform float intensity; varying vec2 vUv;
void main() { float a = texture2D(map, vUv).a; gl_FragColor = vec4(color * a * intensity, 1.0); }`,
        blending: AdditiveBlending, transparent: true, depthWrite: false, depthTest: false,
    })
    const mesh = new Mesh(new PlaneGeometry(size, size), material)
    mesh.renderOrder = 20
    mesh.frustumCulled = false
    return mesh
}

export function ring(color, size = 1, map = ringTexture) {
    const mesh = glow(color, size)
    mesh.material.uniforms.map.value = map
    return mesh
}

// Drifting motes: fireflies, dust in sunbeams, sparkles. Every position is a
// function of time, so any frame can be rendered on its own.
export function motes({ count, box, f = [0.5, 0.9], color = '#ffd27a', size = [6, 14], drift = 30, blink = 0.6, seed = 1, speed = 1 }) {
    const geometry = new BufferGeometry()
    const seedA = new Float32Array(count * 4)
    for (let index = 0; index < count; index += 1) {
        const r = (k) => {
            const v = Math.sin((index + 1) * 12.9898 + seed * 78.233 + k * 37.719) * 43758.5453
            return v - Math.floor(v)
        }
        seedA.set([r(1), r(2), r(3), r(4)], index * 4)
    }
    geometry.setAttribute('position', new BufferAttribute(new Float32Array(count * 3), 3))
    geometry.setAttribute('seed', new BufferAttribute(seedA, 4))
    const material = new ShaderMaterial({
        uniforms: {
            time: { value: 0 }, color: { value: new Color(color) }, box: { value: box }, fRange: { value: f },
            sizeRange: { value: size }, drift: { value: drift }, blink: { value: blink }, map: { value: glowTexture },
            halfSize: { value: [HALF_W, HALF_H] }, far: { value: FAR }, opacity: { value: 1 }, speed: { value: speed },
            pixelScale: { value: 1 },
        },
        vertexShader: /* glsl */ `
attribute vec4 seed;
uniform float time; uniform vec4 box; uniform vec2 fRange; uniform vec2 sizeRange; uniform float drift; uniform float speed;
uniform vec2 halfSize; uniform float far; uniform float pixelScale;
varying float vSeed;
void main() {
    vSeed = seed.w;
    float t = time * speed;
    vec2 px = mix(box.xy, box.zw, seed.xy);
    px += vec2(sin(t * (0.3 + seed.z * 0.5) + seed.w * 6.28), cos(t * (0.25 + seed.x * 0.4) + seed.z * 6.28)) * drift;
    float f = mix(fRange.x, fRange.y, seed.z);
    vec2 ndc = vec2(px.x / ${WIDTH}.0 * 2.0 - 1.0, 1.0 - px.y / ${HEIGHT}.0 * 2.0);
    vec4 mv = modelViewMatrix * vec4(vec3(ndc * halfSize * far, -far) * f, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = mix(sizeRange.x, sizeRange.y, seed.w) * pixelScale * (far * f) / -mv.z;
}`,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform vec3 color; uniform float time; uniform float blink; uniform float opacity;
varying float vSeed;
void main() {
    float a = texture2D(map, gl_PointCoord).a;
    float on = 1.0 - blink + blink * (0.5 + 0.5 * sin(time * (1.5 + vSeed * 2.5) + vSeed * 40.0));
    gl_FragColor = vec4(color * a * on * opacity * 1.6, 1.0);
}`,
        blending: AdditiveBlending, transparent: true, depthWrite: false,
    })
    const points = new Points(geometry, material)
    points.frustumCulled = false
    points.renderOrder = 15
    return points
}

// A soft fog band drawn over a plate region, at one distance.
export function mist({ box, f = 0.8, color = '#ffffff', amount = 0.25, scale = 3, speed = 0.03 }) {
    const [x0, y0, x1, y1] = box
    const a = worldAt(x0, y0, f)
    const b = worldAt(x1, y1, f)
    const material = new ShaderMaterial({
        uniforms: { time: { value: 0 }, color: { value: new Color(color) }, amount: { value: amount }, scale: { value: scale }, speed: { value: speed } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform float time; uniform vec3 color; uniform float amount; uniform float scale; uniform float speed;
varying vec2 vUv;
${NOISE}
void main() {
    vec2 p = vUv * vec2(scale * 2.0, scale) + vec2(time * speed, time * speed * 0.3);
    float n = fbm(p) * 0.7 + fbm(p * 2.3 - vec2(time * speed * 1.7, 0.0)) * 0.3;
    float edge = smoothstep(0.0, 0.25, vUv.x) * smoothstep(1.0, 0.75, vUv.x) * smoothstep(0.0, 0.35, vUv.y) * smoothstep(1.0, 0.6, vUv.y);
    float a = smoothstep(0.35, 0.8, n) * edge * amount;
    gl_FragColor = vec4(color, a);
    #include <colorspace_fragment>
}`,
        transparent: true, depthWrite: false,
    })
    const mesh = new Mesh(new PlaneGeometry(Math.abs(b.x - a.x), Math.abs(a.y - b.y)), material)
    mesh.position.set((a.x + b.x) / 2, (a.y + b.y) / 2, a.z)
    mesh.renderOrder = 8
    mesh.frustumCulled = false
    return mesh
}

// A premultiplied picture on a plane (render-target puppets).
export function premultipliedPlane(map) {
    const material = new ShaderMaterial({
        uniforms: { map: { value: map }, tint: { value: new Color(1, 1, 1) }, opacity: { value: 1 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform vec3 tint; uniform float opacity; varying vec2 vUv;
void main() { vec4 c = texture2D(map, vUv); gl_FragColor = vec4(c.rgb * tint, c.a) * opacity; }`,
        transparent: true, depthWrite: false, side: DoubleSide,
        blending: CustomBlending, blendSrc: OneFactor, blendDst: OneMinusSrcAlphaFactor,
    })
    const mesh = new Mesh(new PlaneGeometry(1, 1), material)
    mesh.renderOrder = 6
    mesh.frustumCulled = false
    return mesh
}

export function ease(x) {
    const t = Math.min(1, Math.max(0, x))
    return t * t * (3 - 2 * t)
}

export function lerp(a, b, t) {
    return a + (b - a) * t
}

// Catmull-Rom through keyed rows { t, ...numbers }, clamped at both ends.
export function track(keys) {
    const names = Object.keys(keys[0]).filter((name) => name !== 't')
    return (t) => {
        let index = keys.findIndex((key) => key.t > t)
        if (index === -1) {
            return { ...keys[keys.length - 1] }
        }
        if (index === 0) {
            return { ...keys[0] }
        }
        const p1 = keys[index - 1]
        const p2 = keys[index]
        const p0 = keys[index - 2] ?? p1
        const p3 = keys[index + 1] ?? p2
        const u = (t - p1.t) / (p2.t - p1.t)
        const out = { t }
        for (const name of names) {
            const a = p0[name], b = p1[name], c = p2[name], d = p3[name]
            out[name] = 0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u)
        }
        return out
    }
}
