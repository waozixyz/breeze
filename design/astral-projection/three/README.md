# Astral exercise motion studies

Standalone review page; no app integration. Reuses the promo-film installation of
**Three.js 0.169.0**, with no CDN or additional dependencies. From the Breeze root:

```sh
node design/promo-film/three/tools/serve.mjs
```

Open http://127.0.0.1:8772/design/astral-projection/three/index.html . Choose an exercise,
play/pause, scrub or click a cue marker. 10×/60× speeds help review long sessions.
Deep links accept `?exercise=bruce_rope_exit&t=1450`.

`src/sessions.json` is an English snapshot of the practices catalogue, all six
session timelines and exact cue captions. Refresh with
`python3 design/astral-projection/three/tools/sync-data.py`. The private test
compares the snapshot against the current upstream files before rendering.
Caption text remains present through the silence until the next cue.

Each exercise owns a separate scene, sampled directly from session seconds.
Foundation shows thumb stirring and leg strokes; Current shows limb bounces and
circuits; Elevator shows the shaft rising around a descending observer; Spin
shows an exterior awareness point (not an exit); Rope shows reaching/climbing;
Roll-Out shows left/right whole-body turns. Physical muscles stay still.
Return/recall cues stop the technique. These are guided-imagery illustrations.

The shared `design/promo-film/three/src/character-shaders.js` provides warm wrapped
lighting, a cool Fresnel rim and lightweight subsurface approximation; astral
figures use one interpolated noise octave, alpha and HDR bloom. Painted Lumi and
both Tai Chi teachers use the same palette and alpha-gradient relief shading,
preserving their source artwork and premultiplied edges. No new normal textures.
The preview caps render width at 960px and pixel ratio at 1; low-poly body meshes
share geometry/materials. Real phone GPU performance still needs device review.

Local test (owns a private Xvfb and headless Chromium; never the desktop):

```sh
build-queue -- node design/astral-projection/three/tools/verify.mjs
```

Frames and the report go to `build/astral-threejs/`. The test compares every cue
boundary, tests controls and captures several cue times in all six exercises,
plus portrait framing and promo character shader compilation. No audio plays.
