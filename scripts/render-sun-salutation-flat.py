#!/usr/bin/env python3
"""Animate flat, cleanly drawn characters through Inbe's sun salutation.

The pose timeline, inverse kinematics and hair simulation come from
render-sun-salutation-girl.py and docs/sun-salutation-girl.json; the
characters come from docs/sun-salutation-flat.json. Instead of warping
painted parts, every part is a flat vector shape drawn with Cairo: limbs are
hulls of circles along their bones, the torso, head, hands and feet are
smooth outlines, and parts of one colour are filled as one shape, so they
join without seams. Feet find their own contact with the floor: a standing
foot lies flat, a foot behind the body rises onto tucked toes, and in
upward-facing dog the top of the foot rests on the floor. See
docs/sun-salutation-flat.md.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile

import cairo

ROOT = Path(__file__).resolve().parents[1]
RIG = ROOT / "docs/sun-salutation-girl.json"
CHARACTERS = ROOT / "docs/sun-salutation-flat.json"
BUILD = ROOT / "build/sun-salutation-flat"


def load_girl_renderer():
    spec = importlib.util.spec_from_file_location(
        "sun_salutation_girl", ROOT / "scripts/render-sun-salutation-girl.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GIRL = load_girl_renderer()
add, sub, mul, mix = GIRL.add, GIRL.sub, GIRL.mul, GIRL.mix
unit, rotate, wrap, ease, smoothstep = GIRL.unit, GIRL.rotate, GIRL.wrap, GIRL.ease, GIRL.smoothstep


def colour(value):
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


# The rig's poses were placed for the painted parts. These ankles let the
# drawn feet reach the floor in plank and upward-facing dog.
POSE_CHANGES = {
    "plank": {"ankles": [441, 395]},
    "low": {"ankles": [441, 395]},
    "stepBack": {"farAnkle": [441, 395]},
    "upDog": {"ankles": [458, 421]},
}


# Shapes -------------------------------------------------------------------

def circle(center, radius, count=40):
    return [add(center, mul(unit(math.tau * index / count), radius)) for index in range(count)]


def hull(points):
    """Convex hull, counter-clockwise in y-down screen space."""
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def cross(origin, a, b):
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

    lower, upper = [], []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def blob(circles):
    """The hull of (center, radius) circles: a rounded, tapering limb part."""
    points = []
    for center, radius in circles:
        points.extend(circle(center, radius, 32))
    return hull(points)


def signed_area(points):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])) / 2


def oriented(points):
    """Every outline runs the same way, so overlapping parts fill as one."""
    return points if signed_area(points) > 0 else list(reversed(points))


def smooth(points, closed=True, samples=8):
    """Dense Catmull-Rom outline through points; a point given as
    (x, y, 0) is a sharp corner."""
    count = len(points)
    result = []
    segments = count if closed else count - 1
    for index in range(segments):
        p1, p2 = points[index], points[(index + 1) % count]
        p0 = points[(index - 1) % count] if closed or index > 0 else p1
        p3 = points[(index + 2) % count] if closed or index + 2 < count else p2
        tension1 = 0.0 if len(p1) > 2 else 1.0
        tension2 = 0.0 if len(p2) > 2 else 1.0
        c1 = add(p1[:2], mul(sub(p2[:2], p0[:2]), tension1 / 6))
        c2 = sub(p2[:2], mul(sub(p3[:2], p1[:2]), tension2 / 6))
        for step in range(samples):
            t = step / samples
            u = 1 - t
            result.append(tuple(
                u ** 3 * p1[axis] + 3 * u * u * t * c1[axis] + 3 * u * t * t * c2[axis] + t ** 3 * p2[axis]
                for axis in (0, 1)))
    if not closed:
        result.append(points[-1][:2])
    return result


def fill(ctx, shapes, rgb, alpha=1.0):
    """Fill several outlines as one shape in one colour."""
    for shape in shapes:
        if len(shape) < 3:
            continue
        shape = oriented(shape)
        ctx.move_to(*shape[0])
        for point in shape[1:]:
            ctx.line_to(*point)
        ctx.close_path()
    ctx.set_source_rgba(*colour(rgb), alpha)
    ctx.fill()


def outline_path(ctx, shapes):
    for shape in shapes:
        shape = oriented(shape)
        ctx.move_to(*shape[0])
        for point in shape[1:]:
            ctx.line_to(*point)
        ctx.close_path()


def stroke(ctx, points, rgb, width):
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    ctx.set_source_rgb(*colour(rgb))
    ctx.set_line_width(width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def profile(stops, share):
    """Smoothly interpolated value between (share, value) stops."""
    for (first, low), (second, high) in zip(stops, stops[1:]):
        if share <= second:
            amount = (share - first) / max(second - first, 1e-9)
            return low + (high - low) * amount * amount * (3 - 2 * amount)
    return stops[-1][1]


def place(points, origin, angle):
    return [add(origin, rotate(point[:2], angle)) for point in points]


# Character design, in rig units ---------------------------------------------

def shade(value, amount):
    """The colour darkened by amount, or lightened by a negative amount."""
    rgb = colour(value)
    if amount >= 0:
        rgb = [channel * (1 - amount) for channel in rgb]
    else:
        rgb = [channel + (1 - channel) * -amount for channel in rgb]
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)


def palette(colors):
    """A character's colours with its far limbs, shades and highlights."""
    return {
        **colors,
        "skinFar": shade(colors["skin"], 0.1),
        "topFar": shade(colors["top"], 0.2),
        "topShade": shade(colors["top"], 0.13),
        "pantsFar": shade(colors["pants"], 0.22),
        "pantsShade": shade(colors["pants"], 0.14),
        "cuffFar": shade(colors["cuff"], 0.2),
        "hairLight": shade(colors["hair"], -0.2),
        "mouth": shade(colors["skin"], 0.22),
        "blush": "#ec9f8f",
    }


