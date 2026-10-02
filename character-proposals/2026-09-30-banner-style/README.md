# Inner Breeze character proposals

Four approved banner-inspired characters: two women and two men. All four are
available in Sun Salutation's Customize screen. The saved selection appears in
the twelve-pose preview, practice animation and guide.

- `01-sunrise-ponytail.webp` — approved woman, honey-brown ponytail, teal top and sage trousers.
- `02-sage-bun.webp` — approved woman, chestnut bun, ivory top and moss trousers.
- `03-sunrise-ponytail-male.webp` — honey-brown ponytail, burnt-rust top and charcoal trousers.
- `04-sage-male.webp` — short chestnut hair, indigo top and sand trousers.
  His painted leg is a fifth thicker than the first man's, so the rig draws it
  narrower and without the seat fullness, keeping his seat flat.

Open `index.html` for synchronized playback. Gwenview can browse the GIF loops
and still images. `00-proposals-montage.jpg` places each woman above her male
counterpart. Each design also has MP4, WebP, GIF, preview PNG and twelve-pose
sequence JPG files.

Each 40-second loop covers prayer, upward salute, forward fold, half lift, plank,
low plank, upward dog, downward dog, half lift, forward fold, upward salute and
prayer. The movement uses articulated transitions, with 1.5-second holds and
2-second transitions. MP4s are 960 × 640 at 20 fps; WebP and GIF loops are
768 × 512 at 12 fps and repeat indefinitely.

The male neck attachment sits inside the painted shirt neckline, with the
head drawn behind the torso. This closes the gap in upright and bent poses.
Both men keep their approved faces, hairstyles and proportions, with distinct
clothing palettes requested by the owner on 2026-10-02.

The women's necks attach inside the round collar too (11% down the torso
instead of 5%). Their heads tilt back up to 42° from the spine in the half
lift, both planks and upward dog, which used to swing the throat out below
the collar. Both women and the first male were rerendered with this and the
current sun salutation motion.

## Artwork and prompts

The first two women and the original male artwork came from the existing
OpenRouter generation archive. The second male atlas was created with the
built-in image_gen tool, using the approved characters and the actual Sun
Salutation banner as references. Its exact prompt and reference paths are
saved in `source/04-sage-male-generation.json`. Saved reference copies are
byte-identical to the images supplied to the tool.

The men's outfit changes used the built-in image_gen tool. Exact edit prompts,
palettes, input and output hashes are in `source/outfit-edits-20261002.json`.
Only clothing colors were requested to change: the first man's torso, sleeve
and collar are rust and his trousers charcoal; the second man's torso and
sleeve are indigo and his trousers sand.

`prompts.json` records the four active concepts and their separate artwork
sources. The first male's torso refinement prompt and original usage metadata
are retained under the `03-sunrise-ponytail-male` source prefix. The archived
metadata did not retain his original atlas prompt.

The renderer uses the existing twelve-pose timeline and draws the painted
parts offscreen with Cairo, then encodes them with FFmpeg. It does not access
the desktop display. The shared rig keeps comparable body proportions.

## Rebuild the male review files

Requires Python with Pillow, NumPy, SciPy, Requests and pycairo, plus FFmpeg.
Run from this folder:

```sh
python3 build_male.py all
python3 validate_male.py
```

The build reuses the saved male atlases, renders both men, exports their GIFs,
and updates the four-character review page and montage. It makes no image API
calls and leaves the female output files untouched. For individual previews:

```sh
python3 build_male.py inspect --concept 3
python3 build_male.py inspect --concept 4
```

`validate_male.py` checks all four loops, decoded frames, duration, repeat
settings, twelve pose chapters and review images, then writes `validation.json`.
Temporary crops, render copies, logs and exit-status files are ignored by Git;
the artwork, prompts, rig settings and final review files are retained.

## Rebuild the app frames

From the repository root, run:

```sh
python3 scripts/render-sun-salutation-characters.py
make sun-salutation-test sun-salutation-assets-test
```

The app exporter reuses the approved painted parts and corrected attachment
points. It writes transparent PNGs under `assets/practices/sunsalutation/characters/`,
the generated Ziran frame table, and `docs/sun-salutation-characters.json`.
All four characters share a stage and 30 fps transitions lasting three seconds;
each has 991 frames covering all twelve poses. Bound hairstyles need no extra
settling frames. Native, Android and web builds include every character.
