# Open practice figure work — 2026-11-18

The owner wants the practice figures used everywhere: Tai Chi, Sun
Salutation, Workout and astral projection, native on Ziran and Kryon
without raylib. They must look as good as the owner's reference sculptures
(practices `figure/design/reference/`): correct proportions, smooth
surfaces, clean colours, no paint, paper or grain. The default is a petite
young Chinese woman with black hair, smooth skin and an attractive Chinese
outfit; a young man in a kung fu outfit is the second character, to be
offered as a choice. Breeze colours and backdrops stay. The characters are
the practices package's `figure/`; the live tuning tool is
`design/figure-preview/` (see its README). The three.js studies in
`design/astral-projection/three/` are look references only.

- Owner review of the live preview, of the reference comparisons in
  `build/practice-compare/reference/` and of the before/after side-by-sides
  in `build/practice-compare/side-by-side/`; tune from that feedback.
- Better base mesh once Kryon's glTF importer lands (the Kryon task
  codex-kryon-kryon-idle-present-fix has it queued): a properly licensed
  higher-resolution base (MakeHuman/MPFB CC0 with a high-res proxy, or
  another CC0/CC-BY model with its licence recorded in practices
  `figure/design/`), chosen by how close it comes to the references. Never
  use ripped game models (the owner's Character-14.zip is one).
- Character work still open:
  - The jacket's skirt swings rigidly from the waist and only by the
    pelvis's tilt; secondary sway and a simple collision with the thighs
    would help in deep squats and folds.
  - The face map is projected from the front; in profile its side fades
    to plain skin.
  - No ambient occlusion yet: crevices (armpits, under the bun, between the
    legs) are lit like open surfaces. Bake it per vertex once the vertex
    format has room, or add it to Kryon's material.
  - The asset bake (shapes, clothes, hair, UVs, texture maps, the face) is
    Python in `scripts/prepare-practice-human.py`; port it to Ziran with the
    anatomy reader.
- Astral session timings: practices' `astral_projection/sessions/*.json`
  are another task's uncommitted files. Until they are pushed, a pinned
  preview plays the six techniques with steps evenly 20 seconds apart.
- Breeze adoption, after the shared Kryon repin (lane -7, plot, entity,
  game2d, css and apps on one Kryon; Breeze audio on Ziran std audio):
  - Make Breeze's `practices` dependency a package pinned at or after the
    commit that has both characters.
  - Move `PreviewJoints` (solver joints to `FigureJoints`) beside the
    solver.
  - Paint Tai Chi, Sun Salutation, Workout and astral with `FigurePaint`
    under `DESKTOP_HOST`, keeping timelines, cues, narration, pause/resume
    and history, with a setting for the woman or the man. Bundle
    `assets/practices/shared/figure/` from the common Practices pack.
- Native app after-frames for those painters, matching
  `build/practice-compare/before/`. Retake the full-form before frame: it
  shows the voice-guidance offer instead of the figure.
- Performance: measure on a real phone GPU; shell GL here is llvmpipe.
  The figure re-skins and recomputes normals for about 17k vertices on the
  CPU every moving frame.
- Narration: the initial audit found all 88 cue texts in each of ten
  locales but only 407/880 female clips (cs 6, de 86, en 86, es 78, fr 37,
  ja 5, ko 6, pt 88, ru 10, zh 5). Complete and listen through the owning
  narration task; legacy cues do not fill the new exercise keys.
- Refresh the three.js caption snapshot if the practices task changes
  session cues or text. Keep `build/astral-compare/before/` as the baseline.
