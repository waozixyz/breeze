import * as T from 'three'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { textures } from './textures.js'

// A bounded four-quadrant brush filter selects the quietest local pigment
// wash. Sixteen colour taps plus four outline taps; no iterative blur chain.
export function createFinish() {
    return new ShaderPass({
        uniforms: {
            tDiffuse: { value: null },
            paper: { value: textures.paper }, wash: { value: textures.pigment },
            resolution: { value: new T.Vector2(1280, 720) },
            tint: { value: new T.Color('#9ed5ff') }, strength: { value: 0.5 },
        },
        vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
        fragmentShader: /* glsl */ `
            uniform sampler2D tDiffuse, paper, wash;
            uniform float strength;
            uniform vec2 resolution;
            uniform vec3 tint;
            varying vec2 vUv;
            vec3 brush(vec2 direction, vec2 texel, out float variance) {
                vec3 a=texture2D(tDiffuse,vUv).rgb;
                vec3 b=texture2D(tDiffuse,vUv+direction*vec2(2.0,0.0)*texel).rgb;
                vec3 c=texture2D(tDiffuse,vUv+direction*vec2(0.0,2.0)*texel).rgb;
                vec3 d=texture2D(tDiffuse,vUv+direction*2.0*texel).rgb;
                vec3 mean=(a+b+c+d)*0.25;
                vec3 square=(a*a+b*b+c*c+d*d)*0.25-mean*mean;
                variance=dot(abs(square),vec3(1.0));
                return mean;
            }
            void main() {
                vec2 texel=1.0/resolution;
                vec2 paperUV=gl_FragCoord.xy/256.0;
                float tooth=texture2D(paper,paperUV).r;
                vec3 pigment=texture2D(wash,vUv*vec2(1.7,1.0)).rgb;
                // Paper fibres disturb wet edges by less than a display pixel.
                vec2 bleed=(pigment.rg-0.35)*texel*1.1;
                vec3 original=texture2D(tDiffuse,vUv+bleed).rgb;
                float bestVariance=100.0;
                vec3 painted=original;
                for(int y=0;y<2;y++) {
                    for(int x=0;x<2;x++) {
                        vec2 direction=vec2(float(x)*2.0-1.0,float(y)*2.0-1.0);
                        float variance;
                        vec3 candidate=brush(direction,texel,variance);
                        if(variance<bestVariance){bestVariance=variance;painted=candidate;}
                    }
                }
                vec3 c=mix(original,painted,0.78);
                vec3 dx=texture2D(tDiffuse,vUv+vec2(texel.x,0.0)).rgb-texture2D(tDiffuse,vUv-vec2(texel.x,0.0)).rgb;
                vec3 dy=texture2D(tDiffuse,vUv+vec2(0.0,texel.y)).rgb-texture2D(tDiffuse,vUv-vec2(0.0,texel.y)).rgb;
                float edge=smoothstep(0.055,0.38,length(dx)+length(dy));
                float luminous=smoothstep(0.65,1.1,max(c.r,max(c.g,c.b)));
                // Broken pencil lines and wet pigment rims, never black neon.
                c=mix(c,c*vec3(0.30,0.36,0.48),edge*(0.40+tooth*0.3)*(1.0-luminous*0.8));
                c*=0.85+tooth*0.24;
                c=mix(c,c*vec3(0.80,0.94,1.10),0.26);
                c*=vec3(0.96)+tint*(0.04+strength*0.025);
                c+=pigment*0.045*(1.0-luminous);
                c+=vec3(0.88,0.83,0.73)*pow(tooth,3.0)*0.035;
                vec2 q=vUv-0.5;
                c*=1.0-smoothstep(0.14,0.50,dot(q,q))*0.25;
                gl_FragColor=vec4(c,1.0);
            }`,
    })
}
