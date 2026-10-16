#!/usr/bin/env python3
"""Final cut of the promo film: picture, real app screens, end card, soundtrack.

  compose.py --animatic            storyboard keyframes with slow camera moves
  compose.py --base FILM.mp4       the generated film (16:9, cut to the soundtrack)
  compose.py --short               the 1080x1920 vertical short from short.json

Options: --from S --to S render a range, --still S writes one frame as PNG.
Output goes to build/promo-video/.
"""
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = ROOT / "build/promo-video"
SCREENS = ROOT / "fastlane/metadata/android/en-US/images/phoneScreenshots"
SUN_FRAMES = ROOT / "assets/practices/sunsalutation/characters/01-jade-bun"
WIDTH, HEIGHT, FPS = 1920, 1080, 24
KEYFRAMES = HERE / "keyframes"
APP_BACKGROUND = (245, 248, 246)
APP_TEXT = (31, 42, 40)
NOTO = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
NOTO_MEDIUM = "/usr/share/fonts/truetype/noto/NotoSans-Medium.ttf"
QUICKSAND_BOLD = "/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf"
QUICKSAND_MEDIUM = "/usr/share/fonts/truetype/quicksand/Quicksand-Medium.ttf"

# Phone mockup: screen 486x864 (a 1080x1920 capture at 0.45).
SCREEN_W, SCREEN_H, BEZEL = 486, 864, 16
PHONE_W, PHONE_H = SCREEN_W + 2 * BEZEL, SCREEN_H + 2 * BEZEL
SHADOW_PAD = 60


def font(path, size):
    return ImageFont.truetype(path, size)


def ease_out(value):
    value = min(1.0, max(0.0, value))
    return 1 - (1 - value) ** 3


