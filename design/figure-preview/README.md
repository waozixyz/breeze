# Figure preview

A native window for the practices' stage. It plays each practice's own
choreography (Tai Chi forms, two rounds of Sun Salutation, the Workout's
twelve exercises and the six astral techniques) on Ziran and Kryon's
SDL/Cairo desktop host, without raylib.

The figure model is pending: the MakeHuman-based figures were removed on
2026-11-18, and the owner will pick a new one
(`../../plans/2026-11-18-figure-model-candidates.md`). Until then the stage
shows each practice's backdrop (a lake terrace for Tai Chi, a sunrise hill
for Sun Salutation, a woodland deck for the Workout and a moonlit veranda
for astral projection) with a "model pending" note, and Breeze's current
flat figure on it when asked. The panel picks the practice and item, plays,
pauses, scrubs and slows the clock. Drag over the stage to turn around it;
scroll to zoom.

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

`./build/app/figure_preview --capture DIR` writes review frames to `DIR` and
exits without a window: the empty stage (`NAME.png`) and Breeze's current
flat figure on it (`NAME-current.png`) for Tai Chi's deepest stance, Sun
Salutation's fold, lunge, plank, cobra and downward dog, the Workout's
lowest squat and lunge, and an astral moment.

## Known limits

- Practices commits without `astral_projection/sessions/` play the astral
  techniques with steps evenly 20 seconds apart, and the panel says so.
