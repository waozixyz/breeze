import * as T from 'three'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'

// One full-screen pass. Small radial colour separation stays outside the focus;
// grain is deterministic at a session second, so pause and scrubbing are stable.
export function createFinish() {
    return new ShaderPass({
        uniforms: {
            tDiffuse: { value: null }, time: { value: 0 },
            tint: { value: new T.Color('#9ed5ff') }, strength: { value: 0.5 },
        },
        vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
        fragmentShader: /* glsl */ `
            uniform sampler2D tDiffuse;
            uniform float time, strength;
            uniform vec3 tint;
            varying vec2 vUv;
            void main() {
                vec2 q=vUv-0.5;
                float radius=dot(q,q);
                vec2 shift=q*radius*0.008*strength;
                vec3 c=texture2D(tDiffuse,vUv).rgb;
                c.r=texture2D(tDiffuse,vUv+shift).r;
                c.b=texture2D(tDiffuse,vUv-shift).b;
                c=mix(c,c*vec3(0.84,0.94,1.12),0.26);
                c+=tint*max(vec3(0.0),vec3(0.12)-c)*0.12;
                c*=1.0-smoothstep(0.06,0.48,radius)*0.43;
                float grain=fract(sin(dot(vUv*vec2(1453.0,997.0)+floor(time*24.0),vec2(12.9898,78.233)))*43758.5453)-0.5;
                c+=grain*0.014;
                gl_FragColor=vec4(c,1.0);
            }`,
    })
}
