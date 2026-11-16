#!/usr/bin/env python3
"""Generate verified guide and practice narration through OpenRouter or local Ming.

Each guide line listed in design/lumi-guide/narration.json is read from
locales/<code>.txt and spoken by the configured voice into
assets/practices/guide/voice/<code>/<key>.ogg, one downloadable pack per
language. Recordings go into the practices checkout that
ziran.local.toml maps (scripts/practice_media.py). The receipt beside the configuration
records a hash of each line's text and settings, so only changed lines are
generated again. Every new clip is transcribed and kept only when the
transcript matches its line.

Set OPENROUTER_API_KEY in the environment before generating. --check needs no
network: it fails when a clip is missing, changed, or older than its line.
"""
import argparse
from array import array
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import difflib
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.request

import ogg_opus
import ming_narration
import ming_verification
from narration_diagnostics import Attempts
import f5_russian_narration
import chatterbox_czech_narration
import chatterbox_portuguese_narration
from practice_media import media_path, narration_text_path, packaged_path, writable_media

LOCAL_PROVIDERS = {'ming': ming_verification, 'f5-russian': f5_russian_narration,
                   'chatterbox-czech': chatterbox_czech_narration,
                   'chatterbox-portuguese': chatterbox_portuguese_narration}

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "design/lumi-guide/narration.json"
RECEIPT = ROOT / "design/lumi-guide/receipt.json"
LOCALES = ROOT / "locales"
VOICE = media_path("assets/practices/guide/voice")
MEDIA_ROOT = None
SPEECH = "https://openrouter.ai/api/v1/audio/speech"
CHAT = "https://openrouter.ai/api/v1/chat/completions"
ATTEMPTS = 4


class ProviderBlocked(RuntimeError):
    """Stop the backlog when credits or credentials require operator action."""


LANGUAGES = {
    "en": "English", "es": "Spanish", "cs": "Czech", "de": "German",
    "fr": "French", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
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


def local_engine(config):
    return config.get('_local_engine') or config.get('_ming_engine')


def local_adapter(config, code):
    for module in LOCAL_PROVIDERS.values():
        if code in module.LANGUAGES:
            return module
    return None


def local_transcriber(module, profile, code):
    return module.transcriber(profile, code) if hasattr(module, 'transcriber') else profile['transcriber']


def verified_speaker(config, module, profile, code, text, row, clip):
    """Keep short-clip scores truthful; context requires its independent proof."""
    score = row.get('speaker_cosine')
    if type(score) not in (int, float) or not math.isfinite(score):
        return False
    if 'speaker_verification' not in row:
        return profile['minimum_speaker_cosine'] <= score <= 1.00001
    proof = row['speaker_verification']
    if (module is None or code not in module.LANGUAGES or
            local_adapter(config, code) is not module or module.descriptor(config) != profile or
            not isinstance(proof, dict) or
            proof.get('scope') != 'context_parent' or
            proof.get('actual_clip_cosine') != score or not -1 <= score <= 1.00001):
        return False
    parent_score = proof.get('parent_cosine')
    if (type(parent_score) not in (int, float) or not math.isfinite(parent_score) or
            not profile['minimum_speaker_cosine'] <= parent_score <= 1.00001):
        return False
    try:
        return verify_context_speaker(config, profile, code, text, row, clip) is True
    except (ImportError, ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        return False


def verify_context_speaker(*args):
    # Import only for explicit context proofs; ordinary engines stay independent.
    import local_narration_context
    return local_narration_context.verify_speaker(*args)


def context_verification_identity(profile, code, proof):
    if (code != 'zh' or profile.get('model') != ming_narration.MODEL or
            not isinstance(proof, dict) or proof.get('scope') != 'context_parent'):
        return None
    import local_narration_context
    identity = local_narration_context.crop_verification_identity(profile, code, proof)
    if identity is None:
        return None
    fields = {'profile_sha256', 'model', 'revision', 'artifacts_sha256',
              'adapter_sha256', 'context_recipe_sha256'}
    model = 'openai/whisper-large-v3-turbo'
    if (not isinstance(identity, dict) or set(identity) != fields or
            identity['model'] != model or identity['revision'] != ming_verification.MODELS[model] or
            identity['context_recipe_sha256'] != proof.get('recipe_sha256') or
            any(not isinstance(identity[field], str) or not re.fullmatch('[0-9a-f]{64}', identity[field])
                for field in fields - {'model', 'revision'})):
        raise ValueError('Invalid explicit Chinese context verification identity')
    return identity


def verify_context_transcription(*args):
    import local_narration_context
    return local_narration_context.verified_crop_transcription(*args)


def context_artifacts(artifacts, code):
    """Constrain proof binaries to the selected practice's sibling directory."""
    if not isinstance(artifacts, list) or len(artifacts) > 8 or MEDIA_ROOT is None:
        raise ValueError('Invalid context proof artifacts')
    media = Path(MEDIA_ROOT).resolve()
    voice = VOICE.resolve()
    prefix = voice.relative_to(media).parent / (voice.name + '-context') / code
    result, seen = [], set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {'source', 'destination_relative', 'sha256'}:
            raise ValueError('Invalid context proof artifact fields')
        checksum = artifact['sha256']
        if not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum):
            raise ValueError('Invalid context proof artifact hash')
        relative = PurePosixPath(artifact['destination_relative'])
        if relative != PurePosixPath(prefix.as_posix()) / (checksum + '.wav') or relative in seen:
            raise ValueError('Context proof must use its exact content-addressed sibling path')
        seen.add(relative)
        source = Path(artifact['source']).resolve(strict=True)
        if (not source.is_relative_to((ROOT / 'backup/narration').resolve()) or
                not source.is_file() or not 1 <= source.stat().st_size <= 32 * 1024 * 1024):
            raise ValueError('Context proof source must be bounded ignored narration data')
        subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(source)],
                       check=True, capture_output=True)
        if ming_narration.file_hash(source) != checksum:
            raise ValueError('Changed context proof source')
        target = (media / relative).resolve()
        if not target.is_relative_to(media) or not target.is_relative_to((media / prefix).resolve()):
            raise ValueError('Context proof destination escapes its media directory')
        result.append((source, target, checksum))
    return result


