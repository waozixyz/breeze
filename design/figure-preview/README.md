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
deck for the Workout and a moonlit veranda for astral projection), and
Breeze's current flat figure can be shown instead. The panel picks the
practice and item, plays, pauses, scrubs and slows the clock. Drag over the
stage to turn around it; scroll to zoom.

This is its own small project so it can pin the Kryon and practices
commits it needs while Breeze's app still pins older ones. The poses are
Breeze's own: the build adds Breeze's Tai Chi, Sun Salutation and practice
folders as module folders, so nothing is copied.

## Build and run

From this folder, through the build queue:

```sh
build-queue -- ziran build --project --target=c --exe \
    --module-path ../../src/practices/tai_chi \
    --module-path ../../src/practices/sun_salutation \
    --module-path ../../apps/practice \
    --entry figure_preview:main -o build/app figure_preview.zi
./build/app/figure_preview
```

The preview asks `ziran pkg path practices --locked` beside this manifest
for its backdrops. `FIGURE_PRACTICES=/path/to/practices` uses a working
checkout instead (add `--module-path ../../../../modules/practices/figure`
to the build to compile that checkout's figure code too).

Without a window:

- `--capture DIR` writes review frames to `DIR`: the woman, the man and
  Breeze's current flat figure for Tai Chi's deepest stance, Sun
  Salutation's fold, lunge, plank, cobra and downward dog, the Workout's
  lowest squat and lunge, and an astral moment.
- `--audit` plays every item of every practice thirty times a second and
  lists each awkward moment with its time: a planted heel or ball sliding,
  a foot through the floor, a joint changing speed too suddenly or moving
  too fast, a knee bent backwards, a hand through the body. It exits
  non-zero when it finds any.
- `--shot DIR PRACTICE ITEM SECONDS... [man]` writes chosen moments, and
  `--video DIR PRACTICE ITEM FROM TO [man]` thirty frames a second of a
  stretch, hair swinging; `--trace PRACTICE ITEM FROM TO` prints the right
  arm's joints and hand frame 120 times a second.

## Known limits

- Practices commits without `astral_projection/sessions/` play the astral
  techniques with steps evenly 20 seconds apart, and the panel says so.
