# Astral exercise motion studies

Standalone review page; no app integration. Reuses the promo-film installation of
**Three.js 0.169.0**, with no CDN or additional dependencies. From the Breeze root:

```sh
node design/promo-film/three/tools/serve.mjs
```

Open http://127.0.0.1:8772/design/astral-projection/three/index.html . The first
technique plays immediately unless reduced motion is enabled. Exercise cards
jump into each technique. **Watch highlights** tours six cue passages in 72
seconds; **Full session** continues from that position. Pause, scrub or click
a cue marker; 10×/60× speeds help review long sessions. **Restart** returns to
the complete session's beginning. The stylesheet is installed from fetched
text because the existing film server has no CSS MIME mapping.
Deep links accept `?exercise=bruce_rope_exit&t=1450`.

`src/sessions.json` is an English snapshot of the practices catalogue, all six
session timelines and exact cue captions. Refresh with
`python3 design/astral-projection/three/tools/sync-data.py`. The private test
compares the snapshot against the current upstream files before rendering.
Caption text remains present through the silence until the next cue.

Each exercise owns a separate scene, sampled directly from session seconds.
The characters are independently sculpted reclining humans, with closed eyes,
individual fingers/toes, arm/elbow/palm pivots and sleep trousers. They share
no rig, poses, artwork or geometry with the Tai Chi teachers or promo puppets.
The dim bedroom contains a bed, pillow, window, curtains and a warm bedside
lamp. All geometry and effects are procedural; no generated bitmap is needed.
Directed cameras frame the hand, pathways and exit motion. **Steady** removes
camera drift. Full canonical captions appear below the shorter action labels.
Foundation shows thumb stirring and leg strokes; Current shows limb bounces and
circuits; Elevator shows the shaft rising around a descending observer; Spin
shows an exterior awareness point (not an exit); Rope shows reaching/climbing;
Roll-Out shows left/right whole-body turns. Physical muscles stay still.
Return/recall cues stop the technique. These are guided-imagery illustrations.

The shared `design/promo-film/three/src/character-shaders.js` provides warm wrapped
lighting, a cool Fresnel rim and lightweight subsurface approximation; astral
figures use two flowing noise layers, translucent bands, veins and HDR bloom.
Pathways and the silver cord reuse ribbon buffers; cord slack decreases with
separation. Rope hands alternate two-bone reaches, the torso peels upward,
then the double floats and rejoins the physical body on the return cue.
Painted Lumi and
both Tai Chi teachers use the same palette and alpha-gradient relief shading,
preserving their source artwork and premultiplied edges. No new normal textures.
The preview caps render width at 1280px (720px in **Phone** quality), pixel
ratio at 1. Static sculpted pieces are merged per material while preserving
the arm pivots. No shadow maps or external textures are added. Real phone GPU
performance still needs device review.

Local test (owns a private Xvfb and headless Chromium; never the desktop):

```sh
build-queue -- node design/astral-projection/three/tools/verify.mjs
```

Frames and the report go to `build/astral-threejs/`. The test compares every cue
boundary, tests controls and captures several cue times in all six exercises,
plus exit/return poses, changing animation pixels, highlights pause/scrub,
computed styles, portrait framing, reduced-motion autoplay and promo character
shader compilation. No audio plays.
