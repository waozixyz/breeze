# Sun salutation animation review

Four complete, silent illustrated videos are saved in
`assets/practices/sunsalutation/animations/`. The `light/` and `dark/` folders
each contain `sun-salutation-man.mp4` and `sun-salutation-woman.mp4`.
Only the four playable videos belong in that review folder.

Each video is 1920 × 1080, 30 fps, H.264 with a broadly compatible YUV 4:2:0
pixel format. One complete round lasts 96 seconds: eight seconds per step,
with five seconds in the pose and three seconds to move into the next pose.
The final mountain pose joins the first pose for looping. Held poses include
subtle breathing movement. MP4 chapter metadata names the twelve steps;
there are no captions, controls, logos, sound, or baked-in timers.

These are original, locally rendered articulated illustrations. They are
continuous video animations, not playback of the existing pose sheets and
not AI-generated footage. Both themes share the same pose timeline and fixed
camera. The woman wears a sports top and leggings; the man wears shorts.

## Existing implementation

The current app uses the files in `src/practices/sun_salutation/`:

- `sun_salutation_rules.zi` defines 12 steps, two figures, 3–12 seconds per
  step, and 2–12 repetitions. Defaults are three repetitions, starting at
  eight seconds per step and ending at five. The timer advances on 60 ticks
  per second, and each repetition uses one duration for all twelve steps.
- `sun_salutation_assets.zi` selects two 424 × 288 pose sheets. Each contains
  twelve 106 × 96 pose frames. Only the man has transition artwork, and only
  for mountain → upward salute and upward salute → forward fold. Each
  transition contains eight frames. The woman and the other ten transitions
  use static pose frames.
- `sun_salutation_session.zi` draws a cropped `Image` from those sheets,
  along with a localized step title, timer, and previous/pause/next controls.
- The English labels name half lifts at steps 4 and 9, while the existing
  artwork depicts lunges. The male low-plank drawing also drops the knees.
  The new videos follow the twelve named poses, with half lifts and low plank.

The generated videos are review assets. The app's current image-based player
has not been changed to play them. Native/web/Android playback and seeking
must be implemented before these can replace the current practice visuals.
MP4 has an opaque background; use the matching light or dark file. Changing
the practice tempo would require matching video speed or seeking within the
eight-second chapter boundaries. Interruption/resume and manual step changes
must continue to follow the practice state.

## Reproduction

The full source is `scripts/render-sun-salutation.py`. It uses Python 3,
pycairo, and FFmpeg with libx264. It renders offscreen without accessing X11
or Wayland. No external image/video generation service was used.

```sh
python3 scripts/render-sun-salutation.py --output output/sun-salutation
```

The default export is 1080p at 30 fps. Use `--theme light` or `--theme dark`
to render one theme and `--figure man` or `--figure woman` for one figure.
For a disposable inspection frame:

```sh
python3 scripts/render-sun-salutation.py --still 58 --theme dark \
  --figure woman --output output/sun-salutation-inspection
```

Existing outputs are never overwritten. Choose a new output directory when
rendering another revision. The final videos should stay in a folder apart
from inspection frames and encoder logs.

## Export checks

All four exports passed FFprobe checks for resolution, frame rate, codec,
pixel format, duration, 2,880 video frames, twelve chapter boundaries, and
absence of audio. Each video decoded completely with FFmpeg without errors.
Rendered frames at 0 and 96 seconds match, and sampled intermediate frames
in the arm-raise and step-back/step-forward transitions are distinct. The
review folder contains exactly four MP4 files across the two theme folders.
