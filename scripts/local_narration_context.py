"""Explicit short-cue context, with contiguous audio and separate speaker evidence.

This wrapper leaves the underlying synthesis profile and ordinary requests intact.
Public proof WAVs allow offline receipt checks without models or private caches.
Prepare the base engines normally, then run this file with --configure explicitly.
"""
import argparse
import array
import difflib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unicodedata
import wave

from practice_media import narration_text_path

from f5_russian_narration import file_hash, json_hash, text_hash as local_text_hash
import ogg_opus

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'contiguous-prefix-v1'
ASR_MODEL = 'openai/whisper-large-v3-turbo'
ASR_REVISION = '41f01f3fe87f28c78e2fbf8b568835947dd65ed9'
POLICY = ROOT / 'design/narration/short-context.json'
RETAIN_LEADING_PCM0 = 'retain-leading-pcm0-v1'
CZECH_COUNT_COMPARISON = 'czech-count-1-2-3-v1'
CZECH_COUNT_PARENTS = {
    '3.': 'Tři, dva, jedna, připrav se na další cvik.',
    '2.': 'Dva, jedna, připrav se na další cvik.',
    '1.': 'Jedna, připrav se na další cvik a klidně dýchej.',
}

PORTUGUESE_COUNT_COMPARISON = 'portuguese-count-1-2-3-v1'
PORTUGUESE_COUNT_PARENTS = {
    'Três.': 'Três. Prepare o corpo para o próximo exercício.',
    'Dois.': 'Dois. Prepare o corpo para o próximo exercício.',
    'Um.': 'Um. Prepare o corpo para o próximo exercício.',
}


class ContextRejected(RuntimeError):
    """One synthesized candidate failed quality checks; its recipe stays valid."""

    def __init__(self, reason, diagnostics=None):
        super().__init__(reason)
        self.diagnostics = dict(diagnostics or {})


def words(text):
    normalized = unicodedata.normalize('NFKC', text).casefold().replace('氣', '气')
    normalized = re.sub(r'([\u3400-\u9fff])', r' \1 ', normalized)
    return re.findall(r"\w+(?:['’\-]\w+)*", normalized)


def rule_comparison(rule):
    """Only explicitly registered workout count rules may equate counts."""
    comparison = rule.get('comparison')
    if comparison is None:
        return None
    if comparison == {'version': PORTUGUESE_COUNT_COMPARISON}:
        if (rule.get('locale') != 'pt' or rule.get('voice_directory') != 'workout/voice' or
                rule.get('text') not in PORTUGUESE_COUNT_PARENTS or
                rule.get('parent_text') != PORTUGUESE_COUNT_PARENTS[rule['text']] or
                any(field in rule for field in ('prefix_alignment', 'crop_asr', 'parent_source'))):
            raise ValueError('Unsupported Portuguese count comparison rule')
        return PORTUGUESE_COUNT_COMPARISON
    if (comparison != {'version': CZECH_COUNT_COMPARISON} or
            rule.get('locale') != 'cs' or rule.get('voice_directory') != 'workout/voice' or
            rule.get('text') not in CZECH_COUNT_PARENTS or
            rule.get('parent_text') != CZECH_COUNT_PARENTS[rule['text']] or
            any(field in rule for field in ('prefix_alignment', 'crop_asr', 'parent_source'))):
        raise ValueError('Unsupported Czech count comparison rule')
    return CZECH_COUNT_COMPARISON


def comparison_words(text, comparison=None):
    if comparison not in (None, CZECH_COUNT_COMPARISON, PORTUGUESE_COUNT_COMPARISON):
        raise ValueError('Unsupported context comparison version')
    tokens = words(text)
    if comparison == PORTUGUESE_COUNT_COMPARISON:
        # Validate raw ASCII boundaries before words() can discard a sign or
        # normalize a different numeric spelling. Default/Czech views stay intact.
        numeric = lambda token: any(char.isnumeric() for char in token)
        if any(numeric(token) for token in tokens):
            first = re.match(r'^\s*([123])(?:[.!?,:;])?(?=\s|$)', text)
            if (first and tokens[0] == first[1] and
                    not any(numeric(token) for token in tokens[1:])):
                tokens[0] = {'1': 'um', '2': 'dois', '3': 'três'}[first[1]]
        return tokens
    if comparison is not None:
        spellings = {'1': 'jedna', '2': 'dva', '3': 'tři'}
        tokens = [spellings.get(token, token) for token in tokens]
    return tokens


def comparison_views(rule, text, transcript):
    comparison = rule_comparison(rule)
    if comparison is None:
        return text, transcript
    if text not in (rule['text'], rule['parent_text']):
        raise ValueError('Count comparison requires its exact registered text')
    return (' '.join(comparison_words(text, comparison)),
            ' '.join(comparison_words(transcript, comparison)))


def parent_match(match, config, code, rule, transcript, length):
    expected, heard = comparison_views(rule, rule['parent_text'], transcript)
    if rule_comparison(rule) is not None and expected != heard:
        return 0.0
    return match(config, code, expected, heard, length, True)


