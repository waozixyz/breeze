// The film page uses Social's shared renderer. The original ten review
// frames and screenshots stay intact; film.json selects the owner's seven.
import {
    CanvasTexture, LinearFilter, Mesh, MeshBasicMaterial, NoToneMapping,
    OrthographicCamera, PlaneGeometry, Scene, SRGBColorSpace, WebGLRenderer,
} from 'three';
import { params, run, size } from '/.video/runtime.js';

const WIDTH = 1920;
const HEIGHT = 1080;
const colors = {
    mist: '#dde9e5', sky: '#a8c8d2', foreground: '#8fbfaf',
    blue: '#3f6f8f', pine: '#1e4a40', earth: '#6e4c36',
    ink: '#385a51', orange: '#f2a65e',
};

function sheet(width = WIDTH, height = HEIGHT) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    return canvas;
}

function write(context, value, x, y, pixels, color) {
    context.font = `${pixels}px Inbe`;
    context.fillStyle = color;
    context.fillText(value, x, y);
}

function image(path) {
    return new Promise((resolve, reject) => {
        const picture = new Image();
        picture.onload = () => resolve(picture);
        picture.onerror = () => reject(new Error(`Could not load ${path}`));
        picture.src = path;
    });
}

function texture(canvas) {
    const value = new CanvasTexture(canvas);
    value.colorSpace = SRGBColorSpace;
    value.minFilter = LinearFilter;
    value.magFilter = LinearFilter;
    value.generateMipmaps = false;
    return value;
}

function plane(canvas, x, y, width, height, z) {
    const material = new MeshBasicMaterial({
        map: texture(canvas), transparent: true, depthTest: false,
        depthWrite: false, toneMapped: false,
    });
    const mesh = new Mesh(new PlaneGeometry(width, height), material);
    mesh.position.set(x + width / 2 - WIDTH / 2, HEIGHT / 2 - y - height / 2, z);
    mesh.renderOrder = z;
    return mesh;
}

function smooth(value) {
    const bounded = Math.max(0, Math.min(1, value));
    return bounded * bounded * (3 - 2 * bounded);
}

function background() {
    const canvas = sheet();
    const context = canvas.getContext('2d');
    context.fillStyle = colors.mist;
    context.fillRect(0, 0, WIDTH, HEIGHT);
    context.fillStyle = colors.sky;
    context.fillRect(1070, 0, 850, HEIGHT);
    context.fillStyle = colors.foreground;
    context.beginPath();
    context.moveTo(1070, 620);
    context.bezierCurveTo(1360, 620, 1600, 480, 1920, 510);
    context.lineTo(1920, HEIGHT);
    context.lineTo(1070, HEIGHT);
    context.closePath();
    context.fill();
    return plane(canvas, 0, 0, WIDTH, HEIGHT, 0);
}

function branding(logo) {
    const canvas = sheet(1000, 180);
    const context = canvas.getContext('2d');
    context.drawImage(logo, 118, 94, 55, 55);
    write(context, 'Inner Breeze', 192, 134, 31, colors.pine);
    return plane(canvas, 0, 0, 1000, 180, 2);
}

function titleLayer(section) {
    const canvas = sheet(1000, 880);
    const context = canvas.getContext('2d');
    context.fillStyle = colors.orange;
    context.fillRect(120, 218, 48, 5);
    write(context, section.label, 120, 280, 27, colors.blue);
    section.title.forEach((line, row) => write(context, line, 114, 423 + row * 114, 88, colors.pine));
    section.copy.forEach((line, row) => write(context, line, 120, 664 + row * 57, 35, colors.ink));
    if (section.note) {
        write(context, section.note, 120, 820, 23, colors.earth);
    }
    return plane(canvas, 0, 0, 1000, 880, 3);
}

function screenLayer(picture) {
    const canvas = sheet(1020, 2004);
    const context = canvas.getContext('2d');
    context.fillStyle = colors.pine;
    context.beginPath();
    context.roundRect(0, 0, 1020, 2004, 44);
    context.fill();
    context.drawImage(picture, 18, 18, 984, 1968);
    return plane(canvas, 1219, 39, 510, 1002, 4);
}

