// Shared warm physical / cool awareness palette. No textures or ray marching.
import { Color, DoubleSide, FrontSide, ShaderMaterial } from 'three'

export const characterLighting = /* glsl */ `
vec3 characterLight(vec3 base, vec3 n, vec3 eye) {
    float diffuse = dot(n, normalize(vec3(-0.5, 0.8, 1.0))) * 0.5 + 0.5;
    float rim = pow(1.0 - abs(dot(n, eye)), 3.0);
    float wrap = pow(max(0.0, dot(-n, normalize(vec3(-0.5, 0.8, 1.0))) + 0.4), 2.0);
    return base * (0.55 + 0.55 * diffuse) + vec3(0.20, 0.09, 0.055) * wrap
        + vec3(0.22, 0.48, 0.55) * rim;
}
`

export function bodyMaterial({ astral = false, color = '#c49881', accent = '#7cecff' } = {}) {
    return new ShaderMaterial({
        uniforms: {
            color: { value: new Color(color) },
            accent: { value: new Color(accent) },
            opacity: { value: 1 },
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
            uniform vec3 color; uniform vec3 accent; uniform float time; uniform float astral; uniform float opacity;
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
                float rim = pow(1.0-abs(dot(n,eye)),2.4);
                if (astral < 0.5) {
                    vec3 halfLight=normalize(eye+normalize(vec3(-0.5,0.8,1.0)));
                    float spec=pow(max(0.0,dot(n,halfLight)),38.0)*0.16;
                    float grain=noise(vPosition*180.0)*0.015;
                    gl_FragColor=vec4(characterLight(color,n,eye)+spec*vec3(1.0,0.86,0.73)-grain,1.0);
                    return;
                }
                vec3 p=vPosition*4.0-vec3(0.0,time*0.17,0.0);
                float flow=noise(p)*0.72+noise(p*2.1+3.0)*0.28;
                float ribbons=pow(0.5+0.5*sin(vPosition.y*22.0+flow*6.0-time*1.2),12.0);
                float veins=pow(max(0.0,1.0-abs(flow-0.5)*9.0),4.0);
                vec3 energy=accent*(0.32+rim*2.8+ribbons*0.65)+vec3(1.0,0.64,0.28)*veins*0.28;
                gl_FragColor=vec4(energy,(0.10+rim*0.58+veins*0.12)*opacity);
            }`,
        transparent: astral,
        depthWrite: !astral,
        side: astral ? FrontSide : DoubleSide,
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
