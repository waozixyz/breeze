#!/usr/bin/env python3
"""Check only Inbe's native geometry on the selected Pixel, without screenshots."""
import argparse
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import time

PIXEL_SERIAL = "93NAY0DF21"
PACKAGE = "xyz.waozi.inbe.debug"
PATTERN = re.compile(
    r"ANDROID_GEOMETRY: ready=1 sample=(\d+) launch=(\d+)x(\d+) screen=(\d+)x(\d+) "
    r"render=(\d+)x(\d+) viewport=(-?\d+),(-?\d+),(\d+)x(\d+) "
    r"offset=(-?\d+),(-?\d+) scale=([\d.eE+-]+),([\d.eE+-]+) "
    r"projection=([\d.eE+-]+),([\d.eE+-]+) layout=(\d+)x(\d+) "
    r"render_scale=([\d.eE+-]+) practice=(-?\d+) paused=(\d+)"
)


def parse_geometry(line):
    match = PATTERN.search(line)
    if not match:
        return None
    groups = match.groups()
    launch = [int(v) for v in groups[1:3]]
    values = (groups[0], *groups[3:])
    return {
        "sample": int(values[0]),
        "launch": launch,
        "screen": [int(v) for v in values[1:3]],
        "render": [int(v) for v in values[3:5]],
        "viewport": [int(v) for v in values[5:9]],
        "offset": [int(v) for v in values[9:11]],
        "scale": [float(v) for v in values[11:13]],
        "projection": [float(v) for v in values[13:15]],
        "layout": [int(v) for v in values[15:17]],
        "render_scale": float(values[17]),
        "practice": int(values[18]),
        "paused": int(values[19]),
    }


