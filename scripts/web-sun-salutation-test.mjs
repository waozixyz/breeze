import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const inventory = readFileSync(new URL('../src/practices/sun_salutation/sun_salutation_inventory.zi', import.meta.url), 'utf8');
const frameSources = [...inventory.matchAll(/sun_salutation_frame_sources_\d+:[^=]+=[^[]*\[([^\]]+)\]/g)]
  .flatMap(match => match[1].split(',').map(value => value.trim()).filter(Boolean).map(Number));

const stateExpression = `(() => {
  const canvas = Module.canvas;
  // Capture the timer and wall clock together, before pixel readback can
  // block rendering. Both measurements refer to the same observed state.
  const practice = {
    sampledAt: performance.now(),
    step: Module._app_web_test_sun_salutation_step(),
    ticks: Module._app_web_test_sun_salutation_ticks(),
    character: Module._app_web_test_sun_salutation_character(),
    paused: Module._app_web_test_sun_salutation_paused(),
    screen: Module._app_web_test_screen()
  };
  const context = canvas.getContext('2d');
  const top = Math.floor(canvas.height * 0.25);
  const height = Math.max(1, canvas.height - top - 90);
  const pixels = context.getImageData(0, top, canvas.width, height).data;
  let painted = 0;
  let hash = 2166136261;
  for (let offset = 0; offset < pixels.length; offset += 4) {
    const red = pixels[offset];
    const green = pixels[offset + 1];
    const value = pixels[offset + 2];
    // Every approved character has warm painted skin, independent of outfit.
    if (red > 150 && green > 85 && red > green + 12 && red > value + 15) {
      painted++;
      hash = Math.imul(hash ^ offset, 16777619) >>> 0;
    }
  }
  return {
    ...practice,
    painted, hash, width: canvas.width, height: canvas.height
  };
})()`;

