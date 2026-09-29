#!/usr/bin/env python3
"""Animate the selected painted character with fixed-size layers and bones.

The image tool creates the artwork. FFmpeg extracts production layers, and
Cairo renders their rigid motion directly to a video encoder, offscreen.
"""

import argparse
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import subprocess

import cairo
import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/sun-salutation-rig.json"
BUILD = ROOT / "build/sun-salutation-rig"
NAMES = (
    "Mountain / prayer pose", "Upward salute", "Standing forward fold",
    "Half lift", "High plank", "Low plank", "Upward-facing dog",
    "Downward-facing dog", "Half lift", "Standing forward fold",
    "Upward salute", "Mountain / prayer pose",
)


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def mul(a, value):
    return a[0] * value, a[1] * value


def unit(angle):
    return math.cos(angle), math.sin(angle)


def mix(a, b, amount):
    return add(mul(a, 1 - amount), mul(b, amount))


def ease(amount):
    amount = min(1.0, max(0.0, amount))
    return amount**3 * (amount * (amount * 6 - 15) + 10)


def joint(root, target, first, second, bend):
    delta = sub(target, root)
    distance = math.hypot(*delta)
    direction = mul(delta, 1 / max(distance, 0.000001))
    distance = min(first + second - 0.00001, max(abs(first - second) + 0.00001, distance))
    endpoint = add(root, mul(direction, distance))
    along = (first**2 - second**2 + distance**2) / (2 * distance)
    height = math.sqrt(max(0.0, first**2 - along**2))
    perpendicular = (-direction[1], direction[0])
    middle = add(add(root, mul(direction, along)), mul(perpendicular, height * bend))
    return middle, endpoint


@dataclass(frozen=True)
class Pose:
    hip: tuple
    spine: float
    gaze: float
    near_ankle: tuple
    far_ankle: tuple
    near_wrist: tuple
    far_wrist: tuple
    foot: float = 0.0
    palm: float = 0.0
    instep: float = 0.0
    upright: float = 0.0

    @property
    def shoulder(self):
        return add(self.hip, mul(unit(self.spine), 110))


def pose(hip, spine, gaze, ankle, wrist, **options):
    return Pose(hip, math.radians(spine), math.radians(gaze), ankle, ankle, wrist, wrist, **options)


MOUNTAIN = pose((626, 226), -90, -90, (630, 417), (691, 128), upright=1)
SALUTE = pose((626, 226), -90, -98, (630, 417), (626, -11), upright=1)
FOLD = pose((626, 226), 60, 30, (630, 417), (662, 425), palm=1)
LIFT = pose((626, 226), 1, -75, (630, 417), (643, 332))
PLANK = pose((622, 329), -19, -80, (441, 391), (727, 421), foot=0.8, palm=1)
LOW = pose((631, 374), -5, -80, (441, 391), (727, 421), foot=0.8, palm=1)
UP_DOG = pose((644, 369), -44, -100, (460, 413), (727, 421), palm=1, instep=1)
DOWN_DOG = pose((550, 262), 42, 20, (420, 404), (727, 421), foot=0.3, palm=1)
POSES = (MOUNTAIN, SALUTE, FOLD, LIFT, PLANK, LOW, UP_DOG, DOWN_DOG, LIFT, FOLD, SALUTE, MOUNTAIN)
PLANT = pose((629, 277), 44, -65, (630, 417), (727, 421), palm=1)
STEP_BACK = replace(pose((577, 311), 21, -65, (630, 417), (727, 421), palm=1), far_ankle=(441, 391))
STEP_FORWARD = replace(pose((575, 315), 19, -65, (630, 417), (727, 421), palm=1), far_ankle=(420, 404))
RETURN_CROUCH = pose((629, 285), 36, -65, (630, 417), (727, 421), palm=1)


