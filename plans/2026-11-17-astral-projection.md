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

## Handoff — natural movement (2026-11-18, moving to Codex)

- Model 4 (pixiv CC0 VRoid woman and man) is committed in practices
  `shared/figure/` and is what the preview shows (Woman/Man switch).
  practices d8b54df1: VRM hair and clothes on spring bones, eye blinks
  (`FigureModelPose(..., seconds)`, `FigureBlink`).
- Kryon `src/ui/scene_vrm.zi` is pushed (Kryon ac6c8f47): VRM 0.x
  humanoid map, expressions, lookAt, spring bones with sphere colliders,
  fixed 60 Hz, world frame. `scene_bvh.zi` is not started: every practice
  is hand-keyed and timed to its narration, and the audit's faults were in
  stepping, IK and interpolation, not in the keys, so mocap has not been
  needed yet.
- Motion audit: `figure_preview --audit` (every item at 30 fps; slides on
  the floor and on screen, floor, jerks, knees, hands, a pinned head).
  Fixed in Breeze 924553d6: feet step and pivot instead of sliding
  (TaiChiStepFoot, the timeline's step and pivot), toes clamp above the
  floor, soft two-bone reach, hand frames slerped between keys, side
  plank roll. 589 findings fell to 9 at the old 2 cm bound.
- The preview no longer follows her pelvis every frame (which pinned her
  in the middle and made her feet slide over the painted floor): each item
  is framed once from its whole motion with a fixed camera
  (`PreviewFrame`); long forms are framed whole, so pan the backdrop with
  a slow follow if they should be closer. The audit now measures a slide
  as distance from where the heel or ball was set down (5 mm), also on
  screen, and flags a head held in place: 66 findings remain, 34 Tai Chi
  step and side-plank-roll slides (Wild Horse, Snake, the full forms), the
  same 28 on screen, 4 jerks, no pinned head.
- Tests: `build-queue -- make workout-test sun-salutation-pose-test`
  (planted feet within 5 mm, floor, speed, knees); practices
  `figure_parts_test` (README); Kryon `build-queue -- make
  scene-gltf-test`; the preview audit.
- Remains: zero-slide foot locking where the audit still finds drift
  (lock a planted foot's floor point through the timeline's blends, with
  two-bone leg IK; the side plank roll); root
  weight shift and breathing for Tai Chi; head and gaze follow with VRM
  lookAt; relaxed fingers check; the before/after clips
  (`make-videos.sh` in the task scratchpad renders them from
  `build/before` and `build/app` with `--video`); Tai Chi parity below.

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
