import * as THREE from './three-r187.module.js';

const assetMode = new URLSearchParams(location.search).has('asset');
const stations = [
  {
    name: 'Ambient Sleeping Pill',
    short: 'SLEEPING PILL',
    url: 'https://radio.stereoscenic.com/asp-s',
  },
  {
    name: 'a.m. ambient',
    short: 'A.M. AMBIENT',
    url: 'https://radio.stereoscenic.com/ama-s',
  },
  {
    name: 'Ambient Modern',
    short: 'AMBIENT MODERN',
    url: 'https://radio.stereoscenic.com/mod-s',
  },
];

const canvas = document.querySelector('#radio-canvas');
const liveRegion = document.querySelector('#radio-live');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
if (assetMode) {
  document.documentElement.style.background = 'transparent';
  document.body.style.background = 'transparent';
}

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: true,
  powerPreference: 'high-performance',
});
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x17120f, 0.028);

const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 80);
camera.position.set(0, 0.65, 12.8);
camera.lookAt(0, 0.15, 0);

scene.add(new THREE.HemisphereLight(0xffe5c0, 0x171219, 1.2));

const keyLight = new THREE.SpotLight(0xffd2a0, 72, 35, Math.PI / 5, 0.7, 1.2);
keyLight.position.set(-5.5, 8, 8);
keyLight.target.position.set(0, 0.3, 0);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(1536, 1536);
keyLight.shadow.bias = -0.0002;
scene.add(keyLight, keyLight.target);

const rimLight = new THREE.SpotLight(0x9bb7ff, 42, 28, Math.PI / 4, 0.8, 1.2);
rimLight.position.set(7, 5, 2);
rimLight.target.position.set(0, 0.6, 0);
scene.add(rimLight, rimLight.target);

const fillLight = new THREE.PointLight(0xff8a54, 19, 18, 1.5);
fillLight.position.set(-6, -1, 5);
scene.add(fillLight);

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(38, 28),
  new THREE.MeshStandardMaterial({ color: 0x171311, roughness: 0.78, metalness: 0.02 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.set(0, -3.02, 0);
floor.receiveShadow = true;
scene.add(floor);

const backdrop = new THREE.Mesh(
  new THREE.PlaneGeometry(34, 22),
  new THREE.MeshStandardMaterial({ color: 0x1d1714, roughness: 1 }),
);
backdrop.position.set(0, 2, -3.2);
backdrop.receiveShadow = true;
scene.add(backdrop);
if (assetMode) {
  floor.visible = false;
  backdrop.visible = false;
  scene.fog = null;
  renderer.setClearColor(0x000000, 0);
}

function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

function canvasTexture(draw, width = 1024, height = 1024) {
  const source = document.createElement('canvas');
  source.width = width;
  source.height = height;
  draw(source.getContext('2d'), width, height);
  const texture = new THREE.CanvasTexture(source);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return texture;
}

function makeWoodTexture() {
  const random = seededRandom(1948);
  const texture = canvasTexture((context, width, height) => {
    const gradient = context.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, '#5b2817');
    gradient.addColorStop(0.28, '#8d4828');
    gradient.addColorStop(0.57, '#6d321c');
    gradient.addColorStop(0.82, '#9b5632');
    gradient.addColorStop(1, '#5a2819');
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    for (let line = 0; line < 190; line += 1) {
      const y = random() * height;
      const wave = 3 + random() * 18;
      context.beginPath();
      context.moveTo(0, y);
      for (let x = 0; x <= width; x += 18) {
        context.lineTo(x, y + Math.sin(x * 0.017 + line) * wave + (random() - 0.5) * 3);
      }
      context.strokeStyle = random() > 0.55
        ? 'rgba(39, 12, 6, 0.19)'
        : 'rgba(255, 190, 118, 0.09)';
      context.lineWidth = 0.5 + random() * 2.2;
      context.stroke();
    }

    const glow = context.createRadialGradient(width * 0.46, height * 0.4, 5,
      width * 0.46, height * 0.4, width * 0.62);
    glow.addColorStop(0, 'rgba(255, 219, 166, 0.13)');
    glow.addColorStop(1, 'rgba(0, 0, 0, 0.24)');
    context.fillStyle = glow;
    context.fillRect(0, 0, width, height);
  });
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

function makeFabricTexture() {
  const texture = canvasTexture((context, width, height) => {
    context.fillStyle = '#5c4530';
    context.fillRect(0, 0, width, height);
    for (let position = -height; position < width + height; position += 18) {
      context.strokeStyle = 'rgba(238, 198, 139, 0.24)';
      context.lineWidth = 5;
      context.beginPath();
      context.moveTo(position, 0);
      context.lineTo(position - height, height);
      context.stroke();
      context.strokeStyle = 'rgba(35, 18, 12, 0.28)';
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(position + 8, 0);
      context.lineTo(position - height + 8, height);
      context.stroke();
    }
    for (let position = 0; position < width + height; position += 18) {
      context.strokeStyle = 'rgba(245, 218, 170, 0.13)';
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(position, 0);
      context.lineTo(position + height, height);
      context.stroke();
    }
  }, 512, 512);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3, 3);
  return texture;
}

function roundedShape(width, height, radius) {
  const left = -width / 2;
  const bottom = -height / 2;
  const right = width / 2;
  const top = height / 2;
  const shape = new THREE.Shape();
  shape.moveTo(left + radius, bottom);
  shape.lineTo(right - radius, bottom);
  shape.quadraticCurveTo(right, bottom, right, bottom + radius);
  shape.lineTo(right, top - radius);
  shape.quadraticCurveTo(right, top, right - radius, top);
  shape.lineTo(left + radius, top);
  shape.quadraticCurveTo(left, top, left, top - radius);
  shape.lineTo(left, bottom + radius);
  shape.quadraticCurveTo(left, bottom, left + radius, bottom);
  return shape;
}

function roundedBox(width, height, depth, radius, material, bevel = 0.07) {
  const geometry = new THREE.ExtrudeGeometry(roundedShape(width, height, radius), {
    depth,
    bevelEnabled: bevel > 0,
    bevelSegments: 5,
    bevelSize: bevel,
    bevelThickness: bevel,
    curveSegments: 10,
    steps: 1,
  });
  geometry.center();
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function physicalLabel(text, width, height, color = '#d6b374', fontSize = 70) {
  const texture = canvasTexture((context, textureWidth, textureHeight) => {
    context.clearRect(0, 0, textureWidth, textureHeight);
    context.fillStyle = color;
    context.font = '600 ' + fontSize + 'px Manrope, sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, textureWidth / 2, textureHeight / 2);
  }, 1024, 180);
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  });
  return new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
}

