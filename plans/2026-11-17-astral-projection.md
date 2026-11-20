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

## Codex continuation — 2026-11-18 (in progress)

Scope received from the coordinator: finish planted-foot locking, stance
weight transfer and breathing, gentle head/eye follow and relaxed fingers;
check every Workout and Sun Salutation step, export the studio course into
canonical practices, repin the preview, then show private before/after clips.
The rendering-performance lane owns Kryon's scene_gltf/scene_skin/scene_gpu
and present path. Those files have not been changed here.

Implemented locally, not yet committed:

- Grounded Tai Chi and Workout IK keeps its endpoint, blending soft reach
  back in only as the foot lifts. Pelvis reach limiting yields smoothly.
- Weight transfers smoothly onto heel or ball over 14 degrees, avoiding a
  derivative discontinuity that jerked the whole torso in Single Whip.
- Tai Chi has a six-second, 2 mm breath and 0.15-degree chest movement.
  The existing keyed load still drives weight shift and the head follows
  its cued gaze. VRM eyes lead that head turn by a bounded small amount.
- Fingers have a graduated relaxed curl; a hook curls the tips separately.
  Both figures keep their selected models, textures and shader appearance.
- Side-plank roll takes 2.4 seconds and computes its handover contact from
  the rig's actual ball distance. Approximate middle-pose dimensions were
  causing a 3.182 mm discontinuity when support changed feet.
- The audit separates true floor contact (1 micrometre height tolerance)
  from peeling/landing; checks drift at 0.1 mm, and prints contact sample
  counts and maximum drift. The former 2 cm contact-height test counted
  low swing feet as planted. Floor, speed, acceleration and joint bounds
  were not relaxed.
- The studio exporter accepts `--media-dir` and `--course-only`; canonical
  practices `taichi/course.tch` was exported without editing package caches
  or narration/locale text. The parity harness accepts `PRACTICE_MEDIA`
  and stages its course binary in its own test output directory.
- `design/figure-preview/review.py` prepares resumable, hash-identified
  before/after videos and a contact sheet for both figures on private Xvfb.

Completed local verification:

- Baseline preview audit reproduced 66 findings (34 world slides, 28 screen
  slides and 4 jerks).
- Intermediate audit passed the old 5 mm limit: 255,689 contact samples,
  no floor/jump/knee/hand/pinned-head findings; worst drift 3.182 mm. The
  stricter audit isolated that residual side-plank handover and tiny IK
  compression during held Workout/Sun poses; these have since been edited.
- Practices: `build-queue -- ziran build --project --target=c --exe
  --entry figure_parts_test:main -o build/figure-parts-test
  tests/figure_parts_test.zi` and
  `build-queue -- ./build/figure-parts-test/figure_parts_test` passed,
  including eye-follow and relaxed/fist/hook finger regression cases.
- Strict audit completed successfully (desktop_run
  `77ca6ea365ca5e4b5ec248b7556d916251d1`): every Tai Chi item, both Sun
  Salutation rounds, all twelve Workout exercises and all six astral
  techniques at 30 fps. Zero slides, floor penetrations, jerks, backwards
  knees, hands through the trunk, screen slides or pinned heads; 264,014
  contact samples, maximum planted drift 0.000000214647 metres. These are
  solver-joint measurements, separate from the rendered-model review.
- `build-queue -- bash -c 'node design/tai-chi/tools/export-app.mjs
  --reference --media-dir ../../modules/practices &&
  PRACTICE_MEDIA=/mnt/storage/Projects/waozixyz/modules/practices
  sh tests/tai_chi_zi_test.sh &&
  make workout-test sun-salutation-pose-test'` passed (desktop_run
  `bc3ee581f32dd9ea06df89fa2dc10606ecc5`). The formerly failing Tai Chi
  sample 11 now agrees with the exported canonical course.

Private render review completed successfully (desktop_run
`ccc42e1ed3ecb388b0be14c25fad0ee5e4b3`):

