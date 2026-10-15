#!/usr/bin/env python3
"""Generate verified guide and practice narration through OpenRouter.

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


class ProviderBlocked(RuntimeError):
    """Stop the backlog when credits or credentials require operator action."""


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
    "луми": "lumi", "ё": "е", "イナブリーズ": "innerbreeze",
    "インナーブリーズ": "innerbreeze", "이너 브리즈": "innerbreeze",
    "이너브리즈": "innerbreeze", "이너 브릿지": "innerbreeze",
    "텔레그램": "telegram", "テレグラム": "telegram", "телеграм": "telegram",
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
    for line in (ROOT / "locales/index.txt").read_text(encoding="utf-8").splitlines():
        if "|" in line:
            codes.append(line.split("|", 1)[0].strip())
    return codes


def narration_keys(config):
    if 'keys_file' in config:
        keys = json.loads((ROOT / config['keys_file']).read_text())
    elif 'keys_from' in config:
        keys = sorted(entries(ROOT / config['keys_from']))
    else:
        keys = config['keys']
    if (not isinstance(keys, list) or not keys or len(keys) > 10000 or
            any(not isinstance(key, str) or not re.fullmatch('[a-z0-9_]+', key) for key in keys) or
            len(set(keys)) != len(keys)):
        raise ValueError('Narration keys must be a bounded, unique list of locale keys')
    return keys


def text_hash(config, text):
    settings = {name: config[name] for name in (
        "model", "voice", "pcm_sample_rate", "sample_rate", "vorbis_bitrate")}
    settings["text"] = text
    if config.get('instructions'):
        settings['instructions'] = config['instructions']
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
            path.is_file() and digest(path.read_bytes()) == row["sha256"] and
            verified_match(config, code, text, row.get('transcript', '')) >= config['minimum_match'])


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
            if error.code == 400:
                raise ProviderBlocked('OpenRouter rejected narration request settings (HTTP 400)') from None
            if error.code == 402:
                try:
                    details = json.loads(error.read(65536))
                    source = details.get('error', {}).get('metadata', {}).get('limit_source')
                except (ValueError, AttributeError):
                    source = None
                if source == 'openrouter_in_flight_budget' and attempt < 3:
                    try:
                        delay = int(error.headers.get('Retry-After', '5'))
                    except ValueError:
                        delay = 5
                    time.sleep(max(1, min(30, delay)))
                    continue
                raise ProviderBlocked('OpenRouter credit limit blocked narration (HTTP 402)') from None
            if error.code in (401, 403):
                raise ProviderBlocked(f'OpenRouter authorization blocked narration (HTTP {error.code})') from None
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
    if config.get('instructions'):
        body['instructions'] = config['instructions']
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
    context = config.get('transcription_contexts', {}).get(code)
    if context:
        prompt += ' ' + context
    model = config.get('locale_transcribers', {}).get(code, config['transcriber'])
    reasoning = config.get('locale_transcription_reasoning', {}).get(code, {'enabled': False})
    maximum_tokens = config.get('locale_transcription_max_tokens', {}).get(code,
        config.get('transcription_max_tokens', 512))
    body = {"model": model, "temperature": 0,
        "max_tokens": maximum_tokens,
        "reasoning": reasoning, "messages": [{
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


def japanese_spelling(text):
    # Katakana and hiragana encode the same syllables. Keep the recording
    # transcript unchanged; fold script only for pronunciation comparison.
    return ''.join(chr(ord(char) - 0x60) if '\u30a1' <= char <= '\u30f6' else char
                   for char in normalized(text))


def direction_tokens(text, code):
    patterns = {
        'en': (r'\bleft\b', r'\bright\b'),
        'es': (r'\bizquierd\w*', r'\bderech\w*'),
        'cs': (r'\blev\w*', r'\bprav\w*'),
        'de': (r'\blink\w*', r'\brecht\w*'),
        'fr': (r'\bgauche\w*', r'\bdroit\w*'),
        'id': (r'\bkiri\b', r'\bkanan\b'),
        'it': (r'\bsinistr\w*', r'\bdestr\w*'),
        'pt': (r'\besquerd\w*', r'\bdireit\w*'),
        'ru': (r'\bлев\w*', r'\bправ\w*'),
        'ja': ('左', '右'), 'zh': ('左', '右'), 'ko': ('왼', '오른'),
    }
    text = unicodedata.normalize('NFKC', text).casefold()
    pair = patterns.get(code)
    if pair is None:
        return ()
    expression = '(?P<left>' + pair[0] + ')|(?P<right>' + pair[1] + ')'
    return tuple(token.lastgroup for token in re.finditer(expression, text))


def verified_match(config, code, text, transcript):
    # Keep the original transcript in the receipt. Equivalent spellings of
    # the same spoken word cannot be distinguished by listening (lute/loot).
    equivalent = transcript
    expected = text
    spellings = config.get('homophones', {}).get(code, {})
    if code == 'ja':
        expected = japanese_spelling(expected)
        equivalent = japanese_spelling(equivalent)
        for heard, intended in spellings.items():
            expected = expected.replace(japanese_spelling(heard), japanese_spelling(intended))
            equivalent = equivalent.replace(japanese_spelling(heard), japanese_spelling(intended))
    else:
        # Both sides take the same spelling, so a line written with either
        # form still matches its recording.
        for heard, intended in spellings.items():
            equivalent = re.sub(r'\b' + re.escape(heard) + r'\b', intended,
                                equivalent, flags=re.IGNORECASE)
            expected = re.sub(r'\b' + re.escape(heard) + r'\b', intended,
                              expected, flags=re.IGNORECASE)
    if config.get('verify_directions') and direction_tokens(expected, code) != direction_tokens(equivalent, code):
        return 0.0
    if config.get('verify_numbers'):
        numbers = lambda value: re.findall(r'\d+(?:[.,]\d+)?', unicodedata.normalize('NFKC', value))
        if numbers(expected) != numbers(equivalent):
            return 0.0
    return match(expected, equivalent)


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
            score = verified_match(config, code, text, transcript)
            if best is None or score > best["match"]:
                best = dict(data=clip.read_bytes(), seconds=round(length, 3),
                            transcript=transcript, match=score,
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
               transcriber=config.get('locale_transcribers', {}).get(code, config['transcriber']),
               bytes=len(best["data"]))
    return row


def save(receipt):
    receipt["clips"] = dict(sorted(receipt["clips"].items()))
    temporary = RECEIPT.with_suffix(".json.part")
    temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(RECEIPT)


def main():
    global CONFIG, RECEIPT, VOICE, LOCALES
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
        help="fail when any clip is missing or older than its line")
    parser.add_argument("--locale", action="append", help="only these locales")
    parser.add_argument("--key", action="append", help="only these lines")
    parser.add_argument("--regenerate", action="store_true",
        help="speak the selected lines again even when they are current")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--practice", choices=("taichi", "taichi_male"),
        help="generate a practice's separate language packs with the same verified speech pipeline")
    args = parser.parse_args()
    if args.practice:
        settings = json.loads((ROOT / "apps/practice/content.json").read_text())["narration"][args.practice]
        CONFIG = ROOT / settings["config"]
        RECEIPT = ROOT / settings["receipt"]
        VOICE = ROOT / settings["output_directory"]
        LOCALES = ROOT / settings["text_directory"]
    if not args.check:
        import fcntl
        lock_directory = ROOT / 'backup/narration'
        lock_directory.mkdir(parents=True, exist_ok=True)
        generation_lock = (lock_directory / (CONFIG.stem + '.lock')).open('a')
        try:
            fcntl.flock(generation_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('This narration generation is already running; reuse its receipt.')
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config['keys'] = narration_keys(config)
    codes = locale_codes()
    receipt = {"clips": {}}
    if RECEIPT.is_file():
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = wanted(config, codes, config["keys"])
    if args.locale and any(code not in codes for code in args.locale):
        parser.error('unknown narration locale')
    scoped_rows = [(code, name, text) for code, name, text in rows
                   if (not args.locale or code in args.locale) and
                   (not args.key or name in args.key)]
    if args.check:
        stale = [f"{code}/{key}" for code, key, text in scoped_rows
                 if not current(receipt, config, code, key, text)]
        expected = {f"{code}/{key}" for code, key, _ in rows}
        extra = sorted(set(receipt.get("clips", {})) - expected)
        for name in stale:
            print(f"{name}: clip is missing or older than its line")
        for name in extra:
            print(f"{name}: receipt lists a clip that is no longer a guide line")
        if stale or extra:
            sys.exit(1)
        print(f"All {len(scoped_rows)} selected narration clips match their lines.")
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
    stopped = threading.Event()
    completed = 0

    def run(item):
        nonlocal completed
        if stopped.is_set():
            return
        code, name, text = item
        try:
            row = generate(config, key, code, name, text)
        except ProviderBlocked as error:
            with lock:
                if not stopped.is_set():
                    failures.append(str(error))
                    print(f'STOP: {error}. Completed clips are saved; resume after resolving the provider limit.', flush=True)
                stopped.set()
            return
        except (RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as error:
            with lock:
                failures.append(f"{code}/{name}: {error}")
                print(f"FAIL {code}/{name}: {error}", flush=True)
            return
        with lock:
            receipt["clips"][code + "/" + name] = row
            completed += 1
            save(receipt)
            print(f"{code}/{name}: {row['seconds']:.2f} s, {row['bytes'] / 1000:.1f} kB, "
                  f"match {row['match']:.2f}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(run, selected))
    save(receipt)
    total = sum(row["bytes"] for row in receipt["clips"].values())
    print(f"{completed} of {len(selected)} clips generated; "
          f"{len(receipt['clips'])} clips, {total / 1000000:.2f} MB in all.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
