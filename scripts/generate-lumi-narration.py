#!/usr/bin/env python3
"""Generate the promo's spoken narration through OpenRouter, without music."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "design/lumi-promo"
ENDPOINT = "https://openrouter.ai/api/v1/audio/speech"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true")
    args = parser.parse_args()
    config_path = ASSETS / "narration.json"
    config = json.loads(config_path.read_text())
    output = ASSETS / "narration"
    output.mkdir(exist_ok=True)
    receipt_path = output / "receipt.json"
    if receipt_path.is_file() and not args.regenerate:
        receipt = json.loads(receipt_path.read_text())
        if receipt["config_sha256"] == digest(config_path) and all(
            (output / row["file"]).is_file() and
            digest(output / row["file"]) == row["sha256"]
            for row in receipt["clips"]):
            print("Using the existing verified OpenRouter narration.")
            return
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise SystemExit("Set OPENROUTER_API_KEY locally before generating narration.")
    models_url = "https://openrouter.ai/api/v1/models?output_modalities=speech"
    with urllib.request.urlopen(models_url, timeout=30) as response:
        models = json.load(response)["data"]
    model = next((item for item in models if item["id"] == config["model"]), None)
    if model is None or config["voice"] not in model.get("supported_voices", []):
        raise SystemExit("The configured narrator model or voice is not in OpenRouter's current catalog.")
    rows = []
    for index, text in enumerate(config["clips"]):
        body = {name: config[name] for name in (
            "model", "voice", "response_format", "speed", "provider")}
        body["input"] = text
        request = urllib.request.Request(ENDPOINT,
            data=json.dumps(body).encode(), headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "X-Title": "Inner Breeze Lumi promo narration"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                mime = response.headers.get_content_type()
                if not mime.startswith("audio/"):
                    raise ValueError("OpenRouter returned a non-audio response")
                audio = response.read()
                generation = response.headers.get("X-Generation-Id")
        except urllib.error.HTTPError as error:
            raise SystemExit(f"OpenRouter narration request failed (HTTP {error.code}); no audio was saved.") from None
        if len(audio) < 1024:
            raise ValueError("OpenRouter returned empty or truncated narration")
        destination = output / f"clip-{index:02}.mp3"
        with tempfile.NamedTemporaryFile(suffix=".mp3", dir=output, delete=False) as stream:
            stream.write(audio)
            temporary = Path(stream.name)
        try:
            seconds = duration(temporary)
            if not 0.3 <= seconds <= 20:
                raise ValueError("Narration clip duration is outside the expected range")
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(temporary),
                "-f", "null", "-"], check=True, capture_output=True)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        rows.append(dict(file=destination.name, text=text, seconds=seconds,
                         sha256=digest(destination), generation_id=generation))
        print(f"Generated narrator line {index + 1}/{len(config['clips'])}: {seconds:.2f} seconds", flush=True)
    receipt = dict(config_sha256=digest(config_path), provider="OpenRouter",
                   model=config["model"], voice=config["voice"], clips=rows,
                   music=False, documentation=config["documentation"])
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print("Saved all narrator clips and their generation record.")


if __name__ == "__main__":
    main()