- `build/practice-motion-review/tai-chi-before-after.mp4`
- `build/practice-motion-review/sun-salutation-before-after.mp4`
- `build/practice-motion-review/workout-before-after.mp4`
- `build/practice-motion-review/astral-before-after.mp4`
- `build/practice-motion-review/contact-sheet.jpg` (woman and man).

The final clips were regenerated after fixing model retargeting (desktop_run
`c19b992dbb89e7a657f9fe2f925326908c2e`). Both figures' wrists now use the
cued palm frame, converted through the avatar's bind pose. Limbs solve with
each avatar's actual segment lengths, retaining its proportions and reaching
the solver's wrist/ankle targets rather than matching bone direction alone.

Selected-model regression and figure-parts tests passed (desktop_run
`231362e559e293f46bf9850b64283679f87f`), from canonical practices:

```sh
build-queue -- bash -c 'ziran build --project --target=c --exe --entry figure_model_pose_test:main -o build/figure-model-pose-test tests/figure_model_pose_test.zi && ./build/figure-model-pose-test/figure_model_pose_test && ziran build --project --target=c --exe --entry figure_parts_test:main -o build/figure-parts-test tests/figure_parts_test.zi && ./build/figure-parts-test/figure_parts_test'
```

The regression measures actual model nodes for both selected VRMs: ankle,
wrist and planted drift all below 0.1 mm while the pelvis moves; palm
orientation also passes. The rebuilt preview's complete solver audit still
has zero findings and the same 264,014 contact samples. These numerical
tests do not measure every vertex or clothing collision.

The complete rendered review covers all twelve Workout exercises at 7.5,
15 and 22.5 seconds and each step of both Sun Salutation rounds, with both
figures. `--review-points` takes timestamps from the preview's timing rules.
`review.py --coverage-only` resumes that part without repeating the four
finished clips. Completed desktop_run `5357cb7a54ca47f56a3a671012e3a06fe79c`:
`workout-all-poses.jpg`, `sun-salutation-all-poses.jpg` and `coverage.json`
beside the clips. The earlier capture failed because the script expected
`15.0.png` while native `FormatDecimal` writes `15.png`; lookup now follows
the native one-decimal filenames.

VLC and Gwenview opened the finished four-clip playlist and comparison
sheet successfully. All 120 Workout/Sun coverage images and the four floor comparisons were
regenerated after the floor/shoe follow-up, then inspected and opened.
The stable native preview is running with the current checkout's figure
code and media. Remaining: complete the shared integrated app validation,
commit own files through private indices, push practices, update both
Breeze/preview practices pins with Ziran's package commands and verify the
pinned preview, then commit/push Breeze.
Other tasks' styles, platform code, narration, cue JSON, Tai Chi draw and
toolchain pin edits remain outside this change. No release or version bump.

## Remaining outside this movement change

- Adopt the selected VRM figures in Breeze's practice screens after the
  shared Kryon integration. Keep timelines, captions, narration, pause/resume
  and history, and expose the existing woman/man choice. This task verifies
  the native design preview; it does not claim the app screens use VRM yet.
- The rendering-performance task owns Kryon scene and presentation changes.
  Its newer dependency pin needs its own verified handoff before adoption.
- Complete astral narration through its owning task. The initial audit found
  88 cue texts per locale but only 407/880 female clips across ten locales;
  that historical count has not been re-audited by this movement change.
- Verify the owning narration task's session JSON has been pushed before
  claiming the pinned preview uses the final astral cue timings.
- Load the selected VRMs in the existing three.js astral studies; they still
  use stand-in skeletons. No change to those studies here.
- A BVH importer remains unstarted. These practices are hand-choreographed
  to narration; the diagnosed motion faults were in IK, stepping and
  interpolation, and were repaired there.

## Owner follow-up: ground registration and plain slippers — 2026-11-18

Owner feedback relayed by the coordinator: Tai Chi looks like walking on
the thin wall; Workout is too close to/off the deck; measure real soles,
put feet on the floor, and replace both pairs of fashion shoes with simple
flat cloth Tai Chi slippers. This extends the current unfinished change.

