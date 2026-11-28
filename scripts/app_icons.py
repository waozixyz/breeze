#!/usr/bin/env python3
"""Every Inner Breeze sub-app's own outline icon, from one source per app.

Each sub-app keeps assets/<app>/sidebar.shape: Kryon's vector icon format,
"S<width>rr:" plus one SVG path in a 24-unit view box with a 1.6-unit
rounded stroke. The same path is exported as sidebar.svg beside it, and
every app's 64-pixel white navigation export ships as
assets/apps/icons/<app>.png for the launcher catalog and outside uses.
The host's navigation reads the shapes and the Apps cards read the catalog,
so run this script after changing a shape and keep both in sync.
"""
from pathlib import Path
import argparse
import re

import cairosvg


ROOT = Path(__file__).resolve().parent.parent

# One line per sub-app: the outline the app is known by, in navigation
# bars, the Apps launcher and outside uses. Lumi's stays a firefly, the
# other shapes describe their app in the same 1.6-unit rounded stroke.
SUB_APPS = {
    "habits": "M5 19C2 10 10 5 20 4C19 14 12 21 5 19ZM5 19L16 8",
    "practices": ("M12 21C7 14 7 8 12 3C17 8 17 14 12 21Z"
                  "M11 21C5 20 2 15 3 8C9 9 12 14 11 21Z"
                  "M13 21C19 20 22 15 21 8C15 9 12 14 13 21ZM6 21H18"),
    "lists": "M8 6H21M8 12H21M8 18H21M3 6H3.1M3 12H3.1M3 18H3.1",
    "diary": ("M12 6C9 4 6 4 3 5V20C6 19 9 19 12 21C15 19 18 19 21 20V5"
              "C18 4 15 4 12 6ZM12 6V21"),
    "lumi": ("M9 7C9 5 7.5 4 6 4M15 7C15 5 16.5 4 18 4"
             "M12 7C15 7 17 9 17 12C17 15 15 17 12 17C9 17 7 15 7 12"
             "C7 9 9 7 12 7ZM9.5 12L9.5 12.1M14.5 12L14.5 12.1"
             "M10 17C10 19 11 20 12 20C13 20 14 19 14 17"
             "M7 12C4 10 3 12 4 14C4.5 16 6 17 9 16"
             "M17 12C20 10 21 12 20 14C19.5 16 18 17 15 16"),
    "leaderboard": "M3 21V13H9V8H15V16H21V21ZM9 21V13M15 21V16",
    "library": ("M19 17L18.4472 18.1056C18.1657 18.6686 18.1657 19.3314"
                " 18.4472 19.8944L19 21H7C5.89543 21 5 20.1046 5 19V5"
                "C5 3.89543 5.89543 3 7 3H18C18.5523 3 19 3.44772 19 4V17Z"
                "M19 21H7.01C5.90543 21 5.01 20.1046 5.01 19"
                "C5.01 17.8954 5.90543 17 7.01 17H19M19 17H17M10 8H14"),
    "radio": ("M7 13H8M7 16H10M8.5 4L19.5 8"
              "M17 14C17 15.1046 16.1046 16 15 16C13.8954 16 13 15.1046 13 14"
              "C13 12.8954 13.8954 12 15 12C16.1046 12 17 12.8954 17 14Z"
              "M4 20H20C20.5523 20 21 19.5523 21 19V9C21 8.44772 20.5523 8 20 8H4"
              "C3.44772 8 3 8.44772 3 9V19C3 19.5523 3.44772 20 4 20Z"),
    "arcade": ("M7.5 8H16.5C19.26 8 21 10.1 21 12.7"
               "C21 15.6 19.3 18 17.2 18C15.8 18 15 16.8 14.4 15.6"
               "C14.1 15.2 13.9 15 13.3 15H10.7C10.1 15 9.9 15.2 9.6 15.6"
               "C9 16.8 8.2 18 6.8 18C4.7 18 3 15.6 3 12.7C3 10.1 4.74 8 7.5 8Z"
               "M8 11V14.5M6.25 12.75H9.75M15.25 12H15.26M17.25 14H17.26"),
}

STROKE_WIDTH = 1.6
CATALOG_SIZE = 64

SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n'
    '  <path fill="none" stroke="white" stroke-width="{width}" '
    'stroke-linecap="round" stroke-linejoin="round" d="{d}"/>\n'
    '</svg>\n'
)


def shape_text(app: str) -> str:
    return f"S{STROKE_WIDTH}rr:{SUB_APPS[app]}\n"


def svg_text(app: str) -> str:
    return SVG_TEMPLATE.format(width=STROKE_WIDTH, d=SUB_APPS[app])


def catalog_png(app: str) -> bytes:
    return cairosvg.svg2png(bytestring=svg_text(app).encode(),
                            output_width=CATALOG_SIZE, output_height=CATALOG_SIZE)


def read_shape(path: Path) -> tuple[str, str]:
    match = re.fullmatch(r"S(\d+(?:\.\d+)?)rr:(.+)", path.read_text().strip())
    if not match:
        raise SystemExit(f"{path}: not a rounded-stroke Kryon icon shape")
    return match[1], match[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail instead of writing when an export is stale")
    options = parser.parse_args()
    stale = []
    wanted_files = {}
    for app, source in SUB_APPS.items():
        wanted_files[ROOT / "assets" / app / "sidebar.shape"] = shape_text(app).encode()
        outputs = {
            ROOT / "assets" / "apps" / "icons" / f"{app}.png": catalog_png(app),
        }
        outputs[ROOT / "assets" / app / "sidebar.svg"] = svg_text(app).encode()
        if app == "lumi":
            # The host names this file for Lumi's navigation picture.
            outputs[ROOT / "assets" / "lumi" / "sidebar.png"] = catalog_png(app)
        wanted_files.update(outputs)
    for path, wanted in wanted_files.items():
        if path.suffix == ".shape" and path.is_file():
            width, stroke_path = read_shape(path)
            if stroke_path != SUB_APPS[path.parent.name]:
                # A hand-tuned shape keeps its path; the script only
                # renames strokes, so an unexpected difference is
                # reported, not written.
                stale.append(f"{path}: path differs from scripts/app_icons.py")
                continue
            if float(width) != STROKE_WIDTH:
                stale.append(f"{path}: strokes share the {STROKE_WIDTH}-unit width")
        if not path.is_file() or path.read_bytes() != wanted:
            stale.append(f"{path}: missing or stale export")
            if not options.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(wanted)
    if options.check and stale:
        raise SystemExit("\n".join(stale))
    if not options.check:
        print(f"wrote icons for {len(SUB_APPS)} sub-apps")


if __name__ == "__main__":
    main()