def publish_context_artifacts(artifacts, code):
    for source, target, checksum in context_artifacts(artifacts, code):
        if target.exists():
            if not target.is_file() or ming_narration.file_hash(target) != checksum:
                raise ValueError('Existing context proof artifact has different content')
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + '.', suffix='.part',
                                         delete=False) as output:
            temporary = Path(output.name)
        try:
            shutil.copyfile(source, temporary)
            if ming_narration.file_hash(temporary) != checksum:
                raise ValueError('Context proof changed during binary copy')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def text_hash(config, text, code=None, synthesis=None, speaker_verification=None):
    # A recording's identity: its spoken text and speech settings. The clip is
    # Ogg Opus now; "vorbis_bitrate" stays in this identity only so the 2026
    # re-encode of existing recordings did not mark every line to be spoken again.
    module = local_adapter(config, code)
    if synthesis is not None or (local_engine(config) and module is not None):
        profile = module.descriptor(config) if module else None
        if profile is None or (synthesis is not None and synthesis != module.provenance(profile)):
            return ''
        identity = module.text_hash(config, text, profile, code)
        if speaker_verification is not None:
            recipe = speaker_verification.get('recipe_sha256')
            if not isinstance(recipe, str) or not re.fullmatch('[0-9a-f]{64}', recipe):
                return ''
            identity = digest(json.dumps(dict(synthesis_text_sha256=identity,
                                             context_recipe_sha256=recipe), sort_keys=True).encode())
        return identity
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
        values = entries(narration_text_path(config, code, LOCALES))
        for key in keys:
            text = values.get(key, "").strip()
            if not text:
                raise SystemExit(f"{code}: {key} has no text")
            rows.append((code, key, text))
    return rows


