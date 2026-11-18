# Figure model candidates — 2026-11-18

The owner rejected the MakeHuman-based figures and had them removed. Never
use a MakeHuman-based body again (MakeHuman, MPFB, Anny, MB-Lab,
CharMorph). This is the shortlist of free models that Inner Breeze, a paid
app on Google Play, may ship. We need a pretty, petite young Asian woman
and a man who can do Tai Chi, Sun Salutation, the Workout and astral
projection.

**The owner picks; nothing is integrated yet.** The pick is loaded through
the glTF importer that is being added to Kryon.

Previews and downloadable files are in `build/model-candidates/` (not
committed). The numbered contact sheet is
`build/model-candidates/contact-sheet.png`. Licence clauses below are
quoted from the licence pages and files themselves; where a page refused
automated reading, that is said.

## 1. Quaternius — Universal Base Characters

- **Preview:** `build/model-candidates/quaternius/universalbasecharacters.jpg`
- **Author:** Quaternius
- **Link:** <https://quaternius.com/packs/universalbasecharacters.html>, download at <https://quaternius.itch.io/universal-base-characters> (free, name your own price; itch.io's download needs a browser, so it isn't fetched here).
- **Licence:** CC0. The pack page says: "Free to use in personal, educational and commercial projects. (CC0 License)". The CC0 deed says: "You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission."
  - Released 2025, before Quaternius's newer QAL licence (2026-08), which by its own terms covers only later releases.
- **Attribution:** none.
- **Format:** glTF, FBX and OBJ; the Source tier adds rigged .blend files.
- **Rig:** "Humanoid Rig compatible with retargeting in any engine". It works with Quaternius's CC0 Universal Animation Library.
- **Triangles:** "Average 13k".
- **Textures:** included.
- **Why it fits:**
  - The closest to the owner's sculpt references: smooth, clean, stylised bodies with good anatomy.
  - Six bodies in Regular, Teen and Superhero proportions (male and female), 20 hairstyles, and skin and eye colour shaders in the Source tier.
  - The Teen or Regular woman with black hair in a bun, a warmer skin tone and our own outfit gives the petite young Asian woman; the Regular man gives him.
  - Matching CC0 outfits exist (Modular Character Outfits).
  - Mobile-friendly.

## 2. VRoid Studio — our own model

- **Preview:** the base models in `build/model-candidates/vroid/cc0-models.png`
- **Author:** us, made in pixiv's free VRoid Studio
- **Link:** <https://vroid.com/en/studio>
- **Licence:** pixiv's VRoid Studio Guidelines (<https://vroid.com/en/studio/guidelines>):
  - "Any individual or corporation may sell or use for commercial purposes any mesh, texture, or preset item provided by VRoid Studio, including models, clothing items, and accessories, provided that no special clauses are indicated in the license."
  - "You can use images and videos of models created with VRoid Studio and generate profit from … games, applications, software …"
  - The one limit: "You cannot create an application that can generate or output 3D models, avatars, or items consisting of deformed or combined meshes and textures that were created in VRoid Studio." Breeze only shows its own fixed characters, so this doesn't apply.
- **Attribution:** none.
- **Format:** VRM, which is glTF 2.0.
- **Rig:** the VRM humanoid skeleton.
- **Triangles:** typically 20k–60k. VRoid's export can reduce polygons and merge materials to fit 50k.
- **Textures:** included.
- **Why it fits:**
  - Exactly the character we want, designed by us: petite, a cute young Chinese woman with a black bun and a qipao-style top; a young man in a kung fu jacket.
  - The cel-shaded anime style suits Breeze's storybook backdrops.
  - Making them is design work done in the desktop app, not a download.

## 3. VRoid — official AvatarSample_A and AvatarSample_C

- **Preview:** `build/model-candidates/vroid/conditions-models.png`
- **Author:** pixiv (official samples)
- **Link:**
  - A: <https://hub.vroid.com/en/characters/2843975675147313744/models/5644550979324015604>
  - C: <https://hub.vroid.com/en/characters/1248981995540129234/models/8640547963669442173>