def interpolate(a, b, amount, stepping=False):
    amount = ease(amount)
    points = {}
    for name in ("hip", "near_ankle", "far_ankle", "near_wrist", "far_wrist"):
        point = mix(getattr(a, name), getattr(b, name), amount)
        if stepping and "ankle" in name:
            travel = abs(getattr(b, name)[0] - getattr(a, name)[0])
            point = point[0], point[1] - min(34, travel * 0.2) * math.sin(math.pi * amount)
        points[name] = point
    scalars = {
        name: getattr(a, name) * (1 - amount) + getattr(b, name) * amount
        for name in ("spine", "gaze", "foot", "palm", "instep", "upright")
    }
    return Pose(**points, **scalars)


def raw_sample(time, hold=3, transition=3):
    step = min(11, int(time / (hold + transition)))
    local = time - step * (hold + transition)
    if local < hold or step == 11:
        breath = math.sin(math.pi * min(local, hold) / hold) ** 2
        return replace(POSES[step], hip=add(POSES[step].hip, (0, -0.15 * breath)))
    amount = (local - hold) / transition
    if step in (3, 7):
        stops = (LIFT, PLANT, STEP_BACK, PLANK) if step == 3 else (DOWN_DOG, STEP_FORWARD, RETURN_CROUCH, LIFT)
        segment = min(2, int(amount * 3))
        return interpolate(stops[segment], stops[segment + 1], amount * 3 - segment, stepping=True)
    return interpolate(POSES[step], POSES[step + 1], amount)


def sample(time):
    p = raw_sample(time)
    axis = mul(unit(p.spine), 110)
    discs = (
        (p.near_ankle, 191.5), (p.far_ankle, 191.5),
        (sub(p.near_wrist, axis), 127.5), (sub(p.far_wrist, axis), 127.5),
    )
    hip = p.hip
    for _ in range(40):
        for center, radius in discs:
            delta = sub(hip, center)
            distance = math.hypot(*delta)
            if distance > radius:
                hip = add(center, mul(delta, radius / distance))
    return replace(p, hip=hip)


def extract_parts(manifest):
    target = ROOT / "design/sun-salutation/hybrid-animation-source/rig-parts"
    target.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    atlas = ROOT / manifest["atlas"]
    with Image.open(atlas) as image:
        pixels = np.asarray(image)
    labels, _ = ndimage.label(pixels[:, :, 3] > 128)
    areas = np.bincount(labels.ravel())
    areas[0] = 0
    identities = np.argsort(areas)[-12:]
    if min(areas[identities]) < 3000:
        raise ValueError("The production atlas must contain twelve separate painted parts")
    pieces = []
    for identity in identities:
        y, x = np.where(labels == identity)
        pieces.append((float(y.mean()), float(x.mean()), int(identity)))
    pieces.sort()
    ordered = []
    for start in (0, 4, 8):
        ordered.extend(sorted(pieces[start:start + 4], key=lambda piece: piece[1]))
    for spec, (_, _, identity) in zip(manifest["parts"], ordered):
        destination = target / f"{spec['name']}.png"
        if destination.exists():
            continue
        mask = ndimage.binary_dilation(labels == identity, iterations=3)
        y, x = np.where(mask)
        left, top = int(x.min()), int(y.min())
        width, height = int(x.max()) - left + 1, int(y.max()) - top + 1
        selection = BUILD / f"{spec['name']}.pgm"
        selection.write_bytes(b"P5\n1536 1024\n255\n" + (mask.astype(np.uint8) * 255).tobytes())
        filters = (
            "[0:v]split[drawing][alpha];[alpha]alphaextract[a];"
            "[a][1:v]blend=all_mode=multiply[selected];"
            f"[drawing][selected]alphamerge,crop={width}:{height}:{left}:{top}[part]"
        )
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(atlas), "-i", str(selection), "-filter_complex", filters,
            "-map", "[part]", "-frames:v", "1", str(destination),
        ], check=True)
    return target


