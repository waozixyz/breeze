# Figure preview

A native window for judging and tuning the shared practice figure. It plays
each practice's own choreography on the character from the practices
package (`figure/`): Tai Chi forms, two rounds of Sun Salutation, the
Workout's twelve exercises and the six astral techniques. It runs on Ziran
and Kryon's SDL/Cairo desktop host, without raylib.

Each practice plays on its own backdrop in Inner Breeze's illustration
style: a lake terrace for Tai Chi, a sunrise hill for Sun Salutation, a
woodland deck for the Workout and a moonlit veranda for astral projection.
The panel picks the practice and item, plays, pauses, scrubs and slows the
clock. It switches the finish off to show the bare surface on paper, and
can show Breeze's current flat figure for the same moment. It also tunes the
seam softening, the dried edges, the line, the texture and the colour
strength. Drag over her to turn around her; scroll to zoom.

This is its own small project so it can pin the Kryon that has
`scene_skin` and portable shaders, and the practices commit that has the figure,
while Breeze's app still pins older ones. The poses are Breeze's own: the
build adds Breeze's Tai Chi, Sun Salutation and practice folders as module
folders, so nothing is copied.

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
for its media. `FIGURE_PRACTICES=/path/to/practices` uses a working
checkout instead, for trying figure changes before they are pushed (add
`--module-path ../../../../modules/practices/figure` to the build to compile
that checkout's figure code too).

`./build/app/figure_preview --capture DIR` writes review frames to `DIR` and
exits without a window. Each frame is written three ways: the painted figure
on the practice's backdrop (`NAME.png`), her bare surface on paper
(`NAME-bare.png`) and Breeze's current flat figure for the same moment and
camera (`NAME-current.png`). The frames cover
Tai Chi's deepest stance, Sun Salutation's fold, lunge, plank, cobra and
downward dog, the Workout's lowest squat and lunge, and the astral exits.

## Profiling

The window prints a timing report to its standard output (the launcher's
journal) every 120 painted frames and when it closes: median and 95th
percentile milliseconds over the last 240 frames
for the whole frame and for each step (the practice's pose solve, the
figure's pose, skinning, cloth, render and readback, finish and ground
shadow, the backdrop, compositing, the astral double, the texture upload
and the panel's controls). `./build/app/figure_preview --profile PRACTICE`
(`tai-chi`, `sun-salutation`, `workout` or `astral`) paints 240 frames
without a window and prints the same report; add `still` to hold one pose.

## Known limits

- Practices commits without `astral_projection/sessions/` play the astral
  techniques with steps evenly 20 seconds apart, and the panel says so.
