# Tai Chi course animation

A complete Yang-style 24-form course for Inner Breeze, built as data first:
a 3D rig, a pose solver, choreography written as code, a Three.js review
studio, automatic motion checks and headless review renders. Inbe's own
code does not use any of this yet; how the app plays the course is decided
later (see "App playback" below).

## Course

- **Foundations**: posture and breathing, warm-up, standing meditation,
  stances, stepping and hand shapes, each as short drills.
- **Lessons 1–8**: the 24 movements in the usual eight groups. Every
  movement has three versions: a *demo* at normal speed, a *breakdown* that
  plays slower and pauses on every step with its cue, and a *follow-along*
  that does the movement, steps into the mirrored start, does it on the
  other side and returns.
- **Full form**: normal tempo (front view, mirrored, so it moves like your
  reflection) and a slow learning tempo (from behind).

## Run

```sh
cd design/tai-chi
npm install                     # Three.js, pinned in package.json
node tools/serve.mjs            # studio at http://127.0.0.1:8765/
node tools/check.mjs            # motion checks for every item and figure
node tools/render.mjs --item lesson-2/brush-knee/demo --stills 3,6,9 --label
node tools/render.mjs --lessons --full --label   # an MP4 per lesson and the full form
node tools/export.mjs [--bake]  # writes docs/tai-chi-24.json
```

Renders run headless Chromium with SwiftShader and no display; the
inherited display and session variables are removed from its environment.
Output goes to `build/tai-chi/` (ignored).

Studio keys: Space plays, ←/→ step a frame (Shift: a second), `[`/`]`
jump between cued steps, 1–6 switch views. Dragging the view switches to
the free orbit camera.

## How it works

- `src/rig.js`: proportions as fractions of height, per figure.
- `src/pose.js`: the pose description (feet, weight, sinking, waist,
  hands in chest axes, gaze) and mirroring.
- `src/form.js`: the choreography builder. Each key edits a copy of the
  previous pose with side-relative calls (`place`, `pivot`, `load`, `waist`,
  `hand`, `look`…), so the same code runs mirrored. Weight leaves a foot
  before it steps, and a loaded foot waits for the weight to go before it
  turns.
- `src/timeline.js`: monotone curves for the body (no overshoot), smooth
  arcs for the hands, and feet that pivot exactly about the heel or ball or
  lift off to step: planted feet never slide.
- `src/solve.js`: inverse kinematics for legs (knees track the toes) and
  arms, spine twist, gaze that follows a hand, heels that rise when a light
  back foot cannot reach, and a centre of mass placed over the weighted
  contact between the feet.
- `src/checks.js`: foot sliding and floating, knee tracking, knee past the
  toes, knee and wrist limits, arms locked out, hands in the body, feet and
  knees colliding, balance over the feet, speed and jumps, facing at the end
  of each movement, and the full form's duration.
- `form/`: the choreography. `lessonN.js` exports the lesson's movements;
  `boundaries.js` holds the poses where lessons hand over.
- `src/view/`: the stage, camera views, the mannequin and the two
  characters (Sage Bun and Sage Male).

## App playback

Pre-rendered frames do not fit: Sun Salutation's 991 frames per character
are about 10 MB, and the app package budget is 38 MB in total, while the
24-form at the same frame rate would be about 100 MB per character. The
exported keyed poses for the whole course are about 350 KB (21 KB
gzipped); the full form baked to joint rotations at 30 fps is about 1.8 MB
per figure (1.2 MB gzipped). Either needs a player in
the app, which means a reusable 3D or projected-skeleton primitive in Kryon
first. That is a separate decision.
