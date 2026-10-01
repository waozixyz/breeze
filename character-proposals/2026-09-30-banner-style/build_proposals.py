#!/usr/bin/env python3
"""Generate review-only InBE characters through the owner's OpenRouter route.

No app assets, generated app sources, or site files are written by this script.
The existing twelve-pose renderer is imported, with all paths redirected here.

2026-10-01 owner feedback revision: the four proposals are gender-varied (two
women, two men) and every prompt carries an explicit natural-anatomy guard
against exaggerated hips or buttocks. `legfix` can correct a generated leg part
whose rear contour still reads as oversized.
"""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = "google/gemini-3.1-flash-image"
SOURCE_PARTS = ROOT / "design/sun-salutation/girl-parts"
PART_FILES = [
    "head.png", "torso.png", "leg.png", "arm.png",
    "hand-upright.png", "hand-flat.png", "foot-flat.png",
    "foot-tucked.png", "foot-instep.png",
]
ANATOMY = ("Natural, tasteful adult anatomy in every part: slim ordinary hips "
           "and seat. NO exaggerated, oversized, rounded or emphasized "
           "buttocks, no arched lower back, no hip or thigh inflation, no "
           "pin-up curves or posed emphasis. The rear contour stays flat to "
           "gently curved, like the quietly standing people in the banners.")
CONCEPTS = [
    {"id": "01-sunrise-ponytail", "name": "Sunrise ponytail",
     "design": "An adult woman with warm light peach skin, honey-brown hair in a short low ponytail (entire ponytail fits inside the head tile), soft brown eyes and a calm expression. A plain muted lake-teal long-sleeve exercise top with a round neckline, olive-sage leggings, bare feet. The top has no hood and no ribbon."},
    {"id": "02-sage-bun", "name": "Sage bun",
     "design": "An adult woman with medium warm golden skin, chestnut-brown hair in a compact high bun, a few softly curved wisps, small brown eyes and a peaceful expression. A plain warm ivory long-sleeve exercise top with a round neckline, moss-green leggings, bare feet. The top has no hood and no ribbon."},
    {
        "id": "03-sunrise-ponytail-male",
        "name": "Sunrise ponytail (male)",
        "gender": "male",
        "design": "The approved adult male counterpart of Sunrise ponytail: warm light peach skin, honey-brown hair in a short tied-back ponytail, calm small brown eyes, a plain lake-teal long-sleeve exercise top, olive-sage trousers and bare feet. Keep his existing face, hair and clothing. His neck tucks naturally inside the shirt collar.",
        "rig": {
            "torso": {"neck": [0.62, 0.13]},
        },
    },
    {
        "id": "04-sage-male",
        "name": "Sage crop (male)",
        "gender": "male",
        "design": "The adult male counterpart of Sage bun: warm golden-tan skin, short softly swept chestnut-brown hair, small calm brown eyes, natural adult male proportions, a plain warm ivory long-sleeve exercise top, moss-green trousers and bare feet. His complete bare neck tucks naturally inside the shirt collar.",
        "rig": {
            "torso": {"neck": [0.62, 0.13]},
            # His painted leg is about a fifth thicker for its length than
            # the first man's, seat included; draw it at the same thickness
            # and without the extra fullness behind the hip.
            "leg": {"width": 0.7, "seat": {"depth": 0.0, "center": 8, "span": 32}},
        },
    },
]
REFERENCES = [
    ROOT / "assets/practices/sunsalutation/banner-light.png",
    ROOT / "assets/practices/meditation/banner-light.png",
    ROOT / "assets/practices/whm/banner-dark.png",
]


def font(size):
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)


