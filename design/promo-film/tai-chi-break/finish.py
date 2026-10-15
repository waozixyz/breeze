#!/usr/bin/env python3
"""Lay the narration and score under the rendered film: finish.py [--vertical] [FILM.mp4] [OUT.mp4].

Defaults: build/promo-video/tai-chi-break/film.mp4 (tools/render.mjs) and
build/promo-video/tai-chi-break/inner-breeze-tai-chi-break.mp4, with
audio/score.mp3 (Lyria take 1 of score.py) cut to the film's 53 s and eased
out over its last 0.8 s. The male Tai Chi voice (Algieba) speaks each line of
narration.json from audio/voice/KEY.flac at its `at` time. The score sits
low and steady through each stretch of talking (lines less than 3 s apart
count as one) and rises only in the real pauses, with slow ramps, so it never
pumps between words. One fixed gain brings the mix to -14 LUFS and a limiter
holds the peaks; nothing rides the level. The picture is
re-encoded at a size social platforms and Telegram accept (under 50 MB) from
the CRF 15 master. Also writes poster.jpg, a frame of the courtyard title.

--vertical finishes the 1080x1920 cut (tools/render.mjs --aspect portrait):
film-vertical.mp4 into inner-breeze-tai-chi-break-vertical.mp4 and
poster-vertical.jpg, with the same narration and mix.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "build/promo-video/tai-chi-break"
LENGTH = 53.0
SCORE = f"atrim=0:{LENGTH},afade=t=out:st={LENGTH - 0.8}:d=0.8"

arguments = [argument for argument in sys.argv[1:] if argument != "--vertical"]
suffix = "-vertical" if "--vertical" in sys.argv else ""
film = Path(arguments[0]) if arguments else OUT / f"film{suffix}.mp4"
final = Path(arguments[1]) if len(arguments) > 1 else OUT / f"inner-breeze-tai-chi-break{suffix}.mp4"
lines = json.loads((HERE / "narration.json").read_text())["lines"]

# Stretches of talking: merge lines less than MERGE seconds apart.
MERGE, DOWN, UP, LOW, HIGH = 3.0, 0.8, 2.0, 0.17, 0.34
spans = []
for line in lines:
    seconds = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(HERE / "audio/voice" / f"{line['key']}.flac")],
                                   capture_output=True, text=True, check=True).stdout)
    start, end = line["at"], line["at"] + seconds
    if spans and start - spans[-1][1] < MERGE:
        spans[-1][1] = max(spans[-1][1], end)
    else:
        spans.append([start, end])
if spans and LENGTH - spans[-1][1] < MERGE:
    spans[-1][1] = LENGTH + UP
# 1 inside a stretch, easing in DOWN s before it and out UP s after it.
talk = "+".join(f"clip(min((t-{a - DOWN:.3f})/{DOWN},({b + UP:.3f}-t)/{UP}),0,1)" for a, b in spans)
gain = f"{HIGH}-({HIGH - LOW})*min(1,{talk})"
inputs = ["-i", str(HERE / "audio/score.mp3")]
graph = [f"[0:a]{SCORE},aresample=48000,volume='{gain}':eval=frame[score]"]
for index, line in enumerate(lines):
    inputs += ["-i", str(HERE / "audio/voice" / f"{line['key']}.flac")]
    delay = round(line["at"] * 1000)
    graph.append(f"[{index + 1}:a]aresample=48000,adelay={delay}:all=1[v{index}]")
voices = "".join(f"[v{index}]" for index in range(len(lines)))
# A warm, even voice.
graph.append(f"{voices}amix=inputs={len(lines)}:normalize=0,highpass=f=75,"
             "acompressor=threshold=0.1:ratio=2.5:attack=8:release=180:makeup=1.4,apad,"
             f"atrim=0:{LENGTH}[voice]")
graph.append("[score][voice]amix=inputs=2:normalize=0[mix]")
mix = ";".join(graph)

probe = subprocess.run(["ffmpeg", "-hide_banner", *inputs, "-filter_complex",
                        f"{mix};[mix]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[out]",
                        "-map", "[out]", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
measured = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
level = f"volume={-14.0 - float(measured['input_i']):.2f}dB,alimiter=limit=0.84:attack=5:release=80:level=0"
# Audio inputs follow the film, so their stream indices shift by one.
shifted = mix.replace("[0:a]", "[score_in]")
for index in range(len(lines), 0, -1):
    shifted = shifted.replace(f"[{index}:a]", f"[{index + 1}:a]")
shifted = shifted.replace("[score_in]", "[1:a]")
subprocess.run([
    "ffmpeg", "-loglevel", "error", "-y", "-i", str(film), *inputs,
    "-filter_complex", f"{shifted};[mix]{level},aresample=48000[a]",
    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "7M",
    "-bufsize", "14M", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", str(LENGTH), "-movflags", "+faststart", str(final)], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "26.0", "-i", str(final), "-frames:v", "1", "-q:v", "2",
                str(final.with_name(f"poster{suffix}.jpg"))], check=True)
print(final)
