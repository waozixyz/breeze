#!/usr/bin/env python3
"""Animate the painted girl through Inbe's twelve-step sun salutation.

Every visible drawing is one of the painted parts in
design/sun-salutation/girl-parts/ (made with Codex's built-in image
generation; prompts in prompts.json). The pose timeline, bone lengths,
camera and part key points live in docs/sun-salutation-girl.json. Arms, legs
and the long hair are warped along their bones, each leg's seat along the
pelvis; the top flares over the leggings; head, hands and feet move rigidly.
Rendering is offscreen with Cairo and deterministic: the same inputs give the
same frames, and a single still matches its video frame.
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


def warp_mesh(ctx, picture, columns, rows, target):
    """Map a picture onto the target of each point of a columns x rows grid."""
    xs = np.linspace(0, picture.width, columns + 1)
    ys = np.linspace(0, picture.height, rows + 1)
    grid = [[((float(x), float(y)), target((x, y))) for x in xs] for y in ys]
    ctx.save()
    ctx.set_antialias(cairo.ANTIALIAS_NONE)
    for row in range(rows):
        for column in range(columns):
            corners = (grid[row][column], grid[row][column + 1],
                       grid[row + 1][column + 1], grid[row + 1][column])
            for indices in ((0, 1, 2), (0, 2, 3)):
                affine_triangle(ctx, picture.surface, [corners[i][0] for i in indices],
                                [corners[i][1] for i in indices])
    ctx.restore()


def bent_point(points, lengths, bands, distance, turns=None):
    """Point and normal at `distance` along a chain of bones from its first
    point, each joint rounded over its band. `lengths` are the bone lengths
    but the last; the chain runs straight on past both ends.

    Across a band the normal turns steadily from one bone to the next, so a
    joint folded all the way back still fans out round. `turns` gives, per
    joint, the middle of the range of its turn in radians (a hip folds
    forward up to 180 degrees); the turn is taken within half a circle of it.
    """
    start = 0.0
    for index in range(len(points) - 1):
        direction = normalize(sub(points[index + 1], points[index]))
        if index == len(lengths):
            break
        joint_at = start + lengths[index]
        band = bands[index]
        if distance <= joint_at - band:
            break
        if distance < joint_at + band:
            onward = normalize(sub(points[index + 2], points[index + 1]))
            joint = points[index + 1]
            amount = (distance - joint_at + band) / (2 * band)
            a, b = sub(joint, mul(direction, band)), add(joint, mul(onward, band))
            center = add(add(mul(a, (1 - amount) ** 2), mul(joint, 2 * amount * (1 - amount))), mul(b, amount ** 2))
            middle = turns[index] if turns else 0.0
            heading = math.atan2(direction[1], direction[0])
            turn = wrap(math.atan2(onward[1], onward[0]) - heading - middle) + middle
            tangent = unit(heading + turn * amount)
            return center, (tangent[1], -tangent[0])
        start = joint_at
    center = add(points[index], mul(direction, distance - start))
    return center, (direction[1], -direction[0])


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
        fronts = []
        for y in range(full.height):
            xs = np.nonzero(full.alpha[y] > 40)[0]
            centers.append((xs.min() + xs.max()) / 2 if len(xs) else full.width / 2)
            fronts.append(xs.max() if len(xs) else full.width / 2)
        self.centers = np.convolve(np.pad(centers, 6, mode="edge"), np.ones(13) / 13, mode="valid")
        self.fronts = np.convolve(np.pad(fronts, 6, mode="edge"), np.ones(13) / 13, mode="valid")

    def paint(self, ctx, start, middle, end, above=None):
        """Bend the painting over start→middle→end.

        With `above`, a point up the body from the root joint, the painting
        above the root joint lies along that line and bends into the first
        bone over the spec's "rootBand": a leg's seat stays on the pelvis
        while the thigh swings.
        """
        picture = self.picture
        first, second = self.lengths
        points, lengths, bands, turns, offset = [start, middle, end], [first], [self.spec["band"]], [0.0], 0.0
        if above is not None:
            offset = math.dist(above, start)
            points, lengths = [above, *points], [offset, first]
            bands, turns = [self.spec["rootBand"], *bands], [math.radians(self.spec["rootTurn"]), *turns]
        # Extra rows across each rounded joint keep a sharp bend smooth.
        scale = self.length / (first + second)
        ys = list(np.linspace(0, picture.height - 1, 40))
        joint_at = 0.0
        for length, band in zip(lengths, bands):
            joint_at += length
            for distance in np.linspace(joint_at - band, joint_at + band, 17):
                ys.append(self.root[1] + (distance - offset) * scale)
        rows = []
        for y in sorted(set(min(picture.height - 1.0, max(0.0, float(y))) for y in ys)):
            distance = offset + (y - self.root[1]) / scale
            center, normal = bent_point(points, lengths, bands, distance, turns)
            row_scale = picture.unit * self.spec["width"]
            seat = self.spec.get("seat")
            if seat:
                fullness = seat["depth"] * smoothstep(0, 1, 1 - abs(distance - offset - seat["center"]) / seat["span"])
                # Widen the painted seat behind her, keeping its front fixed.
                center = add(center, mul(normal, (self.centers[int(y)] - self.fronts[int(y)]) * row_scale * fullness))
                row_scale *= 1 + fullness
            rows.append((float(y), float(self.centers[int(y)]), center, normal,
                         row_scale))
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
        self.hem = [self.to_body(self.picture.point(point)) for point in spec["hem"]]
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

    def place(self, p, point):
        """Where a (distance up the spine, forward offset) point of the top
        goes in this pose: its lower part flares out over the leggings, more
        so at the back when it hangs away from her upside down."""
        up, ahead = point
        flare = self.spec["flare"]
        amount = smoothstep(*flare["from"], up)
        if ahead < 0:
            hang = smoothstep(*flare["hangFrom"], math.sin(p.spine))
            return up, ahead * (1 + (flare["back"] + flare["hang"] * hang) * amount)
        return up, ahead * (1 + flare["front"] * amount)

    def hem_line(self, p):
        """The hem's back and front corners, (up, ahead), as the top flares."""
        return [self.place(p, point) for point in self.hem]

    def paint(self, ctx, p):
        columns, rows = self.spec["mesh"]
        forward = (-math.sin(p.spine), math.cos(p.spine))

        def target(point):
            up, ahead = self.place(p, self.to_body(point))
            return add(add(p.hip, mul(unit(p.spine), up)), mul(forward, ahead))

        warp_mesh(ctx, self.picture, columns, rows, target)


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
        self.hand_upright = Rigid(parts["handUpright"], detail)
        self.hand_flat = Rigid(parts["handFlat"], detail)
        self.foot_flat = Rigid(parts["footFlat"], detail)
        self.foot_tucked = Rigid(parts["footTucked"], detail)
        self.foot_instep = Rigid(parts["footInstep"], detail)
        self.flat_toe = rotate(self.foot_flat.local(parts["footFlat"]["toe"]), self.foot_flat.turn)
        self.instep_toe = rotate(self.foot_instep.local(parts["footInstep"]["toe"]), self.foot_instep.turn)
        self.flat_heel = rotate(self.foot_flat.local(parts["footFlat"]["heel"]), self.foot_flat.turn)
        self.instep_heel = rotate(self.foot_instep.local(parts["footInstep"]["heel"]), self.foot_instep.turn)
        self.foot_roll = None
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

    def roll_feet(self, p, time):
        """Roll the toes under when leaving an instep contact.

        Both painted cels follow the same ankle, toe and heel at their
        handoff. The ankle lifts over the rolling toes, keeping the foot
        above the floor and the leg attached without fading between cels.
        """
        self.foot_roll = None
        step, amount = self.timeline.phase(time)
        if (amount is None or self.timeline.sequence[step].instep != 1
                or self.timeline.sequence[step + 1].instep != 0):
            return p
        start_angle = math.atan2(self.instep_toe[1], self.instep_toe[0])
        finish_angle = math.atan2(self.flat_toe[1], self.flat_toe[0]) + p.foot
        progress = 1 - p.instep
        angle = start_angle + wrap(finish_angle - start_angle) * progress
        start_length = math.hypot(*self.instep_toe)
        finish_length = math.hypot(*self.flat_toe)
        length = start_length * (1 - progress) + finish_length * progress
        toe = mul(unit(angle), length)
        heel = rotate(mix(rotate(self.instep_heel, -start_angle),
                          rotate(self.flat_heel, -(finish_angle - p.foot)), progress), angle)
        self.foot_roll = (self.contact_transform(self.instep_toe, self.instep_heel, toe, heel),
                          self.contact_transform(self.flat_toe, self.flat_heel, toe, heel))
        floor = self.ground - max(toe[1], heel[1])
        return replace(p, near_ankle=(p.near_ankle[0], min(p.near_ankle[1], floor)),
                       far_ankle=(p.far_ankle[0], min(p.far_ankle[1], floor)))

    @staticmethod
    def contact_transform(toe, heel, target_toe, target_heel):
        determinant = toe[0] * heel[1] - heel[0] * toe[1]
        return cairo.Matrix(
            (target_toe[0] * heel[1] - target_heel[0] * toe[1]) / determinant,
            (target_toe[1] * heel[1] - target_heel[1] * toe[1]) / determinant,
            (target_heel[0] * toe[0] - target_toe[0] * heel[0]) / determinant,
            (target_heel[1] * toe[0] - target_toe[1] * heel[0]) / determinant)

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
            # Contact drawings switch as solid cels, without ghosted feet.
            if self.foot_roll is not None:
                part = self.foot_instep if p.instep >= 0.5 else self.foot_flat
                transform = self.foot_roll[0 if p.instep >= 0.5 else 1]
                self.ctx.save()
                self.ctx.translate(*ankle)
                self.ctx.transform(transform)
                part.paint(self.ctx, (0, 0))
                self.ctx.restore()
            elif p.instep >= 0.5:
                self.foot_instep.paint(self.ctx, ankle)
            elif tucked >= 0.5:
                self.foot_tucked.paint(self.ctx, ankle)
            else:
                self.foot_flat.paint(self.ctx, ankle, angle)
            # The seat at the top of the leg painting stays on the pelvis.
            above = add(p.shoulder, sub(hip, p.hip))
            self.leg.paint(self.ctx, hip, knee, ankle, above)

        self.tinted(draw, far)

    def draw_arm(self, p, far):
        shoulder, elbow, wrist = self.limb_ends(p, far, leg=False)
        # Fingers follow the forearm, except upright prayer and salute hands.
        hand_angle = wrap(math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]) + math.pi / 2)
        hand_angle *= 1 - p.upright

        def draw():
            # The flat hand shows only once the wrist is down at the floor.
            flat = smoothstep(0.45, 0.55, p.palm) * (1 - smoothstep(16, 30, self.ground - wrist[1]))
            if flat >= 0.5:
                bottom = self.hand_flat.local((0, 1))[1]
                self.hand_flat.paint(self.ctx, (wrist[0], self.ground - bottom))
            else:
                self.hand_upright.paint(self.ctx, wrist, hand_angle)
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

    def covered_by_top(self, p):
        """Clip away the leggings above the hem behind her back.

        The top is worn over the leggings: above its hem only the top shows,
        so the seat can never stick out past its back. In front the top
        already covers the hips, and the thighs of a fold must stay visible.
        """
        (back_up, back_ahead), (front_up, front_ahead) = self.torso.hem_line(p)
        slope = (front_up - back_up) / (front_ahead - back_ahead)
        reach = self.rig["parts"]["torso"]["cover"]
        corners = [(back_up + (-reach - back_ahead) * slope, -reach),
                   (back_up - back_ahead * slope, 0), (reach, 0), (reach, -reach)]
        ctx = self.ctx
        ctx.rectangle(-10000, -10000, 20000, 20000)
        ctx.move_to(*self.body(p, corners[0]))
        for corner in corners[1:]:
            ctx.line_to(*self.body(p, corner))
        ctx.close_path()
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        ctx.clip()
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)

    def draw_head(self, p, layer=None):
        self.head.paint(self.ctx, self.body(p, self.torso.neck), self.head_turn(p), layer=layer)

    def frame(self, time):
        ctx = self.ctx
        p = self.roll_feet(self.timeline.sample(time), time)
        self.feet = self.timeline.feet(p, time)
        self.update_hair(p, time)
        camera = self.rig["camera"]
        ctx.save()
        background = self.theme.get("background")
        if background is None:
            # A theme without a background leaves the stage transparent.
            ctx.set_operator(cairo.OPERATOR_CLEAR)
            ctx.paint()
            ctx.set_operator(cairo.OPERATOR_OVER)
        else:
            ctx.set_source_rgb(*(value / 255 for value in background))
            ctx.paint()
        ctx.scale(self.width / camera["designWidth"], self.height / camera["designHeight"])
        ctx.translate(camera["centerX"], camera["groundY"])
        ctx.scale(camera["scale"], camera["scale"])
        ctx.translate(-camera["rigX"], -self.ground)
        self.ground_shadow(p)
        # Back to front as seen from her near side: far limbs, the long hair
        # and the back hair behind her head, neck and back, near leg, face
        # and neck, torso (the collar covers the neck's base and the shirt
        # covers the leggings), bangs and side hair, near arm.
        ctx.save()
        self.covered_by_top(p)
        self.draw_leg(p, far=True)
        ctx.restore()
        self.draw_arm(p, far=True)
        # The long lock hangs from under the back hair, which covers its top.
        self.draw_hair()
        if "back" in self.head.layers:
            self.draw_head(p, "back")
        ctx.save()
        self.covered_by_top(p)
        self.draw_leg(p, far=False)
        ctx.restore()
        self.draw_head(p)
        self.torso.paint(ctx, p)
        if "front" in self.head.layers:
            self.draw_head(p, "front")
        self.draw_arm(p, far=False)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def straight_alpha(data, width, height):
    """Cairo's premultiplied BGRA frame as straight-alpha BGRA bytes."""
    pixels = np.frombuffer(data, np.uint8).reshape(height, -1, 4)[:, :width].astype(np.float32)
    alpha = pixels[..., 3:4]
    pixels[..., :3] = np.where(alpha > 0, pixels[..., :3] * 255 / np.maximum(alpha, 1), 0)
    return pixels.clip(0, 255).round().astype(np.uint8).tobytes()


