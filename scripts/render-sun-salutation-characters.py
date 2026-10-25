#!/usr/bin/env python3
"""Export the flat Sun Salutation characters to transparent app frames.

Draws each character of docs/sun-salutation-flat.json with
scripts/render-sun-salutation-flat.py on a clear stage, with the app's
three-second transitions: the woman first, then the man, for the first
round and again for the next one, in which the other leg steps back first.
No image-generation service is called.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import cairo
import numpy as np
from PIL import Image

from practice_media import PREFIX, writable_media

ROOT = Path(__file__).resolve().parents[1]
# The frames go into the practices checkout; the manifest names them
# by their packaged path.
DIRECTORY = "sunsalutation/characters"
TABLE = ROOT / "src/practices/sun_salutation/sun_salutation_frames.zi"
MANIFEST = ROOT / "docs/sun-salutation-characters.json"
# After each move the app keeps playing while the hanging hair settles, so
# the held pose does not freeze it mid-swing.
SETTLE_SECONDS = 1.0


def load_flat_renderer():
    spec = importlib.util.spec_from_file_location(
        "sun_salutation_flat", ROOT / "scripts/render-sun-salutation-flat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bounds(alpha):
    ys, xs = np.nonzero(alpha > 0)
    if not len(xs):
        raise RuntimeError("The character frame is empty")
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def export_character(flat, rig, style, character, number, other_side):
    sprites = rig["sprites"]
    fps = sprites["fps"]
    camera = rig["camera"]
    width = round(camera["designWidth"] * sprites["scale"] / 2) * 2
    height = round(camera["designHeight"] * sprites["scale"] / 2) * 2
    # Supersample the shapes before reducing to the app's size. This smooths
    # moving contours without increasing the texture dimensions.
    sample_scale = 2
    figure = flat.Figure(rig, dict(style, background=None), character,
                         width * sample_scale, height * sample_scale, fps)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    context.scale(1 / sample_scale, 1 / sample_scale)
    context.set_operator(cairo.OPERATOR_SOURCE)
    # Each move is followed by the first second of its hold, while the hair
    # settles. The app holds the pose on that last frame, so the rest of the
    # hold is left out: the hair carries on from there into the next move.
    times = flat.GIRL.sprite_times(dict(rig, sprites=dict(sprites, settle=SETTLE_SECONDS)),
                                   figure.timeline)
    name = f"{number:02d}-{character['id']}" + ("-other-side" if other_side else "")
    directory = writable_media() / DIRECTORY / name
    directory.mkdir(parents=True, exist_ok=True)
    expected = set()
    steps = []
    for step, step_times in enumerate(times):
        # Hold only one transition in memory, rather than the whole round.
        frames = []
        coverage = np.zeros((height, width), dtype=bool)
        for second in step_times:
            if figure.hair_time is not None and second - figure.hair_time > 1.5 * figure.frame_step:
                figure.hair_time = second - figure.frame_step
            figure.frame(second)
            context.set_source_surface(figure.surface)
            context.get_source().set_filter(cairo.FILTER_BEST)
            context.paint()
            surface.flush()
            stride = surface.get_stride()
            pixels = np.frombuffer(surface.get_data(), np.uint8)
            pixels = pixels.reshape(height, stride // 4, 4)[:, :width].copy()
            coverage |= pixels[..., 3] > 0
            frames.append(pixels)
        box = bounds(coverage)
        left, top, right, bottom = box
        held = bounds(frames[-1][top:bottom, left:right, 3])
        for index, pixels in enumerate(frames):
            premultiplied = pixels[top:bottom, left:right].astype(np.float32)
            alpha = premultiplied[..., 3:4]
            color = np.where(
                alpha > 0, premultiplied[..., :3] * 255 / np.maximum(alpha, 1), 0
            )
            rgba = np.concatenate([color[..., ::-1], alpha], -1)
            rgba = rgba.clip(0, 255).round().astype(np.uint8)
            picture = Image.fromarray(rgba).quantize(
                sprites["colors"], method=Image.Quantize.FASTOCTREE
            )
            filename = f"{step + 1:02d}-{index + 1:03d}.png"
            picture.save(directory / filename, optimize=True)
            expected.add(filename)
        steps.append({"frames": len(frames), "box": box, "held": held})
        print(f"{name}: pose {step + 1}/{len(times)}", flush=True)
    for stale in directory.glob("*.png"):
        if stale.name not in expected:
            stale.unlink()
    return {
        "id": name, "name": character["name"], "other_side": other_side,
        "directory": f"{PREFIX}{DIRECTORY}/{name}/", "steps": steps,
        "fps": fps,
        "transition_frames": round(rig["timing"]["transition"] * fps),
        "move_frames": steps[1]["frames"],
    }


def write_tables(characters):
    steps = [step for character in characters for step in character["steps"]]
    boxes = [step["box"] for step in steps]
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    width = max(box[2] for box in boxes) - left
    height = max(box[3] for box in boxes) - top
    manifest = {
        "generator": "scripts/render-sun-salutation-characters.py",
        "stage": {"left": left, "top": top, "width": width, "height": height},
        "characters": characters,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")

    def row(values):
        return ".[" + ", ".join(str(value) for value in values) + "];"

    first = characters[0]
    counts = [step["frames"] for step in first["steps"]]
    if any([step["frames"] for step in c["steps"]] != counts for c in characters):
        raise RuntimeError("All characters must share the same frame timing")
    if counts[0] != 1 or any(count != first["move_frames"] for count in counts[1:]):
        raise RuntimeError("Every move must have the same number of frames")
    lines = [
        "// Generated by scripts/render-sun-salutation-characters.py; do not edit.",
        "// Each frame set has twelve poses: every character for the first round, then",
        "// for the next one, in which the other leg steps back first.",
        "// Geometry is indexed set * 12 + step.",
        "// Frame F of pose S is its directory + SS-FFF.png, counted from 1.",
        "// Every character shares one stage; thumbnails crop to the held pose.",
        "",
        f"SUN_SALUTATION_FRAME_SETS :: {len(characters)}",
        f"SUN_SALUTATION_STAGE_W :: {width}",
        f"SUN_SALUTATION_STAGE_H :: {height}",
        f"SUN_SALUTATION_FRAME_FPS :: {first['fps']}",
        f"SUN_SALUTATION_TRANSITION_FRAMES :: {first['transition_frames']}",
        "// Frames of every pose after the first: the move, then the hair settling.",
        f"SUN_SALUTATION_MOVE_FRAMES :: {first['move_frames']}",
        "",
        f"sun_salutation_frame_directories: [{len(characters)}]string = .[",
        *[f'    "{character["directory"]}",' for character in characters],
        "];",
        f"sun_salutation_step_frames: [12]s32 = " + row(counts),
    ]
    values = {
        "step_x": [b[0] - left for b in boxes],
        "step_y": [b[1] - top for b in boxes],
        "step_w": [b[2] - b[0] for b in boxes],
        "step_h": [b[3] - b[1] for b in boxes],
        "held_x": [s["held"][0] for s in steps],
        "held_y": [s["held"][1] for s in steps],
        "held_w": [s["held"][2] - s["held"][0] for s in steps],
        "held_h": [s["held"][3] - s["held"][1] for s in steps],
    }
    for name, entries in values.items():
        lines.append(f"sun_salutation_{name}: [{len(steps)}]s32 = " + row(entries))
    TABLE.write_text("\n".join(lines) + "\n")
    total = sum(sum(step["frames"] for step in c["steps"]) for c in characters)
    print(f"Exported {len(characters)} frame sets, {total} frames, {width}x{height} stage", flush=True)


def main():
    flat = load_flat_renderer()
    style = json.loads(flat.CHARACTERS.read_text())
    characters = []
    # Folders are numbered by frame set, so sorting them keeps the app's order.
    for other_side in (False, True):
        rig = flat.load_rig(other_side=other_side)
        for character in style["characters"]:
            characters.append(export_character(flat, rig, style, character, len(characters) + 1, other_side))
    # Characters no longer listed leave no frames behind.
    listed = {Path(character["directory"]).name for character in characters}
    for directory in (writable_media() / DIRECTORY).iterdir():
        if directory.is_dir() and directory.name not in listed:
            for stale in directory.glob("*.png"):
                stale.unlink()
            directory.rmdir()
    write_tables(characters)
    subprocess.run([sys.executable, str(ROOT / "scripts/optimize-animation-pngs.py")],
                   check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/animation_inventory.py")],
                   check=True)


if __name__ == "__main__":
    main()