# Torsos: outlines as (distance up the spine from the hip, forward offset),
# the hem band's top edge, the seat under the top and the base of the neck.
TORSOS = {
    "tunic": {
        "outline": [
            (-12, 33, 0), (10, 27), (40, 23), (70, 25.5), (96, 23), (110, 13), (116, 6),
            (117.5, -6), (114, -16), (98, -24), (68, -23), (40, -23), (12, -29),
            (-14, -36, 0), (-16.5, -2),
        ],
        "hem": [(-9, -50), (-11.5, -2), (-7, 50)],
        "seat": ((-2, -8), 20),
        "neck": (114, 2),
    },
    "tunicMale": {
        "outline": [
            (-12, 33, 0), (10, 28), (40, 25), (72, 27), (97, 25.5), (110, 14.5), (116.5, 7),
            (118, -7), (114.5, -19), (98, -27), (68, -25), (40, -23.5), (12, -29),
            (-14, -36, 0), (-16.5, -2),
        ],
        "hem": [(-9, -50), (-11.5, -2), (-7, 50)],
        "seat": ((-2, -8), 20),
        "neck": (115, 1.5),
    },
    "fitted": {
        "outline": [
            (-7, 24, 0), (12, 21), (40, 17.5), (64, 20), (80, 23.5), (98, 18.5), (111, 10),
            (116.5, 4), (117.5, -6), (114, -14.5), (98, -21), (70, -19), (42, -17.5),
            (16, -22.5), (-9, -27.5, 0), (-10.5, -2),
        ],
        "hem": [(-4.5, -50), (-6.5, -2), (-3, 50)],
        "seat": ((-2, -9), 19),
        "neck": (114, 2),
    },
    "male": {
        "outline": [
            (-7, 24, 0), (12, 22), (42, 21), (72, 24.5), (98, 24), (111, 14), (116.5, 6),
            (118, -7), (114.5, -18.5), (98, -26), (70, -23), (42, -19.5), (16, -22.5),
            (-9, -27.5, 0), (-10.5, -2),
        ],
        "hem": [(-4.5, -50), (-6.5, -2), (-3, 50)],
        "seat": ((-2, -9), 18.5),
        "neck": (115, 1.5),
    },
}

# Legs: thigh radii at hip, middle and knee; shin radii at knee and calf;
# where the trousers end (units above the ankle, half width); an optional
# darker band at their end (from, to units above the ankle, half widths).
LEGS = {
    "loose": {"thigh": (19.5, 17.5, 14.0), "shin": (14.0, 13.6), "end": (12, 11.5),
              "band": (13, 4.5, 9.4, 9.0)},
    "leggings": {"thigh": (18.0, 15.8, 11.4), "shin": (11.2, 11.9), "end": (3.5, 7.8), "band": None},
    "trousers": {"thigh": (19.0, 17.0, 13.2), "shin": (13.0, 12.6), "end": (4.5, 10.6),
                 "band": (10, 4.5, 10.6, 10.6)},
}

# Sleeves: upper arm radii at shoulder, middle and elbow; forearm radius at
# the elbow; where the sleeve ends (units before the wrist, half width); the
# cuff band (from, to units before the wrist, half widths).
SLEEVES = {
    "bell": {"upper": (11.2, 10.6, 8.8), "elbow": 8.6, "end": (6, 10.4), "cuff": (6.5, 0.5, 10.3, 11.4)},
    "bellMale": {"upper": (12.2, 11.6, 9.6), "elbow": 9.4, "end": (6, 11.2), "cuff": (6.5, 0.5, 11.1, 12.2)},
    "fitted": {"upper": (10.2, 9.6, 7.6), "elbow": 7.4, "end": (1.5, 6.4), "cuff": (5.5, 1.5, 6.5, 6.6)},
    "fittedMale": {"upper": (11.4, 10.8, 8.6), "elbow": 8.4, "end": (1.5, 7.2), "cuff": (5.5, 1.5, 7.3, 7.4)},
}

