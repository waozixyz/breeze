#!/usr/bin/env python3
"""Mix Lumi's chosen takes over the score at film.json's times.

Reads the chosen takes and score from audio/ beside this script and writes
build/promo-video/audio/soundtrack.wav (48 kHz stereo, -14 LUFS) and
soundtrack.mp3, the audio the film is cut to.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "audio"
AUDIO = HERE.parents[1] / "build/promo-video/audio"
RATE = 48000


def load(path, channels):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", str(channels), "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).copy()


def voice(path):
    # Clean, close and present: rumble cut, gentle compression, a little air.
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-af",
                          "highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,"
                          "equalizer=f=3500:t=q:w=1.2:g=2,equalizer=f=250:t=q:w=1:g=-2",
                          "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def smooth(gate, attack, release):
    out = np.empty_like(gate)
    level = 0.0
    up, down = 1 / (attack * RATE), 1 / (release * RATE)
    for i, target in enumerate(gate):
        level = min(target, level + up) if target > level else max(target, level - down)
        out[i] = level
    return out


def main():
    film = json.loads((HERE / "film.json").read_text())
    length = int(film["format"]["length"] * RATE)
    music = load(SOURCES / film["score"]["file"], 2)[:length]
    music = np.pad(music, ((0, length - len(music)), (0, 0)))
    # The score's own last chord decays fast; ease it out under the title.
    fade_from, fade_to = (int(second * RATE) for second in film["score"]["fade_out"])
    music[fade_from:fade_to] *= np.cos(np.linspace(0, np.pi / 2, fade_to - fade_from))[:, None] ** 2
    music[fade_to:] = 0
    speech = np.zeros(length, np.float32)
    for line in film["voices"]:
        clip = voice(SOURCES / f"{line['take']}.flac")
        start = int(line["at"] * RATE)
        speech[start:start + len(clip)] += clip[:length - start]
    # Duck the score under speech with a smooth gain envelope.
    frame = RATE // 100
    active = np.repeat(np.abs(speech[:len(speech) // frame * frame]).reshape(-1, frame).max(axis=1) > 0.01, frame)
    active = np.pad(active.astype(np.float32), (0, length - len(active)))
    duck = 10 ** (film["score"]["duck_db"] / 20)
    envelope = 1 - (1 - duck) * smooth(active, 0.25, 0.7)
    mix = music * envelope[:, None] + speech[:, None] * 1.0
    AUDIO.mkdir(parents=True, exist_ok=True)
    raw = AUDIO / "premix.f32"
    raw.write_bytes(mix.astype(np.float32).tobytes())
    wav = AUDIO / "soundtrack.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", str(raw),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(RATE), "-c:a", "pcm_s16le", str(wav)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "320k",
                    str(AUDIO / "soundtrack.mp3")], check=True)
    raw.unlink()
    print(wav)


if __name__ == "__main__":
    main()
