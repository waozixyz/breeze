"""Independent, pinned transcript verification without changing Ming speech identity.

Only the verification block is new. Removing it reconstructs the exact original
generation profile, so existing PCM and its synthesis provenance remain intact.
"""
import gc
import json
import os
from pathlib import Path
import re
import subprocess

import ming_narration as ming

LANGUAGES = ming.LANGUAGES
MODELS = {
    'openai/whisper-small': '973afd24965f72e36ca33b3055d56a652f456b4d',
    'openai/whisper-large-v3-turbo': '41f01f3fe87f28c78e2fbf8b568835947dd65ed9',
}


def synthesis_profile(profile):
    return {key: value for key, value in profile.items() if key != 'verification'}


def validate(profile):
    ming.validate(synthesis_profile(profile))
    settings = profile.get('verification')
    if settings is None:
        return
    if (settings.get('mode') != 'per-locale-whisper-v1' or
            settings.get('adapter_sha256') != ming.file_hash(__file__) or
            set(settings.get('routes', {})) != set(LANGUAGES)):
        raise ValueError('Unsupported Ming verification profile')
    for code, route in settings['routes'].items():
        expected_model = 'openai/whisper-large-v3-turbo' if code in ('ja', 'ko') else 'openai/whisper-small'
        if (route.get('model') != expected_model or
                route.get('revision') != MODELS[expected_model] or not route.get('artifacts')):
            raise ValueError('Unpinned Ming ASR route: ' + code)
        for name, digest in route['artifacts'].items():
            path = Path(name)
            if (path.is_absolute() or '..' in path.parts or
                    not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
                raise ValueError('Invalid Ming ASR artifact: ' + name)
    compatible = settings.get('compatible', {})
    if not isinstance(compatible, dict) or set(compatible) - set(LANGUAGES):
        raise ValueError('Invalid compatible verifier locales')
    fields = {'profile_sha256', 'model', 'revision', 'artifacts_sha256', 'adapter_sha256'}
    for code, identities in compatible.items():
        route = settings['routes'][code]
        if not isinstance(identities, list) or len(identities) > 8:
            raise ValueError('Unbounded compatible verifier identities')
        for identity in identities:
            if (not isinstance(identity, dict) or set(identity) != fields or
                    identity['model'] != route['model'] or identity['revision'] != route['revision'] or
                    identity['artifacts_sha256'] != ming.json_hash(route['artifacts']) or
                    any(not isinstance(identity[field], str) or not re.fullmatch('[0-9a-f]{64}', identity[field])
                        for field in ('profile_sha256', 'artifacts_sha256', 'adapter_sha256'))):
                raise ValueError('Compatible verifier must use the same actual locale model and artifacts')


def descriptor(config):
    profile = ming.descriptor(config)
    if profile is not None:
        validate(profile)
    return profile


def provenance(profile):
    return ming.provenance(synthesis_profile(profile))


def text_hash(config, text, profile, code):
    return ming.text_hash(config, text, synthesis_profile(profile), code)


def transcriber(profile, code):
    settings = profile.get('verification')
    if settings is None:
        return profile['transcriber']
    route = settings['routes'][code]
    return route['model'] + '@' + route['revision']


def verification_identity(profile, code):
    settings = profile.get('verification')
    if settings is None:
        return None
    route = settings['routes'][code]
    return dict(profile_sha256=ming.json_hash(settings), model=route['model'],
                revision=route['revision'], artifacts_sha256=ming.json_hash(route['artifacts']),
                adapter_sha256=settings['adapter_sha256'])


def verified_transcription(profile, code, row, verification):
    expected = verification_identity(profile, code)
    if expected is None:
        return True
    samples = row.get('input_samples')
    accepted = [expected] + profile['verification'].get('compatible', {}).get(code, [])
    return (verification in accepted and row.get('model') == expected['model'] and
            row.get('revision') == expected['revision'] and row.get('language') == code and
            row.get('artifacts_sha256') == expected['artifacts_sha256'] and
            type(samples) is int and samples > 0 and
            abs(samples / 16000 - row.get('seconds', 0)) <= 1 / 16000)


class Recognizer:
    def __init__(self, path, route, threads):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads))
        import torch
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        torch.set_num_threads(threads)
        self.torch, self.route = torch, route
        self.processor = WhisperProcessor.from_pretrained(path, local_files_only=True)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            path, local_files_only=True, low_cpu_mem_usage=True).eval()

    def transcribe(self, path, code):
        import numpy as np
        raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1',
                              '-i', str(path), '-f', 'f32le', '-ar', '16000', '-ac', '1', '-'],
                             check=True, capture_output=True).stdout
        audio = np.frombuffer(raw, dtype='<f4').copy()
        if not 0 < len(audio) <= 16000 * 120 or not np.isfinite(audio).all():
            raise ValueError('Invalid or oversized complete narration for QA')
        features = self.processor(audio, sampling_rate=16000, return_tensors='pt',
                                  truncation=False, padding='longest', return_attention_mask=True)
        with self.torch.inference_mode():
            tokens = self.model.generate(input_features=features.input_features,
                attention_mask=features.attention_mask, language=code, task='transcribe',
                return_timestamps=True, max_new_tokens=440, do_sample=False)
        return dict(text=self.processor.batch_decode(tokens, skip_special_tokens=True)[0].strip(),
                    language=code, model=self.route['model'], revision=self.route['revision'],
                    artifacts_sha256=ming.json_hash(self.route['artifacts']),
                    audio_sha256=ming.file_hash(path), seconds=len(audio) / 16000,
                    input_samples=len(audio), truncation=False, long_form=True)