def validate_geometry(sample):
    width, height = sample["screen"]
    if width <= 0 or height <= 0 or sample["render"] != [width, height]:
        raise RuntimeError("Native screen and framebuffer dimensions disagree")
    if sample["offset"] != [0, 0] or sample["scale"] != [1.0, 1.0]:
        raise RuntimeError("Stale native screen scale or letterbox offsets")
    px, py = sample["projection"]
    if not math.isclose(px * width, 2.0, abs_tol=0.0001) or not math.isclose(py * height, -2.0, abs_tol=0.0001):
        raise RuntimeError("Projection is not the current native pixel projection")
    x, y, view_width, view_height = sample["viewport"]
    if x < 0 or y < 0 or view_width <= 0 or view_height <= 0 or x + view_width > width or y + view_height > height:
        raise RuntimeError("Viewport is outside the native screen")
    scale = sample["render_scale"]
    if not math.isfinite(scale) or scale <= 0:
        raise RuntimeError("Invalid application render scale")
    for pixels, units in zip((view_width, view_height), sample["layout"]):
        if abs(pixels - units * scale) > scale / 2 + 0.01:
            raise RuntimeError("Application layout does not match the current viewport and render scale")
    if sample["practice"] != -1:
        raise RuntimeError("Active practice detected; refusing the rotation check")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="local", help="local for direct ADB, otherwise an SSH host")
    parser.add_argument("--serial", default=PIXEL_SERIAL)
    parser.add_argument("--transport", default="192.168.100.23:41787")
    parser.add_argument("--package", default=PACKAGE)
    parser.add_argument("--output", type=Path, default=Path("backup/portrait-landscape/pixel-geometry.json"))
    args = parser.parse_args()
    if args.serial != PIXEL_SERIAL or args.package != PACKAGE:
        parser.error("This check is restricted to Pixel 93NAY0DF21 and xyz.waozi.inbe.debug")

    def adb(*command):
        arguments = ["adb", "-s", args.transport, *map(str, command)]
        if args.host != "local":
            arguments = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", args.host, shlex.join(arguments)]
        return subprocess.check_output(arguments, text=True, timeout=30).strip()

    if adb("get-state") != "device" or adb("shell", "getprop", "ro.serialno") != args.serial:
        raise RuntimeError("Selected ADB transport is not the authorized physical Pixel")
    pid = adb("shell", "pidof", args.package)
    if not pid or not pid.isdigit():
        raise RuntimeError("Inbe must already be running; this check never launches or stops it")

    def guard():
        if adb("shell", "pidof", args.package) != pid:
            raise RuntimeError("Inbe restarted; stopping the geometry check")
        focus = adb("shell", "dumpsys", "window", "windows")
        current = next((line for line in focus.splitlines() if "mCurrentFocus=" in line), "")
        if args.package + "/xyz.waozi.inbe.MainActivity" not in current:
            raise RuntimeError("Inbe is not the focused application; refusing changes")

    last_sample = -1

    def fresh(orientation=None):
        nonlocal last_sample
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            guard()
            lines = adb("logcat", "-d", "--pid=" + pid, "-v", "raw", "-s", "InbeGeometry:I", "*:S").splitlines()
            samples = [parsed for line in lines if (parsed := parse_geometry(line)) is not None]
            if samples and samples[-1]["sample"] > last_sample:
                sample = samples[-1]
                last_sample = sample["sample"]
                # Check the practice before every setting change, including
                # when waiting for the platform to complete a rotation.
                if sample["practice"] != -1:
                    raise RuntimeError("Active practice detected; stopping without practice commands")
                width, height = sample["screen"]
                matches = orientation is None or (orientation == "portrait" and height > width) or (orientation == "landscape" and width > height)
                if matches:
                    validate_geometry(sample)
                    return sample
            time.sleep(0.5)
        raise RuntimeError("No fresh matching native geometry; verify the Debug ANDROID_DEBUG build and System orientation preference")

    guard()
    baseline = fresh()
    if baseline["launch"][1] <= baseline["launch"][0] or baseline["screen"][1] <= baseline["screen"][0]:
        raise RuntimeError("This regression check requires a portrait-first app launch and portrait baseline; no settings changed")
    original = {name: adb("shell", "settings", "get", "system", name) for name in ("accelerometer_rotation", "user_rotation")}
    report = {"serial": args.serial, "package": args.package, "pid": pid, "baseline": baseline, "original_settings": original, "passed": False, "cases": []}

    def setting(name, value):
        if value == "null":
            adb("shell", "settings", "delete", "system", name)
        else:
            adb("shell", "settings", "put", "system", name, value)

    try:
        guard()
        fresh()
        setting("accelerometer_rotation", "0")
        for rotation, orientation in ((0, "portrait"), (1, "landscape"), (0, "portrait")):
            guard()
            fresh()
            setting("user_rotation", str(rotation))
            sample = fresh(orientation)
            report["cases"].append({"orientation": orientation, **sample})
        portrait, landscape, returned = report["cases"]
        if landscape["screen"] != list(reversed(portrait["screen"])) or returned["screen"] != portrait["screen"]:
            raise RuntimeError("Native dimensions did not swap and return during actual rotation")
        if returned["viewport"] != portrait["viewport"] or returned["layout"] != portrait["layout"]:
            raise RuntimeError("Portrait viewport/layout did not recover")
        if any(case["paused"] != baseline["paused"] for case in report["cases"]):
            raise RuntimeError("Pause state changed during rotation")
        report["passed"] = True
    finally:
        errors = []
        for name, value in original.items():
            try:
                setting(name, value)
                if adb("shell", "settings", "get", "system", name) != value:
                    raise RuntimeError("Original rotation setting was not restored: " + name)
            except Exception as error:
                errors.append(str(error))
        report["settings_restored"] = not errors
        report["process_preserved"] = adb("shell", "pidof", args.package) == pid
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        if errors:
            raise RuntimeError("; ".join(errors))
    if not report["process_preserved"]:
        raise RuntimeError("Inbe process changed during geometry verification")
    print("Pixel portrait/landscape/portrait native viewport, projection, scale and layout passed; settings restored; process and pause state preserved; no screen captured")


if __name__ == "__main__":
    main()
