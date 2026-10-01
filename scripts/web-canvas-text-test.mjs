import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function verifyCanvasTextResolution({ evaluate, resize, capture, callHook, browser }) {
  const output = process.env.WEB_SMOKE_ARTIFACT_DIR;
  if (output) mkdirSync(output, { recursive: true });
  const evidence = [];
  await evaluate(`(() => {
    const prototypes = [CanvasRenderingContext2D.prototype];
    if (typeof OffscreenCanvasRenderingContext2D !== 'undefined') {
      prototypes.push(OffscreenCanvasRenderingContext2D.prototype);
    }
    window.__inbeTextProbe = { originals: [], draws: [] };
    for (const prototype of prototypes) {
      const original = prototype.fillText;
      window.__inbeTextProbe.originals.push({ prototype, original });
      prototype.fillText = function(text, x, y) {
        const canvas = Module.canvas;
        // Glyph seed surfaces are smaller than the app's output surface.
        if (this.canvas !== canvas && this.canvas.width === canvas.width &&
            this.canvas.height === canvas.height) {
          const transform = this.getTransform();
          const draws = window.__inbeTextProbe.draws;
          draws.push({ text, font: this.font, scale: transform.a });
          if (draws.length > 2000) draws.shift();
        }
        return original.apply(this, arguments);
      };
    }
  })()`);
  try {
    for (const width of [450, 1280]) {
      for (const dpi of [1, 1.25, 2]) {
        await resize(width, 800, dpi);
        for (const [page, hook] of [
          ['appearance', 'app_web_test_show_appearance'],
          ['practice', 'app_web_test_show_practice_home']
        ]) {
          await callHook(hook);
          await delay(500);
          await evaluate('window.__inbeTextProbe.draws.length = 0');
          await delay(250);
          const state = await evaluate(`(() => {
            const canvas = Module.canvas;
            const rect = canvas.getBoundingClientRect();
            const draws = window.__inbeTextProbe.draws;
            return {
              width: canvas.width, height: canvas.height,
              cssWidth: rect.width, cssHeight: rect.height,
              dpi: window.devicePixelRatio,
              labels: [...new Set(draws.map(draw => draw.text))],
              fonts: [...new Set(draws.map(draw => draw.font))],
              scales: [...new Set(draws.map(draw => draw.scale))]
            };
          })()`);
          if (state.width !== Math.round(state.cssWidth * dpi) ||
              state.height !== Math.round(state.cssHeight * dpi) ||
              Math.abs(state.dpi - dpi) > 0.01) {
            throw new Error(`Canvas backing resolution is incorrect: ${JSON.stringify(state)}`);
          }
          if (state.labels.length < 4 || !state.fonts.length ||
              state.scales.some(scale => !Number.isFinite(scale) || scale <= 0)) {
            throw new Error(`Canvas text is not rasterized at output resolution: ${JSON.stringify(state)}`);
          }
          if (output) {
            writeFileSync(join(output, `${browser}-text-${page}-${width}-dpi-${dpi}.png`), await capture());
          }
          evidence.push({ page, viewport: width, ...state });
        }
      }
    }
  } finally {
    await evaluate(`(() => {
      for (const { prototype, original } of window.__inbeTextProbe.originals) {
        prototype.fillText = original;
      }
      delete window.__inbeTextProbe;
    })()`);
    await resize(1280, 800, 1);
  }
  if (output) {
    writeFileSync(join(output, `${browser}-text-resolution.json`), JSON.stringify(evidence, null, 2));
  }
  console.log(`web canvas text: final-resolution drawing at 100%, 125%, 200% on phone and desktop (${browser})`);
}
