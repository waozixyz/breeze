# Selected cartoon-pixel animation draft

The user selected `09-hand-drawn-pixel-hybrid.png` from the second style
comparison. These previews follow that character through Inbe's full
12-pose sun salutation sequence. The character keeps the brown bun,
cream shirt, sage trousers, bare feet, and warm cartoon-pixel drawing.

The deliverables are separate, silent MP4 videos:

- `design/sun-salutation/hybrid-animation/light/sun-salutation.mp4`
- `design/sun-salutation/hybrid-animation/dark/sun-salutation.mp4`

Both are 1536×1024 H.264 videos at 30 output frames per second, lasting
52.5 seconds. Each pose holds for three seconds and each movement takes
1.5 seconds. The files contain twelve named pose chapters.

## Drawing and movement

Built-in image generation created eight sets of six successive animation
drawings from the selected reference, plus light and dark empty stages.
The return fold, upward salute, and prayer movements reuse those drawings
in reverse. The video displays the original drawn cels with stepped timing;
30 fps is the encoded playback rate, not thirty unique drawings per second.

The exact prompts and sequence are in
`docs/sun-salutation-hybrid-animation.json`. Generated source drawings
are kept separately in `design/sun-salutation/hybrid-animation-source/`,
so the video preview folder contains only the two theme folders and videos.

FFmpeg isolates each cel using its connected alpha silhouette, preserves
the pixel edges with nearest-neighbor scaling, and places it on the fixed
stage. Ground contacts, standing ankles, and planted palms are aligned
to shared stage coordinates. A trial of optical-flow interpolation produced
ghosted arms and was excluded from the deliverables.

## Rebuild

Requires Python with Pillow, NumPy, and SciPy, plus FFmpeg:

```sh
python3 scripts/assemble-sun-salutation-hybrid.py
```

Temporary selection mattes, assembled frames, and logs live under ignored
`build/sun-salutation-hybrid/`. The script does not open a display.

This is a first animation draft for reviewing the selected art direction.
Drawing proportions and limb geometry vary between generated cels, and
motion is visibly stepped. It is not a finished smooth animation or an
in-app replacement: Inbe's current practice renderer still uses its existing
image assets, as described in `docs/sun-salutation-animation.md`.