def ease_in_out(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


@lru_cache(None)
def capture(name):
    return Image.open(SCREENS / f"{name}.png").convert("RGB")


def blank(image, box):
    ImageDraw.Draw(image).rectangle(box, fill=APP_BACKGROUND)


def centered_text(image, text, center_x, top, typeface, fill=APP_TEXT):
    draw = ImageDraw.Draw(image)
    left, upper, right, lower = draw.textbbox((0, 0), text, font=typeface)
    draw.text((center_x - (right - left) / 2 - left, top - upper), text, font=typeface, fill=fill)


@lru_cache(None)
def sun_frame(index):
    return Image.open(SUN_FRAMES / f"02-{index:03d}.png").convert("RGBA")


def sun_salutation_screen(local):
    """The Sun Salutation practice, Step 2 playing with the heroine's frames."""
    screen = capture("04-sun-salutation").copy()
    blank(screen, (300, 500, 800, 1490))
    blank(screen, (420, 222, 680, 268))
    seconds = min(8, 3 + int(local))
    centered_text(screen, f"{seconds}s / 8s", 546, 231, font(NOTO, 36))
    index = 1 + min(89, int(local * 30))
    frame = sun_frame(index)
    scale = 1.93
    frame = frame.resize((round(frame.width * scale), round(frame.height * scale)), Image.LANCZOS)
    screen.paste(frame, (540 - frame.width // 2, 1468 - frame.height), frame)
    return screen


class Clip:
    """Reads a rendered lesson video frame by frame at the film's rate."""

    def __init__(self, path, size, crop=""):
        self.size = size
        self.process = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf",
             f"{crop}fps={FPS},scale={size[0]}:{size[1]}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.last = None

    def next(self):
        raw = self.process.stdout.read(self.size[0] * self.size[1] * 3)
        if len(raw) == self.size[0] * self.size[1] * 3:
            self.last = Image.frombytes("RGB", self.size, raw)
        return self.last


LESSONS = {}


def tai_chi_screen(local, key, title, subtitle, video):
    """Tai Chi lesson in the practice player's layout, playing the painted lesson."""
    if key not in LESSONS:
        LESSONS[key] = Clip(BUILD / "tai-chi" / video, (1080, 1320), "crop=600:733:150:150,")
    screen = capture("04-sun-salutation").copy()
    blank(screen, (290, 40, 800, 160))
    blank(screen, (0, 190, 1080, 1780))
    size = 50
    while ImageDraw.Draw(screen).textlength(title, font=font(NOTO, size)) > 470:
        size -= 2
    centered_text(screen, title, 556, 74 + (50 - size) // 2, font(NOTO, size))
    centered_text(screen, subtitle, 540, 231, font(NOTO, 36))
    frame = LESSONS[key].next()
    if frame is not None:
        screen.paste(frame, (0, 300))
    return screen


def lists_then_diary(local):
    lists, diary = capture("06-lists"), capture("07-diary")
    mix = ease_in_out((local - 2.3) / 0.5)
    return Image.blend(lists, diary, mix) if 0 < mix < 1 else (diary if mix >= 1 else lists)


INSERTS = {
    "01-apps": lambda local: capture("01-apps"),
    "03-practice-home": lambda local: capture("03-practice-home"),
    "04-sun-salutation": sun_salutation_screen,
    "tai-chi-monk": lambda local: tai_chi_screen(local, "monk", "Wave Hands Like Clouds", "Lesson 4 · Move 10 of 24",
                                                 "monk-cloud-hands.mp4"),
    "tai-chi-woman": lambda local: tai_chi_screen(local, "dolma", "Brush Knee and Push", "Lesson 2 · Move 4 of 24",
                                                  "dolma-brush-knee.mp4"),
    "05-habits": lambda local: capture("05-habits"),
    "07-diary": lists_then_diary,
    "02-lumi-customize": lambda local: capture("02-lumi-customize"),
}


@lru_cache(None)
def phone_parts():
    def rounded(size, radius, fill):
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(image).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill)
        return image

    body = rounded((PHONE_W, PHONE_H), 68, (22, 24, 27, 255))
    rim = Image.new("RGBA", (PHONE_W, PHONE_H), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle((1, 1, PHONE_W - 2, PHONE_H - 2), 67, outline=(92, 98, 104, 255), width=2)
    body.alpha_composite(rim)
    mask = rounded((SCREEN_W, SCREEN_H), 52, (255, 255, 255, 255)).getchannel("A")
    shadow = Image.new("RGBA", (PHONE_W + 2 * SHADOW_PAD, PHONE_H + 2 * SHADOW_PAD), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (SHADOW_PAD, SHADOW_PAD + 22, SHADOW_PAD + PHONE_W, SHADOW_PAD + PHONE_H + 22), 68, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    return body, mask, shadow


def phone(screen):
    body, mask, shadow = phone_parts()
    out = shadow.copy()
    device = body.copy()
    content = screen.resize((SCREEN_W, SCREEN_H), Image.LANCZOS).convert("RGBA")
    content.putalpha(mask)
    device.alpha_composite(content, (BEZEL, BEZEL))
    out.alpha_composite(device, (SHADOW_PAD, SHADOW_PAD))
    return out


def place_phone(frame, device, side, local, length):
    enter = ease_out(local / 0.6)
    leave = ease_in_out((local - (length - 0.45)) / 0.45)
    alpha = enter * (1 - leave)
    if alpha <= 0:
        return
    float_y = 6 * math.sin(2 * math.pi * local / 4.5)
    if side == "bottom":
        # Vertical short: lower centre, left of TikTok's buttons, rising in.
        x = round(480 - device.width / 2)
        y = round(1590 - PHONE_H - SHADOW_PAD + float_y + 240 * (1 - enter) + 90 * leave)
    elif side == "center":
        # An app reveal: the scene softens behind a phone rising into the middle.
        soft = frame.filter(ImageFilter.GaussianBlur(16 * alpha))
        dark = Image.new("RGBA", frame.size, (8, 12, 24, round(110 * alpha)))
        soft.alpha_composite(dark)
        frame.paste(soft)
        x = round(WIDTH / 2 - device.width / 2)
        y = round(HEIGHT / 2 - device.height / 2 + 8 + float_y + 160 * (1 - enter) + 60 * leave)
    else:
        direction = 1 if side == "right" else -1
        shift = direction * (220 * (1 - enter) + 90 * leave)
        center_x = 1480 if side == "right" else 440
        x = round(center_x - device.width / 2 + shift)
        y = round(HEIGHT / 2 - device.height / 2 + 8 + float_y)
    if alpha < 1:
        device = device.copy()
        device.putalpha(device.getchannel("A").point(lambda value: round(value * alpha)))
    frame.alpha_composite(device, (x, y))


@lru_cache(None)
def end_card():
    card = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shade = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    rows = np.linspace(0, 1, HEIGHT)
    title = np.clip(1 - np.abs(rows - 0.42) / 0.5, 0, 1) ** 1.4 * 150
    footer = np.clip((rows - 0.7) / 0.3, 0, 1) ** 1.2 * 200
    shade[..., 3] = np.maximum(title, footer)[:, None]
    shade[..., :3] = (6, 12, 30)
    card.alpha_composite(Image.fromarray(shade, "RGBA"))
    logo = Image.open(ROOT / "assets/app/source-icon.png").convert("RGBA").resize((300, 300), Image.LANCZOS)
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((WIDTH / 2 - 190, 120, WIDTH / 2 + 190, 460), fill=(255, 214, 140, 70))
    card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    card.alpha_composite(logo, (WIDTH // 2 - 150, 135))
    centered_text(card, "Inner Breeze", WIDTH / 2, 460, font(QUICKSAND_BOLD, 118), (255, 250, 238, 255))
    centered_text(card, "Breathe  ·  Move  ·  Grow", WIDTH / 2, 610, font(QUICKSAND_MEDIUM, 46), (247, 220, 160, 255))
    badges = [Image.open(ROOT / f"assets/app/badge-{name}.png").convert("RGBA") for name in ("google-play", "f-droid")]
    badges = [badge.resize((round(badge.width * 92 / badge.height), 92), Image.LANCZOS) for badge in badges]
    gap = 28
    total = sum(badge.width for badge in badges) + gap
    x = WIDTH // 2 - total // 2
    for badge in badges:
        card.alpha_composite(badge, (x, 860))
        x += badge.width + gap
    centered_text(card, "Free, private and open source  ·  also on the web at inbe.waozi.xyz", WIDTH / 2, 985,
                  font(QUICKSAND_MEDIUM, 30), (232, 236, 246, 255))
    return card


@lru_cache(None)
def end_card_vertical():
    card = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shade = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    rows = np.linspace(0, 1, HEIGHT)
    title = np.clip(1 - np.abs(rows - 0.33) / 0.3, 0, 1) ** 1.4 * 150
    footer = np.clip(1 - np.abs(rows - 0.7) / 0.14, 0, 1) ** 1.2 * 170
    shade[..., 3] = np.maximum(title, footer)[:, None]
    shade[..., :3] = (6, 12, 30)
    card.alpha_composite(Image.fromarray(shade, "RGBA"))
    center = 520
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((center - 210, 300, center + 210, 680), fill=(255, 214, 140, 70))
    card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    logo = Image.open(ROOT / "assets/app/source-icon.png").convert("RGBA").resize((330, 330), Image.LANCZOS)
    card.alpha_composite(logo, (center - 165, 330))
    centered_text(card, "Inner Breeze", center, 720, font(QUICKSAND_BOLD, 124), (255, 250, 238, 255))
    centered_text(card, "Breathe  ·  Move  ·  Grow", center, 880, font(QUICKSAND_MEDIUM, 50), (247, 220, 160, 255))
    badges = [Image.open(ROOT / f"assets/app/badge-{name}.png").convert("RGBA") for name in ("google-play", "f-droid")]
    badges = [badge.resize((round(badge.width * 100 / badge.height), 100), Image.LANCZOS) for badge in badges]
    gap = 26
    x = center - (sum(badge.width for badge in badges) + gap) // 2
    for badge in badges:
        card.alpha_composite(badge, (x, 1270))
        x += badge.width + gap
    centered_text(card, "Free, private and open source", center, 1410, font(QUICKSAND_MEDIUM, 40), (232, 236, 246, 255))
    return card


def keyframe(shot):
    image = Image.open(KEYFRAMES / f"shot-{shot:02d}.jpg").convert("RGB")
    if image.width * HEIGHT > image.height * WIDTH:
        band = round(image.height * WIDTH / HEIGHT)
        left = (image.width - band) // 2
        return image.crop((left, 0, left + band, image.height))
    band = round(image.width * HEIGHT / WIDTH)
    top = (image.height - band) // 2
    return image.crop((0, top, image.width, top + band))


@lru_cache(None)
def keyframe_big(shot):
    return keyframe(shot).resize((round(WIDTH * 1.12), round(HEIGHT * 1.12)), Image.LANCZOS)


def animatic_frame(film, time):
    clip = next(clip for clip in film["clips"] if clip["start"] <= time < clip["end"] + 1e-6)
    local = (time - clip["start"]) / (clip["end"] - clip["start"])
    name = [name for name, at in clip["keyframes"] if at <= time - clip["start"]][-1]
    big = keyframe_big(int(name[5:]))
    zoom = 1.12 - 0.08 * (1 - local) if clip["clip"] % 2 else 1.04 + 0.08 * (1 - local)
    w, h = round(WIDTH * zoom), round(HEIGHT * zoom)
    drift = (big.width - w) * (0.35 + 0.3 * local)
    crop = big.crop((round(drift), round((big.height - h) / 2), round(drift) + w, round((big.height - h) / 2) + h))
    return crop.resize((WIDTH, HEIGHT), Image.BILINEAR)


def insert_screen(insert, local):
    """The insert's screen at this moment; one phone can change screens."""
    screens = insert.get("screens") or [[insert["screen"], 0.0]]
    current = [index for index, (name, at) in enumerate(screens) if at <= local][-1]
    screen = INSERTS[screens[current][0]](local - screens[current][1])
    if current > 0:
        mix = ease_in_out((local - screens[current][1]) / 0.35)
        if mix < 1:
            previous = INSERTS[screens[current - 1][0]](local - screens[current - 1][1])
            screen = Image.blend(previous.convert("RGB"), screen.convert("RGB"), mix)
    return screen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--animatic", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", type=float)
    parser.add_argument("--still", type=float)
    parser.add_argument("--short", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    global WIDTH, HEIGHT, KEYFRAMES
    if args.short:
        WIDTH, HEIGHT, KEYFRAMES = 1080, 1920, HERE / "keyframes-vertical"
    film = json.loads((HERE / ("short.json" if args.short else "film.json")).read_text())
    length = film["format"]["length"]
    end = args.end if args.end is not None else length
    name = "inner-breeze-a-day-with-lumi" + ("-short" if args.short else "-animatic" if args.animatic else "")
    soundtrack = BUILD / ("audio/short-soundtrack.wav" if args.short else "audio/soundtrack.wav")
    card_at = film.get("end_card", 59.0)
    out = Path(args.out) if args.out else BUILD / f"{name}.mp4"
    base = None
    if args.base:
        base = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(args.start), "-i", args.base, "-vf",
                                 f"fps={FPS},scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1", "-f", "rawvideo",
                                 "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    writer = None
    if args.still is None:
        writer = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
             "-r", str(FPS), "-i", "-", "-ss", str(args.start), "-to", str(end),
             "-i", str(soundtrack), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset",
             "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
             "-shortest", str(out)], stdin=subprocess.PIPE)
    first = round(args.start * FPS)
    last = round(end * FPS) if args.still is None else first
    if args.still is not None:
        first = last = round(args.still * FPS)
    for index in range(first, last + (1 if args.still is not None else 0)):
        time = index / FPS
        if base:
            raw = base.stdout.read(WIDTH * HEIGHT * 3)
            if len(raw) < WIDTH * HEIGHT * 3:
                break
            frame = Image.frombytes("RGB", (WIDTH, HEIGHT), raw).convert("RGBA")
        else:
            frame = animatic_frame(film, time).convert("RGBA")
        for insert in film["inserts"]:
            start, stop = insert["from"], insert["to"]
            if start <= time < stop:
                device = phone(insert_screen(insert, time - start))
                place_phone(frame, device, insert["side"], time - start, stop - start)
        if time >= card_at:
            card = end_card_vertical() if args.short else end_card()
            fade = ease_in_out((time - card_at) / 0.9)
            if fade < 1:
                card = card.copy()
                card.putalpha(card.getchannel("A").point(lambda value: round(value * fade)))
            frame.alpha_composite(card)
        fade_in = ease_in_out(time / 0.9)
        fade_out = ease_in_out((length - time) / 0.8)
        level = min(fade_in, fade_out)
        rgb = frame.convert("RGB")
        if level < 1:
            rgb = Image.blend(Image.new("RGB", rgb.size, (0, 0, 0)), rgb, level)
        if writer:
            writer.stdin.write(rgb.tobytes())
        else:
            path = BUILD / f"still-{args.still:05.2f}.png"
            rgb.save(path)
            print(path)
    if writer:
        writer.stdin.close()
        writer.wait()
        print(out)


if __name__ == "__main__":
    main()
