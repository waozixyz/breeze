#!/usr/bin/env python3
"""Paint one storyboard keyframe per shot with Codex image generation.

Usage: keyframes.py [SHOT...]. Writes build/promo-video/keyframes/shot-NN.png
(1536x1024 from Codex; the film uses its central 16:9 band). Runs up to
four Codex sessions at once and keeps existing keyframes unless named.
Approved keyframes are stored as 1536x864 JPEGs in keyframes/ beside this
script, which compose.py --animatic reads.
"""
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "build/promo-video/keyframes"
REFERENCES = {
    "lumi": ROOT / "assets/lumi/mascot.png",
    "mia": HERE / "references/mia-turnaround.png",
    "monk": ROOT / "design/tai-chi/characters/monk/source/turnaround.png",
    "teacher": ROOT / "design/tai-chi/characters/tibetan-woman/source/turnaround.png",
}
IMAGES = Path.home() / ".codex/generated_images"


def paint(frame):
    target = OUT / f"shot-{frame['shot']:02d}.png"
    log = OUT / f"shot-{frame['shot']:02d}.log"
    # "keyframe-NN" names an earlier shot's painted keyframe, for continuity.
    images = [str(OUT / f"shot-{name[9:]}.png") if name.startswith("keyframe-") else str(REFERENCES[name])
              for name in frame["refs"]]
    with open(log, "w") as output:
        subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(OUT),
                        frame["prompt"], "-i", *images], stdin=subprocess.DEVNULL, stdout=output,
                       stderr=subprocess.STDOUT, timeout=1800)
    session = re.search(r"session id: (\S+)", log.read_text())
    made = sorted((IMAGES / session.group(1)).glob("*.png"), key=lambda path: path.stat().st_mtime) if session else []
    if not made:
        return f"shot {frame['shot']}: no image (see {log.name})"
    shutil.copyfile(made[-1], target)
    return f"shot {frame['shot']}: {target.name}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = json.loads((HERE / "keyframes.json").read_text())
    wanted = {int(arg) for arg in sys.argv[1:]}
    todo = [frame for frame in frames
            if (frame["shot"] in wanted) or (not wanted and not (OUT / f"shot-{frame['shot']:02d}.png").exists())]
    with ThreadPoolExecutor(4) as pool:
        for line in pool.map(paint, todo):
            print(line, flush=True)


if __name__ == "__main__":
    main()