const woodTexture = makeWoodTexture();
const wood = new THREE.MeshPhysicalMaterial({
  color: 0xffffff,
  map: woodTexture,
  roughness: 0.38,
  metalness: 0.02,
  clearcoat: 0.42,
  clearcoatRoughness: 0.28,
});
const woodDark = new THREE.MeshPhysicalMaterial({
  color: 0x3f1b11,
  map: woodTexture,
  roughness: 0.52,
  clearcoat: 0.22,
});
const cream = new THREE.MeshStandardMaterial({
  color: 0xd9b98a,
  roughness: 0.54,
  metalness: 0.04,
});
const brass = new THREE.MeshPhysicalMaterial({
  color: 0xc7964b,
  roughness: 0.25,
  metalness: 0.86,
  clearcoat: 0.34,
});
const darkBrass = new THREE.MeshStandardMaterial({
  color: 0x6d4a27,
  roughness: 0.38,
  metalness: 0.72,
});
const blackMetal = new THREE.MeshStandardMaterial({
  color: 0x211916,
  roughness: 0.3,
  metalness: 0.67,
});
const fabric = new THREE.MeshStandardMaterial({
  color: 0xffffff,
  map: makeFabricTexture(),
  roughness: 0.92,
  metalness: 0,
});

const radio = new THREE.Group();
radio.position.y = -0.05;
scene.add(radio);

const cabinet = roundedBox(9.15, 5.62, 1.68, 0.58, wood, 0.12);
cabinet.position.y = 0.05;
radio.add(cabinet);

const front = roundedBox(8.47, 4.95, 0.2, 0.4, cream, 0.045);
front.position.set(0, 0.06, 0.93);
radio.add(front);

const speakerRecess = roundedBox(3.74, 3.93, 0.22, 0.34, woodDark, 0.035);
speakerRecess.position.set(-2.2, 0.35, 1.08);
radio.add(speakerRecess);

const speaker = roundedBox(3.44, 3.62, 0.14, 0.26, fabric, 0.025);
speaker.position.set(-2.2, 0.35, 1.22);
radio.add(speaker);

