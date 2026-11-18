import * as T from 'three'

// The figure model is pending: the MakeHuman-based body was removed on
// 2026-11-18 and a new, commercially licensed model is still to be chosen.
// Until then each figure is an invisible stand-in skeleton with the same
// joints the scenes drive (arms, elbows, hands and finger chains), so the
// rooms, energy effects, cords and cameras still play.
const ARM = { shoulder: [0.17, 1.38, 0], elbow: [0.04, -0.27, 0.02], wrist: [0, -0.25, 0.03] }
const FINGERS = [[0.025, -0.03, 0.03], [0.02, -0.08, 0.01], [0.007, -0.085, 0], [-0.007, -0.082, 0], [-0.02, -0.075, 0]]

export function createFigure(material, { astral = false } = {}) {
    const root = new T.Group()
    const bones = []
    const add = (parent, position) => {
        const bone = new T.Bone()
        bone.position.fromArray(position)
        parent.add(bone)
        bones.push(bone)
        return bone
    }
    const body = add(root, [0, 0, 0])
    // The existing technique solver expects negative-X then positive-X arms.
    const armsData = [-1, 1].map(sign => {
        const mirror = ([x, y, z]) => [x * sign, y, z]
        const shoulder = add(body, mirror(ARM.shoulder))
        const elbow = add(shoulder, mirror(ARM.elbow))
        const wrist = add(elbow, mirror(ARM.wrist))
        const fingers = FINGERS.map(start => {
            const first = add(wrist, mirror(start))
            const second = add(first, [0, -0.025, 0])
            const third = add(second, [0, -0.02, 0])
            return [first, second, third]
        })
        return { shoulder, elbow, wrist, fingers }
    })
    const grips = armsData.map(() => ({ open: { visible: true }, closed: { visible: false } }))
    root.rotation.x = -Math.PI / 2
    root.position.y = 0.64
    return {
        root,
        arms: armsData.map(info => info.shoulder),
        elbows: armsData.map(info => info.elbow),
        hands: armsData.map(info => info.wrist),
        grips,
        breathe(t) {
            material.uniforms.time.value = t
        },
        articulate() {
            armsData.forEach((info, side) => {
                info.fingers.forEach((chain, digit) => {
                    const curl = grips[side].closed.visible ? 1 : 0
                    chain.forEach((bone, joint) => {
                        bone.rotation.set(-curl * (digit ? 1.05 : 0.65), 0, digit ? 0 : curl * 0.25)
                        if (joint === 0 && digit === 0) bone.rotation.y = curl * (side ? -0.5 : 0.5)
                    })
                })
            })
        },
        touchPoint() {
            return armsData[1].fingers[0][1].getWorldPosition(new T.Vector3())
        },
        fingerCurl() {
            return armsData.map(info => info.fingers[2][0].rotation.x)
        },
        meshInfo: { vertices: 0, bones: bones.length, source: 'model pending', astral },
    }
}
