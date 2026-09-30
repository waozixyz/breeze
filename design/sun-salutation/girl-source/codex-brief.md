You are generating artwork for a 2D skeletal (cut-out) animation of a sun
salutation in the Inbe app. Use your built-in `image_gen` tool (imagegen
skill, built-in mode). Do not write code to draw images. Do not use the CLI
fallback. Work only in this repository; do not touch git.

## The character (inspiration: attached reference images)

The attached images show the girl to take inspiration from: a gentle,
serene adult young woman drawn in a polished anime style, with very long,
flowing, dark sapphire-blue hair, blunt straight-cut bangs across the
forehead, large luminous blue eyes with fine lashes, a small nose, soft pink
lips, pale warm skin with a faint blush, a calm and pretty expression. She
wears a white top with a red sailor-style ribbon bow at the collar.

For our yoga animation she wears:
- a fitted white long-sleeved top with a small white sailor collar and a
  red ribbon bow at the front of the collar, hem at the hips;
- deep navy-blue full-length leggings;
- bare feet.

Art style for every image: clean, high-resolution anime illustration with
crisp thin dark-blue/brown line art and soft two-tone cel shading, the
colour richness of the reference but NO pixel grid, no dithering, no glow,
no stars, no swirling smoke, no background. Adult proportions (about 7 heads
tall), slim and graceful. Same palette, same line weight and same shading in
every image so the pieces fit together.

## Step 1 — master design

Generate `master.png`: ONE full-body image of her standing in a strict
RIGHT-FACING SIDE PROFILE (she looks to the right edge of the image), feet
together, arms hanging relaxed at her sides, long hair falling down her back
to mid-back. Plain transparent background, whole figure visible with margins.
Look at the result. If the face is not pretty and appealing, or it is not a
true right-facing side profile, regenerate until it is. Every later part must
match this master exactly (face, hair colour, outfit colours, line weight).
Attach/view the master when generating the parts so they stay consistent.

## Step 2 — separate parts (transparent background each)

Each part is ONE completely isolated drawing of ONE body part on a truly
transparent background, centred with generous margins, no shadows, no
labels, no floor, no other body parts, same scale and style as the master.
All parts are seen from her right-facing side profile.

1. `head.png` — her head in strict right-facing side profile, looking
   straight ahead (level gaze), upright. Include the blunt bangs, the hair on
   top and back of the skull, the ear, one large pretty eye, nose, lips,
   chin, and a short neck pointing straight down that ends in a clean
   horizontal cut. At the back, the hair stops at the nape/jaw line (the
   long hair is a separate layer), ending in a soft natural edge. No
   shoulders, no clothing.
2. `long-hair.png` — one long lock of her dark sapphire-blue hair hanging
   straight DOWN, as if it continues from under the back of the head: wide
   and full at the top edge (flat, soft top edge), flowing straight down with
   long strand lines and soft highlights, tapering into several softly wavy
   pointed tips at the bottom. About five times taller than wide. Vertical.
3. `torso.png` — her torso only, in the white top, right-facing side
   profile, upright and vertical: neck opening at the top (no neck, no head),
   white sailor collar and the red ribbon bow at the front of the collar,
   gentle bust at the front, slim waist, hem at the hips at the bottom.
   Shoulder area rounded and clean where an arm layer will overlap. No arms,
   no legs.
4. `arm.png` — ONE complete straight arm pointing straight DOWN, vertical:
   rounded shoulder cap at the top, white fitted long sleeve through the
   elbow (exactly halfway) to a neat white cuff at the wrist, ending in a
   small bare wrist stump. No hand, no torso. No seam or cut at the elbow.
5. `leg.png` — ONE complete straight leg pointing straight DOWN, vertical:
   rounded hip at the top, navy leggings through the knee (exactly halfway)
   to the ankle, ending in a small bare ankle stump. Shapely slim thigh and
   calf, calf at the back (left side). No foot, no torso. No seam at the knee.
6. `hips.png` — the pelvis/hip region in navy leggings, right-facing side
   profile: waistband at the top, rounded seat at the back (left), front of
   the hips at the right, stopping at the tops of the thighs. No torso, no
   legs below the top of the thigh.
7. `hand-upright.png` — ONE slender graceful hand seen from the back of the
   hand, fingers together pointing straight UP, thumb along the left side,
   short wrist stump at the bottom centre. Pretty, anatomically correct,
   four fingers plus thumb.
8. `hand-flat.png` — ONE hand pressed flat on the floor seen from the side
   (little-finger side): wrist at the LEFT end, palm and fingers lying flat
   along a horizontal line, fingertips pointing RIGHT. Anatomically correct.
9. `foot-flat.png` — ONE bare foot standing flat, side view: ankle stump at
   the top left third, heel at the LEFT, toes pointing RIGHT, flat sole along
   a horizontal line. Pretty, slim, anatomically correct toes.
10. `foot-tucked.png` — ONE bare foot as in a plank: the sole faces LEFT,
    heel at the top left, the foot almost vertical, toes bent forward and
    resting flat on the floor pointing RIGHT at the bottom. Ankle stump at
    the top.
11. `foot-instep.png` — ONE bare foot pointed, as in upward-facing dog: the
    top of the foot resting on the floor, sole facing up, toes pointing LEFT,
    ankle stump at the RIGHT end.

Check every generated part: isolated, transparent, correct orientation,
consistent with the master. Regenerate any part that fails.

## Saving

Copy each final PNG (keeping its alpha) into
`design/sun-salutation/girl-parts/` with exactly the file names above
(`master.png`, `head.png`, `long-hair.png`, `torso.png`, `arm.png`,
`leg.png`, `hips.png`, `hand-upright.png`, `hand-flat.png`, `foot-flat.png`,
`foot-tucked.png`, `foot-instep.png`). Also write
`design/sun-salutation/girl-parts/prompts.json` mapping each file name to
the exact prompt you used. Finish with a short list of the saved files.
