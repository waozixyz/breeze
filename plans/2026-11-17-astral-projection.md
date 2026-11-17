# Open astral projection work — 2026-11-17

## Review and integration still open

- Owner review of all six Three.js studies and shared character shader looks.
  Preview implementation is deliberately separate from app integration. After
  review, scope the native/Kryon equivalent; this page is not installed in Breeze.
- Reconcile the historical status notes with the already committed selection:
  `017d3565` contains the six-exercise work; `ca99ca92` updates the native
  implementation. Both precede the freshly observed remote Breeze master
  `a3a37e38`. Notes claiming “no feature commit/push” are stale for Breeze code.
  No review receipt establishes that the owner saw those screens.
- Practices master and fresh remote master both equal `b68738d0`. The six
  catalogue/session JSON files remain untracked, with localized text/audio
  changes outside this task. They are not in the pushed practices package.
  Complete and validate that lane before updating Breeze's locked practices pin
  (currently `893e5b6f`). This task changes none of those files or pins.
- Final native/package laws, size/inventory, exact media delivery and installed
  download/desktop launch verification remain open. Historical progress notes
  record successful private chooser tests at desktop/portrait sizes (guides,
  cues, countdown, pause/resume, restart, switching, completion/history) and
  native download-flow tests, but distinguish those from actual installed
  downloads. Repeat on the final integrated source/media revision; no fresh
  native GUI claim is made by this standalone web change.

## Narration still open

All ten locale catalogues contain all 88 new cues. Current local Bruce files
and receipt rows agree at the counts below; SHA-256 of each existing audio file
matches its receipt. Counts do **not** establish current synthesis-profile/text
provenance, listening quality, full decode or coverage of other voice choices.
A fresh strict narration validation and voice/listening review remain required.

| Locale | Female provider recorded | Existing / 88 | Missing |
|---|---|---:|---:|
| cs | Chatterbox Czech | 6 | 82 |
| de | Ming | 86 | 2 |
| en | Ming | 86 | 2 |
| es | Ming | 78 | 10 |
| fr | Ming | 37 | 51 |
| ja | Ming | 5 | 83 |
| ko | Ming | 6 | 82 |
| pt | Chatterbox Portuguese | 88 | 0 |
| ru | F5 Russian | 10 | 78 |
| zh | Ming | 5 | 83 |

- Finish the missing 473 of 880 new female clips through the owning narration
  task. Portuguese has full inventory, but still needs final provenance and
  integrated listening verification. Preserve all existing recordings.
- The interface specifies these female routes only. Any other selectable voice
  must be audited against actual package coverage; no complete alternate voice
  inventory or listening evidence was established here. Legacy English's 20
  old cues are separate and do not fill the new exercise keys.
- The broader progress notes' 4,960-clip target includes other practices; their
  unresolved narration items are outside this animation task.

## Preview verification and remaining limits

- Private software Chromium exercises the page; real phone GPU performance and
  visual acceptance remain open. Width is capped at 1280 (720 in Phone quality)
  and pixel ratio at 1.
- English captions are a reproducible snapshot of the current practices working
  tree, including uncommitted source data. Source JSON is not claimed pushed.
  Refresh the snapshot after the practices owner finalizes cue/text changes.
- Open locally with `node design/promo-film/three/tools/serve.mjs`, then visit
  `http://127.0.0.1:8772/design/astral-projection/three/index.html`.
- Local verification command:
  `build-queue -- node design/astral-projection/three/tools/verify.mjs`.
  Result: PASS, 88 cue boundaries (including immediately before each transition),
  exact canonical captions, six pickers/seek paths, play/pause/restart, nonblank
  canvas pixels at four cue times per exercise, six additional technique
  showcase frames, portrait layout and the real
  promo scene at 38 seconds (Lumi, monk and Tibetan woman). No JavaScript/GLSL
  errors; the unused favicon 404 is excluded. A stale FlatView import was fixed
  in the shader-touched puppet module to enable the actual promo render.
  Report: `build/astral-threejs/verification.json`.
  The expanded local test also verifies full-width styled layout, moving
  pixels, alternating rope hand grips, rope and roll reentry, fixed physical-body
  position, left/right whole-body rolls, Room Spin without an exit, active elevator, highlight
  pause/scrub behavior, Phone resolution cap and reduced-motion autoplay.
  All 32 frames passed. Sampled scenes use 61–81 draw calls including bloom;
  these software-renderer measurements do not establish real phone frame rate.
- The existing promo stack and artwork are ignored by Git. This scoped commit
  includes the three shader-touched source files only; it does not publish the
  pre-existing film assets, server or node_modules. Another machine needs that
  existing local promo setup (and Three.js 0.169.0) to run this preview/test.
  Packaging the entire film stack is outside this task.

## Visual acceptance still open after the owner's feedback

- The two actual catalogue/home images are
  `practices/astral_projection/banner-{dark,light}.webp`, both 2048×1024 RGB
  (496,600 / 593,740 bytes). Both were inspected: a resting person and a pale
  double above a lake, a thin cord and warm chest points. The paired style is
  consistent, with no visible watermark, but the scenery dominates and the
  physical body sits low in the frame. Home's `ImageFitCover` crop and title
  fade can hide it. Neither banner explains the six distinct techniques.
  Banner replacement waits while animations have priority.
