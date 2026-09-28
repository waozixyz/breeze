#!/usr/bin/env python3
"""Synthesises candidate breathing cues (inhale and exhale) for listening tests.

Each style is written as 48 kHz stereo WAV and OGG under the output directory,
matched in loudness to the current assets/sounds files so they can be swapped
in without changing the mix.
    python3 scripts/generate-breath-sounds.py [outdir]
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 48000
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/sound-candidates"
rng = np.random.default_rng(7)


def pink(count):
    """Noise with a 1/f spectrum: what breath and wind sound like."""
    white = rng.standard_normal(count)
    spectrum = np.fft.rfft(white)
    frequency = np.maximum(np.fft.rfftfreq(count, 1 / RATE), 20.0)
    return np.fft.irfft(spectrum / np.sqrt(frequency), count)


def band(signal, centre, quality):
    """State-variable band-pass whose centre frequency follows `centre`."""
    low = band_out = 0.0
    out = np.empty_like(signal)
    damping = 1.0 / quality
    for index, sample in enumerate(signal):
        f = 2.0 * np.sin(np.pi * min(centre[index], RATE * 0.2) / RATE)
        low += f * band_out
        high = sample - low - damping * band_out
        band_out += f * high
        out[index] = band_out
    return out


def lowpass(signal, cutoff):
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff / RATE)
    out = np.empty_like(signal)
    state = 0.0
    for index, sample in enumerate(signal):
        state += alpha * (sample - state)
        out[index] = state
    return out


def swell(count, peak, sharpness):
    """Smooth rise to `peak` (0 to 1 of the length) and fall, no clicks."""
    t = np.linspace(0.0, 1.0, count)
    left = np.sin(0.5 * np.pi * np.clip(t / peak, 0, 1)) ** sharpness
    right = np.cos(0.5 * np.pi * np.clip((t - peak) / (1 - peak), 0, 1)) ** 1.6
    envelope = np.where(t < peak, left, right)
    edge = int(0.012 * RATE)
    envelope[:edge] *= np.linspace(0, 1, edge)
    envelope[-edge:] *= np.linspace(1, 0, edge)
    return envelope


def sweep(count, start, end):
    return np.geomspace(start, end, count)


def airy(seconds, rising):
    count = int(seconds * RATE)
    centre = sweep(count, 500, 1700) if rising else sweep(count, 1500, 420)
    channels = []
    for _ in range(2):
        noise = band(pink(count), centre, 1.1) + 0.35 * lowpass(pink(count), 900)
        channels.append(lowpass(noise, 6500))
    envelope = swell(count, 0.72 if rising else 0.22, 1.4)
    return np.stack(channels, axis=1) * envelope[:, None]


def ocean(seconds, rising):
    count = int(seconds * RATE)
    centre = sweep(count, 260, 900) if rising else sweep(count, 800, 220)
    channels = []
    for _ in range(2):
        noise = band(pink(count), centre, 0.7)
        channels.append(lowpass(noise, 3200))
    envelope = swell(count, 0.8 if rising else 0.18, 1.0)
    return np.stack(channels, axis=1) * envelope[:, None]


def tonal(seconds, rising):
    count = int(seconds * RATE)
    t = np.arange(count) / RATE
    glide = np.linspace(0, 1, count) if rising else np.linspace(1, 0, count)
    base = 196.0 * (1.0 + 0.12 * glide)
    phase = 2 * np.pi * np.cumsum(base) / RATE
    tone = (np.sin(phase) + 0.5 * np.sin(1.5 * phase + 0.4) +
            0.25 * np.sin(2.0 * phase + 1.1))
    air = band(pink(count), sweep(count, 700, 1500) if rising else sweep(count, 1400, 600), 1.0)
    envelope = swell(count, 0.7 if rising else 0.25, 1.3)
    mono = (0.7 * tone + 0.5 * lowpass(air, 5000)) * envelope
    shimmer = np.sin(2 * np.pi * 0.35 * t)[:, None] * 0.08
    return np.stack([mono, mono], axis=1) * (1.0 + np.array([shimmer[:, 0], -shimmer[:, 0]]).T)


def rms_of(path):
    with wave.open(str(path)) as source:
        data = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16)
    return float(np.sqrt(np.mean((data / 32768.0) ** 2)))


def write(path, audio, target_rms):
    audio = audio - audio.mean(axis=0)
    audio = audio * (target_rms / max(np.sqrt(np.mean(audio ** 2)), 1e-9))
    peak = np.max(np.abs(audio))
    if peak > 0.89:
        audio = audio * (0.89 / peak)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as sink:
        sink.setnchannels(2)
        sink.setsampwidth(2)
        sink.setframerate(RATE)
        sink.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path),
                    "-c:a", "libvorbis", "-q:a", "5", str(path.with_suffix(".ogg"))],
                   check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inhale_rms = rms_of(ROOT / "assets/sounds/breath-in.wav")
    exhale_rms = rms_of(ROOT / "assets/sounds/breath-out.wav")
    styles = {"air": airy, "ocean": ocean, "tonal": tonal}
    for name, make in styles.items():
        write(OUT / f"breath-in-{name}.wav", make(1.1, True), inhale_rms)
        write(OUT / f"breath-out-{name}.wav", make(1.7, False), exhale_rms)
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.ogg"))))


main()