def render(rig, theme, output, width, height, fps):
    """The video: H.264 MP4 on a theme's stage, or VP9 WebM with an alpha
    channel on the transparent theme."""
    girl = Girl(rig, theme, width, height, fps)
    transparent = girl.theme.get("background") is None
    target = output / theme / ("sun-salutation.webm" if transparent else "sun-salutation.mp4")
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
        *(["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "32",
           "-row-mt", "1", "-auto-alt-ref", "0", "-threads", "3"] if transparent else
          ["-c:v", "libx264", "-crf", "18", "-preset", "fast", "-threads", "3",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart"]),
        str(target),
    ], stdin=subprocess.PIPE)
    try:
        for frame in range(round(timeline.duration * fps)):
            data = girl.frame(frame / fps)
            encoder.stdin.write(straight_alpha(data, width, height) if transparent else data)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"Encoding failed: {target}")
    print(f"Saved {target}", flush=True)


def sprite_times(rig, timeline):
    """Per step, the times of its frames: the transition into its pose, then
    the first moments of the hold while the hair settles; the last frame is
    the held pose. The first step has only its held pose."""
    sprites = rig["sprites"]
    fps = sprites["fps"]
    moving = round(rig["timing"]["transition"] * fps)
    settle = round(sprites["settle"] * fps)
    steps = [[timeline.hold - 1 / fps]]
    for step in range(1, timeline.steps):
        start = (step - 1) * timeline.period + timeline.hold
        steps.append([start + index / fps for index in range(1, moving + 1)]
                     + [step * timeline.period + index / fps for index in range(1, settle + 1)])
    return steps


