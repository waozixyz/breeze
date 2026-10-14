#!/usr/bin/env python3
"""Speak the promo film's lines in Lumi's voice and check every take.

Writes build/promo-video/audio/<key>-<take>.wav (24 kHz mono) and
takes.json with each take's transcript, match and length. Existing takes
are kept; pass --again to replace them. Store the chosen take as FLAC in
audio/ beside this script and name it in film.json's voices.
"""
import base64
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "build/promo-video/audio"
API = "https://openrouter.ai/api/v1"


def key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in (ROOT.parent / "harmony/.env").read_text().splitlines():
        name, equal, value = line.partition("=")
        if equal and name.strip() == "OPENROUTER_API_KEY":
            return value.strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY is missing")


def post(path, body, timeout=180):
    request = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            detail = error.read()[:300].decode("utf8", "replace")
            if error.code < 500 and error.code != 429:
                sys.exit(f"{path} failed: {error.code} {detail}")
        except (urllib.error.URLError, TimeoutError):
            pass
    sys.exit(f"{path} failed three times")


def transcribe(config, wav):
    audio = base64.b64encode(wav.read_bytes()).decode()
    reply = json.loads(post("/chat/completions", {
        "model": config["transcriber"], "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Transcribe this speech exactly. Reply with the words only."},
            {"type": "input_audio", "input_audio": {"data": audio, "format": "wav"}}]}]}))
    return reply["choices"][0]["message"]["content"].strip()


def words(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower().replace("-", " ")).split()


def main():
    config = json.loads((HERE / "narration.json").read_text())
    again = "--again" in sys.argv
    only = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    OUT.mkdir(parents=True, exist_ok=True)
    receipt_path = OUT / "takes.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    for line in config["lines"]:
        if only and line["key"] not in only:
            continue
        for take in range(1, config["takes"] + 1):
            name = f"{line['key']}-{take}"
            wav = OUT / f"{name}.wav"
            if wav.exists() and not again and receipt.get(name, {}).get("text") == line["text"]:
                continue
            pcm = post("/audio/speech", {"model": config["model"], "voice": config["voice"],
                                         "input": line["text"], "response_format": config["response_format"]})
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(config["pcm_sample_rate"]),
                            "-ac", "1", "-i", "-", str(wav)], input=pcm, check=True)
            heard = transcribe(config, wav)
            match = difflib.SequenceMatcher(None, words(line["text"]), words(heard)).ratio()
            seconds = len(pcm) / 2 / config["pcm_sample_rate"]
            receipt[name] = {"text": line["text"], "heard": heard, "match": round(match, 3), "seconds": round(seconds, 2)}
            receipt_path.write_text(json.dumps(receipt, indent=1) + "\n")
            print(f"{name}: {seconds:.2f}s match {match:.2f} :: {heard}")


if __name__ == "__main__":
    main()