export async function verifySunSalutationCanvas({ evaluate, click, resize, capture, callHook, browser }) {
  const output = process.env.WEB_SMOKE_ARTIFACT_DIR;
  if (output) mkdirSync(output, { recursive: true });
  const evidence = [];

  async function save(name) {
    if (output) writeFileSync(join(output, `${browser}-${name}.png`), await capture());
  }

  async function target(prefix, index) {
    const point = await evaluate(`(() => {
      const canvas = Module.canvas;
      const rect = canvas.getBoundingClientRect();
      return {
        x: rect.left + Module._${prefix}_x(${index}) * rect.width / canvas.width,
        y: rect.top + Module._${prefix}_y(${index}) * rect.height / canvas.height
      };
    })()`);
    if (!(point.x >= 0 && point.y >= 0)) {
      await save(`missing-${prefix}`);
      const state = await evaluate(`(() => ({
        screen: Module._app_web_test_screen(),
        selected: Module._app_web_test_practice_selected(),
        tab: Module._app_web_test_practice_tab(),
        transition: Module._app_web_test_route_transition_active(),
        width: Module.canvas.width, height: Module.canvas.height
      }))()`);
      throw new Error(`missing ${prefix} target: ${JSON.stringify({ point, state })}`);
    }
    return point;
  }

  async function control(index) {
    const point = await target('app_web_test_sun_salutation_control', index);
    await click(point.x, point.y);
    await delay(100);
  }

  async function state() {
    const result = await evaluate(stateExpression);
    if (result.painted < 250) throw new Error(`Sun Salutation artwork is missing: ${JSON.stringify(result)}`);
    return result;
  }

  // Decode every shipped frame in the browser, including frames a slow device
  // can skip during playback. This also verifies the complete release bundle.
  const assets = await evaluate(`(async () => {
    const response = await fetch('/__test_cells__/practices.zib');
    if (!response.ok) throw new Error('Practices package is unavailable');
    const bundle = new Uint8Array(await response.arrayBuffer());
    const view = new DataView(bundle.buffer);
    if (view.getUint32(0, true) !== 0x0042495a || view.getUint32(4, true) !== 26)
      throw new Error('Unsupported Practices package');
    let at = 8;
    function number() {
      const value = view.getUint32(at, true);
      at += 4;
      return value;
    }
    function take(size) {
      if (size > bundle.length - at) throw new Error('Truncated Practices package');
      const value = bundle.subarray(at, at + size);
      at += size;
      return value;
    }
    function text() { return new TextDecoder().decode(take(number())); }
    text(); text();
    for (let count = number(); count > 0; count--) { text(); text(); }
    for (let count = number(); count > 0; count--) {
      for (let field = 0; field < 7; field++) text();
      take(8); text(); take(4);
    }
    for (let count = number(); count > 0; count--) { text(); text(); text(); }
    take(number());
    const files = new Map();
    for (let count = number(); count > 0; count--) {
      const name = text();
      if (files.has(name)) throw new Error('Duplicate package resource ' + name);
      files.set(name, take(number()));
    }
    if (at !== bundle.length) throw new Error('Trailing Practices package data');
    const root = 'assets/practices/sunsalutation/characters';
    const characters = [...new Set([...files.keys()].filter(name => name.startsWith(root + '/'))
      .map(name => name.slice(root.length + 1).split('/')[0]))].sort();
    if (characters.length !== 4) throw new Error('expected four Sun Salutation characters');
    const frameSources = ${JSON.stringify(frameSources)};
    if (frameSources.length !== 3964) throw new Error('incomplete animation timeline');
    const storedPaths = [...files.keys()].filter(name => name.startsWith(root + '/') && name.endsWith('.png'));
    if (storedPaths.length !== new Set(frameSources).size) throw new Error('stored animation inventory differs');
    let totalFrames = 0;
    let maximumFootJump = 0;
    for (const character of characters) {
      const directory = root + '/' + character;
      const paths = [];
      for (let pose = 1; pose <= 12; pose++) {
        for (let frame = 1; frame <= (pose === 1 ? 1 : 90); frame++) {
          paths.push(String(pose).padStart(2, '0') + '-' + String(frame).padStart(3, '0') + '.png');
        }
      }
      const steps = Array(12).fill(0);
      let previousFoot = null;
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d', { willReadFrequently: true });
      for (const [frameIndex, path] of paths.entries()) {
        const step = Number(path.slice(0, 2)) - 1;
        if (step < 0 || step >= 12) throw new Error('invalid pose path ' + path);
        const source = frameSources[characters.indexOf(character) * 991 + frameIndex];
        const sourceCharacter = Math.floor(source / 991);
        const sourceFrame = source % 991;
        const sourcePose = sourceFrame === 0 ? 1 : 2 + Math.floor((sourceFrame - 1) / 90);
        const sourceIndex = sourceFrame === 0 ? 1 : 1 + (sourceFrame - 1) % 90;
        const sourcePath = root + '/' + characters[sourceCharacter] + '/' +
          String(sourcePose).padStart(2, '0') + '-' + String(sourceIndex).padStart(3, '0') + '.png';
        const bytes = files.get(sourcePath);
        if (!bytes) throw new Error('missing stored image for ' + directory + '/' + path);
        const image = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
        if (!image.width || !image.height) throw new Error('empty image ' + path);
        canvas.width = image.width;
        canvas.height = image.height;
        context.drawImage(image, 0, 0);
        image.close();
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        let visible = 0;
        for (let offset = 3; offset < pixels.length; offset += 4) if (pixels[offset] > 0) visible++;
        if (visible < 100) throw new Error('blank image ' + path);
        // Pose 7 -> 8 used to flip the feet in one frame. Track the visible
        // feet through every shipped frame, including the solid-cel handoff.
        if (step === 7) {
          let count = 0, sumX = 0, sumY = 0;
          for (let y = Math.ceil(canvas.height * 0.65); y < canvas.height; y++) {
            for (let x = 0; x < canvas.width / 3; x++) {
              const offset = (y * canvas.width + x) * 4;
              const red = pixels[offset];
              if (pixels[offset + 3] > 80 && red > 140 &&
                  red > pixels[offset + 1] + 8 && red > pixels[offset + 2] + 8) {
                count++; sumX += x; sumY += y;
              }
            }
          }
          if (count < 100) throw new Error('missing feet in ' + path);
          const foot = { x: sumX / count, y: sumY / count };
          if (previousFoot) {
            const jump = Math.hypot(foot.x - previousFoot.x, foot.y - previousFoot.y);
            maximumFootJump = Math.max(maximumFootJump, jump);
            if (jump > 6) throw new Error('foot jumps ' + jump.toFixed(2) + ' pixels in ' + path);
          }
          previousFoot = foot;
        }
        steps[step]++;
      }
      if (steps[0] !== 1 || steps.slice(1).some(count => count !== 90))
        throw new Error('incomplete pose frames ' + JSON.stringify(steps));
      totalFrames += paths.length;
    }
    return { frames: totalFrames, characters, maximumFootJump };
  })()`, true);
  console.log(`web Sun Salutation: decoded ${assets.frames} frames (${browser})`);
  console.log(`web Sun Salutation: maximum foot movement ${assets.maximumFootJump.toFixed(2)}px (${browser})`);

  await evaluate(`(() => {
    const probe = window.__inbeAnimationProbe = {
      active: false, last: 0, gaps: [], decodes: [], readbacks: 0, uploads: 0
    };
    for (const prototype of [CanvasRenderingContext2D.prototype,
      ...(typeof OffscreenCanvasRenderingContext2D === 'undefined' ? [] :
        [OffscreenCanvasRenderingContext2D.prototype])]) {
      for (const method of ['drawImage', 'getImageData', 'putImageData']) {
        const original = prototype[method];
        prototype[method] = function(...args) {
          if (probe.active) {
            if (method === 'drawImage' && this.canvas === Module.canvas) {
              const now = performance.now();
              if (probe.last) probe.gaps.push(now - probe.last);
              probe.last = now;
            }
            if (this.canvas !== Module.canvas && method === 'getImageData') probe.readbacks++;
            if (method === 'putImageData') probe.uploads++;
          }
          return original.apply(this, args);
        };
      }
    }
    const decode = window.createImageBitmap;
    window.createImageBitmap = function(...args) {
      const active = probe.active;
      const start = performance.now();
      return decode.apply(this, args).then(bitmap => {
        if (active) probe.decodes.push(performance.now() - start);
        return bitmap;
      });
    };
  })()`);

  const viewports = [{ width: 450, height: 800 }, { width: 1280, height: 800 }];
  for (const viewport of viewports.filter(viewport =>
    process.env.WEB_SMOKE_SUN_VIEWPORT !== 'phone' || viewport.width === 450)) {
    const label = viewport.width === 450 ? 'phone' : 'desktop';
    await resize(viewport.width, viewport.height);
    await callHook('app_web_test_show_practice_home');
    await delay(500);
    // Select Sun Salutation with the real carousel gestures before opening
    // its manual and Customize pages with their real buttons.
    for (let swipe = 0; swipe < 4; swipe++) {
      if (await evaluate('Module._app_web_test_practice_selected()') === 2) break;
      const rect = await evaluate(`(() => {
        const rect = Module.canvas.getBoundingClientRect();
        return { x: rect.left, y: rect.top, width: rect.width, height: rect.height };
      })()`);
      const previous = await evaluate('Module._app_web_test_practice_selected()');
      let current = previous;
      for (let attempt = 0; attempt < 3 && current === previous; attempt++) {
        await click(rect.x + rect.width * 0.75, rect.y + rect.height * 0.3,
          rect.x + rect.width * 0.25, rect.y + rect.height * 0.3);
        await delay(500);
        current = await evaluate('Module._app_web_test_practice_selected()');
      }
      if (current === previous) throw new Error('Sun Salutation carousel gesture did not change practice');
    }
    const selected = await evaluate('Module._app_web_test_practice_selected()');
    if (selected !== 2) throw new Error(`carousel did not select Sun Salutation: ${selected}`);
    await save(`${label}-home`);
    for (const [action, expected, name] of [[0, 0, 'manual'], [1, 2, 'customize']]) {
      const point = await target('app_web_test_practice_action_click', action);
      await click(point.x, point.y);
      await delay(500);
      const tab = await evaluate('Module._app_web_test_practice_tab()');
      if (tab !== expected) {
        await save(`${label}-${name}-failed`);
        throw new Error(`Sun Salutation ${name} did not open: tab=${tab}, target=${JSON.stringify(point)}`);
      }
      await save(`${label}-${name}`);
      if (name === 'customize') {
        const picker = await evaluate(`(() => ({
          x: Module._app_web_test_control_x(613), y: Module._app_web_test_control_y(613),
          width: Module._app_web_test_control_width(613), height: Module._app_web_test_control_height(613)
        }))()`);
        if (picker.width <= 0 || picker.height <= 0) throw new Error('Character selector is missing');
        for (const character of [1, 2, 3, 0]) {
          await click(picker.x + picker.width / 2, picker.y + picker.height / 2);
          await delay(200);
          await click(picker.x + picker.width / 2, picker.y + picker.height * (character + 1.5));
          await delay(200);
          const selected = await evaluate('Module._app_web_test_sun_salutation_character()');
          if (selected !== character) throw new Error(`Character selector chose ${selected}, expected ${character}`);
          await save(`${label}-character-${character}`);
        }
      }
      await click(24, 24);
      await delay(500);
      if (await evaluate('Module._app_web_test_practice_tab()') !== 1)
        throw new Error(`Sun Salutation ${name} Back did not return home`);
    }

    const start = await target('app_web_test_practice_start_click', 0);
    await click(start.x, start.y);
    await delay(500);
    await control(1);
    const paused = await state();
    if (paused.character !== 0) throw new Error('Practice lost the selected character');
    await delay(350);
    const frozen = await state();
    if (paused.paused !== 1 || paused.ticks !== frozen.ticks || paused.hash !== frozen.hash)
      throw new Error(`Sun Salutation pause did not freeze timer and artwork: ${JSON.stringify({ paused, frozen })}`);
    await control(2);
    if ((await state()).step !== 1) throw new Error('Sun Salutation Next did not advance');
    await control(0);
    if ((await state()).step !== 0) throw new Error('Sun Salutation Previous did not return');
    await save(`${label}-mountain`);

    for (let step = 1; step < 12; step++) {
      await control(2);
      const before = await state();
      if (before.step !== step || before.paused !== 1 || before.ticks !== 0)
        throw new Error(`Sun Salutation Next lost state: ${JSON.stringify(before)}`);
      await control(1);
      // Start both clocks after the resume gesture has been handled. Mouse
      // dispatch and protocol latency happen while the practice is paused.
      const running = await state();
      if (running.paused !== 0 || running.step !== step)
        throw new Error(`Sun Salutation resume lost state: ${JSON.stringify(running)}`);
      // Measure uninterrupted playback after Resume and the pixel comparison.
      // Paused frames and test readbacks are not active rendering work.
      await evaluate(`(() => {
        window.__inbeAnimationProbe.last = 0;
        window.__inbeAnimationProbe.active = true;
      })()`);
      await delay(600);
      await evaluate('window.__inbeAnimationProbe.active = false');
      const moving = await state();
      if (moving.ticks <= before.ticks || moving.paused !== 0 || moving.hash === before.hash)
        throw new Error(`Sun Salutation pose ${step + 1} did not animate: ${JSON.stringify({ before, moving })}`);
      const elapsedSeconds = (moving.sampledAt - running.sampledAt) / 1000;
      const timerSeconds = (moving.ticks - running.ticks) / 60;
      if (timerSeconds < elapsedSeconds * 0.8 || timerSeconds > elapsedSeconds * 1.2)
        throw new Error(`Sun Salutation timer is not running in real time: ${JSON.stringify({
          step: step + 1, elapsedSeconds, timerSeconds
        })}`);
      // On the phone, watch each transition until it settles into its pose.
      // On desktop, cover controls and responsive placement on every step.
      if (label === 'phone') {
        await evaluate(`(() => {
          window.__inbeAnimationProbe.last = 0;
          window.__inbeAnimationProbe.active = true;
        })()`);
        const deadline = Date.now() + 10000;
        while (await evaluate('Module._app_web_test_sun_salutation_ticks()') < 215 && Date.now() < deadline) {
          await delay(100);
        }
      }
      await evaluate('window.__inbeAnimationProbe.active = false');
      await control(1);
      const held = await state();
      if (held.step !== step || held.paused !== 1)
        throw new Error(`Sun Salutation pose ${step + 1} changed unexpectedly: ${JSON.stringify(held)}`);
      if (label === 'phone' && held.ticks < 215) {
        await save(`${label}-pose-${step + 1}-stalled`);
        throw new Error(`pose ${step + 1} playback stalled: ${JSON.stringify(held)}`);
      }
      if (label === 'phone') await save(`${label}-pose-${String(step + 1).padStart(2, '0')}`);
      evidence.push({ viewport: label, step: step + 1, ...held });
    }
    console.log(`web Sun Salutation: all 12 poses, previews, controls and pause passed (${browser}, ${label})`);
  }
  const performance = await evaluate(`(() => {
    const probe = window.__inbeAnimationProbe;
    const sorted = probe.gaps.slice().sort((a, b) => a - b);
    const mean = probe.gaps.reduce((sum, value) => sum + value, 0) / probe.gaps.length;
    return {
      frames: probe.gaps.length, fps: 1000 / mean,
      medianMs: sorted[Math.floor(sorted.length * 0.5)],
      p95Ms: sorted[Math.floor(sorted.length * 0.95)],
      maxMs: sorted[sorted.length - 1],
      decodes: probe.decodes.length,
      decodeMeanMs: probe.decodes.reduce((sum, value) => sum + value, 0) / probe.decodes.length,
      readbacks: probe.readbacks, uploads: probe.uploads
    };
  })()`);
  console.log('web Sun Salutation frame timing: ' + JSON.stringify({ browser, ...performance }));
  if (performance.fps < 45 || performance.medianMs > 25)
    throw new Error(`Sun Salutation rendering missed its active frame rate: ${JSON.stringify(performance)}`);
  if (performance.readbacks !== 0 || performance.uploads !== 0)
    throw new Error(`Sun Salutation playback copied textures through CPU pixel buffers: ${JSON.stringify(performance)}`);
  if (output) writeFileSync(join(output, `${browser}-animation-performance.json`), JSON.stringify(performance, null, 2));
  if (output) writeFileSync(join(output, `${browser}-sun-salutation.json`), JSON.stringify({ assets, evidence }, null, 2));
}

