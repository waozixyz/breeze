#!/usr/bin/env python3
"""Ask Lyria for the promo film's music bed: build/promo-video/audio/score-N.mp3."""
import base64
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "build/promo-video/audio"
sys.path.insert(0, str(HERE))
from narrate import key  # noqa: E402

PROMPT = (
    "Instrumental score for a premium 65-second promo film of a mindful-living app. No vocals, no choir words. "
    "Warm, hopeful and cinematic, 76 BPM, D major. "
    "0-6 s: a hush at dawn, airy pads and one soft felt-piano motif, a single small chime like a firefly lighting up. "
    "6-30 s: gentle bamboo flute melody over the piano, light guzheng plucks, soft breath-like swells. "
    "30-42 s: a graceful East Asian section for a Tai Chi sequence: guzheng and erhu phrase, slow taiko heartbeat, warm low strings. "
    "42-56 s: uplifting build with warm strings, light hand percussion and piano arpeggios, optimistic and bright. "
    "56-65 s: resolve to a tender final chord with a sparkling chime and a clean natural ending, no fade-in loop. "
    "Mixed spaciously so a narrator's voice sits clearly on top: no busy midrange, no loud drums."
)


def main():
    takes = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    OUT.mkdir(parents=True, exist_ok=True)
    for take in range(1, takes + 1):
        body = {"model": "google/lyria-3-pro-preview", "modalities": ["text", "audio"],
                "audio": {"format": "mp3"}, "stream": True,
                "messages": [{"role": "user", "content": PROMPT}]}
        request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
        chunks = []
        with urllib.request.urlopen(request, timeout=600) as response:
            for raw in response:
                line = raw.decode("utf8", "replace").strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    continue
                event = json.loads(line[5:])
                for choice in event.get("choices", []):
                    audio = choice.get("delta", {}).get("audio") or {}
                    if audio.get("data"):
                        chunks.append(audio["data"])
        if not chunks:
            sys.exit("Lyria returned no audio")
        path = OUT / f"score-{take}.mp3"
        path.write_bytes(b"".join(base64.b64decode(chunk) for chunk in chunks))
        print(path)
    (OUT / "score-prompt.txt").write_text(PROMPT + "\n")


if __name__ == "__main__":
    main()