for (let index = 0; index < 13; index += 1) {
  const bar = new THREE.Mesh(new THREE.BoxGeometry(3.34, 0.026, 0.045), darkBrass);
  bar.position.set(-2.2, -1.19 + index * 0.257, 1.34);
  bar.castShadow = true;
  radio.add(bar);
}

const grilleCenter = new THREE.Mesh(new THREE.BoxGeometry(0.08, 3.45, 0.06), brass);
grilleCenter.position.set(-2.2, 0.35, 1.35);
radio.add(grilleCenter);

const dialGroup = new THREE.Group();
dialGroup.position.set(2.0, 1.0, 1.22);
radio.add(dialGroup);

const dialFrame = roundedBox(3.85, 1.72, 0.18, 0.22, darkBrass, 0.045);
dialGroup.add(dialFrame);

const dialTexture = canvasTexture((context, width, height) => {
  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, '#f0dcae');
  gradient.addColorStop(1, '#cfae77');
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  context.strokeStyle = '#6f4828';
  context.lineWidth = 4;
  for (let tick = 0; tick <= 30; tick += 1) {
    const x = 60 + tick * ((width - 120) / 30);
    const length = tick % 5 === 0 ? 38 : 20;
    context.beginPath();
    context.moveTo(x, 38);
    context.lineTo(x, 38 + length);
    context.stroke();
  }

  context.fillStyle = '#4a2c1e';
  context.font = '700 30px Manrope, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  stations.forEach((station, index) => {
    context.fillText(station.short, width * (index + 0.5) / 3, height * 0.6);
  });
  context.font = '600 22px Manrope, sans-serif';
  context.letterSpacing = '8px';
  context.fillText('AMBIENT RADIO', width / 2, height * 0.84);
}, 1200, 420);

const dialFace = new THREE.Mesh(
  new THREE.PlaneGeometry(3.58, 1.45),
  new THREE.MeshStandardMaterial({
    color: 0xffffff,
    map: dialTexture,
    roughness: 0.42,
    metalness: 0,
  }),
);
dialFace.position.z = 0.13;
dialGroup.add(dialFace);

const needle = new THREE.Mesh(
  new THREE.BoxGeometry(0.035, 1.18, 0.025),
  new THREE.MeshBasicMaterial({ color: 0xa33c26, toneMapped: false }),
);
needle.position.set(-1.24, 0.02, 0.18);
dialGroup.add(needle);

const dialGlass = roundedBox(
  3.62,
  1.48,
  0.045,
  0.16,
  new THREE.MeshPhysicalMaterial({
    color: 0xffead0,
    transparent: true,
    opacity: 0.13,
    roughness: 0.08,
    metalness: 0,
    transmission: 0.32,
    thickness: 0.1,
    depthWrite: false,
  }),
  0.018,
);
dialGlass.position.z = 0.23;
dialGroup.add(dialGlass);

const statusCanvas = document.createElement('canvas');
statusCanvas.width = 640;
statusCanvas.height = 100;
const statusTexture = new THREE.CanvasTexture(statusCanvas);
statusTexture.colorSpace = THREE.SRGBColorSpace;
const statusScreen = new THREE.Mesh(
  new THREE.PlaneGeometry(2.6, 0.28),
  new THREE.MeshBasicMaterial({
    map: statusTexture,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
  }),
);
statusScreen.position.set(0, -0.52, 0.27);
dialGroup.add(statusScreen);
if (assetMode) {
  needle.visible = false;
  statusScreen.visible = false;
}

function makeKnob(x, label) {
  const group = new THREE.Group();
  group.position.set(x, -1.28, 1.27);
  radio.add(group);

  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.59, 0.075, 18, 64), brass);
  ring.position.z = 0.03;
  ring.castShadow = true;
  group.add(ring);

  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.49, 0.53, 0.37, 64, 1), blackMetal);
  body.rotation.x = Math.PI / 2;
  body.position.z = 0.19;
  body.castShadow = true;
  group.add(body);

  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.43, 0.06, 64), darkBrass);
  cap.rotation.x = Math.PI / 2;
  cap.position.z = 0.405;
  cap.castShadow = true;
  group.add(cap);

  const marker = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.28, 0.035), cream);
  marker.position.set(0, 0.2, 0.445);
  group.add(marker);

  const text = physicalLabel(label, 1.4, 0.24, '#5d3d24', 76);
  text.position.set(x, -2.05, 1.2);
  radio.add(text);
  return group;
}

