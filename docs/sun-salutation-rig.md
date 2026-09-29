# Sun salutation with a fixed character rig

This preview addresses the changing body proportions in the generated-cel
animation. It reuses the same painted character parts throughout the full
sequence, with fixed bone lengths and smooth movement between poses.

The separate light and dark videos are:

- `design/sun-salutation/rigged-animation/light/sun-salutation.mp4`
- `design/sun-salutation/rigged-animation/dark/sun-salutation.mp4`

Each silent H.264 MP4 lasts 69 seconds at 1536×1024 and 30 fps. All 2,070
frames are rendered from the rig; the output rate does not duplicate a small
set of drawings. The twelve pose chapters follow Inbe's existing sequence.
Each pose holds for three seconds, with three-second transitions. The floor
transitions include stepping back and stepping forward.

The selected reference remains `09-hand-drawn-pixel-hybrid.png`. Built-in
`image_gen` created reusable painted parts from that reference, then two
continuous limbs and a torso without an attached sleeve. Exact prompts,
sources, attachment positions, and scales are in `sun-salutation-rig.json`.
The generated artwork is kept in `hybrid-animation-source/rig-parts/` and
`hybrid-animation-source/rig-parts-v1.png`. Existing painted stages are reused.

Two-bone inverse kinematics keeps each arm segment at 64 rig units and each
leg segment at 96 units. Head scale and the 110-unit torso stay fixed. Whole
painted arm and leg meshes bend over those bones, avoiding the visible seams
from separately rotating upper and lower pieces. Quintic easing makes each
transition start and end gently. Reach constraints keep the wrists and ankles
reachable without stretching the bones. Cairo renders offscreen directly to
FFmpeg; no app display or live desktop is used by the renderer.

Validation samples all 2,070 frames. Maximum bone-length error is below
`1e-8` rig units, and all wrist and ankle targets are reachable within that
tolerance. The head silhouette was also checked across the sequence to keep
it above the mat contact plane. Both encoded videos are checked for their
duration, frame count, chapters, format, and complete decoding.

This remains an art-direction preview. Cloth stays stiff when the torso
rotates, the rigid profile head does not turn in perspective, and hands and
feet blend between alternate contact drawings. The rig removes generated
proportion drift, but these poses and clothing need further artistic work
before this should become an in-app practice animation.

To rebuild, install Python bindings for Cairo, Pillow, NumPy, and SciPy, and
FFmpeg. Run from the real Inbe checkout:

```sh
python3 scripts/render-sun-salutation-rig.py --check
python3 scripts/render-sun-salutation-rig.py --output design/sun-salutation/rigged-animation-new
```

The renderer refuses to overwrite existing videos. `--still 42 --theme light`
renders a review frame instead. Scratch mattes, measurements, and encoding
logs live under ignored `build/sun-salutation-rig/`.
