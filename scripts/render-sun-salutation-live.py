#!/usr/bin/env python3
"""Render the player's actual Sun Salutation artwork and poses, offscreen.

Default: two complete rounds, including both leading legs, at 1536x1024/30fps.
No desktop capture or browser is involved. Native Ziran supplies the same
paint operations, pose solver, timing and framing as the app.
"""

import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import cairo


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/sun-salutation-auburn"


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class Operation(ctypes.Structure):
    _fields_ = [
        ("kind", ctypes.c_int32), ("color", ctypes.c_uint32),
        ("alpha", ctypes.c_double), ("width", ctypes.c_double),
        ("first", ctypes.c_int32), ("count", ctypes.c_int32),
    ]


V3 = ctypes.c_double * 3
QUAT = ctypes.c_double * 4


class Solved(ctypes.Structure):
    """TaiChiSolved in src/practices/tai_chi/tai_chi_solve.zi, field by field."""
    _fields_ = [
        ("pelvis", V3), ("pelvis_quat", QUAT), ("spine1", V3), ("chest", V3), ("chest_quat", QUAT),
        ("head_quat", QUAT), ("neck_base", V3), ("shoulder_center", V3), ("head_center", V3),
        ("head_top", V3), ("com", V3), ("balance_target", V3), ("load", ctypes.c_double),
        ("shoulders", V3 * 2), ("elbows", V3 * 2), ("wrists", V3 * 2), ("palms", V3 * 2),
        ("hand_quats", QUAT * 2), ("hand_shapes", (ctypes.c_double * 3) * 2),
        ("hips", V3 * 2), ("knees", V3 * 2), ("ankles", V3 * 2), ("heels", V3 * 2),
        ("balls", V3 * 2), ("toes", V3 * 2), ("foot_quats", QUAT * 2), ("toes_quats", QUAT * 2),
    ]


def solved_json(solved):
    """Every joint as plain lists, sides as [left, right]."""
    record = {}
    for name, kind in Solved._fields_:
        value = getattr(solved, name)
        if kind is ctypes.c_double:
            record[name] = value
        elif kind in (V3, QUAT):
            record[name] = [round(v, 6) for v in value]
        else:
            record[name] = [[round(v, 6) for v in item] for item in value]
    return record


class Frame(ctypes.Structure):
    _fields_ = [
        ("ops", Operation * 512), ("op_count", ctypes.c_int32),
        ("points", Point * 16384), ("point_count", ctypes.c_int32),
    ]


def compile_renderer():
    generated = BUILD / "c"
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True, exist_ok=True)
    subprocess.run(["make", "build-laws"], cwd=ROOT, check=True)
    subprocess.run([
        str(ROOT / "build/ziran-toolchain/bin/zi2c"), "--no-main", "--root", "scripts",
        "--module-path", "src", "--module-path", "build/packages/ziran/std",
        "-o", str(generated), "scripts/sun_salutation_preview.zi",
    ], cwd=ROOT, check=True)
    library = BUILD / "preview.so"
    subprocess.run([
        os.environ.get("CC", "cc"), "-std=c11", "-O2", "-shared", "-fPIC",
        "-I" + str(ROOT / "build/packages/ziran/include"), "-I" + str(generated),
        *map(str, sorted(generated.glob("*.c"))),
        str(ROOT / "build/ziran-toolchain/libziran.a"), "-lm", "-lz", "-o", str(library),
    ], cwd=ROOT, check=True)
    return library


class Renderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.native = ctypes.CDLL(str(compile_renderer()))
        self.native.PreviewFrame.argtypes = [ctypes.c_double, ctypes.c_int32, ctypes.c_int32]
        self.native.PreviewFrame.restype = ctypes.POINTER(Frame)
        self.native.PreviewSolved.argtypes = [ctypes.c_double]
        self.native.PreviewSolved.restype = ctypes.POINTER(Solved)
        self.native.PreviewYaw.argtypes = []
        self.native.PreviewYaw.restype = ctypes.c_double
        for name in ("PreviewDuration", "PreviewHeight", "PreviewCenter"):
            function = getattr(self.native, name)
            function.argtypes = []
            function.restype = ctypes.c_double
        self.duration = self.native.PreviewDuration()
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.context = cairo.Context(self.surface)

    def frame(self, second):
        frame = self.native.PreviewFrame(second, self.width, self.height).contents
        if not 0 < frame.op_count < 512 or not 0 < frame.point_count < 16384:
            raise RuntimeError(f"Paint capacity exceeded at {second:.3f}s")
        scale = self.height / self.native.PreviewHeight()
        center = self.native.PreviewCenter()
        context = self.context
        context.set_source_rgb(0.9725, 0.9647, 0.9451)
        context.paint()
        for operation in frame.ops[:frame.op_count]:
            points = []
            for point in frame.points[operation.first:operation.first + operation.count]:
                if not math.isfinite(point.x) or not math.isfinite(point.y):
                    raise RuntimeError(f"Non-finite geometry at {second:.3f}s")
                points.append((self.width / 2 + point.x * scale,
                               self.height / 2 - (point.y - center) * scale))
            context.new_path()
            for index, point in enumerate(points):
                if index == 0:
                    context.move_to(*point)
                else:
                    context.line_to(*point)
            color = operation.color
            context.set_source_rgba(((color >> 16) & 255) / 255,
                                    ((color >> 8) & 255) / 255,
                                    (color & 255) / 255, operation.alpha)
            if operation.kind == 0:
                context.close_path()
                context.fill()
            else:
                context.set_line_width(max(operation.width * scale, 1.2) * 1.5)
                context.set_line_cap(cairo.LINE_CAP_ROUND)
                context.set_line_join(cairo.LINE_JOIN_ROUND)
                context.stroke()
        self.surface.flush()
        return self.surface.get_data()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BUILD / "auburn-dawn-full.mp4")
    parser.add_argument("--width", type=int, default=1536)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--still", type=float, action="append")
    parser.add_argument("--review", action="store_true", help="save review poses before the complete video")
    parser.add_argument("--motion", type=Path,
                        help="write every frame's solved skeleton and camera turn as JSON, for the three.js lab")
    options = parser.parse_args()
    if options.width <= 0 or options.height <= 0 or options.fps <= 0:
        parser.error("Width, height and frame rate must be positive")
    if not options.still and (options.width % 2 or options.height % 2):
        parser.error("H.264 dimensions must be even")
    renderer = Renderer(options.width, options.height)
    if options.motion:
        frames = []
        for index in range(round(renderer.duration * options.fps)):
            second = index / options.fps
            record = solved_json(renderer.native.PreviewSolved(second).contents)
            record["yaw"] = renderer.native.PreviewYaw()
            frames.append(record)
        options.motion.parent.mkdir(parents=True, exist_ok=True)
        options.motion.write_text(json.dumps({"fps": options.fps, "height": 1.65, "frames": frames}))
        print(f"Saved {options.motion} ({len(frames)} frames)")
        return
    options.output.parent.mkdir(parents=True, exist_ok=True)
    if options.still or options.review:
        for second in options.still or [0, 11, 41]:
            renderer.frame(second)
            target = options.output.with_name(f"{options.output.stem}-{second:g}.png")
            renderer.surface.write_to_png(str(target))
            print(target, flush=True)
        if options.still:
            return
    encoder = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pixel_format", "bgra",
        "-video_size", f"{options.width}x{options.height}",
        "-framerate", str(options.fps), "-i", "pipe:0", "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-threads", "4",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(options.output),
    ], stdin=subprocess.PIPE)
    try:
        for index in range(round(renderer.duration * options.fps)):
            encoder.stdin.write(renderer.frame(index / options.fps))
            if index % (options.fps * 10) == 0:
                print(f"Rendered {index / options.fps:.0f}/{renderer.duration:.0f}s", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("Video encoding failed")
    print(f"Saved {options.output}", flush=True)


if __name__ == "__main__":
    main()
