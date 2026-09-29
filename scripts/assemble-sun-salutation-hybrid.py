#!/usr/bin/env python3
"""Assemble generated animation cels into separate light and dark MP4 drafts.

Image generation owns the drawings. This script uses FFmpeg to crop the
production grids, place the cels on the fixed stage, and encode the timeline.
Pillow reads the source pixels for alignment and selection mattes. FFmpeg
preserves the drawings and composites each isolated cel onto the stage.
"""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/sun-salutation-hybrid-animation.json"


def run(arguments):
    subprocess.run(arguments, check=True)


def cel_geometry(path):
    with Image.open(path) as image:
        if image.size != (1536, 1024) or image.mode != "RGBA":
            raise ValueError(f"Expected a 1536x1024 RGBA production grid: {path}")
        pixels = np.asarray(image)
    labels, _ = ndimage.label(pixels[:, :, 3] > 128)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    identities = np.argsort(sizes)[-6:]
    if len(identities) != 6 or min(sizes[identities]) < 2000:
        raise ValueError(f"Expected six isolated character drawings: {path}")
    components = []
    for identity in identities:
        y, x = np.where(labels == identity)
        left, top = max(0, int(x.min()) - 2), max(0, int(y.min()) - 2)
        right = min(1536, int(x.max()) + 3)
        bottom = min(1024, int(y.max()) + 3)
        contact_x = x[y >= y.max() - 12]
        component = labels == identity
        red, green, blue = (pixels[:, :, channel].astype(int) for channel in range(3))
        pants = component & (green > red) & (green > blue * 1.08)
        pants_y, pants_x = np.where(pants)
        if len(pants_y) == 0:
            raise ValueError(f"Could not locate the sage pants: {path}")
        ankle_x = float(np.mean(pants_x[pants_y >= pants_y.max() - 7]))
        components.append({
            "bounds": (left, top, right, bottom),
            "ground": int(y.max()) + 1,
            "groundRight": int(contact_x.max()) + 1,
            "ankle": ankle_x,
            "center": (float(x.mean()), float(y.mean())),
            "matte": ndimage.binary_dilation(component, iterations=3),
        })
    # The generator can put a fingertip or toe across the nominal grid line.
    # Find each complete drawing rather than cutting at that nominal line.
    components.sort(key=lambda component: component["center"][1])
    return (
        sorted(components[:3], key=lambda component: component["center"][0])
        + sorted(components[3:], key=lambda component: component["center"][0])
    )


def planted_anchor(clip, index):
    if clip.startswith(("01-", "02-", "03-")):
        return "ankle"
    if clip.startswith("04-") and index < 3:
        return "ankle"
    if clip.startswith("08-") and index >= 4:
        return "ankle"
    return "groundRight"


def concat_entry(path, duration):
    escaped = str(path).replace("'", "'\\''")
    return f"file '{escaped}'\nduration {duration:.6f}\n"


def assemble(manifest, theme, build, output):
    stage = ROOT / manifest["stages"][theme]
    frames = build / theme
    frames.mkdir(parents=True, exist_ok=True)
    cel_paths = {}
    for clip in manifest["clips"]:
        source = ROOT / clip["source"]
        geometry = cel_geometry(source)
        paths = []
        for index in range(6):
            cel = geometry[index]
            left, top, right, bottom = cel["bounds"]
            # Scale all cels equally. Ground stabilization compensates for
            # small differences in the generator's production-grid alignment.
            position_y = round(manifest["groundY"] - (cel["ground"] - top) * 1.5)
            anchor = planted_anchor(clip["id"], index)
            target_x = manifest["ankleX"] if anchor == "ankle" else manifest["palmRightX"]
            position_x = round(target_x - (cel[anchor] - left) * 1.5)
            destination = frames / f"{clip['id']}-{index:02d}.png"
            matte_path = frames / f"{clip['id']}-{index:02d}.pgm"
            matte_path.write_bytes(
                b"P5\n1536 1024\n255\n"
                + (cel["matte"].astype(np.uint8) * 255).tobytes()
            )
            filter_graph = (
                "[1:v]split=2[draw][alpha];[alpha]alphaextract[originalAlpha];"
                "[originalAlpha][2:v]blend=all_mode=multiply[selectedAlpha];"
                "[draw][selectedAlpha]alphamerge,"
                f"crop={right - left}:{bottom - top}:{left}:{top},"
                "scale=iw*1.5:ih*1.5:flags=neighbor[cel];"
                f"[0:v][cel]overlay={position_x}:{position_y}:format=auto,"
                "format=rgb24[frame]"
            )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(stage), "-i", str(source), "-i", str(matte_path),
                "-filter_complex", filter_graph, "-map", "[frame]",
                "-frames:v", "1", str(destination),
            ])
            paths.append(destination)
        cel_paths[clip["id"]] = paths

    hold = manifest["holdSeconds"]
    transition = manifest["transitionSeconds"]
    timeline = "ffconcat version 1.0\n"
    first = cel_paths[manifest["sequence"][0]["clip"]][0]
    timeline += concat_entry(first, hold)
    last = first
    for segment in manifest["sequence"]:
        paths = cel_paths[segment["clip"]]
        if segment.get("reverse"):
            paths = list(reversed(paths))
        for path in paths:
            timeline += concat_entry(path, transition / len(paths))
        last = paths[-1]
        timeline += concat_entry(last, hold)
    timeline += concat_entry(last, 0)
    timeline_path = frames / "timeline.ffconcat"
    timeline_path.write_text(timeline)

    duration = len(manifest["poses"]) * hold + len(manifest["sequence"]) * transition
    chapter_text = ";FFMETADATA1\ntitle=Sun salutation — hand-drawn pixel hybrid\n"
    for index, name in enumerate(manifest["poses"]):
        start = index * (hold + transition)
        end = min(start + hold + transition, duration)
        chapter_text += (
            f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start * 1000)}\n"
            f"END={round(end * 1000)}\ntitle={index + 1:02d} {name}\n"
        )
    metadata = frames / "chapters.ffmetadata"
    metadata.write_text(chapter_text)
    target = output / theme / "sun-salutation.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
        "-f", "concat", "-safe", "0", "-i", str(timeline_path),
        "-i", str(metadata), "-map", "0:v:0", "-map_metadata", "1",
        "-map_chapters", "1", "-vf", "fps=30", "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(target),
    ])
    print(f"Created {target} ({duration:g} seconds)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=["light", "dark", "both"], default="both")
    parser.add_argument("--output", type=Path, default=ROOT / "design/sun-salutation/hybrid-animation")
    options = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    build = ROOT / "build/sun-salutation-hybrid/assembled"
    themes = ["light", "dark"] if options.theme == "both" else [options.theme]
    for theme in themes:
        assemble(manifest, theme, build, options.output)


if __name__ == "__main__":
    main()
