// Shared warm physical / cool awareness palette. No textures or ray marching.
import { Color, DoubleSide, ShaderMaterial } from 'three'

export const characterLighting = /* glsl */ `
vec3 characterLight(vec3 base, vec3 n, vec3 eye) {
    float diffuse = dot(n, normalize(vec3(-0.5, 0.8, 1.0))) * 0.5 + 0.5;
    float rim = pow(1.0 - abs(dot(n, eye)), 3.0);
    float wrap = pow(max(0.0, dot(-n, normalize(vec3(-0.5, 0.8, 1.0))) + 0.4), 2.0);
    return base * (0.55 + 0.55 * diffuse) + vec3(0.20, 0.09, 0.055) * wrap
        + vec3(0.22, 0.48, 0.55) * rim;
}
`

export function bodyMaterial({ astral = false, color = '#bf8973' } = {}) {
    return new ShaderMaterial({
        uniforms: {
            color: { value: new Color(color) },
            time: { value: 0 },
            astral: { value: astral ? 1 : 0 },
        },
        vertexShader: /* glsl */ `
            varying vec3 vNormal; varying vec3 vEye; varying vec3 vPosition;
            void main() {
                vec4 p = modelViewMatrix * vec4(position, 1.0);
                vNormal = normalize(normalMatrix * normal);
                vEye = -p.xyz;
                vPosition = (modelMatrix * vec4(position, 1.0)).xyz;
                gl_Position = projectionMatrix * p;
            }`,
        fragmentShader: /* glsl */ `
            uniform vec3 color; uniform float time; uniform float astral;
            varying vec3 vNormal; varying vec3 vEye; varying vec3 vPosition;
            ${characterLighting}
            float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1,311.7,74.7))) * 43758.5453); }
            float noise(vec3 p) {
                vec3 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
                return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),
                    mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
                    mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),
                    mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
            }
            void main() {
                vec3 n = normalize(vNormal), eye = normalize(vEye);
                float rim = pow(1.0-abs(dot(n,eye)),2.0);
                float flow = noise(vPosition*5.0-vec3(0.0,time*0.22,0.0));
                vec3 physical = characterLight(color,n,eye) * (1.0 + 0.015*sin(time*1.047));
                vec3 energy = vec3(0.18,0.8,1.0)*(0.65+flow*0.9+rim*1.8);
                gl_FragColor = vec4(mix(physical,energy,astral),mix(1.0,0.23+rim*0.48+flow*0.15,astral));
            }`,
        transparent: astral,
        depthWrite: !astral,
        side: DoubleSide,
    })
}

// Painted figures have no surface normal map. Alpha gradients provide a
// shallow relief normal and an edge rim while preserving the painted silhouette.
export const paintedCharacterLighting = /* glsl */ `
${characterLighting}
vec3 lightPaintedCharacter(sampler2D image, vec2 uv, vec2 texel, vec3 rgb, float alpha) {
    vec2 gradient = vec2(texture2D(image,uv+vec2(texel.x,0)).a-texture2D(image,uv-vec2(texel.x,0)).a,
        texture2D(image,uv+vec2(0,texel.y)).a-texture2D(image,uv-vec2(0,texel.y)).a);
    vec3 normal = normalize(vec3(-gradient*2.0, 1.0));
    return characterLight(rgb,normal,vec3(0,0,1)) + vec3(0.14,0.30,0.34)*length(gradient)*alpha;
}
`
