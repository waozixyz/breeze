# A Day with Lumi — Three.js edition

The 65-second trailer animated in Three.js instead of camera moves over still
keyframes. It keeps `../film.json`'s nine clips, voice times and phone inserts;
`../compose.py --base` adds the app screens, the end card and the soundtrack.

## Pictures

- `plates.json` / `plates.py`: Codex image edits of the approved keyframes
  (`build/promo-video/keyframes/`) into clean plates — Lumi removed, and for
  the "-empty" plates Mia too. Raw edits land in `build/promo-video/threejs/plates/`.
- `plates/NAME.jpg`: each plate's 16:9 band at 1920x1080.
- `depth.py`: Depth Anything V2 (small, ONNX) depth maps, `plates/NAME-depth.png`.
  Run it with a venv holding onnxruntime, numpy and pillow; the model is
  `onnx-community/depth-anything-v2-small` (`onnx/model.onnx`).
- `cutouts.py`: Mia's cutouts, `plates/NAME-mia.webp`, from the difference between
  a plate with her and its "-empty" twin; `plates/meta.json` holds their boxes
  and depths. `voice.json` is Lumi's voice level per frame, which drives her glow.

## Film

- `src/world.js`: plates pushed into depth on a 320x180 mesh (parallax when the
  camera moves), water ripples, boiling clouds and mist, wind in reeds and
  grass, rain on glass, twinkling stars, breathing light shafts, prayer flags,
  fog bands, motes, glows, and cutouts that breathe and sway around the hips.
- `src/lumi.js`: Lumi from `design/lumi-promo/lumi-flight-cycle.png` (eight
  wing frames at 16 fps) with tummy, antenna and halo glows, and a golden trail.
- `src/puppets.js`: the painted Tai Chi monk and Tibetan woman from
  `design/tai-chi`, solved from the course's Wave Hands Like Clouds and Brush
  Knee and Push demos and drawn into a transparent picture on the plaza.
- `src/shots.js`: the nine shots; `src/main.js`: dissolves, bloom, grade.

## Run

```sh
npm install                                  # Three.js 0.169.0, as design/tai-chi
node tools/serve.mjs                         # preview at /design/promo-film/three/ (?t=SECONDS)
node tools/render.mjs --stills 3,27,62 --out build/promo-video/threejs/stills/x.mp4
node tools/render.mjs --out build/promo-video/threejs/film.mp4
python3 ../compose.py --base build/promo-video/threejs/film.mp4 \
    --out build/promo-video/inner-breeze-a-day-with-lumi-threejs.mp4   # from the inbe root
```

Renders use headless Chromium on the GPU (`--use-angle=gl-egl`; `--gl
swiftshader` for software) with the display and session variables removed.
Every frame is drawn from timeline time and streamed as raw pixels to ffmpeg.
