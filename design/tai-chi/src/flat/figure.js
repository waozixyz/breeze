// Draws a flat figure (shapes.js) in the studio: its paint operations go to
// a Canvas 2D drawing shown on a full-screen quad, so the studio renders
// and captures it like the painted figures. Units are metres.

import {
    CanvasTexture, Color, Mesh, MeshBasicMaterial, OrthographicCamera, PlaneGeometry, Scene, SRGBColorSpace,
    Vector2,
} from 'three'
import { FlatView } from '../painted/layout.js'
import { FLAT_LOOKS, createFlatShapes } from './shapes.js'

export { FLAT_LOOKS }

export function createFlatFigure(look, rig) {
    const shapes = createFlatShapes(look, rig)
    const view = new FlatView()
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    const scene = new Scene()
    const camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1)
    const material = new MeshBasicMaterial({ depthTest: false, depthWrite: false, toneMapped: false })
    const quad = new Mesh(new PlaneGeometry(2, 2), material)
    quad.frustumCulled = false
    scene.add(quad)
    let texture = null
    let background = '#f1ece0'
    let frame = null

    function draw() {
        context.setTransform(1, 0, 0, 1, 0, 0)
        context.fillStyle = background
        context.fillRect(0, 0, canvas.width, canvas.height)
        if (!frame) {
            return
        }
        const pixels = canvas.height / (frame.top - frame.bottom)
        context.setTransform(pixels, 0, 0, -pixels, -frame.left * pixels, frame.top * pixels)
        context.lineCap = 'round'
        context.lineJoin = 'round'
        for (const op of frame.ops) {
            context.globalAlpha = op.alpha
            context.beginPath()
            context.moveTo(op.points[0].x, op.points[0].y)
            for (let index = 1; index < op.points.length; index += 1) {
                context.lineTo(op.points[index].x, op.points[index].y)
            }
            if (op.kind === 'fill') {
                context.closePath()
                context.fillStyle = op.color
                context.fill()
            } else {
                context.strokeStyle = op.color
                context.lineWidth = op.width
                context.stroke()
            }
        }
        context.globalAlpha = 1
    }

    return {
        scene,
        camera,
        character: look,
        update(solved, { yaw, tilt, center, viewHeight, viewCenter, aspect }) {
            view.set(yaw, tilt, center)
            const halfHeight = viewHeight / 2
            frame = {
                left: -halfHeight * aspect,
                top: viewCenter + halfHeight,
                bottom: viewCenter - halfHeight,
                ops: shapes.paint(solved, view),
            }
        },
        setBackground(color) {
            background = new Color(color).getStyle()
        },
        render(renderer) {
            const size = renderer.getDrawingBufferSize(new Vector2())
            if (canvas.width !== size.x || canvas.height !== size.y || !texture) {
                canvas.width = size.x
                canvas.height = size.y
                texture?.dispose()
                texture = new CanvasTexture(canvas)
                texture.colorSpace = SRGBColorSpace
                material.map = texture
                material.needsUpdate = true
            }
            draw()
            texture.needsUpdate = true
            renderer.render(scene, camera)
        },
        dispose() {
            texture?.dispose()
            material.dispose()
            quad.geometry.dispose()
        },
    }
}