function captionLayer(cue) {
    const canvas = sheet(850, 150);
    const context = canvas.getContext('2d');
    context.strokeStyle = '#a9c3b9';
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(0, 0.5);
    context.lineTo(830, 0.5);
    context.stroke();
    cue.lines.forEach((line, row) => write(context, line, 0, 65 + row * 46, 32, colors.pine));
    return plane(canvas, 120, 886, 850, 150, 5);
}

async function main() {
    const canvas = document.querySelector('canvas');
    const { width, height } = size();
    const [film, font, logo] = await Promise.all([
        fetch('./film.json').then(response => {
            if (!response.ok) throw new Error('Film timeline is unavailable');
            return response.json();
        }),
        new FontFace('Inbe', 'url(../../../assets/fonts/subset/NotoSans-App-Regular.ttf)').load(),
        image('../../../assets/app/icon.png'),
    ]);
    document.fonts.add(font);
    const pictures = await Promise.all(film.sections.map(section => image(`./screens/${section.screen}`)));
    const renderer = new WebGLRenderer({
        canvas, alpha: false, antialias: true,
        preserveDrawingBuffer: Boolean(params.get('render')),
    });
    renderer.setPixelRatio(1);
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = SRGBColorSpace;
    renderer.toneMapping = NoToneMapping;
    renderer.setClearColor(colors.mist, 1);
    const scene = new Scene();
    const camera = new OrthographicCamera(-WIDTH / 2, WIDTH / 2, HEIGHT / 2, -HEIGHT / 2, 0.1, 100);
    camera.position.z = 20;
    scene.add(background(), branding(logo));

    const sections = film.sections.map((section, index) => {
        const title = titleLayer(section);
        const screen = screenLayer(pictures[index]);
        title.userData.restX = title.position.x;
        scene.add(title, screen);
        return { ...section, titleMesh: title, screenMesh: screen };
    });
    const captions = film.captions.map(cue => {
        const mesh = captionLayer(cue);
        mesh.userData.restY = mesh.position.y;
        scene.add(mesh);
        return { ...cue, mesh };
    });

    function draw(time) {
        const t = Math.max(0, Math.min(film.length - 0.001, time));
        for (let index = 0; index < sections.length; index += 1) {
            const section = sections[index];
            // Screens share one fixed position. Gentle cross-dissolves keep
            // the app readable; there is no fake input or fabricated app UI.
            const fadeIn = index === 0 ? smooth(t / 0.65)
                : smooth((t - section.from + 0.4) / 0.8);
            const fadeOut = index === sections.length - 1 ? 1
                : 1 - smooth((t - section.to + 0.4) / 0.8);
            const opacity = fadeIn * fadeOut;
            section.screenMesh.visible = opacity > 0;
            section.titleMesh.visible = opacity > 0;
            section.screenMesh.material.opacity = opacity;
            section.titleMesh.material.opacity = opacity;
            const entrance = smooth((t - section.from + 0.15) / 1.1);
            section.titleMesh.position.x = section.titleMesh.userData.restX - (1 - entrance) * 18;
        }
        for (const cue of captions) {
            const opacity = smooth((t - cue.from) / 0.22) * (1 - smooth((t - cue.to + 0.22) / 0.22));
            cue.mesh.visible = opacity > 0;
            cue.mesh.material.opacity = opacity;
            cue.mesh.position.y = cue.mesh.userData.restY - (1 - smooth((t - cue.from) / 0.3)) * 4;
        }
        renderer.render(scene, camera);
    }

    await run({ length: film.length, fps: film.fps, canvas, draw, gl: renderer.getContext() });
}

main().catch(async error => {
    const job = params.get('render');
    if (job) {
        await fetch(`/render/${job}/error`, { method: 'POST', body: String(error?.stack ?? error) });
    }
    throw error;
});
