# Sun salutation with the painted girl

`scripts/render-sun-salutation-girl.py` animates the painted girl through
Inbe's twelve-step sun salutation:

```sh
python3 scripts/render-sun-salutation-girl.py                # video
python3 scripts/render-sun-salutation-girl.py --still 21     # one frame
python3 scripts/render-sun-salutation-girl.py --theme clear  # transparent video
python3 scripts/render-sun-salutation-girl.py --sprites      # the app's frames
```

The video goes to `build/sun-salutation-girl/video/light/sun-salutation.mp4`
(1536 × 1024, 30 fps, 69 s, one chapter per step) and stills to
`build/sun-salutation-girl/light/`. It needs Python 3 with pycairo, NumPy and
Pillow, and FFmpeg with libx264. Rendering is offscreen and deterministic: the
same inputs give byte-identical video, and a still matches the same frame of
the video, hair included.

The same renderer is also written in Ziran, `scripts/sun_salutation_girl.zi`.
`scripts/render-sun-salutation-girl-zi.sh` builds it to Python with Inbe's
pinned toolchain (`zi2py`, with `LDLIBS=-lcairo` so its C calls reach
Cairo) and runs it; set `STILL=seconds` for one frame and `THEME=dark` for
the dark stage. It reads the same rig and parts and writes under
`build/sun-salutation-girl-zi/`. It measures part images at a quarter of their
size and resamples them with Cairo rather than Pillow, so its frames differ
from the Python ones by a fraction of a pixel along edges.

## Inputs

- `docs/sun-salutation-girl.json` holds everything that places her: the
  poses and their order, hold and transition times, bone lengths, the
  camera, the stepping stops through the low lunge, the swan-dive arms, the
  hair strand, the part key points, and the themes. Change poses here.
- `design/sun-salutation/girl-parts/` holds the painted parts, made with
  Codex's built-in image generation from the reference girl; `prompts.json`
  keeps every prompt and `design/sun-salutation/girl-source/` the briefs.
  The head is three layers on one canvas (back hair, face and neck, front
  hair) so the long hair falls behind a fully painted neck.

## How a frame is drawn

The timeline interpolates the rig poses and moves the hip so hands and feet
can reach. Arms and legs are two-bone chains; their paintings are warped
along the bent bones. Each leg painting carries her seat: above the hip joint
it follows the pelvis and bends round into the thigh, so the seat stays
smooth even when the hip folds all the way. The top is warped too: its hem
flares out over the leggings, more at the back while she is upside down.
The seat is a little fuller at the back, widening smoothly around the hip
while its front and the lower leg keep their shape.
Head and hands move rigidly; the foot drawings rotate and adjust their shape
while rolling between contacts. The long lock is a Verlet strand stepped once per
video frame from rest at 0 s.

Back to front: far leg and arm (slightly darker), long hair, back hair, near
leg, face and neck, top, front hair, near arm. The collar covers the base of
the neck as the head turns. The top is always over the leggings: above its
hem, anything of the leggings behind her back is clipped away.

## Transparent output

The `clear` theme paints no background, so every pixel keeps its real
coverage and the white top stays intact; nothing is keyed out afterwards.
`--theme clear` writes `build/sun-salutation-girl/video/clear/sun-salutation.webm`
(VP9 with an alpha channel) and `--still` writes PNGs with alpha.

## The app's frames

`--sprites` renders what the Sun Salutation practice shows: for every step
the move into its pose at 30 frames per second, then half a second of the hold
while the hair settles; the last frame is the held pose, and the first step
is only its held pose. Frames are rendered at 0.55 of the design size on the
`clear` theme, trimmed to what they show and saved as 256-colour PNGs in
`assets/practices/sunsalutation/girl/`. The generated
`src/practices/sun_salutation/sun_salutation_frames.zi` places every frame on
one shared stage. Settings are under `sprites` in the rig.

The app opens each step with the move, over at most 3 s and at most half the
step, showing one solid frame at a time, then holds the pose. Hands and feet
also switch contact drawings without a fade. Frames are
separate images so that only the few most recent ones stay loaded.

## Transitions

- Upward salute to forward fold, and back up, is a swan dive: straight arms
  stay in line with the spine, then sweep to the floor.
- Half lift to plank goes through a low lunge: hands planted, the far foot
  steps back first with the front knee over the ankle, then the near foot.
  Down dog to half lift steps forward the same way.
- Upward dog to downward dog rolls the toes under and lifts the ankle over
  them. The instep and flat-foot drawings share the same ankle, toe and heel
  positions at their solid handoff, using the `toe` and `heel` key points in
  the rig's foot parts. The two renderers use the same contact transforms.
- A foot in the air points its toes along the shin; each foot keeps its own
  drawing while the feet are apart.