- **Licence:** VRoid Hub conditions as published on the official pages: "Avatar Use: Allow / Violent acts: Allow / Sexual acts: Allow / Corporate use: Allow / Individual commercial use: Allow / Redistribution: Allow / Alterations: Allow / Attribution: Not required".
  - Copyright is not waived; these are not CC0.
  - VRoid Hub and the pixiv help centre refuse automated reading, so I read these conditions through search results; confirm them in a browser.
- **Attribution:** not required.
- **Format:** VRM (glTF 2.0). Downloading needs a VRoid Hub login, so not fetched here.
- **Rig:** VRM humanoid.
- **Triangles:** not measured (the files need the login).
- **Textures:** included.
- **Why it fits:**
  - A is a cute brown-haired girl and C a black-haired young man; recolour her hair black and dress both for practice.
  - Ready now, and editable in VRoid Studio.

## 4. VRoid — HairSample_Female and HairSample_Male (CC0)

- **Preview:** `build/model-candidates/vroid/cc0-models.png`; the files are `build/model-candidates/vroid/HairSample_Female.vrm` and `HairSample_Male.vrm`.
- **Author:** pixiv (VRoid beta samples)
- **Link:** <https://github.com/madjin/vrm-samples> (a mirror of pixiv's samples)
- **Licence:**
  - CC0, written into each file's own VRM metadata: `"licenseName": "CC0", "commercialUssageName": "Allow", "allowedUserName": "Everyone"`.
  - pixiv's list says: "The CC license for these models is CC0. This model can be edited and used freely. Copyright is waived, and there is no particular limit when using them."
- **Attribution:** none.
- **Format:** VRM (glTF 2.0).
- **Rig:** VRM humanoid, plus spring bones for the hair (357 and 273 joints in all).
- **Triangles:** 27,068 (her) and 24,858 (him), measured from the files.
- **Textures:** included (25 images each).
- **Why it fits:**
  - Public domain anime pair with black hair, ready to load the moment the importer lands.
  - Her cat ears and twin tails would need editing in VRoid Studio for a calm practice look.

## 5. Microsoft Rocketbox — Female_Adult_03 and Male_Adult_10

- **Preview:** `build/model-candidates/rocketbox/Female_Adult_03.png` and `Male_Adult_10.png`; the files (FBX plus 2048 px textures) are in `build/model-candidates/rocketbox/Female_Adult_03/` and `Male_Adult_10/`.
- **Author:** Microsoft (Rocketbox)
- **Link:** <https://github.com/microsoft/Microsoft-Rocketbox>
- **Licence:** MIT (`LICENSE.md` in the repository):
  - "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software … The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."
  - The README: "The library of avatars is now released under MIT License."
- **Attribution:** include the MIT notice in the app's licences.
- **Format:** FBX (3ds Max export) with TGA colour, normal, specular and opacity maps. Converts to glTF with Blender or FBX2glTF.
- **Rig:** a 3ds Max Biped humanoid; 80 skin clusters.
- **Triangles:** 9,208 (her) and 6,732 (him), measured from the FBX files.
- **Why it fits:**
  - Realistic, decent East Asian adults with a full rig and 417 MIT animations in the same repository.
  - They're dressed in street clothes and are less smooth and pretty than the sculpt references; the repository is archived.

## 6. suzuart — Rigged Anime Japanese High School Girl and Boy

- **Preview:** `build/model-candidates/sketchfab/Rigged-Anime-Japanese-High-School-Girl.jpg` and `-Boy.jpg`
- **Author:** suzuart (Sketchfab)
- **Link:**
  - Girl: <https://sketchfab.com/3d-models/rigged-anime-japanese-high-school-girl-ad7efa7afb594bffa4cd9733562ef4dc>
  - Boy: <https://sketchfab.com/3d-models/rigged-anime-japanese-high-school-boy-845df0101cd5429e86b190be757d1365>
