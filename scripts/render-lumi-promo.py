#!/usr/bin/env python3
"""Render a captioned Lumi tour using the exact visually reviewed captures."""
import argparse
from collections import deque
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "design/lumi-promo"
OUTPUT = ROOT / "build/lumi-promo"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FLIGHT_SECONDS = 1.35
WING_FRAMES_PER_SECOND = 16
FLIGHT_TARGETS = [(.5, .48), (.85, .66), (.85, .54), (.85, .66),
                  (.85, .58), (.85, .65), (.5, .48)]
STORY = [
    (0, 4, "Hi, I’m Lumi.", "Follow a little light.", None),
    (4, 8, "A world of your own", "Your apps. Your daily rhythm.", "01-apps"),
    (8, 12, "Make space to breathe", "Breathe, meditate, move.", "03-practice-home"),
    (12, 16, "Small steps, brighter days", "Habits that grow with you.", "05-habits"),
    (16, 20, "Keep what matters", "Lists for plans. Diary for thoughts.", "07-diary"),
    (20, 26, "Just ask Lumi", "Change your theme through chat.", "02-lumi-customize"),
    (26, 30, "Inner Breeze", "Make it yours, one little spark at a time.", None),
]


def text_center(draw, text, y, font, fill, width):
    length = draw.textbbox((0, 0), text, font=font)[2]
    draw.text(((width - length) / 2, y), text, font=font, fill=fill)


