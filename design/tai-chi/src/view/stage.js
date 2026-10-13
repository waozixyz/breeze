// The practice floor, lights and camera.

import {
    AmbientLight, CanvasTexture, CircleGeometry, Color, DirectionalLight, Fog, Group,
    HemisphereLight, Mesh, MeshStandardMaterial, PCFSoftShadowMap, PerspectiveCamera,
    RepeatWrapping, Scene, SRGBColorSpace, Vector3, WebGLRenderer,
} from 'three'

export const THEMES = {
    light: {
        background: '#f1ece0',
        floor: '#e7dfcd',
        line: 'rgba(120, 104, 80, 0.16)',
        major: 'rgba(120, 104, 80, 0.3)',
        hemiSky: 0xfff8ec,
        hemiGround: 0xcfc2a8,
        sun: 0xffffff,
        sunIntensity: 2.1,
        hemiIntensity: 1.25,
    },
    dark: {
        background: '#141c22',
        floor: '#1c262d',
        line: 'rgba(200, 220, 230, 0.07)',
        major: 'rgba(200, 220, 230, 0.15)',
        hemiSky: 0xbcd4e6,
        hemiGround: 0x22303a,
        sun: 0xfff1dc,
        sunIntensity: 1.8,
        hemiIntensity: 0.9,
    },
}

function floorTexture(theme) {
    const size = 1024
    const canvas = typeof document !== 'undefined' ? document.createElement('canvas') : new OffscreenCanvas(size, size)
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    context.fillStyle = theme.floor
    context.fillRect(0, 0, size, size)
    // One tile is 2 m: fine lines every 0.25 m, stronger every metre.
    for (let index = 0; index <= 8; index += 1) {
        const position = (index / 8) * size
        context.strokeStyle = index % 4 === 0 ? theme.major : theme.line
        context.lineWidth = index % 4 === 0 ? 3 : 2
        context.beginPath()
        context.moveTo(position, 0)
        context.lineTo(position, size)
        context.moveTo(0, position)
        context.lineTo(size, position)
        context.stroke()
    }
    const texture = new CanvasTexture(canvas)
    texture.wrapS = RepeatWrapping
    texture.wrapT = RepeatWrapping
    texture.repeat.set(20, 20)
    texture.colorSpace = SRGBColorSpace
    texture.anisotropy = 8
    return texture
}

export function createStage(canvas, { preserveDrawingBuffer = false } = {}) {
    const renderer = new WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer })
    renderer.setPixelRatio(Math.min(2, globalThis.devicePixelRatio || 1))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = PCFSoftShadowMap
    renderer.outputColorSpace = SRGBColorSpace

    const scene = new Scene()
    const camera = new PerspectiveCamera(34, 16 / 9, 0.05, 200)
    const hemi = new HemisphereLight(0xffffff, 0x888888, 1)
    scene.add(hemi)
    const ambient = new AmbientLight(0xffffff, 0.15)
    scene.add(ambient)
    const sun = new DirectionalLight(0xffffff, 2)
    sun.castShadow = true
    sun.shadow.mapSize.set(2048, 2048)
    sun.shadow.camera.near = 0.5
    sun.shadow.camera.far = 20
    sun.shadow.camera.left = -2.2
    sun.shadow.camera.right = 2.2
    sun.shadow.camera.top = 2.2
    sun.shadow.camera.bottom = -2.2
    sun.shadow.bias = -0.0004
    sun.shadow.normalBias = 0.02
    sun.shadow.radius = 4
    scene.add(sun)
    scene.add(sun.target)

    const floorMaterial = new MeshStandardMaterial({ roughness: 0.95, metalness: 0 })
    const floor = new Mesh(new CircleGeometry(20, 96), floorMaterial)
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    scene.add(floor)
    const overlay = new Group()
    scene.add(overlay)

    const stage = {
        renderer,
        scene,
        camera,
        overlay,
        theme: 'light',
        setTheme(name) {
            const theme = THEMES[name] ?? THEMES.light
            stage.theme = name
            scene.background = new Color(theme.background)
            scene.fog = new Fog(theme.background, 9, 22)
            if (floorMaterial.map) {
                floorMaterial.map.dispose()
            }
            floorMaterial.map = floorTexture(theme)
            floorMaterial.needsUpdate = true
            hemi.color.set(theme.hemiSky)
            hemi.groundColor.set(theme.hemiGround)
            hemi.intensity = theme.hemiIntensity
            sun.color.set(theme.sun)
            sun.intensity = theme.sunIntensity
        },
        // Keeps the light and its shadow box over the figure.
        follow(center) {
            sun.target.position.copy(center).setY(0)
            sun.position.copy(center).add(new Vector3(2.5, 6, 3.5))
        },
        resize(width, height) {
            renderer.setSize(width, height, false)
            camera.aspect = width / height
            camera.updateProjectionMatrix()
        },
        render() {
            renderer.render(scene, camera)
        },
    }
    stage.setTheme('light')
    return stage
}

// Camera views. The front view is fixed to the starting direction (the
// audience); the others travel with the figure's facing.
export const VIEWS = {
    front: { label: 'Front', yaw: 0, fixed: true, distance: 5.2, height: 1.35, target: 0.88 },
    behind: { label: 'Behind', yaw: Math.PI, fixed: false, distance: 4.4, height: 1.75, target: 0.95 },
    side: { label: 'Side', yaw: -Math.PI / 2, fixed: false, distance: 4.6, height: 1.2, target: 0.85 },
    threeQuarter: { label: '¾', yaw: Math.PI / 4, fixed: false, distance: 4.8, height: 1.6, target: 0.85 },
    top: { label: 'Footwork', yaw: Math.PI, fixed: false, distance: 1.1, height: 5.0, target: 0.0 },
}

export function createCameraRig(camera) {
    const rig = {
        view: 'behind',
        center: new Vector3(0, 0, 0),
        yaw: Math.PI,
        initialized: false,
        // Smoothly follows the pelvis and, for travelling views, the facing.
        update(pelvis, facing, dt, snap = false) {
            const view = VIEWS[rig.view]
            const targetYaw = view.fixed ? view.yaw : facing + view.yaw
            const follow = new Vector3(pelvis.x, 0, pelvis.z)
            if (!rig.initialized || snap) {
                rig.center.copy(follow)
                rig.yaw = targetYaw
                rig.initialized = true
            } else {
                const k = 1 - Math.exp(-dt * 2.2)
                rig.center.lerp(follow, k)
                let delta = targetYaw - rig.yaw
                while (delta > Math.PI) delta -= 2 * Math.PI
                while (delta < -Math.PI) delta += 2 * Math.PI
                rig.yaw += delta * (1 - Math.exp(-dt * 1.6))
            }
            const direction = new Vector3(Math.sin(rig.yaw), 0, Math.cos(rig.yaw))
            camera.position.copy(rig.center).addScaledVector(direction, view.distance).setY(view.height)
            const target = rig.center.clone().setY(view.target)
            if (rig.view === 'top') {
                target.addScaledVector(direction, -0.15)
            }
            camera.lookAt(target)
            if (rig.view === 'top') {
                camera.fov = 40
            } else {
                camera.fov = 34
            }
            camera.updateProjectionMatrix()
        },
    }
    return rig
}