def prepare():
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "source").mkdir(exist_ok=True)
    # A precise parts/pose guide, not a style reference. Every tile is independent.
    atlas = Image.new("RGB", (2048, 2048), "white")
    draw = ImageDraw.Draw(atlas)
    layout = []
    for index, filename in enumerate(PART_FILES):
        left = round(index % 3 * 2048 / 3)
        top = round(index // 3 * 2048 / 3)
        right = round((index % 3 + 1) * 2048 / 3)
        bottom = round((index // 3 + 1) * 2048 / 3)
        picture = Image.open(SOURCE_PARTS / filename).convert("RGBA")
        picture = picture.crop(picture.getbbox())
        picture.thumbnail((right - left - 116, bottom - top - 116), Image.Resampling.LANCZOS)
        x = left + (right - left - picture.width) // 2
        y = top + 58 + (bottom - top - 116 - picture.height) // 2
        atlas.paste(picture, (x, y), picture)
        draw.text((left + 18, top + 14), f"{index + 1} {filename[:-4]}", fill="#777777", font=font(22))
        layout.append({"file": filename, "tile": [left, top, right, bottom],
                       "art_box": [x, y, x + picture.width, y + picture.height]})
    atlas.save(HERE / "source/geometry-guide.png")
    (HERE / "source/layout.json").write_text(json.dumps(layout, indent=2) + "\n")
    manifest = {"model": MODEL, "route": "https://openrouter.ai/api/v1/images",
                "resolution": "2K", "aspect_ratio": "1:1",
                "revision": "2026-10-01 gender-varied set with natural-anatomy guard",
                "references": [str(p.relative_to(ROOT)) for p in REFERENCES],
                "reference_roles": ["sun banner: palette, person, soft paint", "meditation banner: facial depiction and texture", "night banner: quiet atmosphere", "geometry-guide: part order, orientation, anchors only"],
                "concepts": []}
    for concept in CONCEPTS:
        entry = dict(concept)
        entry["prompt"] = prompt(concept)
        manifest["concepts"].append(entry)
    (HERE / "prompts.json").write_text(json.dumps(manifest, indent=2) + "\n")


def prompt(concept):
    return f"""Use case: stylized-concept
Asset type: nine painted animation parts for a NEW Inner Breeze anime-inspired adult character proposal. Across the set the characters are two grown women and two grown men; this request is for {concept['design'].split('.', 1)[0].lower()}.
Input images: images 1-3 are the ACTUAL Inner Breeze banners, the authoritative visual style references. Image 4 is ONLY a geometry and tile-layout guide from the old mismatched character; do NOT copy its blue hair, schoolgirl styling, shiny rendering or large eyes.
Primary request: {concept['design']}
Style/medium: Match the banners' gentle hand-painted storybook anime, matte watercolor-gouache surfaces with fine paper grain, restrained warm contour lines, simplified natural anatomy and small facial features. This character belongs beside the people in these banners. Warm, grounded and quiet, not glossy generic anime. Adult proportions, practical modest yoga clothing. {ANATOMY}
Composition/framing: Repaint image 4 as the exact same 3-column by 3-row atlas, 9 separate parts on PURE WHITE. Preserve its part order, orientation and anchor positions. Each part is centered independently in its tile; do not assemble a full person. Row 1: right-facing profile head WITH painted neck ending at the bottom (new hairstyle contained within this tile), right-facing side torso from neck opening through hips WITHOUT head or arms, one straight full leg from upper hip through ankle WITHOUT foot. Row 2: one straight full arm from shoulder through wrist WITHOUT hand, upright hand with fingers pointing up, horizontal hand with fingers pointing right. Row 3: flat bare foot pointing right, toe-tucked foot matching guide orientation, bare instep foot matching guide orientation. Make torso and sleeve color identical; make skin identical throughout; leggings end at ankles. The leg is matte fabric over a straight adult leg: the rear line from waistband over the seat into the thigh stays nearly straight to gently curved.
Lighting/mood: Soft diffuse warm daylight, calm expression. No hard specular highlights.
Color palette: muted teal, sage, cream and warm earth colors from image 1; use the specified character colors.
Constraints: Clean reusable animation pieces. Preserve geometrical placement, profiles, scale, and silhouettes of limbs and feet from image 4. The head may change hairstyle. Use small relaxed eyes. Draw the entire neck; don't hide it behind hair. The torso is a plain exercise top with sleeves supplied by the separate arm. Remove the old red ribbon and hood completely. {ANATOMY} No blue hair, school uniform, text, labels, grid lines, shadows on white, decorations, extra pieces, extra limbs or background scene. Leave ample pure white gutters around EVERY isolated part. White is background only; ivory clothing remains shaded with painted contour edges.
"""


def data_reference(path):
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")}}


def generate(concept):
    destination = HERE / "source" / (concept["id"] + "-atlas.png")
    if destination.exists():
        return
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OpenRouter key is not configured in the desktop environment")
    payload = {"model": MODEL, "prompt": prompt(concept), "n": 1,
               "resolution": "2K", "aspect_ratio": "1:1",
               "input_references": [data_reference(p) for p in [*REFERENCES, HERE / "source/geometry-guide.png"]]}
    started = time.monotonic()
    response = requests.post("https://openrouter.ai/api/v1/images", json=payload,
                             headers={"Authorization": "Bearer " + key}, timeout=(20, 240))
    if not response.ok:
        # Never log raw requests, headers, responses, data URLs, or keys.
        raise RuntimeError(f"Image API returned HTTP {response.status_code} for {concept['id']}")
    result = response.json()
    if not result.get("data"):
        raise RuntimeError(f"No image was returned for {concept['id']}")
    encoded = result["data"][0].get("b64_json")
    if not encoded:
        raise RuntimeError(f"Image API returned no image bytes for {concept['id']}")
    picture = Image.open(io.BytesIO(base64.b64decode(encoded)))
    picture.save(destination)
    metadata = {"model": MODEL, "elapsed_seconds": round(time.monotonic() - started, 2),
                "dimensions": picture.size, "usage": result.get("usage", {})}
    (HERE / "source" / (concept["id"] + "-generation.json")).write_text(json.dumps(metadata, indent=2) + "\n")
    print("Generated " + concept["id"], flush=True)


def refine_torso(concept):
    destination = HERE / "source" / (concept["id"] + "-torso.png")
    if destination.exists():
        return
    original = Image.open(SOURCE_PARTS / "torso.png").convert("RGBA")
    geometry = Image.new("RGB", original.size, "white")
    geometry.paste(original, (0, 0), original)
    geometry.save(HERE / "source/torso-geometry.png")
    refinement = f"""Use case: precise-object-edit
Asset type: detached torso-only garment for a paper-doll animation rig.
Input images: Image 1 is the new character's painted parts and defines the EXACT palette and matte illustration style. Image 2 is the exact torso-only shape/orientation guide; image 3 is the Inner Breeze banner style reference.
Primary request: Paint ONLY the separate TORSO clothing piece for this character: {concept['design']}
Composition: Right-facing profile garment, centered on pure white with ample margin. Match the torso outline and geometry in image 2: shoulder joint is at the upper LEFT, chest at upper RIGHT, waist and hem below. This is the vest-shaped body panel of the exercise shirt, NOT a complete shirt with hanging arms. The arm is supplied by a different animation asset. Keep the softly outlined round shoulder attachment area on the upper left, but NO sleeve extending downward. Keep the bottom hem covering the hips.
Style: Match image 1's clothing paint exactly, muted color with soft gouache texture and quiet warm contour lines. The hem hangs straight down over the hips in a relaxed drape.
Constraints: Only torso garment fabric may be visible. ZERO SKIN, ZERO NECK, ZERO HEAD, ZERO ARMS, ZERO SLEEVES EXTENDING FROM THE BODY, ZERO HANDS, ZERO PANTS, ZERO LEGS. No hood, no ribbon, no red bow. Do not include the head or any other pieces from image 1. Stop at the neckline and shirt hem. Use a plain small round neck opening. Preserve the shirt color from image 1. No labels, text, grid or ground shadow. One isolated torso clothing panel only, flat side profile as in image 2. {ANATOMY}
"""
    key = os.environ["OPENROUTER_API_KEY"]
    payload = {"model": MODEL, "prompt": refinement, "n": 1, "resolution": "2K",
               "aspect_ratio": "3:4", "input_references": [data_reference(p) for p in [HERE / "source" / (concept["id"] + "-atlas.png"), HERE / "source/torso-geometry.png", REFERENCES[0]]]}
    response = requests.post("https://openrouter.ai/api/v1/images", json=payload, headers={"Authorization": "Bearer " + key}, timeout=(20, 240))
    if not response.ok:
        raise RuntimeError(f"Torso refinement returned HTTP {response.status_code}")
    result = response.json()
    picture = Image.open(io.BytesIO(base64.b64decode(result["data"][0]["b64_json"])))
    picture.save(destination)
    (HERE / "source" / (concept["id"] + "-torso-prompt.json")).write_text(json.dumps({"model": MODEL, "prompt": refinement, "usage": result.get("usage", {})}, indent=2) + "\n")
    print("Refined torso " + concept["id"], flush=True)


def extract(concept):
    atlas = Image.open(HERE / "source" / (concept["id"] + "-atlas.png")).convert("RGBA")
    output = HERE / "source" / concept["id"] / "parts"
    output.mkdir(parents=True, exist_ok=True)
    for index, filename in enumerate(PART_FILES):
        left = round(index % 3 * atlas.width / 3)
        top = round(index // 3 * atlas.height / 3)
        right = round((index % 3 + 1) * atlas.width / 3)
        bottom = round((index // 3 + 1) * atlas.height / 3)
        # Strip tile labels and preserve only the connected painted silhouette.
        margin = round((right - left) * .035)
        picture = atlas.crop((left + margin, top + margin, right - margin, bottom - margin))
        refined_torso = HERE / "source" / (concept["id"] + "-torso.png")
        repaired_torso = HERE / "source" / (concept["id"] + "-torso-v2.png")
        corrected_leg = HERE / "source" / (concept["id"] + "-leg-v2.png")
        if filename == "torso.png":
            if repaired_torso.exists():
                picture = Image.open(repaired_torso).convert("RGBA")
            elif refined_torso.exists():
                picture = Image.open(refined_torso).convert("RGBA")
        elif filename == "leg.png" and corrected_leg.exists():
            picture = Image.open(corrected_leg).convert("RGBA")
        # Built-in imagegen supplies real alpha. Preserve its coverage rather
        # than treating the transparent pixels as a painted background.
        if picture.getchannel("A").getextrema()[0] < 255:
            pixels = np.array(picture)
            labels, count = ndimage.label(pixels[..., 3] > 40)
            areas = np.bincount(labels.ravel())
            areas[0] = 0
            if not count or areas.max() < 500:
                raise RuntimeError("Missing painted part: " + filename)
            silhouette = labels == areas.argmax()
            # Keep the original alpha at the painted contour. Isolated
            # transparent specks must not redefine a part's attachment box.
            coverage = ndimage.binary_dilation(silhouette, iterations=2)
            pixels[..., 3] = np.where(coverage, pixels[..., 3], 0)
            result = Image.fromarray(pixels, "RGBA")
            result = result.crop(result.getbbox())
            result.save(output / filename)
            continue
        pixels = np.asarray(picture.convert("RGB"))
        white = pixels.min(axis=2) > 240
        seeds = np.zeros(white.shape, bool)
        seeds[0] = seeds[-1] = True
        seeds[:, 0] = seeds[:, -1] = True
        background = ndimage.binary_propagation(seeds & white, mask=white)
        foreground = ~background
        labels, count = ndimage.label(foreground)
        areas = np.bincount(labels.ravel())
        areas[0] = 0
        if not count or areas.max() < 500:
            raise RuntimeError("Missing painted part: " + filename)
        # Keep the main part. Hair islands can be kept when close to its outline.
        silhouette = labels == areas.argmax()
        silhouette = ndimage.binary_fill_holes(silhouette)
        edge = ndimage.binary_dilation(silhouette, iterations=1) & ~silhouette
        alpha = np.where(silhouette, 255, 0).astype(np.uint8)
        alpha[edge] = (255 - pixels.min(axis=2)[edge]).clip(0, 255)
        rgba = np.dstack([pixels, alpha])
        result = Image.fromarray(rgba, "RGBA")
        result = result.crop(result.getbbox())
        result.save(output / filename)
    # The full head contains short/bound hair; there is no detached long lock.
    Image.new("RGBA", (8, 8), (70, 45, 30, 255)).save(output / "long-hair.png")
    return output


def repair_shoulder(concept):
    destination = HERE / "source" / (concept["id"] + "-torso-v2.png")
    if destination.exists():
        return
    refinement = """Use case: precise-object-edit
Asset type: painted torso clothing panel for an animation rig.
Primary request: Fill the white oval shoulder cutout in this clothing piece with continuous fabric that exactly matches the surrounding shirt's color, softly painted texture, and shading. The shoulder area must be fully painted shirt fabric; it may have a subtle curved attachment seam but MUST NOT have a white hole. It is a torso panel for a LONG-SLEEVE top; the separate sleeve will be placed over it in animation.
Constraints: Change ONLY the interior white oval shoulder cutout. Keep every other pixel, the exact outer contour, neckline, hem, clothing color, painting style, orientation, scale and pure white background unchanged. No extra sleeve, arm, neck, skin, labels or decorations. Return one isolated corrected clothing panel.
"""
    payload = {"model": MODEL, "prompt": refinement, "n": 1, "resolution": "2K", "aspect_ratio": "3:4",
               "input_references": [data_reference(HERE / "source" / (concept["id"] + "-torso.png"))]}
    response = requests.post("https://openrouter.ai/api/v1/images", json=payload,
                             headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]}, timeout=(20, 240))
    if not response.ok:
        raise RuntimeError(f"Shoulder correction returned HTTP {response.status_code}")
    result = response.json()
    picture = Image.open(io.BytesIO(base64.b64decode(result["data"][0]["b64_json"])))
    picture.save(destination)
    (HERE / "source" / (concept["id"] + "-shoulder-prompt.json")).write_text(json.dumps({"model": MODEL, "prompt": refinement, "usage": result.get("usage", {})}, indent=2) + "\n")
    print("Corrected shoulder " + concept["id"], flush=True)


def fix_leg(concept):
    """Repaint one leg part whose rear contour reads as exaggerated.

    Uses the generated atlas for palette/style, the original guide leg for
    orientation and scale, and demands natural adult hip/seat anatomy.
    """
    destination = HERE / "source" / (concept["id"] + "-leg-v2.png")
    if destination.exists():
        return
    original = Image.open(SOURCE_PARTS / "leg.png").convert("RGBA")
    geometry = Image.new("RGB", original.size, "white")
    geometry.paste(original, (0, 0), original)
    geometry.save(HERE / "source/leg-geometry.png")
    correction = f"""Use case: precise-object-edit
Asset type: one detached painted leg-with-hip part for a paper-doll animation rig.
Input images: Image 1 is the painted leg from the generated part set and defines the EXACT palette and matte illustration style. Image 2 is the leg's shape/orientation guide from the original rig; match its scale, length and ankle position. Image 3 is the Inner Breeze banner style reference.
Primary request: Paint ONLY the corrected replacement leg part for this character: {concept['design']}
Edit: remove every trace of exaggerated or oversized buttocks. The rear of the upper hip must read as natural, tasteful adult anatomy: a nearly straight to only gently curved line from the waistband down over the seat and into the thigh. {ANATOMY}
Composition: Right-facing straight leg from upper hip through ankle, WITHOUT foot, centered on pure white with ample white gutter. Keep the leggings color, matte fabric rendering and quiet painted contour style of image 1. Flat matte fabric: no stretched, shiny or wedgie-emphasizing material, no seam or crease emphasis on the seat.
Constraints: One isolated leg only. No shadows on the white, no other body parts, no text, labels or decorations. Keep paint texture consistent with image 1.
"""
    payload = {"model": MODEL, "prompt": correction, "n": 1, "resolution": "2K",
               "aspect_ratio": "3:4", "input_references": [data_reference(p) for p in
                                                           [HERE / "source" / (concept["id"] + "-atlas.png"),
                                                            HERE / "source/leg-geometry.png",
                                                            REFERENCES[0]]]}
    response = requests.post("https://openrouter.ai/api/v1/images", json=payload,
                             headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]}, timeout=(20, 240))
    if not response.ok:
        raise RuntimeError(f"Leg correction returned HTTP {response.status_code}")
    result = response.json()
    picture = Image.open(io.BytesIO(base64.b64decode(result["data"][0]["b64_json"])))
    picture.save(destination)
    (HERE / "source" / (concept["id"] + "-leg-prompt.json")).write_text(json.dumps({"model": MODEL, "prompt": correction, "usage": result.get("usage", {})}, indent=2) + "\n")
    print("Corrected leg " + concept["id"], flush=True)


def load_renderer():
    spec = importlib.util.spec_from_file_location("inbe_character_review_renderer", ROOT / "scripts/render-sun-salutation-girl.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def render(concept, inspect=False):
    module = load_renderer()
    module.PARTS = extract(concept)
    module.BUILD = HERE / "source" / concept["id"] / "render"
    rig = copy.deepcopy(json.loads((ROOT / "docs/sun-salutation-girl.json").read_text()))
    rig["parts"]["head"] = {"file": "head.png", "pivot": [.66, .985], "height": 71.43}
    rig["parts"]["longHair"] = {"file": "long-hair.png"}
    # Attachment points belong to the painting: the collar covers the neck
    # base before the head rotates through the folded poses.
    for part, adjustments in concept.get("rig", {}).items():
        rig["parts"][part].update(copy.deepcopy(adjustments))
    rig["output"]["detail"] = 1.6
    rig["timing"]["hold"] = 1.5
    rig["timing"]["transition"] = 2.0
    rig["themes"]["light"]["background"] = [244, 239, 222]
    rig["themes"]["light"]["far"] = [50, 65, 49, .13]
    rig["themes"]["light"]["shadow"] = [76, 82, 55, .20]
    (HERE / "source" / concept["id"] / "rig.json").write_text(json.dumps(rig, indent=2) + "\n")
    class ReviewGirl(module.Girl):
        def update_hair(self, pose, seconds):
            pass

        def draw_hair(self):
            pass

    module.Girl = ReviewGirl
    width, height, fps = 960, 640, 20
    if inspect:
        girl = ReviewGirl(rig, "light", width, height, fps)
        for label, second in [("standing", 0), ("salute", 4), ("fold", 8), ("dog", 25)]:
            girl.frame(second)
            girl.surface.write_to_png(str(HERE / "source" / concept["id"] / (label + ".png")))
        print("Inspected " + concept["id"], flush=True)
        return
    module.render(rig, "light", module.BUILD, width, height, fps)
    video = module.BUILD / "light/sun-salutation.mp4"
    final = HERE / (concept["id"] + ".webp")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-i", str(video), "-vf", "fps=12,scale=768:512:flags=lanczos",
                    "-c:v", "libwebp_anim", "-lossless", "0", "-quality", "84",
                    "-loop", "0", "-an", str(final)], check=True)
    # MP4 is useful for smooth scrubbing in the grid; WebP is the infinite loop.
    (HERE / (concept["id"] + ".mp4")).write_bytes(video.read_bytes())
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-ss", "1", "-i", str(video), "-frames:v", "1", str(HERE / (concept["id"] + "-preview.png"))], check=True)
    # Twelve evenly spaced held poses demonstrate that this is a full sequence.
    positions = [index * 3.5 + .6 for index in range(12)]
    contact = Image.new("RGB", (1440, 800), "#f4efde")
    girl = ReviewGirl(rig, "light", 960, 640, fps)
    for index, second in enumerate(positions):
        girl.frame(second)
        frame = Image.frombuffer("RGBA", (960, 640), bytes(girl.surface.get_data()), "raw", "BGRA", 0, 1).convert("RGB")
        frame.thumbnail((360, 240), Image.Resampling.LANCZOS)
        x, y = index % 4 * 360, index // 4 * 266
        contact.paste(frame, (x, y))
        ImageDraw.Draw(contact).text((x + 12, y + 242), rig["names"][index], font=font(14), fill="#465b52")
    contact.save(HERE / (concept["id"] + "-sequence.jpg"), quality=92)
    print("Animated " + concept["id"], flush=True)


def review_page():
    cards = []
    montage = Image.new("RGB", (1600, 1216), "#f4efde")
    draw = ImageDraw.Draw(montage)
    for index, concept in enumerate(CONCEPTS):
        filename = concept["id"]
        picture = Image.open(HERE / (filename + "-preview.png")).convert("RGB")
        picture = picture.resize((776, 517), Image.Resampling.LANCZOS)
        x, y = index % 2 * 800 + 12, index // 2 * 600 + 12
        montage.paste(picture, (x, y))
        draw.text((x + 16, y + 525), concept["name"], font=font(28), fill="#315951")
        cards.append(f'<article><h2>{concept["name"]}</h2><video autoplay loop muted playsinline controls poster="{filename}-preview.png"><source src="{filename}.mp4" type="video/mp4"></video><p><a href="{filename}.webp">Looping WebP</a> · <a href="{filename}-sequence.jpg">All twelve poses</a></p></article>')
    montage.save(HERE / "00-proposals-montage.jpg", quality=94)
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Inner Breeze · Character proposals</title>
<style>body{margin:0;padding:28px;background:#f4efde;color:#315951;font:16px/1.5 system-ui}header{max-width:960px;margin:0 auto 24px}h1{font-size:32px;margin:0}p{margin:8px 0}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;max-width:1400px;margin:auto}article{background:#e9e6d5;border:1px solid #c5d4c7;border-radius:16px;overflow:hidden}h2,article p{padding:0 20px}h2{font-size:20px}video{display:block;width:100%}a{color:#285b58}button{background:#315951;color:white;border:0;border-radius:8px;padding:10px 16px;font:inherit;cursor:pointer}@media(max-width:700px){main{grid-template-columns:1fr}body{padding:16px}}</style>
<header><h1>Inner Breeze · Four character proposals</h1><p>Banner-inspired painted characters, two women and two men, all with natural adult anatomy. Each performs a complete twelve-pose sun-salutation loop. Local review only.</p><button id="restart">Restart all loops together</button> <a href="prompts.json">Models and exact prompts</a></header><main>''' + "".join(cards) + '''</main><script>document.querySelector('#restart').onclick=()=>document.querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play()});</script></html>'''
    (HERE / "index.html").write_text(html)
    manifest = json.loads((HERE / "prompts.json").read_text())
    manifest["targeted_refinements"] = []
    for path in sorted((HERE / "source").glob("*-prompt.json")):
        if not any(path.name.startswith(concept["id"] + "-") for concept in CONCEPTS):
            continue
        manifest["targeted_refinements"].append({"source": str(path.relative_to(HERE)), **json.loads(path.read_text())})
    manifest["animation"] = {"sequence": "complete twelve-pose sun salutation", "seconds": 40,
                             "mp4_fps": 20, "webp_fps": 12, "loop": "infinite",
                             "method": "new model-generated parts articulated by the existing pose rig; Cairo frames and FFmpeg encoding"}
    (HERE / "prompts.json").write_text(json.dumps(manifest, indent=2) + "\n")


def export_gif(concept):
    filename = concept["id"]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-i", str(HERE / (filename + ".mp4")), "-filter_complex_threads", "2",
                    "-filter_complex", "fps=12,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a",
                    "-loop", "0", str(HERE / (filename + ".gif"))], check=True)
    print("Exported GIF " + filename, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "generate", "refine", "shoulder", "legfix", "render", "inspect", "gif", "page"])
    parser.add_argument("--concept", type=int)
    args = parser.parse_args()
    concepts = [CONCEPTS[args.concept - 1]] if args.concept else CONCEPTS
    if args.action == "prepare":
        prepare()
    elif args.action == "generate":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(generate, concepts))
    elif args.action == "refine":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(refine_torso, concepts))
    elif args.action == "shoulder":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(repair_shoulder, concepts))
    elif args.action == "legfix":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(fix_leg, concepts))
    elif args.action in ("render", "inspect"):
        for concept in concepts:
            render(concept, inspect=args.action == "inspect")
    elif args.action == "gif":
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(export_gif, concepts))
    elif args.action == "page":
        review_page()


if __name__ == "__main__":
    main()