const volumeKnob = makeKnob(1.05, 'VOLUME');
const tuningKnob = makeKnob(3.12, 'TUNING');

const presetKeys = [];
for (let index = 0; index < stations.length; index += 1) {
  const key = roundedBox(0.56, 0.36, 0.22, 0.07, brass, 0.025);
  key.position.set(1.42 + index * 0.62, -0.1, 1.3);
  radio.add(key);
  const label = physicalLabel(String(index + 1), 0.28, 0.18, '#2d1c12', 92);
  label.position.set(1.42 + index * 0.62, -0.1, 1.44);
  radio.add(label);
  presetKeys.push(key);
}

const lampMaterial = new THREE.MeshStandardMaterial({
  color: 0x4a1e12,
  emissive: 0x5b1207,
  emissiveIntensity: 0.1,
  roughness: 0.25,
});
const powerButton = new THREE.Group();
powerButton.position.set(0.03, -1.28, 1.3);
const powerRing = new THREE.Mesh(new THREE.TorusGeometry(0.27, 0.055, 18, 48), brass);
powerRing.position.z = 0.03;
powerButton.add(powerRing);
const powerLamp = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.22, 0.18, 48), lampMaterial);
powerLamp.rotation.x = Math.PI / 2;
powerLamp.position.z = 0.12;
powerButton.add(powerLamp);
radio.add(powerButton);
const powerLabel = physicalLabel('POWER', 0.92, 0.22, '#5d3d24', 76);
powerLabel.position.set(0.03, -1.84, 1.2);
radio.add(powerLabel);

const handle = roundedBox(5.65, 0.43, 0.5, 0.2, woodDark, 0.06);
handle.position.set(0, 3.32, -0.02);
radio.add(handle);
for (const x of [-2.44, 2.44]) {
  const mount = roundedBox(0.55, 1.25, 0.54, 0.19, brass, 0.055);
  mount.position.set(x, 2.84, -0.02);
  radio.add(mount);
}

for (const x of [-3.2, 3.2]) {
  const foot = roundedBox(1.0, 0.38, 0.9, 0.17, blackMetal, 0.045);
  foot.position.set(x, -2.84, -0.12);
  radio.add(foot);
}

radio.traverse((object) => {
  if (object.isMesh) {
    object.castShadow = true;
    object.receiveShadow = true;
  }
});

function markControl(object, control) {
  object.traverse((part) => {
    part.userData.control = control;
  });
}

markControl(powerButton, 'power');
markControl(volumeKnob, 'volume');
markControl(tuningKnob, 'tuning');
presetKeys.forEach((key, index) => markControl(key, 'preset-' + index));

const controlRoots = [powerButton, volumeKnob, tuningKnob, ...presetKeys];
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const pointerScene = new THREE.Vector2();
const audio = new Audio();
audio.preload = 'none';

let powered = false;
let volume = 62;
let tuning = 0;
let selectedStation = 0;
let status = 'OFF';
let activeDrag = null;
let hoveredControl = null;
let dragDistance = 0;

function redrawStatus() {
  const context = statusCanvas.getContext('2d');
  context.clearRect(0, 0, statusCanvas.width, statusCanvas.height);
  context.fillStyle = 'rgba(63, 31, 18, 0.76)';
  context.fillRect(0, 0, statusCanvas.width, statusCanvas.height);
  context.fillStyle = powered ? '#ffd397' : '#b68d62';
  context.font = '700 34px Manrope, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  const message = status + '  ·  ' + stations[selectedStation].short + '  ·  ' + volume + '%';
  context.fillText(message, statusCanvas.width / 2, statusCanvas.height / 2);
  statusTexture.needsUpdate = true;
  liveRegion.textContent = status + '. ' + stations[selectedStation].name
    + '. Volume ' + volume + ' percent.';
}

function updateControls() {
  const volumeAngle = THREE.MathUtils.degToRad(-135 + volume * 2.7);
  volumeKnob.rotation.z = volumeAngle;
  tuningKnob.rotation.z = -2.2 + tuning * 2.2;
  needle.position.x = THREE.MathUtils.lerp(-1.23, 1.23, tuning / 2);
  presetKeys.forEach((key, index) => {
    key.position.z = index === selectedStation ? 1.21 : 1.3;
  });
  lampMaterial.emissiveIntensity = powered ? 3.5 : 0.1;
  lampMaterial.color.setHex(powered ? 0xe46b33 : 0x4a1e12);
  redrawStatus();
}

