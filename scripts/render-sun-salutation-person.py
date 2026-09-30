#!/usr/bin/env python3
"""Draw the reference-video person on the fixed sun salutation rig.

The motion, bone lengths, and pose timeline come from
render-sun-salutation-rig.py. This script replaces the painted cutout
character with the woman from the selected generated reference video:
brown hair, beige crew-neck T-shirt, charcoal leggings, bare feet.
Her face is keyed from one reference frame. Long hair hangs from it as a
simulated strand, and the body is drawn as smooth cel-shaded vector shapes
around the rig bones. Rendering is offscreen with Cairo.
"""

import argparse
import importlib.util
import math
from pathlib import Path
import subprocess

import cairo
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.interpolate import PchipInterpolator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design/sun-salutation/person-source"
REFERENCE = SOURCE / "reference.mp4"
HEAD = SOURCE / "head.png"
BUILD = ROOT / "build/sun-salutation-person"

spec = importlib.util.spec_from_file_location("rig", ROOT / "scripts/render-sun-salutation-rig.py")
rig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rig)
add, sub, mul, unit, joint = rig.add, rig.sub, rig.mul, rig.unit, rig.joint

# Reference frame 108 shows her head in clean profile, facing left.
HEAD_FRAME = 108
HEAD_CROP = (136, 252, 222, 346)
HEAD_NECK_CUT = 343
HEAD_CHIN = 334
HEAD_NECK_COLUMNS = (160, 187)
HEAD_BACKGROUND = (239, 233, 228)
# Rig units per reference pixel: 68 px crown-to-chin becomes 56 units.
HEAD_SCALE = 56 / 68
NECK = (120, 2)
GROUND = 435

THEMES = {
    "light": {"background": (240, 234, 229), "shadow": (120, 100, 90, 0.20)},
    "dark": {"background": (36, 34, 40), "shadow": (0, 0, 0, 0.35)},
}
SKIN = (242, 208, 188)
SKIN_SHADE = (228, 184, 164)
SKIN_LINE = (156, 108, 96)
SHIRT = (218, 204, 190)
SHIRT_SHADE = (192, 174, 160)
SHIRT_LIGHT = (229, 219, 208)
SHIRT_LINE = (120, 102, 94)
LEGGING = (92, 91, 97)
LEGGING_SHADE = (76, 75, 82)
LEGGING_LIGHT = (103, 102, 109)
LEGGING_FAR = (79, 78, 85)
LEGGING_LINE = (46, 44, 50)
HAIR = (112, 80, 66)
HAIR_SHADE = (88, 60, 50)
HAIR_LIGHT = (142, 106, 88)
HAIR_LINE = (64, 42, 36)
LINE = 1.1

# Width profiles: (distance along the limb, anterior half-width, posterior half-width).
LEG = ((0, 16.5, 17), (12, 16.5, 17.5), (30, 15, 16), (55, 12.5, 13), (80, 10, 10),
       (93, 9.2, 8.6), (104, 8.6, 9.4), (118, 8.2, 10.8), (135, 7.6, 10.2),
       (155, 6.4, 7.8), (175, 5.3, 5.8), (188, 5.0, 5.2), (192, 5.1, 5.1))
ARM = ((-6, 8.2, 8.2), (0, 8.6, 8.8), (14, 7.8, 8.2), (40, 6.2, 6.6), (58, 5.2, 5.4),
       (68, 5.6, 5.9), (80, 6.0, 6.0), (100, 4.8, 4.8), (120, 3.8, 3.8), (128, 3.7, 3.7))
SLEEVE = ((0, 10.4, 10.7), (10, 10.8, 11.2), (20, 10.7, 11.1), (27, 11.0, 11.4))
SLEEVE_CUFF = 21

# Torso outline in (distance up the spine from the hip, forward offset).
TORSO = ((4, -20.5), (14, -17.5), (30, -14.2), (48, -14), (66, -16), (86, -18.5),
         (102, -18), (113, -13.5), (119, -7.5), (121.5, 1.5), (119, 9.5), (114, 14),
         (106, 18), (98, 22.5), (90, 26.5), (85, 27.6), (79.5, 26.8), (74.5, 24),
         (69, 20.5), (57, 18.2), (44, 17.4), (30, 18.4), (16, 20.2), (4, 21.5),
         (2.5, 11), (3.5, 0), (3, -10))
TORSO_SHADE = ((4, -20.5), (14, -17.5), (30, -14.2), (48, -14), (66, -16), (86, -18.5),
               (102, -18), (111, -14.5), (102, -12.5), (86, -13), (66, -10.5),
               (48, -8.8), (30, -9), (14, -11.5), (5, -14))
