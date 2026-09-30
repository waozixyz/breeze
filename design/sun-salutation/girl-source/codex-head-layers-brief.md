You are preparing layered head artwork for a 2D cut-out (skeletal) animation
of the girl in `design/sun-salutation/girl-parts/`. Use your built-in
`image_gen` tool (imagegen skill, built-in mode) for the artwork, and Python
with Pillow/NumPy only to check alignment, trim, and shift layers. Do not
touch git. Work only in this repository.

## Problem

`design/sun-salutation/girl-parts/head.png` has her face and her hair painted
together, and the separate `long-hair.png` strand hangs from under it. In the
animation the long hair falls across her neck and throat, and the neck hidden
behind the hair was never painted. We need the head split into clean layers
that are drawn in this order (back to front):

1. `hair-back.png` — all hair that lies BEHIND her head and neck: the back of
   the hair mass from the crown down past the nape to about shoulder length,
   ending in a soft, even lower edge (the long hanging strand continues from
   there). No bangs, no hair in front of the ear or face.
2. `head-base.png` — her head with NO hair at all: face, the smooth skin of
   the scalp/skull, ear, jaw, and the COMPLETE neck (front and back of the
   neck fully painted) pointing straight down and ending in a clean
   horizontal cut. Same face, eye, nose, lips, skin tone, blush and line art
   as `head.png`. No shoulders, no clothing.
3. `hair-front.png` — the hair that lies IN FRONT of the skull and face: the
   blunt straight bangs, the hair covering the top and side of the head, and
   the side lock in front of the ear, ending around the jaw. Transparent
   where her face, ear and neck show.

The three layers must register EXACTLY: same canvas size, same scale, same
position. Stacked in the order above they must look like `head.png`
(her identity, right-facing side profile, level gaze, dark sapphire-blue hair,
same anime style, crisp thin line art, two-tone cel shading) — except that
the neck is now complete and the back hair is separate from the face.

Also make `long-hair.png` v2 only if needed: one long lock that continues
seamlessly from the lower edge of `hair-back.png` (same width at the top,
same colours), hanging straight down, tapering into softly wavy pointed tips,
about five times taller than wide, vertical. Save it as `long-hair-v2.png`.

## How

- Attach/view `head.png` and `master.png` as the identity reference.
- Prefer image EDITS of `head.png` (remove the hair to make the base; keep
  only the hair to make the hair layers), keeping the full canvas, so the
  layers stay registered. Generate with a truly transparent background.
- After generating, use Python to composite hair-back + head-base +
  hair-front over a flat background and compare with `head.png`. If a layer
  is offset or scaled, fix it by translating/scaling that layer (do not
  repaint by hand), or regenerate it. Also check: the base has a complete
  neck; the back hair contains no face; the front hair contains no skin.
- Regenerate anything that fails. Keep the face pretty and identical.

## Saving

Save the final PNGs (with alpha, all on the same canvas as each other) into
`design/sun-salutation/girl-parts/`: `head-base.png`, `hair-back.png`,
`hair-front.png`, and `long-hair-v2.png` if you made it. Also save the check
composite as `design/sun-salutation/girl-parts/head-layers-check.png`, and
add each layer's exact prompt to `design/sun-salutation/girl-parts/prompts.json`
(keep the existing entries). Finish with a short list of saved files and the
canvas size.
