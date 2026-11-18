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
The figure model is pending: the MakeHuman-based body was removed on
2026-11-18, and the owner will choose a new, commercially licensed model.
Until then both figures are invisible stand-in skeletons with the joints the
scenes drive (shoulders, elbows, wrists and finger chains for the rope
grips), so the rooms, energy effects, cords and cameras still play.
The dim bedroom contains a bed, pillow, window, curtains and a warm bedside
lamp. Room geometry and energy effects are procedural; the painted material
maps are loaded from local assets.
Directed cameras frame the hand, pathways and exit motion. **Steady** removes
camera drift. Full canonical captions appear below the shorter action labels.
Foundation shows thumb stirring and leg strokes; Current shows limb bounces and
circuits; Elevator shows the shaft rising around a descending observer; Spin
shows an exterior awareness point (not an exit); Rope shows reaching/climbing;
Roll-Out shows left/right whole-body turns. Physical muscles stay still.
Return/recall cues stop the technique. These are guided-imagery illustrations.

The entire scene now follows one watercolor direction. `src/surfaces.js`
combines soft shading bands, pigment pooling at edges, paper granulation,
backscatter-style warmth and painted fabric on the sleeper. The translucent
double uses a luminous wash, flowing noise, contour bands and a soft rim.
The bedroom samples actual paper, linen, plaster and wood textures with
pigment modulation and soft shade bands. Six generated 256px WebP textures
add approximately 81 KB, with no remote texture fetches.

`src/finish.js` uses a bounded four-quadrant minimum-variance brush filter,
subpixel wet-edge disturbance, broken pencil contours and a textured paper
finish. The effects pass covers the room, figures, cord, rays and energy, so
they share the painted treatment. The translucent fields still distinguish
local touch, longitudinal current, ascending elevator bands, orbital spin
and the separating/returning double. Cameras, cue seconds and captions remain
fixed for comparison against the original before frames. Bloom is restrained
to preserve the painted character silhouette.

The earlier shared promo-film shaders still shade painted Lumi and both Tai Chi
teachers; this upgrade leaves their source artwork and materials intact.
The preview caps render width at 1280px (720px in **Phone** quality), pixel
ratio at 1. Each figure owns its stand-in skeleton until the new model is
chosen. No shadow maps are used. Textures are local files. Real phone GPU performance
still needs device review.

Local test (owns a private Xvfb and headless Chromium; never the desktop):

```sh
build-queue -- node design/astral-projection/three/tools/verify.mjs
```

Frames and the report go to `build/astral-threejs/`. The test compares every cue
boundary, tests controls and captures several cue times in all six exercises,
plus exit/return poses, changing animation pixels, highlights pause/scrub,
computed styles, portrait framing, reduced-motion autoplay and promo character
shader compilation, the stand-in skeleton, finger curls and thumb-marker
alignment. No audio plays.

For matching before/after review, preserve the previous six `showcase-*.png`
frames and `portrait-rope-1500.png` in `build/astral-compare/before/`, then run:

```sh
ASTRAL_COMPARE=1 build-queue -- node design/astral-projection/three/tools/verify.mjs
build-queue -- python3 design/astral-projection/three/tools/compare.py
```

The comparison option renders the same cue seconds and directed camera poses,
matching each original's viewport width. It writes seven new captures to
`build/astral-compare/after/`. The Pillow comparison tool labels before on the
left and after on the right without resizing either source; a taller page is
padded below, preserving the complete captions. Results are in
`build/astral-compare/side-by-side/`; `comparison.json` records source hashes,
cue times, camera names and stage differences. Before files are read only.
