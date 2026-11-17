import * as T from 'three'

// Bounded, texture-free value noise shared by the skin and spirit surfaces.
export const flowNoise = /* glsl */ `
float hash(vec3 p) {
    p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float noise(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f*f*(3.0-2.0*f);
    return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),
        mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
        mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),
        mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float flow(vec3 p) {
    return noise(p)*0.65 + noise(p*2.03+4.1)*0.25 + noise(p*4.07)*0.1;
}
`

export function studyBodyMaterial({ astral = false, accent } = {}) {
    return new T.ShaderMaterial({
        uniforms: {
            accent: { value: accent }, time: { value: 0 }, opacity: { value: 1 },
        },
        defines: astral ? { SPIRIT: 1 } : {},
        vertexShader: /* glsl */ `
            varying vec3 normalView, eyeView, local, world;
            void main() {
                vec4 p = modelViewMatrix * vec4(position, 1.0);
                normalView = normalMatrix * normal;
                eyeView = -p.xyz;
                local = position;
                world = (modelMatrix * vec4(position, 1.0)).xyz;
                gl_Position = projectionMatrix * p;
            }`,
        fragmentShader: /* glsl */ `
            uniform vec3 accent;
            uniform float time, opacity;
            varying vec3 normalView, eyeView, local, world;
            ${flowNoise}
            void main() {
                vec3 n = normalize(normalView), eye = normalize(eyeView);
                float facing = abs(dot(n, eye));
                float rim = pow(1.0-facing, 2.3);
                #ifdef SPIRIT
                    vec3 p = world*3.8 + vec3(time*0.04, -time*0.23, 0.0);
                    float mist = flow(p + flow(p*0.6)*2.0);
                    float contours = pow(0.5+0.5*sin(mist*32.0+world.y*9.0-time*1.6), 14.0);
                    float pulse = exp(-pow((fract(world.y*0.34-time*0.16)-0.5)*9.0, 2.0));
                    vec3 core = mix(vec3(0.12,0.22,0.6), accent, mist);
                    vec3 c = core*(0.45+mist*0.8) + accent*rim*2.7;
                    c += mix(accent,vec3(1.0,0.87,0.66),0.45)*contours*0.85;
                    c += vec3(0.42,0.66,1.0)*pulse*0.5;
                    gl_FragColor = vec4(c, opacity*(0.13+rim*0.6+mist*0.15+contours*0.16));
                #else
                    vec3 key = normalize(vec3(0.65,0.6,0.9));
                    vec3 moon = normalize(vec3(-0.9,0.4,-0.2));
                    float wrapped = max(0.0,(dot(n,key)+0.38)/1.38);
                    float scatter = pow(max(0.0,dot(-n,key)+0.45),2.0);
                    float spec = pow(max(0.0,dot(n,normalize(key+eye))),42.0);
                    float pores = noise(world*210.0);
                    float skinVariation = flow(world*7.0);
                    vec3 skin = mix(vec3(0.44,0.23,0.16),vec3(0.60,0.34,0.24),skinVariation);
                    vec3 c = skin*(0.25+wrapped*1.25);
                    c += vec3(0.42,0.08,0.035)*scatter;
                    c += vec3(0.22,0.43,0.72)*pow(max(0.0,dot(n,moon)),1.5)*0.65;
                    c += vec3(0.75,0.85,1.0)*rim*0.20;
                    c += vec3(1.0,0.78,0.58)*spec*0.28;
                    c *= 0.97+pores*0.03;
                    gl_FragColor = vec4(c,1.0);
                #endif
                #include <tonemapping_fragment>
                #include <colorspace_fragment>
            }`,
        transparent: astral,
        depthWrite: !astral,
        side: T.FrontSide,
    })
}

export function energyShell(accent) {
    const material = new T.ShaderMaterial({
        uniforms: { time: { value: 0 }, opacity: { value: 0 }, color: { value: accent }, mode: { value: 0 } },
        vertexShader: /* glsl */ `
            varying vec3 p, n, e;
            void main(){p=position;n=normalMatrix*normal;vec4 v=modelViewMatrix*vec4(position,1.0);e=-v.xyz;gl_Position=projectionMatrix*v;}`,
        fragmentShader: /* glsl */ `
            uniform float time, opacity, mode;
            uniform vec3 color;
            varying vec3 p,n,e;
            void main() {
                float rim=pow(1.0-abs(dot(normalize(n),normalize(e))),2.8);
                float latitude=mode>1.5 ? p.y*19.0+time*3.5 : p.z*19.0-time*3.5;
                float longitude=atan(p.y,p.x)*6.0+p.z*11.0-time*2.5;
                float bands=pow(0.5+0.5*sin(mix(latitude,longitude,mode>0.5 && mode<1.5 ? 1.0 : 0.0)),24.0);
                float sparks=pow(0.5+0.5*sin(longitude*3.0+latitude),36.0);
                float a=opacity*(rim*0.18+bands*0.34+sparks*rim*0.7);
                gl_FragColor=vec4(color*(1.0+bands*1.3)+vec3(0.5,0.7,1.0)*sparks,a);
            }`,
        transparent: true, blending: T.AdditiveBlending, depthWrite: false,
    })
    return new T.Mesh(new T.SphereGeometry(1, 48, 32), material)
}