def current(receipt, config, code, key, text):
    row = receipt.get("clips", {}).get(code + "/" + key)
    path = clip_path(code, key)
    if row is None:
        return False
    synthesis = row.get('synthesis')
    if synthesis is not None:
        module = local_adapter(config, code)
        profile = module.descriptor(config) if module else None
        transcription = row.get('transcription', {})
        if (profile is None or
                synthesis != module.provenance(profile) or
                not verified_speaker(config, module, profile, code, text, row, path)):
            return False
        proof = row.get('speaker_verification')
        try:
            context_identity = context_verification_identity(profile, code, proof)
            if context_identity is not None:
                transcriber = context_identity['model'] + '@' + context_identity['revision']
                if (row.get('verification') != context_identity or
                        not verify_context_transcription(profile, code, proof, transcription, context_identity)):
                    return False
            else:
                transcriber = local_transcriber(module, profile, code)
                if (hasattr(module, 'verified_transcription') and
                        not module.verified_transcription(profile, code, transcription, row.get('verification'))):
                    return False
        except (ImportError, ValueError, KeyError, TypeError, OSError):
            return False
        if (row.get('transcriber') != transcriber or
                transcription.get('audio_sha256') != row.get('sha256') or
                transcription.get('truncation') is not False or
                not transcription.get('long_form') or
                abs(transcription.get('seconds', 0) - row.get('seconds', 0)) > 0.05):
            return False
        if ('verification' in profile and
                transcription.get('text', '').strip() != row.get('transcript')):
            return False
    elif local_engine(config):
        return False
    if not (row.get("text_sha256") == text_hash(config, text, code, synthesis, row.get('speaker_verification')) and
            0.5 <= row.get("seconds", 0) <= maximum_clip_seconds(config, key) and
            path.is_file() and digest(path.read_bytes()) == row["sha256"] and
            assessment(config, code, text, row.get('transcript', ''),
                       row.get('seconds', 0), synthesis is not None,
                       speaker_verification=row.get('speaker_verification'))[0] >= config['minimum_match']):
        return False
    try:
        decoded = encoded_audio_stats(path)
        return (abs(decoded['frames'] / ogg_opus.OPUS_RATE - row['seconds']) <= 0.05 and
                all(result['peak'] < 1 for result in decoded['rates'].values()))
    except (ValueError, OSError, subprocess.SubprocessError):
        return False


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


def encoded_audio_stats(path):
    """Validate the complete mono stream and measure its unclamped float output."""
    data = Path(path).read_bytes()
    pages = ogg_opus.pages(data)
    if not pages or not pages[0][2] & 2 or not pages[-1][2] & 4:
        raise ValueError('Opus stream is missing its beginning or end')
    serial = data[14:18]
    for index, (offset, length, flags, _) in enumerate(pages):
        page = bytearray(data[offset:offset + length])
        if (page[4] != 0 or page[14:18] != serial or
                int.from_bytes(page[18:22], 'little') != index or
                (index > 0 and flags & 2) or
                (index < len(pages) - 1 and flags & 4)):
            raise ValueError('Invalid or discontinuous Ogg stream')
        checksum = int.from_bytes(page[22:26], 'little')
        page[22:26] = bytes(4)
        if ogg_opus.ogg_crc(page) != checksum:
            raise ValueError('Invalid Ogg page checksum')
    header = 27 + data[26]
    if (data[header:header + 8] != b'OpusHead' or len(data[header:]) < 19 or
            data[header + 8] != 1 or data[header + 9] != 1):
        raise ValueError('Expected a mono Opus stream')
    frames = ogg_opus.opus_frames(data)
    ogg_opus.end_trim(data, frames)
    rates = {}
    for rate in (16000, ogg_opus.OPUS_RATE):
        result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror',
            '-err_detect', 'explode', '-threads', '1', '-i', str(path),
            '-map', '0:a:0', '-ar', str(rate), '-ac', '1', '-f', 'f32le', 'pipe:1'],
            check=True, capture_output=True)
        if len(result.stdout) % 4:
            raise ValueError('Incomplete decoded float sample')
        samples = array('f')
        samples.frombytes(result.stdout)
        if sys.byteorder != 'little':
            samples.byteswap()
        expected = (frames * rate + ogg_opus.OPUS_RATE - 1) // ogg_opus.OPUS_RATE
        if not samples or len(samples) != expected:
            raise ValueError(f'Incomplete Opus decode at {rate} Hz: {len(samples)} of {expected} samples')
        if not all(math.isfinite(value) for value in samples):
            raise ValueError('Nonfinite decoded audio')
        peak = max(map(abs, samples))
        rates[str(rate)] = dict(samples=len(samples), seconds=len(samples) / rate,
                               peak=peak, full_scale_samples=sum(abs(value) >= 1 for value in samples))
    return dict(frames=frames, rates=rates)


