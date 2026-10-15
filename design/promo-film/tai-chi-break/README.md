# A Tai Chi break — Three.js

A 53-second 1920x1080 film for social posts: while your AI agents build,
find your calm with Tai Chi in Inner Breeze. Everything moves in Three.js
from timeline time and reuses the trailer's world in `../three/`.

1. 0–13 s: a late-night desk. Six agents work in a terminal on the monitor
   (`src/terminal.js`, drawn into a canvas every frame); the camera eases in
   and passes through the screen's light.
2. 13–18.6 s: above the clouds at dawn, Lumi flies up.
3. 18.6–28.6 s: the monk's Wave Hands Like Clouds in the monastery courtyard.
4. 28.6–38.9 s: the monk and the Tibetan teacher's Part the Wild Horse's
   Mane, with the course's facts.
5. 38.9–46 s: back out of the light, the last agents finish.
6. 46–53 s: the end card under the night sky.

The cuts follow the score: its swells peak at 13.1 and 38.9 s. Titles are
drawn into a canvas (`src/overlay.js`) and laid over the graded picture.

## Pieces

- `plates/studio.jpg`: the desk, painted by `plates.py` (Codex image
  generation from `plates.json`, with the trailer's desk as the style
  reference; take `studio-b`, cropped to 16:9). `plates/studio-depth.png`
  comes from `../three/depth.py`'s Depth Anything model. The other plates
  are the trailer's (`../three/plates/`).
- `src/puppets.js`: the trailer's painted Tai Chi teachers, with `FlatView`
  imported from `painted/layout.js`, where it now lives.
- `audio/score.mp3`: Lyria take 1 of `score.py` (`audio/score-prompt.txt`).

## Run

```sh
node ../three/tools/serve.mjs     # preview at /design/promo-film/tai-chi-break/ (?t=SECONDS)
node design/promo-film/tai-chi-break/tools/render.mjs --stills 3,21,44 --out build/promo-video/tai-chi-break/stills/x.mp4
node design/promo-film/tai-chi-break/tools/render.mjs        # build/promo-video/tai-chi-break/film.mp4
python3 design/promo-film/tai-chi-break/finish.py            # + score → inner-breeze-tai-chi-break.mp4, poster.jpg
```

Run the render commands from the Inbe root. Renders use headless Chromium
on the GPU with the display and session variables removed.