- Each original painting has clear open ground. Same-name JSON files beside
  `shared/figure/backdrops/*.webp` store normalized source coordinates:
  Tai Chi floor `(0.20,0.81)–(0.80,0.97)`, Sun `(0.40,0.87)–(0.60,0.97)`,
  Workout `(0.20,0.79)–(0.80,0.96)`, astral `(0.18,0.78)–(0.82,0.96)`.
  Camera pitch and cover crop are stored with them. No repaint is needed.
- `preview_ground.zi` transforms those areas through the same cover crop
  as the bitmap, fits whole-motion body/ground bounds, and anchors the
  shadow and feet inside the safe floor. The camera remains fixed through
  each item. Shadows now lie on `y=0`, rather than a guessed plane below
  the lowest current joint.
- Complete 30 Hz audit at portrait, live-preview and landscape aspects
  passed: zero ground escapes over 10,589,970 projected foot/shadow samples
  (desktop_run `09cedc736a720fe1dd80b412373f96664ea0`). The existing strict
  motion audit still has zero findings, 264,014 contact samples.
- A reproducible CC0 mesh pipeline replaces only shoe primitives with
  matte stone/charcoal cloth slippers. Originals' shoe bounding heights
  were 172.56 mm (woman) and 104.62 mm (man). New upper height is 57 mm,
  with a 3 mm edge, one flat sole plane, no heel or platform. Original
  non-shoe primitives and every original bitmap/accessor byte are unchanged
  (`tests/slippers_test.py`, desktop_run `f5570f1b59fb9232e661191e682db64602f5`).
- Actual underside vertices are measured at load. Foot turns use the sole
  plane instead of aiming the ankle-to-toe bone, and support is retargeted
  to the solver's heel/ball. Sole length is fitted to that span to avoid a
  contact jump when support changes from heel to ball. Foot-only meshes
  use exact affine skinning for this adjustment; other meshes retain DQ.
- Actual skinned-vertex regression passed both figures in flat stances and
  heel/ball pivots (desktop_run `d63a7e13dd2d907c0f85aa6d8f3426f085dd`):
  woman floor error 0.00001659 mm, pivot error 0.00001746 mm;
  man floor error 0.00000222 mm, pivot error 0.00001017 mm;
  flatness below 0.000001 mm. Both ankle/wrist/palm regressions also pass.
- The additional whole-timeline rendered-sole audit caught 1–9 mm errors
  in nearly straight Tai Chi stances (desktop_run
  `2254d8e3c11bf7090ae10eacd8ca4035d9fc`). The retargeter now places the
  pelvis within both real legs' reach before solving to the measured
  supports. Whole-timeline verification passed as desktop_run
  `3294ac950ee202ea27e0df5d2b219a125d8d`: 5,970 distinct poses and 324,258
  planted vertices; maximum floor gap 0.00001636 mm, flatness 0.2578 mm,
  heel/ball error 0.00001648 mm. It samples every second and skips exactly
  repeated lower-body states, also checking elevated step-up support.
  Dense pivot/near-straight regressions and the independent 30 Hz
  ground/motion audits cover the other boundaries.
- Complete Workout visual coverage revealed that this native preview
  omitted the app's wall and bench. It now renders those same support
  dimensions with shared depth, and includes their bounds in floor fitting.
  This fixes unsupported-looking wall sits, step-ups and triceps dips.
- Frozen pre-floor frames are `build/practice-motion-review/floor-before-*.png`.
  `review.py` wrote one `*-floor-before-after.jpg` per practice after the
  final rebuild; all four were inspected and opened in Gwenview.
  Render/audit command
  `e1c9c6cc16d2ebba7229b80d90200ea46c57` passed: all four comparison
  pictures and clips, 120 Workout/Sun poses, zero 30 Hz motion findings,
  zero escapes in 10,589,970 projected foot/shadow/support samples.
