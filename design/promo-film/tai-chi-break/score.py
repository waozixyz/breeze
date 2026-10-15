#!/usr/bin/env python3
"""Ask Lyria for the Tai Chi break film's music: score.py [TAKES].
Writes build/promo-video/tai-chi-break/audio/score-N.mp3 (OPENROUTER_API_KEY
as for ../narrate.py)."""
import base64
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "build/promo-video/tai-chi-break/audio"
sys.path.insert(0, str(HERE.parent))
from narrate import key  # noqa: E402

PROMPT = (
    "Instrumental score for a premium 48-second film: a developer waits for AI agents to finish their work late at night, "
    "steps away to practise Tai Chi at a mountain monastery at dawn, and comes back calm. No vocals, no choir, no words. 72 BPM, D major. "
    "0-11 s: late-night studio: soft warm lo-fi ambient, a muted felt-piano figure that repeats a little restlessly, "
    "a quiet tape-hiss rain texture and very light ticking percussion like distant keystrokes, a low synth pulse. "
    "11-15 s: transition: the beat stops, an airy rising swell and a soft singing-bowl shimmer open into space. "
    "15-38 s: calm, spacious East Asian Tai Chi section: guzheng plucks and a slow bamboo flute melody over warm pads "
    "and soft low strings, a gentle frame-drum heartbeat, breath-like swells every four seconds, graceful and unhurried. "
    "38-43 s: the felt-piano figure returns, now settled, joined by the flute: content and clear-headed. "
    "43-48 s: resolve to a tender final chord with one sparkling chime and a clean natural ending, no loop. "
    "Cinematic, polished, spacious mix; nothing harsh, no loud drums."
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
        print(path, flush=True)
    (OUT / "score-prompt.txt").write_text(PROMPT + "\n")


if __name__ == "__main__":
    main()
