const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// Observe real WebAudio nodes and the signal after the app's volume controls.
// The analyser passes that signal through unchanged.
function installMusicProbe() {
  const contexts = [];
  const sources = [];
  const connect = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (destination, ...args) {
    const record = contexts.find(item => item.context === this.context);
    if (record && destination === this.context.destination) {
      if (!record.analyser) {
        record.analyser = this.context.createAnalyser();
        record.analyser.fftSize = 2048;
        connect.call(record.analyser, destination);
      }
      connect.call(this, record.analyser, ...args);
      return destination;
    }
    return connect.call(this, destination, ...args);
  };
  for (const name of ['AudioContext', 'webkitAudioContext']) {
    const Original = globalThis[name];
    if (!Original) continue;
    globalThis[name] = new Proxy(Original, {
      construct(target, args) {
        const context = Reflect.construct(target, args);
        contexts.push({ context, analyser: null });
        const create = context.createBufferSource.bind(context);
        context.createBufferSource = () => {
          const source = create();
          const record = { id: sources.length, started: false, stopped: false, ended: false };
          sources.push(record);
          const start = source.start.bind(source);
          source.start = (...startArgs) => {
            start(...startArgs);
            record.started = true;
          };
          const stop = source.stop.bind(source);
          source.stop = (...stopArgs) => {
            stop(...stopArgs);
            record.stopped = true;
          };
          source.addEventListener('ended', () => { record.ended = true; });
          return source;
        };
        return context;
      }
    });
  }
  globalThis.__inbeMusicProbe = () => ({
    active: sources.filter(source => source.started && !source.stopped && !source.ended)
      .map(source => source.id),
    starts: sources.filter(source => source.started).length,
    stops: sources.filter(source => source.stopped).length,
    contexts: contexts.map(({ context, analyser }) => {
      const values = new Float32Array(2048);
      if (analyser) analyser.getFloatTimeDomainData(values);
      return {
        state: context.state,
        time: context.currentTime,
        rms: Math.sqrt(values.reduce((sum, value) => sum + value * value, 0) / values.length)
      };
    })
  });
}

export const musicAudioInstrumentation = `(${installMusicProbe.toString()})()`;