def comparison_rule_from_proof(code, text, proof):
    """Resolve a sealed rule; never infer equivalence from locale or digits."""
    if (not isinstance(proof, dict) or proof.get('scope') != 'context_parent' or
            proof.get('version') != VERSION or proof.get('locale') != code or
            proof.get('text_sha256') != pcm_hash(text.encode()) or
            proof.get('proof_sha256') != json_hash({k: v for k, v in proof.items() if k != 'proof_sha256'})):
        raise ValueError('Invalid context comparison proof')
    rule = recipe(ROOT / proof['policy_path'], code, text, proof['voice_directory'])
    if rule is None or rule['sha256'] != proof['recipe_sha256']:
        raise ValueError('Changed context comparison recipe')
    return rule if rule_comparison(rule) is not None else None


def load_policy(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'design/narration'):
        raise ValueError('Context policy must be a public narration descriptor')
    policy = json.loads(path.read_text())
    if (policy.get('version') != VERSION or policy.get('helper_sha256') != file_hash(__file__) or
            policy.get('verifier_sha256') != file_hash(ROOT / 'scripts/generate-lumi-guide-narration.py') or
            policy.get('asr_model') != ASR_MODEL or policy.get('asr_revision') != ASR_REVISION):
        raise ValueError('Changed or unsupported context verification recipe')
    return policy


def recipe(policy_path, code, text, voice_directory):
    policy = load_policy(policy_path)
    if voice_directory != policy['voice_directory']:
        return None
    candidates = [rule for rule in policy['rules'] if rule['locale'] == code and rule['text'] == text]
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError('Duplicate context rule')
    rule = dict(candidates[0])
    if 'prefix_alignment' in rule and (rule['prefix_alignment'] != RETAIN_LEADING_PCM0 or
            (code, text) not in (('cs', 'Vydechněte.'), ('ru', 'Вдохните.')) or
            voice_directory != 'sunsalutation/voice' or 'parent_source' not in rule):
        raise ValueError('Unsupported retained-leading-PCM context rule')
    if 'crop_asr' in rule and (code != 'zh' or text not in ('吸气。', '呼气。') or
            voice_directory != 'sunsalutation/voice' or
            'parent_source' not in rule or
            rule['crop_asr'] != dict(model=ASR_MODEL, revision=ASR_REVISION, artifacts=policy['asr_artifacts'])):
        raise ValueError('Unsupported short-context final transcription route')
    if 'parent_source' in rule:
        source = rule['parent_source']
        config = json.loads((ROOT / 'design/sun-salutation/narration/narration.json').read_text())
        source_path = narration_text_path(config, code, ROOT / 'design/sun-salutation/narration/text')
        entries = dict(re.findall(r'\[([^\]]+)\]\n(.*?)(?=\n---|\Z)', source_path.read_text(), re.S))
        if (source['file'] != str(source_path.relative_to(ROOT)) or source['sha256'] != file_hash(source_path) or
                entries[source['key']].strip() != rule['parent_text']):
            raise ValueError('Changed registered context parent source')
    comparison = rule_comparison(dict(rule, voice_directory=voice_directory))
    prefix = comparison_words(text, comparison)
    if (not 1 <= len(prefix) <= 4 or len(text) > 80 or
            comparison_words(rule['parent_text'], comparison)[:len(prefix)] != prefix or
            len(comparison_words(rule['parent_text'], comparison)) <= len(prefix) or
            not 0.5 <= rule['maximum_parent_seconds'] <= 5.8 or
            rule['minimum_parent_match'] != 0.92):
        raise ValueError('Context must begin with the exact requested short phrase')
    rule.update(policy_path=str(Path(policy_path).resolve().relative_to(ROOT)),
                policy_sha256=file_hash(policy_path), voice_directory=voice_directory)
    rule['sha256'] = json_hash(rule)
    return rule


def packet_hash(path):
    """Bind Opus audio, header gain and playback length; ignore Ogg serial/tags."""
    data = Path(path).read_bytes()
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('Oversized context clip')
    packets, pending = [], bytearray()
    for offset, length, _, _ in ogg_opus.pages(data):
        page = bytearray(data[offset:offset + length])
        checksum = int.from_bytes(page[22:26], 'little')
        page[22:26] = b'\0' * 4
        if ogg_opus.ogg_crc(page) != checksum:
            raise ValueError('Changed context Ogg page')
        segments = data[offset + 26]
        at = offset + 27 + segments
        for size in data[offset + 27:offset + 27 + segments]:
            pending.extend(data[at:at + size])
            at += size
            if size < 255:
                packets.append(bytes(pending))
                pending.clear()
    if pending or len(packets) < 3 or not packets[0].startswith(b'OpusHead'):
        raise ValueError('Incomplete context Opus stream')
    import hashlib
    digest = hashlib.sha256()
    digest.update(str(ogg_opus.opus_frames(data)).encode())
    for packet in packets:
        if not packet.startswith(b'OpusTags'):
            digest.update(len(packet).to_bytes(4, 'little'))
            digest.update(packet)
    return digest.hexdigest()


