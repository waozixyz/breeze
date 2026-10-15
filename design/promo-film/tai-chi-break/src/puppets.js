// The painted Tai Chi teachers from design/tai-chi, as in ../three/src/puppets.js
// (FlatView now lives in painted/layout.js), solved from the real
// course choreography and drawn into a transparent picture that the
// courtyard shots place on the plaza.
import { HalfFloatType, LinearSRGBColorSpace, Vector3, WebGLRenderTarget } from 'three'
import { buildCourse, timelineFor } from '/design/tai-chi/src/course.js'
import { makeRig } from '/design/tai-chi/src/rig.js'
import { solvePose } from '/design/tai-chi/src/solve.js'
import { createPaintedFigure, loadCharacter } from '/design/tai-chi/src/painted/figure.js'
import { FlatView } from '/design/tai-chi/src/painted/layout.js'
import { premultipliedPlane, worldAt, worldPerPixel } from '/design/promo-film/three/src/world.js'

const CHARACTERS = {
    monk: '/design/tai-chi/characters/monk/character.json',
    tibetanWoman: '/design/tai-chi/characters/tibetan-woman/character.json',
}
// The picture shows VIEW_HEIGHT metres, twice as wide as tall.
const VIEW_HEIGHT = 2.3
const VIEW_CENTER = 0.95
const PICTURE_ASPECT = 2

let course = null

export async function createPuppet(figure, itemId, { from, yaw = 0, tilt = 0.04 }) {
    course ??= buildCourse()
    const item = course.items.get(itemId)
    const timeline = timelineFor(item).timeline
    const rig = makeRig(figure)
    const painted = createPaintedFigure(await loadCharacter(CHARACTERS[figure]), rig)
    const target = new WebGLRenderTarget(1600, 800, { type: HalfFloatType, colorSpace: LinearSRGBColorSpace, samples: 4 })
    const plane = premultipliedPlane(target.texture)
    // Centre the picture on the pelvis averaged over the shot, so the
    // figure really travels across the plaza when it steps.
    const centre = new Vector3()
    for (let i = 0; i <= 20; i += 1) {
        const pose = timeline.sample(timeline.start + from + (i / 20) * 9).pose
        const pelvis = solvePose(pose, rig).joints.pelvis
        centre.add(new Vector3(pelvis.x, 0, pelvis.z))
    }
    centre.multiplyScalar(1 / 21)

    const view = new FlatView()
    view.set(yaw, tilt, centre)
    return {
        plane,
        painted,
        // Draws the pose at shot time `t` into the picture.
        draw(renderer, t) {
            const sample = timeline.sample(timeline.start + Math.min(timeline.duration, from + Math.max(0, t)))
            painted.update(solvePose(sample.pose, rig), { yaw, tilt, center: centre, viewHeight: VIEW_HEIGHT, viewCenter: VIEW_CENTER, aspect: PICTURE_ASPECT })
            const previous = renderer.getRenderTarget()
            renderer.setRenderTarget(target)
            renderer.setClearColor(0x000000, 0)
            renderer.clear()
            painted.render(renderer)
            renderer.setRenderTarget(previous)
        },
        // Stands the picture with the figure's feet at plate pixel (x, y),
        // `height` pixels tall for the whole 1.72 m figure, at distance f.
        place(x, y, height, f) {
            const pxPerMetre = height / rig.height
            const pictureHeight = VIEW_HEIGHT * pxPerMetre
            const bottomPx = y + (VIEW_CENTER - VIEW_HEIGHT / 2) * -pxPerMetre
            const centrePx = bottomPx - pictureHeight / 2
            const unit = worldPerPixel(f)
            plane.position.copy(worldAt(x, centrePx, f))
            plane.scale.set(pictureHeight * PICTURE_ASPECT * unit, pictureHeight * unit, 1)
            this.layout = { x, y, height, f, pxPerMetre }
        },
        // Where a joint is on the plate at shot time `t`, in pixels (Lumi
        // follows a hand).
        jointPixel(name, t) {
            if (!this.layout) {
                return null
            }
            const sample = timeline.sample(timeline.start + Math.min(timeline.duration, from + Math.max(0, t)))
            const point = view.point(solvePose(sample.pose, rig).joints[name])
            const { x, y, pxPerMetre } = this.layout
            return { x: x + point.x * pxPerMetre, y: y - point.y * pxPerMetre }
        },
    }
}
