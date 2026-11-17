import * as T from 'three'

const colors = ['#75d9e4', '#8eafff', '#b397f0', '#78d9cf', '#dfbd83', '#c0a4fa']
export const palette = index => new T.Color(colors[index])

// A quiet bedroom, built for this astral study rather than the promo-film set.
export function createRoom(scene, index) {
    const accent = palette(index)
    scene.background = new T.Color('#080d1b')
    scene.fog = new T.FogExp2('#0b1224', 0.027)
    scene.add(new T.HemisphereLight('#91a8ce', '#231a25', 0.65))
    const moonlight = new T.DirectionalLight('#adc8ff', 3.1)
    moonlight.position.set(-3, 5, -3)
    scene.add(moonlight)
    const lampLight = new T.PointLight('#ffd2a0', 17, 9, 2)
    lampLight.position.set(1.35, 1.25, -1.30)
    scene.add(lampLight)
    const wood = new T.MeshStandardMaterial({ color: '#433743', roughness: 0.77 })
    const wall = new T.MeshStandardMaterial({ color: '#253047', roughness: 1 })
    const linen = new T.MeshStandardMaterial({ color: '#77869e', roughness: 1 })
    linen.onBeforeCompile = shader => {
        shader.vertexShader = 'varying vec3 fabricPosition;\n' + shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nfabricPosition = position;')
        shader.fragmentShader = 'varying vec3 fabricPosition;\n' + shader.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
            float weave=sin(fabricPosition.x*600.0)*sin(fabricPosition.z*600.0);
            float folds=sin(fabricPosition.z*14.0+sin(fabricPosition.x*9.0))*0.08;
            diffuseColor.rgb*=0.93+weave*0.025+folds;
        `)
    }
    function box(size, position, material) {
        const mesh = new T.Mesh(new T.BoxGeometry(...size), material)
        mesh.position.set(...position)
        scene.add(mesh)
        return mesh
    }
    box([15, 0.12, 15], [0, -0.15, 0], wood)
    box([10, 6, 0.16], [0, 2.85, -4.2], wall)
    box([0.16, 6, 9], [-4.2, 2.85, -0.1], wall)
    const rug = box([3.8, 0.025, 4.7], [0, -0.07, 0], new T.MeshStandardMaterial({ color: '#303448', roughness: 1 }))
    for (const x of [-1.75, 1.75]) box([0.018, 0.004, 4.3], [x, rug.position.y + 0.015, 0], linen)
    box([1.30, 0.18, 3.45], [0, 0.19, 0], wood)
    box([1.18, 0.14, 3.28], [0, 0.35, 0], linen)
    box([1.36, 0.56, 0.10], [0, 0.40, -1.78], wood)
    const pillow = new T.Mesh(new T.SphereGeometry(1, 24, 12), linen)
    pillow.scale.set(0.39, 0.065, 0.29)
    pillow.position.set(0, 0.44, -1.25)
    scene.add(pillow)
    for (const x of [-0.50, 0.50]) {
        box([0.028, 0.01, 3.08], [x, 0.426, 0], new T.MeshStandardMaterial({ color: '#6d7188', roughness: 1 }))
    }
    box([0.62, 0.12, 0.62], [1.38, 0.70, -1.30], wood)
    for (const x of [1.15, 1.61]) box([0.07, 0.64, 0.07], [x, 0.32, -1.30], wood)
    const lamp = new T.Mesh(new T.ConeGeometry(0.21, 0.29, 24, 1, true), new T.MeshStandardMaterial({ color: '#eac4a0', emissive: '#d5985d', emissiveIntensity: 0.35, side: T.DoubleSide }))
    lamp.position.set(1.38, 1.22, -1.30)
    scene.add(lamp)
    box([0.025, 0.38, 0.025], [1.38, 0.91, -1.30], wood)

    const sky = new T.Mesh(new T.PlaneGeometry(3.6, 2.8), new T.ShaderMaterial({
        vertexShader: 'varying vec2 p;void main(){p=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
        fragmentShader: `varying vec2 p;float hash(vec2 q){return fract(sin(dot(q,vec2(127.1,311.7)))*43758.5453);}void main(){vec3 c=mix(vec3(0.11,0.18,0.32),vec3(0.012,0.025,0.085),p.y);float mountain=0.22+sin(p.x*8.0)*0.06+sin(p.x*19.0)*0.025;c=mix(c,vec3(0.025,0.06,0.12),1.0-smoothstep(mountain,mountain+0.01,p.y));vec2 moon=(p-vec2(0.73,0.75))*vec2(1.286,1.0);float disc=1.0-smoothstep(0.066,0.069,length(moon));float cut=smoothstep(0.060,0.063,length(moon-vec2(0.025,0.012)));c+=vec3(0.70,0.78,0.85)*disc*cut;vec2 tile=floor(p*vec2(85.0,65.0));float star=step(0.992,hash(tile))*(1.0-smoothstep(0.0,0.10,length(fract(p*vec2(85.0,65.0))-0.5)));c+=star*0.8*step(0.3,p.y);gl_FragColor=vec4(c,1.0);}`,
    }))
    sky.position.set(-0.5, 2.65, -4.10)
    scene.add(sky)
    for (const x of [-2.35, 1.35]) box([0.09, 2.96, 0.10], [x, 2.65, -4.02], wood)
    for (const y of [1.20, 4.10]) box([3.79, 0.10, 0.10], [-0.5, y, -4.02], wood)
    box([0.045, 2.85, 0.07], [-0.5, 2.65, -4.0], wood)
    for (const side of [-1, 1]) {
        for (let fold = 0; fold < 5; fold += 1) {
            box([0.09, 3.25, 0.06], [-0.5 + side * (1.96 + fold * 0.08), 2.48, -3.90 + Math.sin(fold * 2) * 0.05], new T.MeshStandardMaterial({ color: '#404b68', roughness: 1 }))
        }
    }
    // A few drifting motes, one draw call and no CPU particle simulation.
    let seed = 23
    const random = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0
        return seed / 4294967296
    }
    const positions = new Float32Array(420 * 3)
    for (let n = 0; n < 420; n += 1) positions.set([(random() - 0.5) * 6, 0.4 + random() * 3.6, (random() - 0.5) * 6], n * 3)
    const geometry = new T.BufferGeometry()
    geometry.setAttribute('position', new T.BufferAttribute(positions, 3))
    const dust = new T.Points(geometry, new T.ShaderMaterial({
        uniforms: { time: { value: 0 }, color: { value: accent } },
        vertexShader: `uniform float time;varying float alpha;void main(){vec3 p=position;p.y+=sin(time*0.15+p.x)*0.14;p.x+=sin(time*0.12+p.z)*0.08;vec4 mv=modelViewMatrix*vec4(p,1.0);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(19.0/-mv.z,1.0,5.0);alpha=(0.25+0.25*sin(time*0.6+position.y*4.0))*smoothstep(-3.0,0.0,p.z);}`,
        fragmentShader: `uniform vec3 color;varying float alpha;void main(){float d=length(gl_PointCoord-0.5);gl_FragColor=vec4(color*1.5,pow(max(0.0,1.0-d*2.0),3.0)*alpha);}`,
        transparent: true, blending: T.AdditiveBlending, depthWrite: false,
    }))
    scene.add(dust)
    // Layered translucent shafts approximate light scattering without a volume
    // texture or ray march. The window end and floor end both feather to zero.
    const shafts = new T.Group()
    const shaftMaterial = new T.ShaderMaterial({
        uniforms: { time: { value: 0 } },
        vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
        fragmentShader: `
            uniform float time;varying vec2 vUv;
            void main(){
                float edge=pow(max(0.0,sin(vUv.x*3.14159265)),2.0);
                float lengthFade=sin(vUv.y*3.14159265);
                float haze=0.75+0.12*sin(vUv.y*21.0+vUv.x*7.0-time*0.14);
                float bars=0.6+0.4*pow(0.5+0.5*sin(vUv.x*21.0),3.0);
                gl_FragColor=vec4(vec3(0.32,0.54,1.0),edge*lengthFade*haze*bars*0.085);
            }`,
        transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    })
    for (let n = 0; n < 4; n += 1) {
        const shaft = new T.Mesh(new T.PlaneGeometry(1.0, 6.2), shaftMaterial)
        shaft.position.set(-1.5+n*0.64, 1.8, -1.5+n*0.11)
        shaft.rotation.set(-0.71, 0, -0.24)
        shafts.add(shaft)
    }
    scene.add(shafts)
    // Soft moonlight pools ground the bed and contrast the warm skin.
    const pool = new T.Mesh(new T.PlaneGeometry(4.3, 4.8), new T.ShaderMaterial({
        vertexShader: 'varying vec2 p;void main(){p=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
        fragmentShader: 'varying vec2 p;void main(){vec2 q=(p-0.5)*2.0;float a=exp(-dot(q,q)*3.0)*(1.0-smoothstep(0.5,1.0,length(q)));gl_FragColor=vec4(0.19,0.39,0.75,a*0.24);}',
        transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    }))
    pool.rotation.x = -Math.PI / 2
    pool.position.set(0.3, -0.045, 0.7)
    scene.add(pool)
    return {
        update(t) {
            dust.material.uniforms.time.value = t
            shaftMaterial.uniforms.time.value = t
        },
    }
}