function setStatus(nextStatus) {
  status = nextStatus;
  redrawStatus();
}

function selectStation(index, play = powered) {
  selectedStation = THREE.MathUtils.clamp(index, 0, stations.length - 1);
  tuning = selectedStation;
  if (play) {
    audio.src = stations[selectedStation].url;
    audio.volume = volume / 100;
    setStatus('TUNING');
    audio.play().catch(() => setStatus('SIGNAL LOST'));
  }
  updateControls();
}

function setVolume(nextVolume) {
  volume = Math.round(THREE.MathUtils.clamp(nextVolume, 0, 100));
  audio.volume = volume / 100;
  updateControls();
}

function togglePower() {
  if (powered) {
    powered = false;
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    setStatus('OFF');
  } else {
    powered = true;
    audio.src = stations[selectedStation].url;
    audio.volume = volume / 100;
    setStatus('TUNING');
    audio.play().catch(() => {
      setStatus('SIGNAL LOST');
    });
  }
  updateControls();
}

audio.addEventListener('playing', () => {
  if (powered) setStatus('ON AIR');
});
audio.addEventListener('waiting', () => {
  if (powered) setStatus('TUNING');
});
audio.addEventListener('stalled', () => {
  if (powered) setStatus('RECONNECTING');
});
audio.addEventListener('error', () => {
  if (powered) setStatus('SIGNAL LOST');
});

function eventControl(event) {
  const bounds = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersections = raycaster.intersectObjects(controlRoots, true);
  return intersections.length ? intersections[0].object.userData.control : null;
}

function updateScenePointer(event) {
  const bounds = canvas.getBoundingClientRect();
  pointerScene.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointerScene.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
}

canvas.addEventListener('pointerdown', (event) => {
  const control = eventControl(event);
  if (!control) return;
  event.preventDefault();
  canvas.focus({ preventScroll: true });
  canvas.setPointerCapture(event.pointerId);
  activeDrag = {
    control,
    x: event.clientX,
    y: event.clientY,
    volume,
    tuning,
  };
  dragDistance = 0;
});

canvas.addEventListener('pointermove', (event) => {
  updateScenePointer(event);
  if (!activeDrag) {
    hoveredControl = eventControl(event);
    canvas.style.cursor = hoveredControl ? 'grab' : 'default';
    return;
  }

  const deltaX = event.clientX - activeDrag.x;
  const deltaY = event.clientY - activeDrag.y;
  dragDistance = Math.max(dragDistance, Math.hypot(deltaX, deltaY));
  canvas.style.cursor = 'grabbing';

  if (activeDrag.control === 'volume') {
    setVolume(activeDrag.volume + deltaX * 0.42 - deltaY * 0.55);
  } else if (activeDrag.control === 'tuning') {
    const nextTuning = THREE.MathUtils.clamp(activeDrag.tuning + deltaX / 105 - deltaY / 180, 0, 2);
    tuning = nextTuning;
    const nextStation = Math.round(tuning);
    if (nextStation !== selectedStation) {
      selectedStation = nextStation;
      if (powered) {
        audio.src = stations[selectedStation].url;
        audio.play().catch(() => setStatus('SIGNAL LOST'));
      }
    }
    updateControls();
  }
});

function endPointer(event) {
  if (!activeDrag) return;
  const control = activeDrag.control;
  const clicked = dragDistance < 7;
  activeDrag = null;
  canvas.style.cursor = hoveredControl ? 'grab' : 'default';
  if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);

  if (!clicked) {
    if (control === 'tuning') selectStation(Math.round(tuning));
    return;
  }
  if (control === 'power') {
    togglePower();
  } else if (control === 'tuning') {
    selectStation((selectedStation + 1) % stations.length);
  } else if (control.startsWith('preset-')) {
    selectStation(Number(control.slice(7)));
  }
}

canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('pointerleave', () => {
  if (!activeDrag) {
    hoveredControl = null;
    canvas.style.cursor = 'default';
  }
});