export async function verifyAppearanceCanvas({ evaluate, click, resize, capture, callHook, browser }) {
  const output = process.env.WEB_SMOKE_ARTIFACT_DIR;
  if (output) mkdirSync(output, { recursive: true });

  async function save(name) {
    if (output) writeFileSync(join(output, `${browser}-${name}.png`), await capture());
  }

  for (const viewport of [{ width: 450, height: 800 }, { width: 1280, height: 800 }]) {
    await resize(viewport.width, viewport.height);
    await callHook('app_web_test_show_appearance');
    await delay(500);
    const bounds = await evaluate(`(() => ({
      x: Module._app_web_test_control_x(102), y: Module._app_web_test_control_y(102),
      width: Module._app_web_test_control_width(102), height: Module._app_web_test_control_height(102)
    }))()`);
    if (bounds.width <= 0 || bounds.height <= 0) throw new Error('Appearance Mode dropdown is missing');
    // The third option extends over the Layout card. Its label and background
    // must visibly replace the pixels beneath it when the dropdown opens.
    const patch = `Array.from(Module.canvas.getContext('2d').getImageData(
      ${Math.round(bounds.x + 12)}, ${Math.round(bounds.y + bounds.height * 3.25)},
      85, ${Math.round(bounds.height * 0.5)}).data)`;
    const before = await evaluate(patch);
    const light = await evaluate("Array.from(Module.canvas.getContext('2d').getImageData(5, 150, 1, 1).data).slice(0, 3)");
    await click(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
    await delay(300);
    const opened = await evaluate(patch);
    let changed = 0;
    for (let offset = 0; offset < before.length; offset += 4) {
      if (before[offset] !== opened[offset] || before[offset + 1] !== opened[offset + 1] ||
          before[offset + 2] !== opened[offset + 2]) changed++;
    }
    if (changed < 50) throw new Error(`Appearance dropdown is covered by Layout: ${changed} changed pixels`);
    await save(`appearance-dropdown-${viewport.width}`);
    await click(bounds.x + bounds.width / 2, bounds.y + bounds.height * 3.5);
    await delay(300);
    const dark = await evaluate("Array.from(Module.canvas.getContext('2d').getImageData(5, 150, 1, 1).data).slice(0, 3)");
    if (dark.reduce((sum, value) => sum + value, 0) >= light.reduce((sum, value) => sum + value, 0) * 0.6)
      throw new Error(`Appearance dropdown lower option did not enable dark mode: ${JSON.stringify({ light, dark })}`);
    await save(`appearance-dark-${viewport.width}`);
    console.log(`web Appearance: dropdown covers Layout and accepts its lower option (${browser}, ${viewport.width})`);
  }
}
