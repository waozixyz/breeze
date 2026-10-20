# Flat Sun Salutation characters

`scripts/render-sun-salutation-flat.py` draws the Sun Salutation in a clean,
flat vector style: flat colours, no textures or gradients, one darker tone
for the far limbs and shades. It reuses the pose timeline, inverse
kinematics and hair simulation of `scripts/render-sun-salutation-girl.py`
and `docs/sun-salutation-girl.json`, so the yoga form is the same as the
painted animation; only the drawing differs.

```sh
python3 scripts/render-sun-salutation-flat.py                          # first character's video
python3 scripts/render-sun-salutation-flat.py --character indigo-crop  # one character
python3 scripts/render-sun-salutation-flat.py --all                    # every character
python3 scripts/render-sun-salutation-flat.py --grid                   # all side by side, numbered
python3 scripts/render-sun-salutation-flat.py --character indigo-crop --still 25.5
```

Videos go straight into `build/sun-salutation-flat/` as `<id>.mp4` and
`choose-characters.mp4` (1536 × 1024, or 768 × 512 cells in the grid, 30 fps,
69 s, one chapter per step). Stills go to `build/sun-salutation-flat/stills/`;
delete them after review. It needs Python 3 with pycairo, FFmpeg with
libx264, and the girl renderer's NumPy and Pillow for its import.

## Characters

`docs/sun-salutation-flat.json` lists the characters: Jade bun for women
and Indigo crop for men (owner's choice, 2026-10-15). Each picks a torso,
legs, sleeves, face and hair by name and gives its colours: skin, hair, top,
pants, the sleeve cuff and the small light orange accent (hair ties). Far
limbs, shades and hair highlights are derived from those colours.

The shapes behind those names are tables in the script:

- `TORSOS`: the top's outline along the spine, its hem band, the seat, the
  base of the head, where the neck enters the top, and how far the back of
  the hem settles against the hips when lying back up (`tunic`, `male`).
- `LEGS` and `SLEEVES`: limb radii, where trousers and sleeves end and their
  bands (`loose`, `trousers`; `bell`, `fitted`).
- `FACES`: the profile, scale, where the neck meets the head, blush, brow
  and mouth (`female`, `male`). The neck bends between the top and the
  head, so a lifted head never swings it out of the collar, and a shade
  under the jaw (`JAW_SHADE`) sets the head on it.
- `HAIRS`: the cap, an optional bun and an optional hanging strand that
  swings with the hair simulation (`bunLong`, `crop`). Men have short hair
  that never swings: no ponytails or buns.

Limbs are hulls of circles along their bones, and parts of one colour fill as
one shape, so joints never show seams. Feet solve their own floor contact:
flat when standing, on tucked toes behind her in plank and the lunges, on the
instep in cobra. With her chest on the floor, an elbow that would bend down
through it turns up toward her back instead. `--other-side` draws the next
round, in which the other leg steps back first.

## App frames

The app plays the same characters from transparent PNG frames:

```sh
python3 scripts/render-sun-salutation-characters.py
```

It draws every listed character on a clear stage at the rig's sprite scale,
the woman first and then the man, for the first round and again for the next
one (the other leg first), with the app's three-second moves: one
held frame for the first pose, then for each of the other eleven 90 frames
of the move and 30 more while the hanging hair settles
(`SETTLE_SECONDS`). The app plays those during the hold and keeps the last
one; the rest of the hold is left out, so the hair carries on from there
into the next move. Frames are cropped to each move, quantized to 256
colours and saved to `assets/practices/sunsalutation/characters/NN-<id>/`,
numbered by frame set: `01` and `02` for the first round, `03-<id>-other-side`
and `04-<id>-other-side` for the next.
It then writes `src/practices/sun_salutation/sun_salutation_frames.zi` and
`docs/sun-salutation-characters.json`, recompresses the PNGs
(`scripts/optimize-animation-pngs.py`, needs zopfli) and stores identical
frames once (`scripts/animation_inventory.py`). A character no longer listed
loses its frame folder. The app shows the first character as "Woman with
bun" and the second as "Man with short hair", who speaks with the male voice.