canvas.addEventListener('keydown', (event) => {
  if (event.code === 'Space' || event.code === 'Enter') {
    event.preventDefault();
    togglePower();
  } else if (event.code === 'ArrowUp') {
    event.preventDefault();
    setVolume(volume + 5);
  } else if (event.code === 'ArrowDown') {
    event.preventDefault();
    setVolume(volume - 5);
  } else if (event.code === 'ArrowRight') {
    event.preventDefault();
    selectStation(Math.min(selectedStation + 1, stations.length - 1));
  } else if (event.code === 'ArrowLeft') {
    event.preventDefault();
    selectStation(Math.max(selectedStation - 1, 0));
  } else if (/^Digit[123]$/.test(event.code)) {
    selectStation(Number(event.code.slice(5)) - 1);
  }
});

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (canvas.width !== Math.floor(width * renderer.getPixelRatio())
      || canvas.height !== Math.floor(height * renderer.getPixelRatio())) {
    renderer.setSize(width, height, false);
  }
  camera.aspect = width / height;
  if (assetMode) {
    radio.scale.setScalar(0.92);
    camera.position.z = 16;
  } else if (camera.aspect < 0.75) {
    radio.scale.setScalar(0.7);
    camera.position.z = 17.5;
  } else if (camera.aspect < 1.1) {
    radio.scale.setScalar(0.86);
    camera.position.z = 14.3;
  } else {
    radio.scale.setScalar(1);
    camera.position.z = 12.8;
  }
  camera.updateProjectionMatrix();
}

function projectedBounds(object) {
  object.updateWorldMatrix(true, true);
  camera.updateMatrixWorld();
  const box = new THREE.Box3().setFromObject(object);
  const bounds = canvas.getBoundingClientRect();
  const xs = [];
  const ys = [];
  for (const x of [box.min.x, box.max.x]) {
    for (const y of [box.min.y, box.max.y]) {
      for (const z of [box.min.z, box.max.z]) {
        const point = new THREE.Vector3(x, y, z).project(camera);
        xs.push(bounds.left + (point.x + 1) * bounds.width / 2);
        ys.push(bounds.top + (1 - point.y) * bounds.height / 2);
      }
    }
  }
  return {
    x: Math.min(...xs),
    y: Math.min(...ys),
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys),
  };
}

window.__breezeRadio = {
  getState() {
    return {
      ready: true,
      powered,
      volume,
      tuning,
      selectedStation,
      status,
      triangles: renderer.info.render.triangles,
      contextLost: renderer.getContext().isContextLost(),
      width: canvas.width,
      height: canvas.height,
    };
  },
  controlPoint(control) {
    const root = controlRoots.find((candidate) => candidate.userData.control === control);
    if (!root) return null;
    root.updateWorldMatrix(true, true);
    camera.updateMatrixWorld();
    const world = new THREE.Vector3();
    root.getWorldPosition(world);
    world.project(camera);
    const bounds = canvas.getBoundingClientRect();
    return {
      x: bounds.left + (world.x + 1) * bounds.width / 2,
      y: bounds.top + (1 - world.y) * bounds.height / 2,
    };
  },
  layout() {
    return {
      radio: projectedBounds(cabinet),
      dial: projectedBounds(dialFace),
      status: projectedBounds(statusScreen),
      power: this.controlPoint('power'),
      volume: this.controlPoint('volume'),
      tuning: this.controlPoint('tuning'),
      presets: stations.map((station, index) => this.controlPoint('preset-' + index)),
    };
  },
};

const clock = new THREE.Clock();
function animate() {
  resize();
  const elapsed = clock.getElapsedTime();
  const motion = reducedMotion ? 0 : 1;
  const targetX = assetMode ? 0 : pointerScene.x * 0.28 * motion;
  const targetY = assetMode ? 0.65 : 0.65 + pointerScene.y * 0.12 * motion;
  camera.position.x += (targetX - camera.position.x) * 0.035;
  camera.position.y += (targetY - camera.position.y) * 0.035;
  camera.lookAt(0, 0.1, 0);
  radio.rotation.y += ((assetMode ? 0 : pointerScene.x * 0.035 * motion) - radio.rotation.y) * 0.03;
  radio.rotation.x += ((assetMode ? 0 : -pointerScene.y * 0.012 * motion) - radio.rotation.x) * 0.03;
  if (powered) {
    lampMaterial.emissiveIntensity = 3.25 + Math.sin(elapsed * 5.5) * 0.2;
  }
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

updateControls();
animate();
