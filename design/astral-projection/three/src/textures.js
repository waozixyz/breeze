import * as T from 'three'

const loader = new T.TextureLoader()
const names = ['paper', 'pigment', 'linen', 'plaster', 'wood', 'luminous-wash']
const maps = await Promise.all(names.map(async name => {
    const texture = await loader.loadAsync(new URL(`../assets/${name}.webp`, import.meta.url).href)
    texture.wrapS = texture.wrapT = T.RepeatWrapping
    texture.colorSpace = T.SRGBColorSpace
    texture.anisotropy = 2
    return texture
}))
export const textures = Object.fromEntries(names.map((name, index) => [name, maps[index]]))

// Room pigments use the same paper, wash and soft shade bands as the figures.
export function paintedMaterial({ color, texture = 'plaster', roughness = 1, ...options }) {
    const material = new T.MeshStandardMaterial({ color, roughness, ...options })
    material.onBeforeCompile = shader => {
        shader.uniforms.paintPaper = { value: textures.paper }
        shader.uniforms.paintWash = { value: textures[texture] }
        shader.vertexShader = 'varying vec3 paintPosition; varying vec3 paintNormal;\n' + shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
            paintPosition = (modelMatrix * vec4(position,1.0)).xyz;
            paintNormal = normalize(mat3(modelMatrix)*normal);
        `)
        shader.fragmentShader = `uniform sampler2D paintPaper, paintWash; varying vec3 paintPosition, paintNormal;\n` + shader.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
            vec3 direction=abs(paintNormal);
            vec2 coord=direction.y>0.5 ? paintPosition.xz : direction.x>0.5 ? paintPosition.zy : paintPosition.xy;
            vec3 wash=texture2D(paintWash,coord*0.38).rgb;
            float grain=texture2D(paintPaper,coord*1.8).r;
            diffuseColor.rgb*=mix(vec3(0.65),wash*1.5,0.65)*(0.86+grain*0.3);
        `).replace('#include <opaque_fragment>', `
            float lightness=dot(outgoingLight,vec3(0.299,0.587,0.114));
            float bands=(floor(lightness*5.0)+smoothstep(0.3,0.7,fract(lightness*5.0)))/5.0;
            outgoingLight*=mix(1.0,bands/max(0.025,lightness),0.55);
            #include <opaque_fragment>
        `)
    }
    material.customProgramCacheKey = () => `watercolor-${texture}`
    return material
}