def encode(config, pcm, work):
    """Raw speech to a small mono Ogg Opus clip without its silences."""
    raw = work / "speech.pcm"
    raw.write_bytes(pcm)
    speech = work / "speech-clip-rate.pcm"
    clip = work / "clip.ogg"
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
            "areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,"
            "areverse")
    # The trimmed speech at the clip's rate first, so its exact length is known.
    rate = int(config["sample_rate"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le",
        "-ar", str(config["pcm_sample_rate"]), "-ac", "1", "-i", str(raw),
        "-af", trim, "-ar", str(rate), "-ac", "1", "-c:a", "pcm_s16le",
        "-f", "s16le", str(speech)], check=True, capture_output=True)
    source = speech.read_bytes()
    if not source or len(source) % 2:
        raise ValueError('Silence trimming left no complete speech samples')
    if rate not in (8000, 12000, 16000, 24000, 48000):
        raise ValueError('Unsupported Opus input sample rate')
    frames = len(source) // 2 * (ogg_opus.OPUS_RATE // rate)
    gain, passes = 1.0, []
    for attempt in range(3):
        input_path = speech
        if attempt:
            samples = array('h')
            samples.frombytes(source)
            if sys.byteorder != 'little':
                samples.byteswap()
            attenuated = array('h', (round(value * gain) for value in samples))
            if sys.byteorder != 'little':
                attenuated.byteswap()
            input_path = work / 'speech-headroom.pcm'
            input_path.write_bytes(attenuated.tobytes())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le",
            "-ar", str(rate), "-ac", "1", "-i", str(input_path),
            "-c:a", "libopus", "-b:a", config.get("opus_bitrate", "16k"),
            "-application", "voip", "-vbr", "on", "-map_metadata", "-1", "-f", "ogg", str(clip)],
            check=True, capture_output=True)
        # End at the unchanged speech frame count, without the codec's padding.
        clip.write_bytes(ogg_opus.end_trim(clip.read_bytes(), frames))
        decoded = encoded_audio_stats(clip)
        passes.append(dict(gain=gain, audio_sha256=digest(clip.read_bytes()), decoded=decoded))
        (work / 'encoding-headroom.json').write_text(json.dumps(dict(
            source_pcm_sha256=digest(pcm), trimmed_pcm_sha256=digest(source),
            input_sample_rate=rate, frames=frames, passes=passes), indent=2) + '\n')
        peak = max(result['peak'] for result in decoded['rates'].values())
        if peak < 1:
            return clip
        # Codec response is not linear. Leave conservative headroom, re-encode
        # from the untouched source, and measure every candidate independently.
        gain *= min(0.9, 0.9 / peak)
    raise ValueError('Encoded audio still exceeds full scale after three bounded passes')


def seconds(path):
    """How long the Ogg Opus clip plays, from its own trimmed timing."""
    return ogg_opus.opus_seconds(path.read_bytes())


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
                                   normalized(transcript), autojunk=False).ratio()


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


def comparison_spellings(config, code, text, transcript):
    # Keep the original transcript in the receipt. Equivalent spellings of
    # the same spoken word cannot be distinguished by listening (lute/loot).
    equivalent = transcript
    expected = text
    contextual = config.get('contextual_spellings', {}).get(code)
    if contextual and contextual['source'] in text:
        # This exact phrase has a homophone spelling in blind Chinese ASR.
        # It never changes a pulse word elsewhere or supplies a missing word.
        for form in contextual['forms']:
            equivalent = equivalent.replace(form, contextual['source'])
        if code == 'zh':
            # Only the documented phrase's other traditional spellings.
            equivalent = equivalent.translate(str.maketrans('氣蓋後邁', '气盖后迈'))
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
    return expected, equivalent


def verified_match(config, code, text, transcript):
    expected, equivalent = comparison_spellings(config, code, text, transcript)
    if config.get('verify_directions') and direction_tokens(expected, code) != direction_tokens(equivalent, code):
        return 0.0
    if config.get('verify_numbers'):
        numbers = lambda value: re.findall(r'\d+(?:[.,]\d+)?', unicodedata.normalize('NFKC', value))
        if numbers(expected) != numbers(equivalent):
            return 0.0
    return match(expected, equivalent)


