# Open practice figure work — 2026-11-18

The owner wants one figure model used everywhere: Tai Chi, Sun Salutation,
Workout and astral projection, native on Ziran and Kryon without raylib. It
must look as good as the owner's reference sculptures (practices
`figure/design/reference/`): smooth, correct proportions, clean colours.
The default is a pretty, petite young Asian woman; a man is the second
choice. Breeze colours and backdrops stay.

The MakeHuman-based figures were removed on 2026-11-18 at the owner's
request; never use a MakeHuman-based body again (MakeHuman, MPFB, Anny,
MB-Lab, CharMorph). The owner picked pixiv's CC0 VRoid sample models
(practices `shared/figure/woman.vrm` and `man.vrm`); the preview
(`design/figure-preview/`) plays every practice with her or him.

- Tai Chi parity: `make test`'s `tests/tai_chi_zi_test.sh` compares the
  app's solver with the studio's reference, regenerated for the natural
  stepping, pivots, hand turning, soft reach and toe clamp
  (`node design/tai-chi/tools/export-app.mjs --reference`). The studio's
  course differs from the course.tch in the pinned practices package, so
  sample 11 (the right palm) differs until the owner of the course exports
  it to practices and Breeze repins.
- Motion still to smooth (`figure_preview --audit`): the Workout side
  plank's roll to the second side drifts the feet 2-3 cm (the feet have no
  edge to roll on) and jerks the left elbow once; two Tai Chi wrist turns
  (Single Whip again, the full form at 170 s) change speed at 27 m/s².
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
- The three.js astral studies (`design/astral-projection/three/`) still
  play stand-in skeletons; load the chosen VRM there.
