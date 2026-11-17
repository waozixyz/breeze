# Open practice figure work — 2026-11-17

The owner wants one perfected character used everywhere: Tai Chi, Sun
Salutation, Workout and astral projection, native on Ziran and Kryon
without raylib. The character is the practices package's `figure/` (pinned
practices b38054fc: female MakeHuman CC0 surface, dual-quaternion rig,
watercolor painter, floor shadow, Ziran tests). The live tuning tool is
`design/figure-preview/` (see its README). The three.js studies in
`design/astral-projection/three/` are look references only.

- Kryon desktop presentation: at Kryon 199b51c9 the desktop loop keeps
  drawing requested frames, but stops showing them once there is no input
  (a 24-line repro was sent to the coordinator for the Kryon lane). The
  preview's hands-off playback freezes until the pointer moves. Repin the
  preview once Kryon is fixed. The same Kryon compares images by texture id
  only, so `BitmapImageUpdate` on one texture never repaints; the preview
  alternates two textures.
- Owner review of the live preview and of
  `build/practice-compare/side-by-side/` (current flat figure beside the new
  character, same moments and cameras), then tune from that feedback.
- Character work still open:
  - The top and trousers hug the body; the flat figure's loose tunic needs
    cloth geometry (a skirted tunic shell over the hips).
  - Relaxed and open hands still read as claws in some Tai Chi palms.
  - The face is plain at practice sizes.
  - Each practice's look colours come from its flat look; settle one
    palette.
- Astral session timings: practices' `astral_projection/sessions/*.json`
  are another task's uncommitted files. Until they are pushed, a pinned
  preview plays the six techniques with steps evenly 20 seconds apart.
- Breeze adoption, after the shared Kryon repin (lane -7, plot, entity,
  game2d, css and apps on one Kryon; Breeze audio on Ziran std audio):
  - Make Breeze's `practices` dependency a package pinned at or after
    b38054fc.
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
  (watercolor finish and shadow on the CPU). Measure on a real phone GPU;
  shell GL here is llvmpipe.
- Narration: the initial audit found all 88 cue texts in each of ten
  locales but only 407/880 female clips (cs 6, de 86, en 86, es 78, fr 37,
  ja 5, ko 6, pt 88, ru 10, zh 5). Complete and listen through the owning
  narration task; legacy cues do not fill the new exercise keys.
- Refresh the three.js caption snapshot if the practices task changes
  session cues or text. Keep `build/astral-compare/before/` as the baseline.
