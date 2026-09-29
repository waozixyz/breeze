#!/usr/bin/env python3
"""Render complete, continuous Sun Salutation A review videos.

Requires Python 3, pycairo, and FFmpeg. Rendering never opens a display.
The pose timeline and articulated illustration remain editable here rather
than being baked into a pose atlas. See docs/sun-salutation-animation.md.
"""

import argparse
from dataclasses import dataclass, replace
import math
from pathlib import Path
import subprocess
import tempfile

import cairo


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/practices/sunsalutation/animations"
FPS = 30
STEP_SECONDS = 8.0
TRANSITION_SECONDS = 3.0
NAMES = (
    "Mountain pose", "Upward salute", "Standing forward fold", "Half lift",
    "Plank", "Low plank", "Upward-facing dog", "Downward-facing dog",
    "Half lift", "Standing forward fold", "Upward salute", "Mountain pose",
)
Point = tuple[float, float]


def add(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1]


def sub(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def mul(a: Point, value: float) -> Point:
    return a[0] * value, a[1] * value


def mix(a: Point, b: Point, amount: float) -> Point:
    return add(mul(a, 1.0 - amount), mul(b, amount))


def unit(angle: float) -> Point:
    return math.cos(angle), math.sin(angle)


def smooth(amount: float) -> float:
    amount = min(1.0, max(0.0, amount))
    return amount ** 3 * (amount * (amount * 6.0 - 15.0) + 10.0)


def color(value: str) -> tuple[float, float, float]:
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def source(ctx: cairo.Context, value: str, alpha: float = 1.0) -> None:
    ctx.set_source_rgba(*color(value), alpha)


@dataclass(frozen=True)
class Pose:
    hip: Point
    spine: float
    gaze: float
    near_ankle: Point
    far_ankle: Point
    near_wrist: Point
    far_wrist: Point
    knee: float = -1.0
    elbow: float = 1.0
    foot: float = 0.0
    arch: float = 0.0

    @property
    def shoulder(self) -> Point:
        return add(self.hip, mul(unit(self.spine), 110.0))


def pose(hip, spine, gaze, ankle, wrist, **kwargs) -> Pose:
    return Pose(hip, math.radians(spine), math.radians(gaze),
                ankle, ankle, wrist, wrist, **kwargs)


MOUNTAIN = pose((626, 246), -91, -88, (630, 435), (660, 143))
SALUTE = pose((624, 246), -98, -104, (630, 435), (602, 15),
              elbow=-1.0, arch=-4.0)
FOLD = pose((622, 246), 82, 56, (630, 435), (661, 429),
            elbow=1.0, arch=3.0)
LIFT = pose((620, 246), 2, -7, (630, 435), (639, 334), elbow=1.0)
PLANK = pose((613, 306), 0, -8, (450, 407), (727, 430),
             knee=1.0, elbow=-1.0, foot=0.8)
LOW = pose((636, 376), -4, -8, (450, 407), (727, 430),
           knee=1.0, elbow=1.0, foot=0.8)
UP_DOG = pose((610, 393), -48, -67, (426, 432), (727, 430),
              knee=1.0, elbow=-1.0, foot=0.0, arch=-12.0)
DOWN_DOG = pose((550, 273), 36, 57, (430, 420), (727, 430),
                knee=1.0, elbow=-1.0, foot=0.3)
POSES = (MOUNTAIN, SALUTE, FOLD, LIFT, PLANK, LOW, UP_DOG,
         DOWN_DOG, LIFT, FOLD, SALUTE, MOUNTAIN)

# Walking the feet back and forward is part of the motion, rather than a cut
# between two drawings. The planted hand targets stay fixed through the floor
# sequence. There are deliberate intermediate bends before each step.
PLANT = pose((628, 288), 44, 49, (630, 435), (727, 430),
             elbow=-1.0)
STEP_BACK = replace(
    pose((576, 313), 21, 22, (630, 435), (727, 430),
         elbow=-1.0), far_ankle=(450, 407))
STEP_FORWARD = replace(
    pose((575, 315), 19, 26, (630, 435), (727, 430),
         elbow=-1.0), far_ankle=(430, 415))
RETURN_CROUCH = pose((629, 295), 36, 26, (630, 435), (727, 430),
                    elbow=-1.0)


def interpolate(a: Pose, b: Pose, amount: float, lift_foot=False) -> Pose:
    amount = smooth(amount)
    points = {}
    for name in ("hip", "near_ankle", "far_ankle", "near_wrist", "far_wrist"):
        value = mix(getattr(a, name), getattr(b, name), amount)
        if lift_foot and "ankle" in name:
            travel = abs(getattr(a, name)[0] - getattr(b, name)[0])
            value = value[0], value[1] - min(38.0, travel * 0.2) * math.sin(math.pi * amount)
        points[name] = value
    scalars = {}
    for name in ("spine", "gaze", "foot", "arch"):
        start = getattr(a, name)
        end = getattr(b, name)
        scalars[name] = start + (end - start) * amount
    # Blend IK bend hints. When a branch must change, straighten that limb at
    # the zero crossing so the joint never jumps to the other side.
    for name in ("knee", "elbow"):
        scalars[name] = getattr(a, name) * (1.0 - amount) + getattr(b, name) * amount
    return Pose(**points, **scalars)


def transition(step: int, amount: float) -> Pose:
    if step == 3:
        stops = (POSES[3], PLANT, STEP_BACK, POSES[4])
    elif step == 7:
        stops = (POSES[7], STEP_FORWARD, RETURN_CROUCH, POSES[8])
    else:
        return interpolate(POSES[step], POSES[(step + 1) % 12], amount)
    segment = min(2, int(amount * 3))
    return interpolate(stops[segment], stops[segment + 1], amount * 3 - segment,
                       lift_foot=True)


def sample(time: float) -> Pose:
    step = int(time / STEP_SECONDS) % 12
    local = time % STEP_SECONDS
    transition_start = STEP_SECONDS - TRANSITION_SECONDS
    if local > transition_start:
        return transition(step, (local - transition_start) / TRANSITION_SECONDS)
    # A quiet chest movement keeps held poses alive. Its displacement and
    # velocity return to zero before the next transition starts.
    breath = math.sin(math.pi * local / transition_start) ** 2
    held = POSES[step]
    return replace(held, hip=add(held.hip, (0, -0.8 * breath)),
                   arch=held.arch + 0.5 * breath)


def joint(root: Point, target: Point, first: float, second: float,
          bend: float) -> tuple[Point, Point]:
    delta = sub(target, root)
    distance = math.hypot(*delta)
    direction = mul(delta, 1.0 / max(0.001, distance))
    reach = first + second - 0.05
    distance = min(reach, max(abs(first - second) + 0.05, distance))
    target = add(root, mul(direction, distance))
    along = (first * first - second * second + distance * distance) / (2 * distance)
    perpendicular = (-direction[1], direction[0])
    height = math.sqrt(max(0.0, first * first - along * along))
    # A zero bend hint makes a smooth straightening instead of an IK flip.
    offset = height * bend
    middle = add(add(root, mul(direction, along)), mul(perpendicular, offset))
    return middle, target


def ellipse(ctx, center, rx, ry, fill, alpha=1.0, angle=0.0):
    ctx.save()
    ctx.translate(*center)
    ctx.rotate(angle)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    source(ctx, fill, alpha)
    ctx.fill()
    ctx.restore()


def segment(ctx, a, b, r1, r2, base, highlight, shade):
    delta = sub(b, a)
    length = math.hypot(*delta)
    angle = math.atan2(delta[1], delta[0])
    ctx.save()
    ctx.translate(*a)
    ctx.rotate(angle)
    ctx.move_to(0, -r1)
    ctx.curve_to(length * 0.45, -r1 * 1.03, length * 0.75, -r2, length, -r2)
    ctx.curve_to(length + r2 * 1.33, -r2, length + r2 * 1.33, r2, length, r2)
    ctx.curve_to(length * 0.65, r2, length * 0.35, r1, 0, r1)
    ctx.curve_to(-r1 * 1.33, r1, -r1 * 1.33, -r1, 0, -r1)
    gradient = cairo.LinearGradient(0, -r1, 0, r1)
    gradient.add_color_stop_rgb(0, *color(highlight))
    gradient.add_color_stop_rgb(0.55, *color(base))
    gradient.add_color_stop_rgb(1, *color(shade))
    ctx.set_source(gradient)
    ctx.fill()
    ctx.restore()


def foot(ctx, ankle, angle, skin):
    ctx.save()
    ctx.translate(*ankle)
    ctx.rotate(angle)
    ctx.move_to(-8, -2)
    ctx.curve_to(-10, 6, -11, 11, -6, 12)
    ctx.line_to(23, 12)
    ctx.curve_to(29, 12, 29, 7, 21, 5)
    ctx.curve_to(12, 3, 9, 1, 7, -6)
    ctx.close_path()
    source(ctx, skin)
    ctx.fill()
    ctx.restore()


def hand(ctx, wrist, elbow, skin):
    direction = mul(sub(wrist, elbow), 1.0 / max(1, math.dist(wrist, elbow)))
    endpoint = add(wrist, mul(direction, 11))
    # Palms resting on the mat stay above the contact plane.
    if wrist[1] > 414:
        endpoint = wrist[0] + 13, 433
    elif 130 < wrist[1] < 180 and elbow[1] > wrist[1] and wrist[0] > 640:
        endpoint = wrist[0], wrist[1] - 12
    segment(ctx, wrist, endpoint, 5.6, 3.2, skin, skin, skin)


PALETTES = {
    "light": {"canvas": "F4F0E9", "edge": "EAE6DE", "halo": "FFFDF6",
              "mat": "C8CDC1", "mat_edge": "B1BAAE", "shadow": "857E70"},
    "dark": {"canvas": "1C272B", "edge": "121D22", "halo": "35433F",
             "mat": "495F5B", "mat_edge": "364C49", "shadow": "080E12"},
}


class Renderer:
    def __init__(self, width, height, figure, theme):
        self.width = width
        self.height = height
        self.figure = figure
        self.palette = PALETTES[theme]
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)
        self.ctx.scale(width / 960, height / 540)
        # Center the action in the frame while retaining a fixed camera.
        self.background = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        background_ctx = cairo.Context(self.background)
        background_ctx.scale(width / 960, height / 540)
        self.draw_background(background_ctx)

    def draw_background(self, ctx):
        gradient = cairo.RadialGradient(500, 220, 50, 480, 260, 620)
        gradient.add_color_stop_rgb(0, *color(self.palette["canvas"]))
        gradient.add_color_stop_rgb(1, *color(self.palette["edge"]))
        ctx.set_source(gradient)
        ctx.paint()
        ellipse(ctx, (473, 228), 205, 205, self.palette["halo"], 0.2)
        ctx.save()
        ctx.translate(-96, 0)
        ellipse(ctx, (575, 447), 260, 11, self.palette["shadow"], 0.10)
        ctx.move_to(305, 431)
        ctx.line_to(813, 431)
        ctx.curve_to(822, 431, 833, 440, 822, 444)
        ctx.line_to(297, 444)
        ctx.curve_to(286, 440, 296, 431, 305, 431)
        source(ctx, self.palette["mat"])
        ctx.fill()
        source(ctx, self.palette["mat_edge"])
        ctx.set_line_width(1.5)
        ctx.move_to(299, 443)
        ctx.line_to(822, 443)
        ctx.stroke()
        ctx.restore()

    def draw_leg(self, p, far=False):
        offset = (-7, -1) if far else (0, 0)
        hip = add(p.hip, offset)
        ankle = add(p.far_ankle if far else p.near_ankle, offset)
        knee, ankle = joint(hip, ankle, 95, 94, p.knee)
        skin = ("B48968", "C99D7A", "9D7054") if far else ("D9AC87", "EBC5A1", "BD8F6C")
        cloth = ("35464A", "4E5E5F", "29393E") if far else ("46585A", "657475", "32474C")
        if self.figure == "woman":
            segment(self.ctx, hip, knee, 18, 11.5, *cloth)
            segment(self.ctx, knee, ankle, 11.5, 6.8, *cloth)
        else:
            segment(self.ctx, hip, knee, 18, 11, *skin)
            segment(self.ctx, knee, ankle, 11, 6.5, *skin)
            shorts_end = mix(hip, knee, 0.57)
            segment(self.ctx, hip, shorts_end, 20, 17, *cloth)
        foot(self.ctx, ankle, p.foot, skin[0])

    def draw_arm(self, p, far=False):
        offset = (-6, -2) if far else (0, 0)
        shoulder = add(p.shoulder, offset)
        wrist = add(p.far_wrist if far else p.near_wrist, offset)
        elbow, wrist = joint(shoulder, wrist, 64, 61, p.elbow)
        skin = ("B78A69", "CBA17D", "A17355") if far else ("DAAF8A", "EEC9A6", "BE906E")
        segment(self.ctx, shoulder, elbow, 11, 8, *skin)
        segment(self.ctx, elbow, wrist, 8, 5.2, *skin)
        hand(self.ctx, wrist, elbow, skin[0])

    def draw_torso(self, p):
        ctx = self.ctx
        ctx.save()
        ctx.translate(*p.hip)
        ctx.rotate(p.spine)
        waist = 16 if self.figure == "woman" else 18
        rib = 21 if self.figure == "woman" else 23
        ctx.move_to(-9, -waist)
        ctx.curve_to(19, -waist - p.arch, 30, -14 - p.arch, 53, -rib)
        ctx.curve_to(76, -rib - 3, 102, -23, 110, -16)
        ctx.curve_to(121, -10, 121, 10, 110, 16)
        ctx.curve_to(80, 23, 68, rib, 54, rib - 2)
        ctx.curve_to(30, waist + 4 - p.arch, 13, waist - p.arch, -9, waist)
        ctx.curve_to(-21, 10, -21, -10, -9, -waist)
        gradient = cairo.LinearGradient(0, -24, 0, 24)
        gradient.add_color_stop_rgb(0, *color("EBC5A1"))
        gradient.add_color_stop_rgb(0.48, *color("D9AC87"))
        gradient.add_color_stop_rgb(1, *color("B98A69"))
        ctx.set_source(gradient)
        ctx.fill()
        if self.figure == "woman":
            ctx.move_to(66, -21)
            ctx.curve_to(87, -26, 106, -22, 113, -15)
            ctx.line_to(115, 12)
            ctx.curve_to(93, 25, 80, 24, 65, 21)
            ctx.close_path()
            source(ctx, "536564")
            ctx.fill()
            ctx.set_line_width(5)
            source(ctx, "617370")
            ctx.move_to(103, -18)
            ctx.curve_to(113, -12, 114, 4, 111, 13)
            ctx.stroke()
        else:
            source(ctx, "A97D60", 0.22)
            ctx.set_line_width(1)
            ctx.move_to(69, 6)
            ctx.curve_to(79, 11, 92, 9, 99, 3)
            ctx.stroke()
        ctx.restore()

    def draw_head(self, p):
        ctx = self.ctx
        direction = unit(p.gaze)
        head = add(p.shoulder, mul(direction, 41))
        segment(ctx, p.shoulder, add(p.shoulder, mul(direction, 22)), 8, 8,
                "D9AC87", "EBC5A1", "B98A69")
        ctx.save()
        ctx.translate(*head)
        ctx.rotate(p.gaze + math.pi / 2)
        if self.figure == "woman":
            ctx.save()
            ctx.translate(-14, -3)
            ctx.rotate(-0.12 * math.sin(p.spine))
            ctx.move_to(-2, -5)
            ctx.curve_to(-24, -2, -21, 19, -28, 40)
            ctx.curve_to(-13, 34, -3, 15, 4, 3)
            ctx.close_path()
            source(ctx, "3E332E")
            ctx.fill()
            ctx.restore()
        ctx.move_to(-12, -20)
        ctx.curve_to(0, -28, 17, -18, 18, -8)
        ctx.line_to(23, -1)
        ctx.curve_to(27, 2, 25, 5, 19, 5)
        ctx.line_to(19, 15)
        ctx.curve_to(13, 25, 4, 24, -4, 16)
        ctx.curve_to(-16, 9, -21, -9, -12, -20)
        gradient = cairo.LinearGradient(-17, -5, 23, 0)
        gradient.add_color_stop_rgb(0, *color("BD906E"))
        gradient.add_color_stop_rgb(0.6, *color("E3B992"))
        gradient.add_color_stop_rgb(1, *color("F0CBA6"))
        ctx.set_source(gradient)
        ctx.fill()
        ctx.move_to(-15, -17)
        ctx.curve_to(-12, -29, 10, -29, 17, -16)
        ctx.line_to(9, -13)
        ctx.curve_to(-4, -18, -8, -8, -9, 3)
        ctx.line_to(-13, 9)
        ctx.curve_to(-22, 0, -24, -10, -15, -17)
        source(ctx, "3E332E")
        ctx.fill()
        ellipse(ctx, (-4, 3), 4, 6, "D4A480")
        source(ctx, "604734")
        ctx.set_line_width(1.15)
        ctx.move_to(13, -3)
        ctx.line_to(17, -3)
        ctx.move_to(17, 11)
        ctx.line_to(20, 11)
        ctx.stroke()
        ctx.restore()

    def frame(self, time):
        ctx = self.ctx
        ctx.save()
        ctx.identity_matrix()
        ctx.set_source_surface(self.background)
        ctx.paint()
        ctx.restore()
        ctx.save()
        ctx.translate(480, 435)
        ctx.scale(0.9, 0.9)
        ctx.translate(-576, -435)
        p = sample(time)
        ellipse(ctx, (p.hip[0] + 15, 435), 82, 4.5,
                self.palette["shadow"], 0.08)
        self.draw_leg(p, far=True)
        self.draw_arm(p, far=True)
        self.draw_leg(p)
        self.draw_torso(p)
        self.draw_head(p)
        self.draw_arm(p)
        ctx.restore()
        self.surface.flush()
        return self.surface.get_data()