def maximum_clip_seconds(config, name):
    """A bounded speech budget, optionally preserving each cue's quiet period."""
    limits = config.get('maximum_clip_seconds_by_key', {})
    if not isinstance(limits, dict):
        raise ValueError('Per-cue speech limits must be a mapping')
    maximum = config.get('maximum_clip_seconds', 40.0)
    selected = limits.get(name, maximum)
    for value in (maximum, selected):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.5 <= value <= 120:
            raise ValueError('Speech duration limits must be between 0.5 and 120 seconds')
    if selected > maximum:
        raise ValueError('A cue speech limit exceeds the configured maximum')
    interval = config.get('cue_interval_seconds_by_key', {}).get(name)
    quiet = config.get('quiet_after_seconds_by_key', {}).get(name)
    if interval is not None or quiet is not None:
        if (type(interval) not in (int, float) or type(quiet) not in (int, float) or
                not 0 <= quiet < interval <= 7200 or selected + quiet > interval):
            raise ValueError('Cue speech budget would consume its reserved quiet time')
    return selected


def complete_match(config, code, text, transcript, length, ming=False):
    score = verified_match(config, code, text, transcript)
    if ming:
        # A short missing clause can pass the whole-cue score at any duration.
        # Compare both the closing phrase and its context using the same locale
        # spelling aliases as the full transcript, without changing the receipt.
        expected, heard = comparison_spellings(config, code, text, transcript)
        expected, heard = normalized(expected), normalized(heard)
        for size in (64, 24):
            tail = difflib.SequenceMatcher(None, expected[-size:], heard[-size:]).ratio()
            if tail < 0.85:
                return 0.0
    return score


def assessment(config, code, text, transcript, length, local=False, *, speaker_verification=None):
    strict_context = False
    if local and speaker_verification is not None and (
            (code == 'cs' and text in ('1.', '2.', '3.')) or
            (code == 'pt' and text in ('Um.', 'Dois.', 'Três.'))):
        import local_narration_context as context
        # Structural speaker verification runs first in generation/current.
        # Only sealed count recipes change these comparison views.
        rule = context.comparison_rule_from_proof(code, text, speaker_verification)
        if rule is not None:
            text, transcript = context.comparison_views(rule, text, transcript)
            strict_context = text != transcript
    expected, heard = comparison_spellings(config, code, text, transcript)
    directions = dict(expected=direction_tokens(expected, code), heard=direction_tokens(heard, code))
    numbers = lambda value: re.findall(r'\d+(?:[.,]\d+)?', unicodedata.normalize('NFKC', value))
    expected_normalized, heard_normalized = normalized(expected), normalized(heard)
    tails = {str(size): difflib.SequenceMatcher(None, expected_normalized[-size:],
                                               heard_normalized[-size:]).ratio()
             for size in (64, 24)} if local else {}
    score = 0.0 if strict_context else complete_match(config, code, text, transcript, length, local)
    reasons = ['context_tokens'] if strict_context else []
    if config.get('verify_directions') and directions['expected'] != directions['heard']:
        reasons.append('direction')
    if config.get('verify_numbers') and numbers(expected) != numbers(heard):
        reasons.append('number')
    if any(value < 0.85 for value in tails.values()):
        reasons.append('ending')
    if match(expected, heard) < config['minimum_match']:
        reasons.append('transcript')
    return score, dict(score=score, text_score=match(expected, heard),
                       directions=directions, ending_scores=tails, reasons=reasons)