def pcm_hash(pcm):
    import hashlib
    return hashlib.sha256(pcm).hexdigest()


def read_wav(path):
    if not 44 <= Path(path).stat().st_size <= 2 * 1024 * 1024:
        raise ValueError('Invalid context WAV size')
    with wave.open(str(path), 'rb') as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 24000:
            raise ValueError('Context proof requires mono 24 kHz PCM16')
        pcm = audio.readframes(audio.getnframes())
        if len(pcm) != audio.getnframes() * 2:
            raise ValueError('Truncated context PCM')
    return pcm


def write_wav(path, pcm):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(pcm)


def prefix_range(text, alignment, frames, *, retain_leading_pcm0=False, comparison=None):
    if type(retain_leading_pcm0) is not bool:
        raise ValueError('Explicit leading-PCM extraction mode required')
    if comparison is not None and retain_leading_pcm0:
        raise ValueError('Count alignment retains the ordinary onset ceiling')
    target = comparison_words(text, comparison)
    chunks = alignment['words']
    if not isinstance(chunks, list) or not 2 <= len(chunks) <= 256:
        raise ValueError('Invalid context alignment size')
    alignment_text = ' '.join(chunk['text'] for chunk in chunks)
    # Whisper may split an actual internal connector: penchez / -vous, l' / air.
    # Reconstruct only that spacing for coherence; retain the original chunks.
    alignment_text = re.sub(r"(?<=[^\W\d_])\s*([-’'])\s*(?=[^\W\d_])", r'\1', alignment_text)
    if 'text' in alignment and comparison_words(alignment_text, comparison) != comparison_words(alignment['text'], comparison):
        raise ValueError('Context timestamps do not describe the actual full transcription')
    previous = 0.0
    for chunk in chunks:
        start, end = chunk['start'], chunk['end']
        if (not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (start, end)) or
                not previous <= start <= end <= frames / 24000 + 0.04):
            raise ValueError('Nonmonotonic context alignment')
        previous = end
    consumed = []
    boundary = None
    for index, chunk in enumerate(chunks):
        consumed.extend(comparison_words(chunk['text'], comparison))
        if consumed == target:
            boundary = index
            break
        if target[:len(consumed)] != consumed:
            break
    if boundary is None or boundary + 1 >= len(chunks):
        raise ValueError('Alignment does not start with the exact short phrase')
    end = chunks[boundary]['end']
    following = chunks[boundary + 1]['start']
    if (not all(isinstance(value, (int, float)) and math.isfinite(value)
                for value in (end, following, chunks[0]['start'])) or
            not 0 <= chunks[0]['start'] <= end or
            (not retain_leading_pcm0 and chunks[0]['start'] > 0.3) or
            not 0 < end <= following <= frames / 24000 + 0.04):
        raise ValueError('Invalid or overlapping context word boundary')
    end_sample = round(min(end + 0.025, following) * 24000)
    if not 12000 <= end_sample < frames:
        raise ValueError('Context crop would be empty, too short or include the parent ending')
    # ASR onset can be late within the first word. Always retain sample zero;
    # the explicit mode omits only the onset ceiling, never preceding audio.
    return 0, end_sample