# Heads, in their own frame: the neck base at the origin, facing +x, up is
# -y; the frame is scaled by "scale" about the neck base.
FACES = {
    "female": {
        "outline": [
            (3, -77), (19, -71), (27, -60), (29, -51), (28.5, -46.5), (30, -43.5), (33.2, -38.6),
            (29.5, -35.6), (30.2, -32.2), (28.2, -30.4), (29, -28.2), (26.2, -23.4), (19, -19.6),
            (8, -21), (-12, -27), (-23, -40), (-22, -62),
        ],
        "scale": 1.22, "neck": [((0.5, 5), 8.2), ((3, -17), 7.6)],
        "blush": 0.55, "lash": True, "brow": [(17, -53), (21.5, -55), (26, -53.5)], "browWidth": 1.2,
        "mouth": [(28.6, -31.2), (25.6, -31.0)],
    },
    "male": {
        "outline": [
            (3, -77), (19, -72), (27, -62), (29.5, -52), (28.8, -47), (31, -43.5), (35, -37.6),
            (30.6, -35), (30.8, -31.8), (28.8, -30.2), (29.8, -27.8), (28.8, -22.5), (24, -17.2),
            (10, -18.5), (-10, -26), (-23, -40), (-22, -62),
        ],
        "scale": 1.2, "neck": [((0.5, 5), 9.4), ((3, -16), 8.8)],
        "blush": 0.0, "lash": False, "brow": [(16.5, -53), (21.5, -54.5), (26.5, -54)], "browWidth": 2.0,
        "mouth": [(29.2, -31.4), (25.8, -31.2)],
    },
}
EYE = (21, -45.5)
BLUSH = ((16.5, -35.5), 4.6)
CRANIUM = (2, -48)
EAR = [(-1, -49.5), (3, -46), (3.6, -39), (0.5, -33.5), (-3.5, -35.5), (-5, -43)]
EAR_FOLD = [(0.2, -45.5), (1.6, -41), (-0.2, -37)]

# Hair: the cap over the skull, an optional bun (center, radius) with its
# tie, an optional hanging strand (two roots in the head frame, joints, and
# its half width as (share of its length, half width) stops), and whether
# the ear shows.
HAIRS = {
    "bunLong": {
        "cap": [
            (27.5, -61.5), (30.5, -56, 0), (21, -57.5), (13, -53), (7.5, -45), (8, -31.5),
            (3.5, -28.5), (-6, -27.5), (-13, -25), (-22, -30), (-29.5, -46), (-25, -68),
            (-8, -81), (12, -79),
        ],
        "bun": ((-7.5, -89), 15),
        "strand": {"roots": [(-20.5, -40), (-17, -30)], "count": 9,
                   "width": [(0, 11), (0.5, 7.4), (1, 3.5)], "tie": False},
        "ear": False,
    },
    "ponytail": {
        "cap": [
            (26, -63.5), (30.5, -56.5, 0), (22, -58.5), (14, -55.5), (8, -51), (4, -49.5),
            (-3, -51.5), (-8, -46), (-12, -35), (-19, -30), (-27, -38), (-30.5, -52),
            (-25, -69), (-8, -81), (12, -79.5),
        ],
        "bun": None,
        "strand": {"roots": [(-25, -57), (-29.5, -52)], "count": 7,
                   "width": [(0, 5), (0.08, 5.5), (0.3, 9.5), (0.75, 6), (1, 2.2)], "tie": True},
        "ear": True,
    },
    "bun": {
        "cap": [
            (26, -63.5), (30.5, -56.5, 0), (22, -58.5), (14, -55.5), (8, -51), (4, -49.5),
            (-3, -51.5), (-8, -46), (-12, -35), (-19, -30), (-27, -38), (-30.5, -52),
            (-25, -69), (-8, -81), (12, -79.5),
        ],
        "bun": ((-20, -75), 13),
        "strand": None,
        "ear": True,
    },
    "crop": {
        "cap": [
            (25, -67), (31.5, -64.5, 0), (23, -62), (14, -58), (9, -52), (7.5, -44), (8, -38.5, 0),
            (4, -44), (-2, -51), (-9, -46), (-13, -36), (-20, -36.5), (-25.5, -47), (-25.5, -63),
            (-12, -81), (8, -84), (21, -78),
        ],
        "bun": None,
        "strand": None,
        "ear": True,
    },
    "short": {
        "cap": [
            (25, -66), (28, -62.5, 0), (19, -62), (12, -57), (8.5, -50), (7.5, -44), (8, -39, 0),
            (4, -44), (-2, -51), (-9, -46), (-13, -36), (-20, -36.5), (-25.5, -47), (-25.5, -63),
            (-12, -80.5), (8, -82), (20, -77),
        ],
        "bun": None,
        "strand": None,
        "ear": True,
    },
}

