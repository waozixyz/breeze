#!/usr/bin/env python3
"""Validate every current proposal and replace stale review measurements."""
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_frames:format=duration",
            "-show_chapters", "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def frame_stats(path):
    with Image.open(path) as image:
        first = np.array(image.convert("RGB"), dtype=float)
        duration = 0
        for index in range(image.n_frames):
            image.seek(index)
            image.load()
            duration += image.info.get("duration", 0)
        last = np.array(image.convert("RGB"), dtype=float)
        return {
            "frames": image.n_frames,
            "duration_ms": duration,
            "loop": image.info.get("loop"),
            "size": list(image.size),
            "seam": round(float(np.abs(first - last).mean()), 4),
        }


def validate(concept):
    name = concept["id"]
    webp = frame_stats(HERE / (name + ".webp"))
    gif = frame_stats(HERE / (name + ".gif"))
    video = probe(HERE / (name + ".mp4"))
    stream = video["streams"][0]
    duration = round(float(video["format"]["duration"]) * 1000)
    assert webp["size"] == [768, 512], name + ": incorrect WebP size"
    assert webp["loop"] == 0 and gif["loop"] == 0, name + ": not looping"
    assert abs(webp["duration_ms"] - 40000) <= 10, name + ": incomplete WebP"
    assert gif["duration_ms"] == 40000, name + ": incomplete GIF"
    assert duration == 40000 and int(stream["nb_frames"]) == 800, name + ": incomplete video"
    assert stream["r_frame_rate"] == "20/1", name + ": incorrect video speed"
    assert len(video["chapters"]) == 12, name + ": missing poses"
    assert webp["seam"] < 1, name + ": visible loop seam"
    for suffix in ("-preview.png", "-sequence.jpg"):
        with Image.open(HERE / (name + suffix)) as image:
            image.verify()
    return {
        "file": name + ".webp",
        "size": webp["size"],
        "webp_frames": webp["frames"],
        "duration_ms": duration,
        "loop": webp["loop"],
        "video_frames": int(stream["nb_frames"]),
        "chapters": len(video["chapters"]),
        "loop_seam_mean_pixel_error": webp["seam"],
        "gif_frames": gif["frames"],
        "gif_duration_ms": gif["duration_ms"],
        "gif_loop": gif["loop"],
    }


def main():
    manifest = json.loads((HERE / "prompts.json").read_text())
    entries = [validate(concept) for concept in manifest["concepts"]]
    (HERE / "validation.json").write_text(json.dumps(entries, indent=2) + "\n")
    print("Validated all four character loops, all twelve poses and their review images.")


if __name__ == "__main__":
    main()
