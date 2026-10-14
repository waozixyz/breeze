#!/usr/bin/env python3
"""Clean background plates for the Three.js edition: plates.py [NAME...].
Codex image edit of each approved keyframe (build/promo-video/keyframes/shot-NN.png)
into build/promo-video/threejs/plates/NAME.png; up to four sessions at once."""
import json, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "build/promo-video/threejs/plates"
IMAGES = Path.home() / ".codex/generated_images"
def paint(plate):
    log = OUT / f"{plate['name']}.log"
    # An "-empty" plate starts from its Lumi-free plate, so both share one picture.
    source = (OUT / f"{plate['source_plate']}.png") if plate.get("source_plate") else ROOT / "build/promo-video/keyframes" / f"{plate['keyframe']}.png"
    with open(log, "w") as output:
        subprocess.run(["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(OUT),
                        plate["prompt"], "-i", str(source)], stdin=subprocess.DEVNULL, stdout=output,
                       stderr=subprocess.STDOUT, timeout=1800)
    session = re.search(r"session id: (\S+)", log.read_text())
    made = sorted((IMAGES / session.group(1)).glob("*.png"), key=lambda p: p.stat().st_mtime) if session else []
    if not made:
        return f"{plate['name']}: no image"
    shutil.copyfile(made[-1], OUT / f"{plate['name']}.png")
    return f"{plate['name']}: ok"
OUT.mkdir(parents=True, exist_ok=True)
wanted = set(sys.argv[1:])
plates = [p for p in json.loads((HERE / "plates.json").read_text())
          if (p["name"] in wanted) or (not wanted and not (OUT / f"{p['name']}.png").exists())]
with ThreadPoolExecutor(4) as pool:
    for line in pool.map(paint, plates):
        print(line, flush=True)