# The far arm sits only a little behind the near one, so praying hands overlap.
FAR_ARM = (-3, -1)

# Upright hand, wrist at the origin, fingers up (-y), thumb at the back (-x).
HAND_UPRIGHT = [
    (-5.5, 5), (-6.2, -11.5), (-5.1, -24.5), (-1.8, -31), (2.9, -29.8), (5.1, -21),
    (9.4, -14), (7.6, -7), (5.5, 5),
]
# The same outline lying flat: (dx from the wrist, dy from the wrist or the
# floor, measured from "wrist" or "floor").
HAND_FLAT = [
    ((-3, -5), "wrist"), ((13, -9), "floor"), ((24, -7), "floor"), ((33, -3.6), "floor"),
    ((35, -0.8), "floor"), ((24, 0), "floor"), ((10, 0), "floor"), ((1, 0), "floor"),
    ((-4.5, -4), "floor"),
]

# Foot, ankle at the origin, standing, toes at +x. The toes bend about BALL.
FOOT_REAR = [(-6, -3), (-10.5, 6.5), (-8.5, 15.5), (-2, 18.2), (14, 17.4), (27, 18.2)]
BALL = (32, 12.5)
TOES = [(0, 5.7), (11, 5.2), (14.2, 3), (12.6, -0.6), (2, -2.6)]
FOOT_TOP = [(18, 4.5), (6.5, -5.5)]


