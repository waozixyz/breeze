# Sun salutation with the painted girl

`scripts/render-sun-salutation-girl.py` animates the painted girl through
Inbe's twelve-step sun salutation:

```sh
python3 scripts/render-sun-salutation-girl.py            # video
python3 scripts/render-sun-salutation-girl.py --still 21 # one frame
```

The video goes to `build/sun-salutation-girl/video/light/sun-salutation.mp4`
(1536 × 1024, 30 fps, 69 s, one chapter per step) and stills to
`build/sun-salutation-girl/light/`. It needs Python 3 with pycairo, NumPy and
Pillow, and FFmpeg with libx264. Rendering is offscreen and deterministic: the
same inputs give byte-identical video, and a still matches the same frame of
the video, hair included.

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
along the bent bones. Head, torso, hips, hands and feet move rigidly, and the
hand and foot drawings switch at the moment of contact. The long lock is a
Verlet strand stepped once per video frame from rest at 0 s.

Back to front: far leg and arm (slightly darker), long hair, back hair, hips,
near leg, torso, face and neck, front hair, near arm. The shirt is always
drawn over the leggings; when her hips are above her shoulders it slides
toward her chest and shows the waistband.

## Transitions

- Upward salute to forward fold, and back up, is a swan dive: straight arms
  stay in line with the spine, then sweep to the floor.
- Half lift to plank goes through a low lunge: hands planted, the far foot
  steps back first with the front knee over the ankle, then the near foot.
  Down dog to half lift steps forward the same way.
- A foot in the air points its toes along the shin; each foot keeps its own
  drawing while the feet are apart.
