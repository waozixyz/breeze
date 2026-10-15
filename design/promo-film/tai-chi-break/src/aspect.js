// The film's frame: 16:9, or 9:16 for TikTok, Shorts and Reels
// (?aspect=portrait). A portrait camera keeps the vertical field of view
// and pans across the painted plates by turning around its own centre,
// which re-projects the painting without any parallax tearing.
import { HEIGHT, WIDTH } from '/design/promo-film/three/src/world.js'

export const PORTRAIT = new URLSearchParams(location.search).get('aspect') === 'portrait'
export const FRAME_WIDTH = PORTRAIT ? 1080 : WIDTH
export const FRAME_HEIGHT = PORTRAIT ? 1920 : HEIGHT

// The plates fill a 40-degree frustum from the starting camera.
const HALF_H = Math.tan((40 * Math.PI) / 360)
const HALF_W = HALF_H * (WIDTH / HEIGHT)
// Turning further than this would show a plate's edge in a portrait frame.
const MAX_YAW = (19 * Math.PI) / 180
const MAX_PITCH = (1.3 * Math.PI) / 180

export function frame(camera) {
    if (PORTRAIT) {
        camera.aspect = FRAME_WIDTH / FRAME_HEIGHT
        camera.rotation.order = 'YXZ'
        camera.updateProjectionMatrix()
    }
    return camera
}

// Turns a portrait camera to centre plate pixel (px, py); 16:9 keeps its view.
export function aim(camera, px, py = HEIGHT / 2) {
    if (!PORTRAIT) {
        return
    }
    const yaw = -Math.atan(((px / WIDTH) * 2 - 1) * HALF_W)
    const pitch = Math.atan((1 - (py / HEIGHT) * 2) * HALF_H)
    camera.rotation.set(Math.max(-MAX_PITCH, Math.min(MAX_PITCH, pitch)), Math.max(-MAX_YAW, Math.min(MAX_YAW, yaw)), 0)
}

// One value for each frame: `pick(wide, tall)`.
export function pick(wide, tall) {
    return PORTRAIT ? tall : wide
}
