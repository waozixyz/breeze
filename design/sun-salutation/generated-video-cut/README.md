# Generated sun salutation video, cut up

`source.mp4` is the generated 10 s clip (360 × 640, 24 fps, woman figure,
light background). It is not tracked; put it in this folder, then
`python3 design/sun-salutation/generated-video-cut/cut.py` writes these under
`build/sun-salutation-cut/`:

- `poses/` — one still per held pose, taken at the lowest-motion frame.
- `clips/` — each continuous movement, hold to hold, silent.
- `stand-ins/` — first-half clips played backwards for the return steps.
- `coverage.png` — the app's twelve steps marked have / near / missing.

The video runs through the classic lunge version of the sequence once and
stops in the return forward fold. It never bends the elbows and never
flattens the back.

## Poses (steps from `locales/en.txt`)

| Step | Pose | Video | Frame |
|---|---|---|---|
| 1 | Mountain pose | have (prayer hands) | 13 |
| 2 | Upward salute | have | 41 |
| 3 | Standing forward fold | have | 72 |
| 4 | Half lift | **missing** — low lunge instead | 96 |
| 5 | Plank | have | 127 |
| 6 | Low plank | **missing** — slides plank → up dog with straight arms | — |
| 7 | Upward-facing dog | near — thighs stay on the floor (cobra-like) | 165 |
| 8 | Downward-facing dog | have | 204 |
| 9 | Half lift | **missing** — walks feet in straight to the fold | — |
| 10 | Standing forward fold | have | 226 |
| 11 | Upward salute | stand-in only (reversed clip 02) | — |
| 12 | Mountain pose | stand-in only (reversed clip 01) | — |

## Transitions

| Move | Video |
|---|---|
| 1 → 2 | `clips/01` |
| 2 → 3 | `clips/02` — turns from front view to side view mid-dive (frames 54–63) |
| 3 → 4 | fold → lunge only (`clips/03`) |
| 4 → 5 | lunge → plank only (`clips/04`) |
| 5 → 6 | **missing** |
| 6 → 7 | **missing**; `clips/05` goes plank → up dog directly |
| 7 → 8 | `clips/07` |
| 8 → 9 | **missing**; `clips/08` walks in to the fold |
| 9 → 10 | **missing** |
| 10 → 11 | `stand-ins/10` (reversed); `clips/10` starts rising but the video ends |
| 11 → 12 | `stand-ins/11` (reversed) |

## To generate next

1. Fold → half lift → fold (steps 3–4 and 9–10). If lunges are kept
   instead, steps 4 and 9 need relabeling, and 8 → 9 needs a step forward
   into the lunge rather than walking in.
2. Plank → low plank (elbows bent, body hovering) → upward dog, with thighs
   off the floor.
3. Down dog → half lift.
4. Fold → rise to upward salute → mountain, if the reversed first half looks
   wrong (the front/side turn plays backwards).

Framing notes for any regeneration: in plank, up dog, and down dog the toes
touch the left edge of the 360 px frame (x = 0). The floor line drifts from
y ≈ 611 standing to y ≈ 590 on the floor. The return fold (frame 226) sits
about 50 px further right than the first fold (frame 72), so `clips/08`
followed by `stand-ins/10` jumps. There is no man figure and no dark
background version yet.