class Figure:
    """One drawn character on the rig's timeline."""

    def __init__(self, rig, style, character, width, height, fps):
        self.rig = rig
        self.timeline = GIRL.Timeline(rig)
        self.ground = rig["ground"]
        self.bones = rig["bones"]
        self.frame_step = 1 / fps
        self.width, self.height = width, height
        self.background = style["background"]
        self.shadow = style["shadow"]
        self.character = character
        self.colors = palette(character["colors"])
        self.torso = TORSOS[character["torso"]]
        self.legs = LEGS[character["legs"]]
        self.sleeves = SLEEVES[character["sleeves"]]
        self.face = FACES[character["face"]]
        self.hairstyle = HAIRS[character["hair"]]
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)
        self.hair = None
        self.hair_time = None

    # Placement ----------------------------------------------------------

    def body(self, p, point):
        """A (distance up the spine, forward offset) point in rig space."""
        forward = (-math.sin(p.spine), math.cos(p.spine))
        return add(add(p.hip, mul(unit(p.spine), point[0])), mul(forward, point[1]))

    def body_shape(self, p, points):
        return [self.body(p, point) for point in points]

    def head_turn(self, p):
        head = self.rig["head"]
        lift = wrap(p.gaze - p.spine) * head["lift"]
        lift = max(math.radians(head["liftMin"]), min(math.radians(head["liftMax"]), lift))
        return p.spine + lift + math.pi / 2

    def head_point(self, p, point):
        scaled = mul(point, self.face["scale"])
        return add(self.body(p, self.torso["neck"]), rotate(scaled, self.head_turn(p)))

    # Feet ----------------------------------------------------------------

    @staticmethod
    def foot_outline(angle, bend):
        """Foot outline about the ankle: rear foot turned by angle, toes bent
        by bend about the ball."""
        ball = rotate(BALL, angle)
        toes = [add(ball, rotate(point, angle + bend)) for point in TOES]
        return [rotate(point, angle) for point in FOOT_REAR] + toes + [rotate(point, angle) for point in FOOT_TOP]

    def lowest(self, angle, bend):
        return max(point[1] for point in self.foot_outline(angle, bend))

    def solve(self, height, start, end, bend):
        """The angle between start and end at which the foot just touches a
        floor `height` below the ankle; the foot sinks as the angle moves
        from start to end."""
        if self.lowest(start, bend(start)) >= height:
            return start
        if self.lowest(end, bend(end)) <= height:
            return end
        low, high = start, end
        for _ in range(30):
            middle = (low + high) / 2
            if self.lowest(middle, bend(middle)) < height:
                low = middle
            else:
                high = middle
        return (low + high) / 2

    def plant_foot(self, p, ankle, knee, airborne):
        """(ankle, angle, bend) for a foot: lying flat, on tucked toes, or on
        its instep, lifted so it never sinks into the floor."""
        height = self.ground - ankle[1]
        tucked = self.solve(height, 0.0, 1.2, lambda angle: -angle)
        instep = self.solve(height, 2.75, 1.6, lambda angle: 0.15)
        share = ease(p.instep)
        angle = tucked + (instep - tucked) * share
        bend = -tucked * (1 - share) + 0.15 * share
        if airborne > 0:
            shin = math.atan2(ankle[1] - knee[1], ankle[0] - knee[0])
            pointed = shin - math.pi / 2 + self.rig["feet"]["pointToes"]
            amount = smoothstep(0.0, 0.5, airborne)
            angle += wrap(pointed - angle) * amount
            bend += (0.1 - bend) * amount
        sink = self.lowest(angle, bend) - height
        if sink > 0:
            ankle = (ankle[0], ankle[1] - sink)
        return ankle, angle, bend

    # Limbs ----------------------------------------------------------------

    def leg(self, p, far, airborne):
        offset = tuple(self.bones["farOffset"]) if far else (0, 0)
        hip = add(p.hip, offset)
        target = add(p.far_ankle if far else p.near_ankle, offset)
        knee, _ = GIRL.joint(hip, target, self.bones["thigh"], self.bones["shin"], -1)
        target, angle, bend = self.plant_foot(p, target, knee, airborne)
        knee, ankle = GIRL.joint(hip, target, self.bones["thigh"], self.bones["shin"], -1)
        return hip, knee, ankle, angle, bend

    def arm(self, p, far):
        offset = FAR_ARM if far else (0, 0)
        shoulder = add(p.shoulder, offset)
        target = add(p.far_wrist if far else p.near_wrist, offset)
        elbow, wrist = GIRL.joint(shoulder, target, self.bones["upperArm"], self.bones["forearm"], 1)
        return shoulder, elbow, wrist

    @staticmethod
    def along(a, b, amount, back=0.0):
        """A point amount of the way from a to b, moved back (to the left of
        the bone's direction) by back units."""
        direction = GIRL.normalize(sub(b, a))
        normal = (direction[1], -direction[0])
        return add(mix(a, b, amount), mul(normal, back))

    @staticmethod
    def band(a, b, start, end, half_start, half_end):
        """A straight band across the bone a→b, from start to end units
        before b, half_start and half_end wide."""
        direction = GIRL.normalize(sub(b, a))
        normal = (direction[1], -direction[0])
        first, second = sub(b, mul(direction, start)), sub(b, mul(direction, end))
        return [add(first, mul(normal, half_start)), add(second, mul(normal, half_end)),
                sub(second, mul(normal, half_end)), sub(first, mul(normal, half_start))]

    def leg_shapes(self, hip, knee, ankle):
        legs = self.legs
        hip_radius, middle_radius, knee_radius = legs["thigh"]
        shin_radius, calf_radius = legs["shin"]
        end, end_half = legs["end"]
        thigh = blob([(hip, hip_radius), (self.along(hip, knee, 0.45, 1.5), middle_radius), (knee, knee_radius)])
        shin_end = self.band(knee, ankle, end, end, end_half, end_half)
        shin = hull(circle(knee, shin_radius, 32) + circle(self.along(knee, ankle, 0.35, 1.5), calf_radius, 32)
                    + [shin_end[0], shin_end[3]])
        band = self.band(knee, ankle, *legs["band"]) if legs["band"] else None
        ankle_skin = blob([(ankle, 6.4), (self.along(knee, ankle, 0.9), 6.2)])
        return [thigh, shin], band, ankle_skin

    def arm_shapes(self, shoulder, elbow, wrist):
        sleeves = self.sleeves
        shoulder_radius, middle_radius, elbow_radius = sleeves["upper"]
        end, end_half = sleeves["end"]
        upper = blob([(shoulder, shoulder_radius), (self.along(shoulder, elbow, 0.35, 0.8), middle_radius),
                      (elbow, elbow_radius)])
        sleeve_end = self.band(elbow, wrist, end, end, end_half, end_half)
        forearm = hull(circle(elbow, sleeves["elbow"], 32) + [sleeve_end[0], sleeve_end[3]])
        cuff = self.band(elbow, wrist, *sleeves["cuff"])
        return [upper, forearm], cuff

    def hand_shape(self, p, elbow, wrist):
        forearm = math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0])
        turn = wrap(forearm + math.pi / 2) * (1 - p.upright)
        upright = place(HAND_UPRIGHT, wrist, turn)
        flat = smoothstep(0.2, 0.9, p.palm) * (1 - smoothstep(16, 34, self.ground - wrist[1]))
        if flat <= 0:
            return upright
        lying = []
        for (dx, dy), base in HAND_FLAT:
            lying.append((wrist[0] + dx, (wrist[1] if base == "wrist" else self.ground) + dy))
        return [mix(a, b, flat) for a, b in zip(upright, lying)]

    # Hair -----------------------------------------------------------------

    def update_hair(self, p, time):
        """Advance the hanging hair to `time` exactly as the video does: from
        rest at 0 s, one step per video frame."""
        strand = self.hairstyle["strand"]
        if strand is None:
            return
        if self.hair_time is None or time < self.hair_time - 1e-9:
            start = self.timeline.sample(0.0)
            self.hair = GIRL.Hair(dict(self.rig["hair"], count=strand["count"]), self.ground)
            self.hair.reset(tuple(self.head_point(start, root) for root in strand["roots"]))
            self.hair_time = 0.0
        frame = round(self.hair_time / self.frame_step)
        target = round(time / self.frame_step)
        for index in range(frame + 1, target):
            self.advance_hair(self.timeline.sample(index * self.frame_step), index * self.frame_step)
        if target > frame:
            self.advance_hair(p, time)

    def advance_hair(self, p, time):
        roots = tuple(self.head_point(p, root) for root in self.hairstyle["strand"]["roots"])
        self.hair.step(roots, time - self.hair_time, self.back_collider(p))
        self.hair_time = time

    def back_collider(self, p):
        """Keep the hair outside the back while the body is upright."""
        axis = unit(p.spine)
        forward = (-math.sin(p.spine), math.cos(p.spine))
        strength = 1 - smoothstep(0.2, 0.5, forward[1])
        if strength <= 0:
            return None
        back = sorted((point[0], point[1]) for point in self.torso["outline"] if point[1] < 0)
        heights = [point[0] for point in back]
        depths = [point[1] for point in back]

        def collide(point):
            offset = sub(point, p.hip)
            height = offset[0] * axis[0] + offset[1] * axis[1]
            depth = offset[0] * forward[0] + offset[1] * forward[1]
            if not heights[0] <= height <= heights[-1]:
                return point
            limit = depths[0]
            for (h0, d0), (h1, d1) in zip(back, back[1:]):
                if h0 <= height <= h1:
                    limit = d0 + (d1 - d0) * (height - h0) / max(h1 - h0, 1e-9)
                    break
            limit -= 4
            if limit < depth < 6:
                return add(point, mul(forward, (limit - depth) * strength))
            return point

        return collide

    def hair_shape(self):
        stops = self.hairstyle["strand"]["width"]
        points = GIRL.spline_points(self.hair.points, 5)
        lengths = [0.0]
        for a, b in zip(points[:-1], points[1:]):
            lengths.append(lengths[-1] + math.dist(a, b))
        total = max(lengths[-1], 1e-9)
        left, right = [], []
        for index, point in enumerate(points):
            ahead = points[min(index + 1, len(points) - 1)]
            behind = points[max(index - 1, 0)]
            direction = GIRL.normalize(sub(ahead, behind))
            normal = (direction[1], -direction[0])
            share = lengths[index] / total
            half = profile(stops, share)
            left.append(add(point, mul(normal, half)))
            right.append(sub(point, mul(normal, half)))
        return [left + list(reversed(right)), circle(points[0], stops[0][1]), circle(points[-1], stops[-1][1])]

    # Drawing --------------------------------------------------------------

    def ground_shadow(self, ctx, p):
        xs = [p.near_ankle[0], p.far_ankle[0], p.near_wrist[0], p.far_wrist[0], p.hip[0]]
        left, right = min(xs) - 34, max(xs) + 44
        ctx.save()
        ctx.translate((left + right) / 2, self.ground + 1)
        ctx.scale((right - left) / 2, 6.5)
        ctx.arc(0, 0, 1, 0, math.tau)
        ctx.restore()
        ctx.set_source_rgba(*colour(self.shadow), 0.12)
        ctx.fill()

    def draw_leg(self, ctx, leg, far):
        colors = self.colors
        hip, knee, ankle, angle, bend = leg
        foot = place(smooth(self.foot_outline(angle, bend), samples=6), ankle, 0.0)
        shapes, band, ankle_skin = self.leg_shapes(hip, knee, ankle)
        fill(ctx, [foot, ankle_skin], colors["skinFar" if far else "skin"])
        fill(ctx, shapes, colors["pantsFar" if far else "pants"])
        if band:
            fill(ctx, [band], colors["pantsFar"] if far else colors["pantsShade"])

    def draw_arm(self, ctx, p, arm, far, torso=None):
        colors = self.colors
        shoulder, elbow, wrist = arm
        hand = smooth(self.hand_shape(p, elbow, wrist), samples=6)
        fill(ctx, [hand], colors["skinFar" if far else "skin"])
        shapes, cuff = self.arm_shapes(shoulder, elbow, wrist)
        if torso is not None:
            # The near arm casts a crisp shade on the top where it crosses it.
            ctx.save()
            outline_path(ctx, [torso])
            ctx.clip()
            fill(ctx, [[add(point, (-2.4, 3.2)) for point in shape] for shape in shapes], colors["topShade"])
            ctx.restore()
        fill(ctx, shapes, colors["topFar" if far else "top"])
        fill(ctx, [cuff], colors["cuffFar" if far else "cuff"])

    def draw_torso(self, ctx, p):
        torso = self.body_shape(p, smooth(self.torso["outline"]))
        fill(ctx, [torso], self.colors["top"])
        ctx.save()
        outline_path(ctx, [torso])
        ctx.clip()
        band = smooth(self.torso["hem"], closed=False) + [(-60, 40), (-60, -40)]
        fill(ctx, [self.body_shape(p, band)], self.colors["topShade"])
        ctx.restore()
        return torso

    def draw_neck(self, ctx, p):
        neck = [mul(point, self.face["scale"]) for point in blob(self.face["neck"])]
        fill(ctx, [place(neck, self.body(p, self.torso["neck"]), self.head_turn(p))], self.colors["skin"])

    def draw_head(self, ctx, p):
        colors, face, hairstyle = self.colors, self.face, self.hairstyle
        origin, turn = self.body(p, self.torso["neck"]), self.head_turn(p)

        def head(points):
            return place([mul(point[:2], face["scale"]) for point in points], origin, turn)

        fill(ctx, [head(smooth(face["outline"]))], colors["skin"])
        if face["blush"]:
            center, radius = BLUSH
            fill(ctx, [head(circle(center, radius))], colors["blush"], face["blush"])
        eye = [(EYE[0] + 4.6 * math.cos(angle), EYE[1] + 3.2 * math.sin(angle))
               for angle in [math.radians(value) for value in range(15, 170, 10)]]
        stroke(ctx, head(eye), colors["hair"] if face["lash"] else shade(colors["hair"], 0.3), 1.7)
        if face["lash"]:
            stroke(ctx, head([(EYE[0] - 4.2, EYE[1] + 1.0), (EYE[0] - 6.4, EYE[1] + 2.6)]), colors["hair"], 1.3)
        stroke(ctx, head(smooth(face["brow"], closed=False, samples=6)), colors["hair"], face["browWidth"])
        stroke(ctx, head(face["mouth"]), colors["mouth"], 1.1)
        shapes = [head(smooth(hairstyle["cap"]))]
        if hairstyle["bun"]:
            center, radius = hairstyle["bun"]
            shapes.append(head(circle(center, radius, 48)))
        fill(ctx, shapes, colors["hair"])
        if hairstyle["bun"]:
            self.draw_bun_details(ctx, head)
        if hairstyle["ear"]:
            fill(ctx, [head(smooth(EAR))], colors["skin"])
            stroke(ctx, head(smooth(EAR_FOLD, closed=False, samples=4)), colors["mouth"], 1.0)
        strand = hairstyle["strand"]
        if strand and strand["tie"]:
            # The tie wraps the strand a little below where it leaves the head.
            points = self.hair.points
            direction = GIRL.normalize(sub(points[2], points[1]))
            normal = (direction[1], -direction[0])
            center = add(points[1], mul(direction, 1.5))
            half = strand["width"][1][1] - 1.2
            stroke(ctx, [add(center, mul(normal, half)), sub(center, mul(normal, half))],
                   colors["accent"], 4.4)

    def draw_bun_details(self, ctx, head):
        """Wrapped strands across the bun, and the tie where it meets the head."""
        colors = self.colors
        center, radius = self.hairstyle["bun"]
        base = math.degrees(math.atan2(CRANIUM[1] - center[1], CRANIUM[0] - center[0]))
        top = base + 180
        for offset, size, start, end in ((0.6, 1.13, -42, 42), (0.33, 0.8, -55, 30)):
            middle = add(center, mul(unit(math.radians(base)), radius * offset))
            arc = [add(middle, mul(unit(math.radians(top + value)), radius * size))
                   for value in range(start, end + 1, 6)]
            stroke(ctx, head(arc), colors["hairLight"], 1.4)
        tie = [add(center, mul(unit(math.radians(base + value)), radius - 1)) for value in range(-35, 36, 5)]
        stroke(ctx, head(tie), colors["accent"], 2.4 * 2 * self.face["scale"])

    def frame(self, time):
        ctx = self.ctx
        p = self.timeline.sample(time)
        feet = self.timeline.feet(p, time)
        self.update_hair(p, time)
        camera = self.rig["camera"]
        ctx.save()
        ctx.set_source_rgb(*colour(self.background))
        ctx.paint()
        ctx.scale(self.width / camera["designWidth"], self.height / camera["designHeight"])
        ctx.translate(camera["centerX"], camera["groundY"])
        ctx.scale(camera["scale"], camera["scale"])
        ctx.translate(-camera["rigX"], -self.ground)
        self.ground_shadow(ctx, p)
        far_leg = self.leg(p, True, feet[True][1])
        near_leg = self.leg(p, False, feet[False][1])
        # Back to front: far leg and arm, the hanging hair, near leg and
        # seat, neck, top, head, near arm.
        self.draw_leg(ctx, far_leg, far=True)
        self.draw_arm(ctx, p, self.arm(p, True), far=True)
        if self.hairstyle["strand"]:
            fill(ctx, self.hair_shape(), self.colors["hair"])
        self.draw_leg(ctx, near_leg, far=False)
        center, radius = self.torso["seat"]
        fill(ctx, [self.body_shape(p, circle(center, radius))], self.colors["pants"])
        self.draw_neck(ctx, p)
        torso = self.draw_torso(ctx, p)
        self.draw_head(ctx, p)
        self.draw_arm(ctx, p, self.arm(p, False), far=False, torso=torso)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def load_rig():
    rig = json.loads(RIG.read_text())
    for name, changes in POSE_CHANGES.items():
        rig["poses"][name].update(changes)
    return rig


