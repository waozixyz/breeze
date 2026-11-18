# Watercolor textures

The six 256×256 WebP textures total 80,982 bytes:
`paper.webp`, `pigment.webp`, `linen.webp`, `plaster.webp`, `wood.webp`, and
`luminous-wash.webp`. Generated with the built-in imagegen tool as one material
atlas, then its six cells were cropped and downsampled for phone-friendly use.
No watermarks, signatures or text were visible in the inspected atlas. Paper
and pigment are sampled by the full-scene watercolor shader; linen,
plaster and wood by the room materials; the luminous wash shades the double.
The full generated source atlas is retained locally in the ignored
`backup/astral-threejs/watercolor-source-atlas.png` for provenance; the browser loads only the small WebP derivatives.

Generation prompt (built-in tool, no CLI fallback):

> Use case: stylized-concept. Asset type: texture atlas for a watercolor three.js bedroom scene. Create one 1536 by 1024 landscape image with exactly 3 columns and 2 rows of square material swatches, edge to edge, no gutters, no borders, no labels or letters. Each of the six cells should be a flat, evenly lit, top-down texture with no perspective and no objects: top left warm ivory cold-pressed watercolor paper with fine visible fibers; top middle softly mottled indigo and muted teal watercolor pigment blooms on paper, granulation and wet edges; top right pale blue-gray woven linen bedding with small threads and soft natural folds; bottom left dusty blue plaster painted with cloudy watercolor wash; bottom middle weathered dark walnut wood grain painted in watercolor with restrained warm violet brown tones; bottom right soft luminous pale teal watercolor wash fading into ivory, fine salt granulation, no objects. Tactile hand-painted watercolor, atmospheric, delicate pigment variation, real photographed paper fiber microtexture, enough broad smooth variation for a quiet room. All six swatches must be useful as material maps, not a scene or illustration. No watermark, no signatures, no text.