def extract_whole_parts(manifest, directory):
    for spec in manifest["wholeParts"] + manifest.get("replacementParts", []):
        destination = directory / f"{spec['name']}.png"
        if destination.exists():
            continue
        source = ROOT / spec["source"]
        with Image.open(source) as image:
            pixels = np.asarray(image)
        labels, _ = ndimage.label(pixels[:, :, 3] > 128)
        areas = np.bincount(labels.ravel())
        areas[0] = 0
        mask = ndimage.binary_dilation(labels == np.argmax(areas), iterations=3)
        y, x = np.where(mask)
        left, top = int(x.min()), int(y.min())
        width, height = int(x.max()) - left + 1, int(y.max()) - top + 1
        selection = BUILD / f"{spec['name']}.pgm"
        selection.write_bytes(
            f"P5\n{pixels.shape[1]} {pixels.shape[0]}\n255\n".encode()
            + (mask.astype(np.uint8) * 255).tobytes()
        )
        filters = (
            "[0:v]split[drawing][alpha];[alpha]alphaextract[a];"
            "[a][1:v]blend=all_mode=multiply[selected];"
            f"[drawing][selected]alphamerge,crop={width}:{height}:{left}:{top}[part]"
        )
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(source), "-i", str(selection), "-filter_complex", filters,
            "-map", "[part]", "-frames:v", "1", str(destination),
        ], check=True)


class Part:
    def __init__(self, directory, spec):
        self.spec = spec
        filename = spec.get("file", f"{spec['name']}.png")
        self.surface = cairo.ImageSurface.create_from_png(str(directory / filename))
        self.width = self.surface.get_width()
        self.height = self.surface.get_height()
        if spec["kind"] == "bone":
            self.root = self.point(spec["root"])
            tip = self.point(spec["tip"])
            self.angle = math.atan2(tip[1] - self.root[1], tip[0] - self.root[0])
            self.scale = spec["length"] / math.dist(self.root, tip)
        else:
            self.root = self.point(spec["pivot"])
            self.angle = 0
            self.scale = spec["height"] / self.height if "height" in spec else spec["width"] / self.width

    def point(self, fractions):
        return fractions[0] * self.width, fractions[1] * self.height

    def paint(self, ctx, point, angle=0, alpha=1):
        if alpha <= 0:
            return
        ctx.save()
        ctx.translate(*point)
        ctx.rotate(angle - self.angle)
        ctx.scale(self.scale, self.scale)
        ctx.translate(-self.root[0], -self.root[1])
        ctx.set_source_surface(self.surface)
        ctx.get_source().set_filter(cairo.FILTER_NEAREST)
        ctx.paint_with_alpha(alpha)
        ctx.restore()

    def bone(self, ctx, start, end):
        self.paint(ctx, start, math.atan2(end[1] - start[1], end[0] - start[0]))