export async function verifyMusicAcrossTabs({ evaluate, click, scroll, resize, callHook, settle }) {
  await resize(1280, 1600);
  await callHook('app_web_test_save_onboarding_state');
  await evaluate(`(async () => {
    const sampleRate = 24000;
    const frames = sampleRate * 40;
    const bytes = new Uint8Array(44 + frames * 2);
    const view = new DataView(bytes.buffer);
    function text(offset, value) {
      for (let i = 0; i < value.length; i++) bytes[offset + i] = value.charCodeAt(i);
    }
    text(0, 'RIFF'); view.setUint32(4, bytes.length - 8, true);
    text(8, 'WAVE'); text(12, 'fmt '); view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    text(36, 'data'); view.setUint32(40, frames * 2, true);
    for (let i = 0; i < frames; i++)
      view.setInt16(44 + i * 2, Math.sin(i * 2 * Math.PI * 220 / sampleRate) * 6000, true);
    Module.FS.writeFile('/tmp/inbe-navigation.wav', bytes);
    // Seed the optional music pack with valid shipped Ogg data so Customize
    // exposes its preview control. The track being tested is the WAV above.
    Module.FS.mkdirTree('/unpackaged_assets/audio/Elijah_K');
    const cue = await fetch('/__test_assets__/bell.ogg');
    if (!cue.ok) throw new Error('Music test cue is unavailable');
    const ogg = new Uint8Array(await cue.arrayBuffer());
    for (const name of ['deep-meditation', 'path-of-meditation', 'truth-of-silence'])
      Module.FS.writeFile('/unpackaged_assets/audio/Elijah_K/' + name + '.ogg', ogg);
  })()`, true);
  await callHook('app_web_test_prepare_music');
  await delay(250);

  async function button(action) {
    await settle();
    const scrollableAction = action === 0 || action === 1 || (action >= 2 && action <= 5) || action === 8;
    let point;
    for (let attempt = 0; attempt < 4; attempt++) {
      // Entering Audio can suspend the first draw while cue files decode.
      // Wait for that draw and its actual control before choosing a position.
      const deadline = Date.now() + 10000;
      do {
        point = await evaluate(`(() => {
          const canvas = Module.canvas;
          const rect = canvas.getBoundingClientRect();
          const busy = !!(Module.Asyncify?.state || Module.Asyncify?.currData);
          const rawX = busy ? -1 : Module._app_web_test_music_button_x(${action});
          const rawY = busy ? -1 : Module._app_web_test_music_button_y(${action});
          return { rawX, rawY, busy,
            screen: busy ? -1 : Module._app_web_test_screen(),
            x: rect.left + rawX * rect.width / canvas.width,
            y: rect.top + rawY * rect.height / canvas.height,
            right: rect.right, bottom: rect.bottom };
        })()`);
        if (!point.busy) break;
        await delay(100);
      } while (Date.now() < deadline);
      if (!point.busy && point.rawX < 0 && action >= 2 && action <= 5 && attempt === 0) {
        await button(12);
        continue;
      }
      if (!point.busy && point.rawX < 0 && action >= 6 && action <= 10 && attempt === 0) {
        await button(13);
        continue;
      }
      if (!point.busy && point.rawX < 0 && (action === 0 || action === 1)) {
        await scroll(point.right * 0.7, point.bottom * 0.6, 400);
        await delay(600);
        continue;
      }
      if (point.rawX < 0 || point.rawY < 0 ||
          (!scrollableAction || point.y <= point.bottom * 0.75)) break;
      await scroll(point.x, point.bottom * 0.6, point.y - point.bottom * 0.65 + 100);
      await delay(600);
    }
    if (point.rawX < 0 || point.rawY < 0 || point.x > point.right || point.y > point.bottom)
      throw new Error(`music button ${action} is missing or clipped: ${JSON.stringify(point)}`);
    if (process.env.WEB_MUSIC_DEBUG) console.log('music click', action, point);
    await click(point.x, point.y);
    await delay(200);
  }

  const probe = () => evaluate('globalThis.__inbeMusicProbe()');
  function audible(state) {
    return state.active.length === 1 && state.contexts.some(context =>
      context.state === 'running' && context.rms > 0.005);
  }
  async function playing(label, expected) {
    let state;
    const deadline = Date.now() + 10000;
    do {
      state = await probe();
      if (expected || audible(state)) break;
      await delay(100);
    } while (Date.now() < deadline);
    if (!audible(state) || (expected && (state.active[0] !== expected.active[0] ||
        state.starts !== expected.starts || state.stops !== expected.stops ||
        state.contexts[0].time <= expected.contexts[0].time))) {
      throw new Error(`music interrupted during ${label}: ${JSON.stringify({ expected, state })}`);
    }
    return state;
  }

  await button(0);
  let previous = await playing('Audio preview');
  for (const [action, label] of [[2, 'Device'], [4, 'Appearance'], [5, 'About'],
    [3, 'Audio'], [6, 'Habits'], [8, 'Lists'], [7, 'Practices'], [10, 'Settings']]) {
    await button(action);
    previous = await playing(label, previous);
  }

  await button(3);
  await button(0);
  const paused = await probe();
  if (paused.active.length !== 0 || paused.contexts.some(context => context.rms > 0.0001))
    throw new Error(`explicit music pause did not silence playback: ${JSON.stringify(paused)}`);
  await button(0);
  previous = await playing('explicit resume');

  // Selecting another preview must replace the settings stream. Leaving
  // Customize must then preserve that new source, including its sample output.
  await button(7);
  await button(11);
  await button(1);
  const practice = await playing('Customize preview');
  if (practice.active[0] === previous.active[0] || practice.starts !== previous.starts + 1)
    throw new Error(`Customize did not replace the Audio preview: ${JSON.stringify(practice)}`);
  previous = practice;
  for (const [action, label] of [[12, 'leaving Customize'], [10, 'Settings'], [4, 'Appearance'],
    [6, 'Habits'], [8, 'Lists'], [7, 'Practices']]) {
    await button(action);
    previous = await playing(label, previous);
  }
  console.log('web music: real audio continues across internal tabs; pause and resume work');
  await resize(1280, 800);
}
