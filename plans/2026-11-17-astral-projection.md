# Open practice figure work — 2026-11-17

The owner asked for the anatomical watercolor figures in the real Breeze app
(Ziran + Kryon, no raylib) for Tai Chi, Workout and astral practice. The
three.js studies in `design/astral-projection/three/` are the look reference
only. The shared figure media is in practices `shared/watercolor/`:
MakeHuman CC0 surface, MakeHuman CC0 default rig weights folded onto 46
bones, clean plane-cut hems, and paper/pigment/wash textures.

- Shared Kryon repin. Breeze pins Kryon 3f724419, which has no
  `kryon/scene_skin` or `kryon/watercolor`. The repin must move plot, entity,
  game2d, css and apps to the same Kryon, and move
  `src/platform/audio_runtime.zi` and `radio_native.zi` from Kryon's removed
  mixer/sink/decoders to Ziran std audio. It is coordinated with the
  raylib-free desktop work (`plans/2026-11-15-breeze-desktop-without-raylib.md`).
  The coordinator decides who owns that switch.
- Connect the painters after the repin, all under `DESKTOP_HOST`:
  - Tai Chi: `TaiChiPaintFlat` call sites in `tai_chi_draw.zi`, through
    `PracticeWatercolorDraw`.
  - Workout: its solved pose through the same painter.
  - Astral: `AstralSceneDraw`/`AstralPreviewDraw` through
    `AstralWatercolorDraw` (`apps/practice/astral_watercolor_view.zi`), which
    composes the still physical body, translucent double, cord, rope and
    attention marks from `astral_technique.zi`.
  Keep existing timelines, cues, narration, pause/resume and history.
- Native after frames on private Xvfb, matching `build/practice-compare/before/`
  (Tai Chi 9 s, full form 131 s, astral 60 s, Workout ready). Then labelled
  `side-by-side/` images, own inspection, and Gwenview for the owner. Retake
  the full-form before frame, which shows the voice-guidance offer instead of
  the figure.
- Local suites on the integrated build: `make astral-projection-test` (now
  includes `tests/astral_technique_test.sh`), Tai Chi and Workout tests,
  `tests/practice_human_test.sh`, build laws, package/size checks, chooser
  previews, captions and cue boundaries. Bundled delivery of
  `assets/practices/shared/watercolor/` from the common Practices pack is
  configured in `scripts/prepare-package-assets.py`; verify it in the
  built app.
- Performance: the painter re-renders and re-finishes the body on every pose
  change. Measure on a real phone GPU; shell GL here is llvmpipe.
- Owner review of the native characters, watercolor look, Tai Chi motion and
  the six astral techniques.
- Narration: the initial audit found all 88 cue texts in each of ten locales
  but only 407/880 female clips (cs 6, de 86, en 86, es 78, fr 37, ja 5,
  ko 6, pt 88, ru 10, zh 5). Complete and listen through the owning
  narration task; legacy cues do not fill the new exercise keys.
- Refresh the three.js caption snapshot if the practices task changes session
  cues or text. Keep `build/astral-compare/before/` as the baseline.