class PaintedLimb:
    def __init__(self, directory, spec):
        self.surface = cairo.ImageSurface.create_from_png(str(directory / f"{spec['name']}.png"))
        self.width, self.height = self.surface.get_width(), self.surface.get_height()
        self.root = self.point(spec["root"])
        self.joint = self.point(spec["joint"])
        self.tip = self.point(spec["tip"])
        self.lengths = spec["lengths"]
        self.scale = sum(self.lengths) / (self.tip[1] - self.root[1])
        self.rows = sorted(set([
            0, self.height, self.root[1], self.joint[1], self.tip[1],
            *np.linspace(0, self.height, 19).tolist(),
        ]))
        self.columns = [0, self.width / 2, self.width]

    def point(self, fractions):
        return fractions[0] * self.width, fractions[1] * self.height

    def vertex(self, x, y, start, middle, end):
        first, second = self.lengths
        if y <= self.joint[1]:
            fraction = (y - self.root[1]) / (self.joint[1] - self.root[1])
            distance = fraction * first
            source_x = self.root[0] + fraction * (self.joint[0] - self.root[0])
        else:
            fraction = (y - self.joint[1]) / (self.tip[1] - self.joint[1])
            distance = first + fraction * second
            source_x = self.joint[0] + fraction * (self.tip[0] - self.joint[0])
        forward = mul(sub(middle, start), 1 / first)
        onward = mul(sub(end, middle), 1 / second)
        band = 7
        if distance < first - band:
            center = add(start, mul(forward, distance))
            tangent = forward
        elif distance > first + band:
            center = add(middle, mul(onward, distance - first))
            tangent = onward
        else:
            fraction = (distance - first + band) / (2 * band)
            a, b = sub(middle, mul(forward, band)), add(middle, mul(onward, band))
            center = add(add(mul(a, (1 - fraction)**2), mul(middle, 2 * fraction * (1 - fraction))), mul(b, fraction**2))
            tangent = mix(forward, onward, fraction)
            tangent = mul(tangent, 1 / max(0.000001, math.hypot(*tangent)))
        normal = (tangent[1], -tangent[0])
        return add(center, mul(normal, (x - source_x) * self.scale))

    def triangle(self, ctx, source, target):
        (sx, sy), sb, sc = source
        (dx, dy), db, dc = target
        u, v = sub(sb, (sx, sy)), sub(sc, (sx, sy))
        a, b = sub(db, (dx, dy)), sub(dc, (dx, dy))
        if abs(a[0] * b[1] - b[0] * a[1]) < 1e-10:
            return
        determinant = u[0] * v[1] - v[0] * u[1]
        xx = (a[0] * v[1] - b[0] * u[1]) / determinant
        xy = (-a[0] * v[0] + b[0] * u[0]) / determinant
        yx = (a[1] * v[1] - b[1] * u[1]) / determinant
        yy = (-a[1] * v[0] + b[1] * u[0]) / determinant
        ctx.save()
        ctx.set_antialias(cairo.ANTIALIAS_NONE)
        ctx.move_to(*target[0])
        ctx.line_to(*target[1])
        ctx.line_to(*target[2])
        ctx.close_path()
        ctx.clip()
        ctx.transform(cairo.Matrix(xx, yx, xy, yy, dx - xx * sx - xy * sy, dy - yx * sx - yy * sy))
        ctx.set_source_surface(self.surface)
        ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
        ctx.paint()
        ctx.restore()

    def paint(self, ctx, start, middle, end):
        for top, bottom in zip(self.rows[:-1], self.rows[1:]):
            for left, right in zip(self.columns[:-1], self.columns[1:]):
                source = ((left, top), (right, top), (right, bottom), (left, bottom))
                target = tuple(self.vertex(x, y, start, middle, end) for x, y in source)
                for indices in ((0, 1, 2), (0, 2, 3)):
                    self.triangle(ctx, tuple(source[i] for i in indices), tuple(target[i] for i in indices))


class Renderer:
    def __init__(self, manifest, theme, width, height):
        directory = extract_parts(manifest)
        extract_whole_parts(manifest, directory)
        self.parts = {spec["name"]: Part(directory, spec) for spec in manifest["parts"]}
        self.limbs = {spec["name"]: PaintedLimb(directory, spec) for spec in manifest["wholeParts"]}
        self.manifest = manifest
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)
        self.width, self.height = width, height
        self.background = cairo.ImageSurface.create_from_png(str(ROOT / manifest["stages"][theme]))

    def leg(self, p, far=False):
        offset = (-5, -1) if far else (0, 0)
        hip = add(p.hip, offset)
        ankle = add(p.far_ankle if far else p.near_ankle, offset)
        knee, ankle = joint(hip, ankle, 96, 96, -1)
        self.limbs["whole-leg"].paint(self.ctx, hip, knee, ankle)
        self.parts["foot"].paint(self.ctx, ankle, p.foot, 1 - p.instep)
        self.parts["instep-foot"].paint(self.ctx, ankle, 0, p.instep)

    def arm(self, p, far=False):
        offset = (-5, -1) if far else (0, 0)
        shoulder = add(p.shoulder, offset)
        wrist = add(p.far_wrist if far else p.near_wrist, offset)
        elbow, wrist = joint(shoulder, wrist, 64, 64, 1)
        self.limbs["whole-arm"].paint(self.ctx, shoulder, elbow, wrist)
        hand_angle = math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]) + math.pi / 2
        hand_angle *= 1 - p.upright
        self.parts["hand"].paint(self.ctx, wrist, hand_angle, 1 - p.palm)
        self.parts["palm"].paint(self.ctx, wrist, 0, p.palm)

    def frame(self, time):
        ctx = self.ctx
        ctx.save()
        ctx.scale(self.width / 1536, self.height / 1024)
        ctx.set_source_surface(self.background)
        ctx.paint()
        ctx.translate(self.manifest["centerX"], self.manifest["groundY"])
        ctx.scale(self.manifest["characterScale"], self.manifest["characterScale"])
        ctx.translate(-630, -self.manifest["rigGround"])
        p = sample(time)
        self.leg(p, far=True)
        self.arm(p, far=True)
        self.leg(p)
        self.parts["torso"].bone(ctx, p.hip, p.shoulder)
        front = (-math.sin(p.spine), math.cos(p.spine))
        neck = add(add(p.shoulder, mul(unit(p.spine), 7)), mul(front, 11))
        self.parts["head"].paint(ctx, neck, p.gaze + math.pi / 2)
        self.arm(p)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def validate_rig(manifest):
    errors = []
    excursions = []
    fps = manifest["output"]["fps"]
    frames = round(manifest["output"]["totalSeconds"] * fps)
    for frame in range(frames):
        p = sample(frame / fps)
        for root, target, length, bend in (
            (p.hip, p.near_ankle, 96, -1), (p.hip, p.far_ankle, 96, -1),
            (p.shoulder, p.near_wrist, 64, 1), (p.shoulder, p.far_wrist, 64, 1),
        ):
            middle, end = joint(root, target, length, length, bend)
            errors.extend((abs(math.dist(root, middle) - length), abs(math.dist(middle, end) - length)))
            excursions.append(math.dist(target, end))
    report = {"sampledFrames": frames,
              "maximumBoneLengthError": max(errors), "maximumTargetClamp": max(excursions),
              "layerScaleVariesWithTime": False}
    if max(report["maximumBoneLengthError"], report["maximumTargetClamp"]) > 1e-8:
        raise AssertionError(report)
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


