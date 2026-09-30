#!/usr/bin/env python3
"""Cut the generated sun salutation video into poses and transitions.

Frame numbers are zero-based at 24 fps. Hold frames were picked where the
frame-to-frame motion is lowest. The generated video is not tracked; put it
here as source.mp4 first, then run:

    python3 design/sun-salutation/generated-video-cut/cut.py

Writes poses/*.png, clips/*.mp4, stand-ins/*.mp4 and coverage.png under
build/sun-salutation-cut/.
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source.mp4"
OUTPUT = HERE.parents[2] / "build/sun-salutation-cut"
FPS = 24

# Held poses found in the video: name -> frame.
HOLDS = {
    "mountain-prayer": 13,
    "upward-salute": 41,
    "forward-fold": 72,
    "low-lunge": 96,
    "plank": 127,
    "upward-dog": 165,
    "downward-dog": 204,
    "forward-fold-return": 226,
}

# Continuous segments, hold to hold. The last one is cut off by the video end.
CLIPS = [
    ("01-mountain-to-upward-salute", 13, 41),
    ("02-upward-salute-to-forward-fold", 41, 72),
    ("03-forward-fold-to-low-lunge", 72, 96),
    ("04-low-lunge-to-plank", 96, 127),
    ("05-plank-to-upward-dog-skips-low-plank", 127, 165),
    ("07-upward-dog-to-downward-dog", 165, 204),
    ("08-downward-dog-walk-in-to-forward-fold", 204, 226),
    ("10-forward-fold-starts-rising-cut-off", 226, 239),
]

# Return-half transitions made by playing the first half backwards.
STAND_INS = [
    ("10-forward-fold-to-upward-salute-reversed", 41, 72),
    ("11-upward-salute-to-mountain-reversed", 13, 41),
]

# The app's twelve steps (locales/en.txt) and what the video has for each.
# status: have, near (usable but not the named pose), missing.
STEPS = [
    ("Mountain pose", "mountain-prayer", "have", "prayer hands"),
    ("Upward salute", "upward-salute", "have", ""),
    ("Standing forward fold", "forward-fold", "have", ""),
    ("Half lift", "low-lunge", "near", "video does a low lunge"),
    ("Plank", "plank", "have", "toes cut by frame edge"),
    ("Low plank", None, "missing", "arms never bend"),
    ("Upward-facing dog", "upward-dog", "near", "thighs on floor, cobra-like"),
    ("Downward-facing dog", "downward-dog", "have", ""),
    ("Half lift", None, "missing", "walks feet in to fold"),
    ("Standing forward fold", "forward-fold-return", "have", ""),
    ("Upward salute", "upward-salute", "near", "only by reversing step 2"),
    ("Mountain pose", "mountain-prayer", "near", "only by reversing step 1"),
]

STATUS_COLORS = {
    "have": (46, 125, 50),
    "near": (191, 120, 0),
    "missing": (198, 40, 40),
}
STATUS_TEXT = {"have": "HAVE", "near": "NEAR", "missing": "MISSING"}


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def frame_filter(first, last):
    return f"select='between(n,{first},{last})',setpts=N/{FPS}/TB"


def encode(name, first, last, folder, reverse=False):
    vf = frame_filter(first, last)
    if reverse:
        vf += ",reverse"
    ffmpeg("-i", str(SOURCE), "-vf", vf, "-an", "-r", str(FPS),
           "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
           str(folder / f"{name}.mp4"))


def font(size, bold=False):
    name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/noto/{name}", size)


def coverage_sheet(poses):
    tile_w, tile_h, label_h = 240, 300, 86
    cols, rows = 6, 2
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h)),
                      (250, 249, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (title, pose, status, note) in enumerate(STEPS):
        x = (index % cols) * tile_w
        y = (index // cols) * (tile_h + label_h)
        color = STATUS_COLORS[status]
        if pose:
            image = Image.open(poses / f"{pose}.png").convert("RGB")
            # The figure lives in the lower 540 px of the 360x640 frame.
            image = image.crop((0, 100, 360, 640))
            image.thumbnail((tile_w - 12, tile_h - 12))
            if status == "near":
                image = Image.blend(image, Image.new("RGB", image.size,
                                    (250, 249, 246)), 0.25)
            sheet.paste(image, (x + (tile_w - image.width) // 2,
                                y + (tile_h - image.height) // 2))
        else:
            draw.line((x + 60, y + 90, x + tile_w - 60, y + tile_h - 90),
                      fill=color, width=6)
            draw.line((x + tile_w - 60, y + 90, x + 60, y + tile_h - 90),
                      fill=color, width=6)
        draw.rectangle((x + 3, y + 3, x + tile_w - 4, y + tile_h + label_h - 4),
                       outline=color, width=3)
        ly = y + tile_h
        draw.text((x + 12, ly), f"{index + 1}. {title}", fill=(30, 30, 30),
                  font=font(17, bold=True))
        draw.text((x + 12, ly + 26), STATUS_TEXT[status], fill=color,
                  font=font(16, bold=True))
        if note:
            draw.text((x + 12, ly + 50), note, fill=(90, 90, 90), font=font(14))
    sheet.save(OUTPUT / "coverage.png")


def main():
    poses = OUTPUT / "poses"
    clips = OUTPUT / "clips"
    stand_ins = OUTPUT / "stand-ins"
    for folder in (poses, clips, stand_ins):
        folder.mkdir(parents=True, exist_ok=True)
    for name, frame in HOLDS.items():
        ffmpeg("-i", str(SOURCE), "-vf", f"select='eq(n,{frame})'",
               "-frames:v", "1", str(poses / f"{name}.png"))
    for name, first, last in CLIPS:
        encode(name, first, last, clips)
    for name, first, last in STAND_INS:
        encode(name, first, last, stand_ins, reverse=True)
    coverage_sheet(poses)


if __name__ == "__main__":
    main()
