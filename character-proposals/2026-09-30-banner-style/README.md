# Inner Breeze character proposals

Four banner-inspired characters for owner review: two approved women and two
matching male counterparts. The app still uses its existing animation assets.

- `01-sunrise-ponytail.webp` — approved woman, honey-brown ponytail, teal top and sage trousers.
- `02-sage-bun.webp` — approved woman, chestnut bun, ivory top and moss trousers.
- `03-sunrise-ponytail-male.webp` — approved male artwork with the neck joined to the teal shirt.
- `04-sage-male.webp` — new male counterpart, short chestnut hair, ivory top and moss trousers.
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
The approved female output files were reused without rerendering them, and
the first male keeps his approved painting.

## Artwork and prompts

The first two women and the original male artwork came from the existing
OpenRouter generation archive. The second male atlas was created with the
built-in image_gen tool, using the approved characters and the actual Sun
Salutation banner as references. Its exact prompt and reference paths are
saved in `source/04-sage-male-generation.json`. Saved reference copies are
byte-identical to the images supplied to the tool.

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