- Private image inspection confirmed both figures stand on the courtyard,
  grassy area, deck and veranda; wall/bench supports also render correctly.
  It caught a clipped head in crunches: framing now follows the posed head
  direction and includes clothing/hair extents. Review captures additionally
  reject a missing silhouette or any silhouette touching an image edge.
- Regression/native-capture/root-gate command
  `e5e4d5ebe7f4dd4bcf143909ab8b232da742` stopped at a Ziran array-literal
  syntax error in the new avatar-reload reset. The reset now uses explicit
  element assignments. Corrected run
  `bcf70c122718a723ed186f2fc7d73b04e00f` passed all scoped regressions,
  renders, motion/floor audits, Tai Chi parity, Workout/Sun tests,
  `build-laws` and `package-check`. Its only failing pre-push gate was
  app bundles: `Apps controller differs from the reviewed native digest`
  at `mk/apps.mk:31` (`build/node-apps/library.zx`). The coordinator routed
  this to the existing controller/artifact-review lane. No commit/push yet.
- Reusing the model for Woman/Man now resets measured sole points before
  loading the next avatar; the real-mesh regression reuses one model to
  cover this live picker path.

Unchanged details for the owner to decide later: the woman's large white
hair ribbon and flared skirt, and the man's hoodie. No other outfit changes
are included.


## Final scoped verdict — 2026-11-18

The movement, sole contact, floor registration, flat shoes and framing
changes pass their local tests. The last full command was:

```sh
build-queue -- bash backup/figure-motion/verify.sh
```

The ignored script records the exact canonical-practices model tests,
slipper source-preservation test, native preview rebuild, private Xvfb
review/capture, Tai Chi parity and `make workout-test
sun-salutation-pose-test build-laws package-check`, followed by the relevant
pre-push plan. Overall exit was 1 solely because the shared app-bundle
controller digest gate failed; every scoped motion/render test passed.
No failed app validation is being bypassed and no files have been committed.

The final run checked 264,014 planted contacts at 30 Hz (maximum drift
0.000214647 mm) and 10,589,970 projected foot/shadow/support samples
(zero floor-area escapes). Both avatars also passed the real-sole
near-straight/pivot and live avatar-reload regressions; each measured
4,488 sole vertices. All 120 Workout/Sun images passed the silhouette
edge check, including the previously clipped crunch head. Final private
native capture wrote 30 frames under
`build/practice-motion-review/final-native/`.

Final visual review inspected `contact-sheet.jpg`, `workout-all-poses.jpg`,
`sun-salutation-all-poses.jpg` and all four `*-floor-before-after.jpg`.
Feet and contact shadows sit below the Tai Chi wall and astral railing,
inside the Workout deck and on Sun Salutation's clear ground. Workout
wall/bench props are present; both figures' slippers are flat and plain.
The four refreshed MP4s were opened in VLC and all four floor pictures
in Gwenview; each launch reported running after two seconds.

A fresh native preview was opened from the current working tree through
ignored `backup/figure-motion/open-preview`, which sets `FIGURE_PRACTICES`
to canonical practices and executes the stable
`design/figure-preview/build/app/figure_preview`. Its launch reported
running (unit `harmony-app-direct-open-preview-43c6e9d1`, PID 2348411).
This provides the locally built design preview before publication. The
normal locked package still points at the earlier practices commit, so
pinned-media verification and shared Breeze app integration remain pending.
The app's practice screens have not been changed to claim VRM adoption.

Next integration steps, owned with `codex-breeze-session-2`: pass the
reviewed controller digest/app-bundle gate and complete its tested root
dependency graph; then publish this task's own practices files, repin
root/preview practices with official package commands, verify the pinned
preview and commit/push only this task's Breeze files and changelog hunks.
Preserve all other lanes' current changes. No release was requested.

## Owner follow-up: traditional attire and full naturalness — 2026-11-19

