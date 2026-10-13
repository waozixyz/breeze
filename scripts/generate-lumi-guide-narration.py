#!/usr/bin/env python3
"""Generate Lumi's spoken guide lines for every locale through OpenRouter.

Each guide line listed in design/lumi-guide/narration.json is read from
locales/<code>.txt and spoken by the configured voice into
assets/lumi/voice/<code>/<key>.ogg. The receipt beside the configuration
records a hash of each line's text and settings, so only changed lines are
generated again. Every new clip is transcribed and kept only when the
transcript matches its line.

Set OPENROUTER_API_KEY in the environment before generating. --check needs no
network: it fails when a clip is missing, changed, or older than its line.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "design/lumi-guide/narration.json"
RECEIPT = ROOT / "design/lumi-guide/receipt.json"
LOCALES = ROOT / "locales"
VOICE = ROOT / "assets/lumi/voice"
SPEECH = "https://openrouter.ai/api/v1/audio/speech"
CHAT = "https://openrouter.ai/api/v1/chat/completions"
ATTEMPTS = 4
LANGUAGES = {
    "en": "English", "es": "Spanish", "cs": "Czech", "de": "German",
    "fr": "French", "id": "Indonesian", "it": "Italian",
    "pt": "Brazilian Portuguese", "ru": "Russian", "ja": "Japanese",
    "ko": "Korean", "zh": "Simplified Chinese",
}
# Transcribers spell the brand names in the local script; they still match.
BRANDS = {
    "inner breeze": "innerbreeze", "ルミ": "lumi", "루미": "lumi",
    "露米": "lumi", "卢米": "lumi", "鲁米": "lumi", "люми": "lumi",
    "луми": "lumi", "ё": "е",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def entries(path):
    values, key, lines = {}, None, []
    for line in path.read_text(encoding="utf-8").split("\n"):
        header = re.fullmatch(r"\[([a-z0-9_]+)\]", line)
        if header:
            key, lines = header.group(1), []
        elif line == "---" and key is not None:
            values[key] = "\n".join(lines)
            key = None
        else:
            lines.append(line)
    return values


def locale_codes():
    codes = []
    for line in (LOCALES / "index.txt").read_text(encoding="utf-8").splitlines():
        if "|" in line:
            codes.append(line.split("|", 1)[0].strip())
    return codes


def text_hash(config, text):
    settings = {name: config[name] for name in (
        "model", "voice", "pcm_sample_rate", "sample_rate", "vorbis_bitrate")}
    settings["text"] = text
    return digest(json.dumps(settings, sort_keys=True, ensure_ascii=False).encode())


def clip_path(code, key):
    return VOICE / code / (key + ".ogg")


def wanted(config, codes, keys):
    """Every (code, key, text) the receipt must cover."""
    rows = []
    for code in codes:
        values = entries(LOCALES / (code + ".txt"))
        for key in keys:
            text = values.get(key, "").strip()
            if not text:
                raise SystemExit(f"{code}: {key} has no text")
            rows.append((code, key, text))
    return rows


def current(receipt, config, code, key, text):
    row = receipt.get("clips", {}).get(code + "/" + key)
    path = clip_path(code, key)
    return (row is not None and row["text_sha256"] == text_hash(config, text) and
            path.is_file() and digest(path.read_bytes()) == row["sha256"])


def request(url, body, key, timeout):
    """POST JSON with a few retries; returns (bytes, headers)."""
    data = json.dumps(body).encode()
    for attempt in range(4):
        message = urllib.request.Request(url, data=data, headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "X-Title": "Inner Breeze Lumi guide narration"})
        try:
            with urllib.request.urlopen(message, timeout=timeout) as response:
                return response.read(), response.headers
        except urllib.error.HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"OpenRouter request failed (HTTP {error.code})") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise RuntimeError("OpenRouter could not be reached") from None
        time.sleep(2 + attempt * 4)
    raise RuntimeError("OpenRouter request failed")


def speak(config, key, text):
    body = {"model": config["model"], "voice": config["voice"],
            "input": text, "response_format": config["response_format"]}
    audio, headers = request(SPEECH, body, key, 120)
    if not headers.get_content_type().startswith("audio/"):
        raise RuntimeError("OpenRouter returned a non-audio response")
    if len(audio) < config["pcm_sample_rate"]:
        raise RuntimeError("OpenRouter returned empty or truncated speech")
    return audio, headers.get("X-Generation-Id")


def encode(config, pcm, work):
    """Raw speech to a small mono Ogg Vorbis clip without its silences."""
    raw = work / "speech.pcm"
    raw.write_bytes(pcm)
    clip = work / "clip.ogg"
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
            "areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,"
            "areverse")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le",
        "-ar", str(config["pcm_sample_rate"]), "-ac", "1", "-i", str(raw),
        "-af", trim, "-ar", str(config["sample_rate"]), "-ac", "1",
        "-c:a", "libvorbis", "-b:a", config["vorbis_bitrate"], str(clip)],
        check=True, capture_output=True)
    return clip


def seconds(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error",
        "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True))


def transcribe(config, key, clip, code, work):
    mp3 = work / "clip.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-ac", "1",
        "-ar", "24000", "-b:a", "64k", str(mp3)], check=True, capture_output=True)
    audio = base64.b64encode(mp3.read_bytes()).decode()
    prompt = (f"Transcribe this audio exactly as spoken, in its original language "
              f"({LANGUAGES.get(code, code)}). Write numbers as digits. Reply with "
              "the transcript only.")
    body = {"model": config["transcriber"], "temperature": 0, "messages": [{
        "role": "user", "content": [{"type": "text", "text": prompt},
            {"type": "input_audio", "input_audio": {"data": audio, "format": "mp3"}}]}]}
    reply, _ = request(CHAT, body, key, 120)
    choices = json.loads(reply).get("choices") or [{}]
    content = (choices[0].get("message") or {}).get("content")
    # An empty reply counts as hearing nothing, so the line is spoken again.
    return (content or "").strip()


def normalized(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    for spoken, written in BRANDS.items():
        text = text.replace(spoken, written)
    return "".join(c for c in text if unicodedata.category(c)[0] in "LN")


def match(text, transcript):
    return difflib.SequenceMatcher(None, normalized(text),
                                   normalized(transcript)).ratio()


def generate(config, key, code, name, text):
    """Speaks a line until its transcript matches; returns the receipt row."""
    best = None
    with tempfile.TemporaryDirectory(prefix="lumi-voice-") as folder:
        work = Path(folder)
        for attempt in range(ATTEMPTS):
            pcm, generation = speak(config, key, text)
            clip = encode(config, pcm, work)
            length = seconds(clip)
            if not 0.5 <= length <= 40.0:
                continue
            transcript = transcribe(config, key, clip, code, work)
            score = match(text, transcript)
            if best is None or score > best["match"]:
                best = dict(data=clip.read_bytes(), seconds=round(length, 3),
                            transcript=transcript, match=round(score, 3),
                            generation_id=generation, attempts=attempt + 1)
            if score >= config["minimum_match"]:
                break
    if best is None or best["match"] < config["minimum_match"]:
        heard = best["transcript"] if best else "no usable audio"
        raise RuntimeError(f"{code}/{name} never matched its text; last heard: {heard}")
    destination = clip_path(code, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".ogg.part")
    temporary.write_bytes(best["data"])
    temporary.replace(destination)
    row = {name: value for name, value in best.items() if name != "data"}
    row.update(file=destination.relative_to(ROOT).as_posix(),
               text_sha256=text_hash(config, text), sha256=digest(best["data"]),
               bytes=len(best["data"]))
    return row


def save(receipt):
    receipt["clips"] = dict(sorted(receipt["clips"].items()))
    temporary = RECEIPT.with_suffix(".json.part")
    temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(RECEIPT)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
        help="fail when any clip is missing or older than its line")
    parser.add_argument("--locale", action="append", help="only these locales")
    parser.add_argument("--key", action="append", help="only these lines")
    parser.add_argument("--regenerate", action="store_true",
        help="speak the selected lines again even when they are current")
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    codes = locale_codes()
    receipt = {"clips": {}}
    if RECEIPT.is_file():
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = wanted(config, codes, config["keys"])
    if args.check:
        stale = [f"{code}/{key}" for code, key, text in rows
                 if not current(receipt, config, code, key, text)]
        expected = {f"{code}/{key}" for code, key, _ in rows}
        extra = sorted(set(receipt.get("clips", {})) - expected)
        for name in stale:
            print(f"{name}: clip is missing or older than its line")
        for name in extra:
            print(f"{name}: receipt lists a clip that is no longer a guide line")
        if stale or extra:
            sys.exit(1)
        print(f"All {len(rows)} guide clips match their lines.")
        return
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("Set OPENROUTER_API_KEY before generating narration.")
    selected = [(code, name, text) for code, name, text in rows
                if (not args.locale or code in args.locale) and
                (not args.key or name in args.key) and
                (args.regenerate or not current(receipt, config, code, name, text))]
    receipt.update(provider="OpenRouter", model=config["model"],
                   voice=config["voice"], transcriber=config["transcriber"],
                   documentation=config["documentation"])
    receipt["clips"] = {name: row for name, row in receipt.get("clips", {}).items()
                        if name in {f"{c}/{k}" for c, k, _ in rows}}
    lock = threading.Lock()
    failures = []

    def run(item):
        code, name, text = item
        try:
            row = generate(config, key, code, name, text)
        except (RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as error:
            with lock:
                failures.append(f"{code}/{name}: {error}")
                print(f"FAIL {code}/{name}: {error}", flush=True)
            return
        with lock:
            receipt["clips"][code + "/" + name] = row
            save(receipt)
            print(f"{code}/{name}: {row['seconds']:.2f} s, {row['bytes'] / 1000:.1f} kB, "
                  f"match {row['match']:.2f}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(run, selected))
    save(receipt)
    total = sum(row["bytes"] for row in receipt["clips"].values())
    print(f"{len(selected) - len(failures)} of {len(selected)} clips generated; "
          f"{len(receipt['clips'])} clips, {total / 1000000:.2f} MB in all.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