- **Licence:** CC BY 4.0. The CC deed says:
  - "Share — copy and redistribute the material in any medium or format for any purpose, even commercially."
  - "Adapt — remix, transform, and build upon the material for any purpose, even commercially."
  - "Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made."
- **Attribution:** required: "suzuart", the model link and a CC BY 4.0 link, in the app's credits.
- **Format:** GLB / glTF 2.0 with 2048 px textures. Downloading needs a Sketchfab login.
- **Rig:** full rig, exported "Deform Bones Only"; the boy has an animation.
- **Triangles:** 55,517 (her, a little over the 50k aim) and 42,185 (him), from Sketchfab.
- **Why it fits:**
  - A clean, original anime pair with Japanese features and black hair, already in glTF.
  - They wear school uniforms and need practice clothes.

## 7. Sketchfab — Animated Tai Chi Character and Shaolin Kung Fu

- **Preview:** `build/model-candidates/sketchfab/Animated-Tai-Chi-Character.jpg` and `Shaolin-Kung-Fu.jpg`
- **Authors:** LasquetiSpice (the woman) and NORBERTO-3D (the man)
- **Link:**
  - Woman: <https://sketchfab.com/3d-models/animated-tai-chi-character-77af3e36cf384e5c8f7d9cf7dc140a24>
  - Man: <https://sketchfab.com/3d-models/shaolin-kung-fu-07dfbd9317794d9d97a626e66810c607>
- **Licence:** CC BY 4.0 (clauses as in 6).
- **Attribution:** required for each author, as in 6.
- **Format:** glTF via Sketchfab download (login needed).
- **Rig:** rigged and animated. Her animation is a real 25-second Tai Chi "Repulse the Monkey"; he is a Shaolin monk with a kung fu animation.
- **Triangles:** 12,805 (her) and 17,288 (him), from Sketchfab.
- **Why it fits:**
  - Real Tai Chi and kung fu motion on mobile-sized bodies.
  - Plainer looking than 1–6, so more useful as motion than as the final characters.

## Motion sources usable commercially

- **CMU Graphics Lab Motion Capture Database** (<http://mocap.cs.cmu.edu/>):
  - Licence: "This dataset of motions is free for all uses. … You may include this data in commercially-sold products, but you may not resell this data directly, even in converted form."
  - It has Tai Chi (subject 12, trial 4), yoga (subjects 111 and 113), stretches (subject 42 and others), squats and push-ups.
- **Mixamo** (Adobe):
  - Adobe's FAQ (it refuses automated reading; quoted from search results of the page): "You can use both characters and animations royalty free for personal, commercial, and non-profit projects including: … Create video games."
  - Adobe's community FAQ forbids "Any type of free distribution of character or animation raw files" and use for training machine-learning models.
  - Needs an Adobe ID to download. Its characters are generic and none fits as well as 1–6, but its animation library is a good motion source.
- **Quaternius Universal Animation Library:** CC0, made for candidate 1's rig.
- **Candidate 7's own Tai Chi and kung fu animations:** CC BY 4.0.

## Excluded

- **MakeHuman and anything built on it** (MPFB, Anny, MB-Lab, CharMorph): the owner rejected it.
- **Open Source Avatars / 100Avatars** (Polygonal Mind, CC0 VRM): checked all 300 avatars in `build/model-candidates/100avatars/`. They're cartoon and novelty characters; none is a pretty young woman.
- **Poly Pizza** (Quaternius's CC0 low-poly women, e.g. "Animated Woman"): CC0 but low-poly and generic. Candidate 1 is the same author's much better pack.
- **Blender Studio Human Base Meshes** (CC0): no rig and no textures.
- **Fan art of other people's characters on Sketchfab** (Kung Fu Panda, NIKKE, Watamote and others): CC BY labels don't clear the original rights.
- **Models made with Daz or Character Creator** (e.g. "Alina Ip"): their makers' licences don't allow this redistribution; also 137k triangles.
- **Daz, MetaHuman and the Unity Asset Store:** engine-locked or restricted.
- **Anything without a clear licence, non-commercial or editorial licences, and game rips** (such as the Character-14 archive).
