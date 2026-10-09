#!/usr/bin/env python3
"""Render a captioned Lumi tour using the exact visually reviewed captures."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "design/lumi-promo"
OUTPUT = ROOT / "build/lumi-promo"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
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


def soundtrack(path, seconds):
    """An original quiet bell bed, synthesized here; no licensed music."""
    rate = 48000
    time = np.arange(seconds * rate) / rate
    sound = np.zeros_like(time)
    for at, frequency in [(0, 261.63), (4, 329.63), (8, 392), (12, 523.25), (16, 392), (20, 329.63), (23, 523.25), (26, 261.63), (27, 392)]:
        offset = time - at
        active = offset >= 0
        envelope = np.exp(-np.maximum(offset, 0) / 2.7) * np.minimum(np.maximum(offset, 0) * 12, 1)
        sound += active * envelope * (np.sin(2 * math.pi * frequency * offset) + .22 * np.sin(2 * math.pi * frequency * 2.01 * offset)) * .075
    sound *= np.minimum(time, 1) * np.minimum(np.maximum(seconds - time, 0), 1)
    stereo = np.stack([sound, sound * .94], axis=1)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes((stereo * 32767).astype("<i2").tobytes())


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
    from PIL import ImageOps
    background = ImageOps.fit(background, (width, height)).convert("RGBA")
    shade = Image.new("RGBA", (width, height), (3, 19, 20, 90))
    background = Image.alpha_composite(background, shade)
    lumi = Image.open(ASSETS / "lumi-flight.png").convert("RGBA")
    assert lumi.getchannel("A").getextrema() == (0, 255), "Lumi needs true transparency"
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
    audio = OUTPUT / "lumi-bells.wav"
    soundtrack(audio, 30)
    destination = OUTPUT / "inner-breeze-lumi-review.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{width}x{height}", "-framerate", str(args.fps), "-i", "pipe:0", "-i", str(audio), "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(destination)]
    review_frames = []
    with (OUTPUT / "render.log").open("w") as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame in range(30 * args.fps):
                time = frame / args.fps
                start, end, title, subtitle, scene = next(beat for beat in STORY if beat[0] <= time < beat[1])
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
                    if start == 20:
                        card = Image.blend(cards["09-lumi-light"], cards[scene], ease((local - 2.5) / .8))
                    left = (width - card_width) // 2
                    top = int(410 * scale + 12 * scale * math.sin(time * .8))
                    top += int((1 - ease(local / .7)) * 130 * scale)
                    shadow = Image.new("RGBA", canvas.size)
                    ImageDraw.Draw(shadow).rounded_rectangle((left - 12, top - 12, left + card_width + 12, top + card_height + 12), radius=int(48 * scale), fill=(193, 218, 150, 115))
                    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(int(22 * scale))))
                    canvas.alpha_composite(card, (left, top))
                    # An orbiting guide and a glowing trail reveal each screen.
                    progress = min(local / (end - start), 1)
                    center_x = width * (.79 - .13 * math.sin(progress * math.pi))
                    center_y = height * (.72 - .37 * progress)
                    character_size = int(260 * scale)
                else:
                    center_x = width * .5 + width * .13 * math.sin(local * 1.05)
                    center_y = height * (.48 + .025 * math.sin(time * 2.2))
                    character_size = int((570 if start == 0 else 500) * scale)
                draw = ImageDraw.Draw(canvas, "RGBA")
                for tail in range(32, 0, -1):
                    px = center_x - tail * 5 * scale
                    py = center_y + math.sin(time * 4 - tail * .14) * 18 * scale + tail * scale
                    radius = (4 - tail / 12) * scale
                    draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=(255, 222, 122, int(120 * (1 - tail / 33))))
                character = lumi.resize((character_size, character_size), Image.Resampling.LANCZOS)
                character = character.rotate(5 * math.sin(time * 3), resample=Image.Resampling.BICUBIC, expand=True)
                glow = Image.new("RGBA", canvas.size)
                glow_draw = ImageDraw.Draw(glow)
                radius = character_size * .31
                glow_draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=(255, 212, 105, 75))
                canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(int(42 * scale))))
                canvas.alpha_composite(character, (int(center_x - character.width / 2), int(center_y - character.height / 2)))
                if start == 16 and local < 1.6:
                    thumbnail = cards["06-lists"].resize((int(width * .33), int(height * .33)), Image.Resampling.LANCZOS)
                    canvas.alpha_composite(thumbnail, (int(width * .03), int(height * .5)))
                if start == 20:
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    pill = "theme forest" if local < 3 else "/dark"
                    label_font = ImageFont.truetype(BOLD, int(32 * scale))
                    pill_width = int(draw.textlength(pill, font=label_font) + 70 * scale)
                    left = (width - pill_width) // 2
                    draw.rounded_rectangle((left, int(1670 * scale), left + pill_width, int(1760 * scale)), radius=int(35 * scale), fill=(231, 239, 210, 245))
                    text_center(draw, pill, int(1693 * scale), label_font, "#214332", width)
                if start == 26:
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    text_center(draw, "Breathe · Grow · Make it yours", int(1390 * scale), small_font, "#fff0c2", width)
                fade = min(ease(time / .5), ease((30 - time) / .8))
                if fade < 1:
                    canvas = Image.blend(Image.new("RGBA", canvas.size, "#071c1b"), canvas, fade)
                if abs(local - 1.5) < .5 / args.fps:
                    path = OUTPUT / f"review-{start:02}.jpg"
                    canvas.convert("RGB").save(path, quality=93)
                    review_frames.append(path)
                encoder.stdin.write(canvas.convert("RGB").tobytes())
                if frame % (args.fps * 4) == 0:
                    print(f"Rendered {time:.0f}/30 seconds", flush=True)
        finally:
            encoder.stdin.close()
        assert encoder.wait() == 0, "video encoding failed; inspect render.log"
    harness.verify(reviewed=True, current=False)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(destination)], text=True))
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"]) == (width, height) and video["codec_name"] == "h264"
    assert abs(float(probe["format"]["duration"]) - 30) < .2
    assert any(stream["codec_type"] == "audio" for stream in probe["streams"])
    sheet = Image.new("RGB", (280 * len(review_frames), 500), "#09221d")
    for index, path in enumerate(review_frames):
        picture = Image.open(path)
        picture.thumbnail((280, 500))
        sheet.paste(picture, (index * 280, 0))
    sheet.save(OUTPUT / "storyboard.jpg", quality=95)
    receipt = dict(capture_sha256=harness.digest(harness.OUTPUT / "capture.json"), artwork={name: harness.digest(ASSETS / name) for name in ("lumi-flight.png", "forest.png")}, video_sha256=harness.digest(destination), seconds=30, width=width, height=height, fps=args.fps, status="owner-review", soundtrack="original synthesized bells", story=STORY)
    harness.write_json(OUTPUT / "render-receipt.json", receipt)
    audio.unlink()
    print(f"Review video saved: {destination}")


if __name__ == "__main__":
    main()
