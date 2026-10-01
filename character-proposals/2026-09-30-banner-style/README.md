# Inner Breeze character proposals

Four new banner-inspired character designs for owner review. These files are
local proposals; no app asset, app reference, site file or deployment was changed.

Open `index.html` for a two-by-two grid with synchronized restart and playback
controls. Gwenview can browse the looping animations and still previews in this
folder. `00-proposals-montage.jpg` compares all four designs in one image.

## Animations

- `01-sunrise-ponytail.webp` — honey-brown ponytail, lake-teal top, sage trousers.
- `02-sage-bun.webp` — chestnut bun, warm ivory top, moss trousers.
- `03-lake-bob.webp` — dark wavy bob, dusty sage top, blue-teal trousers.
- `04-dusk-braid.webp` — braided crown, clay top, slate-teal trousers.

Each WebP loops infinitely and contains the complete twelve-pose sun-salutation
sequence: prayer, upward salute, forward fold, half lift, plank, low plank,
upward dog, downward dog, half lift, forward fold, upward salute and prayer.
The movement uses continuous articulated transitions rather than a moving camera
over a still picture. The loop lasts 40 seconds, with 1.5-second holds and
2-second transitions. The MP4 companions render at 20 fps; WebP loops render at
12 fps. Separate `*-preview.png` and `*-sequence.jpg` files show each design and
all twelve poses. GIF companions are provided for image viewers with limited
animated WebP support.

## References and generation

Authoritative style references:

- `assets/practices/sunsalutation/banner-light.png`: warm sunlight, muted teal
  mountains, sage greens, natural adult anatomy, quiet painted contours.
- `assets/practices/meditation/banner-light.png`: restrained anime facial
  features, matte hand-painted texture, peaceful expression and atmosphere.
- `assets/practices/whm/banner-dark.png`: muted night palette and serene mood.

The existing mismatched girl is referenced by
`scripts/render-sun-salutation-girl.py` and stored in
`design/sun-salutation/girl-parts/`; the app consumes rendered frames in
`assets/practices/sunsalutation/girl/`. Those existing files were read only.

The owner's configured **OpenRouter** route was used, with the fast image model
**`google/gemini-3.1-flash-image`**, at 2K. The imagegen skill's labeled prompt
conventions were used. The shared brief calls for a new anime-inspired adult
woman matching the actual banners' matte watercolor/gouache painting, subtle
paper texture, muted teal/sage/cream/earth palette, small calm facial features,
natural proportions, modest exercise clothing and bare feet. The four briefs
specify different hair, skin and clothing. Exact prompts are in `prompts.json`;
all targeted refinements and model usage metadata are under `source/`.

The image model generated fresh painted part atlases, then refined the torso
pieces for animation. The existing twelve-pose renderer supplies the pose
timeline and articulates those new paintings. Frames are drawn offscreen with
Cairo and encoded by FFmpeg. No display is accessed while generating frames.
Short/bound hairstyles move with the head. These are art-direction proposals;
the reusable rig keeps the same body proportions across all four for comparison.

## Rebuild locally

Requires Python with Pillow, NumPy, SciPy, Requests and pycairo, and FFmpeg.
The generation commands require the already configured `OPENROUTER_API_KEY` in
the desktop environment. No credential is saved in this folder.

```sh
python3 build_proposals.py prepare
python3 build_proposals.py generate
python3 build_proposals.py refine
python3 build_proposals.py shoulder --concept 3
python3 build_proposals.py shoulder --concept 4
python3 build_proposals.py inspect
python3 build_proposals.py render
python3 build_proposals.py gif
python3 build_proposals.py page
```

Run these from this proposal folder. Image generation skips already saved
outputs; saved atlases and corrected parts can be reused without another API
call. Temporary render copies, logs and intermediate part crops are ignored by
Git. Generated artwork, exact prompts and final review files are retained.