def ease(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def narrated_story(path):
    """Leave each spoken line enough time; never trim speech to fit a card."""
    config_path = ASSETS / "narration.json"
    narration = json.loads((ASSETS / "narration/receipt.json").read_text())
    assert narration["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert len(narration["clips"]) == len(STORY)
    rate = 48000
    story = []
    clips = []
    start = 0.0
    for beat, row in zip(STORY, narration["clips"]):
        audio = ASSETS / "narration" / row["file"]
        assert hashlib.sha256(audio.read_bytes()).hexdigest() == row["sha256"], "Narration changed; regenerate its receipt"
        raw = subprocess.check_output([
            "ffmpeg", "-v", "error", "-i", str(audio), "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(rate), "-ac", "1",
            "-f", "f32le", "pipe:1"])
        samples = np.frombuffer(raw, dtype="<f4")
        end = start + max(beat[1] - beat[0], len(samples) / rate + .65)
        story.append((start, end, *beat[2:]))
        clips.append((round((start + .25) * rate), samples))
        start = end
    sound = np.zeros(math.ceil(start * rate), dtype=np.float32)
    for offset, samples in clips:
        sound[offset:offset + len(samples)] = samples
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes((np.clip(sound, -1, 1) * 32767).astype("<i2").tobytes())
    return story, start, narration


def animation_frames():
    """Slice the generated cycle and align eyes to avoid registration jitter."""
    atlas = Image.open(ASSETS / "lumi-flight-cycle.png").convert("RGBA")
    assert atlas.getchannel("A").getextrema() == (0, 255), "Lumi needs true transparency"
    tiles = []
    anchors = []
    side = round(atlas.width / 4)
    for index in range(8):
        column, row = index % 4, index // 4
        box = (round(column * atlas.width / 4), round(row * atlas.height / 2),
               round((column + 1) * atlas.width / 4), round((row + 1) * atlas.height / 2))
        tile = atlas.crop(box).resize((side, side), Image.Resampling.LANCZOS)
        pixels = np.asarray(tile)
        eyes = ((pixels[:, :, 0] < 65) & (pixels[:, :, 1] < 65) &
                (pixels[:, :, 2] < 60) & (pixels[:, :, 3] > 220))
        eyes[:int(side * .28)] = False
        eyes[int(side * .66):] = False
        eyes[:, :int(side * .38)] = False
        eyes[:, int(side * .81):] = False
        ys, xs = np.nonzero(eyes)
        assert len(xs) > 100, "Animation frame has no stable eye anchor"
        anchors.append((float(xs.mean()), float(ys.mean())))
        tiles.append(tile)
    target = np.mean(anchors, axis=0)
    aligned = []
    for tile, anchor in zip(tiles, anchors):
        canvas = Image.new("RGBA", tile.size)
        canvas.alpha_composite(tile, (round(target[0] - anchor[0]), round(target[1] - anchor[1])))
        aligned.append(canvas)
    return aligned


def flight_position(index, local, width, height):
    """Fly to a destination, settle there, then move when the scene changes."""
    origin = (-.3, .58) if index == 0 else FLIGHT_TARGETS[index - 1]
    target = FLIGHT_TARGETS[index]
    progress = ease(local / FLIGHT_SECONDS)
    x = origin[0] + (target[0] - origin[0]) * progress
    y = origin[1] + (target[1] - origin[1]) * progress
    y -= math.sin(progress * math.pi) * .045
    return x * width, y * height, progress


def flight_facing(index, local):
    """Face the flight direction, then turn inward beside the app screen."""
    origin_x = -.3 if index == 0 else FLIGHT_TARGETS[index - 1][0]
    target_x = FLIGHT_TARGETS[index][0]
    previous = -1.0 if origin_x > .5 else 1.0
    if target_x > origin_x:
        traveling = 1.0
    elif target_x < origin_x:
        traveling = -1.0
    else:
        traveling = previous
    settled = -1.0 if target_x > .5 else traveling
    facing = previous + (traveling - previous) * ease(local / .28)
    turn = ease((local - FLIGHT_SECONDS) / .28)
    return facing + (settled - facing) * turn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    args = parser.parse_args()
    assert args.width % 2 == args.height % 2 == 0 and args.fps > 0
    spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts/screenshot-harness.py")
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    captured = harness.verify(reviewed=True, current=False)
    lookup = {row["slug"]: harness.OUTPUT / row["file"] for row in captured["rows"] if row["bucket"] == "phone"}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    width, height = args.width, args.height
    scale = width / 1080
    background = Image.open(ASSETS / "forest.png").convert("RGB")
    background = ImageOps.fit(background, (width, height)).convert("RGBA")
    shade = Image.new("RGBA", (width, height), (3, 19, 20, 90))
    background = Image.alpha_composite(background, shade)
    sprites = animation_frames()
    title_font = ImageFont.truetype(BOLD, int(54 * scale))
    small_font = ImageFont.truetype(FONT, int(29 * scale))
    brand_font = ImageFont.truetype(FONT, int(23 * scale))
    card_width = int(width * .65)
    card_height = round(card_width * 1920 / 1080)
    cards = {}
    for name, path in lookup.items():
        picture = Image.open(path).convert("RGBA").resize((card_width, card_height), Image.Resampling.LANCZOS)
        mask = Image.new("L", picture.size)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_width - 1, card_height - 1), radius=int(36 * scale), fill=255)
        picture.putalpha(mask)
        cards[name] = picture
    randomizer = random.Random(42)
    motes = [(randomizer.random(), randomizer.random(), randomizer.uniform(.4, 1.4), randomizer.random() * math.tau) for _ in range(70)]
    audio = OUTPUT / "lumi-narration.wav"
    story, seconds, narration = narrated_story(audio)
    destination = OUTPUT / "inner-breeze-lumi-review.mp4"
    staged = OUTPUT / "inner-breeze-lumi-rendering.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{width}x{height}", "-framerate", str(args.fps), "-i", "pipe:0", "-i", str(audio), "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(staged)]
    review_frames = []
    trail = deque(maxlen=24)
    with (OUTPUT / "render.log").open("w") as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame in range(math.ceil(seconds * args.fps)):
                time = frame / args.fps
                index, beat = next((i, beat) for i, beat in enumerate(story) if beat[0] <= time < beat[1])
                start, end, title, subtitle, scene = beat
                local = time - start
                canvas = background.copy()
                draw = ImageDraw.Draw(canvas, "RGBA")
                for x, y, speed, phase in motes:
                    px = int((x + .018 * math.sin(time * speed + phase)) * width)
                    py = int(((y - time * speed * .013) % 1) * height)
                    radius = max(1, int((2 + math.sin(time * 2 + phase)) * scale))
                    draw.ellipse((px - radius * 3, py - radius * 3, px + radius * 3, py + radius * 3), fill=(238, 222, 148, 15))
                    draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=(255, 239, 185, 160))
                text_center(draw, "I N N E R   B R E E Z E", int(104 * scale), brand_font, "#c6d9c4", width)
                text_center(draw, title, int(205 * scale), title_font, "#fff7dc", width)
                text_center(draw, subtitle, int(290 * scale), small_font, "#dfe9d8", width)
                if scene:
                    card = cards[scene]
                    if index == 5:
                        card = Image.blend(cards["09-lumi-light"], cards[scene], ease((local / (end - start) - .43) / .14))
                    left = (width - card_width) // 2
                    top = int(410 * scale)
                    shadow = Image.new("RGBA", canvas.size)
                    ImageDraw.Draw(shadow).rounded_rectangle((left - 12, top - 12, left + card_width + 12, top + card_height + 12), radius=int(48 * scale), fill=(193, 218, 150, 115))
                    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(int(22 * scale))))
                    canvas.alpha_composite(card, (left, top))
                center_x, center_y, progress = flight_position(index, local, width, height)
                previous_size = 570 if index <= 1 else 285
                target_size = 570 if index in (0, 6) else 285
                character_size = int((previous_size + (target_size - previous_size) * progress) * scale)
                draw = ImageDraw.Draw(canvas, "RGBA")
                trail.append((center_x, center_y))
                for age, (px, py) in enumerate(trail):
                    if math.hypot(px - center_x, py - center_y) > 8 * scale:
                        radius = (1 + age / len(trail) * 2) * scale
                        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=(255, 222, 122, int(100 * age / len(trail))))
                phase = (time * WING_FRAMES_PER_SECOND) % len(sprites)
                pose = int(phase)
                character = sprites[pose]
                facing = flight_facing(index, local)
                if facing < 0:
                    character = ImageOps.mirror(character)
                character_width = max(2, round(character_size * abs(facing)))
                character = character.resize((character_width, character_size), Image.Resampling.LANCZOS)
                glow = Image.new("RGBA", canvas.size)
                glow_draw = ImageDraw.Draw(glow)
                radius = character_size * .31
                glow_draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=(255, 212, 105, 75))
                canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(int(42 * scale))))
                canvas.alpha_composite(character, (int(center_x - character.width / 2), int(center_y - character.height / 2)))
                if index == 5:
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    pill = "theme forest" if local / (end - start) < .5 else "/dark"
                    label_font = ImageFont.truetype(BOLD, int(32 * scale))
                    pill_width = int(draw.textlength(pill, font=label_font) + 70 * scale)
                    left = (width - pill_width) // 2
                    draw.rounded_rectangle((left, int(1670 * scale), left + pill_width, int(1760 * scale)), radius=int(35 * scale), fill=(231, 239, 210, 245))
                    text_center(draw, pill, int(1693 * scale), label_font, "#214332", width)
                if index == 6:
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    text_center(draw, "Breathe · Grow · Make it yours", int(1390 * scale), small_font, "#fff0c2", width)
                fade = min(ease(time / .5), ease((seconds - time) / .8))
                if fade < 1:
                    canvas = Image.blend(Image.new("RGBA", canvas.size, "#071c1b"), canvas, fade)
                if abs(local - 1.8) < .5 / args.fps:
                    path = OUTPUT / f"review-{index:02}.jpg"
                    canvas.convert("RGB").save(path, quality=93)
                    review_frames.append(path)
                encoder.stdin.write(canvas.convert("RGB").tobytes())
                if frame % (args.fps * 4) == 0:
                    print(f"Rendered {time:.0f}/{seconds:.1f} seconds", flush=True)
        finally:
            encoder.stdin.close()
        assert encoder.wait() == 0, "video encoding failed; inspect render.log"
    harness.verify(reviewed=True, current=False)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(staged)], text=True))
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"]) == (width, height) and video["codec_name"] == "h264"
    assert abs(float(probe["format"]["duration"]) - seconds) < .2
    assert any(stream["codec_type"] == "audio" for stream in probe["streams"])
    sheet = Image.new("RGB", (280 * len(review_frames), 500), "#09221d")
    for index, path in enumerate(review_frames):
        picture = Image.open(path)
        picture.thumbnail((280, 500))
        sheet.paste(picture, (index * 280, 0))
    sheet.save(OUTPUT / "storyboard.jpg", quality=95)
    staged.replace(destination)
    receipt = dict(
        capture_sha256=harness.digest(harness.OUTPUT / "capture.json"),
        artwork={name: harness.digest(ASSETS / name)
                 for name in ("lumi-flight-cycle.png", "forest.png")},
        video_sha256=harness.digest(destination),
        seconds=seconds,
        width=width,
        height=height,
        fps=args.fps,
        status="owner-review",
        soundtrack="OpenRouter narrator only; no music or sound effects",
        narration_sha256=harness.digest(ASSETS / "narration/receipt.json"),
        narrator=dict(provider=narration["provider"], model=narration["model"],
                      voice=narration["voice"]),
        animation_frames=len(sprites),
        wing_frames_per_second=WING_FRAMES_PER_SECOND,
        screen_motion="Fixed card position; one app screen per scene",
        facing="Flight direction while traveling; inward toward the app while settled on its right",
        renderer_sha256=harness.digest(Path(__file__)),
        story=story,
    )
    harness.write_json(OUTPUT / "render-receipt.json", receipt)
    audio.unlink()
    print(f"Review video saved: {destination}")


if __name__ == "__main__":
    main()