def render(manifest, theme, output, width, height, fps):
    renderer = Renderer(manifest, theme, width, height)
    target = output / theme / "sun-salutation.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    duration = manifest["output"]["totalSeconds"]
    metadata = BUILD / "chapters.txt"
    lines = [";FFMETADATA1", "title=Sun salutation — fixed character rig"]
    for index, name in enumerate(NAMES):
        lines.extend(("[CHAPTER]", "TIMEBASE=1/1000", f"START={index * 6000}",
                      f"END={min(index * 6000 + 6000, int(duration * 1000))}", f"title={name}"))
    metadata.write_text("\n".join(lines) + "\n")
    encoder = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-f", "rawvideo", "-pixel_format", "bgra", "-video_size", f"{width}x{height}",
        "-framerate", str(fps), "-i", "pipe:0", "-f", "ffmetadata", "-i", str(metadata),
        "-map", "0:v:0", "-map_metadata", "1", "-map_chapters", "1", "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-threads", "3",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target),
    ], stdin=subprocess.PIPE)
    try:
        for frame in range(round(duration * fps)):
            encoder.stdin.write(renderer.frame(frame / fps))
            if frame % (fps * 6) == 0:
                print(f"{theme}: {frame / fps:g}/{duration:g}s", flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"Encoding failed: {target}")
    print(f"Saved {target}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "both"), default="both")
    parser.add_argument("--output", type=Path, default=ROOT / "design/sun-salutation/rigged-animation")
    parser.add_argument("--width", type=int, default=1536)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--still", type=float)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    if min(options.width, options.height, options.fps) <= 0 or options.width % 2 or options.height % 2:
        parser.error("Dimensions must be positive and even; fps must be positive")
    manifest = json.loads(MANIFEST.read_text())
    validate_rig(manifest)
    if options.check:
        return
    themes = ("light", "dark") if options.theme == "both" else (options.theme,)
    for theme in themes:
        if options.still is not None:
            renderer = Renderer(manifest, theme, options.width, options.height)
            renderer.frame(options.still)
            target = options.output / theme / f"frame-{options.still:g}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            renderer.surface.write_to_png(str(target))
            print(target, flush=True)
        else:
            render(manifest, theme, options.output, options.width, options.height, options.fps)


if __name__ == "__main__":
    main()
