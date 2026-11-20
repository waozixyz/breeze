# Figure preview

A native window for the practices' stage. It plays each practice's own
choreography (Tai Chi forms, two rounds of Sun Salutation, the Workout's
twelve exercises and the six astral techniques) on Ziran and Kryon's
SDL/Cairo desktop host, without raylib.

The figure is pixiv's CC0 VRoid woman or man from practices'
`shared/figure/` (the panel's Woman/Man switch), posed by practices'
`figure_model` from the practice's own solver, cel-shaded on her own
textures, with her hair and clothes swinging on the model's spring bones
and her eyes blinking as the clock plays. Each practice has its backdrop (a
lake terrace for Tai Chi, a sunrise hill for Sun Salutation, a woodland
deck for the Workout and a moonlit veranda for astral projection). The
Workout wall and bench use the app choreography's exact support dimensions,
with depth shared by the avatar. Both figures wear linen wraps and flat cloth
slippers. The woman wears a skirt with a waist seam that follows the pose and
a hem that clears the legs and floor. The man wears relaxed trousers.
The camera fits the whole figure, with a lower view for standing poses and a
closer overhead angle for low poses. The floor stays in view without a foot
shadow. Certain astral cues show a translucent second figure that separates
from and returns to the resting figure in a steady shot. The panel picks the
practice and item, plays, pauses, scrubs and slows the clock. Drag over the
stage to turn around it.
Scroll to zoom. The panel can also show Breeze's flat figure.

The preview locks its own Kryon and Practices dependencies. The build
uses Breeze's Tai Chi, Sun Salutation and practice modules directly.

## Build and run

Run from this folder in a managed Harmony command.

```sh
../../build/packages/ziran/build/bin/ziran build --project --locked --target=c --exe --release \
    --module-path ../../src/practices/tai_chi \
    --module-path ../../src/practices/sun_salutation \
    --module-path ../../apps/practice \
    --entry figure_preview:main -o build/app figure_preview.zi
PATH="$(cd ../../build/packages/ziran/build/bin && pwd):$PATH" ./build/app/figure_preview
```

The preview reads models and course data from `ziran pkg path practices
--locked`. Put the compiler on `PATH` for runtime package lookup. To develop
against a local Practices checkout, set `practices` under `[overrides]` in
`ziran.local.toml` for compilation and set `FIGURE_PRACTICES=/path/to/practices`
when running the preview. The window logs its renderer and frame timing every
30 animation frames, including median and 95th-percentile frame intervals
and how many frames the window was visible, focused or minimized.

For captures without a window, create the output directory before running
`--capture`, `--shot` or `--video`.

- `--capture DIR` writes review frames to `DIR`: the woman, the man and
  Breeze's current flat figure for Tai Chi's deepest stance, Sun
  Salutation's fold, lunge, plank, cobra and downward dog, the Workout's
  lowest squat and lunge, and an astral moment.
- `--audit` plays every item of every practice thirty times a second and
  lists each awkward moment with its time: a planted heel or ball sliding (0.1 mm limit; actual floor contact),
  a foot through the floor, a joint changing speed too suddenly or moving
  too fast, a knee bent backwards, a hand through the body or an abrupt
  camera change. It exits nonzero when it finds any.
- `--shot DIR PRACTICE ITEM SECONDS... [man]` writes chosen moments, and
  `--video DIR PRACTICE ITEM FROM TO [man]` thirty frames a second of a
  stretch, hair swinging; `--trace PRACTICE ITEM FROM TO` prints the right
  arm's joints and hand frame 120 times a second.

## Known limits

- Practices commits without `astral_projection/sessions/` play the astral
  techniques with steps evenly 20 seconds apart, and the panel says so.

## Motion review

`review.py` writes resumable before/after videos for the four practices and a
contact sheet with both figures under `build/practice-motion-review/`. It
also renders all twelve Workout exercises at three moments each and every
Sun Salutation step in both rounds, with both figures, into
`workout-all-poses.jpg` and `sun-salutation-all-poses.jpg`. Its
`--review-points` catalogue comes from the preview's own timing rules. It
uses the preserved `build/before/figure_preview` and the current stable
`build/app/figure_preview`; binary and course hashes identify each render.
From the Breeze root:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u GDK_DISPLAY -u SESSION_MANAGER HARMONY_DESKTOP_RECOVERY=0 \
    xvfb-run -a python3 design/figure-preview/review.py
```

Support contacts are checked separately from a foot peeling or landing.
The audit prints the number of contact samples and the largest drift, so a
pass cannot hide an untested support phase.

Ground registration is stored beside each practices backdrop as same-name
JSON. `--audit` checks the full motion and verifies foot and support bounds
against that painted floor at three aspect ratios. `--sole-audit` additionally
loads both models and measures the actual skinned soles at one-second
intervals across every item (identical lower-body states share a result),
including the step-up bench, with a 1 mm floor/flatness/heel-ball limit. Both commands exit nonzero on
failure. `review.py` also writes four `*-floor-before-after.jpg` pictures
against the preserved pre-floor frames.

## Complete movement and clothing review

The preview holds a completed demonstration's final pose; Play explicitly
restarts it. It includes the slower Tai Chi breakdown/follow variants as
well as the demos and full forms. `--review-items` exports exact durations;
`--review-spans` exports actual keyed transitions/cue changes for slow
playback. `--clothing-audit` samples the named garment surfaces each second
for both figures throughout the programme. It checks finite geometry, skirt
floor clearance and stretching along mesh edges.

`full_review.py` streams full timelines into owned ffmpeg processes, without
keeping every frame as a PNG. Both figures get a video of every item. The
default is four rendered frames per second. `--transitions` also renders
timeline-defined transitions at 30 Hz and quarter-speed playback. Set
`--practice` and `--item` to render one item. Receipts identify the exact
source, binary and media and validate the encoded frame count. A failed
partial render is preserved for inspection before a retry.

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u GDK_DISPLAY -u SESSION_MANAGER HARMONY_DESKTOP_RECOVERY=0 \
    xvfb-run -a python3 design/figure-preview/full_review.py --transitions
```

For an individual segment, `--stream PRACTICE ITEM FROM TO FPS WIDTH HEIGHT FD
[man]` writes raw RGBA to an already-open file descriptor for ffmpeg.