def verifier():
    spec = importlib.util.spec_from_file_location('context_parent_verifier', ROOT / 'scripts/generate-lumi-guide-narration.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.complete_match


def _parent_source(config, proof, actual_clip):
    relative = PurePosixPath(proof['parent']['file'])
    directory = PurePosixPath(proof['voice_directory'])
    prefix = directory.parent / (directory.name + '-context') / proof['locale']
    if relative != prefix / (proof['parent']['sha256'] + '.wav'):
        raise ValueError('Invalid public context artifact path')
    for artifact in config.get('_context_artifacts', []):
        if artifact['destination_relative'] == str(relative) and artifact['sha256'] == proof['parent']['sha256']:
            path = Path(artifact['source']).resolve()
            if not path.is_relative_to(ROOT / 'backup/narration'):
                raise ValueError('Context runtime artifact escaped ignored narration storage')
            return path
    actual = Path(actual_clip).resolve()
    media = actual.parents[len(directory.parts) + 1]
    if actual.relative_to(media).parts[:-1] != (*directory.parts, proof['locale']):
        raise ValueError('Context receipt is not beside its practice voice directory')
    return media / str(relative)


def source_identity(profile):
    if profile.get('model') == 'inclusionAI/Ming-3.0-tts-0.5B':
        from ming_narration import provenance
        return provenance({key: value for key, value in profile.items() if key != 'verification'})
    from f5_russian_narration import provenance
    return provenance(profile)


def _crop_rule(profile, code, proof):
    if (profile.get('model') != 'inclusionAI/Ming-3.0-tts-0.5B' or code != 'zh' or
            not isinstance(proof, dict) or proof.get('scope') != 'context_parent' or proof.get('locale') != code or
            proof.get('version') != VERSION or
            proof.get('voice_directory') != 'sunsalutation/voice'):
        return None
    policy_path = ROOT / proof['policy_path']
    policy = load_policy(policy_path)
    candidates = [row for row in policy['rules'] if row['locale'] == code and
                  pcm_hash(row['text'].encode()) == proof['text_sha256']]
    if len(candidates) != 1:
        return None
    rule = recipe(policy_path, code, candidates[0]['text'], proof['voice_directory'])
    if (not rule.get('crop_asr') or rule['sha256'] != proof['recipe_sha256'] or
            proof['proof_sha256'] != json_hash({key: value for key, value in proof.items() if key != 'proof_sha256'}) or
            proof['source_identity'] != source_identity(profile)):
        return None
    return rule


def crop_verification_identity(profile, code, proof):
    """Explicit Chinese short-crop QA only; ordinary synthesis identity is intact."""
    try:
        rule = _crop_rule(profile, code, proof)
        if rule is None:
            return None
        route = rule['crop_asr']
        return dict(profile_sha256=rule['policy_sha256'], model=route['model'], revision=route['revision'],
                    artifacts_sha256=json_hash(route['artifacts']), adapter_sha256=file_hash(__file__),
                    context_recipe_sha256=rule['sha256'])
    except (KeyError, TypeError, ValueError, OSError):
        return None


def _verified_crop_metadata(profile, code, proof, row, identity):
    try:
        expected = crop_verification_identity(profile, code, proof)
        if expected is None or identity != expected:
            return False
        samples = row['input_samples']
        return (row['model'] == expected['model'] and row['revision'] == expected['revision'] and
                row['artifacts_sha256'] == expected['artifacts_sha256'] and
                row['adapter_sha256'] == expected['adapter_sha256'] and row['language'] == code and
                row['audio_sha256'] == proof['clip_sha256'] and row['truncation'] is False and
                row['long_form'] is True and type(samples) is int and 0 < samples <= 16000 * 5.8 and
                type(row['seconds']) in (int, float) and math.isfinite(row['seconds']) and
                abs(samples / 16000 - row['seconds']) <= 1 / 16000)
    except (KeyError, TypeError, ValueError, OSError):
        return False


def verified_crop_transcription(profile, code, proof, row, identity):
    if not _verified_crop_metadata(profile, code, proof, row, identity):
        return False
    try:
        rule = _crop_rule(profile, code, proof)
        return words(row['text']) == words(rule['text'])
    except (KeyError, TypeError, ValueError, OSError):
        return False


def verify_speaker(config, profile, code, text, row, actual_clip_path):
    """Offline structural verification; parent and actual short metrics stay distinct."""
    try:
        proof = row['speaker_verification']
        body = {key: value for key, value in proof.items() if key != 'proof_sha256'}
        if (proof['scope'] != 'context_parent' or proof['version'] != VERSION or
                proof['proof_sha256'] != json_hash(body) or proof['locale'] != code or
                proof['text_sha256'] != pcm_hash(text.encode()) or
                proof['actual_clip_cosine'] != row['speaker_cosine'] or
                not math.isfinite(proof['actual_clip_cosine']) or
                not -1.00001 <= proof['actual_clip_cosine'] <= 1.00001 or
                not profile['minimum_speaker_cosine'] <= proof['parent_cosine'] <= 1.00001):
            return False
        rule = recipe(ROOT / proof['policy_path'], code, text, proof['voice_directory'])
        if (not rule or rule['sha256'] != proof['recipe_sha256'] or
                (config.get('_context_voice_directory') is not None and
                 config['_context_voice_directory'] != proof['voice_directory'])):
            return False
        if (file_hash(actual_clip_path) != proof['clip_sha256'] or row['sha256'] != proof['clip_sha256'] or
                packet_hash(actual_clip_path) != proof['crop']['encoded_packets_sha256'] or
                proof['source_identity'] != row['synthesis'] or
                proof['source_identity'] != source_identity(profile) or
                proof['source_identity']['model'] != profile['model'] or
                proof['source_identity']['model_revision'] != profile['model_revision'] or
                proof['source_identity']['reference_sha256'] != profile['reference_sha256']):
            return False
        parent = proof['parent']
        path = _parent_source(config, proof, actual_clip_path)
        pcm = read_wav(path)
        start, end = prefix_range(text, parent['alignment'], len(pcm) // 2,
            retain_leading_pcm0=rule.get('prefix_alignment') == RETAIN_LEADING_PCM0,
            comparison=rule_comparison(rule))
        if (file_hash(path) != parent['sha256'] or pcm_hash(pcm) != parent['pcm_sha256'] or
                parent['text'] != rule['parent_text'] or parent['text_sha256'] != pcm_hash(parent['text'].encode()) or
                not 0.5 <= len(pcm) / 48000 <= rule['maximum_parent_seconds'] or
                proof['crop']['start_sample'] != start or proof['crop']['end_sample'] != end or
                proof['crop']['pcm_sha256'] != pcm_hash(pcm[start * 2:end * 2]) or
                not 0.5 <= row['seconds'] <= 5.8 or not 0 <= proof['crop']['float_peak'] < 1):
            return False
        alignment = parent['alignment']
        if (alignment['model'] != ASR_MODEL or alignment['revision'] != ASR_REVISION or
                alignment['language'] != code or alignment['audio_sha256'] != parent['sha256'] or
                alignment['helper_sha256'] != file_hash(__file__) or
                alignment['truncation'] is not False or alignment['long_form'] is not True or
                abs(alignment['input_samples'] - len(pcm) / 3) > 2 or
                abs(alignment['seconds'] - len(pcm) / 48000) > 2 / 16000 or
                parent_match(verifier(), config, code, rule, alignment['text'], len(pcm) / 48000) < rule['minimum_parent_match']):
            return False
        if 'transcription' in row:
            transcript = row['transcription']
            crop_identity = crop_verification_identity(profile, code, proof)
            if rule.get('crop_asr'):
                if not verified_crop_transcription(profile, code, proof, transcript, row.get('verification')):
                    return False
                asr_model, asr_revision = crop_identity['model'], crop_identity['revision']
            elif profile.get('model') == 'inclusionAI/Ming-3.0-tts-0.5B':
                route = profile['verification']['routes'][code]
                asr_model, asr_revision = route['model'], route['revision']
            else:
                asr_model, asr_revision = profile['transcriber'], profile['asr_revision']
            duration = ogg_opus.opus_seconds(Path(actual_clip_path).read_bytes())
            if (transcript['audio_sha256'] != proof['clip_sha256'] or
                    comparison_words(transcript['text'], rule_comparison(rule)) != comparison_words(text, rule_comparison(rule)) or transcript['truncation'] is not False or
                    transcript['long_form'] is not True or transcript['model'] != asr_model or
                    transcript['revision'] != asr_revision or transcript['language'] != code or
                    abs(transcript['input_samples'] / 16000 - duration) > 2 / 16000 or
                    abs(transcript['seconds'] - duration) > 2 / 16000 or
                    abs(row['seconds'] - duration) > 0.001):
                return False
        return True
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError):
        return False


