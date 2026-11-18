# Open practice figure work — 2026-11-17

The owner wants one perfected character used everywhere: Tai Chi, Sun
Salutation, Workout and astral projection, native on Ziran and Kryon
without raylib: a slim, cute young Chinese woman with sleek black hair, an
attractive Chinese-style practice outfit, matched to Inner Breeze's own
storybook illustrations with only a little texture, and vivid colour. The
character is the practices package's `figure/`; its style target is
practices `figure/design/reference/style-target.webp`, made from the Tai Chi
banner. The live tuning tool is `design/figure-preview/` (see its README).
The three.js studies in `design/astral-projection/three/` are look
references only.

- Kryon, owned by the Kryon lanes: the first-frame sampler-unit clobber in
  `scene_gpu.zi` (the figure paints its first picture twice) and the
  per-frame geometry rebuild (every moving frame re-expands all triangles
  into a new vertex buffer and re-uploads it, about 5–6 ms on llvmpipe);
  then repin and remove the workaround. Images still compare by texture id
  only, so the preview alternates two textures.
- Owner review of the live preview and of
  `build/practice-compare/side-by-side/` (current flat figure beside the new
  character, same moments and cameras), then tune from that feedback.
- Character work still open:
  - The top's lower part swings rigidly from the waist and only by the
    pelvis's tilt; secondary sway and a simple collision with the thighs
    would help in deep squats and folds.
  - The face painting is projected from the front; in profile its side
    fades to plain skin.
  - The cream piping at the top's hem and cuffs in the style target is not
    painted yet.
  - The asset bake (cloth shells, UVs, texture swatches) is Python in
    `scripts/prepare-practice-human.py`; port it to Ziran with the anatomy
    reader.
- Astral session timings: practices' `astral_projection/sessions/*.json`
  are another task's uncommitted files. Until they are pushed, a pinned
  preview plays the six techniques with steps evenly 20 seconds apart.
- Breeze adoption, after the shared Kryon repin (lane -7, plot, entity,
  game2d, css and apps on one Kryon; Breeze audio on Ziran std audio):
  - Make Breeze's `practices` dependency a package pinned at or after
    3e7c7bff.
  - Move `PreviewJoints` (solver joints to `FigureJoints`) beside the
    solver.
  - Paint Tai Chi, Sun Salutation, Workout and astral with `FigurePaint`
    under `DESKTOP_HOST`, keeping timelines, cues, narration, pause/resume
    and history. Bundle `assets/practices/shared/watercolor/` from the
    common Practices pack (the `scripts/prepare-package-assets.py` hunk is
    ready).
- Native app after-frames for those painters, matching
  `build/practice-compare/before/`. Retake the full-form before frame: it
  shows the voice-guidance offer instead of the figure.
- Performance: the painter re-skins and re-finishes on every pose change
  (the wash finish, ground shadow and backdrop on the CPU, about 20k
  vertices skinned on the CPU). Measure on a real phone GPU; shell GL here
  is llvmpipe.
- Narration: the initial audit found all 88 cue texts in each of ten
  locales but only 407/880 female clips (cs 6, de 86, en 86, es 78, fr 37,
  ja 5, ko 6, pt 88, ru 10, zh 5). Complete and listen through the owning
  narration task; legacy cues do not fill the new exercise keys.
- Refresh the three.js caption snapshot if the practices task changes
  session cues or text. Keep `build/astral-compare/before/` as the baseline.