- `flat-edge.png` is a deliberately tiny 6×1 RGBA edge ramp, inspected as pixels.
  It is a painter primitive, not a character sprite; replacing it with a
  detailed figure would break its purpose. `design/astral-projection/banner/`
  is empty; the practices `drafts/` folder contains prose/JSON, no artwork.
  No per-exercise raster sprite or session illustration exists in these paths.
- The existing native astral figure is painted by `AstralScenePaint` and
  `AstralPreviewDraw`: Workout pose/solve plus Tai Chi projection/painter and
  the `jadeWoman` look recolored blue/green. This explains the owner's Tai Chi
  concern. It lacks a distinct supported physical body and a separating double.
  Replacing this native painter remains app integration, after preview review.
- The initial web figures were independent sphere-based bodies, but had blunt
  limbs, paddle hands and a grid-floor setting. The revision uses independent
  sculpted humans, articulated hands/elbows, sleep trousers, a real bed and dim
  bedroom. No Tai Chi rig, pose, teacher image or promo character geometry is
  used. Two-bone rope reaches, torso peeling, whole-body rolls, tension-aware
  silver cord, breathing, particles and directed cameras now clarify the action.
  A 72-second highlights tour makes the key cue passages easy to review.
- Actual frame inspection exposed a CSS MIME gap in the reused film server:
  it had silently rendered the earlier page without styles at a 300×150 canvas.
  The preview now installs its stylesheet from fetched text; the private test
  asserts computed dark styles and a full-width desktop stage. Earlier pixel
  counts alone did not establish correct layout. Owner review of the corrected
  frames remains open. Standalone image generation is unnecessary for the
  procedural character/room, and the existing banners remain untouched.

Private-display frames (local artifacts, not committed):

- `build/astral-threejs/bruce_foundation_touch-30.png`
- `build/astral-threejs/bruce_foundation_touch-630.png`
- `build/astral-threejs/bruce_foundation_touch-870.png`
- `build/astral-threejs/bruce_foundation_touch-1110.png`
- `build/astral-threejs/bruce_full_body_current-30.png`
- `build/astral-threejs/bruce_full_body_current-750.png`
- `build/astral-threejs/bruce_full_body_current-1230.png`
- `build/astral-threejs/bruce_full_body_current-1470.png`
- `build/astral-threejs/bruce_elevator_trance-30.png`
- `build/astral-threejs/bruce_elevator_trance-870.png`
- `build/astral-threejs/bruce_elevator_trance-1470.png`
- `build/astral-threejs/bruce_elevator_trance-1710.png`
- `build/astral-threejs/bruce_spin_loosening-30.png`
- `build/astral-threejs/bruce_spin_loosening-870.png`
- `build/astral-threejs/bruce_spin_loosening-1470.png`
- `build/astral-threejs/bruce_spin_loosening-1710.png`
- `build/astral-threejs/bruce_rope_exit-30.png`
- `build/astral-threejs/bruce_rope_exit-1230.png`
- `build/astral-threejs/bruce_rope_exit-2070.png`
- `build/astral-threejs/bruce_rope_exit-2310.png`
- `build/astral-threejs/bruce_roll_out_exit-30.png`
- `build/astral-threejs/bruce_roll_out_exit-870.png`
- `build/astral-threejs/bruce_roll_out_exit-1470.png`
- `build/astral-threejs/bruce_roll_out_exit-1710.png`
- `build/astral-threejs/portrait-rope-1500.png`
- `build/astral-threejs/promo-shader-review.png`
- `build/astral-threejs/showcase-foundation-hand-169.png`
- `build/astral-threejs/showcase-current-912.png`
- `build/astral-threejs/showcase-elevator-912.png`
- `build/astral-threejs/showcase-spin-1012.png`
- `build/astral-threejs/showcase-rope-ascent-1611.png`
- `build/astral-threejs/showcase-roll-right.png`

## Shader upgrade and before/after review — owner follow-up

- Implemented dedicated astral-study skin and spirit GLSL surfaces, with wrapped
  lighting/backscatter, moon rim, restrained skin variation, layered flowing
  noise, luminous contours and an inner travelling pulse. Added technique-shaped
  translucent fields: local touch, longitudinal current, ascending descent bands,
  orbital spin and a field that follows the separating/returning double.
- Rebuilt ribbon shading with a bright core, soft halo, helical detail and flow
  packets for both the current and silver cord. The bedroom now has layered
  feathered moonlight shafts, more drifting motes, woven linen and a floor pool.
  A dedicated finishing pass adds restrained chromatic shift, vignette, tint and
  deterministic grain, with bloom and shift tuned per technique. These are
  bounded procedural shader approximations; no volume ray march or textures.
- Preserved cue timing, captions, original directed-camera poses, hand-over-hand
  ascent, left/right roll, float and return. The shared promo material remains
  unchanged by this follow-up. Native app integration and banners still wait.
