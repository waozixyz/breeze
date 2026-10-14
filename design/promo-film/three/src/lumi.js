// Lumi: the eight-frame wing-cycle painting on a plane, her tummy and
// antenna glows, and a golden trail drawn along the path she flew.
import {
    AdditiveBlending, BufferAttribute, BufferGeometry, Color, Group, Mesh, PlaneGeometry, ShaderMaterial,
} from 'three'
import { glow, texture, worldAt, worldPerPixel } from './world.js'

const SHEET = '/design/lumi-promo/lumi-flight-cycle.png'
const WING_FPS = 16
// Points in one frame of the sheet, as fractions (x right, y down).
const TUMMY = [0.52, 0.72]
const BULBS = [[0.367, 0.298], [0.829, 0.38]]

export async function createLumi() {
    const sheet = await texture(SHEET)
    const material = new ShaderMaterial({
        uniforms: { map: { value: sheet }, frame: { value: 0 }, flip: { value: 0 }, opacity: { value: 1 }, warmth: { value: 1 } },
        vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform sampler2D map; uniform float frame; uniform float flip; uniform float opacity; uniform float warmth;
varying vec2 vUv;
void main() {
    vec2 uv = vUv;
    if (flip > 0.5) uv.x = 1.0 - uv.x;
    float column = mod(frame, 4.0);
    float row = floor(frame / 4.0);
    vec2 cell = vec2((column + uv.x) / 4.0, 1.0 - (row + 1.0 - uv.y) / 2.0);
    vec4 c = texture2D(map, cell);
    gl_FragColor = vec4(c.rgb * warmth, c.a * opacity);
    #include <colorspace_fragment>
}`,
        transparent: true, depthWrite: false,
    })
    const body = new Mesh(new PlaneGeometry(1, 1), material)
    body.renderOrder = 12
    body.frustumCulled = false
    const halo = glow('#ffcf6a', 1)
    const tummy = glow('#fff1b0', 1)
    const bulbs = BULBS.map(() => glow('#ffe08a', 1))
    const group = new Group()
    group.add(halo, body, tummy, ...bulbs)
    halo.renderOrder = 11

    let facingLeft = false
    return {
        group,
        // state: { x, y (plate px), f, size (px tall at the plate), t, vx, glow, opacity, face }
        update({ x, y, f, size, t, vx = 0, light = 1, opacity = 1, face, spark = 0 }) {
            const position = worldAt(x, y, f)
            const unit = worldPerPixel(f)
            const height = size * unit
            group.position.copy(position)
            body.scale.set(height, height, 1)
            if (face !== undefined) {
                facingLeft = face < 0
            } else if (Math.abs(vx) > 25) {
                facingLeft = vx < 0
            }
            const flip = facingLeft ? 1 : 0
            material.uniforms.flip.value = flip
            material.uniforms.frame.value = Math.floor(t * WING_FPS) % 8
            material.uniforms.opacity.value = opacity
            const local = (point) => [((flip ? 1 - point[0] : point[0]) - 0.5) * height, (0.5 - point[1]) * height]
            const [tx, ty] = local(TUMMY)
            tummy.position.set(tx, ty, 0.001)
            tummy.scale.setScalar(height * 0.75)
            // Before she appears, only her light shows: `spark` keeps it on.
            const lit = Math.max(opacity, spark)
            tummy.material.uniforms.intensity.value = 0.55 * light * lit
            halo.position.set(tx, ty, -0.001)
            halo.scale.setScalar(height * 2.6)
            halo.material.uniforms.intensity.value = 0.32 * light * lit
            BULBS.forEach((point, index) => {
                const [bx, by] = local(point)
                bulbs[index].position.set(bx, by, 0.002)
                bulbs[index].scale.setScalar(height * 0.42)
                bulbs[index].material.uniforms.intensity.value = 0.7 * light * opacity
            })
        },
    }
}

// A glowing ribbon along a path: `path(t)` returns { x, y, f } in plate
// pixels; the ribbon covers [t - length, t], thinning and fading with age.
export function createTrail({ samples = 120, width = 26, color = '#ffd47a', intensity = 1.2 } = {}) {
    const geometry = new BufferGeometry()
    const positions = new Float32Array(samples * 2 * 3)
    const ages = new Float32Array(samples * 2)
    const sides = new Float32Array(samples * 2)
    const index = []
    for (let i = 0; i < samples - 1; i += 1) {
        const a = i * 2
        index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
    }
    for (let i = 0; i < samples; i += 1) {
        sides[i * 2] = -1
        sides[i * 2 + 1] = 1
    }
    geometry.setIndex(index)
    geometry.setAttribute('position', new BufferAttribute(positions, 3))
    geometry.setAttribute('age', new BufferAttribute(ages, 1))
    geometry.setAttribute('side', new BufferAttribute(sides, 1))
    const material = new ShaderMaterial({
        uniforms: { color: { value: new Color(color) }, intensity: { value: intensity }, time: { value: 0 } },
        vertexShader: /* glsl */ `
attribute float age; attribute float side;
varying float vAge; varying float vSide;
void main() { vAge = age; vSide = side; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
uniform vec3 color; uniform float intensity; uniform float time;
varying float vAge; varying float vSide;
float hash(float n) { return fract(sin(n) * 43758.5453); }
void main() {
    float core = exp(-vSide * vSide * 6.0);
    float fade = pow(clamp(1.0 - vAge, 0.0, 1.0), 1.6);
    float sparkle = 0.75 + 0.25 * sin(vAge * 90.0 - time * 9.0);
    gl_FragColor = vec4(color * core * fade * sparkle * intensity, 1.0);
}`,
        blending: AdditiveBlending, transparent: true, depthWrite: false, depthTest: false,
    })
    const mesh = new Mesh(geometry, material)
    mesh.frustumCulled = false
    mesh.renderOrder = 10
    return {
        mesh,
        update(path, t, length, { start = -Infinity, widthScale = 1, alpha = 1 } = {}) {
            const from = Math.max(start, t - length)
            const span = Math.max(1e-3, t - from)
            const points = []
            for (let i = 0; i < samples; i += 1) {
                const time = from + (span * i) / (samples - 1)
                const p = path(time)
                points.push(worldAt(p.x, p.y, p.f))
            }
            for (let i = 0; i < samples; i += 1) {
                const p = points[i]
                const q = points[Math.min(samples - 1, i + 1)]
                const r = points[Math.max(0, i - 1)]
                const dx = q.x - r.x
                const dy = q.y - r.y
                const len = Math.hypot(dx, dy) || 1
                const age = 1 - i / (samples - 1)
                const half = (width * widthScale * worldPerPixel(-p.z / 10)) * (0.25 + 0.75 * (1 - age)) * 0.5
                const nx = (-dy / len) * half
                const ny = (dx / len) * half
                positions.set([p.x + nx, p.y + ny, p.z, p.x - nx, p.y - ny, p.z], i * 6)
                ages[i * 2] = ages[i * 2 + 1] = Math.min(1, age + (1 - alpha))
            }
            geometry.attributes.position.needsUpdate = true
            geometry.attributes.age.needsUpdate = true
            material.uniforms.time.value = t
            mesh.visible = span > 0.05 && alpha > 0.01
        },
    }
}