def write_chapters(rig, timeline, target):
    lines = [";FFMETADATA1", "title=Sun salutation"]
    for index, name in enumerate(rig["names"]):
        start = index * timeline.period * 1000
        end = min(start + timeline.period * 1000, timeline.duration * 1000)
        lines.extend(("[CHAPTER]", "TIMEBASE=1/1000", f"START={start:.0f}", f"END={end:.0f}", f"title={name}"))
    target.write_text("\n".join(lines) + "\n")


def encode(rig, timeline, target, width, height, fps, frames):
    """Pipe BGRA frames into an H.264 MP4 with the pose chapters."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        chapters = Path(directory) / "chapters.txt"
        write_chapters(rig, timeline, chapters)
        run_encoder(target, width, height, fps, chapters, frames)
    print(f"Saved {target}", flush=True)


def run_encoder(target, width, height, fps, chapters, frames):
    encoder = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pixel_format", "bgra", "-video_size", f"{width}x{height}",
        "-framerate", str(fps), "-i", "pipe:0", "-f", "ffmetadata", "-i", str(chapters),
        "-map", "0:v:0", "-map_metadata", "1", "-map_chapters", "1", "-an",
        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-threads", "4",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target),
    ], stdin=subprocess.PIPE)
    try:
        for data in frames:
            encoder.stdin.write(data)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError(f"Encoding failed: {target}")


def render(rig, style, character, output, width, height, fps):
    figure = Figure(rig, style, character, width, height, fps)
    timeline = figure.timeline
    frames = (figure.frame(frame / fps) for frame in range(round(timeline.duration * fps)))
    encode(rig, timeline, output / f"{character['id']}.mp4", width, height, fps, frames)


def render_grid(rig, style, characters, output, width, height, fps, columns=3):
    """All characters side by side, numbered, to choose between them."""
    figures = [Figure(rig, style, character, width, height, fps) for character in characters]
    rows = math.ceil(len(figures) / columns)
    grid = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * columns, height * rows)
    ctx = cairo.Context(grid)
    timeline = figures[0].timeline

    def frames():
        for frame in range(round(timeline.duration * fps)):
            ctx.set_source_rgb(*colour(style["background"]))
            ctx.paint()
            for index, figure in enumerate(figures):
                figure.frame(frame / fps)
                x, y = index % columns * width, index // columns * height
                ctx.set_source_surface(figure.surface, x, y)
                ctx.paint()
                ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                ctx.set_font_size(height * 0.045)
                ctx.set_source_rgb(*colour(style["shadow"]))
                ctx.move_to(x + width * 0.03, y + height * 0.08)
                ctx.show_text(f"{index + 1}  {figure.character['name']}")
            for column in range(1, columns):
                ctx.rectangle(column * width - 1, 0, 2, height * rows)
            for row in range(1, rows):
                ctx.rectangle(0, row * height - 1, width * columns, 2)
            ctx.set_source_rgb(*colour(shade(style["background"], 0.08)))
            ctx.fill()
            grid.flush()
            yield grid.get_data()

    encode(rig, timeline, output / "choose-characters.mp4", width * columns, height * rows, fps, frames())


def main():
    rig = load_rig()
    style = json.loads(CHARACTERS.read_text())
    characters = {character["id"]: character for character in style["characters"]}
    output = rig["output"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", choices=list(characters), default=style["characters"][0]["id"])
    parser.add_argument("--all", action="store_true", help="render every character's video")
    parser.add_argument("--grid", action="store_true", help="render all characters side by side at half size")
    parser.add_argument("--output", type=Path, default=BUILD)
    parser.add_argument("--width", type=int, default=output["width"])
    parser.add_argument("--height", type=int, default=output["height"])
    parser.add_argument("--fps", type=int, default=output["fps"])
    parser.add_argument("--still", type=float, action="append", help="render a PNG at this time in seconds")
    options = parser.parse_args()
    if options.grid:
        render_grid(rig, style, style["characters"], options.output,
                    options.width // 2, options.height // 2, options.fps)
        return
    chosen = style["characters"] if options.all else [characters[options.character]]
    for character in chosen:
        if options.still:
            figure = Figure(rig, style, character, options.width, options.height, options.fps)
            for still in sorted(options.still):
                figure.frame(still)
                target = options.output / "stills" / f"{character['id']}-{still:g}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                figure.surface.write_to_png(str(target))
                print(target, flush=True)
        else:
            render(rig, style, character, options.output, options.width, options.height, options.fps)


if __name__ == "__main__":
    main()
