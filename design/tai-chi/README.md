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

Drills and breakdowns teach step by step: each step's words show from the
start of its motion until the next words, and a step too short to read its
words (`readingTime` in `src/course.js`: 0.8 s plus 14 characters a second,
at least 2 s) is slowed until they can be read. Items at the form's tempo
(demos, whole lessons, follow-alongs, the full form) keep their tempo; the
app names the movement for them instead of the steps' words.

## Run

```sh
cd design/tai-chi
npm install                     # Three.js, pinned in package.json
node tools/serve.mjs            # studio at http://127.0.0.1:8771/ (opens on the full form)
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

## Painted characters

The studio opens on the full form with the painted Tibetan monk: a 2D
cut-out puppet in the hand-painted style of Sun Salutation, drawn over the
same solved body as the 3D figures, so every lesson, version and the full
form play with it. The second painted character is a Tibetan woman (braids
wound round her head, teal wrap vest, pangden-striped sash). Pick them in the
figure buttons (`?figure=monk`, `?figure=tibetanWoman`); the 3D figures are
still there.

- `characters/<id>/source/` keeps the generated turnaround and part sheets
  with their prompts (Codex built-in image generation, the turnaround and
  the approved Sun Salutation characters as references).
- `tools/cut-parts.py characters/<id>` cuts the sheets listed in
  `sheets.json` into transparent `parts/`, recovering edges from the white
  background and fading the cut edges that another part covers (hand into
  forearm, ankle into trouser cuff).
- `characters/<id>/character.json` names each part's points as fractions of
  its image: the neck and hips of the five torso views, the armholes, the
  neck of the five head views, wrist and fingertips of the hands, heel and
  toe of the shoes.
- `src/painted/figure.js` projects the solved joints flat along the view
  and places the paintings as textured meshes in an orthographic scene:
  arms and legs bend along their projected bones, the torso follows the
  projected spine, and the head, torso, hands and shoes switch between
  front, three-quarter, side, three-quarter back and back drawings as they
  turn (mirrored for the other side, with a little hysteresis so a part on
  a boundary does not flicker). Hands pick palm, back, edge, fist or hook
  drawings from the hand's shape and which way the palm faces. Back arms,
  legs, head, torso and front arms are drawn in that order.

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
- `src/view/`: the stage, camera views, the mannequin and the two 3D
  characters (Sage Bun and Sage Male); `src/painted/` the painted 2D
  figures (see above).

## App playback

Inner Breeze plays the course itself as the Tai Chi practice. Frames would
not fit (Sun Salutation's 991 frames per character are about 10 MB; the
24-form would be about 100 MB per character), so the app samples and solves
the key poses the way the studio does:

- `node tools/export-app.mjs` writes `assets/practices/taichi/course.bin`
  (key poses, rigs, part anchors and the course outline; its layout is
  described at the top of the tool), the two painted characters at 0.65
  scale with 256-colour palettes, the floor shadow, the course words as
  locale entries in `text/en.txt`, and `tests/fixtures/tai-chi-reference.json`.
- `src/practices/tai_chi/` in Inbe ports `timeline.js`, `solve.js`,
  `painted/layout.js` and the studio's camera to Ziran and draws each
  painted piece warped over its grid with Kryon's `ImageProps.mesh`.
- `sh tests/tai_chi_zi_test.sh` in Inbe checks the port against the
  reference: channels, joints, drawing choices, draw order and piece
  vertices for both characters must match.

After changing choreography, the solver or the painted layout, run the
export again, commit the new `course.bin` and reference, and translate any
new words in `text/<lang>.txt` (the export prints how many there are); the
course words live in Inbe's `locales/*.txt` as `tai_chi_text_*` entries.