BUST_SHADE = ((83, 27.4), (79.5, 26.8), (74.5, 24), (69, 20.5), (60, 18.4), (66, 16.4),
              (73, 18.5), (78.5, 22))
BUST_LIGHT = ((101, 20.5), (95, 23.8), (89.5, 26), (87, 22.8), (92, 20.2), (98, 18))
TORSO_FOLDS = (((72, 20.5), (57, 16.2), (42, 15.4)), ((40, -12.2), (30, -10.6), (20, -12.4)),
               ((10, -8), (8.5, 4), (10, 15)))
PELVIS = ((22, -17.5), (8, -19.5), (-4, -20), (-15, -17.8), (-22, -11),
          (-20, 4), (-10, 14.5), (4, 18), (22, 18.5))

# Feet, ankle at the origin, facing right. Flat: sole 18 units below.
FLAT_FOOT = ((-4.8, -4), (-5.2, 3), (-7.5, 9), (-9.6, 13.2), (-9, 16.8), (-6, 18),
             (0, 17.6), (8, 16.8), (18, 17.6), (26, 18), (33, 18), (37.5, 17.6),
             (39.5, 16.2), (38.6, 14.2), (35, 13.3), (28, 12.3), (20, 9.8),
             (12, 5.6), (6.5, 1.5), (4.8, -4))
FLAT_FOOT_LINES = (((34.6, 13.5), (35.8, 15.3), (35.4, 17.6)),
                   ((31.2, 13.1), (32.2, 15.4), (31.8, 17.8)))
FLAT_FOOT_SHADE = ((-5, 17.9), (8, 16.8), (22, 17.8), (12, 15.2), (0, 15.6))
# Plank: toes tucked under, sole facing back, floor 44 units below.
TUCKED_FOOT = ((-5, -3), (-9.5, 1.5), (-11.8, 7), (-10.4, 13), (-7.2, 22), (-4.8, 30),
               (-3.4, 35.5), (-1.4, 41), (1.5, 43.8), (10, 44), (11.8, 42.6), (10.2, 40.6),
               (5, 38.4), (4.2, 30), (5.2, 18), (5.8, 8), (5.2, 0))
TUCKED_FOOT_LINES = (((-1.2, 40.6), (2.5, 39.2), (5, 38.6)),
                     ((6.2, 40.2), (6.8, 42.2), (6.4, 43.9)),
                     ((-9.8, 11.5), (-7.6, 12.6), (-6.4, 15)))
# Upward dog: top of the foot on the floor, sole up, floor 22 units below.
INSTEP_FOOT = ((3.8, -5.6), (-1, -8.6), (-7, -8.4), (-10, -5.5), (-18, -1), (-30, 5.5),
               (-40, 11), (-46, 15), (-49.5, 18.6), (-48.5, 21.6), (-43, 22), (-33, 19.6),
               (-20, 14.6), (-8, 9.6), (0, 6.8), (3.8, 5.6))
INSTEP_FOOT_LINES = (((-44, 16.2), (-45.4, 19.4), (-44, 21.8)),
                     ((-40.2, 13.8), (-41.6, 17.6), (-40.2, 21)))
INSTEP_FOOT_SHADE = ((-7, -8.4), (-18, -1), (-30, 5.5), (-40, 11), (-38.5, 13.4),
                     (-28.5, 8.6), (-17.5, 2.6), (-8.5, -3.2))

# Hands, wrist at the origin. Upright: back of the hand, fingers along -y,
# thumb on -x. Flat: little-finger side, palm on a floor 14 units below.
UPRIGHT_HAND = ((3.9, 0), (5.4, -7), (7.4, -14.5), (7.8, -20.5), (7.3, -27.5),
                (6.3, -32.6), (5.0, -34.0), (3.7, -33.2), (3.5, -35.6), (2.4, -38.4),
                (0.9, -38.1), (0.1, -37.0), (-0.6, -39.7), (-2.2, -40.3), (-3.5, -39.3),
                (-4.0, -37.4), (-5.0, -37.6), (-6.5, -36.6), (-7.3, -34.3), (-7.6, -29.5),
                (-7.9, -25.0), (-9.2, -24.8), (-11.0, -24.3), (-12.0, -22.2),
                (-11.4, -17.5), (-9.6, -11.5), (-6.8, -5.5), (-3.9, 0))
UPRIGHT_HAND_LINES = (((3.6, -33.2), (3.9, -27), (4.1, -21.5)),
                      ((0.1, -37), (0.3, -29), (0.5, -21.5)),
                      ((-4.0, -37.4), (-3.9, -29), (-3.6, -22)),
                      ((-7.9, -25), (-7.6, -20), (-6.6, -15)))