class ContextEngine:
    def __init__(self, engine, config, policy_path, local_path, *, encode, complete_match, identity, voice_directory):
        self.engine = engine
        self.profile = engine.profile
        self.config = config
        self.policy_path = Path(policy_path).resolve()
        load_policy(self.policy_path)
        self.local = json.loads(Path(local_path).read_text())
        self.encode = encode
        self.complete_match = complete_match
        self.identity = identity
        self.voice_directory = str(voice_directory)
        self.context = None
        self.context_artifacts = []
        self.last_speaker_verification = None
        self.context_diagnostics = {}
        self.last_context_verification = None
        self.last_transcription = None

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def base_speak(self, config, text, code, work, attempt):
        if config.get('_cached_only') and self.profile['model'] != 'inclusionAI/Ming-3.0-tts-0.5B':
            request = local_text_hash(config, text, self.profile, code)
            identity = json_hash(dict(request=request, attempt=attempt))
            cache = Path(self.engine.local['cache'])
            pcm, receipt = cache / (identity + '.pcm'), cache / (identity + '.json')
            if not pcm.is_file() or not receipt.is_file():
                raise RuntimeError('Cached-only context QA requires the original local PCM: ' + identity)
            saved = json.loads(receipt.read_text())
            if saved.get('request') != identity or saved.get('sha256') != file_hash(pcm):
                raise RuntimeError('Cached-only context QA found changed local PCM or receipt: ' + identity)
        return self.engine.speak(config, text, code, work, attempt)

    def speak(self, config, text, code, work, attempt):
        self.context = None
        self.context_artifacts = []
        self.last_speaker_verification = None
        self.context_diagnostics = {}
        self.last_context_verification = None
        self.last_transcription = None
        rule = recipe(self.policy_path, code, text, self.voice_directory)
        if not rule:
            return self.base_speak(config, text, code, work, attempt)
        if config['pcm_sample_rate'] != 24000:
            raise ValueError('Context extraction requires explicit 24 kHz PCM')
        cache = Path(self.local['cache']).resolve()
        subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(cache / 'probe')], check=True)
        cache.mkdir(parents=True, exist_ok=True)
        parent_work = Path(work) / 'context-parent'
        parent_work.mkdir(exist_ok=True)
        pcm, identity = self.base_speak(config, rule['parent_text'], code, parent_work, attempt)
        self.context_diagnostics = dict(locale=code, text=text, parent_text=rule['parent_text'],
            attempt=attempt, source_identity=identity, parent_pcm_sha256=pcm_hash(pcm),
            parent_seconds=len(pcm) / 48000, maximum_parent_seconds=rule['maximum_parent_seconds'])
        if identity != self.identity:
            raise RuntimeError('Context parent source identity failed')
        if not 0.5 <= len(pcm) / 48000 <= rule['maximum_parent_seconds']:
            raise ContextRejected('Context parent timing failed', self.context_diagnostics)
        wav = cache / (pcm_hash(pcm) + '.wav')
        write_wav(wav, pcm)
        command = [self.local['python'], str(Path(__file__).resolve()), '--align-audio', str(wav),
                   '--language', code, '--model', self.local['model'], '--policy', str(self.policy_path)]
        aligned_path = wav.with_suffix('.alignment.json')
        if aligned_path.exists():
            alignment = json.loads(aligned_path.read_text())
        else:
            alignment = None
        if not alignment or alignment.get('helper_sha256') != file_hash(__file__):
            alignment = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
            aligned_path.write_text(json.dumps(alignment, ensure_ascii=False, indent=2) + '\n')
        if (alignment['audio_sha256'] != file_hash(wav) or alignment['model'] != ASR_MODEL or
                alignment['revision'] != ASR_REVISION or alignment['language'] != code or
                alignment['truncation'] is not False or alignment['long_form'] is not True or
                abs(alignment['input_samples'] / 16000 - len(pcm) / 48000) > 2 / 16000 or
                abs(alignment['seconds'] - len(pcm) / 48000) > 2 / 16000):
            raise RuntimeError('Context parent transcription integrity failed')
        parent_score = parent_match(self.complete_match, config, code, rule, alignment['text'], len(pcm) / 48000)
        self.context_diagnostics.update(parent_audio_sha256=file_hash(wav), parent_transcription=alignment,
            parent_match=parent_score, minimum_parent_match=rule['minimum_parent_match'])
        if parent_score < rule['minimum_parent_match']:
            raise ContextRejected('Complete context parent transcription failed', self.context_diagnostics)
        cosine = self.engine.speaker_match(wav)
        self.context_diagnostics.update(parent_cosine=cosine,
            minimum_parent_cosine=self.profile['minimum_speaker_cosine'])
        if not self.profile['minimum_speaker_cosine'] <= cosine <= 1.00001:
            raise ContextRejected('Context parent female-reference consistency failed', self.context_diagnostics)
        try:
            start, end = prefix_range(text, alignment, len(pcm) // 2,
                retain_leading_pcm0=rule.get('prefix_alignment') == RETAIN_LEADING_PCM0,
                comparison=rule_comparison(rule))
        except ValueError as error:
            raise ContextRejected(str(error), self.context_diagnostics) from error
        crop = pcm[start * 2:end * 2]
        self.context_diagnostics.update(crop_start_sample=start, crop_end_sample=end,
            crop_pcm_sha256=pcm_hash(crop))
        parent_sha = file_hash(wav)
        directory = PurePosixPath(self.voice_directory)
        relative = directory.parent / (directory.name + '-context') / code / (parent_sha + '.wav')
        self.context_artifacts = [dict(source=str(wav), destination_relative=str(relative), sha256=parent_sha)]
        self.context = dict(rule=rule, text=text, code=code, pcm=crop, cosine=cosine,
                            parent=dict(file=str(relative), sha256=parent_sha, pcm_sha256=pcm_hash(pcm),
                                        text=rule['parent_text'], text_sha256=pcm_hash(rule['parent_text'].encode()),
                                        alignment=alignment), start=start, end=end, work=Path(work))
        return crop, identity

    def speaker_match(self, clip):
        actual_cosine = self.engine.speaker_match(clip)
        if self.context is None:
            self.last_speaker_verification = None
            return actual_cosine
        state = self.context
        self.context_diagnostics.update(actual_clip_cosine=actual_cosine,
            actual_clip_sha256=file_hash(clip))
        expected_work = state['work'] / 'context-expected-crop'
        expected_work.mkdir(exist_ok=True)
        expected = self.encode(self.config, state['pcm'], expected_work)
        if packet_hash(clip) != packet_hash(expected):
            raise RuntimeError('Encoded audio is not the exact expected parent crop')
        raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1',
                                       '-i', str(clip), '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'])
        samples = array.array('f', raw)
        if not samples or not all(math.isfinite(value) for value in samples):
            raise RuntimeError('Nonfinite context crop audio')
        peak = max(abs(value) for value in samples)
        self.context_diagnostics['crop_float_peak'] = peak
        if peak >= 1:
            raise ContextRejected('Context crop exceeded full scale', self.context_diagnostics)
        proof = dict(scope='context_parent', version=VERSION, policy_path=state['rule']['policy_path'],
                     recipe_sha256=state['rule']['sha256'], locale=state['code'], text_sha256=pcm_hash(state['text'].encode()),
                     voice_directory=self.voice_directory, source_identity=self.identity,
                     actual_clip_cosine=actual_cosine, parent_cosine=state['cosine'], gender_verified=False,
                     clip_sha256=file_hash(clip), parent=state['parent'],
                     crop=dict(start_sample=state['start'], end_sample=state['end'], pcm_sha256=pcm_hash(state['pcm']),
                               encoded_packets_sha256=packet_hash(expected), float_peak=peak))
        proof['proof_sha256'] = json_hash(proof)
        self.last_speaker_verification = proof
        return actual_cosine

    def transcribe(self, clip, code):
        proof = self.last_speaker_verification
        if self.context is not None and self.context['rule'].get('crop_asr'):
            identity = crop_verification_identity(self.profile, code, proof)
            if identity is None:
                raise ValueError('Unsupported final context transcription identity')
            # The routed Ming verifier retains its recognizer. Release it before
            # running the separately pinned short-crop recognizer subprocess.
            if hasattr(self.engine, 'asr'):
                import gc
                self.engine.asr = None
                self.engine.asr_model = None
                gc.collect()
            command = [self.local['python'], str(Path(__file__).resolve()), '--transcribe-audio', str(clip),
                       '--language', code, '--model', self.local['model'], '--policy', str(self.policy_path)]
            row = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
            if not _verified_crop_metadata(self.profile, code, proof, row, identity):
                raise RuntimeError('Final context transcription integrity failed')
            if words(row['text']) != words(self.context['text']):
                self.context_diagnostics['crop_transcript'] = row['text']
                self.context_diagnostics['crop_transcription'] = row
                raise ContextRejected('Context crop contains missing, changed or adjacent words', self.context_diagnostics)
            self.last_context_verification = identity
            self.last_transcription = row
            text = row['text']
        else:
            text = self.engine.transcribe(clip, code)
            self.last_transcription = getattr(self.engine, 'last_transcription', None)
        if (self.context is not None and
                comparison_words(text, rule_comparison(self.context['rule'])) !=
                comparison_words(self.context['text'], rule_comparison(self.context['rule']))):
            self.context_diagnostics['crop_transcript'] = text
            raise ContextRejected('Context crop contains missing, changed or adjacent words', self.context_diagnostics)
        return text


