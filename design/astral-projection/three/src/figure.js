import * as T from 'three'

// Shared CC0 anatomical surface, reposed and weighted offline. No primitive
// stand-ins: head, face, torso, limbs, hands and feet are one continuous mesh.
const asset = name => new URL(`../assets/${name}`, import.meta.url)
const [human, bytes] = await Promise.all([
    fetch(asset('human.json')).then(response => response.json()),
    fetch(asset('human.bin')).then(response => response.arrayBuffer()),
])
const geometry = new T.BufferGeometry()
for (const [name, entry] of Object.entries(human.attributes)) {
    const ArrayType = entry.type === 'uint16' ? Uint16Array : Float32Array
    const data = new ArrayType(bytes, entry.offset, entry.length)
    if (name === 'index') geometry.setIndex(new T.BufferAttribute(data, 1))
    else geometry.setAttribute(name, new T.BufferAttribute(data, name.startsWith('skin') ? 4 : 3))
}
geometry.computeVertexNormals()
geometry.computeBoundingSphere()

export function createFigure(material, { astral = false } = {}) {
    const root = new T.Group()
    const bones = human.bones.map(info => {
        const bone = new T.Bone()
        bone.name = info.name
        bone.position.fromArray(info.position)
        return bone
    })
    human.bones.forEach((info, index) => {
        if (info.parent >= 0) bones[info.parent].add(bones[index])
    })
    const mesh = new T.SkinnedMesh(geometry, material)
    mesh.add(bones[0])
    mesh.bind(new T.Skeleton(bones))
    mesh.frustumCulled = false
    root.add(mesh)
    // The existing technique solver expects negative-X then positive-X arms.
    const armsData = [...human.arms].reverse()
    const arms = armsData.map(info => bones[info.shoulder])
    const elbows = armsData.map(info => bones[info.elbow])
    const hands = armsData.map(info => bones[info.wrist])
    const grips = armsData.map(() => ({ open: { visible: true }, closed: { visible: false } }))
    root.rotation.x = -Math.PI / 2
    root.position.y = 0.64
    return {
        root, arms, elbows, hands, grips,
        breathe(t) {
            material.uniforms.time.value = t
        },
        articulate() {
            armsData.forEach((info, side) => {
                info.fingers.forEach((chain, digit) => {
                    const curl = grips[side].closed.visible ? 1 : 0
                    chain.forEach((index, joint) => {
                        bones[index].rotation.set(-curl * (digit ? 1.05 : 0.65), 0, digit ? 0 : curl * 0.25)
                        if (joint === 0 && digit === 0) bones[index].rotation.y = curl * (side ? -0.5 : 0.5)
                    })
                })
            })
        },
        touchPoint() {
            return bones[armsData[1].fingers[0][1]].getWorldPosition(new T.Vector3())
        },
        fingerCurl() {
            return armsData.map(info => bones[info.fingers[2][0]].rotation.x)
        },
        meshInfo: { vertices: human.vertices, bones: bones.length, source: 'MakeHuman hm08 CC0', astral },
    }
}