UPRIGHT_HAND_SHADE = ((7.8, -20.5), (7.3, -27.5), (6.3, -32.6), (5.0, -34.0),
                      (4.4, -27), (4.6, -18), (5.2, -10))
FLAT_HAND = ((-3.9, -1), (-5.0, 5), (-5.0, 10.5), (-2.8, 13.6), (4, 14), (20, 14),
             (30, 14), (38.5, 14), (40.4, 13), (39.6, 11.4), (36.8, 10.9), (31, 10.5),
             (24, 9.5), (18, 7.8), (12, 4.8), (6.5, 1.5), (3.9, -1))
FLAT_HAND_LINES = (((35.4, 11.1), (34.2, 12.6), (34.8, 14)),
                   ((30.2, 10.6), (29.1, 12.3), (29.7, 14)),
                   ((17, 8.3), (24, 11), (29.2, 12.4)))

# Long hair hanging from under the back of the bob: one full mass with
# clumped tips and a thin loose lock in front. Roots are head-image pixels;
# widths are half-widths per point.
HAIR_LOCKS = (
    {"roots": ((30, 42), (22, 66)), "segment": 13, "damping": 0.86, "color": HAIR,
     "widths": (5, 10, 15, 16.5, 16.5, 16, 15, 13.5, 12, 10, 8), "clumps": True,
     "wave": 2.6, "phase": 0.0},
    {"roots": ((38, 48), (32, 74)), "segment": 11, "damping": 0.84, "color": HAIR_LIGHT,
     "widths": (4, 5, 6, 6.2, 6, 5.2, 4.2, 3, 1.8), "clumps": False,
     "wave": 3.2, "phase": 1.9},
)
HAIR_GRAVITY = 5000


def normalize(vector):
    length = math.hypot(*vector)
    return mul(vector, 1 / max(length, 1e-9))


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return point[0] * c - point[1] * s, point[0] * s + point[1] * c


def smoothstep(low, high, value):
    amount = min(1.0, max(0.0, (value - low) / (high - low)))
    return amount * amount * (3 - 2 * amount)


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