Authenticated coordinator handoff `fd694c7ecaabc6af9a7ced6e96ffa980c7a3`
relays the owner's request to implement everything, test every movement for
naturalness, and use attractive traditional meditation clothing while
keeping the woman's skirt. This supersedes only the earlier constraint to
leave the other garments unchanged. Faces, hair, bodies, identities and
flat neutral slippers remain selected.

Implementation in progress, not yet generated/built or validated:

- Canonical `figure/tools/prepare_attire.py` starts from checksummed CC0
  originals through the established slipper pipeline. It reuses fitted
  garment topology and skin weights, adds real crossed lapel/sash facings,
  plain matte linen colors, removes the man's hood/cord triangles and
  relaxes his trousers. The woman keeps the flared skirt silhouette.
  New `tests/attire_test.py` verifies geometry, identity preservation,
  CC0 metadata, source bytes and removed hood weights. The slipper test
  now delegates intentional garment changes to this explicit attire check.
- The existing skirt visibly rotates upward in forward folds. New
  `figure_cloth.zi` and model integration constrain the hem under gravity,
  outside leg capsules and above the floor, retaining the skinned waist.
  Added fold-through-ninety-degrees/waist/capsule regression source.
  Actual rendered proof and clipping/stretch correction are still required.
- The preview used to wrap directly from the last pose to time zero;
  it now holds the end and restarts only on an explicit Play action.
  Slower breakdown/follow variants are appended without changing old
  picker IDs. A raw-RGBA pipe mode and `full_review.py` retain complete
  videos plus native timeline-defined 30 Hz slow transition clips, with
  exact source/binary/media receipts and safe refusal of unresolved partials.
  `--clothing-audit` adds actual full-timeline garment surface measurements.
- Both current pre-attire VRMs are copied as binary recovery files in
  ignored practices `backup/figure-source/slippers/`. The source originals
  are still in `backup/figure-source/`. Canonical asset bytes have not yet
  been regenerated by the new pipeline; the old running preview is unchanged.

New validation currently cannot start: `build-queue` is missing from PATH,
`/home/wao/.local/bin/` and the canonical Harmony scripts directory.
Attempt `1ebefd984cf9daec56f7c16242072a108e39` failed with exit 127 before
running anything. Report `8f50042cb7b50dfa22d20806eef899951436` was routed
to Harmony and the coordinator/performance lane informed. No queue bypass,
new helper, root pin edit or shared app-output regeneration is being used.
The prepared next command, after the supported queue is restored, is:

```sh
build-queue -- bash backup/figure-motion/verify-attire.sh
```

Then inspect/correct the private clothing frames before starting the full
actual-surface audit and complete/slow playback review. The former `bcf70`
results remain baseline evidence only; changed model/clothing/preview code
needs impacted regressions. Full review must cover both avatars, every
practice, transitions, repeated cadence and final holds, plus actual skirt,
sleeve and body interactions. Existing native astral preview coverage also
needs checking for the moving awareness double, rather than certifying
only its resting physical body. No medical or biomechanical certification
is implied. Root app/Moto integration and final source/asset identity stay
with the existing performance/artifact lane. Everything remains uncommitted.


Further prepared source, still UNVALIDATED while the queue is unavailable:
- Native astral playback now has an independent awareness model/skin/spring
  state, translucent shading and inverse-camera rigid displacement/roll.
  Whole-item framing includes both figures; captures reject a clipped double.
  This needs private rendered rope/roll/return verification and full cue-boundary
  continuity analysis before it can count as movement coverage.
- Complete review capacity is 128 items and rejects overflow in both catalogue
  passes instead of silently dropping entries. Full videos default to 15 Hz;
  transition videos retain 30 Hz native samples at quarter speed without
  manufacturing duplicate frames. Render receipts include the Python tool hash.
- Fresh scoped instructions now describe plain managed desktop_run commands,
  but the active higher-priority task instruction still requires build-queue.
  Requested a supported queue route/instruction correction from Harmony
  (1466849d7fca7f777824e01ce18f9f4319d7). No build or test was bypassed.