class VerifiedEngine:
    def __init__(self, profile, local_path):
        validate(profile)
        self.profile = profile
        self.generation = ming.Engine(synthesis_profile(profile), local_path)
        self.local = json.loads(Path(local_path).read_text())
        self.asr = None
        self.asr_model = None
        self.last_transcription = None
        checked = set()
        for route in profile['verification']['routes'].values():
            if route['model'] in checked:
                continue
            checked.add(route['model'])
            path = Path(self.local['verification_models'][route['model']])
            for name, digest in route['artifacts'].items():
                if ming.file_hash(path / name) != digest:
                    raise ValueError('Changed verification model artifact: ' + name)

    @property
    def last_generation(self):
        return self.generation.last_generation

    def speak(self, config, text, code, work, attempt):
        if config.get('_cached_only'):
            original = synthesis_profile(self.profile)
            identity = ming.json_hash(dict(synthesis=ming.provenance(original), text=text,
                language=code, attempt=attempt,
                request_sha256=ming.text_hash(config, text, original, code),
                pcm_sample_rate=config['pcm_sample_rate']))
            cache = Path(__file__).resolve().parents[1] / 'backup/narration/cache'
            pcm, receipt = cache / (identity + '.pcm'), cache / (identity + '.json')
            if (not pcm.is_file() or not receipt.is_file() or
                    json.loads(receipt.read_text()).get('sha256') != ming.file_hash(pcm)):
                raise RuntimeError('Cached-only QA requires the original verified PCM cache: ' + identity)
        return self.generation.speak(config, text, code, work, attempt)

    def speaker_match(self, clip):
        return self.generation.speaker_match(clip)

    def transcribe(self, clip, code):
        route = self.profile['verification']['routes'][code]
        if self.asr_model != route['model']:
            # Release before loading: one recognizer per engine, including switches.
            self.asr = None
            self.asr_model = None
            gc.collect()
            self.asr = Recognizer(self.local['verification_models'][route['model']],
                                  route, self.generation.threads)
            self.asr_model = route['model']
        row = self.asr.transcribe(clip, code)
        if (not verified_transcription(self.profile, code, row, verification_identity(self.profile, code)) or
                row.get('audio_sha256') != ming.file_hash(clip) or
                row.get('truncation') is not False or not row.get('long_form') or
                not 0 < row.get('seconds', 0) <= 120):
            raise RuntimeError('ASR did not verify the complete selected audio with its pinned model')
        self.last_transcription = row
        return row['text'].strip()


def Engine(profile, local_path):
    if 'verification' not in profile:
        return ming.Engine(profile, local_path)
    return VerifiedEngine(profile, local_path)
