#!/usr/bin/env python3
"""Lay the score under the rendered film: finish.py [FILM.mp4] [OUT.mp4].

Defaults: build/promo-video/tai-chi-break/film.mp4 (tools/render.mjs) and
build/promo-video/tai-chi-break/inner-breeze-tai-chi-break.mp4, with
audio/score.mp3 (Lyria take 1 of score.py) cut to the film's 53 s, eased out
over its last 0.8 s and normalised in two passes to -14 LUFS. The picture is
re-encoded at a size social platforms and Telegram accept (under 50 MB) from
the CRF 15 master. Also writes poster.jpg, a frame of the courtyard title.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "build/promo-video/tai-chi-break"
LENGTH = 53.0
SCORE = f"atrim=0:{LENGTH},afade=t=out:st={LENGTH - 0.8}:d=0.8"

film = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "film.mp4"
final = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "inner-breeze-tai-chi-break.mp4"
probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(HERE / "audio/score.mp3"), "-af",
                        f"{SCORE},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True).stderr
measured = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
loudnorm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={measured['input_i']}:"
            f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
            f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}")
subprocess.run([
    "ffmpeg", "-loglevel", "error", "-y", "-i", str(film), "-i", str(HERE / "audio/score.mp3"),
    "-filter_complex", f"[1:a]{SCORE},{loudnorm},aresample=48000[a]",
    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "7M",
    "-bufsize", "14M", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", str(LENGTH), "-movflags", "+faststart", str(final)], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "26.0", "-i", str(final), "-frames:v", "1", "-q:v", "2",
                str(final.with_name("poster.jpg"))], check=True)
print(final)