def metadata(path):
    lines = [";FFMETADATA1", "title=Sun Salutation A", "artist=Inner Breeze",
             "comment=Continuous illustrated motion; no pose-sheet playback."]
    for step, name in enumerate(NAMES):
        lines.extend(("[CHAPTER]", "TIMEBASE=1/1000",
                      f"START={int(step * STEP_SECONDS * 1000)}",
                      f"END={int((step + 1) * STEP_SECONDS * 1000)}", f"title={name}"))
    path.write_text("\n".join(lines) + "\n")


def render_video(output, figure, theme, width, height, fps, seconds):
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to replace {output}; choose a new output folder")
    renderer = Renderer(width, height, figure, theme)
    # Disposable encoding metadata is the only file created outside the repo.
    with tempfile.TemporaryDirectory(prefix="inbe-animation-encode-") as temporary:
        chapters = Path(temporary) / "chapters.txt"
        metadata(chapters)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-f", "rawvideo", "-pixel_format", "bgra", "-video_size", f"{width}x{height}",
            "-framerate", str(fps), "-i", "pipe:0", "-f", "ffmetadata", "-i", str(chapters),
            "-map", "0:v:0", "-map_metadata", "1", "-map_chapters", "1",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-threads", "3", str(output),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for frame in range(round(seconds * fps)):
                process.stdin.write(renderer.frame(frame / fps))
                if frame % (fps * 8) == 0:
                    print(f"{theme}/{figure}: {frame / fps:.0f}/{seconds:.0f}s", flush=True)
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"FFmpeg failed while rendering {output}")
    print(f"Saved {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--figure", choices=("man", "woman", "all"), default="all")
    parser.add_argument("--theme", choices=("light", "dark", "all"), default="all")
    parser.add_argument("--still", type=float, help="Render a PNG at this timeline second")
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0 or args.width % 2 or args.height % 2:
        parser.error("Video dimensions must be positive even numbers")
    if args.fps <= 0:
        parser.error("Frame rate must be positive")
    figures = ("man", "woman") if args.figure == "all" else (args.figure,)
    themes = ("light", "dark") if args.theme == "all" else (args.theme,)
    for theme in themes:
        for figure in figures:
            output = args.output / theme / f"sun-salutation-{figure}.mp4"
            if args.still is not None:
                output = output.with_suffix(".png")
                if output.exists():
                    raise FileExistsError(output)
                output.parent.mkdir(parents=True, exist_ok=True)
                renderer = Renderer(args.width, args.height, figure, theme)
                renderer.frame(args.still)
                renderer.surface.write_to_png(str(output))
            else:
                render_video(output, figure, theme, args.width, args.height,
                             args.fps, STEP_SECONDS * len(POSES))


if __name__ == "__main__":
    main()
