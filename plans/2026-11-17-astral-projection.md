# Open practice figure work — 2026-11-18

The owner wants one figure model used everywhere: Tai Chi, Sun Salutation,
Workout and astral projection, native on Ziran and Kryon without raylib. It
must look as good as the owner's reference sculptures (practices
`figure/design/reference/`): smooth, correct proportions, clean colours.
The default is a pretty, petite young Asian woman; a man is the second
choice. Breeze colours and backdrops stay.

The MakeHuman-based figures were removed on 2026-11-18 at the owner's
request; never use a MakeHuman-based body again (MakeHuman, MPFB, Anny,
MB-Lab, CharMorph). The live tuning tool `design/figure-preview/` shows
the empty stage with a "model pending" note.

- The owner picks a model from `plans/2026-11-18-figure-model-candidates.md`
  (contact sheet: `build/model-candidates/contact-sheet.png`).
- Kryon's glTF importer (meshes, skins, animations, morph targets, PBR
  materials) is being added in another task; the picked model loads
  through it.
- Then: map `FigureJoints` (practices `figure/figure_joints.zi`) onto the
  model's skeleton, light it with Kryon's standard material, and show it on
  the preview's stage and in the capture frames.
- Astral session timings: practices' `astral_projection/sessions/*.json`
  are another task's uncommitted files. Until they are pushed, a pinned
  preview plays the six techniques with steps evenly 20 seconds apart.
- Breeze adoption, after the shared Kryon repin (lane -7, plot, entity,
  game2d, css and apps on one Kryon; Breeze audio on Ziran std audio):
  - Move `PreviewJoints` (solver joints to `FigureJoints`) beside the
    solver.
  - Paint Tai Chi, Sun Salutation, Workout and astral with the new figure
    under `DESKTOP_HOST`, keeping timelines, cues, narration, pause/resume
    and history, with a setting for the woman or the man.
- Narration: the initial audit found all 88 cue texts in each of ten
  locales but only 407/880 female clips (cs 6, de 86, en 86, es 78, fr 37,
  ja 5, ko 6, pt 88, ru 10, zh 5). Complete and listen through the owning
  narration task; legacy cues do not fill the new exercise keys.
- The three.js astral studies (`design/astral-projection/three/`) play with
  invisible stand-in skeletons until the new model is chosen.