def generate(config, key, code, name, text):
    """Speaks a line until its transcript matches; returns the receipt row."""
    maximum = maximum_clip_seconds(config, name)
    best = None
    staging = ROOT / 'backup/narration/tmp'
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="voice-", dir=staging) as folder:
        work = Path(folder)
        diagnostics = Attempts(ROOT, code, name, work.name, digest(text.encode()))
        last = None
        for attempt in range(ATTEMPTS):
            engine = local_engine(config)
            detail = dict(attempt=attempt, maximum_seconds=maximum,
                          minimum_match=config['minimum_match'], transcript=None, reasons=[])
            last = detail
            try:
                if engine:
                    pcm, generation = engine.speak(config, text, code, work, attempt)
                else:
                    pcm, generation = speak(config, key, text)
                detail['synthesis'] = generation
                clip = encode(config, pcm, work)
                length = seconds(clip)
                detail.update(seconds=length, audio_sha256=digest(clip.read_bytes()))
                if not 0.5 <= length <= maximum:
                    detail['reasons'] = ['duration']
                    diagnostics.save(detail)
                    continue
                speaker_cosine = engine.speaker_match(clip) if engine else None
                speaker_verification = None
                artifacts = []
                if engine:
                    detail.update(speaker_cosine=speaker_cosine,
                                  minimum_speaker_cosine=engine.profile['minimum_speaker_cosine'])
                    speaker_verification = copy.deepcopy(getattr(engine, 'last_speaker_verification', None))
                    speaker_row = dict(speaker_cosine=speaker_cosine, sha256=detail['audio_sha256'],
                                       seconds=length, synthesis=generation)
                    if speaker_verification is not None:
                        detail['speaker_verification'] = speaker_verification
                        speaker_row['speaker_verification'] = speaker_verification
                        artifacts = copy.deepcopy(getattr(engine, 'context_artifacts', []))
                        context_artifacts(artifacts, code)
                    speaker_config = dict(config, _context_artifacts=artifacts)
                    if not verified_speaker(speaker_config, local_adapter(config, code), engine.profile,
                                            code, text, speaker_row, clip):
                        detail['reasons'] = ['speaker']
                        diagnostics.save(detail)
                        continue
                transcript = engine.transcribe(clip, code) if engine else transcribe(config, key, clip, code, work)
                detail['transcript'] = transcript
                if engine:
                    context_identity = context_verification_identity(engine.profile, code, speaker_verification)
                    if context_identity is not None and not verify_context_transcription(
                            engine.profile, code, speaker_verification, engine.last_transcription, context_identity):
                        raise RuntimeError('Context crop ASR metadata failed verification')
                    detail['asr'] = {field: engine.last_transcription.get(field) for field in (
                        'model', 'revision', 'artifacts_sha256', 'language', 'audio_sha256',
                        'input_samples', 'seconds', 'truncation', 'long_form')}
                score, scores = assessment(config, code, text, transcript, length, bool(engine),
                                           speaker_verification=speaker_verification)
                detail.update(scores)
                diagnostics.save(detail)
            except Exception as error:
                retry_context = False
                if config.get('_context_profile'):
                    import local_narration_context
                    retry_context = isinstance(error, local_narration_context.ContextRejected)
                    if retry_context:
                        detail['context'] = copy.deepcopy(error.diagnostics)
                detail.update(reasons=['context' if retry_context else 'error'],
                              error=type(error).__name__ + ': ' + str(error))
                diagnostics.save(detail)
                if retry_context:
                    continue
                raise
            if best is None or score > best["match"]:
                best = dict(data=clip.read_bytes(), seconds=round(length, 3),
                            transcript=transcript, match=score,
                            generation_id=generation, attempts=attempt + 1)
                if engine:
                    best['synthesis'] = generation
                    best['speaker_cosine'] = speaker_cosine
                    if speaker_verification is not None:
                        best['speaker_verification'] = copy.deepcopy(speaker_verification)
                        best['_context_artifacts'] = artifacts
                    best['transcription'] = engine.last_transcription
                    module = local_adapter(config, code)
                    identity = context_verification_identity(engine.profile, code, speaker_verification)
                    if identity is not None:
                        best['verification'] = identity
                    elif hasattr(module, 'verification_identity'):
                        identity = module.verification_identity(engine.profile, code)
                        if identity is not None:
                            best['verification'] = identity
                    if getattr(engine, 'last_generation', None) is not None:
                        best['segmentation'] = engine.last_generation
            if score >= config["minimum_match"]:
                break
    if best is None or best["match"] < config["minimum_match"]:
        heard = best["transcript"] if best else "no usable transcript"
        last_heard = last['transcript'] if last and last['transcript'] is not None else 'not transcribed'
        reasons = ', '.join(last['reasons']) if last else 'no attempts'
        raise RuntimeError(f"{code}/{name} never matched its text; best heard: {heard}; "
                           f"last attempt {last['attempt'] if last else '-'} ({reasons}): {last_heard}; "
                           f"diagnostics: {diagnostics.path.relative_to(ROOT)}")
    destination = clip_path(code, name)
    if 'speaker_verification' in best:
        publish_context_artifacts(best.pop('_context_artifacts', []), code)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".ogg.part")
    temporary.write_bytes(best["data"])
    temporary.replace(destination)
    row = {name: value for name, value in best.items() if name != "data"}
    engine = local_engine(config)
    if engine:
        identity = context_verification_identity(engine.profile, code, best.get('speaker_verification'))
        transcriber = (identity['model'] + '@' + identity['revision'] if identity is not None else
                       local_transcriber(local_adapter(config, code), engine.profile, code))
    else:
        transcriber = config.get('locale_transcribers', {}).get(code, config['transcriber'])
    row.update(file=packaged_path(destination, MEDIA_ROOT),
               text_sha256=text_hash(config, text, code, best.get('synthesis'), best.get('speaker_verification')),
               sha256=digest(best["data"]),
               transcriber=transcriber,
               bytes=len(best["data"]))
    row['maximum_seconds'] = maximum
    if name in config.get('quiet_after_seconds_by_key', {}):
        row['quiet_after_seconds'] = config['quiet_after_seconds_by_key'][name]
        row['cue_interval_seconds'] = config['cue_interval_seconds_by_key'][name]
    return row