def export_sprites(rig):
    """Transparent frames of every step for the app, and their table.

    Frames are rendered at the app's size on the rig's transparent theme and
    stored as palette PNGs. A step's frames share one box, trimmed to what
    any of them shows; the generated Ziran table places each step's box on
    one shared stage, so the app draws her at a fixed spot.
    """
    sprites = rig["sprites"]
    design = rig["camera"]
    width = round(design["designWidth"] * sprites["scale"] / 2) * 2
    height = round(design["designHeight"] * sprites["scale"] / 2) * 2
    girl = Girl(rig, sprites["theme"], width, height, rig["output"]["fps"])
    directory = ROOT / sprites["directory"]
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("*.png"):
        stale.unlink()
    steps = []
    for times in sprite_times(rig, girl.timeline):
        frames = []
        for time in times:
            girl.frame(time)
            stride = girl.surface.get_stride()
            pixels = np.frombuffer(girl.surface.get_data(), np.uint8).reshape(height, stride // 4, 4)[:, :width]
            frames.append(pixels.copy())
        ys, xs = np.nonzero(np.any(np.stack([frame[..., 3] for frame in frames]) > 0, axis=0))
        box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        steps.append((box, frames))
    for step, (box, frames) in enumerate(steps):
        for index, pixels in enumerate(frames):
            premultiplied = pixels[box[1]:box[3], box[0]:box[2]].astype(np.float32)
            alpha = premultiplied[..., 3:4]
            color = np.where(alpha > 0, premultiplied[..., :3] * 255 / np.maximum(alpha, 1), 0)
            rgba = np.concatenate([color[..., ::-1], alpha], -1).clip(0, 255).round().astype(np.uint8)
            image = Image.fromarray(rgba, "RGBA").quantize(sprites["colors"], method=Image.Quantize.FASTOCTREE)
            image.save(directory / f"{step + 1:02d}-{index + 1:03d}.png", optimize=True)
    boxes = [box for box, _ in steps]
    # The held pose's own box inside its step's frames, for thumbnails.
    held = []
    for box, frames in steps:
        ys, xs = np.nonzero(frames[-1][box[1]:box[3], box[0]:box[2], 3] > 0)
        held.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    stage = (max(box[2] for box in boxes) - left, max(box[3] for box in boxes) - top)

    def row(values):
        return ".[" + ", ".join(str(value) for value in values) + "];"

    lines = [
        "// Generated by scripts/render-sun-salutation-girl.py --sprites from",
        "// docs/sun-salutation-girl.json; do not edit. Frame F of step S is",
        "// SUN_SALUTATION_FRAME_DIRECTORY + \"SS-FFF.png\", both counted from 1.",
        "// A step's frames are the move into its pose and the first moments of",
        "// the hold; the last one is the held pose. All frames of a step fill",
        "// that step's box, in pixels on the shared stage; the held box is",
        "// where the held pose lies inside that frame.",
        "",
        f'SUN_SALUTATION_FRAME_DIRECTORY :: "{sprites["directory"]}/"',
        f"SUN_SALUTATION_STAGE_W :: {stage[0]}",
        f"SUN_SALUTATION_STAGE_H :: {stage[1]}",
        f"SUN_SALUTATION_FRAME_FPS :: {sprites['fps']}",
        f"SUN_SALUTATION_TRANSITION_FRAMES :: {round(rig['timing']['transition'] * sprites['fps'])}",
        "",
        f"sun_salutation_step_frames: [{len(steps)}]s32 = " + row(len(frames) for _, frames in steps),
        f"sun_salutation_step_x: [{len(steps)}]s32 = " + row(box[0] - left for box in boxes),
        f"sun_salutation_step_y: [{len(steps)}]s32 = " + row(box[1] - top for box in boxes),
        f"sun_salutation_step_w: [{len(steps)}]s32 = " + row(box[2] - box[0] for box in boxes),
        f"sun_salutation_step_h: [{len(steps)}]s32 = " + row(box[3] - box[1] for box in boxes),
        f"sun_salutation_held_x: [{len(steps)}]s32 = " + row(box[0] for box in held),
        f"sun_salutation_held_y: [{len(steps)}]s32 = " + row(box[1] for box in held),
        f"sun_salutation_held_w: [{len(steps)}]s32 = " + row(box[2] - box[0] for box in held),
        f"sun_salutation_held_h: [{len(steps)}]s32 = " + row(box[3] - box[1] for box in held),
    ]
    (ROOT / sprites["table"]).write_text("\n".join(lines) + "\n")
    count = sum(len(frames) for _, frames in steps)
    total = sum(path.stat().st_size for path in directory.glob("*.png"))
    print(f"Saved {count} frames ({total / 1024 / 1024:.2f} MB) to {directory}, "
          f"stage {stage[0]}x{stage[1]}, table {sprites['table']}", flush=True)


def main():
    rig = json.loads(RIG.read_text())
    output = rig["output"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "clear", "both"), default="light",
                        help="clear leaves the stage transparent (WebM with alpha, or PNG stills)")
    parser.add_argument("--output", type=Path, default=BUILD / "video")
    parser.add_argument("--width", type=int, default=output["width"])
    parser.add_argument("--height", type=int, default=output["height"])
    parser.add_argument("--fps", type=int, default=output["fps"])
    parser.add_argument("--still", type=float, action="append", help="render a PNG at this time in seconds")
    parser.add_argument("--sprites", action="store_true", help="export the app's transparent frames and table")
    options = parser.parse_args()
    if options.sprites:
        export_sprites(rig)
        return
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