def clockwise(points):
    """Closed shapes share one winding so overlapping sub-paths form a union."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return list(points) if area >= 0 else list(points[::-1])


def smooth_path(ctx, points, closed=True):
    """Catmull-Rom spline through the points, as cubic Beziers."""
    if closed:
        points = clockwise(points)
    count = len(points)
    ctx.move_to(*points[0])
    last = count if closed else count - 1
    for index in range(last):
        p0 = points[(index - 1) % count] if closed or index > 0 else points[index]
        p1 = points[index]
        p2 = points[(index + 1) % count]
        p3 = points[(index + 2) % count] if closed or index + 2 < count else p2
        c1 = add(p1, mul(sub(p2, p0), 1 / 6))
        c2 = sub(p2, mul(sub(p3, p1), 1 / 6))
        ctx.curve_to(*c1, *c2, *p2)
    if closed:
        ctx.close_path()


def polygon_path(ctx, points):
    points = clockwise(points)
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    ctx.close_path()


def rgb(ctx, color, alpha=1.0):
    ctx.set_source_rgba(color[0] / 255, color[1] / 255, color[2] / 255, alpha)


def inked(ctx, build, fill, line, width=LINE):
    """Fill a union of sub-paths with only its outer silhouette outlined."""
    ctx.new_path()
    build()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(width * 2)
    rgb(ctx, line)
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.stroke_preserve()
    rgb(ctx, fill)
    ctx.fill()


def shaded(ctx, clip, shade, color):
    ctx.save()
    ctx.new_path()
    clip()
    ctx.clip()
    ctx.new_path()
    shade()
    rgb(ctx, color)
    ctx.fill()
    ctx.restore()


def detail_lines(ctx, lines, color, width=0.7, alpha=1.0):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(width)
    rgb(ctx, color, alpha)
    for line in lines:
        ctx.new_path()
        smooth_path(ctx, line, closed=False)
        ctx.stroke()


class Profile:
    def __init__(self, rows):
        distances = [row[0] for row in rows]
        self.first, self.last = distances[0], distances[-1]
        self.anterior = PchipInterpolator(distances, [row[1] for row in rows])
        self.posterior = PchipInterpolator(distances, [row[2] for row in rows])


LEG_PROFILE = Profile(LEG)
ARM_PROFILE = Profile(ARM)


class Limb:
    """A smooth tapered limb bent over two bones with a rounded joint."""

    def __init__(self, root, middle, end, profile, split, band, count=44):
        forward = normalize(sub(middle, root))
        onward = normalize(sub(end, middle))
        start = add(root, mul(forward, profile.first))
        first_length = split - profile.first
        distances = np.linspace(profile.first, profile.last, count)
        self.samples = []
        for distance in distances:
            local = distance - profile.first
            if local <= first_length - band:
                center, tangent = add(start, mul(forward, local)), forward
            elif local >= first_length + band:
                center, tangent = add(middle, mul(onward, local - first_length)), onward
            else:
                amount = (local - first_length + band) / (2 * band)
                a, b = sub(middle, mul(forward, band)), add(middle, mul(onward, band))
                center = add(add(mul(a, (1 - amount) ** 2), mul(middle, 2 * amount * (1 - amount))),
                             mul(b, amount ** 2))
                tangent = normalize(add(mul(sub(middle, a), 1 - amount), mul(sub(b, middle), amount)))
            normal = (tangent[1], -tangent[0])
            self.samples.append((float(distance), center, normal))
        self.profile = profile

    def edge(self, anterior_fraction, posterior_fraction, low=None, high=None):
        front, back = [], []
        for distance, center, normal in self.samples:
            if low is not None and not low <= distance <= high:
                continue
            anterior = float(self.profile.anterior(distance))
            posterior = float(self.profile.posterior(distance))
            front.append(add(center, mul(normal, anterior * anterior_fraction)))
            back.append(sub(center, mul(normal, posterior * posterior_fraction)))
        return front, back

    def build(self, ctx):
        front, back = self.edge(1, 1)
        for index in range(len(front) - 1):
            polygon_path(ctx, (front[index], front[index + 1], back[index + 1], back[index]))
        for distance, center, _ in (self.samples[0], self.samples[-1]):
            radius = (float(self.profile.anterior(distance)) + float(self.profile.posterior(distance))) / 2
            ctx.new_sub_path()
            ctx.arc(*center, radius, 0, math.tau)

    def posterior_band(self, ctx, fraction, low=None, high=None):
        _, inner = self.edge(0, 1 - fraction, low, high)
        _, outer = self.edge(0, 1.3, low, high)
        polygon_path(ctx, outer + inner[::-1])

    def anterior_band(self, ctx, inner_fraction, outer_fraction, low, high):
        """Sheen along the front that tapers to nothing at both ends."""
        middle = (inner_fraction + outer_fraction) / 2
        inner, outer = [], []
        for distance, center, normal in self.samples:
            if not low <= distance <= high:
                continue
            taper = math.sin(math.pi * (distance - low) / (high - low))
            anterior = float(self.profile.anterior(distance))
            inner.append(add(center, mul(normal, anterior * (middle + (inner_fraction - middle) * taper))))
            outer.append(add(center, mul(normal, anterior * (middle + (outer_fraction - middle) * taper))))
        if len(inner) > 2:
            smooth_path(ctx, outer + inner[::-1])


class Hair:
    """Verlet strand whose first two points follow the head."""

    def __init__(self, lock):
        self.lock = lock
        self.segment = lock["segment"]
        self.count = len(lock["widths"])
        self.points = None
        self.previous = None
        self.roots = None

    def reset(self, roots):
        start = roots[1]
        self.points = [roots[0], roots[1]] + [
            (start[0], start[1] + self.segment * index) for index in range(1, self.count - 1)]
        self.points = [(x, min(y, GROUND - 3)) for x, y in self.points]
        self.previous = list(self.points)
        self.roots = roots
        for _ in range(90):
            self.substep(roots, 1 / 120)

    def step(self, roots, dt, collide):
        if self.points is None:
            self.reset(roots)
            return
        substeps = 8
        start = self.roots
        for index in range(1, substeps + 1):
            amount = index / substeps
            current = tuple(add(mul(a, 1 - amount), mul(b, amount)) for a, b in zip(start, roots))
            self.substep(current, dt / substeps, collide)
        self.roots = roots

    def substep(self, roots, h, collide=None):
        points = self.points
        damping = self.lock["damping"]
        for index in range(2, self.count):
            x, y = points[index]
            px, py = self.previous[index]
            self.previous[index] = (x, y)
            points[index] = (x + (x - px) * damping, y + (y - py) * damping + HAIR_GRAVITY * h * h)
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
                points[index] = (x, min(y, GROUND - 3))
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

    def outline(self):
        raw = spline_points(self.points, 5)
        count = len(raw)
        widths = np.interp(np.linspace(0, self.count - 1, count), range(self.count), self.lock["widths"])
        center, normals = [], []
        for index, point in enumerate(raw):
            tangent = normalize(sub(raw[min(index + 1, count - 1)], raw[max(index - 1, 0)]))
            normal = (tangent[1], -tangent[0])
            # A soft wave that grows toward the ends.
            amount = index / (count - 1)
            wave = self.lock["wave"] * amount * math.sin(amount * 7.5 + self.lock["phase"])
            center.append(add(point, mul(normal, wave)))
            normals.append(normal)
        left = [add(point, mul(normal, width)) for point, normal, width in zip(center, normals, widths)]
        right = [sub(point, mul(normal, width)) for point, normal, width in zip(center, normals, widths)]
        tip = center[-1]
        tangent = normalize(sub(center[-1], center[-3]))
        normal = normals[-1]
        width = widths[-1]
        if self.lock["clumps"]:
            # Three clumps of different lengths instead of a blunt end.
            notch_left = center[int(count * 0.9)]
            notch_right = center[int(count * 0.86)]
            end = [add(add(tip, mul(tangent, 7)), mul(normal, width * 0.75)),
                   add(notch_left, mul(normals[int(count * 0.9)], width * 0.2)),
                   add(add(tip, mul(tangent, 12)), mul(normal, -width * 0.1)),
                   sub(notch_right, mul(normals[int(count * 0.86)], width * 0.45)),
                   add(add(tip, mul(tangent, 3)), mul(normal, -width * 0.85))]
        else:
            end = [add(tip, mul(tangent, 8))]
        return center, widths, left, right, end


def extract_head():
    if HEAD.exists():
        return
    BUILD.mkdir(parents=True, exist_ok=True)
    frame = BUILD / "head-frame.png"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(REFERENCE),
        "-vf", f"select='eq(n,{HEAD_FRAME})'", "-frames:v", "1", str(frame),
    ], check=True)
    left, top, right, bottom = HEAD_CROP
    pixels = np.asarray(Image.open(frame).convert("RGB")).astype(float)[top:bottom, left:right]
    background = np.array(HEAD_BACKGROUND, dtype=float)
    distance = np.abs(pixels - background).sum(2)
    core = distance > 40
    labels, count = ndimage.label(core)
    areas = ndimage.sum(core, labels, range(1, count + 1))
    core = ndimage.binary_fill_holes(labels == np.argmax(areas) + 1)
    # The video's pale fringe on thin hair tips shows as a halo over dark
    # hair, so the edge band keeps only dark pixels and a soft outer ring.
    edge = core & ~ndimage.binary_erosion(core, iterations=3)
    pale = (pixels.mean(2) > 150) & (pixels[..., 0] - pixels[..., 2] < 38)
    core = core & ~(edge & pale)
    near = ndimage.binary_dilation(core, iterations=1)
    alpha = np.where(core, 1.0, np.where(near, 0.35, 0.0))
    rows = np.arange(bottom - top)[:, None] + top
    columns = np.arange(right - left)[None, :] + left
    alpha *= np.clip((HEAD_NECK_CUT - rows) / 2 + 0.5, 0, 1)
    # Below the chin keep only the neck and brown hair, not the shirt.
    below_chin = rows >= HEAD_CHIN
    neck = (columns >= HEAD_NECK_COLUMNS[0]) & (columns <= HEAD_NECK_COLUMNS[1])
    brown = (pixels.sum(2) < 480) & (pixels[..., 0] - pixels[..., 2] > 25)
    alpha = np.where(below_chin & ~neck & ~brown, 0.0, alpha)
    safe = np.maximum(alpha, 1e-3)[..., None]
    color = np.clip((pixels - (1 - safe) * background) / safe, 0, 255)
    color = np.where(alpha[..., None] > 0.02, color, 0)
    image = Image.fromarray(np.dstack([color, alpha * 255]).astype(np.uint8), "RGBA")
    image.transpose(Image.FLIP_LEFT_RIGHT).save(HEAD)


class Person:
    def __init__(self, theme, width, height):
        extract_head()
        self.head = cairo.ImageSurface.create_from_png(str(HEAD))
        neck_center = (HEAD_NECK_COLUMNS[0] + HEAD_NECK_COLUMNS[1]) / 2 - HEAD_CROP[0]
        self.head_pivot = (self.head.get_width() - neck_center, HEAD_NECK_CUT - HEAD_CROP[1] - 2)
        self.theme = THEMES[theme]
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)
        self.width, self.height = width, height
        self.hair = None
        self.hair_time = None

    def skin_shape(self, origin, shape, turn, lines, shade, far, alpha):
        if alpha <= 0.01:
            return
        ctx = self.ctx
        points = [add(origin, rotate(point, turn)) for point in shape]
        ctx.push_group()
        inked(ctx, lambda: smooth_path(ctx, points), SKIN_SHADE if far else SKIN, SKIN_LINE)
        if shade and not far:
            shade_points = [add(origin, rotate(point, turn)) for point in shade]
            shaded(ctx, lambda: smooth_path(ctx, points), lambda: smooth_path(ctx, shade_points), SKIN_SHADE)
        detail_lines(ctx, [[add(origin, rotate(point, turn)) for point in line] for line in lines],
                     SKIN_LINE, 0.6, 0.8)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)

    def foot(self, ankle, angle, instep, far):
        tucked = (1 - instep) * smoothstep(0.45, 0.7, angle)
        flat = 1 - instep - tucked
        self.skin_shape(ankle, FLAT_FOOT, angle, FLAT_FOOT_LINES, FLAT_FOOT_SHADE, far, flat)
        self.skin_shape(ankle, TUCKED_FOOT, 0, TUCKED_FOOT_LINES, None, far, tucked)
        self.skin_shape(ankle, INSTEP_FOOT, 0, INSTEP_FOOT_LINES, INSTEP_FOOT_SHADE, far, instep)

    def hand(self, wrist, angle, palm, far):
        flat = smoothstep(0.35, 0.65, palm)
        self.skin_shape(wrist, UPRIGHT_HAND, angle, UPRIGHT_HAND_LINES, UPRIGHT_HAND_SHADE, far, 1 - flat)
        self.skin_shape(wrist, FLAT_HAND, 0, FLAT_HAND_LINES, None, far, flat)

    def leg(self, p, far=False):
        ctx = self.ctx
        offset = (-5, -1) if far else (0, 0)
        hip = add(p.hip, offset)
        target = add(p.far_ankle if far else p.near_ankle, offset)
        knee, ankle = joint(hip, target, 96, 96, -1)
        self.foot(ankle, p.foot, p.instep, far)
        limb = Limb(hip, knee, ankle, LEG_PROFILE, 96, 13)
        if far:
            inked(ctx, lambda: limb.build(ctx), LEGGING_FAR, LEGGING_LINE)
            return
        pelvis = self.place(p, PELVIS)

        def build():
            limb.build(ctx)
            ctx.new_sub_path()
            smooth_path(ctx, pelvis)

        inked(ctx, build, LEGGING, LEGGING_LINE)
        shaded(ctx, build, lambda: limb.posterior_band(ctx, 0.42, 26, 192), LEGGING_SHADE)
        shaded(ctx, build, lambda: limb.anterior_band(ctx, 0.2, 0.62, 14, 78), LEGGING_LIGHT)
        shaded(ctx, build, lambda: limb.anterior_band(ctx, 0.25, 0.6, 108, 160), LEGGING_LIGHT)

    def arm(self, p, far=False):
        ctx = self.ctx
        offset = (-5, -1) if far else (0, 0)
        shoulder = add(p.shoulder, offset)
        target = add(p.far_wrist if far else p.near_wrist, offset)
        elbow, wrist = joint(shoulder, target, 64, 64, 1)
        hand_angle = math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]) + math.pi / 2
        hand_angle *= 1 - p.upright
        limb = Limb(shoulder, elbow, wrist, ARM_PROFILE, 64, 9, 36)
        inked(ctx, lambda: limb.build(ctx), SKIN_SHADE if far else SKIN, SKIN_LINE)
        if not far:
            shaded(ctx, lambda: limb.build(ctx), lambda: limb.posterior_band(ctx, 0.38), SKIN_SHADE)
        self.hand(wrist, hand_angle, p.palm, far)
        self.sleeve(shoulder, elbow, far)

    def sleeve(self, shoulder, elbow, far):
        ctx = self.ctx
        axis = normalize(sub(elbow, shoulder))
        normal = (axis[1], -axis[0])
        profile = Profile(SLEEVE)
        front, back = [], []
        for distance in np.linspace(0, SLEEVE[-1][0], 8):
            center = add(shoulder, mul(axis, distance))
            front.append(add(center, mul(normal, float(profile.anterior(distance)))))
            back.append(sub(center, mul(normal, float(profile.posterior(distance)))))
        cap = (SLEEVE[0][1] + SLEEVE[0][2]) / 2
        angle = math.atan2(axis[1], axis[0])

        def build():
            ctx.move_to(*back[-1])
            for point in back[::-1]:
                ctx.line_to(*point)
            ctx.arc(*shoulder, cap, angle + math.pi / 2, angle + math.pi * 1.5)
            for point in front:
                ctx.line_to(*point)
            ctx.close_path()

        inked(ctx, build, SHIRT_SHADE if far else SHIRT, SHIRT_LINE)
        if far:
            return
        shade = [sub(add(shoulder, mul(axis, d)), mul(normal, w)) for d, w in
                 ((-4, 13), (6, 12), (18, 12.8), (27, 13.5), (27, 6), (16, 7.5), (4, 8))]
        shaded(ctx, build, lambda: polygon_path(ctx, shade), SHIRT_SHADE)
        cuff = [add(add(shoulder, mul(axis, SLEEVE_CUFF + bow)), mul(normal, side))
                for side, bow in ((12.1, 0), (0, 1.2), (-12.5, 0))]
        fold = [add(add(shoulder, mul(axis, d)), mul(normal, side))
                for d, side in ((6, -5), (13, -3.5), (18, -4.8))]
        detail_lines(ctx, [cuff], SHIRT_LINE, 0.8)
        detail_lines(ctx, [fold], SHIRT_LINE, 0.6, 0.6)

    def place(self, p, points):
        axis = unit(p.spine)
        forward = (-math.sin(p.spine), math.cos(p.spine))
        return [add(add(p.hip, mul(axis, point[0])), mul(forward, point[1])) for point in points]

    def sag(self, p, points):
        """A loose shirt hangs away from the belly when her front faces the floor."""
        facing_down = max(0.0, math.cos(p.spine))
        result = []
        for height, depth in points:
            if depth > 0:
                bell = math.exp(-((height - 42) / 30) ** 2)
                depth += 4.5 * facing_down * bell
            result.append((height, depth))
        return result

    def torso(self, p):
        ctx = self.ctx
        body = self.place(p, self.sag(p, TORSO))

        def build():
            smooth_path(ctx, body)

        inked(ctx, build, SHIRT, SHIRT_LINE)
        for region, color in ((TORSO_SHADE, SHIRT_SHADE), (BUST_SHADE, SHIRT_SHADE), (BUST_LIGHT, SHIRT_LIGHT)):
            points = self.place(p, region)
            shaded(ctx, build, lambda: smooth_path(ctx, points), color)
        detail_lines(ctx, [self.place(p, fold) for fold in TORSO_FOLDS], SHIRT_LINE, 0.7, 0.55)

    def head_transform(self, p):
        neck = self.place(p, (NECK,))[0]
        # The head follows part of the rig's gaze relative to the spine.
        lift = math.atan2(math.sin(p.gaze - p.spine), math.cos(p.gaze - p.spine))
        lift = max(math.radians(-42), min(math.radians(10), lift * 0.6))
        return neck, p.spine + lift + math.pi / 2

    def head_point(self, p, pixel):
        neck, turn = self.head_transform(p)
        local = mul(sub(pixel, self.head_pivot), HEAD_SCALE)
        return add(neck, rotate(local, turn))

    def update_hair(self, p, time):
        roots = [tuple(self.head_point(p, pixel) for pixel in lock["roots"]) for lock in HAIR_LOCKS]
        if self.hair_time is None or time < self.hair_time:
            self.hair = [Hair(lock) for lock in HAIR_LOCKS]
            for strand, root in zip(self.hair, roots):
                strand.reset(root)
            self.hair_time = time
            return
        collide = self.back_collider(p)
        while self.hair_time + 1e-9 < time:
            dt = min(1 / 30, time - self.hair_time)
            for strand, root in zip(self.hair, roots):
                strand.step(root, dt, collide)
            self.hair_time += dt

    def back_collider(self, p):
        """Keep hair on the outside of her back instead of inside the body.

        Only while she is upright: when her front faces the floor, hair
        falls past the far side of her shoulders and shows over the body.
        """
        axis = unit(p.spine)
        forward = (-math.sin(p.spine), math.cos(p.spine))
        strength = 1 - smoothstep(0.2, 0.5, forward[1])
        if strength <= 0:
            return None
        contour = sorted([point for point in TORSO + PELVIS if point[1] < 0])
        heights = [point[0] for point in contour]
        depths = [point[1] for point in contour]

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

    def long_hair(self):
        for strand in self.hair:
            self.hair_lock(strand)

    def hair_lock(self, strand):
        ctx = self.ctx
        center, widths, left, right, jagged = strand.outline()

        def build():
            ctx.move_to(*left[0])
            for point in left[1:]:
                ctx.line_to(*point)
            for point in jagged:
                ctx.line_to(*point)
            for point in right[::-1]:
                ctx.line_to(*point)
            ctx.close_path()

        inked(ctx, build, strand.lock["color"], HAIR_LINE)
        if not strand.lock["clumps"]:
            return
        band = [add(mul(l, 0.35), mul(c, 0.65)) for l, c in zip(left, center)]
        shaded(ctx, build, lambda: polygon_path(ctx, right + band[::-1]), HAIR_SHADE)
        count = len(center)

        def across(start, end, low, high):
            """A strand drifting from one offset to another across the lock."""
            first, last = int(low * count), int(high * count)
            strand = []
            for index in range(first, last):
                amount = (index - first) / max(1, last - first - 1)
                offset = start + (end - start) * amount
                strand.append(add(mul(left[index], 0.5 + offset / 2), mul(right[index], 0.5 - offset / 2)))
            return strand

        strands = [across(0.5, 0.25, 0.3, 0.9), across(-0.15, 0.1, 0.45, 0.97)]
        detail_lines(ctx, [strand for strand in strands if len(strand) > 2], HAIR_LINE, 0.6, 0.45)
        shine = [across(offset, offset + 0.05, 0.24 + stagger, 0.34 + stagger)
                 for offset, stagger in ((-0.4, 0.02), (0.0, 0.0), (0.35, 0.03))]
        detail_lines(ctx, [strand for strand in shine if len(strand) > 1], HAIR_LIGHT, 1.3, 0.6)

    def head_and_collar(self, p):
        ctx = self.ctx
        neck, turn = self.head_transform(p)
        ctx.save()
        ctx.translate(*neck)
        ctx.rotate(turn)
        ctx.scale(HEAD_SCALE, HEAD_SCALE)
        ctx.translate(-self.head_pivot[0], -self.head_pivot[1])
        ctx.set_source_surface(self.head)
        ctx.get_source().set_filter(cairo.FILTER_GOOD)
        ctx.paint()
        ctx.restore()
        collar = self.place(p, ((121.8, -2.5), (121.3, 3), (119.5, 8.5), (117, 12)))
        ctx.new_path()
        smooth_path(ctx, collar, closed=False)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(4.4)
        rgb(ctx, SHIRT_LINE)
        ctx.stroke_preserve()
        ctx.set_line_width(2.6)
        rgb(ctx, SHIRT)
        ctx.stroke()

    def ground_shadow(self, p):
        ctx = self.ctx
        xs = [p.near_ankle[0], p.far_ankle[0], p.near_wrist[0], p.far_wrist[0], p.hip[0]]
        left, right = min(xs) - 40, max(xs) + 40
        center = ((left + right) / 2, GROUND)
        radius = (right - left) / 2
        ctx.save()
        ctx.translate(*center)
        ctx.scale(1, 9 / radius)
        gradient = cairo.RadialGradient(0, 0, 0, 0, 0, radius)
        red, green, blue, alpha = self.theme["shadow"]
        gradient.add_color_stop_rgba(0, red / 255, green / 255, blue / 255, alpha)
        gradient.add_color_stop_rgba(1, red / 255, green / 255, blue / 255, 0)
        ctx.set_source(gradient)
        ctx.arc(0, 0, radius, 0, math.tau)
        ctx.fill()
        ctx.restore()

    def frame(self, time, manifest):
        ctx = self.ctx
        p = rig.sample(time)
        self.update_hair(p, time)
        ctx.save()
        rgb(ctx, self.theme["background"])
        ctx.paint()
        ctx.scale(self.width / 1536, self.height / 1024)
        ctx.translate(manifest["centerX"], manifest["groundY"])
        ctx.scale(manifest["characterScale"], manifest["characterScale"])
        ctx.translate(-630, -manifest["rigGround"])
        self.ground_shadow(p)
        self.leg(p, far=True)
        self.arm(p, far=True)
        self.leg(p)
        self.torso(p)
        self.long_hair()
        self.head_and_collar(p)
        self.arm(p)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def render(manifest, theme, output, width, height, fps):
    person = Person(theme, width, height)
    target = output / theme / "sun-salutation.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    duration = manifest["output"]["totalSeconds"]
    metadata = BUILD / "chapters.txt"
    lines = [";FFMETADATA1", "title=Sun salutation — reference person on the fixed rig"]
    for index, name in enumerate(rig.NAMES):
        lines.extend(("[CHAPTER]", "TIMEBASE=1/1000", f"START={index * 6000}",
                      f"END={min(index * 6000 + 6000, int(duration * 1000))}", f"title={name}"))
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
        for frame in range(round(duration * fps)):
            encoder.stdin.write(person.frame(frame / fps, manifest))
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"Encoding failed: {target}")
    print(f"Saved {target}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=("light", "dark", "both"), default="light")
    parser.add_argument("--output", type=Path, default=BUILD / "video")
    parser.add_argument("--width", type=int, default=1152)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--still", type=float, action="append")
    options = parser.parse_args()
    if min(options.width, options.height, options.fps) <= 0 or options.width % 2 or options.height % 2:
        parser.error("Dimensions must be positive and even; fps must be positive")
    manifest = rig.json.loads(rig.MANIFEST.read_text())
    themes = ("light", "dark") if options.theme == "both" else (options.theme,)
    for theme in themes:
        if options.still:
            person = Person(theme, options.width, options.height)
            for still in sorted(options.still):
                person.frame(still, manifest)
                target = BUILD / theme / f"frame-{still:g}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                person.surface.write_to_png(str(target))
                print(target, flush=True)
        else:
            render(manifest, theme, options.output, options.width, options.height, options.fps)


if __name__ == "__main__":
    main()