- Final local test: `ASTRAL_COMPARE=1 build-queue -- node
  design/astral-projection/three/tools/verify.mjs` — PASS, all 88 cue boundaries,
  32 standard frames and seven additional matched comparison captures. Controls,
  pause/scrub, highlights, return poses, portrait layout, reduced motion and the
  actual promo shaders passed; no JavaScript/GLSL errors (favicon 404 excluded).
- Comparison local test: `build-queue -- python3
  design/astral-projection/three/tools/compare.py` — PASS, seven labelled pairs,
  matched viewport widths and visible stage differences. `before/` is read only;
  `build/astral-compare/comparison.json` stores source hashes, cue seconds, camera
  names and pixel differences. Images are joined without resizing; a longer
  caption/page gets padding below. All seven pairs were visually inspected.
- Before: `build/astral-compare/before/`; new captures and report:
  `build/astral-compare/after/`. Comparison images:
  - `build/astral-compare/side-by-side/showcase-foundation-hand-169.png`
  - `build/astral-compare/side-by-side/showcase-current-912.png`
  - `build/astral-compare/side-by-side/showcase-elevator-912.png`
  - `build/astral-compare/side-by-side/showcase-spin-1012.png`
  - `build/astral-compare/side-by-side/showcase-rope-ascent-1611.png`
  - `build/astral-compare/side-by-side/showcase-roll-right.png`
  - `build/astral-compare/side-by-side/portrait-rope-1500.png`
- Opened the first comparison in native Gwenview; the launch result confirmed
  `running: true`. The owner can page through all seven. No live desktop pixels
  were captured and no mouse input was used. Owner acceptance and real phone GPU
  frame rate remain unverified; the web preview is not installed in Breeze.

## Anatomical watercolor version — latest owner follow-up

The owner rejected the primitive body and requested watercolor shaders and real
textures. The final version replaces the sphere/lathe figure entirely:

- Sleeper and double share the CC0 MakeHuman hm08 continuous anatomical mesh:
  13,380 vertices, 26,756 triangles, shaped face/neck/shoulders/torso/hips,
  actual hands/fingers/feet, reposed resting limbs and blue pigment sleep clothes.
  A 37-bone skin rig supports shoulder/elbow reaches, wrist movement and curls
  in individual finger segments. Rope gripping deforms the bound surface; it
  no longer switches between separate primitive hands. The original whole-body
  roll, lift, float and return timelines remain intact.
- Source and licence: [MakeHuman base.obj](https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/makehuman/data/3dobjs/base.obj),
  explicitly CC0 in the source header. See the
  [asset licence](https://github.com/makehumancommunity/makehuman/blob/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/LICENSE.md)
  and local `design/astral-projection/three/assets/MAKEHUMAN-CC0.txt`.
  The pinned source, unmodified compressed OBJ, derived binary and reproducible converter
  are retained. Only the 803 KB binary and compact rig metadata load at runtime.
- Watercolor materials apply pigment washes, soft shading bands, edge pooling,
  granulation and paper modulation to the human and room. The double samples a
  luminous watercolor wash while preserving transparency and flowing energy.
  The final scene pass uses a four-quadrant minimum-variance brush filter,
  subpixel wet-edge bleed, broken pencil contours and actual paper texture.
  The room, figures, cord, rays and energy share the same painted finish.
- Six generated 256×256 bitmap textures cover paper, pigment, linen bedding,
  plaster wall, wood floor and luminous wash: 80,982 bytes total. Generated with
  the built-in imagegen tool, inspected for watermark/text, and saved as WebP
  files in `design/astral-projection/three/assets/`. The full prompt and texture
  provenance are in `assets/README.md`; the full source atlas is preserved
  locally in ignored `backup/astral-threejs/watercolor-source-atlas.png`.
- Visual inspection caught and fixed excluded low hand vertices that produced
  spikes. The converter now validates finite positions, normalized weights,
  resting hand bounds and maximum anatomical edge length (0.1044 scene units).
  The touch point now follows the actual thumb joint instead of the old rig's
  hard-coded location. Local browser assertions verify thumb proximity, actual
  finger curls, all cue captions/timings and the exit/return poses.
- Local verification commands are unchanged: mesh preparation through
  `build-queue -- python3 design/astral-projection/three/tools/prepare-human.py`,
  then `ASTRAL_COMPARE=1 build-queue -- node
  design/astral-projection/three/tools/verify.mjs`, then
  `build-queue -- python3 design/astral-projection/three/tools/compare.py`.
  The final after/comparison paths listed above now refer to this anatomical
  watercolor version; the original before files remain unchanged.
- No native app integration, banner replacement or phone GPU performance claim
  is included. Owner visual acceptance remains open after showing the new set.

Final watercolor local result: PASS for mesh preparation (maximum edge 0.1044),
all 88 cue boundaries, 32 standard private-display frames and seven matched
comparison captures. Anatomical thumb alignment, deforming finger grips,
exit/return poses, controls and promo shader rendering passed. The seven
comparison checks passed and all seven pairs were inspected. The final
watercolor set was reopened in Gwenview with `running: true`. Pushed status is
reported separately from these local results; no app installation is claimed.
