# Figure preview

A native window for judging and tuning the shared practice figure. It plays
each practice's own choreography on the character from the practices
package (`figure/`): Tai Chi forms, two rounds of Sun Salutation, the
Workout's twelve exercises and the six astral techniques. It runs on Ziran
and Kryon's SDL/Cairo desktop host, without raylib.

The panel picks the practice and item, plays, pauses, scrubs and slows the
clock. It switches the watercolor finish off to show the bare surface, and
can show Breeze's current flat figure for the same moment. It also tunes
edge pooling, pencil contour and paper grain. Drag over her to turn around
her; scroll to zoom.

This is its own small project so it can pin the Kryon that has
`scene_skin` and `watercolor`, and the practices commit that has the figure,
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
(`NAME.png`), her bare surface (`NAME-bare.png`) and Breeze's current flat
figure for the same moment and camera (`NAME-current.png`). The frames cover
Tai Chi's deepest stance, Sun Salutation's fold, lunge, plank, cobra and
downward dog, the Workout's lowest squat and lunge, and the astral exits.

## Known limits

- At the pinned Kryon, the desktop loop stops showing frames that arrive
  with no input, so hands-off playback freezes until the pointer moves over
  the window. The bug is reported to Kryon with a minimal repro.
- Practices commits without `astral_projection/sessions/` play the astral
  techniques with steps evenly 20 seconds apart, and the panel says so.
