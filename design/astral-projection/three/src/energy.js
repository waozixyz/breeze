import * as T from 'three'

// Reusable ribbons: animation costs buffer updates, never new geometry.
export function filament(color, { width = 0.016, segments = 64, opacity = 1 } = {}) {
    const positions = new Float32Array((segments + 1) * 6)
    const uvs = new Float32Array((segments + 1) * 4)
    const indices = []
    for (let i = 0; i <= segments; i += 1) {
        uvs.set([i / segments, 0, i / segments, 1], i * 4)
        if (i < segments) {
            const a = i * 2
            indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
        }
    }
    const geometry = new T.BufferGeometry()
    geometry.setAttribute('position', new T.BufferAttribute(positions, 3))
    geometry.setAttribute('uv', new T.BufferAttribute(uvs, 2))
    geometry.setIndex(indices)
    const material = new T.ShaderMaterial({
        uniforms: { time: { value: 0 }, color: { value: color }, opacity: { value: opacity } },
        vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
        fragmentShader: `uniform float time;uniform vec3 color;uniform float opacity;varying vec2 vUv;void main(){float crossSection=abs(vUv.y*2.0-1.0);
            float core=exp(-crossSection*crossSection*35.0);
            float halo=exp(-crossSection*crossSection*3.5);
            float packet=pow(0.5+0.5*sin(vUv.x*55.0-time*5.0),12.0);
            float helix=pow(0.5+0.5*cos(vUv.x*120.0-time*7.0+vUv.y*14.0),8.0);
            vec3 light=mix(color,vec3(0.88,0.95,1.0),core*0.7);
            gl_FragColor=vec4(light*(0.9+core*1.5+packet*2.4+helix*0.5),(halo*0.35+core*0.65)*opacity);}`,
        transparent: true, blending: T.AdditiveBlending, depthWrite: false, side: T.DoubleSide,
    })
    const mesh = new T.Mesh(geometry, material)
    mesh.frustumCulled = false
    const p = new T.Vector3()
    const q = new T.Vector3()
    const tangent = new T.Vector3()
    const normal = new T.Vector3()
    const axis = new T.Vector3(0, 1, 0)
    return {
        mesh,
        update(path, time, alpha = 1) {
            material.uniforms.time.value = time
            material.uniforms.opacity.value = opacity * alpha
            for (let i = 0; i <= segments; i += 1) {
                const u = i / segments
                path(u, p)
                path(Math.min(1, u + 0.005), q)
                tangent.copy(q).sub(p)
                normal.crossVectors(tangent, axis).normalize()
                if (normal.lengthSq() < 0.1) normal.set(1, 0, 0)
                const size = width * (0.65 + 0.35 * Math.sin(u * Math.PI))
                positions.set([p.x + normal.x * size, p.y + size * 0.4, p.z + normal.z * size,
                    p.x - normal.x * size, p.y - size * 0.4, p.z - normal.z * size], i * 6)
            }
            geometry.attributes.position.needsUpdate = true
        },
    }
}

export function aura(color) {
    const material = new T.ShaderMaterial({
        uniforms: { color: { value: color }, time: { value: 0 }, opacity: { value: 0.6 } },
        vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
        fragmentShader: `uniform vec3 color;uniform float time;uniform float opacity;varying vec2 vUv;void main(){float r=length((vUv-0.5)*2.0);float glow=exp(-r*r*5.0)*(1.0-smoothstep(0.5,1.0,r));float ring=pow(0.5+0.5*cos(r*45.0-time*3.5),20.0)*exp(-r*2.0);
            float angle=atan(vUv.y-0.5,vUv.x-0.5);
            float rays=pow(0.5+0.5*sin(angle*9.0-r*15.0+time),16.0);
            gl_FragColor=vec4(color*(0.5+ring*2.0)+vec3(0.5,0.7,1.0)*rays*glow,(glow*0.6+ring*0.45+rays*glow*0.25)*opacity);}`,
        transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
    })
    return new T.Mesh(new T.PlaneGeometry(1, 1), material)
}
