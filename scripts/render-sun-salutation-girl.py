#!/usr/bin/env python3
"""Animate the painted girl through Inbe's twelve-step sun salutation.

Every visible drawing is one of the painted parts in
design/sun-salutation/girl-parts/ (made with Codex's built-in image
generation; prompts in prompts.json). The pose timeline, bone lengths,
camera and part key points live in docs/sun-salutation-girl.json. Arms, legs
and the long hair are warped along their bones; head, torso, hands and feet
move rigidly. Rendering is offscreen with Cairo and deterministic: the same
inputs give the same frames, and a single still matches its video frame.
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


ROOT = Path(__file__).resolve().parents[1]
RIG = ROOT / "docs/sun-salutation-girl.json"
PARTS = ROOT / "design/sun-salutation/girl-parts"
BUILD = ROOT / "build/sun-salutation-girl"


# Vector helpers ----------------------------------------------------------

def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def mul(a, value):
    return a[0] * value, a[1] * value


def mix(a, b, amount):
    return add(mul(a, 1 - amount), mul(b, amount))


def unit(angle):
    return math.cos(angle), math.sin(angle)


def normalize(vector):
    return mul(vector, 1 / max(math.hypot(*vector), 1e-9))


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return point[0] * c - point[1] * s, point[0] * s + point[1] * c


def wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def ease(amount):
    amount = min(1.0, max(0.0, amount))
    return amount ** 3 * (amount * (amount * 6 - 15) + 10)


def smoothstep(low, high, value):
    amount = min(1.0, max(0.0, (value - low) / (high - low)))
    return amount * amount * (3 - 2 * amount)


def joint(root, target, first, second, bend):
    """Two-bone inverse kinematics: the middle joint and the reached end."""
    delta = sub(target, root)
    distance = math.hypot(*delta)
    direction = mul(delta, 1 / max(distance, 0.000001))
    distance = min(first + second - 0.00001, max(abs(first - second) + 0.00001, distance))
    endpoint = add(root, mul(direction, distance))
    along = (first ** 2 - second ** 2 + distance ** 2) / (2 * distance)
    height = math.sqrt(max(0.0, first ** 2 - along ** 2))
    perpendicular = (-direction[1], direction[0])
    middle = add(add(root, mul(direction, along)), mul(perpendicular, height * bend))
    return middle, endpoint


def spline_points(points, per_segment=6):
    """Dense open Catmull-Rom samples through the points."""
    result = []
    count = len(points)
    for index in range(count - 1):
        p0 = points[max(index - 1, 0)]
        p1, p2 = points[index], points[index + 1]
        p3 = points[min(index + 2, count - 1)]
        for step in range(per_segment):
            t = step / per_segment
            t2, t3 = t * t, t * t * t
            result.append(tuple(
                0.5 * (2 * p1[axis] + (p2[axis] - p0[axis]) * t
                       + (2 * p0[axis] - 5 * p1[axis] + 4 * p2[axis] - p3[axis]) * t2
                       + (3 * p1[axis] - p0[axis] - 3 * p2[axis] + p3[axis]) * t3)
                for axis in (0, 1)))
    result.append(points[-1])
    return result


# Poses and timeline ------------------------------------------------------

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
    torso: float = 110.0

    @property
    def shoulder(self):
        return add(self.hip, mul(unit(self.spine), self.torso))


class Timeline:
    """The twelve poses, their holds and transitions, from the rig JSON."""

    def __init__(self, rig):
        self.rig = rig
        self.hold = rig["timing"]["hold"]
        self.transition = rig["timing"]["transition"]
        self.period = self.hold + self.transition
        self.steps = len(rig["sequence"])
        self.poses = {name: self.pose(spec) for name, spec in rig["poses"].items()}
        self.sequence = [self.poses[name] for name in rig["sequence"]]
        self.stepping = {int(step): [self.poses[name] for name in stops]
                         for step, stops in rig["stepping"].items() if step.isdigit()}
        self.duration = self.period * (self.steps - 1) + self.hold

    def pose(self, spec):
        ankles = tuple(spec["ankles"])
        wrists = tuple(spec["wrists"])
        return Pose(
            hip=tuple(spec["hip"]), spine=math.radians(spec["spine"]), gaze=math.radians(spec["gaze"]),
            near_ankle=ankles, far_ankle=tuple(spec.get("farAnkle", ankles)),
            near_wrist=wrists, far_wrist=tuple(spec.get("farWrist", wrists)),
            foot=spec.get("foot", 0.0), palm=spec.get("palm", 0.0),
            instep=spec.get("instep", 0.0), upright=spec.get("upright", 0.0),
            torso=self.rig["bones"]["torso"])

    def phase(self, time):
        """Step index and linear transition amount, or None while a pose holds."""
        step = min(self.steps - 1, int(time / self.period))
        local = time - step * self.period
        if local < self.hold or step == self.steps - 1:
            return step, None
        return step, (local - self.hold) / self.transition

    def stepping_segment(self, step, amount):
        stops = self.stepping[step]
        count = len(stops) - 1
        segment = min(count - 1, int(amount * count))
        return stops[segment], stops[segment + 1], amount * count - segment

    def interpolate(self, a, b, amount, stepping=False):
        amount = ease(amount)
        points = {}
        for name in ("hip", "near_ankle", "far_ankle", "near_wrist", "far_wrist"):
            point = mix(getattr(a, name), getattr(b, name), amount)
            if stepping and "ankle" in name:
                travel = abs(getattr(b, name)[0] - getattr(a, name)[0])
                lift = min(self.rig["stepping"]["lift"], travel * 0.2)
                point = point[0], point[1] - lift * math.sin(math.pi * amount)
            points[name] = point
        scalars = {name: getattr(a, name) * (1 - amount) + getattr(b, name) * amount
                   for name in ("spine", "gaze", "foot", "palm", "instep", "upright")}
        return Pose(**points, **scalars, torso=a.torso)

    def raw(self, time):
        step, amount = self.phase(time)
        if amount is None:
            local = time - step * self.period
            breath = math.sin(math.pi * min(local, self.hold) / self.hold) ** 2
            pose = self.sequence[step]
            return replace(pose, hip=add(pose.hip, (0, -self.rig["timing"]["breath"] * breath)))
        if step in self.stepping:
            start, end, part = self.stepping_segment(step, amount)
            return self.interpolate(start, end, part, stepping=True)
        return self.interpolate(self.sequence[step], self.sequence[step + 1], amount)

    def sample(self, time):
        """The pose at `time`, with the hip moved so hands and feet can reach."""
        p = self.swan_dive(self.raw(time), time)
        axis = mul(unit(p.spine), p.torso)
        reach = self.rig["reach"]
        discs = ((p.near_ankle, reach["leg"]), (p.far_ankle, reach["leg"]),
                 (sub(p.near_wrist, axis), reach["arm"]), (sub(p.far_wrist, axis), reach["arm"]))
        hip = p.hip
        for _ in range(40):
            for center, radius in discs:
                delta = sub(hip, center)
                distance = math.hypot(*delta)
                if distance > radius:
                    hip = add(center, mul(delta, radius / distance))
        return replace(p, hip=hip)

    def swan_dive(self, p, time):
        """Upward salute to forward fold (and back up) as a swan dive.

        Moving the wrists in a straight line from overhead to the floor while
        the spine hinges folds the elbows up behind the head. Instead the
        straight arms stay in line with the spine as she hinges, then sweep
        down to the floor beside her feet in the last part of the fold.
        """
        dive = self.rig["swanDive"]
        step, amount = self.phase(time)
        if amount is None or step not in dive["steps"]:
            return p
        amount = ease(amount)
        down = amount if self.sequence[step + 1] is self.poses["fold"] else 1 - amount
        fold = self.poses["fold"]
        reach_vector = sub(fold.near_wrist, fold.shoulder)
        fold_relative = wrap(math.atan2(reach_vector[1], reach_vector[0]) - fold.spine)
        lower = smoothstep(dive["lowerFrom"], 1.0, down)
        straight = dive["straightReach"]
        reach = straight + (math.hypot(*reach_vector) - straight) * lower
        wrist = add(p.shoulder, mul(unit(p.spine + fold_relative * lower), reach))
        return replace(p, near_wrist=wrist, far_wrist=wrist, upright=0.0,
                       palm=smoothstep(dive["palmFrom"], 1.0, down))

    def resting_foot(self, ankle):
        """The foot angle for where an ankle rests: plank, down dog, or standing."""
        radius = self.rig["feet"]["restingRadius"]
        for name in ("plank", "downDog"):
            pose = self.poses[name]
            if math.dist(ankle, pose.near_ankle) < radius:
                return pose.foot
        return 0.0

    def feet(self, p, time):
        """Per-foot (foot angle, airborne amount), keyed by far=True/False.

        While stepping back into plank or forward out of down dog the feet are
        in different places, and the moving foot is in the air.
        """
        shared = {False: (p.foot, 0.0), True: (p.foot, 0.0)}
        step, amount = self.phase(time)
        if amount is None or step not in self.stepping:
            return shared
        start, end, part = self.stepping_segment(step, amount)
        eased = ease(part)
        result = {}
        for far, name in ((False, "near_ankle"), (True, "far_ankle")):
            begin, finish = getattr(start, name), getattr(end, name)
            angle = self.resting_foot(begin) * (1 - eased) + self.resting_foot(finish) * eased
            airborne = math.sin(math.pi * eased) if math.dist(begin, finish) > 1 else 0.0
            result[far] = (angle, airborne)
        return result


class Hair:
    """Verlet strand whose first two points follow the head."""

    def __init__(self, spec, ground):
        self.segment = spec["segment"]
        self.count = spec["count"]
        self.damping = spec["damping"]
        self.gravity = spec["gravity"]
        self.substeps = spec["substeps"]
        self.floor = ground - 3
        self.points = None
        self.previous = None
        self.roots = None

    def reset(self, roots):
        start = roots[1]
        self.points = [roots[0], roots[1]] + [
            (start[0], start[1] + self.segment * index) for index in range(1, self.count - 1)]
        self.points = [(x, min(y, self.floor)) for x, y in self.points]
        self.previous = list(self.points)
        self.roots = roots
        for _ in range(90):
            self.substep(roots, 1 / 120)

    def step(self, roots, dt, collide):
        start = self.roots
        for index in range(1, self.substeps + 1):
            amount = index / self.substeps
            current = tuple(mix(a, b, amount) for a, b in zip(start, roots))
            self.substep(current, dt / self.substeps, collide)
        self.roots = roots

    def substep(self, roots, h, collide=None):
        points = self.points
        for index in range(2, self.count):
            x, y = points[index]
            px, py = self.previous[index]
            self.previous[index] = (x, y)
            points[index] = (x + (x - px) * self.damping,
                             y + (y - py) * self.damping + self.gravity * h * h)
        points[0], points[1] = roots
        self.previous[0], self.previous[1] = roots
        # Bending limits keep the hair from folding back on itself into a loop.
        for _ in range(6):
            for index in range(1, self.count - 1):
                self.hold(index, index + 1, self.segment, self.segment)
            for index in range(1, self.count - 2):
                self.hold(index, index + 2, self.segment * 1.85, self.segment * 2)
            for index in range(1, self.count - 3):
                self.hold(index, index + 3, self.segment * 2.5, self.segment * 3)
            for index in range(2, self.count):
                x, y = points[index]
                points[index] = (x, min(y, self.floor))
                if collide:
                    points[index] = collide(points[index])

    def hold(self, first, second, shortest, longest):
        points = self.points
        delta = sub(points[second], points[first])
        distance = max(math.hypot(*delta), 1e-9)
        target = min(longest, max(shortest, distance))
        if abs(target - distance) < 1e-9:
            return
        correction = mul(delta, (distance - target) / distance)
        if first <= 1:
            points[second] = sub(points[second], correction)
        else:
            points[first] = add(points[first], mul(correction, 0.5))
            points[second] = sub(points[second], mul(correction, 0.5))


# Painted parts -----------------------------------------------------------

def trimmed_box(filenames):
    """Union of the non-transparent boxes of images sharing one canvas."""
    boxes = []
    for filename in filenames:
        alpha = np.asarray(Image.open(PARTS / filename).convert("RGBA"))[..., 3]
        ys, xs = np.nonzero(alpha > 20)
        boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


class Picture:
    """A trimmed part, resampled once to `detail` pixels per rig unit.

    `fade` fades out rows below that fraction (a cut stump tucks under a hand
    or foot); `top` is (fraction, ramp) where the picture fades in from above;
    `cut` is ("top" or "right", fraction) beyond which it is trimmed.
    """

    def __init__(self, filename, units_per_pixel, detail, box=None, fade=None, cut=None, top=None):
        image = Image.open(PARTS / filename).convert("RGBA")
        image = image.crop(box or trimmed_box([filename]))
        factor = units_per_pixel * detail
        size = (max(2, round(image.width * factor)), max(2, round(image.height * factor)))
        image = image.resize(size, Image.LANCZOS)
        pixels = np.asarray(image).astype(np.float32)
        rows = np.arange(size[1])[:, None] / size[1]
        columns = np.arange(size[0])[None, :] / size[0]
        if fade is not None:
            pixels[..., 3] *= np.clip((fade + 0.012 - rows) / 0.024, 0, 1)
        if top is not None:
            start, ramp = top
            pixels[..., 3] *= np.clip((rows - start) / ramp + 0.5, 0, 1)
        if cut is not None:
            side, fraction = cut
            if side == "top":
                pixels[..., 3] *= np.clip((rows - fraction) / 0.03 + 0.5, 0, 1)
            else:
                pixels[..., 3] *= np.clip((fraction - columns) / 0.02 + 0.5, 0, 1)
        premultiplied = pixels.copy()
        premultiplied[..., :3] *= pixels[..., 3:4] / 255
        bgra = premultiplied[..., [2, 1, 0, 3]].round().astype(np.uint8)
        self.width, self.height = size
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.width)
        self.buffer = np.zeros((self.height, stride), dtype=np.uint8)
        self.buffer[:, :self.width * 4] = bgra.reshape(self.height, -1)
        self.surface = cairo.ImageSurface.create_for_data(
            self.buffer, cairo.FORMAT_ARGB32, self.width, self.height, stride)
        self.alpha = pixels[..., 3]
        self.unit = 1 / detail

    def point(self, fractions):
        return fractions[0] * self.width, fractions[1] * self.height


def affine_triangle(ctx, surface, source, target):
    (sx, sy), sb, sc = source
    (dx, dy), db, dc = target
    u, v = sub(sb, (sx, sy)), sub(sc, (sx, sy))
    a, b = sub(db, (dx, dy)), sub(dc, (dx, dy))
    determinant = u[0] * v[1] - v[0] * u[1]
    if abs(determinant) < 1e-9:
        return
    xx = (a[0] * v[1] - b[0] * u[1]) / determinant
    xy = (-a[0] * v[0] + b[0] * u[0]) / determinant
    yx = (a[1] * v[1] - b[1] * u[1]) / determinant
    yy = (-a[1] * v[0] + b[1] * u[0]) / determinant
    # A collapsed sliver (the inside of a tightly bent knee) has nothing to
    # show, and its near-singular transform makes Cairo allocate huge
    # intermediate surfaces.
    stretch = max(xx * xx + yx * yx, xy * xy + yy * yy)
    if abs(xx * yy - xy * yx) < 1e-3 * stretch:
        return
    ctx.save()
    ctx.move_to(*target[0])
    ctx.line_to(*target[1])
    ctx.line_to(*target[2])
    ctx.close_path()
    ctx.clip()
    ctx.transform(cairo.Matrix(xx, yx, xy, yy, dx - xx * sx - xy * sy, dy - yx * sx - yy * sy))
    ctx.set_source_surface(surface)
    ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
    ctx.paint()
    ctx.restore()


def warp_strip(ctx, picture, rows):
    """Map horizontal bands of a picture onto a curved strip.

    Each row is (source_y, source_center_x, target_center, target_normal,
    across_scale); source columns left of the center go to -normal.
    """
    ctx.save()
    ctx.set_antialias(cairo.ANTIALIAS_NONE)
    for first, second in zip(rows[:-1], rows[1:]):
        for left, right in ((0.0, None), (None, float(picture.width))):
            corners = []
            for row, column in ((first, left), (first, right), (second, right), (second, left)):
                source_y, center_x, center, normal, scale = row
                x = center_x if column is None else column
                corners.append(((x, source_y), add(center, mul(normal, (x - center_x) * scale))))
            source = [corner[0] for corner in corners]
            target = [corner[1] for corner in corners]
            for indices in ((0, 1, 2), (0, 2, 3)):
                affine_triangle(ctx, picture.surface, [source[i] for i in indices],
                                [target[i] for i in indices])
    ctx.restore()


def bent_point(start, middle, end, first, band, distance):
    """Point and normal at `distance` along start→middle→end, joint rounded."""
    forward = normalize(sub(middle, start))
    onward = normalize(sub(end, middle))
    if distance <= first - band:
        center, tangent = add(start, mul(forward, distance)), forward
    elif distance >= first + band:
        center, tangent = add(middle, mul(onward, distance - first)), onward
    else:
        amount = (distance - first + band) / (2 * band)
        a, b = sub(middle, mul(forward, band)), add(middle, mul(onward, band))
        center = add(add(mul(a, (1 - amount) ** 2), mul(middle, 2 * amount * (1 - amount))), mul(b, amount ** 2))
        tangent = normalize(add(mul(sub(middle, a), 1 - amount), mul(sub(b, middle), amount)))
    return center, (tangent[1], -tangent[0])


class Limb:
    """An arm or leg painting bent over two bones."""

    def __init__(self, spec, lengths, detail):
        box = trimmed_box([spec["file"]])
        width, height = box[2] - box[0], box[3] - box[1]
        root_y, tip_y = spec["root"][1] * height, spec["tip"][1] * height
        units = sum(lengths) / (tip_y - root_y)
        self.spec, self.lengths = spec, lengths
        self.picture = Picture(spec["file"], units, detail, box, spec.get("fade"), top=spec.get("top"))
        self.root = self.picture.point(spec["root"])
        self.length = self.picture.point(spec["tip"])[1] - self.root[1]
        # Smoothed center line of the painting, row by row.
        full = Picture(spec["file"], units, detail, box)
        centers = []
        for y in range(full.height):
            xs = np.nonzero(full.alpha[y] > 40)[0]
            centers.append((xs.min() + xs.max()) / 2 if len(xs) else full.width / 2)
        self.centers = np.convolve(np.pad(centers, 6, mode="edge"), np.ones(13) / 13, mode="valid")

    def paint(self, ctx, start, middle, end):
        picture = self.picture
        first, second = self.lengths
        rows = []
        for y in np.linspace(0, picture.height - 1, 40):
            distance = (y - self.root[1]) / self.length * (first + second)
            center, normal = bent_point(start, middle, end, first, self.spec["band"], distance)
            rows.append((float(y), float(self.centers[int(y)]), center, normal,
                         picture.unit * self.spec["width"]))
        warp_strip(ctx, picture, rows)


class Rigid:
    """A part that moves rigidly: pivot pinned to a point, turned, scaled.

    A part may have `layers` painted on one shared canvas (the head: back
    hair, face and neck, front hair). Its key points and size are then
    measured on the `reference` image's trimmed box on that canvas.
    """

    def __init__(self, spec, detail):
        files = list(spec.get("layers", {}).values()) or [spec["file"]]
        reference = trimmed_box([spec.get("reference", files[0])])
        box = trimmed_box(files + [spec.get("reference", files[0])])
        width, height = reference[2] - reference[0], reference[3] - reference[1]
        units = spec["height"] / height if "height" in spec else spec["width"] / width
        cut = spec.get("cut")
        self.layers = {name: Picture(filename, units, detail, box, cut=cut)
                       for name, filename in spec.get("layers", {}).items()}
        self.picture = self.layers.get("base") or Picture(spec["file"], units, detail, box, cut=cut)
        # Picture pixels per canvas pixel, and the reference box inside it.
        self.scale = self.picture.width / (box[2] - box[0])
        self.reference = (reference[0] - box[0], reference[1] - box[1], width, height)
        self.pivot = self.canvas_point(spec["pivot"])
        self.turn = math.radians(spec.get("turn", 0.0))

    def canvas_point(self, fractions):
        """A point given as fractions of the reference box, in picture pixels."""
        left, top, width, height = self.reference
        return ((left + fractions[0] * width) * self.scale, (top + fractions[1] * height) * self.scale)

    def paint(self, ctx, point, angle=0.0, alpha=1.0, layer=None):
        if alpha <= 0.01:
            return
        picture = self.layers[layer] if layer else self.picture
        ctx.save()
        ctx.translate(*point)
        ctx.rotate(angle + self.turn)
        ctx.scale(picture.unit, picture.unit)
        ctx.translate(-self.pivot[0], -self.pivot[1])
        ctx.set_source_surface(picture.surface)
        ctx.get_source().set_filter(cairo.FILTER_GOOD)
        ctx.paint_with_alpha(alpha)
        ctx.restore()

    def local(self, fractions):
        """Offset of a reference-box point from the pivot, in unrotated rig units."""
        return mul(sub(self.canvas_point(fractions), self.pivot), self.picture.unit)


class Torso:
    def __init__(self, spec, length, detail):
        box = trimmed_box([spec["file"]])
        width, height = box[2] - box[0], box[3] - box[1]
        hip = (spec["hip"][0] * width, spec["hip"][1] * height)
        shoulder = (spec["shoulder"][0] * width, spec["shoulder"][1] * height)
        self.spec = spec
        self.picture = Picture(spec["file"], length / math.dist(hip, shoulder), detail, box)
        self.hip = self.picture.point(spec["hip"])
        shoulder = self.picture.point(spec["shoulder"])
        self.axis_angle = math.atan2(shoulder[1] - self.hip[1], shoulder[0] - self.hip[0])
        self.neck = self.to_body(self.picture.point(spec["neck"]))
        self.back = self.back_contour()

    def to_body(self, point):
        """Image pixel to (distance up the spine, forward offset) in rig units."""
        offset = sub(point, self.hip)
        axis = unit(self.axis_angle)
        forward = (-axis[1], axis[0])
        up = (offset[0] * axis[0] + offset[1] * axis[1]) * self.picture.unit
        ahead = (offset[0] * forward[0] + offset[1] * forward[1]) * self.picture.unit
        return up, ahead * self.spec["width"]

    def back_contour(self):
        ys, xs = np.nonzero(self.picture.alpha > 60)
        bins = {}
        for x, y in zip(xs[::7], ys[::7]):
            up, ahead = self.to_body((x, y))
            key = round(up / 4)
            bins[key] = min(bins.get(key, 0), ahead)
        return sorted((key * 4, depth) for key, depth in bins.items())

    def paint(self, ctx, p, length):
        ctx.save()
        ctx.translate(*p.hip)
        ctx.rotate(p.spine)
        # The loose top slides toward her chest when her hips are above her
        # shoulders, showing the waistband of her leggings.
        inverted = smoothstep(*self.spec["slideFrom"], math.sin(p.spine))
        ctx.translate(length, 0)
        ctx.scale(1 - self.spec["slide"] * inverted, 1)
        ctx.translate(-length, 0)
        # Squeeze front-to-back around the spine axis.
        ctx.scale(1, self.spec["width"])
        ctx.rotate(-self.axis_angle)
        ctx.scale(self.picture.unit, self.picture.unit)
        ctx.translate(-self.hip[0], -self.hip[1])
        ctx.set_source_surface(self.picture.surface)
        ctx.get_source().set_filter(cairo.FILTER_GOOD)
        ctx.paint()
        ctx.restore()


# The girl ----------------------------------------------------------------

class Girl:
    def __init__(self, rig, theme, width, height, fps):
        self.rig = rig
        self.timeline = Timeline(rig)
        self.theme = rig["themes"][theme]
        self.ground = rig["ground"]
        self.frame_step = 1 / fps
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)
        self.width, self.height = width, height
        parts, bones = rig["parts"], rig["bones"]
        detail = rig["output"]["detail"]
        self.leg = Limb(parts["leg"], (bones["thigh"], bones["shin"]), detail)
        self.arm = Limb(parts["arm"], (bones["upperArm"], bones["forearm"]), detail)
        self.torso = Torso(parts["torso"], bones["torso"], detail)
        self.head = Rigid(parts["head"], detail)
        self.hips = Rigid(parts["hips"], detail)
        self.hand_upright = Rigid(parts["handUpright"], detail)
        self.hand_flat = Rigid(parts["handFlat"], detail)
        self.foot_flat = Rigid(parts["footFlat"], detail)
        self.foot_tucked = Rigid(parts["footTucked"], detail)
        self.foot_instep = Rigid(parts["footInstep"], detail)
        hair = rig["hair"]
        hair_box = trimmed_box([parts["longHair"]["file"]])
        hair_length = hair["segment"] * (hair["count"] - 1) + 10
        self.hair_picture = Picture(parts["longHair"]["file"], hair_length / (hair_box[3] - hair_box[1]),
                                    detail, hair_box)
        self.hair = None
        self.hair_time = None
        self.feet = None

    # Placement ---------------------------------------------------------

    def body(self, p, point):
        """A (distance up the spine, forward offset) point in rig space."""
        forward = (-math.sin(p.spine), math.cos(p.spine))
        return add(add(p.hip, mul(unit(p.spine), point[0])), mul(forward, point[1]))

    def head_turn(self, p):
        head = self.rig["head"]
        lift = wrap(p.gaze - p.spine) * head["lift"]
        lift = max(math.radians(head["liftMin"]), min(math.radians(head["liftMax"]), lift))
        return p.spine + lift + math.pi / 2

    def head_point(self, p, fractions):
        neck = self.body(p, self.torso.neck)
        return add(neck, rotate(self.head.local(fractions), self.head_turn(p)))

    def limb_ends(self, p, far, leg):
        offset = tuple(self.rig["bones"]["farOffset"]) if far else (0, 0)
        bones = self.rig["bones"]
        if leg:
            root = add(p.hip, offset)
            target = add(p.far_ankle if far else p.near_ankle, offset)
            return (root, *joint(root, target, bones["thigh"], bones["shin"], -1))
        root = add(p.shoulder, offset)
        target = add(p.far_wrist if far else p.near_wrist, offset)
        return (root, *joint(root, target, bones["upperArm"], bones["forearm"], 1))

    # Drawing -----------------------------------------------------------

    def tinted(self, draw, far):
        """Draw the far-side limbs slightly darker."""
        ctx = self.ctx
        if not far:
            draw()
            return
        ctx.push_group()
        draw()
        red, green, blue, alpha = self.theme["far"]
        ctx.set_operator(cairo.OPERATOR_ATOP)
        ctx.set_source_rgba(red / 255, green / 255, blue / 255, alpha)
        ctx.paint()
        ctx.pop_group_to_source()
        ctx.paint()

    def draw_leg(self, p, far):
        hip, knee, ankle = self.limb_ends(p, far, leg=True)
        foot, airborne = self.feet[far]
        # A lifted foot points its toes along the line of the shin.
        shin = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
        pointed = shin - math.pi / 2 + self.rig["feet"]["pointToes"]
        angle = foot + wrap(pointed - foot) * smoothstep(0.0, 0.5, airborne)

        def draw():
            tucked = (1 - p.instep) * smoothstep(0.55, 0.63, foot) * (1 - smoothstep(0.18, 0.22, airborne))
            self.foot_flat.paint(self.ctx, ankle, angle, 1 - p.instep - tucked)
            self.foot_tucked.paint(self.ctx, ankle, 0, tucked)
            self.foot_instep.paint(self.ctx, ankle, 0, p.instep)
            self.leg.paint(self.ctx, hip, knee, ankle)

        self.tinted(draw, far)

    def draw_arm(self, p, far):
        shoulder, elbow, wrist = self.limb_ends(p, far, leg=False)
        # Fingers follow the forearm, except upright prayer and salute hands.
        hand_angle = wrap(math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]) + math.pi / 2)
        hand_angle *= 1 - p.upright

        def draw():
            # The flat hand shows only once the wrist is down at the floor.
            flat = smoothstep(0.45, 0.55, p.palm) * (1 - smoothstep(16, 30, self.ground - wrist[1]))
            self.hand_upright.paint(self.ctx, wrist, hand_angle, 1 - flat)
            if flat > 0.01:
                bottom = self.hand_flat.local((0, 1))[1]
                self.hand_flat.paint(self.ctx, (wrist[0], self.ground - bottom), 0, flat)
            self.arm.paint(self.ctx, shoulder, elbow, wrist)

        self.tinted(draw, far)

    def update_hair(self, p, time):
        """Advance the hair to `time` exactly as the video does.

        The hair starts at rest at 0 s and steps once per video frame with
        that frame's pose, so a single still matches the same video frame.
        """
        roots = self.rig["hair"]["roots"]
        if self.hair_time is None or time < self.hair_time - 1e-9:
            start = self.timeline.sample(0.0)
            self.hair = Hair(self.rig["hair"], self.ground)
            self.hair.reset(tuple(self.head_point(start, fractions) for fractions in roots))
            self.hair_time = 0.0
        frame = round(self.hair_time / self.frame_step)
        target = round(time / self.frame_step)
        for index in range(frame + 1, target):
            self.advance_hair(self.timeline.sample(index * self.frame_step), index * self.frame_step)
        if target > frame:
            self.advance_hair(p, time)

    def advance_hair(self, p, time):
        roots = tuple(self.head_point(p, fractions) for fractions in self.rig["hair"]["roots"])
        self.hair.step(roots, time - self.hair_time, self.back_collider(p))
        self.hair_time = time

    def back_collider(self, p):
        """Keep hair outside her back while she is upright."""
        axis = unit(p.spine)
        forward = (-math.sin(p.spine), math.cos(p.spine))
        strength = 1 - smoothstep(0.2, 0.5, forward[1])
        if strength <= 0:
            return None
        heights = [point[0] for point in self.torso.back]
        depths = [point[1] for point in self.torso.back]

        def collide(point):
            offset = sub(point, p.hip)
            height = offset[0] * axis[0] + offset[1] * axis[1]
            depth = offset[0] * forward[0] + offset[1] * forward[1]
            if not heights[0] <= height <= heights[-1]:
                return point
            back = float(np.interp(height, heights, depths)) - 1.5
            if back < depth < 0:
                return add(point, mul(forward, (back - depth) * strength))
            return point

        return collide

    def draw_hair(self):
        points = spline_points(self.hair.points, 5)
        lengths = [0.0]
        for a, b in zip(points[:-1], points[1:]):
            lengths.append(lengths[-1] + math.dist(a, b))
        total = lengths[-1]
        picture = self.hair_picture
        rows = []
        for y in np.linspace(0, picture.height - 1, 48):
            distance = y / (picture.height - 1) * total
            index = max(0, min(len(points) - 2, int(np.searchsorted(lengths, distance, side="right")) - 1))
            span = max(lengths[index + 1] - lengths[index], 1e-9)
            center = mix(points[index], points[index + 1], (distance - lengths[index]) / span)
            tangent = normalize(sub(points[index + 1], points[index]))
            rows.append((float(y), picture.width / 2, center, (tangent[1], -tangent[0]),
                         picture.unit * self.rig["hair"]["width"]))
        warp_strip(self.ctx, picture, rows)

    def ground_shadow(self, p):
        ctx = self.ctx
        xs = [p.near_ankle[0], p.far_ankle[0], p.near_wrist[0], p.far_wrist[0], p.hip[0]]
        left, right = min(xs) - 40, max(xs) + 40
        radius = (right - left) / 2
        ctx.save()
        ctx.translate((left + right) / 2, self.ground)
        ctx.scale(1, 9 / radius)
        gradient = cairo.RadialGradient(0, 0, 0, 0, 0, radius)
        red, green, blue, alpha = self.theme["shadow"]
        gradient.add_color_stop_rgba(0, red / 255, green / 255, blue / 255, alpha)
        gradient.add_color_stop_rgba(1, red / 255, green / 255, blue / 255, 0)
        ctx.set_source(gradient)
        ctx.arc(0, 0, radius, 0, math.tau)
        ctx.fill()
        ctx.restore()

    def draw_head(self, p, layer=None):
        self.head.paint(self.ctx, self.body(p, self.torso.neck), self.head_turn(p), layer=layer)

    def frame(self, time):
        ctx = self.ctx
        p = self.timeline.sample(time)
        self.feet = self.timeline.feet(p, time)
        self.update_hair(p, time)
        camera = self.rig["camera"]
        ctx.save()
        ctx.set_source_rgb(*(value / 255 for value in self.theme["background"]))
        ctx.paint()
        ctx.scale(self.width / camera["designWidth"], self.height / camera["designHeight"])
        ctx.translate(camera["centerX"], camera["groundY"])
        ctx.scale(camera["scale"], camera["scale"])
        ctx.translate(-camera["rigX"], -self.ground)
        self.ground_shadow(p)
        # Back to front as seen from her near side: far limbs, the long hair
        # and the back hair behind her head, neck and back, hips, near leg,
        # torso (the shirt covers the leggings), face and neck, the bangs and
        # side hair in front of the face, near arm.
        self.draw_leg(p, far=True)
        self.draw_arm(p, far=True)
        # The long lock hangs from under the back hair, which covers its top.
        self.draw_hair()
        if "back" in self.head.layers:
            self.draw_head(p, "back")
        # The pelvis in leggings moves with the torso; the shirt covers it
        # unless she is upside down.
        self.hips.paint(ctx, p.hip, p.spine + math.pi / 2)
        self.draw_leg(p, far=False)
        self.torso.paint(ctx, p, self.rig["bones"]["torso"])
        self.draw_head(p)
        if "front" in self.head.layers:
            self.draw_head(p, "front")
        self.draw_arm(p, far=False)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def render(rig, theme, output, width, height, fps):
    girl = Girl(rig, theme, width, height, fps)
    target = output / theme / "sun-salutation.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    timeline = girl.timeline
    metadata = BUILD / "chapters.txt"
    lines = [";FFMETADATA1", "title=Sun salutation"]
    for index, name in enumerate(rig["names"]):
        start = index * timeline.period * 1000
        end = min(start + timeline.period * 1000, timeline.duration * 1000)
        lines.extend(("[CHAPTER]", "TIMEBASE=1/1000", f"START={start:.0f}", f"END={end:.0f}", f"title={name}"))
    metadata.write_text("\n".join(lines) + "\n")
    encoder = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pixel_format", "bgra", "-video_size", f"{width}x{height}",
        "-framerate", str(fps), "-i", "pipe:0", "-f", "ffmetadata", "-i", str(metadata),
        "-map", "0:v:0", "-map_metadata", "1", "-map_chapters", "1", "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-threads", "3",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target),
    ], stdin=subprocess.PIPE)
    try:
        for frame in range(round(timeline.duration * fps)):
            encoder.stdin.write(girl.frame(frame / fps))
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"Encoding failed: {target}")
    print(f"Saved {target}", flush=True)


def main():
    rig = json.loads(RIG.read_text())
    output = rig["output"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "both"), default="light")
    parser.add_argument("--output", type=Path, default=BUILD / "video")
    parser.add_argument("--width", type=int, default=output["width"])
    parser.add_argument("--height", type=int, default=output["height"])
    parser.add_argument("--fps", type=int, default=output["fps"])
    parser.add_argument("--still", type=float, action="append", help="render a PNG at this time in seconds")
    options = parser.parse_args()
    if min(options.width, options.height, options.fps) <= 0 or options.width % 2 or options.height % 2:
        parser.error("Dimensions must be positive and even; fps must be positive")
    themes = ("light", "dark") if options.theme == "both" else (options.theme,)
    for theme in themes:
        if options.still:
            girl = Girl(rig, theme, options.width, options.height, options.fps)
            for still in sorted(options.still):
                girl.frame(still)
                target = BUILD / theme / f"frame-{still:g}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                girl.surface.write_to_png(str(target))
                print(target, flush=True)
        else:
            render(rig, theme, options.output, options.width, options.height, options.fps)


if __name__ == "__main__":
    main()