def save(receipt):
    receipt["clips"] = dict(sorted(receipt["clips"].items()))
    temporary = RECEIPT.with_suffix(".json.part")
    temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(RECEIPT)


def main():
    global CONFIG, RECEIPT, VOICE, LOCALES, MEDIA_ROOT
    generation_lock = None
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
        help="fail when any clip is missing or older than its line")
    parser.add_argument("--locale", action="append", help="only these locales")
    parser.add_argument("--key", action="append", help="only these lines")
    parser.add_argument("--regenerate", action="store_true",
        help="speak the selected lines again even when they are current")
    parser.add_argument("--jobs", type=int)
    parser.add_argument('--ming-profile', type=Path,
        help='explicit local runtime/model/reference/ASR paths; enables Ming for supported female locales')
    parser.add_argument('--local-provider', choices=tuple(name for name in LOCAL_PROVIDERS if name != 'ming'),
        help='explicit offline language engine; never falls back to another provider')
    parser.add_argument('--local-voice-profile', type=Path,
        help='private local paths; run with this profile\'s own Python interpreter')
    parser.add_argument('--preflight', action='store_true',
        help='verify local voice hashes without loading a model or generating audio')
    parser.add_argument('--cached-only', action='store_true',
        help='recheck existing Ming or explicit local-context PCM; fail before new synthesis')
    parser.add_argument('--context-profile', type=Path,
        help='explicit public short-cue context policy; ordinary cues retain their engine and identity')
    parser.add_argument('--context-local-profile', type=Path,
        help='explicit private context QA/alignment paths; not required for --check')
    parser.add_argument("--practice", choices=tuple(json.loads((ROOT / "apps/practice/content.json").read_text())["narration"]),
        help="generate a practice's separate language packs with the same verified speech pipeline")
    args = parser.parse_args()
    if bool(args.local_provider) != bool(args.local_voice_profile):
        parser.error('--local-provider and --local-voice-profile are required together')
    if args.ming_profile and args.local_provider:
        parser.error('Select one local provider per command')
    local_path = args.ming_profile or args.local_voice_profile
    provider = 'ming' if args.ming_profile else args.local_provider
    module = LOCAL_PROVIDERS.get(provider)
    if args.context_local_profile and not args.context_profile:
        parser.error('--context-local-profile requires --context-profile')
    if args.context_profile and (not local_path or (not args.check and not args.context_local_profile)):
        parser.error('--context-profile requires a local speech provider and --context-local-profile except with --check')
    if (args.cached_only and provider != 'ming' and
            not (args.context_profile and args.context_local_profile)):
        parser.error('--cached-only requires Ming verification or both explicit local context profiles')
    if args.local_voice_profile and not args.check:
        local = json.loads(args.local_voice_profile.read_text())
        if os.path.abspath(sys.executable) != os.path.abspath(local['python']):
            parser.error('Run the generator with the selected local profile Python interpreter')
    if args.practice:
        settings = json.loads((ROOT / "apps/practice/content.json").read_text())["narration"][args.practice]
        CONFIG = ROOT / settings["config"]
        RECEIPT = ROOT / settings["receipt"]
        VOICE = media_path(settings["output_directory"])
        LOCALES = media_path(settings["text_directory"])
    if local_path and args.practice and args.practice.endswith('_male'):
        parser.error('Local female generation must not overwrite male recordings')
    if args.preflight and not local_path:
        parser.error('--preflight requires an explicit local profile')
    if not args.check and not args.preflight:
        # Recordings are written only into a practices checkout.
        MEDIA_ROOT = writable_media().resolve()
        VOICE = VOICE.resolve()
        LOCALES = LOCALES.resolve()
        if not VOICE.is_relative_to(MEDIA_ROOT):
            raise SystemExit('Narration output must stay inside its canonical practices checkout')
        import fcntl
        lock_directory = ROOT / 'backup/narration'
        lock_directory.mkdir(parents=True, exist_ok=True)
        lock_name = digest(str(VOICE.resolve()).encode())[:20]
        generation_lock = (lock_directory / (lock_name + '.lock')).open('a')
        try:
            fcntl.flock(generation_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('This narration generation is already running; reuse its receipt.')
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config['_cached_only'] = args.cached_only
    if args.context_profile:
        config['_context_profile'] = str(args.context_profile)
    media_directory = Path(MEDIA_ROOT).resolve() if MEDIA_ROOT else media_path('assets/practices/').resolve()
    if VOICE.resolve().is_relative_to(media_directory):
        config['_context_voice_directory'] = VOICE.resolve().relative_to(media_directory).as_posix()
    elif args.context_profile:
        parser.error('Context voice directory must be inside canonical practice media')
    config['keys'] = narration_keys(config)
    codes = locale_codes()
    jobs = args.jobs if args.jobs is not None else (1 if local_path else 6)
    if jobs < 1:
        parser.error('--jobs must be positive')
    if args.key and any(name not in config['keys'] for name in args.key):
        parser.error('unknown narration key')
    if local_path:
        if jobs != 1:
            parser.error('Local speech uses one cached model; use --jobs 1')
        if args.locale and any(code not in module.LANGUAGES for code in args.locale):
            parser.error(provider + ' supports only ' + ', '.join(module.LANGUAGES) +
                         '; no fallback is performed')
        profile = module.descriptor(config)
        if not profile:
            parser.error('This narration config has no public ' + provider + ' profile')
        if args.cached_only and provider == 'ming' and 'verification' not in profile:
            parser.error('--cached-only requires a routed verification profile')
        if args.check:
            # No installed model or interpreter is needed for receipt validation.
            config['_local_engine'] = True
        else:
            config['_local_engine'] = module.Engine(profile, local_path)
            if args.context_profile:
                import local_narration_context
                config['_local_engine'] = local_narration_context.ContextEngine(
                    config['_local_engine'], config, args.context_profile, args.context_local_profile,
                    encode=encode, complete_match=complete_match, identity=module.provenance(profile),
                    voice_directory=config['_context_voice_directory'])
        if args.preflight:
            print('Local ' + provider + ' adapter, model and female reference hashes match; no audio generated.')
            return
        codes = [code for code in codes if code in module.LANGUAGES]
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
        expected = {f"{code}/{key}" for code in locale_codes() for key in config['keys']}
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
    if not key and not local_path:
        raise SystemExit("Set OPENROUTER_API_KEY before generating narration.")
    selected = [(code, name, text) for code, name, text in rows
                if (not args.locale or code in args.locale) and
                (not args.key or name in args.key) and
                (args.regenerate or not current(receipt, config, code, name, text))]
    if local_path:
        identity = module.provenance(profile)
        receipt['provider'] = 'Mixed' if receipt['clips'] else identity['provider']
        receipt[provider] = identity
    else:
        receipt.update(provider="OpenRouter", model=config["model"],
                       voice=config["voice"], transcriber=config["transcriber"],
                       documentation=config["documentation"])
    # Keep unselected locales and older compatible recordings in mixed receipts.
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

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        list(pool.map(run, selected))
    save(receipt)
    total = sum(row["bytes"] for row in receipt["clips"].values())
    print(f"{completed} of {len(selected)} clips generated; "
          f"{len(receipt['clips'])} clips, {total / 1000000:.2f} MB in all.")
    if generation_lock is not None:
        generation_lock.close()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
