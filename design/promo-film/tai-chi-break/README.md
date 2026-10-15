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
- `narration.json`: the narrator's lines, their start times and chosen takes,
  spoken in the male Tai Chi voice (Gemini TTS `Algieba`) by
  `../narrate.py --config narration.json --out build/promo-video/tai-chi-break/voice`.
  The chosen takes, levelled to -16 LUFS, are `audio/voice/KEY.flac`.
  `finish.py` keeps the score low and steady under each stretch of talking
  and lets it rise only in the real pauses, without any pumping.

## Portrait cut

`?aspect=portrait` (`tools/render.mjs --aspect portrait`) renders the same
53 s at 1080x1920 for TikTok, YouTube Shorts and Facebook Reels
(`src/aspect.js`). The camera keeps its vertical field of view and pans
across the plates by turning around its own centre, so the painting
re-projects without parallax tears. The terminal stacks each lane (name,
task, bar) in the middle of the monitor, the only part a portrait frame
sees; the push-in stops while the lanes still fit. Lumi rises up the frame
on the ledge and the end card, the monk stands a little right of centre,
and the two teachers stand closer, the teacher a step behind. Titles keep
out of the top 220 px, the bottom 420 px and the buttons on the right.
`finish.py --vertical` lays the same narration and mix under it.

## Run

```sh
node ../three/tools/serve.mjs     # preview at /design/promo-film/tai-chi-break/ (?t=SECONDS)
node design/promo-film/tai-chi-break/tools/render.mjs --stills 3,21,44 --out build/promo-video/tai-chi-break/stills/x.mp4
node design/promo-film/tai-chi-break/tools/render.mjs        # build/promo-video/tai-chi-break/film.mp4
python3 design/promo-film/tai-chi-break/finish.py            # + score → inner-breeze-tai-chi-break.mp4, poster.jpg
node design/promo-film/tai-chi-break/tools/render.mjs --aspect portrait    # film-vertical.mp4
python3 design/promo-film/tai-chi-break/finish.py --vertical # → inner-breeze-tai-chi-break-vertical.mp4
```

Run the render commands from the Inbe root. Renders use headless Chromium
on the GPU with the display and session variables removed.