def align_audio(audio, code, model_path, policy_path):
    """Blind official Whisper token timestamps: only audio and language are inputs."""
    policy = load_policy(policy_path)
    helper_sha256 = file_hash(__file__)
    model_path = Path(model_path)
    for name, digest in policy['asr_artifacts'].items():
        if file_hash(model_path / name) != digest:
            raise ValueError('Changed context alignment model artifact')
    import os
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    import numpy as np
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    torch.set_num_threads(2)
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i', str(audio),
                                   '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'])
    waveform = np.frombuffer(raw, dtype='<f4').copy()
    if not 0 < len(waveform) <= 16000 * 5.8 or not np.isfinite(waveform).all():
        raise ValueError('Context parent exceeds its complete alignment budget')
    processor = WhisperProcessor.from_pretrained(model_path, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(model_path, local_files_only=True,
                low_cpu_mem_usage=True, attn_implementation='eager').eval()
    features = processor(waveform, sampling_rate=16000, return_tensors='pt', return_attention_mask=True)
    with torch.inference_mode():
        output = model.generate(input_features=features.input_features, attention_mask=features.attention_mask,
            language=code, task='transcribe', return_timestamps=True, return_token_timestamps=True,
            return_dict_in_generate=True, max_new_tokens=256, do_sample=False,
            num_frames=len(waveform) // processor.feature_extractor.hop_length)
    text, timing = processor.tokenizer._decode_asr(
        [dict(tokens=output.sequences.cpu().numpy(), token_timestamps=output.token_timestamps.cpu().numpy())],
        return_timestamps='word', return_language=False, time_precision=0.02)
    return dict(text=text.strip(), language=code, model=ASR_MODEL, revision=ASR_REVISION,
                audio_sha256=file_hash(audio), input_samples=len(waveform), seconds=len(waveform) / 16000,
                truncation=False, long_form=True, helper_sha256=helper_sha256,
                words=[dict(text=row['text'].strip(), start=row['timestamp'][0], end=row['timestamp'][1])
                       for row in timing['chunks']])


def transcribe_audio(audio, code, model_path, policy_path):
    """Blind complete-crop QA; the only inputs are actual audio and language."""
    policy = load_policy(policy_path)
    if code != 'zh':
        raise ValueError('The explicit final-crop recognizer is limited to Chinese')
    model_path = Path(model_path)
    for name, digest in policy['asr_artifacts'].items():
        if file_hash(model_path / name) != digest:
            raise ValueError('Changed context crop recognition model artifact')
    import os
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    import numpy as np
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    torch.set_num_threads(2)
    raw = subprocess.check_output(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i', str(audio),
                                   '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'])
    waveform = np.frombuffer(raw, dtype='<f4').copy()
    if not 0 < len(waveform) <= 16000 * 5.8 or not np.isfinite(waveform).all():
        raise ValueError('Invalid complete context crop audio')
    processor = WhisperProcessor.from_pretrained(model_path, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(model_path, local_files_only=True,
                low_cpu_mem_usage=True).eval()
    features = processor(waveform, sampling_rate=16000, return_tensors='pt', truncation=False,
                         padding='longest', return_attention_mask=True)
    with torch.inference_mode():
        tokens = model.generate(input_features=features.input_features, attention_mask=features.attention_mask,
            language=code, task='transcribe', return_timestamps=True, max_new_tokens=440, do_sample=False)
    return dict(text=processor.batch_decode(tokens, skip_special_tokens=True)[0].strip(), language=code,
                model=ASR_MODEL, revision=ASR_REVISION, artifacts_sha256=json_hash(policy['asr_artifacts']),
                adapter_sha256=file_hash(__file__), audio_sha256=file_hash(audio),
                input_samples=len(waveform), seconds=len(waveform) / 16000, truncation=False, long_form=True)


def configure():
    text_root = ROOT / 'design/sun-salutation/narration/text'
    config = json.loads((ROOT / 'design/sun-salutation/narration/narration.json').read_text())
    rules = []
    for code in ('pt', 'cs', 'ru', 'es', 'fr', 'zh'):
        source_path = narration_text_path(config, code, text_root)
        raw = source_path.read_text()
        entries = dict(re.findall(r'\[([^\]]+)\]\n(.*?)(?=\n---|\Z)', raw, re.S))
        for short_key, parent_key in [('sun_salutation_voice_breathe_in', 'sun_salutation_voice_lunge_right'),
                                      ('sun_salutation_voice_breathe_out', 'sun_salutation_voice_forward_fold')]:
            if code == 'zh' and short_key == 'sun_salutation_voice_breathe_out':
                parent_key = 'sun_salutation_voice_plank'
            if code == 'pt' and short_key == 'sun_salutation_voice_breathe_out':
                parent_key = 'sun_salutation_voice_downward_dog'
            text = entries[short_key].strip()
            parent = entries.get(parent_key, '').strip()
            if not parent or words(parent)[:len(words(text))] != words(text):
                alternatives = [(key, value.strip()) for key, value in entries.items()
                                if key != short_key and words(value)[:len(words(text))] == words(text)
                                and len(words(value)) > len(words(text))]
                if not alternatives:
                    continue
                parent_key, parent = min(alternatives, key=lambda item: len(item[1]))
            rules.append(dict(locale=code, text=text, parent_text=parent,
                              parent_source=dict(file=str(source_path.relative_to(ROOT)),
                                                 key=parent_key, sha256=file_hash(source_path)),
                              maximum_parent_seconds=5.8, minimum_parent_match=0.92))
            if (code, short_key) in (('cs', 'sun_salutation_voice_breathe_out'),
                                    ('ru', 'sun_salutation_voice_breathe_in')):
                rules[-1]['prefix_alignment'] = RETAIN_LEADING_PCM0
    profile = json.loads((ROOT / 'design/narration/chatterbox-czech.json').read_text())
    for rule in rules:
        if rule['locale'] == 'zh':
            rule['crop_asr'] = dict(model=ASR_MODEL, revision=ASR_REVISION, artifacts=profile['asr_artifacts'])
    policy = dict(version=VERSION, helper_sha256=file_hash(__file__),
                  verifier_sha256=file_hash(ROOT / 'scripts/generate-lumi-guide-narration.py'),
                  voice_directory='sunsalutation/voice', asr_model=ASR_MODEL, asr_revision=ASR_REVISION,
                  asr_artifacts=profile['asr_artifacts'], rules=rules)
    POLICY.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + '\n')
    local_path = ROOT / 'backup/narration/context-local.json'
    subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(local_path)], check=True)
    local = dict(python='/mnt/storage/Projects/waozixyz/learning/jungle/local/speech-development/ming-evaluation/venv/bin/python',
                 model='/mnt/storage/Projects/harness/models/weights/asr/whisper-large-v3-turbo',
                 cache=str(ROOT / 'backup/narration/local-models/context-cache'))
    local_path.write_text(json.dumps(local, indent=2) + '\n')
    for rule in rules:
        recipe(POLICY, rule['locale'], rule['text'], policy['voice_directory'])
    print('Explicit context policy and ignored local paths configured; no synthesis performed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--align-audio', type=Path)
    parser.add_argument('--transcribe-audio', type=Path)
    parser.add_argument('--language')
    parser.add_argument('--model', type=Path)
    parser.add_argument('--policy', type=Path, default=POLICY)
    args = parser.parse_args()
    if args.configure:
        configure()
    elif args.transcribe_audio and args.language and args.model:
        print(json.dumps(transcribe_audio(args.transcribe_audio, args.language, args.model, args.policy), ensure_ascii=False))
    elif args.align_audio and args.language and args.model:
        print(json.dumps(align_audio(args.align_audio, args.language, args.model, args.policy), ensure_ascii=False))
    else:
        parser.error('Select --configure or --align-audio with --language and --model')
